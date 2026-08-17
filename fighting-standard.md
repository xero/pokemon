# Fox's Ground Zero — Standard Legal

### Build 3 of 3 · Fighting · no evolutions, no waiting, no fire

> [!NOTE]
> **How to read this file.**
>
> Third of three Standard-legal directions for Fox. This is the one you asked for that isn't fire — and it isn't Eevee either.
>
> - **[Flareon ex / Noctowl](./fire-standard.md)** — Fire, tournament-proven, built on what he owns.
> - **[Rainbow DNA](./eevee-standard.md)** — the Eevee toolbox. Six types, hardest to pilot.
> - **This file** — **Mega Zygarde ex**. One Basic Pokémon, three Energy, 200 damage. The simplest deck on this list by a mile.
>
> All Regulation **H / I / J**.

---

## The Thesis

Every deck Fox has ever played is an **evolution** deck. Charmander waits to become Charmeleon waits to become Charizard. Eevee waits to become Flareon. He spends the first three turns of every game not attacking, and the whole design problem is protecting babies on the Bench.

**This deck deletes that entire category of problem.**

> **Mega Zygarde ex — Perfect Order 047.** Fighting, **310 HP**, **Basic Pokémon**. Regulation **J**.
> - ***Gaia Wave*** [F][F][F], **200 damage.** During your opponent's next turn, this Pokémon takes **30 less damage** from attacks (after Weakness and Resistance).
> - ***Nullifying Zero*** [F][F][F][F][F] — for **each** of your opponent's Pokémon, flip a coin. If heads, this attack does **150 damage** to that Pokémon. (Don't apply Weakness and Resistance for Benched Pokémon.)
> - Weak **Grass ×2**. Retreat 2.

**A Basic Pokémon with 310 HP that hits for 200.** No Rare Candy. No evolution line. No Bench to protect. You put it down, you attach Energy three times, and you start knocking things out.

That is an enormously good deck for a ten-year-old to learn on, for reasons that have nothing to do with power level:

1. **There is no wrong sequencing.** The most common mistakes in his current deck — Rare Candy on turn one, Rare Candy on a Basic played this turn, evolving the wrong Charmander — simply cannot happen here.
2. **The turn is short.** Draw, attach, attack. He can actually hold the whole plan in his head.
3. **It teaches the one skill his other decks don't: the Prize race.** More on that below, because it's the catch.

---

## The Catch, Stated Up Front

> [!WARNING]
> **Mega Evolution Pokémon ex give up 3 Prize cards when Knocked Out.**
>
> Games go to 6. **Two knockouts and he loses.** Every other deck on this table — dad's Gengar Gang, dad's psychic builds, his own current Charizard deck — is entirely 1-Prize. This is the opposite extreme.

That is not a reason to skip the deck. It's the *reason to play it*, once. Prize math is the single most important thing a player learns after "attacking ends your turn," and nothing teaches it like piloting a deck where every mistake costs half the game.

**310 HP is what buys the time.** Very little in Standard one-shots that, and *Gaia Wave* subtracts 30 from the next hit — so realistically the opponent needs two turns to take three Prizes. That's a fair trade, and it's exactly the arithmetic he needs to start doing.

---

## Why Fighting, Specifically

**Because it doubles against dad's entire Dark deck.**

| Dad's Pokémon | HP | Weakness | *Gaia Wave* 200 → |
| :--- | :--- | :--- | :--- |
| Gengar (POR 050) | 130 | Fighting ×2 | **400** ☠️ |
| Weezing (JTG 092) | 130 | Fighting ×2 | **400** ☠️ |
| Haunter (PFL 055) | 100 | Fighting ×2 | **400** ☠️ |
| Gastly / Koffing | 70 / 60 | Fighting ×2 | **400** ☠️ |

Every Pokémon in `dark.csv` is Weak to Fighting ×2. Fox currently has exactly one answer to that — a rotated Sudowoodo — and this deck makes it the whole plan.

**Dad's lantern deck is the wrong target, though.** Mega Chandelure ex in [Psychic Lanterns](./psychic-lanterns.md) resists Fighting and carries 350 HP, so *Gaia Wave* lands at 170 and needs three clean hits against a deck that one-shots back.

> [!NOTE]
> **Nullifying Zero is a board wipe, and it's the flashiest card in this whole project.** Five Energy, then flip a coin for *every* Pokémon your opponent has in play — Active and Bench — and each heads does **150 to that Pokémon**.
>
> Against a full board of six, that's six flips. Expected three heads. Against dad's deck, where nothing has more than 130 HP, **every head is a knockout** — and Weakness isn't even applied on the Bench, because it doesn't need to be.
>
> It is win-the-game-on-the-spot in a way nothing else here is, and it is entirely down to coin flips. He will love it.

---

## Deck List

> [!CAUTION]
> **This is the least-verified of the three lists.** I confirmed Mega Zygarde ex's text, stats, and Regulation J mark directly. I did **not** verify the current Fighting-type support cards or the post-rotation Energy-acceleration staples — those are the cards that make or break a 3-Energy-attack deck, and I'd be guessing.
>
> Treat this as a **shell and a direction**, not a finished 60. The core is right; the support needs a current staple list.

**Pokémon (8-10)**

| Qty | Card | Set | Number | Reg |
| --- | --- | --- | --- | --- |
| 3-4 | **Mega Zygarde ex** | Perfect Order | 047 | **J** |
| 4-6 | *Fighting support / secondary attacker* | — | — | to research |

**Trainers (~36)** — verified legal core:

