import re
from typing import Dict, Any, List
from llm_engine import LLMServiceFactory
from core.logging_config import logger


def clean_summary_text(text: str) -> str:
    """Strips Markdown and formatting artifacts from plain text strings."""
    if not text:
        return ""
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"^\s*[\*\-•]\s*", '', text, flags=re.MULTILINE)
    text = re.sub(r"^\s*#+\s*", '', text, flags=re.MULTILINE)
    return text.strip()


def clean_and_complete_description(title: str = "", description: str = "", country_name: str = "") -> str:
    """Cleans raw API truncation markers and repairs incomplete sentences."""
    t_clean = (title or "").rstrip(".").strip()
    d_raw = (description or "").strip()

    d_clean = re.sub(r'Read More:\s*https?://\S+', '', d_raw, flags=re.IGNORECASE)
    d_clean = re.sub(r'\[\+\d+\s*chars?\]', '', d_clean, flags=re.IGNORECASE)
    d_clean = re.sub(r'<[^>]+>', '', d_clean).strip()

    if d_clean:
        if not d_clean.endswith(('.', '!', '?')):
            last_period = max(d_clean.rfind('.'), d_clean.rfind('!'), d_clean.rfind('?'))
            if last_period > 35:
                d_clean = d_clean[:last_period + 1]
            else:
                words = d_clean.split()
                if len(words) > 3:
                    d_clean = " ".join(words[:-1]) + "."
                else:
                    d_clean = d_clean.rstrip(' ,;:-') + "."
    else:
        d_clean = f"Frontline humanitarian teams report ongoing emergency developments across {country_name or 'the affected region'}, requiring coordinated relief operations."

    return d_clean


