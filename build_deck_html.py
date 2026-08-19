#!/usr/bin/env python3
"""Convert a deck guide from markdown to HTML: dark.md -> dark.html.

    python3 build_deck_html.py dark.md fire.md

Unlike collection.html, these are not generated from cards.csv. The prose in
them is hand written and is the whole point of the files, so this converts what
is there rather than rebuilding it from the data.

The markdown is a known shape rather than arbitrary, so this parses that shape
instead of pulling in a full markdown engine:

    # Title                 the page
    > [!NOTE] ...           a callout
    > ### Table of Contents the nav
    # Pokémon               a group heading
    ### Gastly              a card, followed by an <img>, a stat table,
                            then #### General use / Pairing / Strategy
    ## 1. The Two-Turn Fuse a named game plan

Cards become the same <article> the collection page uses, so both read the
same. Stat rows reuse the shared glyph lookup where the field lines up.
"""
import re, sys
from collections import Counter
from pathlib import Path

from pokelib import (CREDITS_NOTE, anchor, card_art, cost_icons,
                     count_badge, esc, find_card, flair, icon, img,
                     legal_cell, page, row, set_folder, set_slug, stat_cell,
                     type_icon)

ROOT = Path(__file__).parent

# Contents labels that read better than the heading they come from. The
# headings themselves are left alone; this only affects the contents list.
NAV_LABEL = {
    "Trainers — Supporters": "Trainers (Support)",
    "Trainers — Items": "Trainers (Items)",
    "Trainers — Tool & Stadium": "Trainers (Tool / Stadium)",
}

# The mascot shown beside each deck's title.
MASCOT = {"rules.md": ["gengar-hop", "cursed"],
          "dark.md": ["gengar", "weezing"],
          "fire.md": ["charmander", "charizard"],
          "fire-tournament.md": ["flareon", "noctowl"],
          "dark-ex.md": ["gengar-smile", "gengar-mega"],
          "psychic-lanterns.md": ["chandelure", "gourgeist"],
          "eevee-standard.md": ["eevee", "umbreon", "espeon", "glaceon"],
          "rocket-mewtwo.md": ["crobat", "mewtwo"],
          "metal-excadrill.md": ["drilbur", "excadrill"]}

