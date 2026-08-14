import json
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

if not DISCORD_TOKEN:
    raise ValueError("❌ Error: DISCORD_TOKEN is missing or not loaded from the .env file.")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

class WeaponSelectView(discord.ui.View):
    def __init__(self, data):
        super().__init__(timeout=180)
        self.data = data
        
        # Populate character dropdown options (max 25 options limit per select menu)
        char_options = [
            discord.SelectOption(label=group.get("folder", "").capitalize(), value=group.get("folder", ""))
            for group in data if "folder" in group
        ][:25]
        
        self.char_select = discord.ui.Select(
            placeholder="Choose a character...",
            min_values=1,
            max_values=1,
            options=char_options
        )
        self.char_select.callback = self.char_callback
        self.add_item(self.char_select)

    async def char_callback(self, interaction: discord.Interaction):
        selected_folder = self.char_select.values[0]
        
        # Find the selected character's weapons
        char_data = next((g for g in self.data if g.get("folder") == selected_folder), None)
        if not char_data:
            return await interaction.response.send_message("❌ Character data not found.", ephemeral=True)

        weapons = char_data.get("weapons", [])[:25]
        
        # Build weapon options
        weapon_options = [
            discord.SelectOption(
                label=w.get("file", "").replace(".png", ""),
                value=w.get("urlName"),
                description=f"WSAP: {w.get('WSAP', 'N/A')} | Cooldown: {w.get('cooldown', 'N/A')}"
            )
            for w in weapons
        ]

        # Create a new view for the weapon selection dropdown
        weapon_view = discord.ui.View(timeout=180)
        weapon_select = discord.ui.Select(
            placeholder=f"Choose a weapon for {selected_folder.capitalize()}...",
            min_values=1,
            max_values=1,
            options=weapon_options
        )

        async def weapon_callback(w_interaction: discord.Interaction):
            selected_url_name = weapon_select.values[0]
            chosen_weapon = next((w for w in weapons if w.get("urlName") == selected_url_name), None)
            
            if not chosen_weapon:
                return await w_interaction.response.send_message("❌ Weapon not found.", ephemeral=True)

            # Build embed for the selected weapon
            embed = discord.Embed(
                title=f"{chosen_weapon.get('file', '').replace('.png', '')} ({selected_folder.capitalize()})",
                description=chosen_weapon.get("description", "No description available."),
                color=discord.Color.blue()
            )
            
            embed.add_field(name="WSAP", value=chosen_weapon.get("WSAP", "N/A"), inline=True)
            embed.add_field(name="Cooldown", value=chosen_weapon.get("cooldown", "N/A"), inline=True)
            
            price = chosen_weapon.get("price", "0")
            price_type = chosen_weapon.get("priceType", "Gem")
            embed.add_field(name="Price", value=f"{price} {price_type}", inline=True)
            
            tags = chosen_weapon.get("tags", [])
            if tags and tags != ["-"]:
                embed.add_field(name="Tags", value=", ".join(tags), inline=False)
            else:
                embed.add_field(name="Tags", value="None", inline=False)

            if chosen_weapon.get("recommended") == 1:
                embed.set_footer(text="⭐ Recommended Weapon")

            # Update message to show the weapon embed and remove dropdowns
            await w_interaction.response.edit_message(content="Here is your weapon info:", embed=embed, view=None)

        weapon_select.callback = weapon_callback
        weapon_view.add_item(weapon_select)

        # Update the message with the weapon dropdown menu
        await interaction.response.edit_message(content=f"Character selected: **{selected_folder.capitalize()}**. Now select a weapon:", view=weapon_view)


class WeaponCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def load_weapons(self):
        """Loads weapon data locally from the JSON file."""
        try:
            with open("ds_wiki_npoint_weapons.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("data", [])
        except Exception as e:
            print(f"Error loading local json file: {e}")
            return []

    @commands.command(name="weapon", aliases=["w"])
    async def weapon_command(self, ctx):
        """Starts the interactive weapon lookup process via dropdowns."""
        data = self.load_weapons()
        if not data:
            return await ctx.send("❌ Failed to load local weapon data.")

        view = WeaponSelectView(data)
        await ctx.send("Select a character folder:", view=view)

@bot.event
async def on_ready():
    await bot.add_cog(WeaponCog(bot))
    print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    print("------")

bot.run(DISCORD_TOKEN)