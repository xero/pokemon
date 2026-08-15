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
MASCOT = {"dark.md": ["gengar", "weezing"],
          "fire.md": ["charizard", "flareon"],
          "fire-tournament.md": ["flareon", "noctowl"],
          "fire-standard.md": ["eevee", "flareon"],
          "dark-ex.md": ["gengar-mega", "gengar-mega-shiny"],
          "psychic-lanterns.md": ["chandelure", "gengar"],
          "psychic-sleep.md": ["hypno", "gengar"],
          "psychic-standard.md": ["chandelure", "gourgeist"],
          "eevee-standard.md": ["eevee-ex", "umbreon"]}

# Sprites tucked into the corner of a heading, purely for flavour. Keyed by the
# exact heading text, so a reworded heading loses its sprite loudly rather than
# silently attaching it to the wrong section.
FLAVOR = {
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
    # the planning docs put their sprites on the Key Card Text entries, which
    # are the closest thing they have to a card page.
    # no sprite exists for Toxtricity, Munkidori, or Dragapult, so this one
    # runs on the Gengar line it is named after.
    # no sprite exists for Toxel, Toxtricity, Munkidori, Fezandipiti, or
    # Pecharunt, so the cards that have one get it and the rest go without.
    # seviper and sableye were promoted from assets/ani for this page.
    "dark-ex.md": {
        "Mega Gengar ex — Phantasmal Flames 056 · Reg I": ["gengar-mega"],
        "Gastly — Phantasmal Flames 054 · Reg I": ["gastly"],
        "Haunter — Perfect Order 049 · Reg J": ["haunter"],
        "Gengar — Perfect Order 050 · Reg J": ["gengar"],
        "Seviper — Phantasmal Flames 062 · Reg I": ["seviper"],
        "Sableye — Phantasmal Flames 059 · Reg I": ["sableye"],
        "✗ Gengar Spirit Link — Skip It": ["wobbuffet-back"],
        "Gengar Spirit Link — Phantom Forces 095": ["gengar-mega-shiny"],
        "The Real Card Is the Ability, Not the Attack": ["gengar-booty"],
        "Versus the Kitchen Table": ["weezing"],
        "How To Play ex Style": ["charizard"],
        "7. Errors to expect on the way over": ["eevee-back"],
        "What To Buy": ["koffing"],
    },
    "fire-standard.md": {
        # the card pages get the card's own Pokemon
        "Flareon ex — Prismatic Evolutions 014 · Reg H": ["flareon-ex"],
        "Eevee ex — Prismatic Evolutions 075 · Reg H": ["eevee-ex"],
        "Eevee — Prismatic Evolutions 074 · Reg H": ["eevee"],
        "Hoothoot — Stellar Crown 114 · Reg H": ["hoothoot"],
        "Noctowl — Stellar Crown 115 · Reg H": ["noctowl"],
        # the argument and the game plans
        "The Thesis": ["flareon"],
        "1. Turn One, Flareon": ["eevee"],
        "2. Jewel Seeker Is Your Real Draw Engine": ["noctowl"],
        "3. The Bench Is a Fortress": ["hoothoot"],
        # a back sprite means walking away: the trap play and the honest
        # downsides, not the cards the deck is built on
        "4. Carnelian Is a Trap Most of the Time": ["flareon-back"],
        "Honest Weaknesses": ["eevee-back"],
    },
    "psychic-lanterns.md": {
        "The Thesis": ["gastly"],
        "Chandelure — Noble Victories 060": ["chandelure"],
        "Litwick — Noble Victories 058": ["litwick"],
        "Lampent — Noble Victories 059": ["lampent"],
        "Wobbuffet — Phantom Forces 036": ["wobbuffet"],
        "Gengar — Lost Origin 066 *(you own the Trick or Trade 2023 reprint)*":
            ["gengar"],
        "Gengar — Sword & Shield 085": ["gengar-booty"],
        "Gourgeist — Evolving Skies 077 *(you own this as Trick or Trade 077)*":
            ["gourgeist"],
        "2. The Traffic Jam": ["pumpkaboo"],
        "Versus Fox": ["charizard"],
        "Build A or Build B?": ["drowzee"],
    },
    "psychic-standard.md": {
        # the ghost and ice lines came from assets/ani; no Mega Chandelure
        # sprite exists, so the base form stands in for it.
        "Mega Chandelure ex — Pitch Black 038 · Reg J": ["chandelure"],
        "Litwick — Pitch Black 036 · Reg J": ["litwick"],
        "Lampent — Pitch Black 037 · Reg J": ["lampent"],
        "Pumpkaboo — Chaos Rising 040 · Reg J": ["pumpkaboo"],
        "Gourgeist ex — Chaos Rising 041 · Reg J": ["gourgeist"],
        "Duskull — Shrouded Fable 018 · Reg H": ["duskull"],
        "Dusknoir — Shrouded Fable 020 · Reg H": ["dusknoir"],
        "Snorunt — Twilight Masquerade 051 · Reg H": ["snorunt"],
        "Froslass — Twilight Masquerade 053 · Reg H": ["froslass"],
        "Smoochum — Surging Sparks 075 · Reg H": ["smoochum"],
        "The Thesis": ["litwick"],
        "The Energy Engine": ["smoochum"],
        "1. The Trap": ["chandelure"],
        "2. Feeding the Rondo": ["gourgeist"],
        "3. The Thirteen-Counter Button": ["dusknoir"],
        "4. The Spreading Light Endgame": ["lampent"],
        "5. What This Deck Gives Up": ["duskull"],
        "Versus the Kitchen Table": ["charizard"],
        "What To Buy": ["pumpkaboo"],
    },
    # umbreon, espeon, and glaceon were promoted from assets/ani for this page.
    # the two module sections get their pair of Eeveelutions, which is the
    # fastest way to see at a glance which ten cards each one means.
    "eevee-standard.md": {
        "Eevee — Prismatic Evolutions 074 · Reg H": ["eevee"],
        "Eevee — Twilight Masquerade 135 · Reg H": ["eevee"],
        "Eevee ex — Prismatic Evolutions 075 · Reg H": ["eevee-ex"],
        "Flareon ex — Prismatic Evolutions 014 · Reg H": ["flareon-ex"],
        "Umbreon ex — Prismatic Evolutions 060 · Reg H": ["umbreon"],
        "Espeon ex — Prismatic Evolutions 034 · Reg H": ["espeon"],
        "Glaceon — Prismatic Evolutions 025 · Reg H": ["glaceon"],
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
    "psychic-sleep.md": {
        "The Thesis": ["gastly"],
        "Drowzee — Unbroken Bonds 071": ["drowzee"],
        "Hypno — Unbroken Bonds 072": ["hypno"],
        "Gengar — Sword & Shield 085": ["gengar"],
        "Gourgeist — Paradox Rift 078": ["gourgeist"],
        "Wobbuffet — Phantom Forces 036": ["wobbuffet"],
        "Gengar — Lost Origin 066 *(single copy)*": ["gengar-booty"],
        "4. Bide Barricade, and the One Thing It Costs You":
            ["wobbuffet-back"],
        "6. The Cemetery Tax": ["pumpkaboo"],
        "Versus Fox": ["charizard"],
        "Build A or Build B?": ["chandelure"],
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
    m = re.fullmatch(r"(\./)([\w-]+)\.md", url)
    if m and (ROOT / f"{m.group(2)}.html").exists():
        return f"./{m.group(2)}.html"
    return url


def inline(s):
    """Markdown spans to HTML. Raw tags in the source are passed through."""
    keep = []

    def stash(m):
        keep.append(m.group(0))
        return f"\x00{len(keep) - 1}\x00"

    s = re.sub(r"<(?:img|br)\b[^>]*/?>", stash, s)
    s = esc(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
               lambda m: f'<a href="{local_href(m.group(2))}">{m.group(1)}</a>', s)
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


# "Flareon ex — Prismatic Evolutions 014 · Reg H", and some headings name two
# cards. The number is what pins the printing.
HEADING_CARD = re.compile(r"([A-Z][\w'’.\- ]*?)\s+[—-]\s+([A-Za-z&'’.: \-]+?)\s+(\d{2,3})\b")

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
    different counts, as psychic-sleep does with Gengar.
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


def in_deck(counts, name, number):
    """How many of this card the deck list runs."""
    n = re.sub(r"\s*[—-]\s*.*$", "", name).strip().lower()
    num = str(number).split("/")[0].lstrip("0")
    return counts.get((n, num)) or counts.get((n, "")) or 0


def owned(n):
    n = int(n or 0)
    return "none yet" if n == 0 else ("1 copy" if n == 1 else f"{n} copies")


def card_block(heading, ind, counts=None):
    """Art and stats for every card a Key Card Text heading names.

    The deck guides hand-write this table; the planning docs never did, because
    until cards.csv carried the cards we do not own there was nothing to look
    up. A heading that names no card in the data produces nothing.
    """
    blocks, found = [], []
    for name, set_hint, number in HEADING_CARD.findall(heading):
        r = find_card(name.strip(), set_hint.strip(), number)
        if not r:
            continue
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
                # same badge the collection page uses, worded for a deck plan
                body = legal_cell(v, esc(LEGAL.get(v, v)))
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
    flav, seen_flav = FLAVOR.get(src.name, {}), set()
    counts = deck_counts(lines)
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
                blocks, found = card_block(name, "\t\t\t\t\t", counts)
                if blocks:
                    badge = count_badge(sum(
                        in_deck(counts, name, r["card_number"]) for r in found))
                    # each card is its own aside+section pair; the trailing
                    # open <section> then takes the hand-written prose
                    art = art[:-1] + blocks + [art[-1]]
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
            # a game plan gets its own box, the way a card does. left loose in
            # <main> its list markers hang outside the text column.
            sect = [f'\t\t\t\t<h3 id="{a}">{inline(name)}'
                    f'{flavor(name, flav, seen_flav)}</h3>']
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
            for h in render_table(parse_table(table), "\t\t\t\t\t"):
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
    for miss in sorted(set(flav) - seen_flav):
        print(f"  {src.name}: no heading matches flavour key {miss!r}")
    return title, subtitle, build_nav(toc), "\n".join(body), "\n".join(notes)


def build_nav(toc):
    """A contents list grouped by the document's own headings.

    Groups come from the top-level headings. Inside a group that has named
    subsections, only those are listed: the game plans each contain their own
    prose headings, and listing those buries the plans they belong to. A
    heading that appears before any group, like Fox's word list, becomes a
    group in its own right rather than being dropped.
    """
    out = ["<nav>", "\t<details open>", "\t\t<summary>Contents</summary>"]
    group, kids = None, []
    # the planning docs have no top-level groups at all, only ## sections. with
    # nothing to group under, promoting the first one turned it into a label
    # for its own siblings and cost it its link.
    grouped = any(lvl == 1 for lvl, _, _ in toc)

    def flush():
        nonlocal group
        if kids:
            if any(lvl == 2 for lvl, _, _ in kids):
                kids[:] = [k for k in kids if k[0] == 2]
            links = " · ".join(f'<a href="#{a}">{esc(x)}</a>' for _, x, a in kids)
            name = NAV_LABEL.get(group, group)
            label = f"<b>{esc(name)} —</b>" if group else ""
            out.append(f"\t\t<p>{label}<span>{links}</span></p>")
        elif group:
            out.append(f'\t\t<p><b>{esc(NAV_LABEL.get(group, group))}</b></p>')
        kids.clear()
        group = None

    for level, text, a in toc:
        if level == 1 or (grouped and level == 2 and group is None and not kids):
            flush()
            group = text
        else:
            kids.append((level, text, a))
    flush()
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


DECKS = ["dark.md", "dark-ex.md", "fire.md", "fire-tournament.md",
         "fire-standard.md", "psychic-lanterns.md", "psychic-sleep.md",
         "psychic-standard.md", "eevee-standard.md"]

for name in sys.argv[1:] or DECKS:
    src = ROOT / name
    dest = src.with_suffix(".html")
    title, subtitle, nav, body, notes = convert(src)
    out = page(dest, title, subtitle, nav, body, notes or CREDITS_NOTE,
               MASCOT.get(src.name, []))
    print(f"{dest.name}: {body.count('<article>')} cards, "
          f"{len(out.splitlines())} lines, {len(out) / 1024:.0f}kb")
