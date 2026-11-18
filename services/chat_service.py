import re
from typing import Optional, List
from sqlalchemy.orm import Session
from models import NewsArticle
from services.geo_service import detect_geo_entity, detect_country_coords
from services.relief_service import donation_links
from core.logging_config import logger

CHAT_STOP_WORDS = {
    'what', 'when', 'where', 'which', 'who', 'whom', 'this', 'that', 'these', 'those',
    'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
    'do', 'does', 'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or', 'because',
    'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between',
    'into', 'through', 'during', 'before', 'after', 'above', 'below', 'to', 'from',
    'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further', 'then',
    'once', 'here', 'there', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other',
    'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
    'can', 'will', 'just', 'should', 'now', 'news', 'update', 'updates', 'latest', 'today',
    'tell', 'give', 'show', 'happening', 'going', 'please', 'crisis', 'crises'
}


def get_rag_context_for_query(query: str, db: Optional[Session] = None, max_articles: int = 5) -> str:
    """
    Retrieves and ranks live database articles matching query keywords/geography,
    formatting them as real-time RAG context for neural LLMs (e.g. Qwen).
    """
    if not db:
        return ""
    try:
        geo_type, geo_name, _, geo_target_countries = detect_geo_entity(query)
        all_articles = db.query(NewsArticle).all()
        words = [re.sub(r'[^a-z0-9]', '', w) for w in query.lower().split()]
        keywords = [w for w in words if len(w) >= 3 and w not in CHAT_STOP_WORDS]

        scored = []
        for art in all_articles:
            title_l = (art.title or "").lower()
            desc_l = (art.description or "").lower()
            art_text = f"{title_l} {desc_l}"
            art_geo_type, art_c_name, _, _ = detect_geo_entity(art_text)
            score = 0

            if geo_type == "country" and geo_name:
                if art_c_name.lower() == geo_name.lower():
                    score += 30
                elif geo_name.lower() in title_l:
                    score += 20
                elif geo_name.lower() in desc_l:
                    score += 10
            elif geo_type == "region":
                if art_c_name.lower() in geo_target_countries:
                    score += 25
                elif any(c in art_text for c in geo_target_countries):
                    score += 12

            for kw in keywords:
                if kw in title_l:
                    score += 5
                elif kw in desc_l:
                    score += 2

            if score > 0:
                scored.append((score, art))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_articles = [art for _, art in scored[:max_articles]]
        if not top_articles and all_articles:
            top_articles = all_articles[:max_articles]

        context_lines = []
        for i, art in enumerate(top_articles, 1):
            date_str = art.publishedAt or "Recent"
            context_lines.append(f"Report {i}: [{date_str}] {art.title}\nSummary: {art.description}\nSource: {art.url or 'Wire'}")

        return "\n\n".join(context_lines)
    except Exception as e:
        logger.warning("Error building RAG context for query '%s': %s", query, e)
        return ""