# Sprites tucked into the corner of a heading, purely for flavour. Keyed by the
# exact heading text, so a reworded heading loses its sprite loudly rather than
# silently attaching it to the wrong section.
FLAVOR = {
    # the rules lawyers: the fake tree and the wall that just sits there.
    "rules.md": {
        "The board": ["sudowoodo"],
        "Rules that trip people up": ["wobbuffet"],
        "The big-card words": ["gengar-mega"],
        "How a Game Runs": ["hoothoot"],
        "Special Conditions": ["drowzee"],
        "Standard Legal, and Why Some Decks Aren't": ["charizard"],
        "Tournament Night": ["noctowl"],
        "How To Play ex Style": ["gengar-mega-shiny"],
        "7. Errors to expect on the way over": ["eevee-back"],
    },
    "fire.md": {
        # the Pokemon card pages
        "Charmander": ["charmander"],
        "Charmeleon": ["charmeleon"],
        "Charizard": ["charizard"],
        "Eevee": ["eevee"],
        "Flareon": ["flareon"],
        "Sudowoodo": ["sudowoodo"],
        # the game plans
        "1. The Leon Engine": ["charizard"],
        "2. Two Speeds": ["eevee", "charmander"],
        "3. The Rock That Hits Back": ["sudowoodo"],
        "4. Winning the Stadium War": ["charizard-mega-y"],
        "5. Reading Your First Hand": ["flareon"],
        "Weezing — his early attacker (130 HP)": ["weezing"],
        "Gengar — his closer (130 HP)": ["gengar"],
        "His annoying cards": ["haunter"],
        "7. Mistakes That Will Cost You The Game": ["eevee-back"],
        "8. The Turn Checklist": ["charmeleon"],
    },
    # no sprite exists for Toxel, Toxtricity, Munkidori, or Fezandipiti, so
    # the cards that have one get it and the rest go without. sableye was
    # promoted from assets/ani for this page; the plain gengar sprite now
    # marks Gengar ex, since no dedicated ex sprite exists.
    "dark-ex.md": {
        "Gastly": ["gastly"],
        "Haunter": ["haunter"],
        "Gengar ex": ["gengar"],
        "Mega Gengar ex": ["gengar-mega"],
        "Sableye": ["sableye"],
        "The Prize Ladder": ["gengar-booty"],
        "1. Two Ghosts, One Line": ["gengar", "gengar-mega"],
        "6. Things That Will Cost You a Game": ["eevee-back"],
        "✗ Gengar Spirit Link — Skip It": ["wobbuffet-back", "gengar-mega-shiny"],
        "Versus the Kitchen Table": ["mewtwo"],
        "How To Play ex Style": ["charizard"],
        "What To Buy": ["koffing"],
    },
    "psychic-lanterns.md": {
        # the ghost and ice lines came from assets/ani; no Mega Chandelure
        # sprite exists, so the base form stands in for it.
        "The Thesis": ["litwick"],
        "Mega Chandelure ex": ["chandelure"],
        "Litwick": ["litwick"],
        "Lampent": ["lampent"],
        "Pumpkaboo": ["pumpkaboo"],
        "Gourgeist ex": ["gourgeist"],
        "Snorunt": ["snorunt"],
        "Froslass": ["froslass"],
        "Duskull": ["duskull"],
        "Dusknoir": ["dusknoir"],
        "The Energy Engine": ["snorunt"],
        "1. The Trap": ["chandelure"],
        "2. Feeding the Rondo": ["gourgeist"],
        "3. The Thirteen-Counter Button": ["dusknoir"],
        "4. The Spreading Light Endgame": ["lampent"],
        "5. Bench Discipline": ["pumpkaboo"],
        "6. What This Deck Gives Up": ["duskull"],
        "Versus the Kitchen Table": ["charizard"],
        "Versus the Card Shop": ["froslass"],
        # dusclops sits in the alternatives table, already owned
        "Alternatives": ["dusclops"],
        # the swap module forks the same line, so it gets the two stages the
        # forks grow from; no back sprites exist for the lantern line.
        "Night Parade": ["litwick", "lampent"],
        "Chandelure (Lost Thunder)": ["chandelure"],
        "Chandelure (Guardians Rising)": ["chandelure"],
        "What To Buy": ["pumpkaboo"],
    },
    # umbreon, espeon, and glaceon were promoted from assets/ani for this page.
    # the two module sections get their pair of Eeveelutions, which is the
    # fastest way to see at a glance which ten cards each one means.
    "eevee-standard.md": {
        "Eevee (Prismatic Evolutions · H)": ["eevee"],
        "Eevee (Twilight Masquerade · H)": ["eevee"],
        "Eevee ex": ["eevee-ex"],
        "Flareon ex": ["flareon-ex"],
        "Umbreon ex": ["umbreon"],
        "Espeon ex": ["espeon"],
        "Glaceon": ["glaceon"],
        "The Thesis": ["eevee"],
        "Sun and Moon": ["espeon", "umbreon"],
        "Fire and Ice": ["flareon", "glaceon"],
        "Pick Your Ten": ["eevee-ex"],
        "1. The Bench Is Safe, So Wait": ["hoothoot"],
        "2. Flareon ex Pays for Everything": ["flareon-ex"],
        # a back sprite for the honest downside, as in the other files
        "3. Three Knockouts and It Is Over": ["eevee-back"],
        "4. Choosing the Crystal's Home": ["noctowl"],
        "What To Buy": ["flareon"],
    },
    "fire-tournament.md": {
        # the Pokemon card pages
        "Eevee": ["eevee"],
        "Eevee ex": ["eevee-ex"],
        "Flareon ex": ["flareon-ex"],
        "Hoothoot": ["hoothoot"],
        "Noctowl": ["noctowl"],
        # the game plans
        "1. The Two-Energy Engine": ["flareon"],
        "2. Turn One, Flareon": ["eevee"],
        "3. Jewel Seeker Is Your Real Draw Engine": ["noctowl"],
        "4. The Bench Is a Fortress": ["hoothoot"],
        "5. The Prize Race Changed": ["gengar-mega"],
        "6. Reading Your First Hand": ["eevee-back"],
        "7. Beating Dad's Gengar Gang": ["gengar"],
        "Weezing — his early attacker (130 HP)": ["weezing"],
        "Gengar — his closer (130 HP)": ["gengar-booty"],
        "His answer to *Tera* is Boss's Orders": ["koffing"],
        "His annoying cards": ["haunter"],
        "8. Mistakes That Will Cost You The Game": ["flareon-back"],
        "9. The Turn Checklist": ["charizard"],
        # the argument up front and the honest downsides at the back, absorbed
        # from the retired fire-standard planning notes; a back sprite means
        # walking away, as in the other files.
        "The Thesis": ["flareon"],
        "Honest Weaknesses": ["eevee-back"],
    },
    # mewtwo, zubat, golbat, crobat and articuno were promoted from assets/ani
    # for this page. Spidops and Tarountula are gen 9, so the engine's own two
    # cards are the ones that go bare.
    "rocket-mewtwo.md": {
        "Team Rocket's Mewtwo ex": ["mewtwo"],
        "Team Rocket's Crobat ex": ["crobat"],
        "Team Rocket's Golbat": ["golbat"],
        "Team Rocket's Zubat": ["zubat"],
        "Team Rocket's Articuno": ["articuno"],
        "The Thesis": ["mewtwo"],
        "The Engine": ["zubat", "golbat"],
        "Damage Math": ["mewtwo"],
        "The Prize Map": ["crobat"],
        "2. Two attachments, then Mewtwo swings": ["mewtwo"],
        "4. Evolve Crobat by hand when you can afford the turn": ["golbat"],
        "5. Crobat is the answer to a bad Active": ["crobat"],
        "6. Articuno goes down early against effects": ["articuno"],
        # the matchups get the deck they are about, not this deck's cards.
        # zygarde was promoted from assets/ani for the Fighting row.
        "The Fighting deck, Mega Zygarde ex": ["zygarde"],
        "The Charizard deck": ["charizard"],
        "The Eeveelution deck, Flareon ex": ["flareon-ex"],
        "The Gengar decks": ["gengar", "gengar-mega"],
        "The lantern deck, Mega Chandelure ex": ["chandelure"],
        "What To Buy": ["zubat"],
    },
    # drilbur, excadrill, beldum, metang, genesect, metagross, scizor and
    # aggron were promoted from assets/ani for this page. No Mega Excadrill
    # sprite exists, so the base form stands in for it, and Fezandipiti is
    # gen 9 so it goes bare like the other gen 9 cards in the box.
    "metal-excadrill.md": {
        "Mega Excadrill ex": ["excadrill"],
        "Drilbur": ["drilbur"],
        "Metang": ["metang"],
        "Beldum": ["beldum"],
        "Genesect ex": ["genesect"],
        "The Thesis": ["excadrill"],
        "The Energy Engine": ["metang"],
        "Damage Math": ["excadrill"],
        "The Prize Map": ["genesect"],
        "1. Turn one is Drilbur, and it is not optional": ["drilbur"],
        "2. Two Metang before anything else": ["beldum", "metang"],
        "3. Count to five before you swing": ["excadrill"],
        # the matchup plans get the deck they are about, as on the other pages
        "4. Magnetic Metal is the anti-lantern card": ["chandelure"],
        "5. Losing Excadrill is not losing the game": ["genesect"],
        "6. Reading the opening hand": ["beldum"],
        "Versus the Kitchen Table": ["gengar", "chandelure"],
        "Versus the Card Shop": ["metagross"],
        "Alternatives": ["scizor", "aggron"],
        "What To Buy": ["drilbur"],
    },
    "dark.md": {
        "Gastly": ["gastly"],
        "Haunter": ["haunter"],
        "Gengar": ["gengar"],
        "Koffing": ["koffing"],
        "Weezing": ["weezing"],
        # no sprite exists for Toxel or Toxtricity; Sableye's came from ani
        "Sableye": ["sableye"],
        "1. The Two-Turn Fuse": ["weezing"],
        "2. Growing a Ghost in the Dark": ["gastly"],
        "3. The Bench Tax": ["gengar"],
        "4. Wearing the Helmet": ["koffing"],
        "5. Trading Ghosts": ["haunter"],
        "7. Things That Will Cost You a Game": ["gengar-booty"],
        "8. Teaching Notes": ["gengar-mega"],
        "Versus Fox's Decks": ["eevee", "seviper"],
    },
}