def analyze_crisis_article(title: str = "", description: str = "", country_name: str = "") -> Dict[str, Any]:
    """Generates structured situation assessment, urgency level, takeaways, and timeline."""
    text_combined = f"{title} {description}".lower()

    if any(w in text_combined for w in ["war", "strike", "attack", "militia", "clash", "bomb", "missile", "troop", "killing", "atrocit", "hostage", "ceasefire", "military", "combat"]):
        crisis_type = "Armed Conflict & Violence"
        default_urgency = "CRITICAL"
        needs = ["Emergency Trauma Kits", "Safe Passage Corridors", "Emergency Shelter Kits", "Psychosocial Care"]
    elif any(w in text_combined for w in ["flood", "earthquake", "quake", "storm", "hurricane", "typhoon", "cyclone", "wildfire", "tsunami", "drought", "landslide"]):
        crisis_type = "Natural Disaster & Climate Shock"
        default_urgency = "CRITICAL" if any(w in text_combined for w in ["dead", "kill", "mass", "submerged", "casualt"]) else "HIGH"
        needs = ["Clean Drinking Water", "Search & Rescue Units", "Temporary Tarpaulins", "Water Purification Kits"]
    elif any(w in text_combined for w in ["famine", "hunger", "starvat", "food", "malnutrition", "crops"]):
        crisis_type = "Food Insecurity & Famine"
        default_urgency = "CRITICAL"
        needs = ["Therapeutic Food Rations", "Infant Nutrition Packs", "Clean Water Supply", "Agricultural Recovery"]
    elif any(w in text_combined for w in ["refugee", "displace", "flee", "camp", "asylum", "migration", "exodus"]):
        crisis_type = "Displacement & Refugee Emergency"
        default_urgency = "HIGH"
        needs = ["Emergency Tents & Tarpaulins", "Sanitation Facilities", "Family Hygiene Kits", "Child Protection"]
    elif any(w in text_combined for w in ["cholera", "disease", "outbreak", "epidemic", "hospital", "medical", "virus", "health"]):
        crisis_type = "Health & Medical Emergency"
        default_urgency = "HIGH"
        needs = ["Essential Medications", "Mobile Field Clinics", "Vaccines & Cold-Chain", "IV Fluids & Antibiotics"]
    else:
        crisis_type = "Humanitarian Emergency"
        default_urgency = "HIGH"
        needs = ["Emergency Financial Aid", "Essential Relief Kits", "Emergency Medical Attention", "Community Shelter"]

    if any(w in text_combined for w in ["dead", "kill", "massacre", "catastroph", "apocalyptic", "urgent", "imminent", "mass killing"]):
        urgency = "CRITICAL"
    elif any(w in text_combined for w in ["severe", "escalat", "warning", "destruct", "thousands", "critical"]):
        urgency = "HIGH"
    else:
        urgency = default_urgency

    t_clean = title.rstrip(".").strip() if title else "Humanitarian Emergency"
    d_clean = clean_and_complete_description(title=title, description=description, country_name=country_name)
    c_label = country_name or "the affected crisis region"

    # Multi-Paragraph Situation Report tailored by Domain
    if crisis_type == "Armed Conflict & Violence":
        p1 = (
            f"<strong>Operational Crisis Dynamics:</strong> Field intelligence across <strong>{c_label}</strong> highlights active security escalations "
            "and severe pressure on civilian protection zones. Hostilities have disrupted transportation networks, municipal power, "
            "and commercial supply chains, isolating vulnerable municipal sectors."
        )
        p2 = (
            f"<strong>Civilian Welfare & Hospital Capacity:</strong> Frontline medical responders in {c_label} report severe caseloads "
            "of blast injuries and acute trauma, exacerbated by severe shortages of sterile surgical packs, blood products, and anesthetics. "
            "Displaced families fleeing active combat zones are seeking refuge in improvised shelters with compromised sanitation lifelines."
        )
        p3 = (
            "<strong>Humanitarian Corridors & Logistical Access:</strong> International relief agencies and local emergency committees "
            "are actively negotiating neutralized humanitarian corridors to facilitate the delivery of emergency aid convoys. "
            "Security checkpoints and damaged transit arteries remain significant bottlenecks for frontline aid workers."
        )
    elif crisis_type == "Natural Disaster & Climate Shock":
        p1 = (
            f"<strong>Disaster Extent & Environmental Impact:</strong> Rapid geospatial assessments in <strong>{c_label}</strong> confirm widespread "
            "structural damage to residential settlements, agricultural acreage, and transit bridges following severe weather and geophysical shocks. "
            "Power grids and telecommunication networks have experienced widespread blackouts."
        )
        p2 = (
            f"<strong>Search, Rescue & Disease Surveillance:</strong> Disaster management authorities in {c_label} are deploying search and rescue teams "
            "alongside heavy earth-moving equipment. Stagnant floodwaters and damaged municipal water infrastructure have heightened "
            "the imminent risk of waterborne disease outbreaks, including cholera and acute watery diarrhea."
        )
        p3 = (
            "<strong>Emergency Supply Lines:</strong> Prepositioned disaster relief supplies—including heavy-duty tarpaulins, mobile water treatment units, "
            "and emergency trauma kits—are being mobilized from central logistics depots to frontline staging areas."
        )
    elif crisis_type == "Food Insecurity & Famine":
        p1 = (
            f"<strong>Agricultural Strains & Market Vulnerability:</strong> Comprehensive food security monitoring in <strong>{c_label}</strong> "
            "indicates acute food deficits driven by harvest failures, macroeconomic volatility, and market supply disruptions. "
            "Staple food prices have spiked significantly beyond baseline affordability thresholds."
        )
        p2 = (
            f"<strong>Nutritional Crisis & Child Vulnerability:</strong> Nutrition screening centers in {c_label} report alarming surges in Severe Acute Malnutrition (SAM) "
            "among infants, young children, and lactating mothers. Therapeutic feeding centers are operating at peak capacity, "
            "requiring immediate infusions of ready-to-use therapeutic food (RUTF) rations."
        )
        p3 = (
            "<strong>Frontline Distribution Channels:</strong> World Food Programme (WFP) convoys and frontline partners are coordinating generalized food distributions "
            "and emergency cash assistance, prioritizing rural and cut-off pastoral communities."
        )
    elif crisis_type == "Displacement & Refugee Emergency":
        p1 = (
            f"<strong>Displacement Wave & Border Strains:</strong> Escalating instability in <strong>{c_label}</strong> has triggered massive population movements, "
            "with thousands of internally displaced persons (IDPs) and cross-border refugees arriving daily at spontaneous settlement camps."
        )
        p2 = (
            f"<strong>Camp Infrastructure & Protection Risks:</strong> Overcrowded transit centers in {c_label} face acute deficits in emergency shelter, "
            "segregated sanitation blocks, and clean drinking water points. Protection monitors emphasize the heightened risks faced by unaccompanied minors, "
            "female-headed households, and persons with disabilities."
        )
        p3 = (
            "<strong>Shelter & Registration Pipeline:</strong> UNHCR and accredited NGOs are expanding biometric registration hubs, deploying all-weather family tents, "
            "and establishing dedicated psychosocial support spaces for displaced survivors."
        )
    else:
        p1 = (
            f"<strong>Situational Overview & Field Context:</strong> Humanitarian monitors across <strong>{c_label}</strong> report compounding vulnerabilities "
            "affecting essential civilian lifelines. Interrupted basic services have strained local coping capacities, "
            "demanding sustained, multi-sectoral emergency interventions."
        )
        p2 = (
            f"<strong>Public Health & Civilian Livelihoods:</strong> Vulnerable communities in {c_label} face critical gaps in primary healthcare access, "
            "potable water supplies, and essential livelihood assets. Community health networks are actively mobilizing to prevent secondary mortality."
        )
        p3 = (
            "<strong>Inter-Agency Response Coordination:</strong> Relief clusters are harmonizing logistics, distribution monitoring, and frontline needs assessments "
            "to ensure equitable aid coverage across underserved operational zones."
        )

    p4 = (
        "<strong>Strategic Priorities & Appeal:</strong> Sustaining emergency response capacity requires immediate donor commitments, "
        "unhindered bureaucratic clearances, and continuous resource flows to accredited frontline non-governmental organizations."
    )

    full_report = [p1, p2, p3, p4]

    takeaways = [
        f"<strong>Classification:</strong> {urgency} emergency status categorized under {crisis_type}.",
        f"<strong>Impacted Zone:</strong> High-density civilian clusters and transit infrastructure across {c_label}.",
        f"<strong>Critical Deficit:</strong> Urgent field requirement for {', '.join(needs[:2]).lower()} and medical triage supplies.",
        "<strong>Operational Mandate:</strong> Fast-track humanitarian corridor clearances and deploy emergency distribution reserves."
    ]

    timeline = [
        {
            "phase": "Catalyst & Regional Context",
            "detail": f"Underlying vulnerabilities and compounding shocks have triggered heightened humanitarian strain across {c_label}."
        },
        {
            "phase": "Active Emergency Phase",
            "detail": f"Civilian infrastructure and community services have sustained disruption, requiring immediate emergency mobilization."
        },
        {
            "phase": "Frontline Response",
            "detail": "Emergency responders, accredited international agencies, and local humanitarian clusters are deploying active relief pipelines."
        }
    ]

    return {
        "crisis_type": crisis_type,
        "urgency": urgency,
        "immediate_needs": needs,
        "cleaned_description": d_clean,
        "full_report": full_report,
        "takeaways": takeaways,
        "timeline": timeline
    }


