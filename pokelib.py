#!/usr/bin/env python3
"""Shared pieces for the HTML builds: icon lookup, slugs, page assembly.

build_html.py renders the collection and build_deck_html.py renders a deck
guide. Both want the same glyphs resolved the same way, so that lives here
rather than in three copies that drift.
"""
import html, re
from pathlib import Path

ROOT = Path(__file__).parent
ASSETS = ROOT / "assets"
TEMPLATE = ASSETS / "template.html"

# Set names that do not slugify onto their pokesymbols filename.
SET_SLUG = {
    "Base Set": "base",
    "EX Crystal Guardians": "crystal-guardians",
    "Pokémon GO": "pokemon-go",
    "SV: Scarlet & Violet 151": "151",
    "SWSH01: Sword & Shield Base Set": "sword-and-shield",
    "SWSH: Sword & Shield Promo Cards": "swsh-black-star-promos",
    # All three Halloween bundles carry the same Pikachu jack-o'-lantern stamp.
    "Trick or Trade BOOster Bundle": "trick-or-trade",
    "Trick or Trade BOOster Bundle 2023": "trick-or-trade",
    "Trick or Trade BOOster Bundle 2024": "trick-or-trade",
    "MBG: MEGA Starter Set Mega Gengar ex": "megagengar",
}

# Holo Rare shares the plain black star with Rare. Art Rare is what the
# Japanese line calls an Illustration Rare, and they share a symbol.
RARITY_SLUG = {
    "Common": "common", "Uncommon": "uncommon", "Rare": "rare",
    "Holo Rare": "rare", "Double Rare": "double-rare",
    "Ultra Rare": "ultra-rare", "ACE SPEC Rare": "ace-spec-rare",
    "Promo": "promo", "Art Rare": "illustration-rare",
}

TYPES = {"Colorless", "Darkness", "Dragon", "Fairy", "Fighting", "Fire",
         "Grass", "Lightning", "Metal", "Psychic", "Water"}

# Attack costs print as energy symbols, so the bracket letters become glyphs.
COST_TYPE = {"G": "Grass", "R": "Fire", "W": "Water", "L": "Lightning",
             "P": "Psychic", "F": "Fighting", "D": "Darkness", "M": "Metal",
             "Y": "Fairy", "N": "Dragon", "C": "Colorless"}


def esc(s):
    return html.escape(str(s or ""))


def img(src, alt, extra=""):
    return f'<img src="{src}" alt="{esc(alt)}"{extra} />'


def icon(folder, slug, alt):
    """An inline graphic, wrapped in <picture> when a dark variant exists."""
    if not slug:
        return ""
    for f in ((folder, "set-logos") if folder == "sets" else (folder,)):
        if not (ASSETS / f / f"{slug}.png").exists():
            continue
        tag = img(f"./assets/{f}/{slug}.png", alt)
        if (ASSETS / f"{f}-dark" / f"{slug}.png").exists():
            return ('<picture><source media="(prefers-color-scheme: dark)" '
                    f'srcset="./assets/{f}-dark/{slug}.png" />{tag}</picture>')
        return tag
    return ""


def type_icon(tcg_type):
    if tcg_type not in TYPES:
        return ""
    slug = tcg_type.lower()
    if not (ASSETS / "types" / f"{slug}.png").exists():
        return ""
    return img(f"./assets/types/{slug}.png", tcg_type)


def group(icons, kind=""):
    """Wrap a row's leading glyphs so they align as a column.

    Everything is left-aligned in a fixed box; "cost" only differs in being
    allowed to grow past that box when a card wants four symbols.
    """
    if not icons:
        return ""
    attr = ' data-icons="cost"' if kind == "cost" else " data-icons"
    return f"<span{attr}>{icons}</span>"


def row(icons, text, kind=""):
    """A value cell: leading glyphs, then the text in its own box.

    The text is boxed so a wrapped line stays under the first one rather than
    running back beneath the icons.
    """
    return group(icons, kind) + f"<span>{text}</span>"


def typed(v):
    """A value like "Darkness ×2" or "Fighting -30", led by its energy glyph."""
    return row(type_icon(v.split(" ")[0]), esc(v))


def cost_icons(letters):
    """Glyphs for an attack cost, or "" if any letter is not an energy type."""
    if not letters or any(c not in COST_TYPE for c in letters):
        return ""
    return "".join(type_icon(COST_TYPE[c]) for c in letters)


def set_slug(name):
    if name in SET_SLUG:
        return SET_SLUG[name]
    # Names arrive code-prefixed: "SWSH01: ", "SV: ", "ME03: ", "SM - ", "MBG: "
    s = re.sub(r"^[A-Z][A-Z0-9]{1,5}\s*[:\-]\s*", "", name)
    return re.sub(r"[^a-z0-9]+", "-", s.replace("&", "and").lower()).strip("-")


def set_folder(product_line):
    return "sets-jp" if "japan" in (product_line or "").lower() else "sets"


def mega_sigil(stage, name):
    """The Mega sigil, for cards that are one.

    Both signals are checked because the lines disagree: the Japanese one marks
    the stage "MegaEX" while the name carries "Mega".
    """
    if not (stage.lower().startswith("mega") or name.lower().startswith("mega ")):
        return ""
    if not (ASSETS / "glyphs" / "mega-evolution.svg").exists():
        return ""
    return img("./assets/glyphs/mega-evolution.svg", "Mega Evolution")


def anchor(text, seen):
    """Slugify a heading, keeping GitHub's -1/-2 suffix for repeats."""
    s = re.sub(r"[^\w\s-]", "", text.lower(), flags=re.UNICODE)
    s = re.sub(r"\s+", "-", s.strip())
    n = seen[s]
    seen[s] += 1
    return s if n == 0 else f"{s}-{n}"


def page(dest, title, subtitle, nav, body, notes="", sprite=""):
    """Fill the shared template and write it out.

    sprite names one file in assets/sprites, or several, shown beside the
    page title. Missing files are skipped rather than left as broken images.
    """
    out = TEMPLATE.read_text(encoding="utf-8")
    names = [sprite] if isinstance(sprite, str) else list(sprite or [])
    tag = "".join(
        f' <img data-mascot src="./assets/sprites/{s}.gif" alt="" />'
        for s in names if s and (ASSETS / "sprites" / f"{s}.gif").exists())
    out = out.replace("${SPRITE}", tag)
    if not nav:                       # no contents list, drop its line entirely
        out = re.sub(r"\n\t*\$\{NAV\}", "", out)
    if not subtitle:                  # likewise, no empty <p> left behind
        out = re.sub(r"\n\t*<p>\$\{SUBTITLE\}</p>", "", out)
    for token, repl in (("${TITLE}", title), ("${SUBTITLE}", subtitle),
                        ("${NAV}", nav), ("${ARTICLES}", body),
                        ("${NOTES}", notes)):
        out = out.replace(token, repl)
    dest.write_text(out, encoding="utf-8")
    return out
