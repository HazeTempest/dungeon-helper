# cogs/artifacts.py
import discord
from discord import app_commands
from discord.ext import commands
from utils import ARTIFACTS_DATA, format_field_value

async def artifact_tag_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    unique_tags = set()
    for art in ARTIFACTS_DATA:
        if isinstance(art, dict):
            tags = art.get("tags", [])
            if isinstance(tags, list):
                for t in tags:
                    if t and t != "-":
                        unique_tags.add(str(t))

    filtered = [
        app_commands.Choice(name=tag, value=tag)
        for tag in sorted(unique_tags)
        if current.lower() in tag.lower()
    ]
    return filtered[:25]

class ArtifactFilterModal(discord.ui.Modal, title="Filter Artifacts Catalog"):
    query_input = discord.ui.TextInput(
        label="Name or Keyword",
        required=False,
        placeholder="e.g. Ring, Fireball",
        max_length=100
    )
    tier_input = discord.ui.TextInput(
        label="Tier (boss, cursed, lesser, greater, etc.)",
        required=False,
        placeholder="Leave blank for any",
        max_length=50
    )
    tag_input = discord.ui.TextInput(
        label="Tag",
        required=False,
        placeholder="e.g. CH01",
        max_length=50
    )

    def __init__(self, original_view):
        super().__init__()
        self.original_view = original_view

    async def on_submit(self, interaction: discord.Interaction):
        q = self.query_input.value.strip().lower()
        t = self.tier_input.value.strip().lower()
        tag = self.tag_input.value.strip().lower()

        results = []
        for art in self.original_view.all_artifacts:
            if not isinstance(art, dict):
                continue

            match_query = (
                not q
                or q in str(art.get("name", "")).lower()
                or q in str(art.get("description", "")).lower()
            )
            match_tier = not t or t == str(art.get("tier", "")).strip().lower()
            match_tag = not tag or any(tag in str(item_tag).lower() for item_tag in art.get("tags", []))

            if match_query and match_tier and match_tag:
                results.append(art)

        if not results:
            return await interaction.response.send_message("❌ No artifacts matched your filter criteria.", ephemeral=True)

        filtered_view = ArtifactSelectView(self.original_view.all_artifacts, results=results, page=0)
        await interaction.response.edit_message(embed=filtered_view.get_list_embed(), view=filtered_view)

