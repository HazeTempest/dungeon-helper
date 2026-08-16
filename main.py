# bot.py
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

class MainBot(commands.Bot):
    async def setup_hook(self):
        # Load cogs dynamically from the 'cogs' folder
        initial_extensions = [
            "cogs.artifacts",
            "cogs.collections",
            "cogs.characters",
            "cogs.skills",
            "cogs.weapons",
            "cogs.extras"
        ]
        for extension in initial_extensions:
            try:
                await self.load_extension(extension)
                print(f"Loaded extension: {extension}")
            except Exception as e:
                print(f"Failed to load extension {extension}: {e}")

if __name__ == "__main__":
    bot = MainBot(command_prefix="!", intents=intents)
    bot.run(DISCORD_TOKEN)