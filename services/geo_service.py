import json
import re
from typing import Tuple, Set, List, Dict, Any
from core.config import settings
from core.logging_config import logger

# Load country coordinates data
if settings.COUNTRY_COORDINATES_PATH.exists():
    try:
        with open(settings.COUNTRY_COORDINATES_PATH, "r", encoding="utf-8") as f:
            country_coordinates_data: Dict[str, List[float]] = json.load(f)
    except Exception as e:
        logger.warning("Failed to load country coordinates from JSON: %s", e)
        country_coordinates_data = {}
else:
    country_coordinates_data = {}

# High-Resolution City & District Hotspots
CRISIS_CITY_COORDINATES: Dict[str, Dict[str, Any]] = {
    "al-fashir": {"country": "Sudan", "display": "Al-Fashir, North Darfur", "coords": [13.6294, 25.3549]},
    "el fasher": {"country": "Sudan", "display": "Al-Fashir, North Darfur", "coords": [13.6294, 25.3549]},
    "khartoum": {"country": "Sudan", "display": "Khartoum, Sudan", "coords": [15.5007, 32.5599]},
    "port sudan": {"country": "Sudan", "display": "Port Sudan, Red Sea", "coords": [19.6158, 37.2164]},
    "darfur": {"country": "Sudan", "display": "Darfur Region, Sudan", "coords": [13.0, 24.5]},
    "rafah": {"country": "Palestine", "display": "Rafah, Southern Gaza", "coords": [31.2858, 34.2483]},
    "khan younis": {"country": "Palestine", "display": "Khan Younis, Gaza", "coords": [31.3462, 34.3063]},
    "gaza": {"country": "Palestine", "display": "Gaza City, Palestine", "coords": [31.5017, 34.4668]},
    "west bank": {"country": "Palestine", "display": "West Bank, Palestine", "coords": [31.9466, 35.3027]},
    "jenin": {"country": "Palestine", "display": "Jenin, West Bank", "coords": [32.4646, 35.2957]},
    "goma": {"country": "Democratic Republic of the Congo", "display": "Goma, North Kivu", "coords": [-1.6792, 29.2228]},
    "north kivu": {"country": "Democratic Republic of the Congo", "display": "North Kivu, DR Congo", "coords": [-0.5, 29.0]},
    "bukavu": {"country": "Democratic Republic of the Congo", "display": "Bukavu, South Kivu", "coords": [-2.5083, 28.8608]},
    "kyiv": {"country": "Ukraine", "display": "Kyiv, Ukraine", "coords": [50.4501, 30.5234]},
    "kharkiv": {"country": "Ukraine", "display": "Kharkiv, Ukraine", "coords": [49.9935, 36.2304]},
    "zaporizhzhia": {"country": "Ukraine", "display": "Zaporizhzhia, Ukraine", "coords": [47.8388, 35.1396]},
    "odesa": {"country": "Ukraine", "display": "Odesa, Ukraine", "coords": [46.4825, 30.7233]},
    "kherson": {"country": "Ukraine", "display": "Kherson, Ukraine", "coords": [46.6354, 32.6169]},
    "port-au-prince": {"country": "Haiti", "display": "Port-au-Prince, Haiti", "coords": [18.5944, -72.3074]},
    "cox's bazar": {"country": "Bangladesh", "display": "Cox's Bazar, Bangladesh", "coords": [21.4272, 92.0058]},
    "sana'a": {"country": "Yemen", "display": "Sana'a, Yemen", "coords": [15.3694, 44.1910]},
    "aden": {"country": "Yemen", "display": "Aden, Yemen", "coords": [12.7855, 45.0187]},
    "hodeidah": {"country": "Yemen", "display": "Al Hudaydah, Yemen", "coords": [14.7978, 42.9545]},
    "derna": {"country": "Libya", "display": "Derna, Libya", "coords": [32.7667, 22.6367]},
    "beirut": {"country": "Lebanon", "display": "Beirut, Lebanon", "coords": [33.8938, 35.5018]},
    "southern lebanon": {"country": "Lebanon", "display": "Southern Lebanon", "coords": [33.2721, 35.2033]},
    "aleppo": {"country": "Syria", "display": "Aleppo, Syria", "coords": [36.2021, 37.1343]},
    "idlib": {"country": "Syria", "display": "Idlib, Syria", "coords": [35.9306, 36.6339]},
    "maiduguri": {"country": "Nigeria", "display": "Maiduguri, Borno State", "coords": [11.8333, 13.1500]},
    "antakya": {"country": "Turkey", "display": "Antakya, Hatay", "coords": [36.2023, 36.1613]},
    "marrakesh": {"country": "Morocco", "display": "Al Haouz / Marrakesh", "coords": [31.6295, -7.9811]},
    "kerala": {"country": "India", "display": "Kerala, India", "coords": [10.8505, 76.2711]},
    "wayanad": {"country": "India", "display": "Wayanad, Kerala", "coords": [11.6854, 76.1320]},
    "assam": {"country": "India", "display": "Assam Flood Corridor", "coords": [26.2006, 92.9376]},
    "uttarakhand": {"country": "India", "display": "Uttarakhand, Himalayas", "coords": [30.0668, 79.0193]},
    "himachal": {"country": "India", "display": "Himachal Pradesh, India", "coords": [31.1048, 77.1734]},
    "odisha": {"country": "India", "display": "Odisha Coastal Zone", "coords": [20.9517, 85.0985]},
    "new delhi": {"country": "India", "display": "New Delhi, India", "coords": [28.6139, 77.2090]},
    "delhi": {"country": "India", "display": "Delhi, India", "coords": [28.6139, 77.2090]},
    "mumbai": {"country": "India", "display": "Mumbai, Maharashtra", "coords": [19.0760, 72.8777]},
    "bihar": {"country": "India", "display": "Bihar Flood Basin", "coords": [25.0961, 85.3131]},
    "manipur": {"country": "India", "display": "Manipur, India", "coords": [24.6637, 93.9063]}
}

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
    High-Resolution NLP Entity & Geographic Coordinate Resolver.
    Prioritizes city/district level tactical coordinates over country geometric centroids.
    Returns (geo_type, display_name, [lat, lng], set_of_target_country_names)
    """
    if not text and default_country:
        text = default_country

    if not text:
        return ("global", "Global Crisis Region", [20.0, 0.0], set())

    text_lower = text.lower()

    # 1. High-Resolution City / District Matching
    for city_key, city_data in CRISIS_CITY_COORDINATES.items():
        if re.search(r'\b' + re.escape(city_key) + r'\b', text_lower):
            return ("city", city_data["display"], city_data["coords"], {city_data["country"].lower()})

    # 2. Match continent / regional grouping
    for reg_key, reg_info in CONTINENTS_REGIONS.items():
        if re.search(r'\b' + re.escape(reg_key) + r'\b', text_lower):
            return ("region", reg_info["name"], reg_info["coords"], reg_info["countries"])

    # 3. Match specific country name in text
    for country, coords in country_coordinates_data.items():
        if re.search(r'\b' + re.escape(country.lower()) + r'\b', text_lower):
            return ("country", country, coords, {country.lower()})

    # 4. Match from default country if provided
    if default_country and default_country != "None":
        for entity, c_info in CONTINENTS_REGIONS.items():
            if default_country.lower() == entity:
                return ("region", c_info["name"], c_info["coords"], c_info["countries"])
        for entity, coords in country_coordinates_data.items():
            if default_country.lower() == entity.lower():
                return ("country", entity, coords, {entity.lower()})

    # 5. Fallback search
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


def get_country_keywords(country_name: str) -> Set[str]:
    """Returns set of all associated city, state, and alias keywords for a country or region."""
    if not country_name:
        return set()
    c_lower = country_name.lower().strip()
    keywords = {c_lower}
    
    # Add matching cities/districts
    for city_key, city_data in CRISIS_CITY_COORDINATES.items():
        if city_data["country"].lower() == c_lower or c_lower in city_data["country"].lower():
            keywords.add(city_key.lower())
            
    # Add matching region countries
    for reg_key, reg_info in CONTINENTS_REGIONS.items():
        if reg_key == c_lower or reg_info["name"].lower() == c_lower:
            keywords.update(reg_info["countries"])
            
    return keywords
