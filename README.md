# pokemon decks

tcg deck planning for me and my son

- [caught pokemon](./collection.md)
- [table rules](./rules.md)

## our decks

- [xero's gengar gang](./dark-gang.md)
- [fox's fire force](./fire.md)

## other decks

### gengar and the dark box

- [gengar gang classic](./dark-classic.md), the non-ex build
- [snake charmer](./dark-mega.md)
- [curse toll](./dark-curse.md)
- [gengar's guard dogs](./dark-dogs.md)
- [shadow syndicate](./dark-rocket.md)
- [smog signals](./dark-smog.md)

### lanterns

- [psychic lanterns](./psychic-lanterns.md)
- [flaming lanterns](./flaming-lanterns.md)
- [phantom toll](./phantom-toll.md)
- [phantom tax](./phantom-tax.md)
- [phantom ferry](./phantom-ferry.md)

### fire and eevee

- [flareon engine](./fire-tournament.md)
- [rainbow dna](./eevee-standard.md)

### rockets and steel

- [hostile takeover](./rocket-mewtwo.md)
- [steel wolves](./steel-wolves.md)

## opponent decks

models of what the league regulars bring

- [iron excavation](./metal-excadrill.md), matt's excadrill
- [champion's call](./cynthia-garchomp.md), elliot's garchomp
- [crystal dragons](./dragons.md), steve's dragapult

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

### the registry

`decks.toml` is the one list of what is on the site, in the order the front
page shows it: the library pages first, then the league decks, then every other
deck under its group, then the opponent decks. a deck's entry says whose it is, which shelf it sits on,
its sprites, its front-page blurb, and the corner sprites on its headings.

a deck goes live by getting an entry. `draft = true` keeps it off the site: no
page, no front-page row, and the pull list names it without a link. a full build
deletes any page a draft left behind, because the site publishes every html file
in the repo. markdown with no entry at all is a planning doc, and the build
leaves it alone, naming it if it has a deck list in it.

### adding a card

`add_cards.py` puts a card in `product-ids.tsv`, the seed for everything else.
every card needs a tcgplayer product id, which is not something you can work out
from a card name, so this looks it up.

```sh
python3 add_cards.py "Umbreon ex Prismatic Evolutions" -n 060/131
python3 add_cards.py "Umbreon ex Prismatic Evolutions" -n 060/131 --need
python3 add_cards.py https://www.tcgplayer.com/product/94663/... --have
python3 add_cards.py --file new-deck.tsv
```

#### options

| flag | | what it does |
| :--- | :--- | :--- |
| `card` | | positional. a card name and its set, or a tcgplayer product url. |
| `-n` | `--number` | the printed number, `060/131` or `060`. pins which printing. |
| | `--need` | not owned. adds the card to the pull list, or flips one already in the seed. |
| | `--have` | owned. takes the card off the pull list. |
| `-j` | `--japanese` | search the japanese product line. |
| `-f` | `--file` | a batch of cards, tab separated. |
| | `--dry-run` | say what would change, write nothing. |

#### owned, and the pull list

every card is owned unless someone says otherwise. that is the whole model:
one flag per card, `1` or `0`, and nothing counts copies or scrapes an order
history. `--need` sets the flag to `0`, which puts the card on
[the pull list](./wishlist.html) with the decks that run it and how many to
buy. `--have` sets it back once the card is in the binder.

how many to buy comes from the decks' own lists, one deck per player. i sleeve
one of my decks and fox sleeves one of his, so four of a card in two of my decks
is four, while four in mine and four in his is eight.

#### the three forms

**by name.** the name and set go in one string, and the words in it are matched
against the set name, so "Yanmega Vivid Voltage" is enough. this is a search, so
it can come back with more than one answer.

**by url.** paste any tcgplayer product link. the id is in the path, so this
skips the search entirely and is exact. everything after the id is ignored,
query string and all, so a copied address bar works as is.

**by file.** the batch form, tab separated, `#` comments and blank lines
skipped. the third column is optional and takes `need` or `have`, the same as
the flags:

```
query<TAB>number<TAB>need

Umbreon ex Prismatic Evolutions   060/131   need
Yanmega Vivid Voltage             007/185
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

#### japanese cards

the search runs against one product line at a time, and **`--japanese`
switches it** to the japanese one:

```sh
python3 add_cards.py --japanese "Ultra Ball MEGA Starter Set Mega Gengar ex" -n 011/021
```

the url form needs no such hint. it asks both lines at once, since an id is
unique across them.

#### what it prints

| | |
| :--- | :--- |
| `add` | a new row went in, owned |
| `want` | a new row went in not owned, or an owned one flipped to the pull list |
| `got` | flipped back to owned |
| `same` | already in the seed, nothing changed |
| `??` | not resolved. the reason is on the next line |

#### afterwards

```sh
python3 normalize_cards.py   # pull the card text and scan, carry the flag over
python3 build.py             # rebuild every page
```

`normalize_cards.py` only fetches what it does not already have, so adding one
card costs one request rather than a refetch of all of them, and flipping a flag
costs none.

there is also a **form on the actions tab** that runs all three and republishes
the site. it takes a card, a number, and two checkboxes: need, and japanese.

## sources

every csv and image in here is fetched by a script, so it all rebuilds from
scratch. the poké ball at the top is the one exception.

**header and footer artwork.** the spooky forest gengar, haunter, and gastly
artwork in every page's banner and footer is by
[arai kiriko](https://www.artofpkm.com/illustrators/204/cards).

**card data.** names, sets, numbers, rarity, types, hp, stage, attacks,
weakness, resistance, retreat cost, and card text all come from the
[tcgplayer](https://www.tcgplayer.com) marketplace search api, and the card
scans come from the tcgplayer cdn. `normalize_cards.py` pulls both and writes
`cards.csv`.

**what we own.** one flag per card in `product-ids.tsv`, set by hand through
`add_cards.py`. every card is owned unless it is marked otherwise, and the
marked ones are the pull list. there used to be copy counts here, merged from a
scrape of tcgplayer order history and a card-by-card list of every sealed
product, and they were retired in september 2026 because they never matched the
binders.

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

**energy glyphs and the mega sigil.** both from
[poképédia](https://www.pokepedia.fr/), zero-licence svgs kept in
`assets/glyphs`. the energy set are the actual tcg energy symbols rather than
video game type icons, so they need no mapping: the file is named for the card
type, and `build_glyphs.py` sets the fill on each and renders it to png in
`assets/types`. the
[mega sigil](https://www.pokepedia.fr/Fichier:Symbole_M%C3%A9ga-%C3%89volution_LPZA.svg)
stays referenced as an svg rather than rendered to png, because it is a
four-stop gradient and imagemagick quietly drops the gradient and returns a
black silhouette.

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