async def generate_content(title: str = "", description: str = "") -> str:
    """Generates structured executive takeaways using the local in-memory LLM."""
    prompt = (
        f"Write a detailed, factual and structured humanitarian report based on this development:\n"
        f"Title: {title}\nDescription: {description}\n"
        "Provide 3-5 structured bullet points detailing context, civilian impact, and relief operations."
    )
    system_prompt = "You are CrisisAid AI, an expert humanitarian crisis analyst."

    try:
        report_text, _ = await LLMServiceFactory.generate_with_fallback(prompt, system_prompt)
        if report_text and len(report_text) > 30:
            return clean_summary_text(report_text)
    except Exception as e:
        logger.warning("[Local LLM] Content generation fallback: %s", e)

    t = title.rstrip(".").strip() if title else "Humanitarian Crisis Development"
    d = description.strip() if description else "Emergency response teams are monitoring relief efforts on the ground."
    points = [
        f"<strong>Key Development:</strong> {t}.",
        f"<strong>Situational Overview:</strong> {d}",
        "<strong>Humanitarian Impact:</strong> Impacted populations face urgent shortages of critical supplies, food, and clean water.",
        "<strong>Frontline Logistics:</strong> Emergency response networks are coordinating supply lines and distribution hubs.",
        "<strong>Verified Action:</strong> Immediate assistance channels are active for humanitarian relief."
    ]
    return "\n".join(points)
