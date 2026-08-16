import os
import discord
from discord.ext import commands
from discord import app_commands

class CodeRedeemCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="code-redeem", description="Guide on how to redeem codes in Dungeon Slasher")
    async def code_redeem(self, interaction: discord.Interaction):
        c = discord.Color.gold()
        embed = discord.Embed(
            title="🎁 Dungeon Slasher: Code Redemption Guide",
            description=(
                "Follow these steps to redeem your active promo codes:\n\n"
                "1. Open the **Settings** menu in-game.\n"
                "2. Navigate to the **Account / Other** tab.\n"
                "3. Tap on **Coupon Code** and enter your code.\n\n"
                "-# Make sure to check for any case sensitivity or trailing spaces!"
            ),
            color=c
        )
        
        file = None
        if os.path.exists("cecicode.png"):
            file = discord.File("cecicode.png", filename="cecicode.png")
            embed.set_image(url="attachment://cecicode.png")

        await interaction.response.send_message(embed=embed, file=file if file else None)

async def setup(bot):
    await bot.add_cog(CodeRedeemCog(bot))