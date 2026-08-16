# cogs/extras.py
import os
import discord
from discord import app_commands
from discord.ext import commands

class ExtrasCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="code-redeem", description="Displays the code redemption guide and instructions")
    async def code_redeem(self, interaction: discord.Interaction):
        file_path = "cecicodes.png"
        
        if not os.path.exists(file_path):
            return await interaction.response.send_message(
                "The code redemption image (`cecicodes.png`) could not be found on the server directory.", 
                ephemeral=True
            )
        
        file = discord.File(file_path, filename="cecicode.png")
        embed = discord.Embed(
            title="lmao",
            color=discord.Color.blurple()
        )
        embed.set_image(url="attachment://cecicode.png")
        
        await interaction.response.send_message(embed=embed, file=file)

    @app_commands.command(name="beginner-tips", description="Essential tips and tricks for getting started in Dungeon Slasher")
    async def beginner_tips(self, interaction: discord.Interaction):
        c, files = discord.Color.gold(), [discord.File(img) for img in ["kelsey_guide.png", "tag_combinations.png"] if os.path.exists(img)]
        
        embeds = [
            discord.Embed(title="Beginner Tips", 
                          description="""# Game Tips
- Press, Settings, Graphics, set __**Skill Transparency to low**__. This will help you see your mistakes in 4K 
- __**New Player Missions**__ will need __**Level 30 Knight**__ to complete it's last task
-# It will give you 2 characters or 3k gems each if you have them
- __**Artifacts do not grant synergy**__ unless it says "Gains X synergy when equipped"
- Artifacts must have the __**same Tag**__ to boost the Skill
- Most __**Characters have Tag Restrictions**__ making certain Artifacts and Skills unavailable. This makes them use less bans and easier to build 
-# Artifacts and Skills have Words above their icon called __**Tags**__ 
- __**Sin Points**__ have a maximum of 40. 20 from Unlocking Artifacts, and 20 from first clearing each of the 20 floors of Arena mode. 
-# 10 points to Gluttony
- __**Don't unlock too much**__ as it makes it harder to build  
- __**Real Kelsey**__ is the one that is not smoking """, color=c),
            discord.Embed(color=c),
            discord.Embed(color=c),
            discord.Embed(title="Here are some common questions:", 
                          description="""## Basic Currencies
- Best way to earn Soulstones is to run around the dungeon IN NORMAL MODE skipping all Chapter 1 mobs and watch the 1000 Soulstone ads
continue the run after skipping chapter 1
- Breachstones/Riftstones are used to level characters after level 30, they're from CHALLENGE MODE after beating the game
- Challenge mode doesn't drop Soulstones
- Prayerstones are used to roll item blessings at the start of the game and roll conditions for a game mode unlocked after beating normal mode
not recommended to roll for blessings
- Mileage Points are EXCLUSIVELY EARNED by spending money and is 5% of your product in KR Won
- Gems are mainly obtained by doing daily, weekly and achievement missions for 950
-# you get most of your early gems by unlocking things in the unlock menu, or doing challenges on the mission tab
- Sin Points have a maximum of 40. 20 from Unlocking Artifacts, and 20 from first clearing each of the 20 floors of Arena mode.
## Basics
- Some Characters are not fully functionable for new players due to needing Riftstones for Masteries to work
- Plunging Attacks stuns enemies and is performed by, Double Jump, Down Movement + Basic Attack""", color=c)
        ]
        
        for i, file in enumerate(files):
            embeds[i + 1].set_image(url=f"attachment://{file.filename}")

        active_embeds = [embeds[0]] + embeds[1:1+len(files)] + [embeds[3]]
        await interaction.response.send_message(embeds=active_embeds, files=files or None)

async def setup(bot):
    await bot.add_cog(ExtrasCog(bot))