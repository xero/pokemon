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

from pokelib import (anchor, cost_icons, esc, icon, page, row, set_slug,
                     typed, type_icon)

ROOT = Path(__file__).parent

# Stat rows that have a glyph to show. Everything else renders as plain text.
GLYPH_ROWS = {"Type", "Weakness", "Resistance"}


def inline(s):
    """Markdown spans to HTML. Raw tags in the source are passed through."""
    keep = []

    def stash(m):
        keep.append(m.group(0))
        return f"\x00{len(keep) - 1}\x00"

    s = re.sub(r"<(?:img|br)\b[^>]*/?>", stash, s)
    s = esc(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![*\w])\*([^*]+)\*(?!\*)", r"<em>\1</em>", s)
    return re.sub(r"\x00(\d+)\x00", lambda m: keep[int(m.group(1))], s)


def stat_rows(table):
    """A markdown key/value table as <dl> rows, with glyphs where they fit.

    The first two lines are the header and its underline, which carry no card
    data; a <dl> has no header row to put them in.
    """
    out = []
    for line in table[2:]:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 2 or set(cells[0]) <= set("-: "):
            continue
        key = re.sub(r"\*\*(.*?)\*\*", r"\1", cells[0])
        val = cells[1]
        if key == "Set":
            body = row(icon("sets", set_slug(val), val), esc(val))
        elif key in GLYPH_ROWS and val not in ("—", "-", ""):
            body = typed(val)
        elif key == "Retreat" and val.isdigit():
            body = row(type_icon("Colorless") * int(val), esc(val), "cost")
        elif key == "Attack":
            body = attack_row(val)
        else:
            body = row("", inline(val))
        out.append(f"\t\t\t\t\t\t<dt>{esc(key)}</dt><dd>{body}</dd>")
    return out


def attack_row(val):
    """Attack lines read "*Name* **[D] 30** — effect"; show the cost as glyphs."""
    m = re.search(r"\[([A-Z]+)\]", val)
    icons = cost_icons(m.group(1)) if m else ""
    if icons:
        val = val.replace(m.group(0), "", 1)
        val = re.sub(r"\*\*\s+", "**", val)     # "** 30**" -> "**30**"
    return row(icons, inline(val).strip(), "cost")


def convert(src):
    lines = src.read_text(encoding="utf-8").splitlines()
    title, subtitle = "", ""
    nav, notes, body = [], [], []
    seen = Counter()
    i, n = 0, len(lines)
    art = None            # the card currently being filled in

    def close():
        nonlocal art
        if art:
            body.append("\n".join(art + ["\t\t\t\t</section>", "\t\t\t</article>"]))
            art = None

    def emit(html_):
        (art if art is not None else body).append(html_)

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
                nav.append("<nav>\n\t<details open>\n\t\t<summary>Contents</summary>")
                for t in block:
                    if t.startswith("###") or not t.strip():
                        continue
                    nav.append(f"\t\t<p>{inline(t)}</p>")
                nav.append("\t</details>\n</nav>")
            else:
                target = notes if not body else body
                target.append(f'\t\t\t<aside data-callout="{kind}">')
                for para in "\n".join(block).split("\n\n"):
                    target += bullets_or_para(para, "\t\t\t\t")
                target.append("\t\t\t</aside>")
            continue

        if stripped.startswith("### "):
            close()
            name = stripped[4:].strip()
            a = anchor(name, seen)
            art = [f'\t\t\t<article>\n\t\t\t\t<h3 id="{a}">{inline(name)}</h3>']
            # an image on its own line becomes the card's aside
            j = i + 1
            while j < n and not lines[j].strip():
                j += 1
            if j < n and lines[j].strip().startswith("<img"):
                src_m = re.search(r'src="([^"]+)"', lines[j])
                art.append("\t\t\t\t<aside>"
                           f'<img src="{src_m.group(1)}" alt="{esc(name)}" />'
                           "</aside>")
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
                art += ["\t\t\t\t\t<dl>"] + stat_rows(table) + ["\t\t\t\t\t</dl>"]
                i = j - 1
            i += 1
            continue

        if stripped.startswith("#### "):
            emit(f"\t\t\t\t\t<h4>{inline(stripped[5:].strip())}</h4>")
            i += 1
            continue

        if stripped.startswith("## "):
            close()
            name = stripped[3:].strip()
            a = anchor(name, seen)
            body.append(f'\t\t\t<h3 id="{a}">{inline(name)}</h3>')
            i += 1
            continue

        if stripped.startswith("# "):
            close()
            name = stripped[2:].strip()
            a = anchor(name, seen)
            body.append(f'\t\t\t<h2 id="{a}">{inline(name)}</h2>')
            i += 1
            continue

        if stripped.startswith("```"):
            code = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                code.append(esc(lines[i]))
                i += 1
            emit("<pre><code>" + "\n".join(code) + "</code></pre>")
            i += 1
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
    if not subtitle:
        cards = sum(1 for x in body if "<article>" in x)
        subtitle = f"{cards} cards, one entry each."
    return title, subtitle, "\n".join(nav), "\n".join(body), "\n".join(notes)


def bullets_or_para(text, ind):
    """A block of lines as either a list or a paragraph."""
    lines = [l for l in text.splitlines() if l.strip()]
    if not lines:
        return []
    if all(re.match(r"^\s*[-*] ", l) for l in lines):
        out = [f"{ind}<ul>"]
        out += [f"{ind}\t<li>{inline(re.sub(r'^\\s*[-*] ', '', l))}</li>" for l in lines]
        return out + [f"{ind}</ul>"]
    if all(re.match(r"^\s*\d+\. ", l) for l in lines):
        out = [f"{ind}<ol>"]
        out += [f"{ind}\t<li>{inline(re.sub(r'^\\s*\\d+\\. ', '', l))}</li>" for l in lines]
        return out + [f"{ind}</ol>"]
    return [f"{ind}<p>{inline(' '.join(lines))}</p>"]


for name in sys.argv[1:] or ["dark.md", "fire.md"]:
    src = ROOT / name
    dest = src.with_suffix(".html")
    title, subtitle, nav, body, notes = convert(src)
    out = page(dest, title, subtitle, nav, body, notes)
    print(f"{dest.name}: {body.count('<article>')} cards, "
          f"{len(out.splitlines())} lines, {len(out) / 1024:.0f}kb")
