"""Catalogue d'annuaires et de plateformes legitimes, et classement par thematique.

Chaque entree decrit une plateforme ou l'on peut obtenir un backlink de facon
legitime. Le champ ``api`` indique si une API officielle permet l'envoi
automatise (sinon, la soumission reste manuelle : l'humain valide).

Les champs ``dofollow`` marques "inconnu" sont a verifier au moment de la
soumission : ils changent souvent.
"""

from __future__ import annotations

import re
import unicodedata

# scope : "general" (tout sujet), "local" (annuaire local/pays), "niche" (thematique)
# cost  : "gratuit", "payant", "freemium"
DIRECTORIES: list[dict] = [
    {
        "slug": "google-business-profile",
        "name": "Google Business Profile",
        "url": "https://www.google.com/business/",
        "submit_url": "https://www.google.com/business/",
        "scope": "local", "cost": "gratuit", "api": True, "dofollow": "nofollow",
        "country": "*", "tags": [],
        "notes": "Incontournable en SEO local. Lien nofollow mais visibilite majeure. API officielle de gestion de fiches.",
    },
    {
        "slug": "bing-places",
        "name": "Bing Places for Business",
        "url": "https://www.bingplaces.com/",
        "submit_url": "https://www.bingplaces.com/",
        "scope": "local", "cost": "gratuit", "api": True, "dofollow": "nofollow",
        "country": "*", "tags": [],
        "notes": "Equivalent Microsoft. Import en masse et API disponibles.",
    },
    {
        "slug": "apple-business-connect",
        "name": "Apple Business Connect",
        "url": "https://businessconnect.apple.com/",
        "submit_url": "https://businessconnect.apple.com/",
        "scope": "local", "cost": "gratuit", "api": True, "dofollow": "nofollow",
        "country": "*", "tags": [],
        "notes": "Pour apparaitre sur Apple Plans. API / import de lieux.",
    },
    {
        "slug": "facebook-page",
        "name": "Meta - Page Facebook",
        "url": "https://www.facebook.com/business/pages",
        "submit_url": "https://www.facebook.com/pages/create",
        "scope": "general", "cost": "gratuit", "api": True, "dofollow": "nofollow",
        "country": "*", "tags": [],
        "notes": "Page entreprise via Graph API. Lien nofollow mais utile pour la presence.",
    },
    {
        "slug": "foursquare",
        "name": "Foursquare Places",
        "url": "https://foursquare.com/",
        "submit_url": "https://foursquare.com/add-place",
        "scope": "local", "cost": "freemium", "api": True, "dofollow": "inconnu",
        "country": "*", "tags": [],
        "notes": "Alimente de nombreuses applications cartographiques. API Places.",
    },
    {
        "slug": "pages-jaunes",
        "name": "PagesJaunes (FR)",
        "url": "https://www.pagesjaunes.fr/",
        "submit_url": "https://www.pagesjaunes.fr/pros/creation-fiche",
        "scope": "local", "cost": "freemium", "api": False, "dofollow": "inconnu",
        "country": "FR", "tags": [],
        "notes": "Annuaire local francais de reference. Soumission manuelle.",
    },
    {
        "slug": "yelp",
        "name": "Yelp",
        "url": "https://www.yelp.com/",
        "submit_url": "https://biz.yelp.com/",
        "scope": "local", "cost": "freemium", "api": False, "dofollow": "nofollow",
        "country": "*", "tags": ["restaurant", "commerce", "service", "local"],
        "notes": "API surtout en lecture : la creation de fiche se fait a la main.",
    },
    {
        "slug": "yext",
        "name": "Yext (agregateur)",
        "url": "https://www.yext.com/",
        "submit_url": "https://www.yext.com/",
        "scope": "general", "cost": "payant", "api": True, "dofollow": "inconnu",
        "country": "*", "tags": [],
        "notes": "Une fiche -> diffusion vers des dizaines d'annuaires partenaires via API. Payant.",
    },
    {
        "slug": "uberall",
        "name": "Uberall (agregateur)",
        "url": "https://uberall.com/",
        "submit_url": "https://uberall.com/",
        "scope": "general", "cost": "payant", "api": True, "dofollow": "inconnu",
        "country": "*", "tags": [],
        "notes": "Agregateur de fiches locales avec API. Payant.",
    },
    {
        "slug": "dev-to",
        "name": "DEV Community (dev.to)",
        "url": "https://dev.to/",
        "submit_url": "https://dev.to/new",
        "scope": "niche", "cost": "gratuit", "api": True, "dofollow": "inconnu",
        "country": "*",
        "tags": ["tech", "developpement", "logiciel", "programmation", "saas", "code", "informatique"],
        "notes": "Publication d'articles via API officielle (Forem). Backlink de contenu reel.",
    },
    {
        "slug": "hashnode",
        "name": "Hashnode",
        "url": "https://hashnode.com/",
        "submit_url": "https://hashnode.com/",
        "scope": "niche", "cost": "gratuit", "api": True, "dofollow": "inconnu",
        "country": "*",
        "tags": ["tech", "developpement", "logiciel", "programmation", "saas", "blog"],
        "notes": "Plateforme de blog technique avec API GraphQL.",
    },
    {
        "slug": "wordpress-com",
        "name": "WordPress.com",
        "url": "https://wordpress.com/",
        "submit_url": "https://wordpress.com/start",
        "scope": "general", "cost": "freemium", "api": True, "dofollow": "inconnu",
        "country": "*", "tags": ["blog", "contenu", "actualite"],
        "notes": "Publication de contenu via API REST. Backlink de contenu.",
    },
    {
        "slug": "product-hunt",
        "name": "Product Hunt",
        "url": "https://www.producthunt.com/",
        "submit_url": "https://www.producthunt.com/posts/new",
        "scope": "niche", "cost": "gratuit", "api": True, "dofollow": "inconnu",
        "country": "*",
        "tags": ["saas", "startup", "produit", "app", "tech", "logiciel"],
        "notes": "Lancement de produit/app. API disponible. Pertinent pour un produit tech.",
    },
    {
        "slug": "crunchbase",
        "name": "Crunchbase",
        "url": "https://www.crunchbase.com/",
        "submit_url": "https://www.crunchbase.com/",
        "scope": "niche", "cost": "freemium", "api": True, "dofollow": "inconnu",
        "country": "*",
        "tags": ["startup", "entreprise", "saas", "tech", "investissement"],
        "notes": "Fiche entreprise/startup. Soumission manuelle, donnees via API.",
    },
]

