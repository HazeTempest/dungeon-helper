import json
import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Initialize bot with default intents
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


# ==========================================
# HELPER FUNCTIONS & FORMATTERS
# ==========================================
def load_json(filename):
    """Safely loads local JSON files."""
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def extract_list(data):
    """Robustly normalizes nested JSON structures and injects tier keys from parent categories."""
    cleaned = []
    
    def parse_recursive(node, current_tier=None):
        if isinstance(node, list):
            for item in node:
                parse_recursive(item, current_tier)
        elif isinstance(node, dict):
            # Check if this level represents a tier category (like boss, lesser, greater, etc.)
            for key, val in node.items():
                if isinstance(val, (list, dict)) and key.lower() in ["boss", "cursed", "lesser", "greater", "regular", "superior"]:
                    parse_recursive(val, current_tier=key)
                elif key == "list" and isinstance(val, list):
                    parse_recursive(val, current_tier=current_tier)
            
            # If this dictionary looks like an item
            if any(k in node for k in ["file", "urlName", "description", "abilities"]):
                # Assign tier if found from parent structure
                if current_tier and not node.get("tier"):
                    node["tier"] = current_tier
                
                # Determine a proper name if 'name' is missing
                if not node.get("name"):
                    if node.get("file"):
                        node["name"] = str(node["file"]).replace(".png", "")
                    elif node.get("urlName"):
                        node["name"] = str(node["urlName"]).replace("-", " ").title()
                    else:
                        node["name"] = "Unknown Item"
                cleaned.append(node)
            else:
                # Traverse other values if they aren't already handled
                for k, val in node.items():
                    if k.lower() not in ["boss", "cursed", "lesser", "greater", "regular", "superior", "list"]:
                        if isinstance(val, (dict, list)):
                            parse_recursive(val, current_tier=current_tier)

    parse_recursive(data)
    return cleaned


def clean_item_text(text: str) -> str:
    """Strips internal prefix tags like 'a:', 'c:', 'w:' from data strings."""
    text = str(text).strip()
    if text.startswith(("a:", "c:", "w:", "s:")):
        return text[2:]
    return text


def format_field_value(val) -> str:
    """Formats lists, dicts, or strings into clean Discord markdown bullet points."""
    if not val:
        return "None specified"

    if isinstance(val, list):
        if not val:
            return "None specified"
        cleaned_items = [clean_item_text(item) for item in val if item]
        return "\n".join(f"• {item}" for item in cleaned_items) if cleaned_items else "None specified"

    if isinstance(val, dict):
        return "\n".join(f"**{k}:** {v}" for k, v in val.items()) if val else "None specified"

    if isinstance(val, str):
        cleaned = clean_item_text(val)
        return cleaned if cleaned else "None specified"

    return str(val)


# Load local JSON datasets
CHARACTERS_DATA = extract_list(load_json("ds_wiki_npoint_character.json"))
ARTIFACTS_DATA = extract_list(load_json("ds_wiki_npoint_artifacts.json"))
COLLECTIONS_DATA = extract_list(load_json("ds_wiki_npoint_collections.json"))
SKILLS_DATA = extract_list(load_json("ds_wiki_npoint_skills.json"))
WEAPONS_DATA = extract_list(load_json("ds_wiki_npoint_weapons.json"))


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")


# ==========================================
# 1. ARTIFACT COMMAND (MULTI-PAGE LIST)
# ==========================================
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

        # Switch to filtered view
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

        # Row 1: Filter button, reset button, or pagination controls
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

        # Add a button to return to the specific filtered or unfiltered list view
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
@bot.tree.command(name="artifact", description="Browse all artifacts or filter by tier and tags")
@app_commands.describe(
    query="Artifact name or keyword search",
    tier="Filter by artifact tier",
    tag="Filter by item or combat tag",
)
async def artifact(
    interaction: discord.Interaction,
    query: str = None,
    tier: str = None,
    tag: str = None,
):
    # If no parameters are provided at all, return the full master list directly
    if not query and not tier and not tag:
        if not ARTIFACTS_DATA:
            return await interaction.response.send_message("❌ No artifact data loaded or available.", ephemeral=True)
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
        match_tier = not tier or tier.lower() == str(art.get("tier", "")).strip().lower()
        match_tag = not tag or any(tag.lower() in str(t).lower() for t in art.get("tags", []))

        if match_query and match_tier and match_tag:
            results.append(art)

    if not results:
        return await interaction.response.send_message("No artifacts found matching your criteria.", ephemeral=True)

    view = ArtifactSelectView(results)
    await interaction.response.send_message(embed=view.get_list_embed(), view=view)


# ==========================================
# 2. COLLECTION COMMAND
# ==========================================
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


