import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

class DungeonSlasherBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.default())

    async def setup_hook(self):
        # Ensure cogs directory exists
        if not os.path.exists("./cogs"):
            os.makedirs("./cogs")
        
        # Load all cogs dynamically from the cogs folder
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                cog_name = filename[:-3]
                await self.load_extension(f"cogs.{cog_name}")
                print(f"Loaded cog: {cog_name}")
        
        # Sync global slash commands with Discord
        await self.tree.sync()
        print("Slash commands synced successfully.")

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")

bot = DungeonSlasherBot()

if __name__ == "__main__":
    if not TOKEN:
        print("Error: DISCORD_TOKEN not found in environment variables.")
    else:
        bot.run(TOKEN)