_SLUGS = {d["slug"] for d in DIRECTORIES}

STOPWORDS = {
    # francais
    "le", "la", "les", "un", "une", "des", "de", "du", "et", "ou", "a", "au",
    "aux", "en", "dans", "pour", "par", "sur", "avec", "sans", "ce", "cet",
    "cette", "ces", "son", "sa", "ses", "nos", "vos", "leur", "qui", "que",
    "quoi", "dont", "est", "sont", "etre", "avoir", "plus", "tout", "tous",
    "votre", "notre", "nous", "vous", "ils", "elle", "elles", "il", "se",
    # anglais
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
    "your", "our", "is", "are", "be", "this", "that", "we", "you", "it",
}


def get_directory(slug: str) -> dict | None:
    for d in DIRECTORIES:
        if d["slug"] == slug:
            return d
    return None


def _strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize_keywords(raw: str) -> list[str]:
    """Transforme un texte libre en liste de mots-cles normalises (sans accents,
    sans doublons, sans mots vides)."""
    text = _strip_accents(raw.lower())
    tokens = re.findall(r"[a-z0-9]+", text)
    seen: list[str] = []
    for tok in tokens:
        if len(tok) < 3 or tok in STOPWORDS:
            continue
        if tok not in seen:
            seen.append(tok)
    return seen


def score_directory(directory: dict, keywords: list[str], country: str = "FR") -> int:
    """Score de pertinence d'un annuaire pour une liste de mots-cles."""
    kw = set(keywords)
    score = 0
    scope = directory.get("scope")
    if scope == "general":
        score += 2
    elif scope == "local":
        score += 1
    # niche : pas de bonus de base, depend des tags

    tags = {_strip_accents(t.lower()) for t in directory.get("tags", [])}
    overlap = kw & tags
    score += 4 * len(overlap)

    dir_country = directory.get("country", "*")
    if dir_country == "*":
        score += 1
    elif dir_country.upper() == (country or "FR").upper():
        score += 2

    return score


def match_directories(keywords: list[str], country: str = "FR") -> list[dict]:
    """Retourne les annuaires classes par pertinence decroissante.

    Les entrees "niche" sans aucun tag correspondant sont ecartees (elles ne
    concernent pas la thematique du site)."""
    results = []
    kw = set(keywords)
    for d in DIRECTORIES:
        score = score_directory(d, keywords, country)
        tags = {_strip_accents(t.lower()) for t in d.get("tags", [])}
        if d.get("scope") == "niche" and not (kw & tags):
            continue
        results.append({**d, "score": score})
    results.sort(key=lambda d: (-d["score"], d["name"].lower()))
    return results
