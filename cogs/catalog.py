import discord
from discord.ext import commands
from discord import app_commands
from data_handler import load_game_data, extract_list

class CatalogPaginator(discord.ui.View):
    def __init__(self, items, category_name):
        super().__init__(timeout=180)
        self.items = items
        self.category_name = category_name
        self.current_page = 0
        self.per_page = 5

    def create_embed(self):
        embed = discord.Embed(
            title=f"📖 Dungeon Slasher Catalog: {self.category_name.capitalize()}",
            color=discord.Color.blue()
        )
        
        start = self.current_page * self.per_page
        end = start + self.per_page
        page_items = self.items[start:end]

        if not page_items:
            embed.description = "No items found matching the criteria."
        else:
            for item in page_items:
                name = item.get("name", "Unknown Item")
                desc = item.get("description", "No description available.")
                tier = item.get("tier", "N/A")
                embed.add_field(name=f"{name} (Tier: {tier})", value=desc, inline=False)

        embed.set_footer(text=f"Page {self.current_page + 1} of {max(1, (len(self.items) + self.per_page - 1) // self.per_page)}")
        return embed

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary, disabled=True)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        max_pages = (len(self.items) + self.per_page - 1) // self.per_page
        if self.current_page < max_pages - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.create_embed(), view=self)

    def update_buttons(self):
        max_pages = max(1, (len(self.items) + self.per_page - 1) // self.per_page)
        self.children[0].disabled = (self.current_page == 0)
        self.children[1].disabled = (self.current_page >= max_pages - 1)

class CatalogCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Ensure you have your game data json loaded (e.g., 'gamedata.json')
        # self.data = load_game_data("gamedata.json")

    @app_commands.command(name="catalog", description="Search and filter game data (artifacts, skills, weapons)")
    @app_commands.describe(category="Select category (artifact, skill, weapon, character)", tier="Optional artifact tier filter")
    async def catalog(self, interaction: discord.Interaction, category: str, tier: str = None):
        # Example invocation using your extract_list function:
        # items = extract_list(self.data, category.lower(), tier)
        
        # Placeholder list for demonstration:
        items = [{"name": f"{category.capitalize()} Item {i+1}", "description": "Sample description.", "tier": tier or "Common"} for i in range(12)]
        
        if not items:
            await interaction.response.send_message(f"No items found for category **{category}** with tier **{tier}**.", ephemeral=True)
            return

        view = CatalogPaginator(items, category)
        view.update_buttons()
        await interaction.response.send_message(embed=view.create_embed(), view=view)

async def setup(bot):
    await bot.add_cog(CatalogCog(bot))