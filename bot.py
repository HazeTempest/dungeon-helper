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


# Helper function to safely load local JSON files
def load_json(filename):
  if os.path.exists(filename):
    with open(filename, "r", encoding="utf-8") as f:
      return json.load(f)
  return {}


# Load local JSON datasets
CHARACTERS_DATA = load_json("ds_wiki_npoint_character.json")
ARTIFACTS_DATA = load_json("ds_wiki_npoint_artifacts.json")
COLLECTIONS_DATA = load_json("ds_wiki_npoint_collections.json")
SKILLS_DATA = load_json("ds_wiki_npoint_skills.json")
WEAPONS_DATA = load_json("ds_wiki_npoint_weapons.json")


@bot.event
async def on_ready():
  await bot.tree.sync()
  print(f"Logged in as {bot.user} (ID: {bot.user.id})")


# ==========================================
# 1. CHARACTER COMMAND (Single Embed Layout)
# ==========================================
@bot.tree.command(
    name="character", description="View character notes, stats, and level perks"
)
@app_commands.describe(name="The name of the character")
async def character(interaction: discord.Interaction, name: str):
  key = name.lower()
  char_data = None

  # Case-insensitive search through dataset keys or name fields
  for k, v in CHARACTERS_DATA.items():
    if k.lower() == key or v.get("name", "").lower() == key:
      char_data = v
      break

  if not char_data:
    await interaction.response.send_message(
        f"Character '{name}' not found.", ephemeral=True
    )
    return

  embed = discord.Embed(
      title=char_data.get("name", name.capitalize()),
      description=char_data.get("notes", "No notes available."),
      color=discord.Color.blue(),
  )

  # Format stats field
  stats = char_data.get("stats", {})
  if stats:
    stats_str = "\n".join([f"**{k}:** {v}" for k, v in stats.items()])
    embed.add_field(name="Stats", value=stats_str, inline=False)

  # Format level perks field
  perks = char_data.get("levelperks", char_data.get("perks", {}))
  if perks:
    perks_str = "\n".join([f"**{k}:** {v}" for k, v in perks.items()])
    embed.add_field(name="Level Perks", value=perks_str, inline=False)

  await interaction.response.send_message(embed=embed)


# ==========================================
# 2. ARTIFACT COMMAND (Searchable & Filterable)
# ==========================================
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
@bot.tree.command(
    name="artifact",
    description="Search or filter artifacts by tier, tags, or name",
)
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
  for art_id, art in ARTIFACTS_DATA.items():
    match_query = (
        not query
        or query.lower() in art.get("name", "").lower()
        or query.lower() in art.get("description", "").lower()
    )
    match_tier = (
        not tier or tier.lower() == art.get("tier", "").strip().lower()
    )
    match_tag = not tag or any(
        tag.lower() in t.lower() for t in art.get("tags", [])
    )

    if match_query and match_tier and match_tag:
      results.append(art)

  if not results:
    await interaction.response.send_message(
        "No artifacts found matching your criteria.", ephemeral=True
    )
    return

  # Display the first matching artifact as an embed card
  art = results[0]
  embed = discord.Embed(
      title=f"Artifact: {art.get('name')}",
      description=art.get("description", "No description available."),
      color=discord.Color.gold(),
  )
  embed.add_field(name="Tier", value=art.get("tier", "Unknown"), inline=True)
  embed.add_field(
      name="Tags", value=", ".join(art.get("tags", [])), inline=True
  )
  embed.add_field(
      name="Abilities",
      value=art.get("abilities", "None specified"),
      inline=False,
  )

  if art.get("unlock"):
    embed.add_field(
        name="Unlock Requirement", value=art.get("unlock"), inline=False
    )

  await interaction.response.send_message(embed=embed)


# ==========================================
# 3. COLLECTION COMMAND
# ==========================================
@bot.tree.command(
    name="collection", description="View collection name, effects, and requirements"
)
@app_commands.describe(name="The name of the collection")
async def collection(interaction: discord.Interaction, name: str):
  key = name.lower()
  col_data = None

  for k, v in COLLECTIONS_DATA.items():
    if k.lower() == key or v.get("name", "").lower() == key:
      col_data = v
      break

  if not col_data:
    await interaction.response.send_message(
        f"Collection '{name}' not found.", ephemeral=True
    )
    return

  embed = discord.Embed(
      title=f"Collection: {col_data.get('name')}",
      description=col_data.get("description", "No description available."),
      color=discord.Color.purple(),
  )
  embed.add_field(
      name="Effects",
      value=col_data.get("effects", "None specified"),
      inline=False,
  )
  embed.add_field(
      name="Requirements",
      value=col_data.get("requirements", "None specified"),
      inline=False,
  )

  await interaction.response.send_message(embed=embed)


