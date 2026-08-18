# CLAUDE.md

> [!NOTE]
> Operating notes for the data pipeline and site generator in this repo. The deeper docs live in [README.md](./README.md); this file is the working contract a session needs before touching anything. Nothing here is about the decks themselves.

---

## The data pipeline

```
wanted-cards.tsv --add_cards.py--> product-ids.tsv --normalize_cards.py--> cards.csv + assets/*.jpg
sealed-contents.tsv + tcgplayer order scrape --scrape_quantities.py--> quantities in product-ids.tsv
pokemontcg.io --fetch_regulation.py--> regulation-marks.json --> the reg mark and legal columns
```

- **`product-ids.tsv` is the seed.** Everything else derives from it. Never invent a row by hand; it needs a TCGplayer product id, and `add_cards.py` is the lookup.
- **`cards.csv` is generated.** Do not hand-edit it. Columns worth knowing: `name`, `set_name`, `card_number`, `card_text`, `attack1-4`, `regulation_mark`, `standard_legal`, `image_file`, `quantity`, `category`, `source_url`. Card text in it comes from TCGplayer and is the authoritative text to quote in deck prose.
- **`quantity` 0 is a real value**: a card a deck plan wants but nobody owns. It still gets a full card block on deck pages and stays off the collection page.
- **A hand-set quantity only survives `scrape_quantities.py` if the merge has never heard of the row.** Wishlist rows sitting at 0 are safe. Anything listed in `order-quantities.tsv` or `sealed-contents.tsv` gets recomputed as ordered plus sealed, and a hand edit there is silently overwritten on the next run. Correct the source tsv instead, or the edit will not survive.
- The collection mixes more than one person's cards. Check the memory notes before treating a quantity as "available."

## The legal card pool

`legal-cards-<epoch>.json` is a snapshot of every Standard-legal card, pulled from pokemontcg.io. `python3 fetch_legal_pool.py` writes a fresh one. It takes a few minutes, and nothing in the build reads the result.

- **`cards.csv` is what we own; this is what exists.** Roughly 200 cards against roughly 3,000. Any question shaped like "what is legal that does X" has to be answered from here. The collection is the wrong pool to search, and the answer is not reliably in anyone's memory.
- **The legal marks are H, I, and J**, as of the 2026 rotation. `LEGAL_MARKS` in the script is the one line to change when that moves.
- **The filename carries the fetch time because the answer expires.** Keep the old snapshots rather than replacing them; diffing two shows what a rotation took away.
- **It carries card text, not card stats.** Every card keeps its `rules`, `abilities`, and `attacks`, so grepping card text is the intended use. Prices, ids, and image urls are stripped, and so are `weaknesses`, `convertedRetreatCost`, and `evolvesFrom` — "what does this hit for double", "what is its Retreat Cost", and "what does this evolve from" all need a live API pull. `FIELDS` in the script is where to widen it.
- The upstream API returns bare 502s in bursts and spells the supertype one way in the query and another in the response. The script already handles both, so reach for it instead of hitting the API by hand.

## Adding a card

1. Append to `wanted-cards.tsv`: `query<TAB>number<TAB>quantity<TAB>note<TAB>kind`. **`kind` is the column that carries meaning, not the section header you happen to append under** — `deck`, `ordered`, `binder`, `reorder`, `reference`. Rows appended to the end of the old file inherited whatever heading was last, which filed a binder pull and a mail reorder under an energy-acceleration tier list. `add_cards.py` slices the first four fields, so it ignores `kind`.
   A row is spent once it has been looked up: the product id is in `product-ids.tsv` and the card is in `cards.csv`, and those two are the record of what we own. The file holds what we *want*, so a row whose card has arrived comes out rather than being re-filed as owned. The query must contain enough set words to disambiguate, and the number pins the printing (`056/094`). Both matter; the same number exists in multiple sets, and the same name exists at wildly different prices.
2. `python3 add_cards.py` (batch mode reads the tsv; existing rows report `have` and are safe to re-run). The word `japan` anywhere in the note switches the search to the Japanese product line.
3. `python3 normalize_cards.py` fetches text and scans for new rows only (network: TCGplayer API and CDN).
4. `python3 build.py`.

