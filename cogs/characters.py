# cogs/characters.py
import discord
from discord import app_commands
from discord.ext import commands
from utils import CHARACTERS_DATA, format_field_value

def create_character_embed(char_data: dict) -> discord.Embed:
    embed = discord.Embed(
        title=str(char_data.get("name", "Character")),
        color=discord.Color.blue(),
    )
    
    notes = char_data.get("notes")
    if notes:
        embed.description = str(notes)
        
    stats = char_data.get("stats", {})
    if stats:
        embed.add_field(name="Stats", value=format_field_value(stats), inline=False)

    perks = char_data.get("levelperks", char_data.get("perks", {}))
    if perks:
        embed.add_field(name="Level Perks", value=format_field_value(perks), inline=False)
    return embed

class CharacterSelectView(discord.ui.View):
    def __init__(self, characters: list, page: int = 0):
        super().__init__(timeout=180)
        self.characters = characters
        self.page = page
        self.max_page = max(0, (len(characters) - 1) // 25)
        self.update_components()

    def update_components(self):
        self.clear_items()
        start_idx = self.page * 25
        end_idx = start_idx + 25
        page_items = self.characters[start_idx:end_idx]

        options = [
            discord.SelectOption(
                label=str(char.get("name", "Unknown Character"))[:100],
                value=str(char.get("name", "Unknown Character"))[:100]
            )
            for char in page_items if isinstance(char, dict)
        ]

        if options:
            select = discord.ui.Select(
                placeholder=f"Select Character (Page {self.page + 1}/{self.max_page + 1})...",
                options=options
            )
            select.callback = self.select_callback
            self.add_item(select)

        if self.max_page > 0:
            prev_btn = discord.ui.Button(label="◀ Prev", disabled=(self.page == 0))
            next_btn = discord.ui.Button(label="Next ▶", disabled=(self.page >= self.max_page))
            prev_btn.callback = self.prev_callback
            next_btn.callback = self.next_callback
            self.add_item(prev_btn)
            self.add_item(next_btn)

    async def select_callback(self, interaction: discord.Interaction):
        selected_name = interaction.data["values"][0]
        char_data = next((c for c in self.characters if c.get("name") == selected_name), None)

        if not char_data:
            return await interaction.response.send_message("❌ Character not found.", ephemeral=True)

        embed = create_character_embed(char_data)
        await interaction.response.edit_message(content=None, embed=embed, view=self)

    async def prev_callback(self, interaction: discord.Interaction):
        self.page -= 1
        self.update_components()
        first_char = self.characters[self.page * 25]
        embed = create_character_embed(first_char)
        await interaction.response.edit_message(content=None, embed=embed, view=self)

    async def next_callback(self, interaction: discord.Interaction):
        self.page += 1
        self.update_components()
        first_char = self.characters[self.page * 25]
        embed = create_character_embed(first_char)
        await interaction.response.edit_message(content=None, embed=embed, view=self)

class CharactersCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def character_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        choices = []
        for char in CHARACTERS_DATA:
            if isinstance(char, dict):
                cname = str(char.get("name", ""))
                if current.lower() in cname.lower():
                    choices.append(app_commands.Choice(name=cname, value=cname))
            if len(choices) >= 25:
                break
        return choices

    @app_commands.command(name="character", description="View character notes, stats, and level perks")
    @app_commands.describe(name="The name of the character")
    @app_commands.autocomplete(name=character_autocomplete)
    async def character(self, interaction: discord.Interaction, name: str = None):
        if not name:
            if not CHARACTERS_DATA:
                return await interaction.response.send_message("❌ No character data available.", ephemeral=True)
            view = CharacterSelectView(CHARACTERS_DATA, page=0)
            embed = create_character_embed(CHARACTERS_DATA[0])
            return await interaction.response.send_message(embed=embed, view=view)

        key = name.lower()
        char_index = next((i for i, c in enumerate(CHARACTERS_DATA) if isinstance(c, dict) and str(c.get("name", "")).lower() == key), -1)

        if char_index == -1:
            matches = [c for c in CHARACTERS_DATA if isinstance(c, dict) and key in str(c.get("name", "")).lower()]
            if matches:
                view = CharacterSelectView(matches)
                embed = create_character_embed(matches[0])
                return await interaction.response.send_message(f"Multiple characters matched '{name}'. Showing first match:", embed=embed, view=view)
            return await interaction.response.send_message(f"Character '{name}' not found.", ephemeral=True)

        char_data = CHARACTERS_DATA[char_index]
        page = char_index // 25
        view = CharacterSelectView(CHARACTERS_DATA, page=page)
        embed = create_character_embed(char_data)
        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(CharactersCog(bot))