#!/usr/bin/env python3
"""Write credits.html, the attribution page for everything on these pages.

The content lives here rather than in a markdown source because it is a flat
list of "this came from there", with no headings, tables, or cards for a
converter to find. README.md carries the same list for anyone reading the repo.
"""
from pathlib import Path

from pokelib import HOME_NOTE, flair, page

ROOT = Path(__file__).parent

# (heading, sprite, [paragraph, ...]). Links are written inline; there are few
# enough that a link table would be more indirection than it saves. Every
# sprite is used once, and the pick is a joke about the section where there was
# one to make: koffing is round and sudowoodo stands there like a judge.
SOURCES = [
    ("Header and footer artwork", "gengar", [
        'The spooky forest Gengar, Haunter, and Gastly artwork in the banner'
        ' and footer of every page is by'
        ' <a href="https://www.artofpkm.com/illustrators/204/cards">Arai'
        ' Kiriko</a>.',
    ]),
    ("Card text and rulings", "haunter", [
        'The wording on every card, and the rulings for how it actually'
        ' behaves, come from <a href="https://pkmncards.com/">PkmnCards</a>,'
        ' <a href="https://www.tcgcollector.com/">TCG Collector</a>, and'
        ' <a href="https://bulbapedia.bulbagarden.net/">Bulbapedia</a>.',
        'Two Bulbapedia pages did most of the work:'
        ' <a href="https://bulbapedia.bulbagarden.net/wiki/Confused_(TCG)">'
        'Confused (TCG)</a>, because both decks lean on it, and'
        ' <a href="https://bulbapedia.bulbagarden.net/wiki/Gengar_(Perfect_Order_50)">'
        'Gengar (Perfect Order 50)</a>, for the exact text of Infinite Shadow.',
        'The awkward rules questions were settled by'
        ' <a href="https://www.justinbasil.com/guide/damage">JustinBasil</a> on'
        ' why damage counters ignore Weakness and every prevent-damage effect,'
        ' the <a href="https://compendium.pokegym.net/category/7-gameplay/retreating/">'
        'Pokégym Compendium</a> on retreating, and'
        ' <a href="https://bulbapedia.bulbagarden.net/wiki/Special_Conditions_(TCG)">'
        'Bulbapedia on Special Conditions</a> for how Sleep and Confusion'
        ' actually resolve.',
        'Deck lists and what people are really playing come from'
        ' <a href="https://limitlesstcg.com/">Limitless TCG</a> and the'
        ' <a href="https://www.pokemon.com/us/pokemon-tcg/">Pokémon.com card'
        ' database</a>. Full set lists, for checking a card exists before'
        ' planning around it, come from'
        ' <a href="https://www.serebii.net/card/">Serebii</a>. And'
        ' <a href="https://www.josephwriteranderson.com/blog/mega-gengar-ex-deck-list-and-guide">'
        "Joseph Writer Anderson's Mega Gengar ex guide</a> worked out how that"
        ' deck is actually piloted.',
    ]),
    ("Card data", "weezing", [
        'Names, sets, numbers, rarity, types, HP, stage, attacks, weakness,'
        ' resistance, retreat cost, and card text come from the'
        ' <a href="https://www.tcgplayer.com">TCGplayer</a> marketplace search'
        ' API. The card scans come from the TCGplayer CDN.',
    ]),
    ("Tournament legality", "sudowoodo", [
        'Regulation marks come from'
        ' <a href="https://pokemontcg.io">pokemontcg.io</a>, one lookup per'
        ' card rather than one per set. That distinction matters. Prismatic'
        ' Evolutions prints Flareon 013 with a G mark and Flareon ex 014 with'
        ' an H, so a set-level table would call rotated cards legal.',
        'The rotation rules behind the yes or no come from the'
        ' <a href="https://www.pokemon.com/us/pokemon-news/2026-pokemon-tcg-standard-format-rotation-announcement">'
        '2026 Standard rotation announcement</a> and'
        ' <a href="https://bulbapedia.bulbagarden.net/wiki/2026-27_Standard_format_%28TCG%29">'
        "Bulbapedia's 2026-27 Standard format page</a>.",
    ]),
    ("Set symbols, set logos, and rarity symbols", "gastly", [
        '<a href="https://pokesymbols.com">pokesymbols.com</a>, covering the'
        ' <a href="https://pokesymbols.com/tcg/rarities">rarities</a>,'
        ' <a href="https://pokesymbols.com/tcg/sets">English sets</a>, and'
        ' <a href="https://pokesymbols.com/tcg/japanese-sets">Japanese sets</a>.',
        'pokesymbols has no entry for the Halloween bundles, so the Pikachu'
        ' jack-o&#x27;-lantern stamp on the Trick or Trade cards comes from'
        ' <a href="https://dextcg.com">DexTCG</a> instead.',
    ]),
    ("Energy glyphs and the Mega sigil", "gengar-mega-shiny", [
        'The energy type symbols beside every cost, and the'
        ' <a href="https://www.pokepedia.fr/Fichier:Symbole_M%C3%A9ga-%C3%89volution_LPZA.svg">'
        'Mega sigil</a> beside a Mega card, are both zero-licence SVGs from'
        ' <a href="https://www.pokepedia.fr/">Poképédia</a>.',
    ]),
    ("Poké Ball", "koffing", [
        'The ball at the top of every page is the app icon from'
        ' <a href="https://github.com/HybridShivam/Pokemon">HybridShivam/Pokemon</a>.',
    ]),
    ("Sprites", "eevee", [
        'The animated sprites tucked into the headings are the 3D models from'
        ' <a href="https://pkparaiso.com">pkparaiso.com</a>, by way of'
        ' <a href="https://github.com/tdmalone/pokecss-media">tdmalone/pokecss-media</a>.',
    ]),
]

RIGHTS = [
    '\t\t\t<aside data-callout="important">',
    '\t\t\t\t<h2>We claim no ownership of any of it.'
    f'{flair(["charizard-mega-y"])}</h2>',
    '\t\t\t\t<p>Pokémon and all related names, characters, card text, card'
    ' images, set symbols, and type symbols are © Nintendo, Creatures Inc.,'
    ' and Game Freak. Pokémon and the Pokémon TCG are trademarks of Nintendo.'
    ' Every card image and every piece of card text reproduced here belongs'
    ' to them.</p>',
    '\t\t\t\t<p>Nothing on these pages is official, endorsed, or affiliated'
    ' with Nintendo, Creatures Inc., Game Freak, or The Pokémon Company. This'
    ' is an unofficial fan project made for a father and son to plan decks at'
    ' the kitchen table. No money changes hands and nothing is for sale.</p>',
    '\t\t\t\t<p>All rights remain reserved by the original artists.'
    ' <i>Thank you for sharing!</i></p>',
    '\t\t\t</aside>',
]

body = []
for heading, sprite, paras in SOURCES:
    body.append("\t\t\t<article>")
    body.append("\t\t\t\t<section>")
    body.append(f"\t\t\t\t\t<h2>{heading}{flair([sprite])}</h2>")
    body += [f"\t\t\t\t\t<p>{p}</p>" for p in paras]
    body.append("\t\t\t\t</section>")
    body.append("\t\t\t</article>")
body += RIGHTS

out = page(ROOT / "credits.html", "Credits",
           "Where the card text, images, and symbols came from.",
           "", "\n".join(body), HOME_NOTE)
print(f"credits.html: {len(SOURCES)} sources, {len(out.splitlines())} lines")
