import pandas as pd
from typing import Dict, List, Any
from core.config import settings
from core.logging_config import logger

# Load verified donation links
if settings.DONATION_LINKS_PATH.exists():
    try:
        donation_links: Dict[str, str] = pd.read_csv(
            settings.DONATION_LINKS_PATH,
            encoding='latin-1',
            index_col=0
        ).to_dict()["Link"]
    except Exception as e:
        logger.warning("Failed to load donation links CSV: %s", e)
        donation_links = {}
else:
    donation_links = {}

GLOBAL_RELIEF_PARTNERS: List[Dict[str, str]] = [
    {
        "name": "Doctors Without Borders (MSF)",
        "focus": "Emergency Medical & Trauma Care",
        "url": "https://www.msf.org/donate",
        "icon": "bi-heart-pulse-fill"
    },
    {
        "name": "UN World Food Programme (WFP)",
        "focus": "Emergency Food Assistance & Nutrition",
        "url": "https://www.wfp.org/donate",
        "icon": "bi-basket2-fill"
    },
    {
        "name": "International Red Cross (ICRC)",
        "focus": "Humanitarian Corridors & Neutral Aid",
        "url": "https://www.icrc.org/en/donate",
        "icon": "bi-shield-plus"
    },
    {
        "name": "UN Refugee Agency (UNHCR)",
        "focus": "Refugee Shelter, Tents & Legal Protection",
        "url": "https://donate.unhcr.org/",
        "icon": "bi-house-heart-fill"
    }
]

HUMANITARIAN_CORRIDORS: List[Dict[str, Any]] = [
    {
        "id": 1,
        "name": "Port Sudan to Darfur Relief Lifeline",
        "region": "Sudan",
        "status": "Active Safe Passage",
        "status_type": "active",
        "managed_by": "UN OCHA & WFP",
        "focus": "Food Rations & Medical Triage",
        "coordinates": [[19.6158, 37.2164], [15.5007, 32.5599], [13.6294, 25.3549]]
    },
    {
        "id": 2,
        "name": "Rafah Border Humanitarian Crossing",
        "region": "Gaza / Palestine",
        "status": "High Friction / Priority Aid",
        "status_type": "warning",
        "managed_by": "UNRWA & Red Crescent",
        "focus": "Emergency Trauma Supplies & Fuel",
        "coordinates": [[31.2858, 34.2483], [31.5017, 34.4668]]
    },
    {
        "id": 3,
        "name": "Polish Border Hub to Western Ukraine",
        "region": "Ukraine",
        "status": "Continuous Logistics Pipeline",
        "status_type": "active",
        "managed_by": "UNHCR & European Civil Protection",
        "focus": "Power Generators, Winter Gear & Trauma Kits",
        "coordinates": [[50.0412, 21.9991], [49.8397, 24.0297], [50.4501, 30.5234]]
    },
    {
        "id": 4,
        "name": "Goma - North Kivu Humanitarian Axis",
        "region": "DR Congo",
        "status": "Severe Access Constraint",
        "status_type": "critical",
        "managed_by": "Monusco & MSF",
        "focus": "Cholera Response & Emergency Tarpaulins",
        "coordinates": [[-1.6792, 29.2228], [-1.2833, 29.5000]]
    },
    {
        "id": 5,
        "name": "Aden to Taiz Safe Supply Corridor",
        "region": "Yemen",
        "status": "Monitored De-escalation Route",
        "status_type": "warning",
        "managed_by": "ICRC & WFP",
        "focus": "Clean Water Logistics & Child Nutrition",
        "coordinates": [[12.7855, 45.0187], [13.5795, 44.0209]]
    },
    {
        "id": 6,
        "name": "Cox's Bazar Refugee Support Line",
        "region": "Bangladesh",
        "status": "Operational Monsoonal Response",
        "status_type": "active",
        "managed_by": "IOM & Red Crescent",
        "focus": "Camp Fortification, Water & Sanitation",
        "coordinates": [[21.4272, 92.0058], [21.1969, 92.1583]]
    },
    {
        "id": 7,
        "name": "Port-au-Prince Metropolitan Aid Access",
        "region": "Haiti",
        "status": "Extreme Volatility & Escorted Convoys",
        "status_type": "critical",
        "managed_by": "UN Integrated Office & PAHO",
        "focus": "Emergency Surgery & Potable Water",
        "coordinates": [[18.5944, -72.3074], [18.5392, -72.3364]]
    }
]


async def get_donation_link(news: str = "", country: str = None) -> str:
    """Retrieves verified frontline donation URL matching country or news context."""
    if country and country != "None" and country in donation_links:
        return donation_links[country]

    for c, link in donation_links.items():
        if c.lower() in (news or "").lower():
            return link

    return "https://www.redcross.org/donate/donation.html/"
