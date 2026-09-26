#!/usr/bin/env python3
"""Convert a deck guide from markdown to HTML: dark-gang.md -> dark-gang.html.

    python3 build_deck_html.py                  # every page decks.toml publishes
    python3 build_deck_html.py dark-gang.md     # just this one

What gets built, and the sprites on it, come from decks.toml through decklib.
A deck marked draft there is not built, and a full build deletes any page it
left behind, since the site publishes every .html in the repo.

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

from decklib import load as load_registry, published
from pokelib import (CREDITS_NOTE, anchor, card_art, cost_icons,
                     count_badge, esc, find_card, flair, icon, img,
                     legal_cell, page, row, set_slug, stat_cell,
                     type_icon)

ROOT = Path(__file__).parent

# Contents labels that read better than the heading they come from. The
# headings themselves are left alone; this only affects the contents list.
NAV_LABEL = {
    "Trainers — Supporters": "Trainers (Support)",
    "Trainers — Items": "Trainers (Items)",
    "Trainers — Tool & Stadium": "Trainers (Tool / Stadium)",
}

# Which pages exist, their title sprites, and their heading sprites all live in
# decks.toml, next to everything else about the page. decklib reads it.
LIBRARY, DECKS = load_registry()
ENTRIES = [e for e in LIBRARY + DECKS if e.get("source")]
MASCOT = {e["source"]: e["mascot"] for e in ENTRIES}
FLAVOR = {e["source"]: e["flavor"] for e in ENTRIES}

# every page the site publishes, by stem, generated or built from markdown
PUBLISHED = {Path(e["page"]).stem for e in published(LIBRARY + DECKS)}

# markdown that is never a page: the repo's own docs, and the GitHub copy of
# the collection that build_markdown.py writes
NOT_PAGES = {"README.md", "CLAUDE.md", "collection.md"}


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
    """Point a sibling .md link at its built page when that page is published.

    The markdown has to link .md so the files navigate on GitHub. From the
    built page that lands on the raw source instead, so a link to a published
    page is rewritten to its .html. Asking the registry rather than the disk
    keeps the first build after adding a deck identical to the second, and
    keeps a draft's leftover .html from being linked.
    """
    m = re.fullmatch(r"(\./)([\w-]+)\.md(#[^\s]*)?", url)
    if m and m.group(2) in PUBLISHED:
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
    child of the last group: The Thesis, the Versus pages, Alternatives. It
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


def build(name):
    src = ROOT / name
    dest = src.with_suffix(".html")
    title, subtitle, nav, body, notes = convert(src)
    out = page(dest, title, subtitle, nav, body, notes or CREDITS_NOTE,
               MASCOT.get(src.name, []))
    print(f"{dest.name}: {body.count('<article>')} cards, "
          f"{len(out.splitlines())} lines, {len(out) / 1024:.0f}kb")


def main():
    """Build the pages named on the command line, or every published one.

    A full build also clears out the page of any deck marked draft, because
    the site publishes every .html in the repo and a leftover would put the
    deck online before it is ready. And it names any deck-shaped markdown the
    registry does not list, since that is usually a deck someone forgot to add.
    """
    if sys.argv[1:]:
        for name in sys.argv[1:]:
            build(name)
        return
    for e in ENTRIES:
        if e["draft"] and (ROOT / e["page"]).exists():
            (ROOT / e["page"]).unlink()
            print(f"  removed {e['page']}: {e['source']} is a draft")
    for e in published(ENTRIES):
        build(e["source"])
    known = {e["source"] for e in ENTRIES} | NOT_PAGES
    for md in sorted(ROOT.glob("*.md")):
        if md.name not in known and re.search(r"^\|\s*\**Qty", md.read_text(
                encoding="utf-8"), re.M):
            print(f"  {md.name}: has a deck list but is not in decks.toml, so not built")


# guarded so the pull list can import the markdown readers without building
if __name__ == "__main__":
    main()