class ArtifactSelectView(discord.ui.View):
    def __init__(self, all_artifacts: list, results: list = None, page: int = 0):
        super().__init__(timeout=180)
        self.all_artifacts = all_artifacts
        self.artifacts = results if results is not None else all_artifacts
        self.page = page
        self.max_page = max(0, (len(self.artifacts) - 1) // 25)
        self.is_filtered = results is not None
        self.update_components()

    def get_list_embed(self) -> discord.Embed:
        start_idx = self.page * 25
        page_items = self.artifacts[start_idx:start_idx + 25]
        
        desc_lines = []
        for art in page_items:
            name = art.get("name", "Unknown Item")
            tier = str(art.get("tier", "Unknown")).capitalize()
            tags = art.get("tags", [])
            tags_str = ", ".join(str(t) for t in tags) if isinstance(tags, list) and tags else "None"
            desc_lines.append(f"**{name}** - Tier: {tier} | Tags: {tags_str}")

        title_prefix = "Filtered Artifacts" if self.is_filtered else "Artifacts Catalog"
        embed = discord.Embed(
            title=f"{title_prefix} (Page {self.page + 1}/{self.max_page + 1}) - Total: {len(self.artifacts)}",
            description="\n".join(desc_lines) if desc_lines else "No artifacts found.",
            color=discord.Color.gold()
        )
        return embed

    def update_components(self):
        self.clear_items()
        start_idx = self.page * 25
        end_idx = start_idx + 25
        page_items = self.artifacts[start_idx:end_idx]

        options = [
            discord.SelectOption(
                label=str(art.get("name", "Unknown Item"))[:100],
                value=str(art.get("name", "Unknown Item"))[:100],
                description=f"Tier: {str(art.get('tier', 'Unknown')).capitalize()}"[:100]
            )
            for art in page_items if isinstance(art, dict)
        ]

        if options:
            select = discord.ui.Select(
                placeholder=f"Select Artifact to view details...",
                options=options,
                row=0
            )
            select.callback = self.select_callback
            self.add_item(select)

        filter_btn = discord.ui.Button(label="🔍 Filter", style=discord.ButtonStyle.primary, row=1)
        filter_btn.callback = self.filter_callback
        self.add_item(filter_btn)

        if self.is_filtered:
            reset_btn = discord.ui.Button(label="🔄 Reset Filter", style=discord.ButtonStyle.secondary, row=1)
            reset_btn.callback = self.reset_callback
            self.add_item(reset_btn)

        if self.max_page > 0:
            prev_btn = discord.ui.Button(label="◀ Prev", disabled=(self.page == 0), row=2)
            next_btn = discord.ui.Button(label="Next ▶", disabled=(self.page >= self.max_page), row=2)
            prev_btn.callback = self.prev_callback
            next_btn.callback = self.next_callback
            self.add_item(prev_btn)
            self.add_item(next_btn)

    async def filter_callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ArtifactFilterModal(self))

    async def reset_callback(self, interaction: discord.Interaction):
        reset_view = ArtifactSelectView(self.all_artifacts, results=None, page=0)
        await interaction.response.edit_message(embed=reset_view.get_list_embed(), view=reset_view)

    async def select_callback(self, interaction: discord.Interaction):
        selected_name = interaction.data["values"][0]
        art = next((a for a in self.artifacts if a.get("name") == selected_name), None)

        if not art:
            return await interaction.response.send_message("❌ Artifact not found.", ephemeral=True)

        embed = discord.Embed(
            title=f"Artifact: {art.get('name')}",
            description=str(art.get("description", "No description available.")),
            color=discord.Color.gold(),
        )
        embed.add_field(name="Tier", value=str(art.get("tier", "Unknown")).capitalize(), inline=True)
        
        tags = art.get("tags", [])
        tags_str = ", ".join(str(t) for t in tags) if isinstance(tags, list) and tags else "None"
        embed.add_field(name="Tags", value=tags_str, inline=True)
        embed.add_field(name="Abilities", value=format_field_value(art.get("abilities")), inline=False)

        if art.get("unlock") and art.get("unlock") != "-":
            embed.add_field(name="Unlock Requirement", value=format_field_value(art.get("unlock")), inline=False)

        view = discord.ui.View()
        back_btn = discord.ui.Button(label="📋 Back to List", style=discord.ButtonStyle.secondary)
        
        async def back_callback(inter: discord.Interaction):
            await inter.response.edit_message(embed=self.get_list_embed(), view=self)
            
        back_btn.callback = back_callback
        view.add_item(back_btn)

        await interaction.response.edit_message(embed=embed, view=view)

    async def prev_callback(self, interaction: discord.Interaction):
        self.page -= 1
        self.update_components()
        await interaction.response.edit_message(embed=self.get_list_embed(), view=self)

    async def next_callback(self, interaction: discord.Interaction):
        self.page += 1
        self.update_components()
        await interaction.response.edit_message(embed=self.get_list_embed(), view=self)

class ArtifactCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.choices(
        tier=[
            app_commands.Choice(name="Boss", value="boss"),
            app_commands.Choice(name="Cursed", value="cursed"),
            app_commands.Choice(name="Lesser", value="lesser"),
            app_commands.Choice(name="Greater", value="greater"),
            app_commands.Choice(name="Regular", value="regular"),
            app_commands.Choice(name="Superior", value="superior"),
        ]
    )
    @app_commands.command(name="artifact", description="Browse all artifacts or filter by keywords and tags")
    @app_commands.describe(
        query="Artifact name or keyword search",
        tag="Filter by artifact tag",
        tier="Filter by artifact tier",
    )
    @app_commands.autocomplete(tag=artifact_tag_autocomplete)
    async def artifact(
        self,
        interaction: discord.Interaction,
        query: str = None,
        tag: str = None,
        tier: str = None,
    ):
        if not ARTIFACTS_DATA:
            return await interaction.response.send_message("❌ No artifact data loaded or available.", ephemeral=True)

        if not query and not tag and not tier:
            view = ArtifactSelectView(ARTIFACTS_DATA)
            return await interaction.response.send_message(embed=view.get_list_embed(), view=view)

        results = []
        for art in ARTIFACTS_DATA:
            if not isinstance(art, dict):
                continue

            match_query = (
                not query
                or query.lower() in str(art.get("name", "")).lower()
                or query.lower() in str(art.get("description", "")).lower()
            )
            
            art_tags = [str(t).lower() for t in art.get("tags", []) if t and t != "-"]
            match_tag = not tag or any(tag.lower() in t for t in art_tags)
            match_tier = not tier or tier.lower() == str(art.get("tier", "")).strip().lower()

            if match_query and match_tag and match_tier:
                results.append(art)

        if not results:
            return await interaction.response.send_message("No artifacts found matching your criteria.", ephemeral=True)

        view = ArtifactSelectView(ARTIFACTS_DATA, results=results)
        await interaction.response.send_message(embed=view.get_list_embed(), view=view)

async def setup(bot):
    await bot.add_cog(ArtifactCog(bot))