def flavor(name, table, used):
    """The corner sprites for a heading, or "" when it has none."""
    names = table.get(name)
    if not names:
        return ""
    used.add(name)
    return flair(names)

# Stat rows that have a glyph to show. Everything else renders as plain text.
GLYPH_ROWS = {"Type", "Weakness", "Resistance"}


def local_href(url):
    """Point a sibling .md link at its built page when there is one.

    The markdown has to link .md so the files navigate on GitHub. From the
    built page that lands on the raw source instead, so a link is rewritten
    only when the .html actually exists.
    """
    m = re.fullmatch(r"(\./)([\w-]+)\.md(#[^\s]*)?", url)
    if m and (ROOT / f"{m.group(2)}.html").exists():
        return f"./{m.group(2)}.html{m.group(3) or ''}"
    return url


def inline(s):
    """Markdown spans to HTML. Raw tags in the source are passed through."""
    keep = []

    def stash(m):
        keep.append(m.group(0))
        return f"\x00{len(keep) - 1}\x00"

    # the tags the hand-written pages actually use; anything else is text.
    # </?  so closing tags survive too, which <small>...</small> needs.
    s = re.sub(r"</?(?:img|br|small)\b[^>]*/?>", stash, s)
    s = esc(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    # the url half allows one level of balanced parens, because wiki urls carry
    # them (..._ex_(TCG)) and stopping at the first ) truncates the link and
    # spills the rest into the sentence as text.
    s = re.sub(r"\[([^\]]+)\]\(((?:[^()]|\([^()]*\))*)\)",
               lambda m: f'<a href="{local_href(m.group(2))}">{m.group(1)}</a>', s)

    # inline energy notation: a run like [R][W][L] (or a bundled [PPC])
    # becomes one span of type glyphs sitting in the sentence like words.
    # after the link pass, so [text](url) never looks like a cost.
    def glyphs(m):
        icons = cost_icons(re.sub(r"[\[\]]", "", m.group(0)))
        return f'<span data-icons="inline">{icons}</span>' if icons else m.group(0)

    s = re.sub(r"(?:\[[RWLGPDFMC]+\])+", glyphs, s)
    # ***both*** first: letting the bold rule see it produced <strong><em>x
    # </strong></em>, which is mis-nested and only survived because browsers
    # repair it.
    s = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", s, flags=re.S)
    # bold next, and allowed to span anything, so "**a *b* c**" works. the
    # old pattern refused to cross a nested emphasis and left the ** visible.
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s, flags=re.S)
    s = re.sub(r"(?<!\w)\*([^*]+)\*(?!\w)", r"<em>\1</em>", s, flags=re.S)
    return re.sub(r"\x00(\d+)\x00", lambda m: keep[int(m.group(1))], s)


def parse_table(table):
    """Markdown table lines to a grid, minus the |:---| underline row."""
    rows = [[c.strip() for c in l.strip().strip("|").split("|")] for l in table]
    return [r for r in rows if not all(set(c) <= set("-: ") and c for c in r)]