def generate_ai_chat_response(user_message: str, db: Optional[Session] = None) -> str:
    """
    Primary Instant RAG Intelligence Engine.
    Executes live database retrieval, ranking, and constructs structured Markdown briefings.
    """
    msg_lower = user_message.lower().strip()
    geo_type, geo_name, geo_coords, geo_target_countries = detect_geo_entity(user_message)
    verified_donation_url = donation_links.get(geo_name) if geo_type == "country" else None

    # Step 1: Ranked search in database
    matched_articles = []
    all_db_articles = []
    if db:
        try:
            all_db_articles = db.query(NewsArticle).all()
            words = [re.sub(r'[^a-z0-9]', '', w) for w in msg_lower.split()]
            keywords = [w for w in words if len(w) >= 3 and w not in CHAT_STOP_WORDS]

            scored = []
            for art in all_db_articles:
                title_l = (art.title or "").lower()
                desc_l = (art.description or "").lower()
                art_text = f"{title_l} {desc_l}"
                art_geo_type, art_c_name, _, _ = detect_geo_entity(art_text)
                score = 0

                # Match by region / continent
                if geo_type == "region":
                    if art_c_name.lower() in geo_target_countries:
                        score += 20
                    elif any(c in art_text for c in geo_target_countries):
                        score += 12

                # Match by specific country
                elif geo_type == "country":
                    if art_c_name.lower() == geo_name.lower():
                        score += 25
                    elif geo_name.lower() in title_l:
                        score += 15
                    elif geo_name.lower() in desc_l:
                        score += 8

                # Match by remaining keywords
                for kw in keywords:
                    if kw in title_l:
                        score += 4
                    elif kw in desc_l:
                        score += 2

                if score > 0:
                    scored.append((score, art))

            scored.sort(key=lambda x: x[0], reverse=True)
            matched_articles = [art for score, art in scored]
        except Exception as e:
            logger.warning("Chat DB ranking error: %s", e)

    # Step 2: Deterministic Markdown Response Construction

    # Greetings
    if any(msg_lower.startswith(g) for g in ["hi", "hello", "hey", "greetings", "howdy", "good morning", "good evening"]):
        return (
            "### 👋 Hello! I am CrisisAid AI.\n\n"
            "I provide real-time situational intelligence on active humanitarian crises, disaster response, and verified relief channels.\n\n"
            "**What you can ask me:**\n"
            "* **Countries & Regions:** e.g., *'Situation in Sudan'*, *'Africa crisis updates'*, or *'Middle East briefing'*\n"
            "* **Verified Aid Funds:** e.g., *'How can I donate to emergency relief?'*\n"
            "* **Disaster Preparedness:** e.g., *'Earthquake safety tips'*"
        )

    # Donation query
    if any(w in msg_lower for w in ["donate", "donation", "give", "contribute", "help", "fund", "charity"]):
        if verified_donation_url and geo_type == "country":
            return (
                f"### 💸 Verified Frontline Relief for {geo_name}\n\n"
                f"You can support verified frontline relief operations in **{geo_name}** directly:\n\n"
                f"👉 **[Official {geo_name} Verified Relief Fund ↗]({verified_donation_url})**\n\n"
                f"**Leading International Partners in {geo_name}:**\n"
                "* **Doctors Without Borders (MSF):** [Medical & Trauma Relief ↗](https://www.msf.org/donate)\n"
                "* **UN World Food Programme (WFP):** [Emergency Food Assistance ↗](https://www.wfp.org/donate)\n"
                "* **International Red Cross (ICRC):** [Neutral Humanitarian Corridors ↗](https://www.icrc.org/en/donate)"
            )
        return (
            "### 💸 Verified Humanitarian Relief Channels\n\n"
            "To ensure your donation reaches verified frontline responders on the ground, support accredited international partners:\n\n"
            "* **Medical & Trauma Care:** [Doctors Without Borders (MSF) ↗](https://www.msf.org/donate)\n"
            "* **Emergency Food & Nutrition:** [UN World Food Programme (WFP) ↗](https://www.wfp.org/donate)\n"
            "* **Refugee Shelter & Legal Protection:** [UNHCR ↗](https://donate.unhcr.org/)\n"
            "* **Neutral Rapid Corridors:** [International Red Cross (ICRC) ↗](https://www.icrc.org/en/donate)\n\n"
            "*You can also search for a specific country in the search bar to find localized relief funds.*"
        )

    # Disaster preparedness & safety query
    if any(w in msg_lower for w in ["safety", "prepare", "tips", "survival", "first aid", "kit", "preparedness"]):
        return (
            "### 🛡️ Emergency Disaster Preparedness Guidelines\n\n"
            "* **72-Hour Emergency Go-Bag:** Pack 1 gallon of water per person per day, non-perishable food, high-lumen flashlights, portable battery radio, and a trauma first-aid kit.\n"
            "* **Water Purification:** Boil water vigorously for at least 1 full minute or use chlorine water purification tablets before consumption during flood and earthquake emergencies.\n"
            "* **Family Communication Plan:** Establish an out-of-area emergency contact and designate two safe evacuation meeting points.\n"
            "* **Official Broadcasts:** Monitor local civil defense emergency frequencies and official Red Cross/Crescent alerts."
        )

    # Continent / Region query
    if geo_type == "region":
        if matched_articles:
            reports = []
            for art in matched_articles[:4]:
                t = art.title.rstrip(".")
                d = art.description or "Active humanitarian monitoring."
                _, c_name, _, _ = detect_geo_entity(f"{art.title} {art.description or ''}")
                reports.append(
                    f"* **{t}** `({c_name})`\n"
                    f"  {d} [Read Briefing ↗](/news_article/{art.id}/{c_name})"
                )
            return (
                f"### 🌍 Regional Humanitarian Intelligence: {geo_name}\n\n"
                f"Current crisis monitoring across **{geo_name}** identifies active emergency responses in affected zones:\n\n"
                + "\n\n".join(reports)
                + "\n\n👉 **Frontline Relief:** Support emergency relief through [International Red Cross Corridors ↗](https://www.icrc.org/en/donate)"
            )

    # Specific country query
    if geo_type == "country" and geo_name != "Global Crisis Region":
        if matched_articles:
            reports = []
            for art in matched_articles[:3]:
                t = art.title.rstrip(".")
                d = art.description or "Ongoing frontline monitoring."
                reports.append(
                    f"* **{t}**\n"
                    f"  {d} [Read Briefing ↗](/news_article/{art.id}/{geo_name})"
                )
            donate_btn = ""
            if verified_donation_url:
                donate_btn = f"\n\n👉 **Verified Action:** [Donate to {geo_name} Emergency Relief ↗]({verified_donation_url})"
            return f"### 🚨 Crisis Overview & Latest Reports for {geo_name}\n\n" + "\n\n".join(reports) + donate_btn
        else:
            relief_url = donation_links.get(geo_name, "https://www.redcross.org/donate/donation.html/")
            return (
                f"### 🚨 Humanitarian Situation in {geo_name}\n\n"
                f"Frontline monitoring indicates active humanitarian distress in **{geo_name}**. Aid agencies are coordinating emergency supplies and medical relief.\n\n"
                f"👉 **Verified Relief Action:** [Donate to {geo_name} Relief ↗]({relief_url})"
            )

    # General crisis updates query (or fallback for broad search)
    is_general_update = any(w in msg_lower for w in ["latest", "update", "updates", "overview", "breaking", "current", "news", "summary", "today", "global"])
    if is_general_update or not matched_articles:
        source_articles = all_db_articles[:4] if all_db_articles else []
        if source_articles:
            reports = []
            for art in source_articles:
                t = art.title.rstrip(".")
                d = art.description or "Active humanitarian monitoring."
                c_name, _ = detect_country_coords(f"{art.title} {art.description or ''}")
                reports.append(
                    f"* **{t}** `({c_name})`\n"
                    f"  {d} [Read Briefing ↗](/news_article/{art.id}/{c_name})"
                )
            return "### 🚨 Global Humanitarian Crisis Briefing (Latest Updates)\n\n" + "\n\n".join(reports)

    return (
        "### 🤖 CrisisAid Humanitarian Assistant\n\n"
        "I am actively tracking global emergencies, natural disasters, and frontline relief corridors.\n\n"
        "Try asking me about a specific country (e.g. *'Sudan'*, *'Gaza'*, *'Ukraine'*), "
        "a continent (e.g. *'Africa'*, *'Middle East'*, *'Asia'*), "
        "or ask how you can donate to verified relief efforts."
    )
