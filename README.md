# pokemon decks

tcg deck planning for me and my son

- [caught pokemon](./collection.md)

## our starter decks

- [xero's gengar gang](./dark.md)
- [fox's fire force](./fire.md)

## future plans

- [xero's witching hour](./psychic-lanterns.md)
- [xero's long night](./psychic-sleep.md)
- [dark ex](./dark-ex.md)
- [fire standard](./fire-standard.md)
- [eevee standard](./eevee-standard.md)
- [fighting standard](./fighting-standard.md)

## sources

every csv and image in here is fetched by a script, so it all rebuilds from
scratch. the poké ball at the top is the one exception.

**card data.** names, sets, numbers, rarity, types, hp, stage, attacks,
weakness, resistance, retreat cost, and card text all come from the
[tcgplayer](https://www.tcgplayer.com) marketplace search api, and the card
scans come from the tcgplayer cdn. `normalize_cards.py` pulls both and writes
`cards.csv`.

**what we own.** `product-ids.tsv` is the seed for everything else. it is
scraped from tcgplayer order history, which stays out of the repo along with the
raw api dumps. see `.gitignore`.

**tournament legality.** regulation marks come from
[pokemontcg.io](https://pokemontcg.io), one lookup per card rather than per set.
that distinction matters: prismatic evolutions prints flareon 013 with a g mark
and flareon ex 014 with an h, so a set-level table would call rotated cards
legal. `fetch_regulation.py` caches the marks in `regulation-marks.json`. the
rotation rules behind the yes/no answer come from the
[2026 standard rotation announcement](https://www.pokemon.com/us/pokemon-news/2026-pokemon-tcg-standard-format-rotation-announcement)
and [bulbapedia's 2026-27 standard format page](https://bulbapedia.bulbagarden.net/wiki/2026-27_Standard_format_%28TCG%29).

**set symbols, set logos, and rarity symbols.**
[pokesymbols.com](https://pokesymbols.com), covering the
[rarities](https://pokesymbols.com/tcg/rarities),
[english sets](https://pokesymbols.com/tcg/sets), and
[japanese sets](https://pokesymbols.com/tcg/japanese-sets).
`fetch_symbols.py` downloads them into `assets/rarities`, `assets/sets`,
`assets/set-logos`, and `assets/sets-jp`, then builds the inverted `-dark`
copies that let the black line art survive github's dark theme.

**trick or trade stamp.** pokesymbols has no entry for the halloween bundles,
so the pikachu jack-o'-lantern stamp comes from
[dextcg](https://dextcg.com). same script fetches it.

**energy type glyphs.** zero-licence svgs kept in `assets/glyphs`. these are the
actual tcg energy symbols rather than video game type icons, so they need no
mapping: the file is named for the card type. `build_glyphs.py` sets the fill on
each and renders it to png in `assets/types`.

**the two static images.** both come from
[HybridShivam/Pokemon](https://github.com/HybridShivam/Pokemon) and are the only
assets here that no script fetches. `assets/pokeball.png` is that repo's app
icon, [icon-512x512.psd](https://github.com/HybridShivam/Pokemon/blob/master/assets/Others/app-icons/icon-512x512.psd),
flattened to png by hand; it heads this page and `collection.md`.
`assets/mega-evolution-sigil.png` is waiting on a mega card to mark.

### a note on rights

the pokémon trading card game, the card text, and the card images are property
of nintendo, creatures inc., and game freak. this is a personal fan project for
me and my kid, not affiliated with any of them.

the pokesymbols and dextcg graphics carry no license notice, and the
HybridShivam repo has no license file, which makes those assets
all-rights-reserved by default. fine for a family repo. worth sorting out before
anyone leans on this for anything public.

---

> [!IMPORTANT]
> **we claim no ownership of any of it.**
>
> pokémon and all related names, characters, card text, card images, set
> symbols, and type symbols are © nintendo, creatures inc., and game freak.
> pokémon and the pokémon tcg are trademarks of nintendo. every card image and
> every piece of card text reproduced here belongs to them.
>
> nothing in this repo is official, endorsed, or affiliated with nintendo,
> creatures inc., game freak, or the pokémon company. it is an unofficial fan
> project made for a father and son to plan decks at the kitchen table. no
> money changes hands and nothing is for sale.