# ==========================================
# 4. SKILL COMMAND (Searchable & Filterable)
# ==========================================
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
@bot.tree.command(
    name="skill",
    description="Search and filter skills by type, tags, or name",
)
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
  for sk_id, sk in SKILLS_DATA.items():
    match_query = (
        not query
        or query.lower() in sk.get("name", "").lower()
        or query.lower() in sk.get("description", "").lower()
    )
    match_type = (
        not skill_type
        or skill_type.lower() == sk.get("type", "").strip().lower()
    )
    match_tag = not tag or any(
        tag.lower() in t.lower() for t in sk.get("tags", [])
    )

    if match_query and match_type and match_tag:
      results.append(sk)

  if not results:
    await interaction.response.send_message(
        "No skills found matching your criteria.", ephemeral=True
    )
    return

  sk = results[0]
  embed = discord.Embed(
      title=f"Skill: {sk.get('name')} [{sk.get('type', 'Skill').capitalize()}]",
      description=sk.get("description", "No description available."),
      color=discord.Color.green(),
  )
  embed.add_field(name="Stat / Scaling", value=sk.get("stat", "N/A"), inline=True)

  if sk.get("interval"):
    embed.add_field(
        name="Interval / Cooldown", value=sk.get("interval"), inline=True
    )

  embed.add_field(
      name="Tags", value=", ".join(sk.get("tags", [])), inline=False
  )

  if sk.get("modifications"):
    embed.add_field(
        name="Modifications", value=sk.get("modifications"), inline=False
    )

  await interaction.response.send_message(embed=embed)


# ==========================================
# 5. WEAPON COMMAND (Interactive Dropdowns)
# ==========================================
class WeaponSelectView(discord.ui.View):

  def __init__(self, data):
    super().__init__(timeout=180)
    self.data = data

    char_options = [
        discord.SelectOption(
            label=group.get("folder", "").capitalize(),
            value=group.get("folder", ""),
        )
        for group in data
        if "folder" in group
    ][:25]

    self.char_select = discord.ui.Select(
        placeholder="Choose a character...",
        min_values=1,
        max_values=1,
        options=char_options,
    )
    self.char_select.callback = self.char_callback
    self.add_item(self.char_select)

  async def char_callback(self, interaction: discord.Interaction):
    selected_folder = self.char_select.values[0]

    char_data = next(
        (g for g in self.data if g.get("folder") == selected_folder), None
    )
    if not char_data:
      return await interaction.response.send_message(
          "❌ Character data not found.", ephemeral=True
      )

    weapons = char_data.get("weapons", [])[:25]
    if not weapons:
      return await interaction.response.send_message(
          "❌ No weapons found for this character.", ephemeral=True
      )

    weapon_options = [
        discord.SelectOption(
            label=w.get("file", "").replace(".png", ""),
            value=w.get("urlName", w.get("file", "")),
            description=f"WSAP: {w.get('WSAP', 'N/A')} | Cooldown: {w.get('cooldown', 'N/A')}",
        )
        for w in weapons
    ]

    weapon_view = discord.ui.View(timeout=180)
    weapon_select = discord.ui.Select(
        placeholder=f"Choose a weapon for {selected_folder.capitalize()}...",
        min_values=1,
        max_values=1,
        options=weapon_options,
    )

    async def weapon_callback(w_interaction: discord.Interaction):
      selected_url_name = weapon_select.values[0]
      chosen_weapon = next(
          (
              w
              for w in weapons
              if w.get("urlName", w.get("file", "")) == selected_url_name
          ),
          None,
      )

      if not chosen_weapon:
        return await w_interaction.response.send_message(
            "❌ Weapon not found.", ephemeral=True
        )

      embed = discord.Embed(
          title=f"{chosen_weapon.get('file', '').replace('.png', '')} ({selected_folder.capitalize()})",
          description=chosen_weapon.get(
              "description", "No description available."
          ),
          color=discord.Color.red(),
      )

      embed.add_field(
          name="WSAP", value=chosen_weapon.get("WSAP", "N/A"), inline=True
      )
      embed.add_field(
          name="Cooldown",
          value=chosen_weapon.get("cooldown", "N/A"),
          inline=True,
      )

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

      await w_interaction.response.edit_message(
          content="Here is your weapon info:", embed=embed, view=None
      )

    weapon_select.callback = weapon_callback
    weapon_view.add_item(weapon_select)

    await interaction.response.edit_message(
        content=(
            f"Character selected: **{selected_folder.capitalize()}**."
            " Now select a weapon:"
        ),
        view=weapon_view,
    )


@bot.tree.command(
    name="weapon",
    description="Interactive weapon lookup by character and weapon dropdowns",
)
async def weapon(interaction: discord.Interaction):
  data = WEAPONS_DATA
  if isinstance(data, dict):
    data = list(data.values())

  if not data:
    return await interaction.response.send_message(
        "❌ Weapon data not loaded or empty.", ephemeral=True
    )

  view = WeaponSelectView(data)
  await interaction.response.send_message(
      "Select a character folder:", view=view
  )


bot.run(DISCORD_TOKEN)