# cogs/weapons.py
import discord
from discord import app_commands
from discord.ext import commands
from utils import WEAPONS_DATA

class WeaponDropdownView(discord.ui.View):
    def __init__(self, char_folder: str, weapons: list):
        super().__init__(timeout=180)
        self.char_folder = char_folder
        self.weapons = weapons

        options = [
            discord.SelectOption(
                label=str(w.get("file", "")).replace(".png", "")[:100],
                value=str(w.get("urlName", w.get("file", "")))[:100],
                description=f"WSAP: {w.get('WSAP', 'N/A')} | CD: {w.get('cooldown', 'N/A')}"[:100],
            )
            for w in weapons[:25] if isinstance(w, dict)
        ]

        if not options:
            options = [discord.SelectOption(label="No weapons found", value="none")]

        select = discord.ui.Select(
            placeholder=f"Choose a weapon for {char_folder.capitalize()}...",
            options=options
        )
        select.callback = self.weapon_callback
        self.add_item(select)

    async def weapon_callback(self, interaction: discord.Interaction):
        selected_val = interaction.data["values"][0]
        if selected_val == "none":
            return await interaction.response.send_message("❌ No valid weapons available.", ephemeral=True)

        chosen_weapon = next(
            (w for w in self.weapons if isinstance(w, dict) and str(w.get("urlName", w.get("file", ""))) == selected_val),
            None
        )

        if not chosen_weapon:
            return await interaction.response.send_message("❌ Weapon details not found.", ephemeral=True)

        embed = discord.Embed(
            title=f"{str(chosen_weapon.get('file', '')).replace('.png', '')} ({self.char_folder.capitalize()})",
            description=str(chosen_weapon.get("description", "No description available.")),
            color=discord.Color.red(),
        )
        embed.add_field(name="WSAP", value=str(chosen_weapon.get("WSAP", "N/A")), inline=True)
        embed.add_field(name="Cooldown", value=str(chosen_weapon.get("cooldown", "N/A")), inline=True)

        price = chosen_weapon.get("price", "0")
        price_type = chosen_weapon.get("priceType", "Gem")
        embed.add_field(name="Price", value=f"{price} {price_type}", inline=True)

        tags = chosen_weapon.get("tags", [])
        if tags and tags != ["-"]:
            embed.add_field(name="Tags", value=", ".join(str(t) for t in tags), inline=False)
        else:
            embed.add_field(name="Tags", value="None", inline=False)

        if chosen_weapon.get("recommended") == 1:
            embed.set_footer(text="⭐ Recommended Weapon")

        await interaction.response.edit_message(content="Here is your weapon info:", embed=embed, view=self)

class WeaponSelectView(discord.ui.View):
    def __init__(self, data):
        super().__init__(timeout=180)
        self.data = data

        char_options = [
            discord.SelectOption(
                label=str(group.get("folder", "")).capitalize()[:100],
                value=str(group.get("folder", ""))[:100],
            )
            for group in data if isinstance(group, dict) and "folder" in group
        ][:25]

        if not char_options:
            char_options = [discord.SelectOption(label="No characters found", value="none")]

        self.char_select = discord.ui.Select(
            placeholder="Choose a character...",
            options=char_options,
        )
        self.char_select.callback = self.char_callback
        self.add_item(self.char_select)

    async def char_callback(self, interaction: discord.Interaction):
        selected_folder = self.char_select.values[0]
        if selected_folder == "none":
            return await interaction.response.send_message("❌ No valid characters loaded.", ephemeral=True)

        char_data = next((g for g in self.data if isinstance(g, dict) and g.get("folder") == selected_folder), None)
        if not char_data or not char_data.get("weapons"):
            return await interaction.response.send_message("❌ No weapons found for this character.", ephemeral=True)

        weapon_view = WeaponDropdownView(selected_folder, char_data.get("weapons", []))
        await interaction.response.edit_message(
            content=f"Character selected: **{selected_folder.capitalize()}**. Now select a weapon:",
            view=weapon_view,
        )

class WeaponsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def weapon_character_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        choices = []
        for group in WEAPONS_DATA:
            if isinstance(group, dict) and "folder" in group:
                folder_name = str(group["folder"])
                if current.lower() in folder_name.lower():
                    choices.append(app_commands.Choice(name=folder_name.capitalize(), value=folder_name))
            if len(choices) >= 25:
                break
        return choices

    @app_commands.command(name="weapon", description="Lookup weapons by character autocomplete and drop-downs")
    @app_commands.describe(character="Character name to view weapons for")
    @app_commands.autocomplete(character=weapon_character_autocomplete)
    async def weapon(self, interaction: discord.Interaction, character: str = None):
        if not WEAPONS_DATA:
            return await interaction.response.send_message("❌ Weapon data not loaded or empty.", ephemeral=True)

        if character:
            char_data = next((g for g in WEAPONS_DATA if isinstance(g, dict) and str(g.get("folder", "")).lower() == character.lower()), None)
            if not char_data or not char_data.get("weapons"):
                return await interaction.response.send_message(f"❌ No weapon data found for character '{character}'.", ephemeral=True)

            view = WeaponDropdownView(char_data.get("folder"), char_data.get("weapons", []))
            return await interaction.response.send_message(
                f"Select a weapon for **{str(char_data.get('folder', '')).capitalize()}**:",
                view=view
            )

        view = WeaponSelectView(WEAPONS_DATA)
        await interaction.response.send_message("Select a character folder:", view=view)

async def setup(bot):
    await bot.add_cog(WeaponsCog(bot))
    