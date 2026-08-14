# pokemon decks

tcg deck planning for me and my son

- [caught pokemon](./collection.md)

## our starter decks

- [xero's gengar gang](./dark.md)
- [fox's fire force](./fire.md)

## future plans

- [xero's witching hour](./psychic-lanterns.md)
- [xero's long night](./psychic-sleep.md)
- [xero's lanterns reborn](./psychic-standard.md)
- [dark ex](./dark-ex.md)
- [fire standard](./fire-standard.md)
- [eevee standard](./eevee-standard.md)
- [fighting standard](./fighting-standard.md)

## building

```sh
python3 build.py            # rebuild every generated page
python3 build.py --check    # rebuild, then fail if the result differs from git
python3 build.py --data     # re-fetch cards.csv first, then build
```

run `build.py` rather than the builders under it. `build_index.py` reads the
finished pages back to count the cards on each one, so it has to run last, and
running them by hand in the wrong order has produced a wrong index twice.

everything generated is committed, so `--check` on a clean tree proves the html
still matches the sources it came from.

### adding a card

`add_cards.py` puts a card in `product-ids.tsv`. that file is the seed for
everything else, and it needs a tcgplayer product id, which is not something you
can work out from a card name. this looks it up.

```sh
python3 add_cards.py "Umbreon ex Prismatic Evolutions" -n 060/131 -q 2
python3 add_cards.py https://www.tcgplayer.com/product/94663/... -q 0
python3 add_cards.py                       # everything in wanted-cards.tsv
```

#### options

| flag | | what it does |
| :--- | :--- | :--- |
| `card` | | positional. a card name and its set, or a tcgplayer product url. leave it off to read the batch file instead. |
| `-n` | `--number` | the printed number, `060/131` or `060`. pins which printing. |
| `-q` | `--quantity` | how many you own. `0` for a card you want but have not bought. defaults to `0`. |
| | `--note` | why it is on the list. also picks the product line, see below. |
| `-f` | `--file` | a batch of cards, tab separated. defaults to `wanted-cards.tsv`. |
| | `--dry-run` | say what would change, write nothing. |

#### the three forms

**by name.** the name and set go in one string, and the words in it are matched
against the set name, so "Yanmega Vivid Voltage" is enough. this is a search, so
it can come back with more than one answer.

**by url.** paste any tcgplayer product link. the id is in the path, so this
skips the search entirely and is exact. everything after the id is ignored,
query string and all, so a copied address bar works as is.

**by file.** the batch form, tab separated, `#` comments and blank lines
skipped:

```
query<TAB>number<TAB>quantity<TAB>note

Umbreon ex Prismatic Evolutions   060/131   0   eevee-standard wants 2
Yanmega Vivid Voltage             007/185   2   charizard theme deck
```

#### pinning the printing

**use `-n` whenever a name has more than one print.** "Umbreon ex" matches both
the $2 double rare `060/131` and the special illustration rare `161/131`, and
picking the wrong one is an expensive mistake. without a number it refuses to
guess and shows you what it saw:

```
??    Umbreon ex Prismatic Evolutions
        ambiguous, pin it with --number. Saw: Umbreon ex - 161/131 (SV: Prismatic
        Evolutions), Umbreon ex - 060/131 (SV: Prismatic Evolutions), ...
```

a number on its own is still not always enough, so the set words in the query
break the tie. both mega starter sets are 21 cards, so `011/021` exists in each,
and matching on the number alone once put the gengar deck's ultra ball in the
diancie set.

#### quantity

`-q 0` is a real value, not a missing one. it means a deck plan wants this card
and we do not own it. the card still gets a full card page in the plans, with
its art, stats, and text, and it is left off the collection page entirely.

`scrape_quantities.py` leaves a row it knows nothing about alone, so a hand-set
quantity survives a re-run.

#### japanese cards

the search runs against one product line at a time, and **the word `japan`
anywhere in `--note` switches it** to the japanese one:

```sh
python3 add_cards.py "Ultra Ball MEGA Starter Set Mega Gengar ex" \
  -n 011/021 -q 4 --note "japan, mbg starter"
```

the url form needs no such hint. it asks both lines at once, since an id is
unique across them.

#### what it prints

| | |
| :--- | :--- |
| `add` | a new row went in |
| `have` | already in the seed, nothing done |
| `set` | quantity changed, with the old value and the new |
| `??` | not resolved. the reason is on the next line |

naming one card updates its quantity if the card is already there, because "add
this, i own 2" is a statement about today. the batch file only ever adds, so it
stays safe to re-run after appending a line.

#### afterwards

```sh
python3 normalize_cards.py   # pull the card text and scan
python3 build.py             # rebuild every page
```

`normalize_cards.py` only fetches what it does not already have, so adding one
card costs one request rather than a refetch of all 172.

there is also a **form on the actions tab** that runs all three and republishes
the site. it takes the same four fields.

## sources

every csv and image in here is fetched by a script, so it all rebuilds from
scratch. the poké ball at the top is the one exception.

**card data.** names, sets, numbers, rarity, types, hp, stage, attacks,
weakness, resistance, retreat cost, and card text all come from the
[tcgplayer](https://www.tcgplayer.com) marketplace search api, and the card
scans come from the tcgplayer cdn. `normalize_cards.py` pulls both and writes
`cards.csv`.

**what we own.** `product-ids.tsv` is the seed for everything else: a product
id, a url, and how many we own. the count is merged by `scrape_quantities.py`
from two places, because neither one knows the whole answer:

- **singles**, scraped from tcgplayer order history. that scrape stays out of
  the repo along with the raw api dumps. see `.gitignore`.
- **sealed products**, listed card by card in `sealed-contents.tsv`. order
  history knows we bought one theme deck; only a decklist knows it held 18 fire
  energy.

a quantity of 0 means a card a deck plan wants but we do not own. it still gets
a full card page in the plans, and is left off the collection page entirely.

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

**mega evolution sigil.**
[poképédia](https://www.pokepedia.fr/Fichier:Symbole_M%C3%A9ga-%C3%89volution_LPZA.svg),
also zero-licence, kept at `assets/glyphs/mega-evolution.svg`. this one is
referenced as an svg rather than rendered to png, because it is a four-stop
gradient and imagemagick quietly drops the gradient and returns a black
silhouette.

**poké ball.** the title image is the app icon from
[HybridShivam/Pokemon](https://github.com/HybridShivam/Pokemon),
[icon-512x512.psd](https://github.com/HybridShivam/Pokemon/blob/master/assets/Others/app-icons/icon-512x512.psd),
flattened to png by hand into `assets/pokeball.png`. it is the one asset here no
script fetches.

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
