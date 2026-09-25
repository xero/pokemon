#!/usr/bin/env python3
"""Write index.html, the front page linking the three generated pages.

Counts are read back out of the pages themselves rather than recomputed, so
the index cannot claim a number the page it links to disagrees with.
"""
import re
from pathlib import Path

from pokelib import CREDITS_NOTE, esc, page

ROOT = Path(__file__).parent

# the heading that opens the plain rows. every card above it, the library
# and the league decks, carries data-featured, which the template tints.
OTHER = "## Other Decks"

PAGES = [
    # the library, not decks, so no heading of its own
    ("collection.html", ["pokedex", "pokeball"],
     "A searchable collection of our combined binders. Every card, stat, and"
     " ability, and whether it's legal for tournament play."),
    ("wishlist.html", ["deck"],
     "The pull list: every card a deck asks for that the binders cannot"
     " cover, costed against what we already own."),
    ("rules.html", ["gengar-hop", "cursed"],
     "The table rulebook: every game word the deck pages lean on, how a game"
     " actually runs, what the letters on the cards mean, and what a real"
     " tournament expects."),
    # a bare string is a heading, and its hashes are its level, same as the
    # markdown. every page after it takes the next level down for its title.
    # the two decks we are sleeving now, Fox first. these are the only two
    # titles that carry our names.
    "## League Decks",
    ("fire.html", ["charmander", "charizard"],
     "Fox's deck, card by card: what each one is for, what it wants to sit next"
     " to, and how to beat dad."),
    ("dark-gang.html", ["gengar", "okidogi"],
     "Xero's league-night 60, built on the 30th Celebration Gengar ex. Chaotic"
     " Pain kills the body every Mega grows out of, Grimsley's Move drops a"
     " Mega Gengar straight onto the Bench for the Prize tax, and the Okidogi"
     " hold the door while the ghosts arrive."),
    OTHER,
    "### Gengar and the Dark Box",
    ("dark-classic.html", ["gengar-smile", "weezing"],
     "The original Gengar Gang, and the non-ex build. Nothing in it gives up"
     " more than one Prize. The dark duo of Gengar and Weezing, and the"
     " two-turn combo the whole deck is built around."),
    ("dark-mega.html", ["seviper", "gengar-mega"],
     "Ex-battle mode. Eleven cards swap Gengar Gang Classic into a prize"
     " cage. Mega Gengar ex zeroes every trade, and Seviper hits 240 while the"
     " wall takes the hits."),
    ("dark-curse.html", ["gengar-smile", "gengar-mega"],
     "The bigger plan, on hold until the Gnawing Curse pair is sourced. Two ex"
     " Gengars on one Haunter line; the Mega bends every prize trade, and the"
     " Curse taxes every Energy the opponent plays."),
    ("dark-dogs.html", ["okidogi", "gengar-smile"],
     "A Wednesday-night 60, the same box with the legal Gengar in it."
     " Okidogi ex hits 300 under a Binding Mochi, Gnawing Curse and Risky"
     " Ruins supply the chip that turns 300 into lethal, and the Prize tax"
     " makes their Mega cost three while your dog costs one."),
    ("dark-rocket.html", ["gengar-mega", "crobat"],
     "A game-night hybrid for when the other side brings ex. Mega Gengar ex"
     " taxes every Prize taken off a Darkness Pokémon, and Team Rocket's"
     " Crobat ex chips two Pokémon each time it comes down, then goes back to"
     " hand healed."),
    ("dark-smog.html", ["koffing", "weezing"],
     "The other game-night hybrid, for when you don't know what's coming."
     " Every Pokémon is a Koffing or a Weezing and none is an ex, so Team"
     " Rocket's Weezing hits 40 for each one in play and the opponent needs"
     " six knockouts whatever they bring."),
    "### Lanterns",
    ("psychic-lanterns.html", ["chandelure", "gourgeist"],
     "The first lantern deck. Mega Chandelure ex turns the opponent's own"
     " Retreat Cost into damage at the shop, and three card swaps turn the"
     " whole thing into the Night Parade at home."),
    ("flaming-lanterns.html", ["litwick", "chandelure"],
     "The meta lantern. Four Fire Chandelure read the opponent's hand while"
     " Mega Chandelure prices their exits; the archetype's tournament-winning"
     " shape, rebuilt from the binder for about two dollars."),
    ("phantom-toll.html", ["chandelure", "gengar-mega"],
     "The first two-color hybrid. Mega Chandelure makes leaving expensive and"
     " Mega Gengar makes losing cheap, while every gust drags something heavy"
     " into a toll booth it cannot afford to sit in."),
    ("phantom-tax.html", ["chandelure", "gengar"],
     "Phantom Toll, rebuilt off the TCG Live ladder. Wondrous Patch"
     " recharges the next lantern the turn the first one falls, a single-prize"
     " Gengar pays the opponent nothing, and Munkidori sends their counters"
     " home."),
    ("phantom-ferry.html", ["gengar-mega", "chandelure"],
     "A card-shop 60, built entirely from the box. Mega Gengar ex carries the"
     " Energy, Mega Chandelure ex collects the Prizes, and Okidogi ex holds"
     " the line against the Wednesday field."),
    "### Fire and Eevee",
    ("fire-tournament.html", ["flareon", "noctowl"],
     "The tournament take on Fire Force. Flareon ex, Noctowl, and why a Bench"
     " dad cannot touch changes how the whole game is played."),
    ("eevee-standard.html", ["eevee", "umbreon", "espeon", "glaceon"],
     "The Eevee deck, and the only one here that is two decks. Fifty cards"
     " never move; ten swap between Sun and Moon for home and Fire and Ice for"
     " game night."),
    "### Rockets, Steel, and Dragons",
    ("rocket-mewtwo.html", ["crobat", "mewtwo"],
     "A game-night deck. Team Rocket's Mewtwo ex swinging off a Spidops"
     " payroll, and a Crobat line that fixes a bad Active for free."),
    ("metal-excadrill.html", ["drilbur", "metagross"],
     "A Metal deck, bought from zero. One Beldum line feeds both the Energy"
     " engine and a Metagross that hits for 330 and gives up a single Prize;"
     " the Mega only comes out to close."),
    ("steel-wolves.html", ["metagross", "snorlax"],
     "An online 60 for TCG Live. Three separate cards each add 30 to Hop's"
     " Zacian ex, so Brave Slash lands at 330 and one-shots Dragapult; a"
     " Metagross on the Bench pays for it, and Zamazenta covers the turn"
     " Zacian is locked out."),
    ("dragons.html", ["giratina-origin", "clefairy"],
     "A Dragapult deck, rebuilt from the card that beat dad. Four Drakloaks"
     " draw every turn, Sparkling Crystal makes Phantom Dive cost one Energy,"
     " and Lillie's Clefairy ex turns the mirror into a Fairy Zone."),
]