async def collection_autocomplete(
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


@bot.tree.command(name="collection", description="View collection name, effects, and requirements")
@app_commands.describe(name="The name of the collection")
@app_commands.autocomplete(name=collection_autocomplete)
async def collection(interaction: discord.Interaction, name: str = None):
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


# ==========================================
# 3. CHARACTER COMMAND
# ==========================================
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


async def character_autocomplete(
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


@bot.tree.command(name="character", description="View character notes, stats, and level perks")
@app_commands.describe(name="The name of the character")
@app_commands.autocomplete(name=character_autocomplete)
async def character(interaction: discord.Interaction, name: str = None):
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


# ==========================================
# 4. SKILL COMMAND (MULTI-PAGE LIST)
# ==========================================
class SkillSelectView(discord.ui.View):
    def __init__(self, skills: list, page: int = 0):
        super().__init__(timeout=180)
        self.skills = skills
        self.page = page
        self.max_page = max(0, (len(skills) - 1) // 25)
        self.update_components()

    def get_list_embed(self) -> discord.Embed:
        start_idx = self.page * 25
        page_items = self.skills[start_idx:start_idx + 25]
        
        desc_lines = []
        for sk in page_items:
            name = sk.get("name", "Unknown Skill")
            stype = str(sk.get("type", "Skill")).capitalize()
            tags = sk.get("tags", [])
            tags_str = ", ".join(str(t) for t in tags) if isinstance(tags, list) and tags else "None"
            desc_lines.append(f"**{name}** - Type: {stype} | Tags: {tags_str}")

        embed = discord.Embed(
            title=f"Skills Catalog (Page {self.page + 1}/{self.max_page + 1})",
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
                description=f"Type: {str(sk.get('type', 'Skill')).capitalize()}"[:100]
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

        if self.max_page > 0:
            prev_btn = discord.ui.Button(label="◀ Prev", disabled=(self.page == 0), row=1)
            next_btn = discord.ui.Button(label="Next ▶", disabled=(self.page >= self.max_page), row=1)
            prev_btn.callback = self.prev_callback
            next_btn.callback = self.next_callback
            self.add_item(prev_btn)
            
            list_btn = discord.ui.Button(label="📋 Back to List", style=discord.ButtonStyle.secondary, row=1)
            list_btn.callback = self.list_callback
            self.add_item(list_btn)
            self.add_item(next_btn)
        else:
            list_btn = discord.ui.Button(label="📋 Back to List", style=discord.ButtonStyle.secondary, row=1)
            list_btn.callback = self.list_callback
            self.add_item(list_btn)

    async def list_callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=self.get_list_embed(), view=self)

    async def select_callback(self, interaction: discord.Interaction):
        selected_name = interaction.data["values"][0]
        sk = next((s for s in self.skills if s.get("name") == selected_name), None)

        if not sk:
            return await interaction.response.send_message("❌ Skill not found.", ephemeral=True)

        embed = discord.Embed(
            title=f"Skill: {sk.get('name')} [{str(sk.get('type', 'Skill')).capitalize()}]",
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

        await interaction.response.edit_message(embed=embed, view=self)

    async def prev_callback(self, interaction: discord.Interaction):
        self.page -= 1
        self.update_components()
        await interaction.response.edit_message(embed=self.get_list_embed(), view=self)

    async def next_callback(self, interaction: discord.Interaction):
        self.page += 1
        self.update_components()
        await interaction.response.edit_message(embed=self.get_list_embed(), view=self)


@app_commands.choices(
    skill_type=[
        app_commands.Choice(name="Subskill", value="subskill"),
        app_commands.Choice(name="Buff Skill", value="buffskill"),
        app_commands.Choice(name="Main Skill", value="mainskill"),
        app_commands.Choice(name="Curse Skill", value="curseskill"),
        app_commands.Choice(name="Summon Skill", value="summonskill"),
        app_commands.Choice(name="Enchant Skill", value="enchantskill"),
    ]
)
@bot.tree.command(name="skill", description="Browse all skills or filter by type and tags")
@app_commands.describe(
    query="Skill name or keyword search",
    skill_type="Filter by skill category",
    tag="Filter by combat tag",
)
async def skill(
    interaction: discord.Interaction,
    query: str = None,
    skill_type: str = None,
    tag: str = None,
):
    # If no parameters are provided at all, return the full master list directly
    if not query and not skill_type and not tag:
        if not SKILLS_DATA:
            return await interaction.response.send_message("❌ No skill data loaded or available.", ephemeral=True)
        view = SkillSelectView(SKILLS_DATA)
        return await interaction.response.send_message(embed=view.get_list_embed(), view=view)

    results = []
    for sk in SKILLS_DATA:
        if not isinstance(sk, dict):
            continue

        match_query = (
            not query
            or query.lower() in str(sk.get("name", "")).lower()
            or query.lower() in str(sk.get("description", "")).lower()
        )
        match_type = (
            not skill_type
            or skill_type.lower() == str(sk.get("type", "")).strip().lower()
        )
        match_tag = not tag or any(tag.lower() in str(t).lower() for t in sk.get("tags", []))

        if match_query and match_type and match_tag:
            results.append(sk)

    if not results:
        return await interaction.response.send_message("No skills found matching your criteria.", ephemeral=True)

    view = SkillSelectView(results)
    await interaction.response.send_message(embed=view.get_list_embed(), view=view)


# ==========================================
# 5. WEAPON COMMAND
# ==========================================
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


async def weapon_character_autocomplete(
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


@bot.tree.command(name="weapon", description="Lookup weapons by character autocomplete and drop-downs")
@app_commands.describe(character="Character name to view weapons for")
@app_commands.autocomplete(character=weapon_character_autocomplete)
async def weapon(interaction: discord.Interaction, character: str = None):
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


bot.run(DISCORD_TOKEN)