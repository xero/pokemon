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
- **`quantity` 0 is a real value**: a card a deck plan wants but nobody owns. It still gets a full card block on deck pages and stays off the collection page. Hand-set quantities survive `scrape_quantities.py` re-runs.
- The collection mixes more than one person's cards. Check the memory notes before treating a quantity as "available."

## The legal card pool

`legal-cards-<epoch>.json` is a snapshot of every Standard-legal card, pulled from pokemontcg.io. `python3 fetch_legal_pool.py` writes a fresh one. It takes a few minutes, and nothing in the build reads the result.

- **`cards.csv` is what we own; this is what exists.** Roughly 200 cards against roughly 3,000. Any question shaped like "what is legal that does X" has to be answered from here. The collection is the wrong pool to search, and the answer is not reliably in anyone's memory.
- **The legal marks are H, I, and J**, as of the 2026 rotation. `LEGAL_MARKS` in the script is the one line to change when that moves.
- **The filename carries the fetch time because the answer expires.** Keep the old snapshots rather than replacing them; diffing two shows what a rotation took away.
- Every card keeps its `rules`, `abilities`, and `attacks`, so grepping card text is the intended use. Prices, ids, and image urls are stripped.
- The upstream API returns bare 502s in bursts and spells the supertype one way in the query and another in the response. The script already handles both, so reach for it instead of hitting the API by hand.

## Adding a card

1. Append to `wanted-cards.tsv`: `query<TAB>number<TAB>quantity<TAB>note`. The query must contain enough set words to disambiguate, and the number pins the printing (`056/094`). Both matter; the same number exists in multiple sets, and the same name exists at wildly different prices.
2. `python3 add_cards.py` (batch mode reads the tsv; existing rows report `have` and are safe to re-run). The word `japan` anywhere in the note switches the search to the Japanese product line.
3. `python3 normalize_cards.py` fetches text and scans for new rows only (network: TCGplayer API and CDN).
4. `python3 build.py`.

A TCGplayer product URL also works as the query and skips the search entirely.

## The build

```sh
python3 build.py            # rebuild every generated page
python3 build.py --check    # rebuild, then fail if the result differs from git
python3 build.py --data     # re-fetch cards.csv first
```

- **Run `build.py`, never the builders individually.** `build_index.py` reads finished pages back off disk, so order matters.
- **Every generated file is committed.** `--check` on a clean tree is the regression test; CI runs it. After changing a builder or a deck .md, run a build before committing or the commit is stale.
- Generated: `collection.html`, every `*-*.html` deck page, `credits.html`, `collection.md`, `index.html`. Hand-written: the deck `.md` files, the tsv files, the Python.

## Deck page markdown contract

`build_deck_html.py` parses a known shape, not general markdown. Breaking the shape fails quietly, so follow it exactly.

- **Card headings**: `### Name — Set Words 056 · Reg I`. The regex wants `Name — SetWords NNN`; a matching row in `cards.csv` auto-renders the scan, stat table, and legality badge. No row, no card block, silently. Add the card to the pipeline first.
- **Deck list tables** whose first header cell is `Qty` feed the count badges on card headings. Card numbers in those tables must be bare (`056`), not `056/094`; the parser fullmatches 2-3 digits.
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
