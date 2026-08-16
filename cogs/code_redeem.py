import os
import discord
from discord.ext import commands
from discord import app_commands

class CodeRedeemCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="code-redeem", description="Displays the code redemption guide and instructions")
    async def code_redeem(interaction: discord.Interaction):
        file_path = "cecicodes.png"
        
        if not os.path.exists(file_path):
            return await interaction.response.send_message(
                "The code redemption image (`cecicode.png`) could not be found on the server directory.", 
                ephemeral=True
            )
        
        file = discord.File(file_path, filename="cecicode.png")
        embed = discord.Embed(
            title="lmao",
            color=discord.Color.blurple()
        )
        embed.set_image(url="attachment://cecicode.png")
    
        await interaction.response.send_message(embed=embed, file=file)

async def setup(bot):
    await bot.add_cog(CodeRedeemCog(bot))