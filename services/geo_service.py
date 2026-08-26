import json
import re
from typing import Tuple, Set, List
from core.config import settings
from core.logging_config import logger

# Load country coordinates data
if settings.COUNTRY_COORDINATES_PATH.exists():
    try:
        with open(settings.COUNTRY_COORDINATES_PATH, "r", encoding="utf-8") as f:
            country_coordinates_data = json.load(f)
    except Exception as e:
        logger.warning("Failed to load country coordinates from JSON: %s", e)
        country_coordinates_data = {}
else:
    country_coordinates_data = {}

CONTINENTS_REGIONS = {
    "africa": {
        "name": "Africa",
        "coords": [7.18, 21.09],
        "countries": {"sudan", "south sudan", "nigeria", "somalia", "ethiopia", "democratic republic of the congo", "congo", "chad", "niger", "mali", "burkina faso", "mozambique", "kenya", "uganda", "libya", "cameroon", "central african republic"}
    },
    "middle east": {
        "name": "Middle East",
        "coords": [29.29, 42.55],
        "countries": {"palestine", "gaza", "israel", "yemen", "syria", "lebanon", "iraq", "iran", "jordan"}
    },
    "asia": {
        "name": "Asia",
        "coords": [34.04, 100.61],
        "countries": {"bangladesh", "myanmar", "pakistan", "afghanistan", "india", "philippines", "indonesia", "nepal", "sri lanka"}
    },
    "europe": {
        "name": "Europe",
        "coords": [54.52, 15.25],
        "countries": {"ukraine", "greece", "turkey", "poland", "romania"}
    },
    "latin america": {
        "name": "Latin America & Caribbean",
        "coords": [-8.78, -55.49],
        "countries": {"haiti", "colombia", "venezuela", "ecuador", "peru", "guatemala", "honduras", "el salvador", "cuba"}
    },
    "south america": {
        "name": "Latin America & Caribbean",
        "coords": [-8.78, -55.49],
        "countries": {"haiti", "colombia", "venezuela", "ecuador", "peru", "guatemala", "honduras", "el salvador", "cuba"}
    },
    "sahel": {
        "name": "Sahel Region",
        "coords": [14.49, 0.44],
        "countries": {"mali", "niger", "burkina faso", "chad", "sudan", "mauritania"}
    },
    "horn of africa": {
        "name": "Horn of Africa",
        "coords": [8.03, 46.19],
        "countries": {"somalia", "ethiopia", "kenya", "djibouti", "eritrea", "south sudan"}
    }
}


def detect_geo_entity(text: str = "", default_country: str = None) -> Tuple[str, str, List[float], Set[str]]:
    """
    NLP Entity & Geographic Coordinate Resolver.
    Returns (geo_type, display_name, [lat, lng], set_of_target_country_names)
    """
    if not text and default_country:
        text = default_country

    if not text:
        return ("global", "Global Crisis Region", [20.0, 0.0], set())

    text_lower = text.lower()

    # 1. Match continent / regional grouping
    for reg_key, reg_info in CONTINENTS_REGIONS.items():
        if re.search(r'\b' + re.escape(reg_key) + r'\b', text_lower):
            return ("region", reg_info["name"], reg_info["coords"], reg_info["countries"])

    # 2. Match specific country name in text
    for country, coords in country_coordinates_data.items():
        if re.search(r'\b' + re.escape(country.lower()) + r'\b', text_lower):
            return ("country", country, coords, {country.lower()})

    # 3. Match from default country if provided
    if default_country and default_country != "None":
        for entity, c_info in CONTINENTS_REGIONS.items():
            if default_country.lower() == entity:
                return ("region", c_info["name"], c_info["coords"], c_info["countries"])
        for entity, coords in country_coordinates_data.items():
            if default_country.lower() == entity.lower():
                return ("country", entity, coords, {entity.lower()})

    # 4. Fallback search
    for entity in list(CONTINENTS_REGIONS.keys()) + list(country_coordinates_data.keys()):
        if entity.lower() in text_lower:
            if entity in CONTINENTS_REGIONS:
                return ("region", CONTINENTS_REGIONS[entity]["name"], CONTINENTS_REGIONS[entity]["coords"], CONTINENTS_REGIONS[entity]["countries"])
            elif entity in country_coordinates_data:
                return ("country", entity, country_coordinates_data[entity], {entity.lower()})

    return ("global", "Global Crisis Region", [20.0, 0.0], set())


def detect_country_coords(text: str = "", default_country: str = None) -> Tuple[str, List[float]]:
    """Helper returning only (country_name, coords)"""
    _, name, coords, _ = detect_geo_entity(text, default_country)
    return (name, coords)
