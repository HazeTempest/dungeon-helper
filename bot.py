import os
import aiohttp
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
NPOINT_URL = os.getenv("NPOINT_WEAPONS_URL")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

class WeaponView(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def fetch_weapons(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(NPOINT_URL) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", [])
                return []

    @commands.command(name="weapon", aliases=["w"])
    async def view_weapon(self, ctx, character: str, *, weapon_name: str):
        """View details of a specific weapon for a character folder."""
        data = await self.fetch_weapons()
        
        # Find the character folder (case-insensitive)
        char_folder = next((group for group in data if group.get("folder", "").lower() == character.lower()), None)
        
        if not char_folder:
            return await ctx.send(f"❌ Character folder **'{character}'** not found.")

        # Find the weapon by urlName or file name (case-insensitive)
        weapon_query = weapon_name.lower().replace(" ", "-")
        weapon = next((w for w in char_folder.get("weapons", []) 
                       if w.get("urlName") == weapon_query or 
                       w.get("file", "").lower().replace(".png", "") == weapon_name.lower()), None)

        if not weapon:
            return await ctx.send(f"❌ Weapon **'{weapon_name}'** not found under **{character}**.")

        # Build an embed for clean viewing
        embed = discord.Embed(
            title=f"{weapon.get('file', '').replace('.png', '')} ({character.capitalize()})",
            description=weapon.get("description", "No description available."),
            color=discord.Color.blue()
        )
        
        embed.add_field(name="WSAP", value=weapon.get("WSAP", "N/A"), inline=True)
        embed.add_field(name="Cooldown", value=weapon.get("cooldown", "N/A"), inline=True)
        
        price = weapon.get("price", "0")
        price_type = weapon.get("priceType", "Gem")
        embed.add_field(name="Price", value=f"{price} {price_type}", inline=True)
        
        tags = weapon.get("tags", [])
        if tags and tags != ["-"]:
            embed.add_field(name="Tags", value=", ".join(tags), inline=False)
        else:
            embed.add_field(name="Tags", value="None", inline=False)

        if weapon.get("recommended") == 1:
            embed.set_footer(text="⭐ Recommended Weapon")

        await ctx.send(embed=embed)

@bot.event
async def on_ready():
    await bot.add_cog(WeaponView(bot))
    print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    print("------")

# Run the bot using the token loaded from the .env file
bot.run(DISCORD_TOKEN)