def render_table(rows, ind, stats=False):
    """A table as a <dl> when it is key/value, otherwise as a real <table>.

    Two columns is a card's stat block or a term and its meaning, which a <dl>
    says better. Three or more is a genuine table and needs to stay one; those
    were being dropped entirely before, since a <dl> has nowhere to put a third
    column.
    """
    if not rows:
        return []
    if max(len(r) for r in rows) == 2:
        # a card's stat block is marked so it can be styled apart from the
        # tables that appear in the prose. the tell is the card image: a real
        # card has one, a table of matchups or opening hands does not.
        if stats:
            # "Key | Val" over a card's stats says nothing worth a row
            return ([f'{ind}<dl class="card">'] + stat_rows(rows[1:])
                    + [f"{ind}</dl>"])
        # everywhere else the header is the only thing that says what the left
        # column means. dropping it left tables reading "3 | 60".
        head = (f"{ind}\t<dt data-head>{inline(rows[0][0])}</dt>"
                f"<dd data-head>{inline(rows[0][1])}</dd>")
        return [f"{ind}<dl>", head] + stat_rows(rows[1:]) + [f"{ind}</dl>"]
    head, body = rows[0], rows[1:]
    out = [f"{ind}<table>",
           f"{ind}\t<thead><tr>"
           + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead>",
           f"{ind}\t<tbody>"]
    for r in body:
        out.append(f"{ind}\t\t<tr>"
                   + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
    return out + [f"{ind}\t</tbody>", f"{ind}</table>"]


def stat_rows(rows):
    """Key/value rows as <dl> pairs, with glyphs where the field lines up."""
    out = []
    for cells in rows:
        if len(cells) != 2:
            continue
        key = re.sub(r"\*\*(.*?)\*\*", r"\1", cells[0])
        val = cells[1]
        # glyphs are looked up against the plain text, but the cell still
        # renders with its markdown; matching on "**Fighting**" finds nothing
        # and printing the plain form loses the emphasis
        plain = val.replace("*", "").strip()
        if key == "Set":
            body = row(icon("sets", set_slug(plain), plain), inline(val))
        elif key in GLYPH_ROWS and plain not in ("—", "-", ""):
            body = row(type_icon(plain.split(" ")[0]), inline(val))
        elif key == "Retreat" and plain.isdigit():
            body = row(type_icon("Colorless") * int(plain), esc(plain), "cost")
        elif key == "Attack":
            body = attack_row(val)
        else:
            body = row("", inline(val))
        # the key matches on plain text, but renders with its markdown, since
        # an arbitrary two-column table can have emphasis in the left column
        out.append(f"\t\t\t\t\t\t<dt>{inline(cells[0])}</dt><dd>{body}</dd>")
    return out


def attack_row(val):
    """Attack lines read "*Name* **[D] 30** — effect"; show the cost as glyphs."""
    m = re.search(r"\[([A-Z]+)\]", val)
    icons = cost_icons(m.group(1)) if m else ""
    if icons:
        val = val.replace(m.group(0), "", 1)
        val = re.sub(r"\*\*\s+", "**", val)     # "** 30**" -> "**30**"
    return row(icons, inline(val).strip(), "cost")


# A card heading is the card's name and nothing else. The set used to ride
# along in the heading text, which repeated on screen what the stat table
# already prints. It comes back only when a deck runs two printings of one
# card and the name alone stops saying which: "Eevee (Prismatic Evolutions ·
# H)". Set words and the regulation mark are both optional inside the parens,
# so "(H)" and "(Lost Thunder)" parse too, and "(130 HP)" parses to a set hint
# that matches nothing, which is what a prose heading deserves.
HEADING_CARD = re.compile(r"([A-Z][\w'’.\- ]*?)(?:\s*\(([^()]*)\))?\s*$")
REG_ONLY = re.compile(r"(?:Reg\s+)?[A-J]", re.I)


def heading_card(heading):
    """(name, set words) for a card heading, or None if it names no card.

    The parens hold the set, the regulation mark, or both, separated by a
    middot. The mark on its own is not a set hint, so it is dropped rather
    than handed to find_card as a word to match sets against.
    """
    m = HEADING_CARD.fullmatch(heading.strip())
    if not m:
        return None
    name, paren = m.group(1).strip(), (m.group(2) or "").strip()
    parts = [x.strip() for x in re.split(r"\s*·\s*", paren) if x.strip()]
    words = [x for x in parts if not REG_ONLY.fullmatch(x)]
    return name, " ".join(words)

# How a deck plan words legality. Terser than the collection page, which is
# talking to a reader browsing a binder rather than one checking a deck list.
# The badge that goes with each is shared, in pokelib.
LEGAL = {"yes": "legal", "no": "rotated out",
         "japanese": "Japanese, not legal in the US",
         "unknown": "unknown, check the letter on the card"}

# Which stat rows to show, and what to call them.
CARD_ROWS = [("set_name", "Set"), ("rarity", "Rarity"),
             ("card_type", "Type"), ("hp", "HP"), ("stage", "Stage"),
             ("card_text", "Ability"), ("weakness", "Weakness"),
             ("resistance", "Resistance"), ("retreat_cost", "Retreat"),
             ("standard_legal", "Tournament")]


def deck_counts(lines):
    """{(name, number): qty} from every table that leads with a Qty column.

    A card page shows how many that deck runs, and on the planning docs that
    number lives only in the deck list, not on the card entry. Keyed by number
    as well as name because a list can run two printings of one card at
    different counts.
    """
    out, cols = {}, None
    for l in lines:
        s = l.strip()
        if not s.startswith("|"):
            cols = None
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if cells and cells[0].lower() == "qty":
            cols = cells
            continue
        if not cols or set("".join(cells)) <= set("-: "):
            continue
        if len(cells) < 2 or not cells[0].strip("*").isdigit():
            continue
        qty = int(cells[0].strip("*"))
        name = re.sub(r"\*+|\[.*?\]", "", cells[1]).strip()
        num = ""
        for c in cells[2:]:
            m = re.fullmatch(r"\**(\d{2,3})\**", c.strip())
            if m:
                num = m.group(1).lstrip("0")
                break
        out[(name.lower(), num)] = qty
        out.setdefault((name.lower(), ""), qty)
    return out


def deck_printings(lines):
    """{name: [(set words, number), ...]} for every card the deck list names.

    Now that a heading carries the card's name alone, this is what says which
    printing it meant. The deck list already spells out the set and the number
    for all sixty, so the pin lives in one place instead of being repeated in
    every heading. A name with two entries here is exactly the case where the
    heading carries set words to choose between them.
    """
    out = {}
    i, n = 0, len(lines)
    while i < n:
        if not lines[i].strip().startswith("|"):
            i += 1
            continue
        table = []
        while i < n and lines[i].strip().startswith("|"):
            table.append(lines[i])
            i += 1
        grid = parse_table(table)
        if not grid or grid[0][0].lower() != "qty":
            continue
        head = [c.lower() for c in grid[0]]

        def col(row, want):
            j = head.index(want) if want in head else -1
            return row[j] if 0 <= j < len(row) else ""

        for r in grid[1:]:
            if len(r) < 2 or not r[0].strip("*").isdigit():
                continue
            name = re.sub(r"\*+|\[.*?\]", "", col(r, "card")).strip()
            # some deck lists have no Number column and print the number inside
            # the Set cell instead, the same shape deck_list() reads.
            hint, num = col(r, "set"), col(r, "number").strip("*")
            m = re.search(r"(\d{2,3})\s*$", hint)
            if not num and m:
                num, hint = m.group(1), hint[:m.start()]
            hint = hint.strip()
            if not name or set(hint) <= set("—- "):
                continue        # a flex slot, not a card
            seen = out.setdefault(name.lower(), [])
            if (hint, num) not in seen:
                seen.append((hint, num))
    return out


def resolve_card(heading, prints):
    """The cards.csv row a card heading names, or None.

    Two lookups, in order. The deck list is asked first, because it pins the
    exact printing and the heading no longer does. Only cards the deck list
    never mentions fall through to the set words in the heading's parens, which
    is how the alternatives and swap sections get their art.
    """
    parsed = heading_card(heading)
    if not parsed:
        return None
    name, hint = parsed
    rows = list((prints or {}).get(name.lower(), []))
    if len(rows) > 1 and hint:
        want = set(hint.lower().split())
        rows.sort(key=lambda sn: -len(want & set(sn[0].lower().split())))
    for st, num in rows[:1]:
        r = find_card(name, st or hint, num)
        if r:
            return r
    return find_card(name, hint, "")


def deck_list(lines, where=""):
    """(src, name, qty) for every distinct card the deck runs, in list order.

    Two page shapes feed the same strip. The planning docs carry Qty tables and
    nothing else, so the scan is looked up in cards.csv from the name, set, and
    number the table already prints. The older guides have no deck list at all;
    they give every card its own page, with the scan written into the markdown
    and the count in its stat table, so those are read off the card pages.

    Keyed on the scan, so a card that appears in both a Qty table and a card
    page is listed once, and two printings of one card stay two entries.
    """
    out, seen = [], set()

    def add(src, name, qty):
        if not src or src in seen:
            return
        seen.add(src)
        out.append((src, name, qty))

    i, n = 0, len(lines)
    heading, scan = "", ""
    while i < n:
        s = lines[i].strip()
        if s.startswith("### "):
            heading, scan = s[4:].strip(), ""
        elif s.startswith("<img"):
            m = re.search(r'src="([^"]+)"', s)
            scan = m.group(1) if m else ""
        elif s.startswith("|"):
            table = []
            while i < n and lines[i].strip().startswith("|"):
                table.append(lines[i])
                i += 1
            grid = parse_table(table)
            i -= 1
            if not grid:
                pass
            elif grid[0][0].lower() == "qty":
                head = [c.lower() for c in grid[0]]

                def col(row, want):
                    j = head.index(want) if want in head else -1
                    return row[j] if 0 <= j < len(row) else ""

                for r in grid[1:]:
                    if len(r) < 2 or not r[0].strip("*").isdigit():
                        continue
                    name = re.sub(r"\*+|\[.*?\]", "", col(r, "card")).strip()
                    # some deck lists have no Number column and print the number
                    # inside the Set cell instead. without it "Switch" picks a
                    # printing by set words alone, which is a coin toss.
                    hint = col(r, "set")
                    num = col(r, "number").strip("*")
                    m = re.search(r"(\d{2,3})\s*$", hint)
                    if not num and m:
                        num, hint = m.group(1), hint[:m.start()]
                    if not name or set(hint) <= set("—- "):
                        continue        # a flex slot, not a card
                    card = find_card(name, hint, num)
                    if card and card["image_file"]:
                        add(f'./assets/{card["image_file"]}', card["name"],
                            r[0].strip("*"))
                    else:
                        print(f"  {where}: no scan for deck list entry {name!r}")
            else:
                # a card page's own stat table: "| **Qty** | 4 |". the Set row
                # is the tell that this is a card and not a table of Fox's
                # annoying Trainers, which sits under a scan of its own.
                cells = {re.sub(r"\*+", "", r[0]).strip(): r[1].strip()
                         for r in grid if len(r) == 2}
                if "Set" in cells:
                    src = scan
                    if not src:
                        # Basic Water Energy is a card page with no scan
                        # written into it; the row in cards.csv has one.
                        card = find_card(heading, cells["Set"],
                                         cells.get("Number", ""))
                        src = (f'./assets/{card["image_file"]}'
                               if card and card["image_file"] else "")
                    add(src, heading,
                        cells.get("How many") or cells.get("Qty", ""))
                scan = ""
        i += 1
    return out


def gallery(entries, heading, ind="\t\t\t"):
    """The deck list as a strip of thumbnails, counts sitting on the art.

    One <article> rather than one per card: this is a single picture of the
    sixty, and the card pages below it are where a card gets its own box.
    """
    out = [f"{ind}<article data-decklist>"]
    if heading:
        out.append(f'{ind}\t<h3 id="deck-list">Deck List</h3>')
    for src, name, qty in entries:
        # singles carry no badge; the whole point of the number is to say
        # which cards arrive more than one at a time. counts read "4" or
        # "**1** (ACE SPEC)", so take the number rather than the whole cell.
        m = re.search(r"\d+", str(qty))
        badge = count_badge(qty) if m and int(m.group()) > 1 else ""
        # the name rides between sentinels so convert() can wrap the figure
        # in a link to the card's own section once the anchors exist; a name
        # no heading matches falls back to a plain image.
        out.append(f"{ind}\t<figure>\x00{name}\x01{img(src, name)}{badge}\x02"
                   "</figure>")
    return out + [f"{ind}</article>"]


def in_deck(counts, name, number):
    """How many of this card the deck list runs."""
    n = re.sub(r"\s*\([^()]*\)\s*$", "", name).strip().lower()
    num = str(number).split("/")[0].lstrip("0")
    return counts.get((n, num)) or counts.get((n, "")) or 0


def owned(n):
    n = int(n or 0)
    return "none yet" if n == 0 else ("1 copy" if n == 1 else f"{n} copies")


def card_block(heading, ind, prints=None):
    """Art and stats for the card a Key Card Text heading names.

    The deck guides hand-write this table; the planning docs never did, because
    until cards.csv carried the cards we do not own there was nothing to look
    up. A heading that names no card in the data produces nothing.
    """
    blocks, found = [], []
    r = resolve_card(heading, prints)
    if r:
        out = []
        if r["image_file"]:
            out += ["\t\t\t\t<aside>",
                    "\t\t\t\t\t" + card_art(f'./assets/{r["image_file"]}',
                                            r["name"]),
                    "\t\t\t\t</aside>"]
        out.append("\t\t\t\t<section>")
        out.append(f'{ind}<dl class="card">')
        for key, label in CARD_ROWS:
            v = r.get(key, "")
            if not v:
                continue
            if key == "standard_legal":
                # same badge the collection page uses, worded for a deck plan.
                # the regulation mark rides along here because the heading used
                # to carry it and nothing else on the page does.
                mark = r.get("regulation_mark", "")
                text = LEGAL.get(v, v) + (f" (Reg {mark})" if mark else "")
                body = legal_cell(v, esc(text))
            else:
                body = stat_cell(key, r)
            out.append(f"{ind}\t<dt>{esc(label)}</dt><dd>{body}</dd>")
        for k in ("attack1", "attack2", "attack3", "attack4"):
            if r.get(k):
                out.append(f"{ind}\t<dt>Attack</dt><dd>{attack_row(r[k])}</dd>")
        out.append(f"{ind}</dl>")
        out.append("\t\t\t\t</section>")
        blocks += out
        found.append(r)
    return blocks, found


def buy_table(body, ind):
    """A ```buy block into a shopping table costed from cards.csv.

    The Own column used to be typed by hand and went stale the moment anything
    was ordered. Here it is looked up, and Buy is arithmetic, so the table
    cannot disagree with the collection.
    """
    out = [f"{ind}<table>",
           f"{ind}\t<thead><tr><th>Card</th><th>Own</th><th>Need</th>"
           f"<th>Buy</th><th>Note</th></tr></thead>", f"{ind}\t<tbody>"]
    total = 0
    for line in body.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        f = [x.strip() for x in (line.split("|") + [""] * 4)[:4]]
        query, where, need, note = f
        m = re.search(r"(\d{2,3})\s*$", where)
        r = find_card(query, re.sub(r"\d+\s*$", "", where), m.group(1) if m else "")
        own = int(r["quantity"]) if r else 0
        try:
            want = int(need)
        except ValueError:
            want = 0
        buy = max(0, want - own)
        total += buy
        label = esc(query)
        if r:
            label = row(icon(set_folder(r.get("product_line")),
                             set_slug(r["set_name"]), r["set_name"]),
                        f'{esc(r["name"])} <small>{esc(r["set_name"])} '
                        f'{esc(r["card_number"])}</small>')
        elif where:
            label += f" <small>{esc(where)}</small>"
        cells = [label, str(own), esc(need),
                 f"<strong>{buy}</strong>" if buy else "✓",
                 inline(note) if note else ""]
        out.append(f"{ind}\t\t<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
    out.append(f"{ind}\t\t<tr><td><strong>Total to buy</strong></td><td></td><td></td>"
               f"<td><strong>{total}</strong></td><td></td></tr>")
    return out + [f"{ind}\t</tbody>", f"{ind}</table>"]


def convert(src):
    lines = src.read_text(encoding="utf-8").splitlines()
    title, subtitle = "", ""
    nav, notes, body = [], [], []
    # (level, text, anchor) for every heading, so the contents list is built
    # from the document rather than from a hand-kept list that drifts out of
    # step with it. fire.md's own list had lost "Word List" and never had the
    # game plans in it at all.
    toc = []
    seen = Counter()
    # heading text -> anchor, for linking the deck-list thumbnails to their
    # card sections. also keyed with the parens dropped, which is the name a
    # Qty table row carries for a card whose heading pins a printing.
    card_anchor = {}
    flav, seen_flav = FLAVOR.get(src.name, {}), set()
    counts = deck_counts(lines)
    prints = deck_printings(lines)
    thumbs, shown = deck_list(lines, src.name), False
    i, n = 0, len(lines)
    art = None            # the card currently being filled in
    sect = None           # the ## section currently being filled in

    def close_art():
        nonlocal art
        if art:
            done = "\n".join(art + ["\t\t\t\t</section>", "\t\t\t</article>"])
            (sect if sect is not None else body).append(done)
            art = None

    def close_sect():
        nonlocal sect
        close_art()
        if sect is not None:
            if sect and sect[0].lstrip() == "<details>":
                sect.append("\t\t\t\t</details>")
            body.append("\n".join(["\t\t\t<section>"] + sect + ["\t\t\t</section>"]))
            sect = None

    def close():
        close_sect()

    def emit(html_):
        for target in (art, sect, body):
            if target is not None:
                target.append(html_)
                return

    while i < n:
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("# ") and not title:
            title = stripped[2:].strip()
            i += 1
            continue

        # the thumbnail strip goes directly above the Pokémon, which the two
        # page shapes announce differently: the guides open a "# Pokémon"
        # group, the planning docs label the first table "**Pokémon (22)**"
        # inside their Deck List section. only the first gets a heading of its
        # own; in the planning docs it is already under one.
        if thumbs and not shown and re.match(r"(#{1,2} |\*\*)Pokémon\b", stripped):
            head = stripped.startswith("#")
            if head:
                close_sect()
            for h in gallery(thumbs, head):
                emit(h)
            shown = True

        # blockquote run: either a callout, the contents, or a plain aside
        if stripped.startswith(">"):
            block, kind = [], "note"
            while i < n and lines[i].strip().startswith(">"):
                t = re.sub(r"^>\s?", "", lines[i].strip())
                m = re.match(r"\[!(\w+)\]", t)
                if m:
                    kind = m.group(1).lower()
                else:
                    block.append(t)
                i += 1
            if any(x.startswith("### Table of Contents") for x in block):
                pass                       # rebuilt below from the headings
            else:
                # emit(), so a callout that belongs to a card ends up inside
                # that card rather than loose in <main>. before any card, it
                # lands at the top of the page where the intro belongs.
                emit(f'\t\t\t<aside data-callout="{kind}">')
                for para in "\n".join(block).split("\n\n"):
                    for h in bullets_or_para(para, "\t\t\t\t"):
                        emit(h)
                emit("\t\t\t</aside>")
            continue

        # a ### sitting directly under the page title is a subtitle, not a
        # card. the planning docs open that way ("Build A - ..."), and left as
        # an article it swallowed the intro callout into a box of its own.
        if (stripped.startswith("### ") and title and not subtitle
                and not body and art is None and sect is None):
            subtitle = stripped[4:].strip()
            i += 1
            continue

        if stripped.startswith("### "):
            close_art()
            name = stripped[4:].strip()
            a = anchor(name, seen)
            card_anchor.setdefault(name, a)
            card_anchor.setdefault(
                re.sub(r"\s*\([^()]*\)\s*$", "", name).strip(), a)
            art = [f'\t\t\t<article>\n\t\t\t\t<h3 id="{a}">{inline(name)}'
                   f'\x00{flavor(name, flav, seen_flav)}</h3>']
            badge = ""
            # an image on its own line becomes the card's aside
            has_image = False
            j = i + 1
            while j < n and not lines[j].strip():
                j += 1
            if j < n and lines[j].strip().startswith("<img"):
                has_image = True
                src_m = re.search(r'src="([^"]+)"', lines[j])
                art.append("\t\t\t\t<aside>"
                           + card_art(src_m.group(1), name)
                           + "</aside>")
                i = j
            art.append("\t\t\t\t<section>")
            # the stat table, if the next non-blank block is one
            j = i + 1
            while j < n and not lines[j].strip():
                j += 1
            if j < n and lines[j].strip().startswith("|"):
                table = []
                while j < n and lines[j].strip().startswith("|"):
                    table.append(lines[j])
                    j += 1
                grid = parse_table(table)
                cells = {re.sub(r"\*+", "", r[0]).strip(): r[1].strip()
                         for r in grid if len(r) == 2}
                # a card scan used to be the tell for "this is a card", which
                # missed Basic Water Energy: a real card page with no scan. The
                # count row is the better tell, and a glossary table has none.
                is_card = has_image or "How many" in cells or "Qty" in cells
                if is_card:
                    # the hand-written count is how many the DECK runs. read it
                    # before dropping the row, then show it as the badge in the
                    # heading rather than repeating it here.
                    badge = count_badge(cells.get("How many")
                                        or cells.get("Qty", ""))
                    grid = [r for r in grid
                            if re.sub(r"\*+", "", r[0]).strip()
                            not in ("How many", "Qty")]
                rendered = render_table(grid, "\t\t\t\t\t", stats=is_card)
                art += rendered
                i = j - 1
                # a table means this is a card or a glossary entry, both worth
                # indexing. a ### with no table is a prose subsection inside a
                # game plan, and listing those buries the plans themselves.
                toc.append((3, name, a))
            elif not has_image:
                # no hand-written table. if the heading names a card, build one
                # from cards.csv; the planning docs get their art this way.
                blocks, found = card_block(name, "\t\t\t\t\t", prints)
                if blocks:
                    badge = count_badge(sum(
                        in_deck(counts, name, r["card_number"]) for r in found))
                    # each card is its own aside+section pair; the trailing
                    # open <section> then takes the hand-written prose
                    art = art[:-1] + blocks + [art[-1]]
                    toc.append((3, name, a))
                elif re.match(r"(?:[A-Za-z]+ )?\d+[.:]", name):
                    # a numbered prose subsection is a named step, and the
                    # steps are the section: index it under its ## the same
                    # way a numbered ## nests under its group.
                    toc.append((3, name, a))
            art[0] = art[0].replace("\x00", badge)
            i += 1
            continue

        if stripped.startswith("#### "):
            emit(f"\t\t\t\t\t<h4>{inline(stripped[5:].strip())}</h4>")
            i += 1
            continue

        if stripped.startswith("## "):
            close_sect()
            name = stripped[3:].strip()
            a = anchor(name, seen)
            toc.append((2, name, a))
            head = (f'<h3 id="{a}">{inline(name)}'
                    f'{flavor(name, flav, seen_flav)}</h3>')
            # a game plan gets its own box, the way a card does. left loose in
            # <main> its list markers hang outside the text column.
            if name == "What To Buy":
                # the shopping list collapses behind its own heading; the box
                # and the corner sprite stay, the contents wait to be asked.
                sect = ["\t\t\t\t<details>",
                        f"\t\t\t\t\t<summary>{head}</summary>"]
            else:
                sect = [f"\t\t\t\t{head}"]
            i += 1
            continue

        if stripped.startswith("# "):
            close_sect()
            name = stripped[2:].strip()
            a = anchor(name, seen)
            toc.append((1, name, a))
            body.append(f'\t\t\t<h2 id="{a}">{inline(name)}</h2>')
            i += 1
            continue

        if stripped.startswith("```"):
            lang = stripped[3:].strip().lower()
            code = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1
            if lang == "buy":
                for h in buy_table("\n".join(code), "\t\t\t\t\t"):
                    emit(h)
            else:
                emit("<pre><code>" + "\n".join(esc(c) for c in code)
                     + "</code></pre>")
            continue

        if stripped.startswith("|"):
            table = []
            while i < n and lines[i].strip().startswith("|"):
                table.append(lines[i])
                i += 1
            grid = parse_table(table)
            rendered = render_table(grid, "\t\t\t\t\t")
            # a Qty table exists to feed the badges and the deck-list strip.
            # on a page that draws the strip, the strip IS the deck list, so
            # the rows stay in the markdown and out of the rendered page.
            if (thumbs and rendered and grid and grid[0]
                    and grid[0][0].strip().strip("*").strip().lower() == "qty"):
                rendered[0] = rendered[0].replace(
                    "<table>", "<table data-deck-rows>", 1)
            # an <img> on its own line directly after a table rides beside it:
            # the pair share a flex row, image on the right, and the image
            # drops below the table on a narrow screen. a card scan never
            # lands here, because those sit above their table, not below.
            j = i
            while j < n and not lines[j].strip():
                j += 1
            if j < n and lines[j].strip().startswith("<img"):
                emit("\t\t\t\t\t<div data-beside>")
                for h in rendered:
                    emit("\t" + h)
                emit(f"\t\t\t\t\t\t{lines[j].strip()}")
                emit("\t\t\t\t\t</div>")
                i = j + 1
            else:
                for h in rendered:
                    emit(h)
            continue

        if stripped in ("---", "") or stripped.startswith("<br"):
            i += 1
            continue

        # a paragraph or list runs to the next blank line
        para = []
        while i < n and lines[i].strip() and not re.match(
                r"^\s*(#{1,4} |```|---|>|\|)", lines[i]):
            para.append(lines[i].strip())
            i += 1
        if not para:
            i += 1              # nothing consumable here, do not stall on it
            continue
        for h in bullets_or_para("\n".join(para), "\t\t\t\t\t"):
            emit(h)

    close()
    # resolve the thumbnail links now that every heading has its anchor: the
    # strip renders before the card sections are parsed, so gallery() leaves
    # the card name between sentinels and the href lands here.
    def link_thumb(m):
        name = m.group(1)
        # a cards.csv name can carry a qualifier the heading drops, in parens
        # (Welder (#25 Charizard Stamped)) or brackets (Boss's Orders
        # [Ghetsis]); retry bare before giving up on the link.
        a = (card_anchor.get(name)
             or card_anchor.get(
                 re.sub(r"\s*[\[(][^)\]]*[)\]]\s*$", "", name).strip()))
        return f'<a href="#{a}">{m.group(2)}</a>' if a else m.group(2)
    body = [re.sub("\x00(.*?)\x01(.*?)\x02", link_thumb, b) for b in body]
    for miss in sorted(set(flav) - seen_flav):
        print(f"  {src.name}: no heading matches flavour key {miss!r}")
    return title, subtitle, build_nav(toc), "\n".join(body), "\n".join(notes)


def build_nav(toc):
    """A contents list grouped by the document's own headings.

    Top-level headings are groups: an unlinked label followed by whatever
    they contain. Inside a group that has numbered subsections, only those
    are listed: the game plans each contain their own prose headings, and
    listing those buries the plans they belong to.

    A ## heading that is not a numbered plan is a section of its own, not a
    child of the last group: The Thesis, the Versus pages, What To Buy. It
    gets its own linked row, and if it carries indexed subsections of its own,
    like Fox's word list, they follow it after the dash.

    The rows then split by whether they have children, because the two kinds
    were reading identically. A childless row is a destination and leads as a
    chip; a row with children is a heading over a list, and those go in a
    definition list underneath, where one shared label column lets the eye run
    down the group names instead of chasing a ragged edge.
    """
    out = ["<nav>", "\t<details open>", "\t\t<summary>Contents</summary>"]
    # (origin level, label text, anchor or None, kids)
    rows = []
    # a page with no top-level groups at all, only ## sections, stays a flat
    # list of links rather than promoting the first section into a label.
    grouped = any(lvl == 1 for lvl, _, _ in toc)

    kids = []
    def start(origin, text, a):
        nonlocal kids
        kids = []
        rows.append((origin, text, a, kids))

    for level, text, a in toc:
        if level == 1:
            start(1, text, None)
        elif level == 2 and grouped:
            # a numbered heading ("3. The Bench Tax", "Reason 1: ...") is a
            # child of the group above it; anything else is a section of its
            # own, however far down the page it sits.
            if rows and rows[-1][0] == 1 and re.match(r"(?:[A-Za-z]+ )?\d+[.:]", text):
                kids.append((level, text, a))
            else:
                start(2, text, a)
        else:
            if not rows:
                start(0, "", None)
            kids.append((level, text, a))

    chips, index = [], []
    for origin, text, a, ks in rows:
        if any(lvl == 2 for lvl, _, _ in ks):
            ks = [k for k in ks if k[0] == 2]
        name = NAV_LABEL.get(text, text)
        if origin == 0:
            # an ungrouped page is nothing but destinations
            chips += [(x, ka) for _, x, ka in ks]
        elif not ks:
            # a group heading with no cards under it is not a destination and
            # not a list; there is nothing for it to link to either way.
            if a:
                chips.append((name, a))
        else:
            label = f'<a href="#{a}">{esc(name)}</a>' if a else esc(name)
            # no separator between them: the row is a flex line, so the gap
            # does the separating and a long plan title wraps as a whole
            # instead of breaking across the dot.
            links = " ".join(f'<a href="#{ka}">{esc(x)}</a>' for _, x, ka in ks)
            index.append((label, links))

    if chips:
        out.append("\t\t<ul data-sections>")
        out += [f'\t\t\t<li><a href="#{ka}">{esc(x)}</a></li>' for x, ka in chips]
        out.append("\t\t</ul>")
    if index:
        out.append("\t\t<dl data-index>")
        for label, links in index:
            out += [f"\t\t\t<dt>{label}</dt>", f"\t\t\t<dd>{links}</dd>"]
        out.append("\t\t</dl>")
    out += ["\t</details>", "</nav>"]
    return "\n".join(out)


def bullets_or_para(text, ind):
    """A block of lines as either a list or a paragraph."""
    lines = [l for l in text.splitlines() if l.strip()]
    if not lines:
        return []
    if all(re.match(r"^\s*[-*] ", l) for l in lines):
        out = [f"{ind}<ul>"]
        out += [f"{ind}\t<li>{inline(re.sub(r'^\s*[-*] ', '', l))}</li>" for l in lines]
        return out + [f"{ind}</ul>"]
    if all(re.match(r"^\s*\d+\. ", l) for l in lines):
        out = [f"{ind}<ol>"]
        out += [f"{ind}\t<li>{inline(re.sub(r'^\s*\d+\. ', '', l))}</li>" for l in lines]
        return out + [f"{ind}</ol>"]
    return [f"{ind}<p>{inline(' '.join(lines))}</p>"]


DECKS = ["rules.md", "dark.md", "dark-ex.md", "fire.md", "fire-tournament.md",
         "rocket-mewtwo.md",
         "psychic-lanterns.md", "eevee-standard.md", "metal-excadrill.md"]

for name in sys.argv[1:] or DECKS:
    src = ROOT / name
    dest = src.with_suffix(".html")
    title, subtitle, nav, body, notes = convert(src)
    out = page(dest, title, subtitle, nav, body, notes or CREDITS_NOTE,
               MASCOT.get(src.name, []))
    print(f"{dest.name}: {body.count('<article>')} cards, "
          f"{len(out.splitlines())} lines, {len(out) / 1024:.0f}kb")
