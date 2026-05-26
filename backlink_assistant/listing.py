"""Generation du contenu de fiche pret a coller pour chaque annuaire."""

from __future__ import annotations

import re

SHORT_LIMIT = 160


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def short_description(text: str, limit: int = SHORT_LIMIT) -> str:
    text = _clean(text)
    if len(text) <= limit:
        return text
    cut = text[: limit - 1]
    if " " in cut:
        cut = cut[: cut.rfind(" ")]
    return cut + "…"


def generate_listing(site: dict, directory: dict) -> dict:
    """Prepare les champs a fournir a un annuaire pour un site donne."""
    name = _clean(site.get("name", ""))
    desc = _clean(site.get("description", ""))
    keywords = _clean(site.get("keywords", ""))

    listing = {
        "title": name,
        "url": _clean(site.get("url", "")),
        "short_description": short_description(desc),
        "long_description": desc,
        "category": _clean(site.get("category", "")),
        "keywords": keywords,
        "contact_email": _clean(site.get("contact_email", "")),
        "phone": _clean(site.get("phone", "")),
        "address": _clean(site.get("address", "")),
        "city": _clean(site.get("city", "")),
        "country": _clean(site.get("country", "")),
    }

    hints: list[str] = []
    if directory.get("api"):
        hints.append(
            "Cette plateforme propose une API officielle : l'envoi peut etre "
            "automatise une fois la cle API configuree."
        )
    else:
        hints.append(
            "Soumission manuelle : ouvrez le formulaire, collez les champs "
            "ci-dessus, puis validez vous-meme l'envoi."
        )
    if directory.get("dofollow") == "nofollow":
        hints.append(
            "Lien nofollow : faible impact SEO direct, mais utile pour la "
            "visibilite et la coherence des informations (NAP)."
        )
    elif directory.get("dofollow") == "inconnu":
        hints.append("Type de lien a verifier au moment de la soumission.")
    if directory.get("cost") == "payant":
        hints.append("Service payant.")

    return {"fields": listing, "hints": hints, "directory": directory}
