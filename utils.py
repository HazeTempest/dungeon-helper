# utils.py
import json
import os
import re
import discord
from discord import app_commands

def load_json(filename):
    """Safely loads local JSON files."""
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def extract_list(data):
    """Robustly normalizes all nested JSON structures (collections, characters, weapons, skills, artifacts)."""
    cleaned = []
    
    artifact_tiers = ["lesser",  "regular", "greater", "superior", "boss", "cursed"]
    all_categories = artifact_tiers + [
        "subskill", "buffskill", "mainskill", "curseskill", "summonskill", "enchantskill"
    ]
    
    # We add current_folder to keep track of the character[cite: 3]
    def parse_recursive(node, current_cat=None, current_folder=None):
        if isinstance(node, list):
            for item in node:
                parse_recursive(item, current_cat, current_folder)
        elif isinstance(node, dict):
            # Capture the folder name if it exists (e.g., "knight", "fighter")[cite: 2, 3]
            folder = node.get("folder", current_folder)

            for key, val in node.items():
                if isinstance(val, (list, dict)) and key.lower() in all_categories:
                    parse_recursive(val, current_cat=key, current_folder=folder)
                elif key == "list" and isinstance(val, list):
                    parse_recursive(val, current_cat=current_cat, current_folder=folder)
                # Explicitly parse "weapons" lists[cite: 2, 3]
                elif key == "weapons" and isinstance(val, list):
                    parse_recursive(val, current_cat=current_cat, current_folder=folder)
            
            if any(k in node for k in ["file", "urlName", "description", "abilities", "stat", "modifications"]):
                if current_cat:
                    if current_cat.lower() in artifact_tiers:
                        node["tier"] = current_cat.lower()
                    
                    if "tags" not in node or not isinstance(node["tags"], list):
                        node["tags"] = []
                    if current_cat not in node["tags"]:
                        node["tags"].append(current_cat)
                
                # Inject the tracked folder so the cog knows who the weapon belongs to[cite: 3]
                if folder:
                    node["character_folder"] = folder
                
                if not node.get("name"):
                    if node.get("file"):
                        node["name"] = str(node["file"]).replace(".png", "")
                    elif node.get("urlName"):
                        node["name"] = str(node["urlName"]).replace("-", " ").title()
                    else:
                        node["name"] = "Unknown Item"
                cleaned.append(node)
            else:
                for k, val in node.items():
                    if k.lower() not in all_categories and k.lower() not in ["list", "weapons"]:
                        if isinstance(val, (dict, list)):
                            parse_recursive(val, current_cat=current_cat, current_folder=folder)

    parse_recursive(data)
    return cleaned

def clean_item_text(text: str) -> str:
    """Strips internal prefix tags like 'a:', 'c:', 'w:' from data strings."""
    text = str(text).strip()
    if text.startswith(("a:", "c:", "w:", "s:")):
        return text[2:]
    return text

def strip_html_tags(text: str) -> str:
    """Removes all HTML-like tags (e.g., <character>, </character>) from strings."""
    if not isinstance(text, str):
        return str(text)
    # This regex matches anything starting with < and ending with >
    return re.sub(r'<[^>]+>', '', text)

def format_field_value(val) -> str:
    """Formats lists, dicts, or strings into clean Discord markdown bullet points."""
    if not val:
        return "None specified"

    if isinstance(val, list):
        if isinstance(val, list):
            if not val:
                return "None specified"
        cleaned_items = [strip_html_tags(clean_item_text(item)) for item in val if item]
        return "\n".join(f"• {item}" for item in cleaned_items) if cleaned_items else "None specified"

    if isinstance(val, dict):
        return "\n".join(f"**{strip_html_tags(str(k))}:** {strip_html_tags(str(v))}" for k, v in val.items()) if val else "None specified"

    if isinstance(val, str):
        cleaned = strip_html_tags(clean_item_text(val))
        return cleaned if cleaned else "None specified"

    return strip_html_tags(str(val))

# Load global local datasets
CHARACTERS_DATA = extract_list(load_json("ds_wiki_npoint_character.json"))
ARTIFACTS_DATA = extract_list(load_json("ds_wiki_npoint_artifacts.json"))
COLLECTIONS_DATA = extract_list(load_json("ds_wiki_npoint_collections.json"))
SKILLS_DATA = extract_list(load_json("ds_wiki_npoint_skills.json"))
WEAPONS_DATA = extract_list(load_json("ds_wiki_npoint_weapons.json"))