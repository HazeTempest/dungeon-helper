import discord
from discord import app_commands
from discord.ext import commands

from utils import WEAPONS_DATA 


def build_weapon_embed(character_folder: str, page_index: int):
    """Helper function to construct the embed for a given character and weapon page index."""
    char_weapons = [w for w in WEAPONS_DATA if w.get("character_folder", "").lower() == character_folder.lower()]
    if not char_weapons:
        embed = discord.Embed(
            title="No Weapons Found", 
            description=f"No weapons found for `{character_folder.capitalize()}`.", 
            color=discord.Color.red()
        )
        return embed, 0, 0
    
    page_index = max(0, min(page_index, len(char_weapons) - 1))
    matched_weapon = char_weapons[page_index]
    
    weapon_name = matched_weapon.get("name", "Unknown Weapon")
    is_recommended = matched_weapon.get("recommended") == 1
    embed_title = f"⚔️ {weapon_name} ⭐ (Recommended)" if is_recommended else f"⚔️ {weapon_name}"
    
    embed = discord.Embed(title=embed_title, color=discord.Color.blurple())
    
    wsap = matched_weapon.get("WSAP", "N/A")
    cooldown = matched_weapon.get("cooldown", "N/A")
    price = f"{matched_weapon.get('price', '0')} {matched_weapon.get('priceType', 'Gem')}"
    tags = ", ".join(matched_weapon.get("tags", [])) if matched_weapon.get("tags") else "None"
    desc = matched_weapon.get("description", "No description available.")
    
    details = (
        f"**WSAP:** {wsap}\n"
        f"**Cooldown:** {cooldown}\n"
        f"**Price:** {price}\n"
        f"**Tags:** {tags}"
    )
    embed.add_field(name="Stats & Info", value=details, inline=False)
    embed.add_field(name="Description", value=f"_{desc}_", inline=False)
    embed.set_footer(text=f"Character: {character_folder.capitalize()} | Weapon {page_index + 1} of {len(char_weapons)}")
    
    return embed, page_index, len(char_weapons)


class CharacterSelect(discord.ui.Select):
    """Dropdown menu to switch characters on the fly."""
    def __init__(self, paging_view):
        self.paging_view = paging_view
        
        characters = list(set([w.get("character_folder") for w in WEAPONS_DATA if w.get("character_folder")]))
        characters.sort()
        
        options = []
        for char in characters:
            options.append(discord.SelectOption(
                label=char.capitalize(),
                value=char.lower(),
                default=(char.lower() == paging_view.current_character)
            ))
        
        super().__init__(placeholder="Switch character...", min_values=1, max_values=1, options=options[:25])

    async def callback(self, interaction: discord.Interaction):
        self.paging_view.current_character = self.values[0]
        self.paging_view.current_page = 0  # Reset to first weapon of the new character
        
        # Update default flags on options
        for option in self.options:
            option.default = (option.value == self.paging_view.current_character)
            
        self.paging_view.update_button_states()
        embed, _, _ = build_weapon_embed(self.paging_view.current_character, self.paging_view.current_page)
        await interaction.response.edit_message(embed=embed, view=self.paging_view)


class WeaponPagingView(discord.ui.View):
    """View container holding the character dropdown and L/R pagination buttons."""
    def __init__(self, initial_character: str):
        super().__init__(timeout=180)
        self.current_character = initial_character.lower()
        self.current_page = 0
        
        # Add character select dropdown
        self.add_item(CharacterSelect(self))
        self.update_button_states()

    def update_button_states(self):
        char_weapons = [w for w in WEAPONS_DATA if w.get("character_folder", "").lower() == self.current_character]
        total = len(char_weapons)
        
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                if child.custom_id == "prev":
                    child.disabled = self.current_page <= 0
                elif child.custom_id == "next":
                    child.disabled = self.current_page >= total - 1

    @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.secondary, custom_id="prev")
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
        self.update_button_states()
        embed, _, _ = build_weapon_embed(self.current_character, self.current_page)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary, custom_id="next")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        char_weapons = [w for w in WEAPONS_DATA if w.get("character_folder", "").lower() == self.current_character]
        if self.current_page < len(char_weapons) - 1:
            self.current_page += 1
        self.update_button_states()
        embed, _, _ = build_weapon_embed(self.current_character, self.current_page)
        await interaction.response.edit_message(embed=embed, view=self)


class WeaponsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def character_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        characters = list(set([w.get("character_folder") for w in WEAPONS_DATA if w.get("character_folder")]))
        characters.sort()
        
        choices = []
        for char in characters:
            if current.lower() in char.lower():
                choices.append(app_commands.Choice(name=char.capitalize(), value=char.lower()))
            if len(choices) >= 25:
                break
        return choices

    @app_commands.command(name="weapon", description="Browse character weapons with pagination and character selection")
    @app_commands.autocomplete(character=character_autocomplete)
    async def weapon(self, interaction: discord.Interaction, character: str):
        # Validate character exists
        matched_char = next(
            (w.get("character_folder") for w in WEAPONS_DATA if w.get("character_folder", "").lower() == character.lower()),
            None
        )
        
        if not matched_char:
            all_chars = list(set([w.get("character_folder") for w in WEAPONS_DATA if w.get("character_folder")]))
            if all_chars:
                matched_char = all_chars[0]
            else:
                await interaction.response.send_message("❌ No weapon data available.", ephemeral=True)
                return

        embed, page, total = build_weapon_embed(matched_char, 0)
        if total == 0:
            await interaction.response.send_message(f"❌ No weapons found for `{matched_char.capitalize()}`.", ephemeral=True)
            return

        view = WeaponPagingView(matched_char)
        await interaction.response.send_message(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(WeaponsCog(bot))