---
name: tcg-deck
description: Xero's procedure for building a Pokémon TCG deck (paper, 60-card) around a given core card or cards. Invoked as `/tcg-deck <tourney|home> deck based on <core card> [from <set>] [restrictions]`. Use this skill whenever the task is to construct, brew, or design a Pokémon deck starting from one or more specific cards — not to copy a meta list. Triggers on any request to build a deck "around", "based on", or "for" a named Pokémon card, or any Pokémon deck-building request that names a centerpiece card, whether the user says "deck" explicitly or just hands over a card and a play context. This is construction from a card, not selection of a top-tier list.
---

# TCG Deck — Build a Pokémon deck around a core card

This skill builds a 60-card paper Pokémon TCG deck **outward from a core card**, the way a builder does it — not by copying a tournament list. The distinction matters: meta-chasing is *selection* (find the best-performing 60 and clone it); this is *construction* (start from a card's text, derive how it wins, and assemble the deck that makes it work). Most of the format's best cards never put you at a blank page; a chosen core card always does. This skill is the procedure for that blank page.

The session this runs in already has the card database and the deck-building site wired up — use them for card text, the legal card pool, partner discovery, assembly, pricing, and export. In this repo that means `cards.csv` and the page generator; the repo's `CLAUDE.md` documents the pipeline contract (adding cards, buy blocks, the deck-page markdown shape). The public sites listed at the bottom are for cross-checking and for anything the local DB can't answer.

---

## Invocation

Parse the command into three things:

- **Play context** — `tourney` or `home`. Required. Governs legality (see *Legality*). If absent, ask before building.
- **Core card(s)** — the centerpiece(s) to build around. Required. If a name maps to multiple prints, use the `from <set>` hint to disambiguate; otherwise pick the print that's legal for the play context and note the choice.
- **Restrictions** — anything else in the command: a budget cap, "only cards I own", single-prize only, a type or set limit, cards to exclude. Honor all of them; state any assumption inline.

**Example:** `/tcg-deck home deck based on gourgeist ex from chaos rising`
→ home deck, core = Gourgeist ex (Chaos Rising print), no extra restrictions.

---

## Core principle: card-first is fine, but win-condition-first always

Starting from a card is not the beginner trap. The trap is starting from a card and stopping at "I like it" without working out how it takes six Prizes. So the first move is never "what pairs with this" — it's **translate the card into a win condition.** Everything downstream is enablement for that win condition. If you can't state in one sentence how this card wins the game, you don't have a deck yet; you have a card you like.

The community "commonly played with" data (pokemoncard.io) is seductive because it looks like the answer. It isn't the starting point — it's the crowd's aggregated output, and leaning on it first is just meta-chasing one level down. Reason from the card, then use co-occurrence data as a **sanity check at the end** (step 9), where it can catch a card you missed — and where you can catch a synergy the crowd missed.

---

## The build procedure

Work these in order. Each step feeds the next.

### 1. Read the core card into a spec

Pull the exact card text (local DB first; Bulbapedia for authoritative text **and rulings**). Extract every one of these — they are the whole design brief:

- **Type, HP, stage, retreat cost, weakness, resistance.**
- **Attack(s): energy cost and damage.** The cost sets your energy plan; the damage sets your archetype (step 2).
- **Ability**, if any — often the real reason to play the card.
- **Self-imposed "downsides" that are actually engine features.** Read effects like "move an Energy from this Pokémon" or "discard" as mechanisms, not penalties — they usually point at what the rest of the deck should do (e.g. a benched recipient for moved Energy → a partner attacker).
- **Hidden synergies from the rulings.** The rulings text surfaces interactions the card text alone hides (prize-denial stacking, what does/doesn't trigger an ability). This is where card-first beats copying — it finds lines the crowd hasn't converged on.
- **The exact card name, including any brand prefix.** "Team Rocket's Mimikyu" is not "Mimikyu"; brand cards evolve, search, and combo only within their brand, and a brand core drags its whole brand engine into the deck (see reference §7).

### 2. Fix the archetype from the breakpoints

Compare the core's **damage against the format's HP wall**, and its **HP against the format's damage output** (current numbers in `references/deckbuilding-reference.md`). This choice is forced by the card, before any support is picked:

- Damage clears the top HP tier → **one-shot aggro** build.
- Damage lands short of it → **two-shot midrange**, so the deck needs damage modifiers, spread, or a prize-race plan instead of raw racing.
- Damage spreads across the bench → **spread** build.
- Low damage but a disruptive ability / high HP → **control / attrition**.
- Low HP but single-prize → **out-trade** build (win the Prize race by giving up fewer).

The archetype dictates every later choice. Don't pick support before you've named it.

### 3. Commit the core line

Run the core at **3–4 copies** — a 1-of centerpiece is unreliable (it opens in hand ~12% of games and sits in Prizes ~10%; see reference). For evolving cores, choose the line philosophy the card invites:

- **Rare Candy jump** — thick Basic, thin Stage 1, Rare Candy to skip to Stage 2. Fastest for a Stage 2 that wants to attack early.
- **Manual line** — thick Stage 1 (e.g. 4-3-2), no/low Rare Candy. Steadier when the Stage 1 matters or you evolve every turn.

### 4. Assemble the enablement as packages, not single cards

Build in modules — a builder chooses ~6–8 packages, not 60 cards. For each, ask what the *spec* from step 1 requires:

- **Setup / search** — get the core and its pieces onto the board.
- **Draw engine** — a Pokémon line with a draw ability plus your draw Supporters.
- **Energy plan** — basic type(s) + count sized to the attack cost, plus any acceleration. If the core accelerates itself (step 1), spend those slots elsewhere.
- **Gust** — pull up a benched target to close or disrupt.
- **Recovery** — get KO'd pieces back.
- **One ACE SPEC** — exactly one per deck; this is a high-leverage pick, choose it deliberately.
- **Partner / second attacker** — covers the core's slow setup and its Prize liability, and receives anything the core's engine feeds.
- **Tech / Stadium** — answers to the matchups the archetype fears.

### 5. Add the consistency shell

Bolt on the format's near-invariant staples (draw, search, gust — see reference for the current list). This shell is what makes a 60-card deck feel small. **It is format-relative** — Standard's shell is not Expanded's — and it **rotates**, so verify the current staples against a live list rather than trusting any hardcoded set (including this skill's).

### 6. Cover the two gaps the card creates

- **Setup speed.** Evolving cores are slow by construction — plan turns 1–2 with a cheap early attacker or a setup engine so you're not dead before the core exists. The partner from step 4 can double as this.
- **Weakness.** A printed weakness is a hole; either tech an answer or plan bench/gust management around it.

### 7. Balance to the skeleton and check the math

Start from the skeleton — **~20 Pokémon / ~30 Trainers / ~10 Energy**, ±3 per category — then adjust with the consistency math (tables in reference):

- **Count outs, not copies.** For any goal (find the core, switch, an Energy), sum *every* card that achieves it and treat them as one pool. That pool size, not the literal count of one card, is what determines reliability.
- **Basics for mulligans.** Keep enough Basics to hit ~75–85% no-mulligan (roughly 7–11 Basics; see table). Too few = you hand the opponent free turns.
- **Energy is usually low** (8–12), lower with acceleration — over-loading Energy causes dead hands.
- **Prize-check the core.** With the core at 3–4, all copies prized is a non-event; at 1–2 it's a real risk the build must tolerate or answer with prize-checking cards.

### 8. Validate legality

Apply the *Legality* rules for the play context. For `tourney`, confirm every card's regulation mark is currently legal and the list obeys the sanctioned constraints. For `home`, only the hard deck rules apply.

### 9. Sanity-check against community data — now, not earlier

Only after the deck is reasoned out, compare it to what exists: the co-occurrence data (pokemoncard.io `category/pokemon/<card>`), any tournament lists (limitlesstcg.com `/decks`), casual brews. Use it to catch a support card you overlooked or confirm your energy count — **not** to overwrite your reasoning. If the crowd runs something you didn't, decide *why* before adding it. If you found a line the crowd didn't, keep it if the reasoning holds.

### 10. Output and hand off to the test loop

Produce the deck in the output format below, then frame the tuning loop: the list is a hypothesis, playtesting is the confirmation. Point at the diagnostic table so the next iteration is symptom-driven, not guesswork.

---

## Legality

**Hard deck rules (both contexts):** exactly 60 cards; at least 1 Basic Pokémon; at most 4 of any one card name (basic Energy is exempt and unlimited; special Energy is capped at 4); at most **one** ACE SPEC of any kind.

**`tourney`** — enforce the sanctioned format:
- **Standard** is the default. Legality follows the **regulation mark**, not the set. Marks rotate every spring, so **verify the current legal marks against a live source** (pokegym legal list / pokemon.com) rather than trusting a memorized set. *As of the April 2026 rotation: H, I, J and later are legal; G rotated out.* A card is legal if any of its prints carries a legal mark, so reprints keep older cards alive — and pre-rotation "what's rotating" predictions are unreliable; trust live decklists.
- New cards are legal ~2 weeks after release (2nd Friday); promos on the 1st/3rd Friday.
- No proxies, no foreign-language cards, no World Championship-deck cards (grey-bordered — note these *are* allowed at casual league), nothing marked "NOT TOURNAMENT LEGAL".
- **Expanded** (Black & White onward) only if the command asks for it — much larger pool, its own staples.

**`home`** — no sanctioned enforcement. Keep the hard deck rules unless the command says otherwise (kids' games sometimes drop the 4-of or 60-card rule). Rotated and any-mark cards are fine. Bias the build toward **fun, budget, and a clear, teachable game plan** over raw optimization, and explain choices in plain language.

---

## Output format

Deliver, in this order:

1. **Win condition** — one or two sentences: how this deck takes six Prizes.
2. **Archetype** — the label from step 2 and why the core forces it.
3. **Decklist** — 60 cards, grouped Pokémon / Trainers (Supporters, Items, Stadiums, Tools) / Energy, with counts. Mark the core line and the ACE SPEC.
4. **Why it's built this way** — the packages from step 4, one line each, tied back to the spec.
5. **Legality note** — context, format, and confirmation it's legal (or, for home, that it's casual-legal).
6. **Test-and-tune** — 2–3 things to watch in playtesting and the ratio each points at, drawn from the diagnostics.

For `home` decks, keep the language friendly and the reasoning legible. If a budget or owned-only restriction is in play, note the approximate cost and flag any card that breaks the cap.

---

## Diagnostics — symptom to cause to fix

After playtesting, most problems map to a small set of causes. Use this instead of guessing:

- **Bricking on the open** → too few outs to the core / too few Basics → raise search count and Basic count.
- **Too slow, core online too late** → line too thin or no Rare Candy / no early attacker → thicken the line or add setup + a turn-1 option.
- **Energy drought** → count too low or no acceleration → +1–2 Energy or add an accelerator.
- **Energy flood / dead hands** → count too high → cut 1–2 Energy for draw or outs.
- **Key piece prized too often** → core or key tech at too low a count → raise to 3–4, or add prize-checking.
- **Folds to one matchup** → missing tech / weakness unanswered → add a targeted answer in the flex slots.
- **Runs out of resources late** → recovery too thin → add Night Stretcher / Super Rod-type effects.

**Build-time smells** (catch before testing): a 1-of load-bearing card; more than ~15 Basics or under ~8; Energy over ~14 without a reason; two ACE SPECs; a ceiling you can't actually cast on curve; support that doesn't serve the win condition; a list that mixes pre- and post-rotation staples.

---

## Sites

Local DB and deck site first; these for cross-checking and gaps. Each rotates/updates, so read the date stamp.

| Site | Use in building |
| --- | --- |
| [pokemoncard.io](https://pokemoncard.io) | Card DB, deck builder, budget decks, and per-card **"commonly played with"** co-occurrence at `category/pokemon/<card>` — the step-9 sanity check on partners and the shell. |
| [limitlesstcg.com](https://limitlesstcg.com) | Per-card pages at `/cards/<SET>/<NUM>` — the fastest authoritative single-card text check. Tournament decklists and per-card deck overviews (`/decks`), current meta, and the **DrawCalc** consistency tool at `/tools/drawcalc`. JP City League lists (`/decks/list/jp/…`) run on the newest sets first, so they are the earliest post-rotation evidence. |
| [play.limitlesstcg.com](https://play.limitlesstcg.com/decks?game=PTCG&format=standard) | Live online meta shares and win rates by archetype — the current field for step 6 tech choices, fresher than any writeup. |
| [bulbapedia.bulbagarden.net](https://bulbapedia.bulbagarden.net) | Authoritative card text **and rulings** — the source for the step-1 spec. |
| [justinbasil.com/guide](https://www.justinbasil.com/guide/) | Deckbuilding theory: the skeleton, draw engines, and the ACE SPEC / copy limits. |
| [ptcgstats.com](https://www.ptcgstats.com) | Tournament meta writeups — what the field looks like, for picking tech in step 6. |
| [pokegym.net legal list](https://pokegym.net/current-standard-legal-card-list/) | Live Standard legal-card list — the step-8 legality check for `tourney`. |

> [!CAUTION]
> **Pokémon TCG Pocket is a different game.** ptcgpocket.gg, pocket.limitlesstcg.com, and anything with Pocket set codes (A1, A2, B1, B2b, ...) describe cards that share names with paper cards but have different text, costs, and rules (20-card decks, no Energy cards, 3-point wins). Never source card text, legality, or partner data from a Pocket site for a paper build. Pocket lists are usable only as loose archetype inspiration, clearly labeled.

---

## Reference

`references/deckbuilding-reference.md` holds the numbers this procedure leans on: the hypergeometric copy-count and mulligan tables, current HP/damage breakpoints, the archetype taxonomy, the Prize-trade map, evolution-line patterns, the current consistency shell and package catalog, and the full legality detail. Read it whenever a step needs a concrete number or the current staple list.
