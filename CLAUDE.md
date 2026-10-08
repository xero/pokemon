# CLAUDE.md

> [!NOTE]
> Operating notes for the data pipeline and site generator in this repo. The deeper docs live in [README.md](./README.md); this file is the working contract a session needs before touching anything. Nothing here is about the decks themselves.

---

## The data pipeline

```
add_cards.py --> product-ids.tsv --normalize_cards.py--> cards.csv + assets/*.jpg
pokemontcg.io --fetch_regulation.py--> regulation-marks.json --> the reg mark and legal columns
pokemontcg.io --fetch_legal_pool.py--> legal-cards-<epoch>.json --build_calc.py--> assets/calc/pool.json
decks.toml + the deck .md files --build.py--> the site
```

- **`product-ids.tsv` is the seed.** Everything else derives from it: a TCGplayer product id, the store URL, and an `owned` flag. Never invent a row by hand; it needs a product id, and `add_cards.py` is the lookup. The `#` lines at its top are its own notes.
- **Ownership is one flag, and it defaults to owned.** `owned` is `1` or `0`. There are no copy counts anywhere, nothing scrapes an order history, and nothing infers ownership from anything else. A card is on the pull list because someone marked it `0`, and for no other reason. Xero says when a card needs buying; `add_cards.py --need` records it and `--have` undoes it. Do not flip a flag on a guess.
- **`cards.csv` is generated.** Do not hand-edit it. Columns worth knowing: `name`, `set_name`, `card_number`, `card_text`, `attack1-4`, `regulation_mark`, `standard_legal`, `image_file`, `owned`, `source_url`. Card text in it comes from TCGplayer and is the authoritative text to quote in deck prose.
- **A card marked `0` still gets a full card block on deck pages.** It stays off the collection page and lands on the pull list.
- The collection mixes more than one person's cards. Owned means in the house, not in any one binder.

## The legal card pool

`legal-cards-<epoch>.json` is a snapshot of every Standard-legal card, pulled from pokemontcg.io. `python3 fetch_legal_pool.py` writes a fresh one. It takes a few minutes. The one thing in the build that reads it is `build_calc.py`, which takes the newest snapshot by epoch, so a fresh pull changes the damage calculator on the next build.

- **`cards.csv` is our cards; this is what exists.** Roughly 300 cards against roughly 3,000. Any question shaped like "what is legal that does X" has to be answered from here. Our cards are the wrong pool to search, and the answer is not reliably in anyone's memory.
- **The legal marks are H, I, and J**, as of the 2026 rotation. `LEGAL_MARKS` in the script is the one line to change when that moves.
- **The filename carries the fetch time because the answer expires.** Keep the old snapshots rather than replacing them; diffing two shows what a rotation took away.
- **It carries card text and the stats the calculator needs.** Every card keeps its `rules`, `abilities`, and `attacks`, so grepping card text is the intended use, plus `weaknesses`, `resistances`, and `evolvesFrom` since 2026-10-01. Snapshots older than that lack those three. Prices and image urls are stripped, and so is `convertedRetreatCost`, so "what is its Retreat Cost" still needs a live API pull. `FIELDS` in the script is where to widen it.
- **Upstream has typos.** 30th Celebration's Murkrow lists a Fighting Resistance of "×2". `build_calc.py` reports a value it can't read and leaves it off.
- The upstream API returns bare 502s in bursts and spells the supertype one way in the query and another in the response. The script already handles both, so reach for it instead of hitting the API by hand.

## Adding a card

1. `python3 add_cards.py "Name Set Words" -n 056/094` adds it as owned. Add `--need` when Xero says it has to be bought. The query must contain enough set words to disambiguate, and the number pins the printing. Both matter; the same number exists in multiple sets, and the same name exists at wildly different prices. `--japanese` searches the Japanese product line.
2. `python3 normalize_cards.py` fetches text and scans for new rows only (network: TCGplayer API and CDN), and carries every flag into `cards.csv`. Flipping a flag on a card it already has costs no network at all.
3. `python3 build.py`.

A TCGplayer product URL also works as the query and skips the search entirely. `--file` takes a batch, `query<TAB>number<TAB>need`, with the third column optional; write it to the scratchpad, not the repo. A new deck's cards are the usual batch.

