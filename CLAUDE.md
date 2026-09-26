# CLAUDE.md

> [!NOTE]
> Operating notes for the data pipeline and site generator in this repo. The deeper docs live in [README.md](./README.md); this file is the working contract a session needs before touching anything. Nothing here is about the decks themselves.

---

## The data pipeline

```
add_cards.py --> product-ids.tsv --normalize_cards.py--> cards.csv + assets/*.jpg
pokemontcg.io --fetch_regulation.py--> regulation-marks.json --> the reg mark and legal columns
decks.toml + the deck .md files --build.py--> the site
```

- **`product-ids.tsv` is the seed.** Everything else derives from it: a TCGplayer product id, the store URL, and an `owned` flag. Never invent a row by hand; it needs a product id, and `add_cards.py` is the lookup. The `#` lines at its top are its own notes.
- **Ownership is one flag, and it defaults to owned.** `owned` is `1` or `0`. There are no copy counts anywhere, nothing scrapes an order history, and nothing infers ownership from anything else. A card is on the pull list because someone marked it `0`, and for no other reason. Xero says when a card needs buying; `add_cards.py --need` records it and `--have` undoes it. Do not flip a flag on a guess.
- **`cards.csv` is generated.** Do not hand-edit it. Columns worth knowing: `name`, `set_name`, `card_number`, `card_text`, `attack1-4`, `regulation_mark`, `standard_legal`, `image_file`, `owned`, `source_url`. Card text in it comes from TCGplayer and is the authoritative text to quote in deck prose.
- **A card marked `0` still gets a full card block on deck pages.** It stays off the collection page and lands on the pull list.
- The collection mixes more than one person's cards. Owned means in the house, not in any one binder.

## The legal card pool

`legal-cards-<epoch>.json` is a snapshot of every Standard-legal card, pulled from pokemontcg.io. `python3 fetch_legal_pool.py` writes a fresh one. It takes a few minutes, and nothing in the build reads the result.

- **`cards.csv` is our cards; this is what exists.** Roughly 300 cards against roughly 3,000. Any question shaped like "what is legal that does X" has to be answered from here. Our cards are the wrong pool to search, and the answer is not reliably in anyone's memory.
- **The legal marks are H, I, and J**, as of the 2026 rotation. `LEGAL_MARKS` in the script is the one line to change when that moves.
- **The filename carries the fetch time because the answer expires.** Keep the old snapshots rather than replacing them; diffing two shows what a rotation took away.
- **It carries card text, not card stats.** Every card keeps its `rules`, `abilities`, and `attacks`, so grepping card text is the intended use. Prices, ids, and image urls are stripped, and so are `weaknesses`, `convertedRetreatCost`, and `evolvesFrom`. "What does this hit for double", "what is its Retreat Cost", and "what does this evolve from" all need a live API pull. `FIELDS` in the script is where to widen it.
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

- **Publishing a deck is one entry.** `source`, `player` (`xero` or `fox`), `shelf`, `group` for an other-shelf deck, `sprites`, `blurb`, and the heading sprites under `[deck.flavor]`. The deck builder, the front page, and the pull list all read it, so there is no second list to forget.
- **`draft = true` keeps a deck off the site.** No page, no front-page row, and the pull list names it without a link. A full build deletes a draft's leftover `.html`, because the Pages workflow publishes every `.html` in the repo. Delete the line to publish. A `.md` with no entry at all is a planning doc; the build names it if it contains a Qty table, since that is usually a deck someone forgot to register.
- **Shelves.** `league` holds the two decks we are sleeving now, Xero's first, and they are the only titles that carry our names ("Fox's", "Xero's"); every other deck's `# Title` drops the name. The library pages lead with no heading, then League Decks, then Other Decks with a subheading per `group`, in the order the groups first appear. Everything above Other Decks carries `data-featured`, which the template tints. Retiring a league deck means moving it to `shelf = "other"` with a group and taking the name off its title.
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
- Generated: `collection.html`, `wishlist.html`, every deck page, `credits.html`, `collection.md`, `index.html`. Hand-written: the deck `.md` files, `decks.toml`, `product-ids.tsv` through `add_cards.py`, the Python. (`deck-registration.html` is a hand-made Worlds Celebration sheet, not part of the build.)

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
