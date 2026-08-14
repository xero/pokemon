# TCG Deck — Deckbuilding Reference

The numbers and catalogs behind the procedure in `SKILL.md`. Card-specific values (HP, staples, the shell) drift with each set and each spring rotation — **verify anything time-sensitive against a live source**; the marked values are current as of the 2026 season and are here as anchors, not gospel.

## Contents

1. [Consistency math](#1-consistency-math)
2. [Format breakpoints (HP and damage)](#2-format-breakpoints)
3. [Archetype taxonomy](#3-archetype-taxonomy)
4. [Prize-trade map](#4-prize-trade-map)
5. [Evolution-line patterns](#5-evolution-line-patterns)
6. [The consistency shell and package catalog](#6-consistency-shell-and-packages)
7. [Legality in full](#7-legality-in-full)

---

## 1. Consistency math

Deck consistency is hypergeometric: the question is never "what fraction of my deck is X" but "what's the probability I have X when I need it." 60-card deck, 7-card opening hand.

**Copies vs. chance to open with it (before search or mulligan):**

| Copies | In opening 7 | Notes |
| --- | --- | --- |
| 4 | ~40% | The reason 4-of is the max for cards you always want. |
| 3 | ~32% | |
| 2 | ~23% | |
| 1 | ~12% | And ~10% to be sitting in your Prizes. Never build a plan on a 1-of. |

Search and mulligans push these up; that's what the shell is for. A key combo piece above ~50% to be *accessible* (drawn or searchable) turn 1 is "consistent enough."

**Basics vs. mulligan risk** (you mulligan when you open with zero Basics):

- 7–11 Basics → roughly **60–80% chance of NOT mulliganing**. Target band.
- ~12 Basics → ~19% mulligan rate; ~13 Basics → ~16%.
- Aim for **75–85%** to open with a playable Basic. Below ~7 Basics you mulligan too often and hand the opponent free setup; above ~15 you crowd out Trainers.
- Current winning lists skew Pokémon-heavy: 19–22 Pokémon with 11–13 Basics, ~30 Trainers, 8–13 Energy. When a deck feels like "too many Trainers," the verified fix is cutting Energy and adding Pokémon, not cutting Trainers.

**Prize math:** any specific single card is ~10% (6/60) to be prized. All four copies of a 4-of prized at once is ~1 in 32,500 — effectively never, which is *why* 4 copies guarantees access. At 2 copies the both-prized case is small but real; at 1 copy, ~10% of games it's simply unavailable.

**Outs, not copies:** for any goal, sum every card that achieves it and treat the total as the copy count in the tables above. "Find the core" outs = every searcher that can grab it + the core copies. "Get a switch" outs = Switch + Escape Rope + Jet Energy + any retreat-substitute. Reliability tracks the *pool*, not one card.

**Energy count:** most decks run **8–12**; as low as 4 with heavy acceleration, as high as ~14 for two-Energy-cost single-prize attackers without accel. Size it by counting how much Energy you need *in play* by your ideal attacking turn, then subtract what acceleration supplies. Over-counting Energy is the classic cause of dead hands.

Tools: [Limitless DrawCalc](https://limitlesstcg.com/tools/drawcalc) for exact hypergeometric odds on a real list.

---

## 2. Format breakpoints

*(2026 Standard anchors — verify against current sets.)*

The core's numbers relative to these decide its archetype in step 2.

- **Top HP tier:** Mega Evolution ex run **330–380 HP** (Mega Venusaur and Mega Emboar 380, Mega Dragonite 370, Mega Gengar 350, Mega Excadrill 340); Dragapult ex 320; most meta ex 280–330. The wall a true one-shot attacker must clear is **350–380**, not 320.
- **Field damage ceiling:** the hardest common single hit is ~330 (Mega Excadrill's Maximum Drilling). 340+ HP survives it; everything below trades into it.
- **To one-shot the field** you generally need ~350+, usually only via **damage modifiers** (Black Belt's Training is the current verified one; check the live pool — modifier Trainers rotate fast). A core that tops out below that (e.g. a 230 attacker) is a two-shot card and must win by chip, spread, prize denial, or Prize race. Free, repeatable damage-counter placement (abilities and cheap attacks) is how 230 becomes lethal; counters also ignore Weakness and Resistance.
- **Survivability:** ~340+ HP survives most single non-weakness hits (build to grind); ~200–230 HP gets one-shot by the field (build to trade favorably). A printed **weakness ×2** turns a survivable Pokémon into a one-shot against that type — a real hole to answer, and sometimes a reason to hybridize (a partner line that *resists* the feared type patches a dodge matchup).
- **Mega ex give up 3 Prizes** when KO'd — the defining liability of the current top HP tier; factor it into every Mega-core build. Modern Mega Evolution ex evolve like any Stage 1/2 and do **not** end your turn (the XY-era Spirit Link problem no longer exists; those Tools also name the old "M X-EX" cards and never trigger on current Megas).

---

## 3. Archetype taxonomy

The core's spec forces one of these; each implies a different build.

- **Aggro / big Basic** — fast, few moving parts, one-shots where possible. Friendliest to pilot and to a home build. Energy plan simple, line short or none.
- **Evolution midrange** — set up a Stage 1/2 engine, take over mid-game. Higher ceiling, fragile early → needs setup speed and an early attacker.
- **Spread** — damage across the bench for multi-KO turns; wants damage-movement support and gust to convert.
- **Control / disruption** — win by denying resources (hand, Energy, board) rather than racing; leans on disruption Supporters, recovery, and durability.
- **Mill / deck-out** — win by emptying the opponent's deck. Niche, demanding, real.
- **Single-prize toolbox** — give up fewer Prizes than the opponent and win the trade; strong against multi-prize/Mega fields and naturally budget.

---

## 4. Prize-trade map

You take 6 Prizes; how many you *give up* per Pokémon is the strategic spine.

- **Single-prize:** 1 on KO. Slower to close, but the opponent needs six knockouts. Win the race by trading up (your 1-prize piece KOs their 2–3-prize piece). Basis of budget/toolbox decks — and currently a strong meta call because it out-trades the Mega-heavy field (single-prize archetypes are roughly a fifth to a third of the 2026 field).
- **Pokémon ex:** 2 on KO. Higher damage/HP ceiling; each loss is a third of the game.
- **Mega Evolution ex:** 3 on KO. Biggest liability in the game; mitigate with high HP, not getting hit back, and any prize-denial the core offers.

**Prize-denial modifiers exist and stack.** Two verified kinds: ability-based (e.g. Mega Gengar ex's Shadowy Concealment — opponent takes 1 fewer Prize when your Darkness Pokémon is KO'd by an opposing ex's attack; explicitly non-stacking across copies of itself) and **Legacy Energy** (ACE SPEC special Energy — 1 fewer Prize when its holder is KO'd by any attack, once per game). Together a 1-prize attacker can award **zero** Prizes, twice over. Two warnings that come with them:

- Read the trigger exactly. Denial keyed to "your opponent's Pokémon ex" is **blank against single-prize attackers** — a large slice of the field — so a denial-based deck still needs a plan for the fair game.
- Denial only covers what the text says. Type-restricted abilities skip off-type partners in the same deck (a Psychic partner in a Darkness deck gives full Prizes).

Build the **Prize map** explicitly, in both directions: how many KOs does the opponent need to beat me (after denial), versus how fast can I take my six? A deck that forces a 6-KO game against your 3-KO game is winning by construction.

---

## 5. Evolution-line patterns

- **Rare Candy jump:** thick Basic (e.g. 4), thin Stage 1 (1–2 as backup), Rare Candy to skip Basic → Stage 2 in one step. Use when the Stage 2 wants to attack early and the Stage 1 is just a bridge. Two Rare Candy timing rules that decide openings: never on your first turn, and never on a Basic that entered play this turn — so the fastest Stage 2 is turn two, off a Basic benched on turn one.
- **Manual line:** e.g. 4-3-2 or 3-2-2, little/no Rare Candy. Use when you evolve every turn or the Stage 1 does real work (a Stage 1 with a useful cheap attack earns its copies even in a Candy deck).
- **Basic → Stage 1:** run more Basics than Stage 1s (4-3, 3-2) so you reliably start on the Basic.
- **Big Basic (no evolving):** most consistent to pilot, best home/beginner default; the whole line question disappears.
- **Mega jump (current format):** Wally's Compassion (MEG) is a Rare Candy alternative that current Mega lists actually run; Mega Signal (MEG) searches the Mega itself. Both exist because a 3-prize Stage 2 core cannot afford to whiff its own arrival.
- **One Basic can feed two payoffs.** Different Stage 2s that evolve from the same Stage 1 (or two prints of different names in one line, like Mega Gengar ex and a single-prize Gengar) share the whole bottom of the line — a cheap way to add a plan B without new Basics.

Match the pattern to what the core's text rewards, not to a template.

---

## 6. Consistency shell and packages

**The shell is format-relative and rotates — verify the current list before trusting it.** The roster below was verified against live post-rotation tournament lists (Limitless, August 2026). The pre-rotation staples **Professor's Research, Nest Ball, Counter Catcher, Super Rod, Judge, Iono, Arven**, and the plain **N** and **Marnie** all carried mark G, rotated in April 2026, and have no legal reprint — a list containing any of them is a pre-rotation list. (The "N's" and "Marnie's" cards in current sets are different names; see §7 on brands.)

- **Draw Supporters:** Lillie's Determination (4 copies in effectively every list), Dawn (fetches one Basic + one Stage 1 + one Stage 2 — the evolution-deck enabler), Brock's Scouting, Drayton.
- **Search Items:** Ultra Ball (MEG print), Buddy-Buddy Poffin (2 Basics ≤70 HP straight to Bench — design lines around the 70 HP cap), Poké Pad (POR).
- **Gust:** Boss's Orders (MEG) — the only generic gust Supporter left, so 2–3 copies is the norm. Type-specific supplements exist (e.g. Grimsley's Move benches a Darkness Pokémon from the top 7).
- **Disruption:** Special Red Card (CRI, Item), Unfair Stamp (ACE SPEC).
- **Recovery:** Night Stretcher (a Pokémon **or a basic Energy** from discard to hand). **Special Energy is unrecoverable once discarded** — price that in before building on one.
- **Draw-engine Pokémon:** Fezandipiti ex (draw 3 after one of yours was KO'd — natural in decks that trade bodies), Noctowl + Hoothoot, Dudunsparce + Dunsparce, N's Zoroark ex (in Darkness shells).
- **Energy acceleration is type-specific and era-specific** — check the type's current options instead of assuming an old analogue exists (Darkness right now: Janine's Secret Art from deck, Toxtricity's Sinister Surge ability from deck with self-damage; the self-damage is often a feature that feeds counter-moving abilities like Munkidori's).
- **ACE SPEC (pick one):** Prime Catcher (gust + switch, most-played), Unfair Stamp (hand disruption on a KO — the most common pick in aggressive lists), Legacy Energy (any-type Energy plus once-per-game prize denial; see §4), Secret Box, Maximum Belt.

**Packages** are the modules a build is assembled from — think in these, not single cards:

- *Search/setup package:* the search Items above, sized to your line.
- *Draw package:* a draw-engine Pokémon line + draw Supporters.
- *Energy package:* basic Energy of the core's type(s) + any accelerator (ability or Trainer).
- *Gust package:* Boss's Orders, plus the ACE SPEC slot if Prime Catcher takes it.
- *Recovery package:* Night Stretcher, sized up in decks that discard aggressively.
- *ACE SPEC:* exactly one.
- *Core package:* the evolution line at 3–4 + Rare Candy if used.
- *Partner package:* a second attacker covering the core's weaknesses and Prize liability.

Most of a list is the first six — near-invariant within the format. The build work is the core, partner, and tech.

---

## 7. Legality in full

**Hard deck rules (always):** 60 cards exactly; ≥1 Basic; ≤4 of any card name; basic Energy exempt/unlimited; special Energy capped at 4; ≤1 ACE SPEC of any kind.

**Standard (tourney default):**
- Legality is by **regulation mark**, not set. **Marks rotate each spring — verify current marks live.** *2026 season: H, I, J and later legal; G rotated out (in effect April 10 2026 for paper, March 26 for TCG Live).*
- A card is legal if any of its prints has a legal mark; older printings play at the current text (errata applies, and players are expected to know errata). Reprints keep staples alive, so pre-rotation "rotating out" lists are unreliable — trust live decklists.
- **Marks are per card, not per set.** One set can print mark-G and mark-H cards side by side (Prismatic Evolutions does), so never infer legality from the set name.
- **All prints of one name share the 4-copy limit** — mix printings freely, never exceed four of the name. Prints numbered **above the set size** (e.g. 269/217) are the same card as the base print at collector prices; for budget builds, always buy the lowest-numbered print.
- **Brand prefixes are part of the card name.** "Team Rocket's Wobbuffet," "N's Zoroark ex," and "Marnie's Grimmsnarl ex" are distinct names from any plain version: separate 4-copy limits, evolution only within the brand (Team Rocket's Koffing evolves into Team Rocket's Weezing, never plain Weezing), and brand support usually works only on brand Pokémon (Team Rocket's Energy provides Energy only to Team Rocket's Pokémon). Choosing one brand card as a partner usually commits the deck to that brand's engine.
- New cards legal ~2 weeks post-release (2nd Friday); promos 1st/3rd Friday.
- Banned in Standard: none currently. Rotated ≠ banned.
- Not tournament-legal: proxies, foreign-language cards (incl. Japanese, incl. their basic Energy), World Championship-deck cards (grey border — allowed at casual league, not sanctioned), anything printed "NOT TOURNAMENT LEGAL".

**Expanded (tourney, on request):** Black & White onward — much larger pool, its own staple set (e.g. the search/recovery cards differ), its own ban list. Only build Expanded if the command asks for it.

**Home:** no enforcement. Keep the hard deck rules unless told otherwise (kitchen-table games sometimes drop 60/4-of). Any mark, rotated cards, and mixed eras are all fine. Optimize for fun, budget, teachability, and a legible game plan rather than tournament efficiency.
