"""Detection de thematique : telecharge une page et en extrait des mots-cles.

Degrade proprement : si l'acces internet est indisponible, renvoie une erreur
exploitable par l'interface (l'utilisateur saisit alors les mots-cles a la main).
"""

from __future__ import annotations

import re
import urllib.error
import urllib.request
from collections import Counter

from .catalog import normalize_keywords

USER_AGENT = "BacklinkAssistant/0.1 (+local tool)"
TIMEOUT = 8
MAX_BYTES = 600_000


class AnalyzeError(Exception):
    """Erreur recuperable lors de l'analyse d'une URL."""


def _meta(pattern: str, html: str) -> str:
    m = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else ""


def _strip_tags(html: str) -> str:
    html = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    return re.sub(r"(?s)<[^>]+>", " ", html)


def fetch_html(url: str) -> str:
    if not re.match(r"^https?://", url, re.IGNORECASE):
        url = "https://" + url
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            raw = resp.read(MAX_BYTES)
        return raw.decode(charset, errors="replace")
    except urllib.error.URLError as exc:
        raise AnalyzeError(
            f"Impossible de telecharger la page ({exc}). "
            "Verifiez l'URL ou saisissez les mots-cles manuellement."
        ) from exc
    except Exception as exc:  # pragma: no cover - filet de securite
        raise AnalyzeError(f"Erreur d'analyse : {exc}") from exc


def extract_keywords(html: str, top: int = 12) -> dict:
    title = _meta(r"<title[^>]*>(.*?)</title>", html)
    description = _meta(
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', html
    )
    meta_keywords = _meta(
        r'<meta[^>]+name=["\']keywords["\'][^>]+content=["\'](.*?)["\']', html
    )

    text = " ".join([title, description, meta_keywords, _strip_tags(html)])
    tokens = normalize_keywords(text)

    # Privilegie les mots du titre et de la description.
    weighted = normalize_keywords(" ".join([title, description, meta_keywords]))
    counts = Counter(tokens)
    for w in weighted:
        counts[w] += 3

    keywords = [w for w, _ in counts.most_common(top)]
    return {
        "title": re.sub(r"\s+", " ", title).strip(),
        "description": re.sub(r"\s+", " ", description).strip(),
        "keywords": keywords,
    }


def analyze_url(url: str, top: int = 12) -> dict:
    html = fetch_html(url)
    result = extract_keywords(html, top=top)
    result["url"] = url
    return result
