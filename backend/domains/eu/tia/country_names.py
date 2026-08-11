"""Country-name normalization shared by TIA routing and risk assessment."""

from __future__ import annotations


COUNTRY_ALIASES = {
    "us": "United States",
    "u.s.": "United States",
    "usa": "United States",
    "u.s.a.": "United States",
    "in": "India",
    "cn": "China",
    "gb": "United Kingdom",
    "uk": "United Kingdom",
    "u.k.": "United Kingdom",
}


def normalize_country_name(value: str) -> str:
    normalized = value.strip()
    return COUNTRY_ALIASES.get(normalized.lower(), normalized)


def country_name_matches(value: str, known_country: str) -> bool:
    normalized = normalize_country_name(value).lower()
    known = known_country.strip().lower()
    if normalized == known:
        return True
    return len(normalized) >= 4 and (known in normalized or normalized in known)
