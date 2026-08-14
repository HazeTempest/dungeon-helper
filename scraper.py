import aiohttp
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from typing import Optional, Dict

@dataclass
class CharacterData:
    name: str
    category: str
    image_url: Optional[str] = None
    description: str = ""
    # Store dynamic data like stats or build items here
    extra_fields: Dict[str, str] = field(default_factory=dict)

@dataclass
class SkillData:
    name: str
    image_url: Optional[str] = None
    damage: Optional[str] = None
    activation: Optional[str] = None # Activation chance/cooldown
    description: str = "No description available."
    modifications: Optional[str] = None
    unlock_conditions: Optional[str] = None

@dataclass
class ArtifactData:
    name: str
    image_url: Optional[str] = None
    description: str = "No description available."
    unlock_conditions: Optional[str] = None


class DungeonSlasherScraper:
    def __init__(self):
        self.base_url = "https://dungeonslasher.wiki"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    async def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetches the URL and returns a parsed BeautifulSoup object."""
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    return BeautifulSoup(html, 'html.parser')
                return None

    def _resolve_image(self, img_node) -> Optional[str]:
        """Helper to safely extract and format image URLs."""
        if not img_node or 'src' not in img_node.attrs:
            return None
        url = img_node['src']
        return self.base_url + url if url.startswith('/') else url

    async def get_character(self, character: str, page_category: str) -> Optional[CharacterData]:
        url = f"{self.base_url}/player?character={character}&page={page_category}"
        soup = await self.fetch_page(url)
        if not soup: return None

        try:
            # TODO: Replace these with actual CSS selectors for the character pages
            desc_node = soup.select_one('div.content-desc')
            description = desc_node.get_text(strip=True) if desc_node else f"{page_category} information for {character.title()}."
            
            img_node = soup.select_one('img.character-img')
            image_url = self._resolve_image(img_node)

            # Example of extracting table stats if they exist
            extra_fields = {}
            for row in soup.select('table.stats tr'):
                cols = row.select('td')
                if len(cols) == 2:
                    extra_fields[cols[0].get_text(strip=True)] = cols[1].get_text(strip=True)

            return CharacterData(
                name=character.title(), 
                category=page_category, 
                image_url=image_url, 
                description=description, 
                extra_fields=extra_fields
            )
        except Exception as e:
            print(f"Error parsing Character {character} {page_category}: {e}")
            return None

    async def get_skill(self, skill: str) -> Optional[SkillData]:
        # Assuming the site uses URL parameters to load specific skills
        url = f"{self.base_url}/unlocks?page=Skills&skill={skill}"
        soup = await self.fetch_page(url)
        if not soup: return None

        try:
            # TODO: Replace with actual CSS selectors
            img_node = soup.select_one('img.skill-icon')
            image_url = self._resolve_image(img_node)

            desc_node = soup.select_one('p.skill-desc')
            dmg_node = soup.select_one('span.skill-damage')
            act_node = soup.select_one('span.skill-cooldown')
            mod_node = soup.select_one('div.skill-mods')
            unlock_node = soup.select_one('div.unlock-req')

            return SkillData(
                name=skill.title().replace("_", " "),
                image_url=image_url,
                description=desc_node.get_text(strip=True) if desc_node else "No description.",
                damage=dmg_node.get_text(strip=True) if dmg_node else None,
                activation=act_node.get_text(strip=True) if act_node else None,
                modifications=mod_node.get_text(strip=True) if mod_node else None,
                unlock_conditions=unlock_node.get_text(strip=True) if unlock_node else None
            )
        except Exception as e:
            print(f"Error parsing Skill {skill}: {e}")
            return None

    async def get_artifact(self, artifact: str) -> Optional[ArtifactData]:
        url = f"{self.base_url}/unlocks?page=Artifacts&artifact={artifact}"
        soup = await self.fetch_page(url)
        if not soup: return None

        try:
            # TODO: Replace with actual CSS selectors
            img_node = soup.select_one('img.artifact-icon')
            image_url = self._resolve_image(img_node)
            
            desc_node = soup.select_one('p.artifact-desc')
            unlock_node = soup.select_one('div.unlock-req')

            return ArtifactData(
                name=artifact.title().replace("_", " "),
                image_url=image_url,
                description=desc_node.get_text(strip=True) if desc_node else "No description.",
                unlock_conditions=unlock_node.get_text(strip=True) if unlock_node else None
            )
        except Exception as e:
            print(f"Error parsing Artifact {artifact}: {e}")
            return None