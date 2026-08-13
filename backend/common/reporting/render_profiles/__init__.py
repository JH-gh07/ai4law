"""Render profiles for cross-format professional typesetting (task067 T05).

A render profile is the single authority for page geometry, base typography and
named style identifiers shared by the IR → DOCX/PDF renderers. The compiler
already gates ``render_contract.profile_id`` against the known set; the DOCX
renderer re-resolves the same ID through :func:`get_profile` and fails closed
on an unknown profile so a renderer can never invent geometry for an
unregistered profile.

The profile is pure data (no ``python-docx`` import) so it stays trivially
testable and reusable across DOCX and PDF backends.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]


class RenderProfileError(ValueError):
    """Raised when a render contract names an unknown render profile."""


@dataclass(frozen=True)
class RenderProfile:
    profile_id: str
    locale: str
    page_width_mm: float
    page_height_mm: float
    margin_top_mm: float
    margin_bottom_mm: float
    margin_left_mm: float
    margin_right_mm: float
    body_font: str
    body_font_cjk: str
    heading_font: str
    heading_font_cjk: str
    base_font_size_pt: float
    # Named Word style identifiers the DOCX renderer creates/validates.
    citation_note_style: str = "CitationNote"
    field_label_style: str = "FieldLabel"
    warning_style: str = "Warning"


_PROFILES: dict[str, RenderProfile] = {
    "legal-report-a4-v1": RenderProfile(
        profile_id="legal-report-a4-v1",
        locale="zh-CN",
        page_width_mm=210.0,
        page_height_mm=297.0,
        margin_top_mm=25.4,
        margin_bottom_mm=25.4,
        margin_left_mm=31.8,
        margin_right_mm=31.8,
        body_font="Calibri",
        body_font_cjk="宋体",
        heading_font="Calibri",
        heading_font_cjk="黑体",
        base_font_size_pt=11.0,
    ),
}

KNOWN_PROFILE_IDS = frozenset(_PROFILES)


def get_profile(profile_id: str) -> RenderProfile:
    """Return the registered profile, failing closed on unknown IDs."""
    profile = _PROFILES.get(profile_id)
    if profile is None:
        raise RenderProfileError(f"未知 render profile: {profile_id}")
    return profile


# ── font assets ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class FontAsset:
    """A discovered font asset, identified by path + content hash + license.

    The hash makes the asset part of the auditable render contract; the
    ``covers_cjk`` flag tells the PDF renderer whether it can carry Chinese
    text with ``emb=yes``. A Latin-only font must never be used for CJK text.
    """

    path: str
    sha256: str
    license: str | None
    covers_cjk: bool


# Filename hints for CJK-capable fonts. The same hints are used by the T00
# environment gate so the two inventories stay consistent.
_CJK_FONT_HINTS = (
    "noto", "sourcehan", "sourcehans", "pingfang", "microsoftyahei",
    "simsun", "simhei", "song", "hei", "kai", "cjk", "wqy", "zen",
    "fang", "ming", "gothic", "han",
)

# Dedicated backend font directory first, then the frontend public assets.
_FONT_SEARCH_ROOTS = (
    _ROOT / "resources" / "fonts",
    _ROOT / "assets" / "fonts",
    _ROOT / "frontend" / "public",
)

# Latin-only (but redistributable) Liberation Sans, already shipped with the
# repo's PDF.js assets. It embeds cleanly (``emb=yes``) and covers Latin text.
_LATIN_FONT_NAMES = ("liberationsans", "liberation-sans", "arial", "helvetica", "dejavu")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_font(path: Path) -> bool:
    return path.suffix.lower() in {".ttf", ".otf", ".ttc"}


def discover_font_assets() -> list[FontAsset]:
    """Inventory candidate font assets under the tracked font roots.

    Latin-only PDF.js fonts are discovered too (for the Latin body font), but
    their ``covers_cjk`` flag stays ``False`` so the renderer never uses them
    for Chinese text.
    """
    assets: list[FontAsset] = []
    seen: set[str] = set()
    for root in _FONT_SEARCH_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not _is_font(path):
                continue
            key = str(path)
            if key in seen:
                continue
            seen.add(key)
            lower = path.stem.lower()
            covers_cjk = any(hint in lower for hint in _CJK_FONT_HINTS)
            assets.append(FontAsset(
                path=str(path.relative_to(_ROOT)),
                sha256=_sha256(path),
                license=None,
                covers_cjk=covers_cjk,
            ))
    return assets


def get_cjk_font() -> FontAsset | None:
    """Return the first CJK-capable font asset, or ``None`` if none is tracked.

    ``None`` is the current repository state; the PDF renderer then degrades to
    the non-embedded ``STSong-Light`` CID font and the PDF font gate stays
    ``BLOCKED_BY_FONT`` until a licensed + hashed CJK font is added.
    """
    for asset in discover_font_assets():
        if asset.covers_cjk:
            return asset
    return None


def get_latin_font() -> FontAsset | None:
    """Return a Latin-capable font asset suitable for the body text.

    Prefers the *regular* weight so bold can be registered separately.
    """
    latin = [
        asset for asset in discover_font_assets()
        if not asset.covers_cjk and any(name in asset.path.lower() for name in _LATIN_FONT_NAMES)
    ]
    regular = [asset for asset in latin if "regular" in asset.path.lower()]
    return (regular or latin)[0] if (regular or latin) else None


__all__ = [
    "RenderProfile",
    "RenderProfileError",
    "FontAsset",
    "KNOWN_PROFILE_IDS",
    "get_profile",
    "discover_font_assets",
    "get_cjk_font",
    "get_latin_font",
]
