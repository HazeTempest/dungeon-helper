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
    """Normalizes JSON data into a searchable list."""
    if isinstance(data, dict):
        if "data" in data and isinstance(data["data"], list):
            return data["data"]
        return list(data.values())
    elif isinstance(data, list):
        return data
    return []


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
# 1. ARTIFACT COMMAND & PAGINATED VIEW
# ==========================================
class ArtifactSelectView(discord.ui.View):
    def __init__(self, artifacts: list, page: int = 0):
        super().__init__(timeout=180)
        self.artifacts = artifacts
        self.page = page
        self.max_page = max(0, (len(artifacts) - 1) // 25)
        self.update_components()

    def update_components(self):
        self.clear_items()
        start_idx = self.page * 25
        end_idx = start_idx + 25
        page_items = self.artifacts[start_idx:end_idx]

        options = [
            discord.SelectOption(
                label=art.get("name", "Unknown Artifact")[:100],
                value=art.get("name", "Unknown Artifact")[:100],
                description=f"Tier: {art.get('tier', 'Unknown')}"[:100]
            )
            for art in page_items if isinstance(art, dict)
        ]

        if options:
            select = discord.ui.Select(
                placeholder=f"Select Artifact (Page {self.page + 1}/{self.max_page + 1})...",
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
        art = next((a for a in self.artifacts if a.get("name") == selected_name), None)

        if not art:
            return await interaction.response.send_message("❌ Artifact not found.", ephemeral=True)

        embed = discord.Embed(
            title=f"Artifact: {art.get('name')}",
            description=art.get("description", "No description available."),
            color=discord.Color.gold(),
        )
        embed.add_field(name="Tier", value=art.get("tier", "Unknown"), inline=True)

        tags = art.get("tags", [])
        tags_str = ", ".join(tags) if isinstance(tags, list) and tags else "None"
        embed.add_field(name="Tags", value=tags_str, inline=True)
        embed.add_field(name="Abilities", value=format_field_value(art.get("abilities")), inline=False)

        if art.get("unlock"):
            embed.add_field(name="Unlock Requirement", value=format_field_value(art.get("unlock")), inline=False)

        await interaction.response.edit_message(embed=embed, view=self)

    async def prev_callback(self, interaction: discord.Interaction):
        self.page -= 1
        self.update_components()
        embed = discord.Embed(
            title="Artifact Search Results",
            description=f"Found **{len(self.artifacts)}** artifact(s). Select one below:",
            color=discord.Color.gold()
        )
        await interaction.response.edit_message(embed=embed, view=self)

    async def next_callback(self, interaction: discord.Interaction):
        self.page += 1
        self.update_components()
        embed = discord.Embed(
            title="Artifact Search Results",
            description=f"Found **{len(self.artifacts)}** artifact(s). Select one below:",
            color=discord.Color.gold()
        )
        await interaction.response.edit_message(embed=embed, view=self)


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
@bot.tree.command(name="artifact", description="Search or filter artifacts with multi-page dropdowns")
@app_commands.describe(
    query="Artifact name or keyword",
    tier="Filter by artifact tier",
    tag="Filter by item or combat tag",
)
async def artifact(
    interaction: discord.Interaction,
    query: str = None,
    tier: str = None,
    tag: str = None,
):
    results = []
    for art in ARTIFACTS_DATA:
        if not isinstance(art, dict):
            continue

        match_query = (
            not query
            or query.lower() in art.get("name", "").lower()
            or query.lower() in art.get("description", "").lower()
        )
        match_tier = not tier or tier.lower() == art.get("tier", "").strip().lower()
        match_tag = not tag or any(tag.lower() in t.lower() for t in art.get("tags", []))

        if match_query and match_tier and match_tag:
            results.append(art)

    if not results:
        return await interaction.response.send_message("No artifacts found matching your criteria.", ephemeral=True)

    view = ArtifactSelectView(results)
    embed = discord.Embed(
        title="Artifact Search Results",
        description=f"Found **{len(results)}** artifact(s). Select an artifact from the drop-down below:",
        color=discord.Color.gold()
    )
    await interaction.response.send_message(embed=embed, view=view)


# ==========================================
# 2. COLLECTION COMMAND (CLEAN MARKDOWN)
# ==========================================
def create_collection_embed(col_data: dict) -> discord.Embed:
    embed = discord.Embed(
        title=f"Collection: {col_data.get('name')}",
        description=col_data.get("description", "No description available."),
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
                label=col.get("name", "Unknown Collection")[:100],
                value=col.get("name", "Unknown Collection")[:100]
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
            cname = col.get("name", "")
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
        view = CollectionSelectView(COLLECTIONS_DATA)
        return await interaction.response.send_message("Select a collection from the dropdown:", view=view)

    key = name.lower()
    col_data = next((c for c in COLLECTIONS_DATA if isinstance(c, dict) and c.get("name", "").lower() == key), None)

    if not col_data:
        matches = [c for c in COLLECTIONS_DATA if isinstance(c, dict) and key in c.get("name", "").lower()]
        if matches:
            view = CollectionSelectView(matches)
            return await interaction.response.send_message(f"Multiple collections matched '{name}'. Select one:", view=view)
        return await interaction.response.send_message(f"Collection '{name}' not found.", ephemeral=True)

    embed = create_collection_embed(col_data)
    await interaction.response.send_message(embed=embed)


# ==========================================
# 3. CHARACTER COMMAND (PAGINATED DROPDOWN & AUTOCOMPLETE)
# ==========================================
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
                label=char.get("name", "Unknown Character")[:100],
                value=char.get("name", "Unknown Character")[:100]
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
        await interaction.response.edit_message(content="Select a character from the drop-down:", view=self)

    async def next_callback(self, interaction: discord.Interaction):
        self.page += 1
        self.update_components()
        await interaction.response.edit_message(content="Select a character from the drop-down:", view=self)


def create_character_embed(char_data: dict) -> discord.Embed:
    embed = discord.Embed(
        title=char_data.get("name", "Character"),
        description=char_data.get("notes", "No notes available."),
        color=discord.Color.blue(),
    )
    stats = char_data.get("stats", {})
    if stats:
        embed.add_field(name="Stats", value=format_field_value(stats), inline=False)

    perks = char_data.get("levelperks", char_data.get("perks", {}))
    if perks:
        embed.add_field(name="Level Perks", value=format_field_value(perks), inline=False)
    return embed


async def character_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    choices = []
    for char in CHARACTERS_DATA:
        if isinstance(char, dict):
            cname = char.get("name", "")
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
        view = CharacterSelectView(CHARACTERS_DATA)
        return await interaction.response.send_message("Select a character from the drop-down:", view=view)

    key = name.lower()
    char_data = next((c for c in CHARACTERS_DATA if isinstance(c, dict) and c.get("name", "").lower() == key), None)

    if not char_data:
        matches = [c for c in CHARACTERS_DATA if isinstance(c, dict) and key in c.get("name", "").lower()]
        if matches:
            view = CharacterSelectView(matches)
            return await interaction.response.send_message(f"Multiple characters matched '{name}'. Select one:", view=view)
        return await interaction.response.send_message(f"Character '{name}' not found.", ephemeral=True)

    embed = create_character_embed(char_data)
    await interaction.response.send_message(embed=embed)


# ==========================================
# 4. SKILL COMMAND & FILTERED SELECTION
# ==========================================
class SkillSelectView(discord.ui.View):
    def __init__(self, skills: list, page: int = 0):
        super().__init__(timeout=180)
        self.skills = skills
        self.page = page
        self.max_page = max(0, (len(skills) - 1) // 25)
        self.update_components()

    def update_components(self):
        self.clear_items()
        start_idx = self.page * 25
        end_idx = start_idx + 25
        page_items = self.skills[start_idx:end_idx]

        options = [
            discord.SelectOption(
                label=sk.get("name", "Unknown Skill")[:100],
                value=sk.get("name", "Unknown Skill")[:100],
                description=f"Type: {sk.get('type', 'Skill').capitalize()}"[:100]
            )
            for sk in page_items if isinstance(sk, dict)
        ]

        if options:
            select = discord.ui.Select(
                placeholder=f"Select Skill (Page {self.page + 1}/{self.max_page + 1})...",
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
        sk = next((s for s in self.skills if s.get("name") == selected_name), None)

        if not sk:
            return await interaction.response.send_message("❌ Skill not found.", ephemeral=True)

        embed = discord.Embed(
            title=f"Skill: {sk.get('name')} [{sk.get('type', 'Skill').capitalize()}]",
            description=sk.get("description", "No description available."),
            color=discord.Color.green(),
        )
        embed.add_field(name="Stat / Scaling", value=sk.get("stat", "N/A"), inline=True)

        if sk.get("interval"):
            embed.add_field(name="Interval / Cooldown", value=sk.get("interval"), inline=True)

        tags = sk.get("tags", [])
        tags_str = ", ".join(tags) if isinstance(tags, list) and tags else "None"
        embed.add_field(name="Tags", value=tags_str, inline=False)

        if sk.get("modifications"):
            embed.add_field(name="Modifications", value=format_field_value(sk.get("modifications")), inline=False)

        await interaction.response.edit_message(embed=embed, view=self)

    async def prev_callback(self, interaction: discord.Interaction):
        self.page -= 1
        self.update_components()
        embed = discord.Embed(
            title="Skill Search Results",
            description=f"Found **{len(self.skills)}** matching skill(s). Select one below:",
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=self)

    async def next_callback(self, interaction: discord.Interaction):
        self.page += 1
        self.update_components()
        embed = discord.Embed(
            title="Skill Search Results",
            description=f"Found **{len(self.skills)}** matching skill(s). Select one below:",
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=self)


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
@bot.tree.command(name="skill", description="Search and filter skills by type, tags, or keyword")
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
    results = []
    for sk in SKILLS_DATA:
        if not isinstance(sk, dict):
            continue

        match_query = (
            not query
            or query.lower() in sk.get("name", "").lower()
            or query.lower() in sk.get("description", "").lower()
        )
        match_type = (
            not skill_type
            or skill_type.lower() == sk.get("type", "").strip().lower()
        )
        match_tag = not tag or any(tag.lower() in t.lower() for t in sk.get("tags", []))

        if match_query and match_type and match_tag:
            results.append(sk)

    if not results:
        return await interaction.response.send_message("No skills found matching your criteria.", ephemeral=True)

    view = SkillSelectView(results)
    embed = discord.Embed(
        title="Skill Search Results",
        description=f"Found **{len(results)}** matching skill(s). Select a skill from the drop-down below:",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, view=view)


# ==========================================
# 5. WEAPON COMMAND (AUTOCOMPLETE & DROPDOWNS)
# ==========================================
class WeaponDropdownView(discord.ui.View):
    def __init__(self, char_folder: str, weapons: list):
        super().__init__(timeout=180)
        self.char_folder = char_folder
        self.weapons = weapons

        options = [
            discord.SelectOption(
                label=w.get("file", "").replace(".png", "")[:100],
                value=w.get("urlName", w.get("file", ""))[:100],
                description=f"WSAP: {w.get('WSAP', 'N/A')} | Cooldown: {w.get('cooldown', 'N/A')}"[:100],
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
            (w for w in self.weapons if isinstance(w, dict) and w.get("urlName", w.get("file", "")) == selected_val),
            None
        )

        if not chosen_weapon:
            return await interaction.response.send_message("❌ Weapon details not found.", ephemeral=True)

        embed = discord.Embed(
            title=f"{chosen_weapon.get('file', '').replace('.png', '')} ({self.char_folder.capitalize()})",
            description=chosen_weapon.get("description", "No description available."),
            color=discord.Color.red(),
        )
        embed.add_field(name="WSAP", value=chosen_weapon.get("WSAP", "N/A"), inline=True)
        embed.add_field(name="Cooldown", value=chosen_weapon.get("cooldown", "N/A"), inline=True)

        price = chosen_weapon.get("price", "0")
        price_type = chosen_weapon.get("priceType", "Gem")
        embed.add_field(name="Price", value=f"{price} {price_type}", inline=True)

        tags = chosen_weapon.get("tags", [])
        if tags and tags != ["-"]:
            embed.add_field(name="Tags", value=", ".join(tags), inline=False)
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
                label=group.get("folder", "").capitalize()[:100],
                value=group.get("folder", "")[:100],
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
            folder_name = group["folder"]
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
        char_data = next((g for g in WEAPONS_DATA if isinstance(g, dict) and g.get("folder", "").lower() == character.lower()), None)
        if not char_data or not char_data.get("weapons"):
            return await interaction.response.send_message(f"❌ No weapon data found for character '{character}'.", ephemeral=True)

        view = WeaponDropdownView(char_data.get("folder"), char_data.get("weapons", []))
        return await interaction.response.send_message(
            f"Select a weapon for **{char_data.get('folder', '').capitalize()}**:",
            view=view
        )

    view = WeaponSelectView(WEAPONS_DATA)
    await interaction.response.send_message("Select a character folder:", view=view)


bot.run(DISCORD_TOKEN)