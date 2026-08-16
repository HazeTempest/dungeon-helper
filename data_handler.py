import json

def load_game_data(filepath: str):
    """Loads and returns JSON game data."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def extract_list(data, category: str, tier: str = None):
    """Universal extraction helper handling nested keys, artifact tiers, etc."""
    results = []
    items = data.get(category, [])
    
    if isinstance(items, dict):
        for sub_key, sub_val in items.items():
            if isinstance(sub_val, list):
                for item in sub_val:
                    if isinstance(item, dict):
                        if category == "artifact" and tier:
                            if item.get("tier") == tier:
                                results.append(item)
                        else:
                            results.append(item)
            elif isinstance(sub_val, dict):
                if category == "artifact" and tier:
                    if sub_val.get("tier") == tier:
                        results.append(sub_val)
                else:
                    results.append(sub_val)
    elif isinstance(items, list):
        for item in items:
            if isinstance(item, dict):
                if category == "artifact" and tier:
                    if item.get("tier") == tier:
                        results.append(item)
                else:
                    results.append(item)
                    
    return results