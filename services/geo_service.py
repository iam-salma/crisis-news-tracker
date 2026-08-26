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

# High-Resolution City, District, Capital & Disaster Hotspots for All Global Countries
CRISIS_CITY_COORDINATES: Dict[str, Dict[str, Any]] = {
    # Sudan & East Africa
    "al-fashir": {"country": "Sudan", "display": "Al-Fashir, North Darfur", "coords": [13.6294, 25.3549]},
    "el fasher": {"country": "Sudan", "display": "Al-Fashir, North Darfur", "coords": [13.6294, 25.3549]},
    "khartoum": {"country": "Sudan", "display": "Khartoum, Sudan", "coords": [15.5007, 32.5599]},
    "port sudan": {"country": "Sudan", "display": "Port Sudan, Red Sea", "coords": [19.6158, 37.2164]},
    "darfur": {"country": "Sudan", "display": "Darfur Region, Sudan", "coords": [13.0, 24.5]},
    "omdurman": {"country": "Sudan", "display": "Omdurman, Sudan", "coords": [15.65, 32.48]},
    "kassala": {"country": "Sudan", "display": "Kassala, Sudan", "coords": [15.45, 36.40]},
    "juba": {"country": "South Sudan", "display": "Juba, South Sudan", "coords": [4.8517, 31.5825]},
    "malakal": {"country": "South Sudan", "display": "Malakal, Upper Nile", "coords": [9.5333, 31.6500]},
    "bentiu": {"country": "South Sudan", "display": "Bentiu, Unity State", "coords": [9.2333, 29.8333]},

    # Palestine & Middle East
    "rafah": {"country": "Palestine", "display": "Rafah, Southern Gaza", "coords": [31.2858, 34.2483]},
    "khan younis": {"country": "Palestine", "display": "Khan Younis, Gaza", "coords": [31.3462, 34.3063]},
    "gaza": {"country": "Palestine", "display": "Gaza City, Palestine", "coords": [31.5017, 34.4668]},
    "west bank": {"country": "Palestine", "display": "West Bank, Palestine", "coords": [31.9466, 35.3027]},
    "jenin": {"country": "Palestine", "display": "Jenin, West Bank", "coords": [32.4646, 35.2957]},
    "ramallah": {"country": "Palestine", "display": "Ramallah, West Bank", "coords": [31.9038, 35.2034]},
    "nablus": {"country": "Palestine", "display": "Nablus, West Bank", "coords": [32.2211, 35.2544]},
    "jerusalem": {"country": "Palestine", "display": "Jerusalem", "coords": [31.7683, 35.2137]},
    "tel aviv": {"country": "Israel", "display": "Tel Aviv, Israel", "coords": [32.0853, 34.7818]},
    "haifa": {"country": "Israel", "display": "Haifa, Israel", "coords": [32.7940, 34.9896]},
    "sana'a": {"country": "Yemen", "display": "Sana'a, Yemen", "coords": [15.3694, 44.1910]},
    "aden": {"country": "Yemen", "display": "Aden, Yemen", "coords": [12.7855, 45.0187]},
    "hodeidah": {"country": "Yemen", "display": "Al Hudaydah, Yemen", "coords": [14.7978, 42.9545]},
    "taiz": {"country": "Yemen", "display": "Taiz, Yemen", "coords": [13.5795, 44.0209]},
    "marib": {"country": "Yemen", "display": "Marib, Yemen", "coords": [15.4600, 45.3200]},
    "beirut": {"country": "Lebanon", "display": "Beirut, Lebanon", "coords": [33.8938, 35.5018]},
    "southern lebanon": {"country": "Lebanon", "display": "Southern Lebanon", "coords": [33.2721, 35.2033]},
    "damascus": {"country": "Syria", "display": "Damascus, Syria", "coords": [33.5138, 36.2765]},
    "aleppo": {"country": "Syria", "display": "Aleppo, Syria", "coords": [36.2021, 37.1343]},
    "idlib": {"country": "Syria", "display": "Idlib, Syria", "coords": [35.9306, 36.6339]},
    "homs": {"country": "Syria", "display": "Homs, Syria", "coords": [34.7324, 36.7137]},
    "baghdad": {"country": "Iraq", "display": "Baghdad, Iraq", "coords": [33.3152, 44.3661]},
    "basra": {"country": "Iraq", "display": "Basra, Iraq", "coords": [30.5081, 47.7835]},
    "mosul": {"country": "Iraq", "display": "Mosul, Nineveh", "coords": [36.3400, 43.1300]},
    "erbil": {"country": "Iraq", "display": "Erbil, Kurdistan Region", "coords": [36.1901, 44.0091]},
    "tehran": {"country": "Iran", "display": "Tehran, Iran", "coords": [35.6892, 51.3890]},
    "isfahan": {"country": "Iran", "display": "Isfahan, Iran", "coords": [32.6546, 51.6680]},
    "riyadh": {"country": "Saudi Arabia", "display": "Riyadh, Saudi Arabia", "coords": [24.7136, 46.6753]},
    "jeddah": {"country": "Saudi Arabia", "display": "Jeddah, Saudi Arabia", "coords": [21.4858, 39.1925]},
    "amman": {"country": "Jordan", "display": "Amman, Jordan", "coords": [31.9454, 35.9284]},
    "doha": {"country": "Qatar", "display": "Doha, Qatar", "coords": [25.2854, 51.5310]},
    "dubai": {"country": "United Arab Emirates", "display": "Dubai, UAE", "coords": [25.2048, 55.2708]},
    "abu dhabi": {"country": "United Arab Emirates", "display": "Abu Dhabi, UAE", "coords": [24.4539, 54.3773]},
    "muscat": {"country": "Oman", "display": "Muscat, Oman", "coords": [23.5880, 58.3829]},
    "kuwait city": {"country": "Kuwait", "display": "Kuwait City, Kuwait", "coords": [29.3759, 47.9774]},

    # Ukraine & Europe
    "kyiv": {"country": "Ukraine", "display": "Kyiv, Ukraine", "coords": [50.4501, 30.5234]},
    "kharkiv": {"country": "Ukraine", "display": "Kharkiv, Ukraine", "coords": [49.9935, 36.2304]},
    "zaporizhzhia": {"country": "Ukraine", "display": "Zaporizhzhia, Ukraine", "coords": [47.8388, 35.1396]},
    "odesa": {"country": "Ukraine", "display": "Odesa, Ukraine", "coords": [46.4825, 30.7233]},
    "kherson": {"country": "Ukraine", "display": "Kherson, Ukraine", "coords": [46.6354, 32.6169]},
    "lviv": {"country": "Ukraine", "display": "Lviv, Ukraine", "coords": [49.8397, 24.0297]},
    "dnipro": {"country": "Ukraine", "display": "Dnipro, Ukraine", "coords": [48.4647, 35.0462]},
    "antakya": {"country": "Turkey", "display": "Antakya, Hatay", "coords": [36.2023, 36.1613]},
    "gaziantep": {"country": "Turkey", "display": "Gaziantep, Turkey", "coords": [37.0662, 37.3833]},
    "kahramanmaras": {"country": "Turkey", "display": "Kahramanmaras, Turkey", "coords": [37.5858, 36.9371]},
    "istanbul": {"country": "Turkey", "display": "Istanbul, Turkey", "coords": [41.0082, 28.9784]},
    "ankara": {"country": "Turkey", "display": "Ankara, Turkey", "coords": [39.9334, 32.8597]},
    "izmir": {"country": "Turkey", "display": "Izmir, Turkey", "coords": [38.4237, 27.1428]},
    "athens": {"country": "Greece", "display": "Athens, Greece", "coords": [37.9838, 23.7275]},
    "london": {"country": "United Kingdom", "display": "London, United Kingdom", "coords": [51.5074, -0.1278]},
    "paris": {"country": "France", "display": "Paris, France", "coords": [48.8566, 2.3522]},
    "berlin": {"country": "Germany", "display": "Berlin, Germany", "coords": [52.5200, 13.4050]},
    "rome": {"country": "Italy", "display": "Rome, Italy", "coords": [41.9028, 12.4964]},
    "madrid": {"country": "Spain", "display": "Madrid, Spain", "coords": [40.4168, -3.7038]},
    "valencia": {"country": "Spain", "display": "Valencia Flood Zone, Spain", "coords": [39.4699, -0.3763]},
    "lisbon": {"country": "Portugal", "display": "Lisbon, Portugal", "coords": [38.7223, -9.1393]},
    "warsaw": {"country": "Poland", "display": "Warsaw, Poland", "coords": [52.2297, 21.0122]},
    "bucharest": {"country": "Romania", "display": "Bucharest, Romania", "coords": [44.4268, 26.1025]},
    "vienna": {"country": "Austria", "display": "Vienna, Austria", "coords": [48.2082, 16.3738]},
    "moscow": {"country": "Russia", "display": "Moscow, Russia", "coords": [55.7558, 37.6173]},
    "kursk": {"country": "Russia", "display": "Kursk Region, Russia", "coords": [51.7304, 36.1927]},
    "belgorod": {"country": "Russia", "display": "Belgorod Region, Russia", "coords": [50.5956, 36.5873]},

    # South Asia (India, Pakistan, Bangladesh, etc.)
    "new delhi": {"country": "India", "display": "New Delhi, India", "coords": [28.6139, 77.2090]},
    "delhi": {"country": "India", "display": "Delhi, India", "coords": [28.6139, 77.2090]},
    "mumbai": {"country": "India", "display": "Mumbai, Maharashtra", "coords": [19.0760, 72.8777]},
    "kerala": {"country": "India", "display": "Kerala, India", "coords": [10.8505, 76.2711]},
    "wayanad": {"country": "India", "display": "Wayanad, Kerala", "coords": [11.6854, 76.1320]},
    "assam": {"country": "India", "display": "Assam Flood Corridor", "coords": [26.2006, 92.9376]},
    "uttarakhand": {"country": "India", "display": "Uttarakhand, Himalayas", "coords": [30.0668, 79.0193]},
    "himachal": {"country": "India", "display": "Himachal Pradesh, India", "coords": [31.1048, 77.1734]},
    "odisha": {"country": "India", "display": "Odisha Coastal Zone", "coords": [20.9517, 85.0985]},
    "bihar": {"country": "India", "display": "Bihar Flood Basin", "coords": [25.0961, 85.3131]},
    "manipur": {"country": "India", "display": "Manipur, India", "coords": [24.6637, 93.9063]},
    "chennai": {"country": "India", "display": "Chennai, Tamil Nadu", "coords": [13.0827, 80.2707]},
    "kolkata": {"country": "India", "display": "Kolkata, West Bengal", "coords": [22.5726, 88.3639]},
    "bengaluru": {"country": "India", "display": "Bengaluru, Karnataka", "coords": [12.9716, 77.5946]},
    "hyderabad": {"country": "India", "display": "Hyderabad, Telangana", "coords": [17.3850, 78.4867]},
    "islamabad": {"country": "Pakistan", "display": "Islamabad, Pakistan", "coords": [33.6844, 73.0479]},
    "karachi": {"country": "Pakistan", "display": "Karachi, Sindh", "coords": [24.8607, 67.0011]},
    "lahore": {"country": "Pakistan", "display": "Lahore, Punjab", "coords": [31.5204, 74.3587]},
    "peshawar": {"country": "Pakistan", "display": "Peshawar, Khyber Pakhtunkhwa", "coords": [34.0151, 71.5249]},
    "quetta": {"country": "Pakistan", "display": "Quetta, Balochistan", "coords": [30.1798, 66.9750]},
    "balochistan": {"country": "Pakistan", "display": "Balochistan, Pakistan", "coords": [28.4907, 65.0958]},
    "dhaka": {"country": "Bangladesh", "display": "Dhaka, Bangladesh", "coords": [23.8103, 90.4125]},
    "chittagong": {"country": "Bangladesh", "display": "Chittagong, Bangladesh", "coords": [22.3569, 91.7832]},
    "sylhet": {"country": "Bangladesh", "display": "Sylhet Flood Basin", "coords": [24.8949, 91.8687]},
    "cox's bazar": {"country": "Bangladesh", "display": "Cox's Bazar, Bangladesh", "coords": [21.4272, 92.0058]},
    "kabul": {"country": "Afghanistan", "display": "Kabul, Afghanistan", "coords": [34.5553, 69.2075]},
    "herat": {"country": "Afghanistan", "display": "Herat Earthquake Zone", "coords": [34.3529, 62.2040]},
    "kandahar": {"country": "Afghanistan", "display": "Kandahar, Afghanistan", "coords": [31.6289, 65.7372]},
    "kathmandu": {"country": "Nepal", "display": "Kathmandu, Nepal", "coords": [27.7172, 85.3240]},
    "colombo": {"country": "Sri Lanka", "display": "Colombo, Sri Lanka", "coords": [6.9271, 79.8612]},

    # East & Southeast Asia
    "tokyo": {"country": "Japan", "display": "Tokyo, Japan", "coords": [35.6762, 139.6503]},
    "noto": {"country": "Japan", "display": "Noto Peninsula, Ishikawa", "coords": [37.2500, 137.0000]},
    "ishikawa": {"country": "Japan", "display": "Ishikawa, Japan", "coords": [36.5947, 136.6256]},
    "osaka": {"country": "Japan", "display": "Osaka, Japan", "coords": [34.6937, 135.5023]},
    "beijing": {"country": "China", "display": "Beijing, China", "coords": [39.9042, 116.4074]},
    "shanghai": {"country": "China", "display": "Shanghai, China", "coords": [31.2304, 121.4737]},
    "sichuan": {"country": "China", "display": "Sichuan Basin, China", "coords": [30.6517, 104.0759]},
    "manila": {"country": "Philippines", "display": "Manila, Philippines", "coords": [14.5995, 120.9842]},
    "cebu": {"country": "Philippines", "display": "Cebu, Philippines", "coords": [10.3157, 123.8854]},
    "mindanao": {"country": "Philippines", "display": "Mindanao, Philippines", "coords": [7.8731, 125.0483]},
    "jakarta": {"country": "Indonesia", "display": "Jakarta, Indonesia", "coords": [-6.2088, 106.8456]},
    "sumatra": {"country": "Indonesia", "display": "Sumatra, Indonesia", "coords": [-0.5897, 101.3431]},
    "bali": {"country": "Indonesia", "display": "Bali, Indonesia", "coords": [-8.4095, 115.1889]},
    "yangon": {"country": "Myanmar", "display": "Yangon, Myanmar", "coords": [16.8661, 96.1951]},
    "mandalay": {"country": "Myanmar", "display": "Mandalay, Myanmar", "coords": [21.9588, 96.0891]},
    "rakhine": {"country": "Myanmar", "display": "Rakhine State, Myanmar", "coords": [20.1041, 93.5813]},
    "bangkok": {"country": "Thailand", "display": "Bangkok, Thailand", "coords": [13.7563, 100.5018]},
    "hanoi": {"country": "Vietnam", "display": "Hanoi, Vietnam", "coords": [21.0285, 105.8542]},
    "seoul": {"country": "South Korea", "display": "Seoul, South Korea", "coords": [37.5665, 126.9780]},
    "taipei": {"country": "Taiwan", "display": "Taipei, Taiwan", "coords": [25.0330, 121.5654]},
    "hualien": {"country": "Taiwan", "display": "Hualien Earthquake Zone", "coords": [23.9872, 121.6016]},

    # Africa Hotspots
    "goma": {"country": "Democratic Republic of the Congo", "display": "Goma, North Kivu", "coords": [-1.6792, 29.2228]},
    "north kivu": {"country": "Democratic Republic of the Congo", "display": "North Kivu, DR Congo", "coords": [-0.5, 29.0]},
    "bukavu": {"country": "Democratic Republic of the Congo", "display": "Bukavu, South Kivu", "coords": [-2.5083, 28.8608]},
    "kinshasa": {"country": "Democratic Republic of the Congo", "display": "Kinshasa, DR Congo", "coords": [-4.4419, 15.2663]},
    "ituri": {"country": "Democratic Republic of the Congo", "display": "Ituri Province, DR Congo", "coords": [1.56, 30.25]},
    "maiduguri": {"country": "Nigeria", "display": "Maiduguri, Borno State", "coords": [11.8333, 13.1500]},
    "lagos": {"country": "Nigeria", "display": "Lagos, Nigeria", "coords": [6.5244, 3.3792]},
    "abuja": {"country": "Nigeria", "display": "Abuja, Nigeria", "coords": [9.0765, 7.3986]},
    "kano": {"country": "Nigeria", "display": "Kano, Nigeria", "coords": [12.0022, 8.5920]},
    "mogadishu": {"country": "Somalia", "display": "Mogadishu, Somalia", "coords": [2.0469, 45.3182]},
    "baidoa": {"country": "Somalia", "display": "Baidoa Drought Zone", "coords": [3.1138, 43.6500]},
    "addis ababa": {"country": "Ethiopia", "display": "Addis Ababa, Ethiopia", "coords": [9.0320, 38.7469]},
    "tigray": {"country": "Ethiopia", "display": "Tigray Region, Ethiopia", "coords": [14.0323, 38.3166]},
    "amhara": {"country": "Ethiopia", "display": "Amhara Region, Ethiopia", "coords": [11.5936, 37.3908]},
    "nairobi": {"country": "Kenya", "display": "Nairobi, Kenya", "coords": [-1.2921, 36.8219]},
    "turkana": {"country": "Kenya", "display": "Turkana Drought Zone", "coords": [3.1167, 35.6000]},
    "kampala": {"country": "Uganda", "display": "Kampala, Uganda", "coords": [0.3476, 32.5825]},
    "maputo": {"country": "Mozambique", "display": "Maputo, Mozambique", "coords": [-25.9692, 32.5732]},
    "cabo delgado": {"country": "Mozambique", "display": "Cabo Delgado, Mozambique", "coords": [-12.3333, 39.3333]},
    "beira": {"country": "Mozambique", "display": "Beira Cyclone Corridor", "coords": [-19.8436, 34.8389]},
    "cairo": {"country": "Egypt", "display": "Cairo, Egypt", "coords": [30.0444, 31.2357]},
    "derna": {"country": "Libya", "display": "Derna Flood Zone, Libya", "coords": [32.7667, 22.6367]},
    "tripoli": {"country": "Libya", "display": "Tripoli, Libya", "coords": [32.8872, 13.1913]},
    "marrakesh": {"country": "Morocco", "display": "Al Haouz / Marrakesh", "coords": [31.6295, -7.9811]},
    "rabat": {"country": "Morocco", "display": "Rabat, Morocco", "coords": [34.0209, -6.8416]},
    "bamako": {"country": "Mali", "display": "Bamako, Mali", "coords": [12.6392, -8.0029]},
    "niamey": {"country": "Niger", "display": "Niamey, Niger", "coords": [13.5116, 2.1254]},
    "ouagadougou": {"country": "Burkina Faso", "display": "Ouagadougou, Burkina Faso", "coords": [12.3714, -1.5197]},
    "ndjamena": {"country": "Chad", "display": "N'Djamena, Chad", "coords": [12.1348, 15.0557]},
    "bangui": {"country": "Central African Republic", "display": "Bangui, CAR", "coords": [4.3947, 18.5582]},
    "johannesburg": {"country": "South Africa", "display": "Johannesburg, South Africa", "coords": [-26.2041, 28.0473]},
    "cape town": {"country": "South Africa", "display": "Cape Town, South Africa", "coords": [-33.9249, 18.4241]},
    "durban": {"country": "South Africa", "display": "Durban Flood Zone", "coords": [-29.8587, 31.0218]},

    # Americas & Caribbean
    "port-au-prince": {"country": "Haiti", "display": "Port-au-Prince, Haiti", "coords": [18.5944, -72.3074]},
    "havana": {"country": "Cuba", "display": "Havana, Cuba", "coords": [23.1136, -82.3666]},
    "santo domingo": {"country": "Dominican Republic", "display": "Santo Domingo", "coords": [18.4861, -69.9312]},
    "kingston": {"country": "Jamaica", "display": "Kingston, Jamaica", "coords": [17.9714, -76.7936]},
    "mexico city": {"country": "Mexico", "display": "Mexico City, Mexico", "coords": [19.4326, -99.1332]},
    "acapulco": {"country": "Mexico", "display": "Acapulco Hurricane Zone", "coords": [16.8531, -99.8237]},
    "guatemala city": {"country": "Guatemala", "display": "Guatemala City", "coords": [14.6349, -90.5069]},
    "tegucigalpa": {"country": "Honduras", "display": "Tegucigalpa, Honduras", "coords": [14.0723, -87.1921]},
    "san salvador": {"country": "El Salvador", "display": "San Salvador", "coords": [13.6929, -89.2182]},
    "bogota": {"country": "Colombia", "display": "Bogota, Colombia", "coords": [4.7110, -74.0721]},
    "medellin": {"country": "Colombia", "display": "Medellin, Colombia", "coords": [6.2442, -75.5812]},
    "caracas": {"country": "Venezuela", "display": "Caracas, Venezuela", "coords": [10.4806, -66.9036]},
    "quito": {"country": "Ecuador", "display": "Quito, Ecuador", "coords": [-0.1807, -78.4678]},
    "lima": {"country": "Peru", "display": "Lima, Peru", "coords": [-12.0464, -77.0428]},
    "la paz": {"country": "Bolivia", "display": "La Paz, Bolivia", "coords": [-16.5000, -68.1500]},
    "santiago": {"country": "Chile", "display": "Santiago, Chile", "coords": [-33.4489, -70.6693]},
    "buenos aires": {"country": "Argentina", "display": "Buenos Aires, Argentina", "coords": [-34.6037, -58.3816]},
    "brasilia": {"country": "Brazil", "display": "Brasilia, Brazil", "coords": [-15.8267, -47.9218]},
    "rio de janeiro": {"country": "Brazil", "display": "Rio de Janeiro, Brazil", "coords": [-22.9068, -43.1729]},
    "sao paulo": {"country": "Brazil", "display": "Sao Paulo, Brazil", "coords": [-23.5505, -46.6333]},
    "porto alegre": {"country": "Brazil", "display": "Porto Alegre / Rio Grande do Sul Flood", "coords": [-30.0346, -51.2177]},
    "washington": {"country": "United States", "display": "Washington, D.C.", "coords": [38.9072, -77.0369]},
    "new york": {"country": "United States", "display": "New York, USA", "coords": [40.7128, -74.0060]},
    "los angeles": {"country": "United States", "display": "Los Angeles, California", "coords": [34.0522, -118.2437]},
    "houston": {"country": "United States", "display": "Houston, Texas", "coords": [29.7604, -95.3698]},
    "miami": {"country": "United States", "display": "Miami Hurricane Zone, Florida", "coords": [25.7617, -80.1918]},
    "ottawa": {"country": "Canada", "display": "Ottawa, Canada", "coords": [45.4215, -75.6972]},
    "toronto": {"country": "Canada", "display": "Toronto, Canada", "coords": [43.6532, -79.3832]},

    # Oceania
    "sydney": {"country": "Australia", "display": "Sydney, Australia", "coords": [-33.8688, 151.2093]},
    "melbourne": {"country": "Australia", "display": "Melbourne, Australia", "coords": [-37.8136, 144.9631]},
    "brisbane": {"country": "Australia", "display": "Brisbane, Australia", "coords": [-27.4698, 153.0251]},
    "auckland": {"country": "New Zealand", "display": "Auckland, New Zealand", "coords": [-36.8485, 174.7633]},
    "wellington": {"country": "New Zealand", "display": "Wellington, New Zealand", "coords": [-41.2865, 174.7762]},
    "port moresby": {"country": "Papua New Guinea", "display": "Port Moresby, PNG", "coords": [-9.4438, 147.1803]},
    "suva": {"country": "Fiji", "display": "Suva, Fiji", "coords": [-18.1416, 178.4419]},
    "port vila": {"country": "Vanuatu", "display": "Port Vila, Vanuatu", "coords": [-17.7333, 168.3273]}
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


def is_valid_geo_entity(text: str) -> Tuple[bool, str, str, List[float], Set[str]]:
    """
    Validates strictly whether a given query text matches a valid Country, City, or Region.
    Returns (is_valid, geo_type, display_name, coords, target_countries)
    """
    if not text or not text.strip():
        return False, "unknown", "", [0.0, 0.0], set()
    
    geo_type, display_name, coords, target_countries = detect_geo_entity(text.strip())
    if geo_type in ("country", "city", "region"):
        return True, geo_type, display_name, coords, target_countries
    
    return False, "unknown", "", [0.0, 0.0], set()


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