| Qty | Card | Type | Set | Reg |
| --- | --- | --- | --- | --- |
| 4 | Ultra Ball | Item | Mega Evolution 131 | I |
| 4 | Lillie's Determination | Supporter | Mega Evolution 119 | I |
| 3 | Boss's Orders | Supporter | Mega Evolution 114 | I |
| 3 | Switch | Item | Mega Evolution 130 | I |
| 3 | Night Stretcher | Item | Shrouded Fable 061 | H |
| 2 | Gwynn | Supporter | Pitch Black 078 | J |
| — | *Energy acceleration* | — | — | **the critical gap** |

**Energy (~14)** — Basic Fighting.

> [!IMPORTANT]
> **The whole deck lives or dies on Energy acceleration.** *Gaia Wave* costs **three** Fighting Energy and you attach one per turn. Without a way to cheat that, Mega Zygarde ex sits there doing nothing until turn three — which is precisely the problem this deck was supposed to solve.
>
> This is the one thing to research before building. Every serious version of this deck will be built around whatever the current Fighting acceleration is.

---

## Game Plans

### 1. Draw, Attach, Attack

That's it. That's the deck.

```
Turn 1   Play Mega Zygarde ex Active. Attach Fighting.
Turn 2   Attach Fighting.
Turn 3   Attach Fighting → GAIA WAVE, 200 damage.
Turn 4+  Gaia Wave again. And again.
```

**No Rare Candy. No evolution timing. No Bench management.** Compare that to the eight-step turn checklist in `fire.md` and you can see why this is the right deck to hand a kid who's still forgetting to use *Battle Sense*.

### 2. Gaia Wave Defends Itself

> During your opponent's next turn, this Pokémon takes **30 less damage** from attacks.

That's not a rounding error on a 310 HP body — it's a fourth attack they have to land. And it's automatic: it happens every time he attacks, with no card, no cost, and nothing to remember.

**Against dad's Gengar Gang**, run the numbers: *Mind Jack* at a full Bench does 160, minus 30, into 310 HP. **He survives two.** *Crazy Blast* does 170, minus 30 → 140. He survives two of those as well.

Dad needs three or four good turns to take three Prizes. Fox needs two Gaia Waves to take two.

### 3. The Prize Race Is the Lesson

| Deck | Prizes per knockout | Knockouts to lose |
| :--- | :--- | :--- |
| Dad's Gengar Gang | 1 | 6 |
| Fox's current fire deck | 1 | 6 |
| **This deck** | **3** | **2** |

**Two mistakes and it's over.** Which means the actual skill this deck teaches is *not attacking* — knowing when to Switch out, when to take a turn off, when a trade is bad even though it's available.

That is a genuinely more advanced skill than anything his current deck asks for, packaged inside the simplest possible turn structure. That combination is rare and it's why this build is worth taking seriously despite being the least developed of the three.

### 4. Nullifying Zero Is the Party Trick

Five Energy is a lot and you will rarely get there. When you do, flip for **every** Pokémon they have in play, 150 damage per heads, no Weakness applied on the Bench.

Against a wide board it ends games outright. Against a narrow one it's a coin flip for 150. Either way it's the most exciting attack in this entire project and it costs nothing to include, because it's printed on a card you're already playing.

---

## Honest Weaknesses

**Weak to Grass ×2.** 310 HP becomes 155 effective against anything Grass — including **Leafeon ex** from [Build 2](./eevee-standard.md), whose *Verdant Storm* does 60× the Energy on your Pokémon. A Mega Zygarde with three Energy attached takes 180, doubled to **360**. That's a clean one-shot for three Prizes. These two decks are a hard counter to each other in both directions.

**The Energy problem is real and unsolved here.** Three Energy for the main attack in a format where you attach one per turn is a genuine cost. Don't build this without answering it.

**It's the least *interesting* of the three to an adult.** There's no combo, no toolbox, no clever rules interaction. It's a big Pokémon that hits hard. That's a feature for a ten-year-old and a bug for you — worth being honest that you'd probably enjoy piloting the other two more than this one.

---

## Which Of The Three?

| | **[Flareon ex](./fire-standard.md)** | **[Rainbow DNA](./eevee-standard.md)** | **Ground Zero** |
| :--- | :--- | :--- | :--- |
| **Type** | Fire | Six types | Fighting |
| **Uses cards he owns** | ✅ **All of it** | ✅ All but 3 | Trainers only |
| **Complexity** | Medium | **High** | **Low** |
| **Cost to build** | Medium | **High** | Low–Medium |
| **Prizes given up** | 2 | 2 | **3** |
| **Tournament proven** | ✅ 2nd, Birmingham 2026 | Partly | Emerging |
| **Beats dad's Dark deck** | No edge | Situational | ✅ **×2 on everything** |
| **How ready is this doc** | Full 60, 3 flex | Full 60, 3 flex | **Shell only** |

**My recommendation: [Flareon ex / Noctowl](./fire-standard.md).** It's the only one where his birthday presents *are* the deck, it's proven at Regional level, and the Tera mechanic directly fixes the weakness he's currently living with (Basics dying on the Bench). It's also a natural bridge — same Eevee, same Flareon, new rules.

**[Rainbow DNA](./eevee-standard.md) is where I'd go next**, once he's comfortable. It's the deck he'd actually be excited about, and *Onyx* stealing a Prize card is the kind of effect a kid remembers for years.

**Ground Zero is the wildcard.** Build it if he ever says the Charizard deck feels slow — or if you want him to learn Prize math the hard way, in one afternoon.
