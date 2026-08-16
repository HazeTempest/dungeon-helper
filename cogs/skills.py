# cogs/skills.py
import discord
from discord import app_commands
from discord.ext import commands
from utils import SKILLS_DATA, format_field_value

async def skill_tag_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    unique_tags = set()
    for sk in SKILLS_DATA:
        if isinstance(sk, dict):
            tags = sk.get("tags", [])
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

class SkillFilterModal(discord.ui.Modal, title="Filter Skills Catalog"):
    query_input = discord.ui.TextInput(
        label="Name or Keyword",
        required=False,
        placeholder="e.g. Slash, Fire",
        max_length=100
    )
    tag_input = discord.ui.TextInput(
        label="Tag / Type",
        required=False,
        placeholder="e.g. subskill, Combat",
        max_length=50
    )

    def __init__(self, original_view):
        super().__init__()
        self.original_view = original_view

    async def on_submit(self, interaction: discord.Interaction):
        q = self.query_input.value.strip().lower()
        tag = self.tag_input.value.strip().lower()

        results = []
        for sk in self.original_view.all_skills:
            if not isinstance(sk, dict):
                continue

            match_query = (
                not q
                or q in str(sk.get("name", "")).lower()
                or q in str(sk.get("description", "")).lower()
            )
            match_tag = not tag or any(tag in str(item_tag).lower() for item_tag in sk.get("tags", []))

            if match_query and match_tag:
                results.append(sk)

        if not results:
            return await interaction.response.send_message("❌ No skills matched your filter criteria.", ephemeral=True)

        filtered_view = SkillSelectView(self.original_view.all_skills, results=results, page=0)
        await interaction.response.edit_message(embed=filtered_view.get_list_embed(), view=filtered_view)

class SkillSelectView(discord.ui.View):
    def __init__(self, all_skills: list, results: list = None, page: int = 0):
        super().__init__(timeout=180)
        self.all_skills = all_skills
        self.skills = results if results is not None else all_skills
        self.page = page
        self.max_page = max(0, (len(self.skills) - 1) // 25)
        self.is_filtered = results is not None
        self.update_components()

    def get_list_embed(self) -> discord.Embed:
        start_idx = self.page * 25
        page_items = self.skills[start_idx:start_idx + 25]
        
        desc_lines = []
        for sk in page_items:
            name = sk.get("name", "Unknown Skill")
            tags = sk.get("tags", [])
            tags_str = ", ".join(str(t) for t in tags) if isinstance(tags, list) and tags else "None"
            desc_lines.append(f"**{name}** - Tags: {tags_str}")

        title_prefix = "Filtered Skills" if self.is_filtered else "Skills Catalog"
        embed = discord.Embed(
            title=f"{title_prefix} (Page {self.page + 1}/{self.max_page + 1}) - Total: {len(self.skills)}",
            description="\n".join(desc_lines) if desc_lines else "No skills found.",
            color=discord.Color.green()
        )
        return embed

    def update_components(self):
        self.clear_items()
        start_idx = self.page * 25
        end_idx = start_idx + 25
        page_items = self.skills[start_idx:end_idx]

        options = [
            discord.SelectOption(
                label=str(sk.get("name", "Unknown Skill"))[:100],
                value=str(sk.get("name", "Unknown Skill"))[:100],
                description=f"Tags: {', '.join(str(t) for t in sk.get('tags', []))}"[:100]
            )
            for sk in page_items if isinstance(sk, dict)
        ]

        if options:
            select = discord.ui.Select(
                placeholder=f"Select Skill to view details...",
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
            next_btn.callback = self.next_btn_callback
            self.add_item(prev_btn)
            self.add_item(next_btn)

    async def filter_callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SkillFilterModal(self))

    async def reset_callback(self, interaction: discord.Interaction):
        reset_view = SkillSelectView(self.all_skills, results=None, page=0)
        await interaction.response.edit_message(embed=reset_view.get_list_embed(), view=reset_view)

    async def select_callback(self, interaction: discord.Interaction):
        selected_name = interaction.data["values"][0]
        sk = next((s for s in self.skills if s.get("name") == selected_name), None)

        if not sk:
            return await interaction.response.send_message("❌ Skill not found.", ephemeral=True)

        embed = discord.Embed(
            title=f"Skill: {sk.get('name')}",
            description=str(sk.get("description", "No description available.")),
            color=discord.Color.green(),
        )
        embed.add_field(name="Stat / Scaling", value=str(sk.get("stat", "N/A")), inline=True)

        if sk.get("interval"):
            embed.add_field(name="Interval / Cooldown", value=str(sk.get("interval")), inline=True)

        tags = sk.get("tags", [])
        tags_str = ", ".join(str(t) for t in tags) if isinstance(tags, list) and tags else "None"
        embed.add_field(name="Tags", value=tags_str, inline=False)

        if sk.get("modifications"):
            embed.add_field(name="Modifications", value=format_field_value(sk.get("modifications")), inline=False)

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

    async def next_btn_callback(self, interaction: discord.Interaction):
        self.page += 1
        self.update_components()
        await interaction.response.edit_message(embed=self.get_list_embed(), view=self)

class SkillsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="skill", description="Browse all skills or filter by keywords and tags")
    @app_commands.describe(
        query="Skill name or keyword search",
        tag="Filter by skill tag",
    )
    @app_commands.autocomplete(tag=skill_tag_autocomplete)
    async def skill(
        self,
        interaction: discord.Interaction,
        query: str = None,
        tag: str = None,
    ):
        if not SKILLS_DATA:
            return await interaction.response.send_message("❌ No skill data loaded or available.", ephemeral=True)

        if not query and not tag:
            view = SkillSelectView(SKILLS_DATA)
            return await interaction.response.send_message(embed=view.get_list_embed(), view=view)

        results = []
        for s in SKILLS_DATA:
            if not isinstance(s, dict):
                continue

            match_query = (
                not query
                or query.lower() in str(s.get("name", "")).lower()
                or query.lower() in str(s.get("description", "")).lower()
            )
            
            s_tags = [str(t) for t in s.get("tags", [])]
            match_tag = not tag or any(tag.lower() in t.lower() for t in s_tags)

            if match_query and match_tag:
                results.append(s)

        if not results:
            return await interaction.response.send_message("No skills found matching your criteria.", ephemeral=True)

        view = SkillSelectView(SKILLS_DATA, results=results)
        await interaction.response.send_message(embed=view.get_list_embed(), view=view)

async def setup(bot):
    await bot.add_cog(SkillsCog(bot))