A TCGplayer product URL also works as the query and skips the search entirely.

- **TCGplayer's product name is the authority, and it is not always the printed name.** It is `Poke Pad`, not `Poké Pad`. Basic energy is `Basic Water Energy` in the API and `cards.csv` but `Water Energy` on the storefront. A buy block or card heading that guesses wrong resolves to nothing, silently.
- **Restocking a list is faster through [Mass Entry](https://www.tcgplayer.com/massentry) than the search.** Format is `qty Name [SET]` using the codes behind *Show Set/Series Codes*. Two things the docs get wrong for Pokémon: a trailing collector number does not work, and a card with more than one print in its set needs that number **inside the name** (`3 Mega Chandelure ex - 038/084 [PBL]`). One bad line discards the entire batch with nothing added.

## The build

```sh
python3 build.py            # rebuild every generated page
python3 build.py --check    # rebuild, then fail if the result differs from git
python3 build.py --data     # re-fetch cards.csv first
```

- **Adding a deck page takes two edits.** `DECKS` in `build_deck_html.py` builds it; `PAGES` in `build_index.py` links it. They are separate lists, so missing the second gives you a page nothing points at. A new page also wants a `MASCOT` pair and `FLAVOR` keys.
- **Run `build.py`, never the builders individually.** Two steps read finished pages back off disk, so order matters: `build_index.py` counts the cards on each page, and `build_wishlist.py` only links a deck whose `.html` already exists — run it early and a newly added deck is plain text on the first build and a link on the second.
- **`assets/template.html` has an `@media print` block, and it is load-bearing.** The screen type scale is `vw` clamps that resolve against the sheet and arrive oversized, the dark-mode block has no print guard, and browsers drop backgrounds. Anything that encodes meaning in a fill needs an explicit print rule; the table headers and the `[data-count]` badge already have one.
- **Every generated file is committed.** `--check` on a clean tree is the regression test; CI runs it. After changing a builder or a deck .md, run a build before committing or the commit is stale.
- Generated: `collection.html`, `wishlist.html`, every `*-*.html` deck page, `credits.html`, `collection.md`, `index.html`. Hand-written: the deck `.md` files, the tsv files, the Python. (`buy-list.html` is a hand-made print sheet with base64 art, not part of the build.)
- **Research shortlists do not go in the tsv files.** An energy-acceleration survey once seeded 40 candidates into `wanted-cards.tsv`, and every page that touched the data read them as 40 things to go buy. They were purged from `product-ids.tsv` and `cards.csv`; the 6 that decks actually run stayed. Their 34 scans are still in `assets/`, unreferenced. Keep a survey in its own document, not in the seed.
- **`wishlist.html` is the pull list, and it is buy blocks only.** A row exists when a deck's ```buy block asks for more than `cards.csv` owns; Need sums across decks, because both decks stay sleeved. `quantity` 0 is deliberately *not* a source: most of those rows are a shortlist, not a shopping list — one energy-acceleration survey seeded 35 candidates at once. The reason any card entered the pipeline is the note column of `wanted-cards.tsv`, and nothing carries it into `cards.csv`.
- **A buy block's first column is the card *name*.** `find_card` matches it against the name, so repeating the set words there (`Mega Gengar ex Phantasmal Flames | Phantasmal Flames 056`) resolves to nothing and costs the line at zero, silently.

## Deck page markdown contract

`build_deck_html.py` parses a known shape, not general markdown. Breaking the shape fails quietly, so follow it exactly.

- **Every deck page uses one shape now, dark.md's.** Group headings at `#` level in this order: `# Pokémon`, `# Trainers — Supporters`, `# Trainers — Items`, `# Trainers — Tool & Stadium`, `# Energy`, `# Game Plans`; one `###` card section per card under the card groups, `## N. Name` plans under Game Plans. Narrative sections (`## The Thesis`, `## Versus ...`, `## What To Buy`) stay at `##` anywhere. The contents nav nests a `##` under the group above it only when it starts with a number (`3. The Bench Tax`, `Reason 1: ...`); every other `##` gets its own linked row.
- **`## What To Buy` renders collapsed**: the builder wraps that section in a closed `<details>` with the heading as the `<summary>`; print CSS forces it open so the shopping list still prints.
- **Card headings are the card's name and nothing else**: `### Ultra Ball`. A matching row in `cards.csv` auto-renders the scan, stat table, and legality badge, and the badge now carries the regulation mark, so the heading does not. No row, no card block, silently. Add the card to the pipeline first.
- **The deck list pins the printing, not the heading.** `deck_printings()` reads the Card, Set, and Number columns off every `Qty` table, and that is how a bare `### Switch` resolves to one of four printings. A card no `Qty` table lists falls through to the set words in the heading's parens, which is what the alternatives and swap sections rely on.
- **Set words go in the heading only when a deck runs two printings of one card**: `### Eevee (Prismatic Evolutions · H)`. The parens hold set words, the regulation mark, or both, separated by a middot. Adding them where the name is already unique is noise; the stat table prints the set either way.
- **Deck list tables** whose first header cell is `Qty` feed the count badges on card headings. Card numbers in those tables must be bare (`056`), not `056/094`; the parser fullmatches 2-3 digits.
- **`deck_counts()` overwrites, so the last `Qty` table wins.** It scans *every* table whose first header cell is `Qty`. Two tables listing the same card at different counts silently render the wrong badge. Keep one canonical set of Qty tables per page and express variants under a different header (`| Out | In |`), which the parser ignores.
- **The deck list strip is generated, and it reads whichever shape the page has.** `deck_list()` builds one full-width `[data-decklist]` article of 150px scans, one per distinct card, badged with the count where the deck runs more than one. Qty tables feed it, using the Card, Set, and Number columns to pin the printing; it also reads each card page's `<img>` and its `Qty` or `How many` row, and dedupes the two on the scan path. Every deck page carries Qty tables now, but the card-page path is still what resolves a card no table lists. A `###` block only counts as a card if its table carries a `Set` row. The strip lands directly above the first `# Pokémon` heading or `**Pokémon (N)**` label, and gets its own heading only in the first case, since the planning docs already sit under one. A row with no set, like fire-standard's flex slots, is skipped; anything else that fails to resolve prints a warning naming the card.
- **Buy blocks**: fenced ` ```buy ` with lines `query | Set Words NNN | need | note`. Own is looked up live from `cards.csv`, Buy is `max(0, need - own)`. Never hand-write ownership counts in prose tables; they go stale, and the buy block exists so they cannot.
- A `###` directly under the page `# Title` is the subtitle, not a card.
- The `> ### Table of Contents` blockquote is discarded and rebuilt from headings in the HTML, but keep it accurate in the .md for GitHub readers.
- `./file.md` links are rewritten to `.html` in the built page when the built page exists, so always link the `.md`.

## Sprites and flavor

- `MASCOT` and `FLAVOR` dicts at the top of `build_deck_html.py` attach gifs to pages and headings. `FLAVOR` keys are **exact heading text**; a reworded heading orphans its key and the build prints a warning naming it. Renaming a heading in a deck .md means updating the dict in the same change.
- Sprites render from `assets/sprites/` only; missing files skip silently. The full library sits untracked in `assets/ani/`; promote a sprite by copying it over. Gen 9 Pokémon are absent from the library.

## Gotchas

- **Regulation marks are per card, not per set.** One set can print reg G and reg H cards side by side. Trust `regulation_mark` in `cards.csv`, never the set.
- **Japanese prints are tracked but flagged** (`standard_legal` = `japanese`); the deck pages label them "not legal in the US." Do not count them toward a tournament list.
- Both Mega starter sets are 21 cards, so `011/021` alone is ambiguous; set words in the query break the tie.
- Basic energy uses short numbers in `cards.csv` (`7`, not `007`); buy blocks written as `007` still resolve.
- There is a form on the repo's GitHub Actions tab that runs add, normalize, and build remotely; useful when local network access is the blocker.