- **TCGplayer's product name is the authority, and it is not always the printed name.** It is `Poke Pad`, not `Poké Pad`. Basic energy is `Basic Water Energy` in the API and `cards.csv` but `Water Energy` on the storefront. A card heading or deck-list row that guesses wrong resolves to nothing, silently.
- **Restocking a list is faster through [Mass Entry](https://www.tcgplayer.com/massentry) than the search.** Format is `qty Name [SET]` using the codes behind *Show Set/Series Codes*. Two things the docs get wrong for Pokémon: a trailing collector number does not work, and a card with more than one print in its set needs that number **inside the name** (`3 Mega Chandelure ex - 038/084 [PBL]`). One bad line discards the entire batch with nothing added.
- **Research shortlists do not go in the seed.** An energy-acceleration survey once seeded 40 candidates into the pipeline, and every page that touched the data read them as 40 things to go buy. Keep a survey in its own document. A card goes in the seed when a deck runs it or Xero owns it.

## The registry

`decks.toml` lists every page on the site, in the order the front page shows it, and it is the only place a page is registered. `decklib.py` is its one reader. Its header documents every key.

- **Publishing a deck is one entry.** `source`, `player` (`xero` or `fox`), `shelf` (`league`, `other`, or `opponent`), `group` for an other-shelf deck, `sprites`, `blurb`, and the heading sprites under `[deck.flavor]`. The deck builder, the front page, and the pull list all read it, so there is no second list to forget.
- **`[deck.companion]` hangs a generated page on a deck.** It takes `page`, `sprites`, and `blurb`, and the front page renders it as a second section inside the deck's own row, under a rule, with its title one level below the deck's. The calculator is the one companion; move the table with the deck if the calculator follows it to another list.
- **`draft = true` keeps a deck off the site.** No page, no front-page row, and the pull list names it without a link. A full build deletes a draft's leftover `.html`, because the Pages workflow publishes every `.html` in the repo. Delete the line to publish. A `.md` with no entry at all is a planning doc; the build names it if it contains a Qty table, since that is usually a deck someone forgot to register.
- **Shelves.** `league` holds the two decks we are sleeving now, Xero's first, and they are the only titles that carry our names ("Fox's", "Xero's"); every other deck's `# Title` drops the name. `opponent` holds models of the decks league regulars bring (Matt's Excadrill, Elliott's Garchomp, Steve's Dragapult); they are written from the pilot's chair so we know what the other side wants to do. The library pages lead with no heading, then League Decks, then Other Decks with a subheading per `group`, in the order the groups first appear, then Opponent Decks. Everything above Other Decks carries `data-featured`, which the template tints. Retiring a league deck means moving it to `shelf = "other"` with a group and taking the name off its title.
- **`[deck.flavor]` keys are exact heading text.** A reworded heading orphans its key and the build prints a warning naming it. Renaming a heading in a deck .md means updating its flavor key in the same change.
- Sprites render from `assets/sprites/` only; missing files skip silently. The full library is in `assets/ani/`; promote a sprite by copying it over. Gen 9 Pokémon are absent from the library.

## The pull list

`wishlist.html` is the one place buying lives. Deck pages carry no What To Buy section and no buy blocks; do not write either.

- **A card is on it when its `owned` flag is `0`.** Nothing else puts it there.
- **How many to buy comes from the deck lists**, the Qty tables in each registered deck, drafts included, and it is one deck per player: the largest ask among Xero's decks plus the largest among Fox's. Each of us sleeves one deck at a time, but both get sleeved on the same night. A flagged card no deck lists shows as wanted by no deck.
- **Never hand-write ownership or copy counts in deck prose.** They go stale the day they are written, which is the whole reason the counts were retired.

## The build

```sh
python3 build.py            # rebuild every generated page
python3 build.py --check    # rebuild, then fail if the result differs from git
python3 build.py --data     # re-fetch cards.csv first
```

- **Run `build.py`, never the builders individually.** `build_index.py` reads the finished pages back off disk to count the cards on each, so it runs last.
- **`assets/template.html` has an `@media print` block, and it is load-bearing.** The screen type scale is `vw` clamps that resolve against the sheet and arrive oversized, the dark-mode block has no print guard, and browsers drop backgrounds. Anything that encodes meaning in a fill needs an explicit print rule; the table headers and the `[data-count]` badge already have one.
- **Every generated file is committed.** `--check` on a clean tree is the regression test. No workflow runs it, so run it before committing a builder change. After changing a builder, a deck .md, or `decks.toml`, run a build before committing or the commit is stale.
- Generated: `collection.html`, `wishlist.html`, every deck page, `credits.html`, `collection.md`, `calc.html`, `assets/calc/pool.json`, `index.html`. Hand-written: the deck `.md` files, `decks.toml`, `calc.toml`, `assets/calc/calc.js` and `calc.css`, `product-ids.tsv` through `add_cards.py`, the Python. (`deck-registration.html` is a hand-made Worlds Celebration sheet, not part of the build.) Neither: `logs/`, the TCG Live battle logs the tcg-log skill (`.claude/skills/tcg-log/`) archives, which is gitignored. Xero drops raw logs there under any name, and the skill's `save` renames them.

## The damage calculator

`calc.html` is a phone-first form for Lucky Haunt: pick the opponent's Pokémon, say what is on it, and each of the deck's five attackers shows its damage and whether it Knocks Out. It is for planning a matchup before the game, never during one: Play! Pokémon rules don't allow phones during league play, and the page's subtitle says so. `build_calc.py` writes the page and `assets/calc/pool.json`; `assets/calc/calc.js` and `calc.css` are hand-written and only this page loads them. It is Lucky Haunt's `[deck.companion]` in `decks.toml`, so the front page lists it as a second section inside that deck's row rather than as a row of its own.

- **The attackers come from the deck, never from the code.** `ATTACKERS` in the builder names each one and the attack it is there for; the deck list in dark-lucky.md pins the printing and `cards.csv` supplies the cost and damage. Okidogi ex shows only *Chain-Crazed*, with a Poisoned switch that starts on, because that is what Xero asked for. The icons are `assets/calc/<key>.png`.
- **Card text becomes effects at build time.** Abilities and "during your opponent's next turn" attacks are read by patterns in `read_sentence()`. A sentence that sounds like it should matter and matched nothing is printed as a build warning, so a new set's wording shows up as a line in the build rather than a wrong number on the page. `python3 build_calc.py --review` prints every attack sentence that fell back to a plain callout too. Board-wide Abilities (Rabsca, Bronzong, Gastrodon) are written by hand in `BY_HAND`, and so are Tools, Stadiums, and Special Energy in `TOOLS`, `STADIUMS`, and `ENERGIES`; an empty list puts a card in the menu's "Nothing to your attacks" group.
- **Anything that reaches your Bench gets a red warning**, attacks and Abilities alike: a snipe like *Phantom Dive*, a spread like *Wide Blast*, or every Pokémon you have like *Hail*. `reach()` reads it from the card text and `second_person()` turns the sentence to face you, swapping both sides so Munkidori's "from 1 of your Pokémon to 1 of your opponent's Pokémon" reads "from 1 of their Pokémon to 1 of your Pokémon". A sentence that only counts your Bench for its own damage, like *Mind Jack*, is left out.
- **Effects carry condition tokens** (`atk:ex`, `tgt:bench`, `dmg:>=240`), and `test()` in calc.js reads them. An unknown token is false, so a token the builder learns first switches its effect off, not on. A new token needs a case in both files.
- **`calc.toml` holds what card text can't say: what to do about it.** Each note is seeded from dark-lucky.md's Cards to Watch Out For and links back to it. **A note never claims what lands or what Knocks Out.** A note can't see the board, and "Pain still lands" on Crustle sat beside a table saying Mist Energy blocked it. The calculator says what gets through in one summary line built from every attacker's actual result, and each effect's line says only what that effect stops. Hang a note on `abilities` rather than `cards` when only some prints of a name carry the Ability (Banette, Sylveon, Crustle). A name the pool lacks prints a warning and is skipped. When the Watch Out table changes, change the note in the same commit.
- **Images load from Scrydex by card id** (`images.scrydex.com/pokemon/<id>/medium`), the same host pokemontcg.io's own image field points at. None are in the repo, and no header is needed: an `<img>` from another origin needs no CORS.
- **The template's `${HEAD}` slot exists for this page's stylesheet.** Its line drops out when empty, like `${SCRIPT}`, so no other page changes. Script, stylesheet, and pool URLs carry a `?v=` hash of the file, so a phone never runs new HTML against a cached old script.
- **It saves the form to `localStorage`**, because Android discards background tabs. Clear resets the opponent's Pokémon and what is on it, and leaves the Stadium, the attacker, and the Poisoned switch alone.

## The deck simulator

`tools/dark_gang_sim.py` plays dark-gang.md's list against three opponent models and counts how often the deck attacks: its first attack by turn 3, an attack the turn after losing the Active, stranded turns, and dry turns. `--vs "Label=Card:+1,Card:-1"` compares a variant against the committed list, and `--cards` lists the card keys. The docstring covers the metrics and the models.

- **Read it as relative.** Compare variants to each other, never to a real win rate.
- **It can't see durability or disruption.** Its opponent KOs whatever it targets, so tanky lines score low. Boss's Orders, Risky Ruins, and Hero's Cape do nothing in it, so cutting them looks free.
- **Its list is hard-coded.** `BASE` is dark-gang.md at `df7ccfe`; update it when the Qty tables change. Nothing in the build reads it.
- **`tools/lucky_sim.py` runs dark-lucky.md's list through it, one decision at a time.** `order` tests what the board builds first, and `call` tests Call for Family's first two picks; Lucky Haunt's Build order section cites it. It subclasses the simulator through two hooks, `Game.cff_pick()` and `run(game=...)`. Its `LUCKY` list is hard-coded too, and it adds a blind spot of its own: the simulator barely uses *Happy Switch*, so it sees what building Blissey costs, not what Blissey gives back.

## Deck page markdown contract

`build_deck_html.py` parses a known shape, not general markdown. Breaking the shape fails quietly, so follow it exactly.

- **Every deck page uses one shape now, dark-classic.md's.** Group headings at `#` level in this order: `# Pokémon`, `# Trainers — Supporters`, `# Trainers — Items`, `# Trainers — Tool & Stadium`, `# Energy`, `# Game Plans`; one `###` card section per card under the card groups, `## N. Name` plans under Game Plans. Narrative sections (`## The Thesis`, `## Versus ...`, `## Alternatives`) stay at `##` anywhere. The contents nav nests a `##` under the group above it only when it starts with a number (`3. The Bench Tax`, `Reason 1: ...`); every other `##` gets its own linked row. A numbered `###` (`2. Take a turn`) is likewise indexed under its `##` section; an unnumbered prose `###` stays out of the nav unless a table follows it directly.
- **Card headings are the card's name and nothing else**: `### Ultra Ball`. A matching row in `cards.csv` auto-renders the scan, stat table, and legality badge, and the badge carries the regulation mark, so the heading does not. No row, no card block, silently. Add the card to the pipeline first.
- **The deck list pins the printing, not the heading.** `deck_printings()` reads the Card, Set, and Number columns off every `Qty` table, and that is how a bare `### Switch` resolves to one of four printings. A card no `Qty` table lists falls through to the set words in the heading's parens, which is what the alternatives and swap sections rely on.
- **Set words go in the heading only when a deck runs two printings of one card**: `### Eevee (Prismatic Evolutions · H)`. The parens hold set words, the regulation mark, or both, separated by a middot. Adding them where the name is already unique is noise; the stat table prints the set either way.
- **Deck list tables** whose first header cell is `Qty` feed the count badges on card headings and the pull list's counts. Card numbers in those tables must be bare (`056`), not `056/094`; the parser fullmatches 2-3 digits.
- **`deck_counts()` overwrites, so the last `Qty` table wins.** It scans *every* table whose first header cell is `Qty`, and so does the pull list's `decklib.qty_rows()`. Two tables listing the same card at different counts silently render the wrong badge and the wrong buy count. Keep one canonical set of Qty tables per page and express variants under a different header (`| Out | In |`), which both parsers ignore.
- **The deck list strip is generated, and it reads whichever shape the page has.** `deck_list()` builds one full-width `[data-decklist]` article of 150px scans, one per distinct card, badged with the count where the deck runs more than one. Qty tables feed it, using the Card, Set, and Number columns to pin the printing; it also reads each card page's `<img>` and its `Qty` or `How many` row, and dedupes the two on the scan path. A `###` block only counts as a card if its table carries a `Set` row. The strip lands directly above the first `# Pokémon` heading or `**Pokémon (N)**` label, and gets its own heading only in the first case, since the planning docs already sit under one. A row with no set (a flex slot) is skipped; anything else that fails to resolve prints a warning naming the card. Each thumbnail links to the card's own `###` section, matched on the heading text with and without its parens; a card with no section on the page stays a plain image.
- **An `<img>` on its own line directly after a table renders beside it**: the pair share a `[data-beside]` flex row, image on the right at a quarter width, dropping below the table on a phone and out of print entirely. A card scan never triggers this, because scans sit above their table.
- A `###` directly under the page `# Title` is the subtitle, not a card.
- The `> ### Table of Contents` blockquote is discarded and rebuilt from headings in the HTML, but keep it accurate in the .md for GitHub readers.
- `./file.md` links are rewritten to `.html` when `decks.toml` publishes that page, so always link the `.md`. A link to a draft or a planning doc stays `.md`.

## Gotchas

- **Regulation marks are per card, not per set.** One set can print reg G and reg H cards side by side. Trust `regulation_mark` in `cards.csv`, never the set.
- **Japanese prints are tracked but flagged** (`standard_legal` = `japanese`); the deck pages label them "not legal in the US." Do not count them toward a tournament list.
- Both Mega starter sets are 21 cards, so `011/021` alone is ambiguous; set words in the query break the tie.
- Basic energy uses short numbers in `cards.csv` (`7`, not `007`); deck lists written as `007` still resolve.
- There is a form on the repo's GitHub Actions tab that runs add, normalize, and build remotely: a card, a number, and two checkboxes, need and japanese. Useful when local network access is the blocker.
