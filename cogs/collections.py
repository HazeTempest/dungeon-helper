# cogs/collections.py
import discord
from discord import app_commands
from discord.ext import commands
from utils import COLLECTIONS_DATA, format_field_value

def create_collection_embed(col_data: dict) -> discord.Embed:
    embed = discord.Embed(
        title=f"Collection: {col_data.get('name')}",
        description=str(col_data.get("description", "No description available.")),
        color=discord.Color.purple(),
    )
    embed.add_field(
        name="Effects",
        value=format_field_value(col_data.get("effects")),
        inline=False,
    )
    embed.add_field(
        name="Requirements",
        value=format_field_value(col_data.get("requirements")),
        inline=False,
    )
    return embed

class CollectionSelectView(discord.ui.View):
    def __init__(self, collections: list):
        super().__init__(timeout=180)
        options = [
            discord.SelectOption(
                label=str(col.get("name", "Unknown Collection"))[:100],
                value=str(col.get("name", "Unknown Collection"))[:100]
            )
            for col in collections[:25] if isinstance(col, dict)
        ]
        select = discord.ui.Select(placeholder="Select a collection...", options=options)
        select.callback = self.select_callback
        self.add_item(select)
        self.collections = collections

    async def select_callback(self, interaction: discord.Interaction):
        selected_name = interaction.data["values"][0]
        col_data = next((c for c in self.collections if c.get("name") == selected_name), None)
        if col_data:
            embed = create_collection_embed(col_data)
            await interaction.response.edit_message(content=None, embed=embed, view=self)

class CollectionsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def collection_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        choices = []
        for col in COLLECTIONS_DATA:
            if isinstance(col, dict):
                cname = str(col.get("name", ""))
                if current.lower() in cname.lower():
                    choices.append(app_commands.Choice(name=cname, value=cname))
            if len(choices) >= 25:
                break
        return choices

    @app_commands.command(name="collection", description="View collection name, effects, and requirements")
    @app_commands.describe(name="The name of the collection")
    @app_commands.autocomplete(name=collection_autocomplete)
    async def collection(self, interaction: discord.Interaction, name: str = None):
        if not name:
            if not COLLECTIONS_DATA:
                return await interaction.response.send_message("❌ No collection data available.", ephemeral=True)
            view = CollectionSelectView(COLLECTIONS_DATA)
            return await interaction.response.send_message("Select a collection from the dropdown:", view=view)

        key = name.lower()
        col_data = next((c for c in COLLECTIONS_DATA if isinstance(c, dict) and str(c.get("name", "")).lower() == key), None)

        if not col_data:
            matches = [c for c in COLLECTIONS_DATA if isinstance(c, dict) and key in str(c.get("name", "")).lower()]
            if matches:
                view = CollectionSelectView(matches)
                return await interaction.response.send_message(f"Multiple collections matched '{name}'. Select one:", view=view)
            return await interaction.response.send_message(f"Collection '{name}' not found.", ephemeral=True)

        embed = create_collection_embed(col_data)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(CollectionsCog(bot))