def read(name):
    """(title, card count) straight from a built page.

    Counting every <article> overstated it: on a deck page the word list and
    the game plans are articles too, which had fire.html claiming 38 unique
    cards for a 20-card list. A real card page is the one carrying a stat
    block, so that is what gets counted.
    """
    html = (ROOT / name).read_text(encoding="utf-8")
    title = re.search(r"<title>(.*?)</title>", html, re.S).group(1)
    # split on the tag name, not on "<article>": the collection's articles
    # carry the filter values as attributes, and matching the bare tag counted
    # every one of them as zero
    cards = sum(1 for a in re.split(r"<article\b", html)[1:]
                if "How many" in (body := a.split("</article>")[0])
                or 'class="card"' in body)
    return title, cards


body, total = [], 0
level = 2   # a page title sits one level under the last heading, h2 before any
featured = True
for entry in PAGES:
    if isinstance(entry, str):
        featured = featured and entry != OTHER
        hashes, text = entry.split(" ", 1)
        body.append(f"\t\t\t<h{len(hashes)}>{esc(text)}</h{len(hashes)}>")
        level = len(hashes) + 1
        continue
    name, sprites, blurb = entry
    if not (ROOT / name).exists():
        print(f"  skipping {name}, not built yet")
        continue
    title, count = read(name)
    total += count
    art = ['\t\t\t<article class="index" data-featured>' if featured
           else '\t\t\t<article class="index">']
    # decorative, and the heading right beside them already names the page
    gifs = [s for s in sprites
            if (ROOT / "assets" / "sprites" / f"{s}.gif").exists()]
    if gifs:
        tags = "".join(f'<img src="./assets/sprites/{s}.gif" alt="" />'
                       for s in gifs)
        art.append(f"\t\t\t\t<aside data-sprite>{tags}</aside>")
    # the heading lives inside the section so the sprite can sit beside it
    # rather than being pushed under a full-width row
    art += [
        "\t\t\t\t<section>",
        f'\t\t\t\t\t<h{level}><a href="./{name}">{title}</a></h{level}>',
        f"\t\t\t\t\t<p>{esc(blurb)}</p>",
    ]
    # the planning docs have no card pages to count, so they get no count line
    # rather than an honest-looking "0 unique cards"
    if count:
        art.append(f"\t\t\t\t\t<p><small><em>{count} unique cards</em></small></p>")
    art += ["\t\t\t\t</section>", "\t\t\t</article>"]
    body += art

out = page(ROOT / "index.html", "Pokémon TCG",
           "Deck planning for me and my son.",
           "", "\n".join(body), CREDITS_NOTE, back="")
pages = sum(1 for e in PAGES if not isinstance(e, str))
print(f"index.html: {pages} pages, {total} cards linked, "
      f"{len(out.splitlines())} lines")
