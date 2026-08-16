# Xero's Long Night

### Build B — They never get a turn

> [!NOTE]
> **How to read this file.**
>
> This is the second of **two** paper builds for your Psychic Gengars. Both are "versus Fox" future plans; both lean on old cards deliberately.
>
> - **Build A — Witching Hour** was built on **Gengar, Lost Origin 066**, a **spread** deck: damage counters on everything, including the Bench. It was retired in August 2026; its file now holds [Night Parade](./psychic-lanterns.md), the tournament lantern deck, and the old list lives in git history.
> - **This file (Build B)** is built on **Gengar, Sword & Shield 085** — the *Life Shaker* / *Hypnoblast* one. It's a **lock** deck: it wins by making sure the Pokémon in front of you never does anything.
>
> They share a Gastly line and about eight Trainers. Otherwise they play nothing alike. Build A grinds; this one strangles.
>
> `psychic.md` — the first draft — is untouched.

---

## The Thesis

**Asleep is the most under-rated Special Condition in the game, and it is the only one that stops both halves of a turn.**

> **The rule:** an Asleep Pokémon **cannot attack and cannot retreat**. During Pokémon Checkup its owner flips a coin — heads it wakes up, tails it stays Asleep. It also clears if the Pokémon leaves the Active Spot. ([Bulbapedia — Special Conditions](https://bulbapedia.bulbagarden.net/wiki/Special_Conditions_(TCG)))

Compare that to what your Dark deck does with Confusion. A Confused Pokémon *can* attack — it just flips first. An Asleep Pokémon has no flip and no choice. It stands there.

And the escape hatch is narrow. It cannot retreat, so paying Energy is not an option. It has to either **win a coin flip at Checkup** or **be removed by a card effect** — and Fox runs exactly **two Switch**.

**So the whole deck is one question: how many different ways can I put something to sleep?**

This build has three, at three different price points:

| Card | Cost | Effect |
| :--- | :--- | :--- |
| **Drowzee**, *Hypnosis* | **[P]** — one Energy | Asleep. Turn one. No coin flip. |
| **Gengar**, *Hypnoblast* | [P][P][C] | **90 damage** + Asleep |
| **Gourgeist**, *Shadow Bind* | [P][C][C] | **100 damage** + can't retreat |

Sleep them cheaply early, sleep them expensively late, and trap them when they wake up.

---

> ### Table of Contents
> - [Deck List](#deck-list)
> - [Key Card Text](#key-card-text)
> - [Game Plans](#game-plans)
> - [Versus Fox](#versus-fox)
> - [What To Buy](#what-to-buy)
> - [Build A or Build B?](#build-a-or-build-b)

---

## Deck List

**Pokémon (23)**

| Qty | Card | Set | Number | Own | Need |
| --- | --- | --- | --- | --- | --- |
| 4 | Gastly | any Psychic print | — | **4** | 0 |
| 2 | Haunter | any Psychic print | — | **5** | 0 |
| 3 | Gengar | Sword & Shield | 085 | **1** | 2 |
| 1 | Gengar | Lost Origin | 066 | **1** | 0 |
| 4 | Drowzee | Unbroken Bonds | 071 | 0 | 4 |
| 3 | Hypno | Unbroken Bonds | 072 | 0 | 3 |
| 2 | Wobbuffet | Phantom Forces | 036 | 0 | 2 |
| 2 | Pumpkaboo | any Psychic print | — | **3** | 0 |
| 2 | Gourgeist | Paradox Rift | 078 | 0 | 2 |

**Trainers (25)**

| Qty | Card | Type | Set |
| --- | --- | --- | --- |
| 4 | Rare Candy | Item | any |
| 4 | Ultra Ball | Item | any |
| 4 | Professor's Research | Supporter | any |
| 3 | N | Supporter | Noble Victories 92 |
| 3 | Fog Crystal | Item | Chilling Reign 140 |
| 3 | Mysterious Treasure | Item | Forbidden Light 113 |
| 2 | Switch | Item | any |
| 2 | Old Cemetery | Stadium | Chilling Reign 147 |

**Energy (12)**

| Qty | Card | Set | Number |
| --- | --- | --- | --- |
| 12 | Basic Psychic Energy | Mega Evolution Energies | 005 |

**23 + 25 + 12 = 60.** ✅

**Basics: 12** (4 Gastly, 4 Drowzee, 2 Wobbuffet, 2 Pumpkaboo) — about a **19% mulligan rate**.

**Twelve Energy, not eleven.** Build A's main attack costs one Energy; this deck's do not. *Hypnoblast*, *Shadow Bind*, and *Stir the Brain* are all three-Energy attacks, and three Fog Crystal are in the list partly to find Energy.

> [!WARNING]
> **The Gengar split is 3 + 1 and it's the opposite of Build A's.** Both prints share one four-card name limit. Here the Sword & Shield 085 is the *attacker* — you want to draw it — and the single Lost Origin copy is there purely for *Netherworld Gate*, which works from the discard pile and only needs to exist once.

---

## Key Card Text

### Drowzee — Unbroken Bonds 071

Basic, and the whole reason this build exists.

> One Energy. No coin flip. No damage — and that's fine, because this card isn't here to deal damage, it's here to make turn two not happen.

### Hypno — Unbroken Bonds 072

Stage 1 from Drowzee. ***Hypnotic Pendulum* fires on a knockout, not on your attack**, so it works whichever of your Pokémon took the Prize.

*Stir the Brain* scales off their hand, which is why the N problem below matters:

| Cards in their hand | Stir the Brain |
| :--- | :--- |
| 3 | 60 |
| 5 | 80 |
| 7 (just played Professor's Research) | **100** |
| 9 | 120 |

### Gengar — Sword & Shield 085

Stage 2 from Haunter. ***Life Shaker* has no once-per-turn limit.**

> **90 damage *and* Asleep on the same attack.** This is the card the whole deck is built to protect and power up.

### Gourgeist — Paradox Rift 078

Stage 1 from Pumpkaboo. ***Startling Pumpkin* pays you for losing it**, which is unusual and worth planning around.

> Note this is a **different Gourgeist** from the one you own. Yours is the *Pandemonium* print (Evolving Skies 077) and it's the right card for Build A. This one is the right card here.

### Wobbuffet — Phantom Forces 036

Basic. The Ability exempts **[P] Pokémon**, and every Pokémon in this deck is Psychic, so the lock is entirely one-sided.

### Gengar — Lost Origin 066 *(single copy)*

***Netherworld Gate* works from the discard pile**, so the single copy does its job without ever being drawn.

### Old Cemetery — Chilling Reign 147 *(Stadium)*

> Whenever a player attaches an Energy card **from their hand** to 1 of their **non-Psychic** Pokémon, put 2 damage counters on that Pokémon.

---

## Game Plans

---

### 1. The Long Night

**The core loop. Sleep on turn one, sleep forever.**

```
Turn 1   Drowzee Active, 1 Energy → HYPNOSIS. They're Asleep.
Turn 2   Still Asleep? They can't attack or retreat.
         Hypnosis again if they woke up.
Turn 3+  Gastly → Gengar (Rare Candy) → HYPNOBLAST:
         90 damage AND they're Asleep again.
```

**Every one of their turns is a coin flip on whether it happens at all.** They flip at Checkup: heads they wake and get a normal turn, tails they stand there. Then you re-apply on your turn and it starts over.

**Do the arithmetic on that.** Over six of their turns, they get roughly three. You get six. That is the entire deck in one sentence.

> [!IMPORTANT]
> **Asleep clears when the Pokémon leaves the Active Spot** — and Asleep, Paralyzed, and Confused are mutually exclusive, so anything that applies a different one *replaces* your Sleep. Nothing in Fox's deck does that, so against him the only outs are the Checkup flip and his two Switch.
>
> **Count his Switch.** Two in sixty cards. Once both are gone, a sleeping Charizard is a dead Charizard.

**Why Drowzee is 4-of and not a throwaway.** *Hypnosis* costs one Energy and works on turn one, before you have a Stage 2, before you have three Energy, before anything. Locking your opponent out on turn one while you set up a Stage 2 behind it is the best trade in the deck — and it's why this build can afford to run a three-Energy main attacker at all.

---

### 2. Two Ways Out, and You Close Both

**Asleep stops retreating. Shadow Bind stops the rest.**

An Asleep Pokémon can't retreat, so it has two escapes: **win the Checkup flip**, or **get switched out by a card effect**. Switch, Escape Rope, and friends are not "retreating" — they bypass the restriction entirely. ([Pokégym Compendium — Retreating](https://compendium.pokegym.net/category/7-gameplay/retreating/))

**Gourgeist's *Shadow Bind* is your answer to the turn they wake up.** 100 damage, and the Defending Pokémon can't retreat during their next turn — awake or not.

So the pattern against a big, expensive Active Pokémon:

| Their state | Your play |
| :--- | :--- |
| Fresh | *Hypnosis* — cheap, immediate |
| Asleep, you're set up | *Hypnoblast* — 90 and re-sleep |
| They woke up | *Shadow Bind* — 100 and they still can't leave |
| Buried in counters | *Psychic Assault* — cash out for one Energy |

**And *Startling Pumpkin* makes Gourgeist unpleasant to kill.** If they knock it out, they discard **2 random cards** from their hand. In a deck already being denied turns, losing two random cards off the top is a real tax on the one thing they *did* get to do.

---

### 3. Hypnotic Pendulum Picks the Next Victim

**A free gust, every knockout, forever.**

> When your opponent's Active Pokémon is Knocked Out, flip a coin. If heads, choose which of your opponent's Benched Pokémon becomes their new Active Pokémon.

Normally the *opponent* chooses their replacement, and they will always choose the healthiest thing they own. On heads, **you** choose — and you choose the 70 HP Charmander they were growing into a Charizard.

Then you put it to sleep, and it never becomes a Charizard.

**This is why Hypno is a 3-of and not a 1-of.** Each Hypno has its own Ability, so multiple Hypno means multiple flips on the same knockout — three Hypno in play is a **87.5%** chance at least one comes up heads.

> [!NOTE]
> It's an Ability, not an attack, and it has no Active requirement. Hypno does its job from the Bench all game. That matters enormously in a deck where the Active Spot is already spoken for.

---

### 4. Bide Barricade, and the One Thing It Costs You

Same card as Build A, same one-sided lock — **Psychic Pokémon are exempt**, and every Pokémon here is Psychic:

| Yours | Theirs (Fox) |
| :--- | :--- |
| *Life Shaker* ✅ | **Charizard, *Battle Sense*** ❌ |
| *Netherworld Gate* ✅ | **Eevee, *Boosted Evolution*** ❌ |
| *Hypnotic Pendulum* ✅ | |
| *Startling Pumpkin* ✅ | |

**But here the cost is higher than in Build A**, and you should know it going in. Wobbuffet has to be **Active** to do this — which means the turn you play the lock is a turn you are not applying Sleep. If they wake up on that Checkup, they get a completely free turn.

**So Wobbuffet is a scalpel here, not a default.** Bring it up on a turn where their Active is already deeply buried in damage counters — *Psychic Assault* cashes those in, so the turn isn't wasted — or on the exact turn Fox most needs *Battle Sense* to find a Rare Candy.

**One quiet upside:** *Psychic Assault* costs **one** Energy. In a deck full of three-Energy attacks, having a cheap button for the turn you're short on Energy is worth more than it looks.

---

### 5. Stir the Brain and the N Problem

**A real tension in the list, stated honestly.**

*Stir the Brain* does 30 plus 10 per card in your opponent's hand. It rewards you for letting them refill.

**N does the opposite of what you want here.** N makes each player shuffle their hand into their deck and draw a card for each remaining Prize card. When you're winning — which is the plan — they have *fewer* Prizes left, so N shrinks their hand and shrinks *Stir the Brain*.

So the two cards actively fight. Play them accordingly:

- **N is for when you're behind.** You draw more, they draw less. It's a catch-up card.
- **Stir the Brain is for right after they refill.** Fox plays Professor's Research and draws 7 — that's your window, and it's a 100-damage attack.
- **Don't play N on a turn you're planning to Stir the Brain.** You'd be deleting your own damage.

Three N is the right count for a slow control deck that sometimes falls behind early. Just don't play it on autopilot.

---

### 6. The Cemetery Tax

Unchanged from Build A, and it's still one of the harshest Stadiums in casual play:

> Whenever a player attaches an Energy card **from their hand** to 1 of their **non-Psychic** Pokémon, put 2 damage counters on that Pokémon.

Every Pokémon in this deck is Psychic. Every Pokémon in Fox's deck is not. **20 damage per Energy attachment, all game, one-sided.**

> [!TIP]
> **Welder triggers it twice.** Welder attaches *up to 2* Fire Energy from hand — that is two separate attachment events, so Old Cemetery fires twice for **40 damage** on the Pokémon he just powered up.
>
> **Magma Basin does not trigger it** — that attaches from the **discard pile**, and the Stadium says "from their hand."

And it stacks beautifully with the sleep lock. He's taking 20 a turn just to function, on a Pokémon that keeps failing to wake up.

---

## Versus Fox

### The type chart cancels out

Everything here is Weak to **Darkness** or **Psychic**. Fox plays **Fire**, **Fighting**, and **Colorless**. He hits no Weakness — and Psychic doesn't hit Fire's Water Weakness either. **Neither player gets a free multiplier.** The game is decided entirely by mechanics, which is what makes it a good match.

### Why sleep is especially cruel to his deck

**His deck is built to take big turns.** Welder into a fully-loaded Charizard. Leon plus Royal Blaze. Battle Sense every turn digging toward the combo. All of it assumes he *gets* turns.

| His card | What Sleep does to it |
| :--- | :--- |
| **Charizard**, *Royal Blaze* | Can't attack. The 150-damage swing simply doesn't happen. |
| **Charizard**, retreat **3** | Asleep means it can't retreat at any price. |
| **Welder** | He can still play it — but powering up a Pokémon that can't attack is a wasted turn *and* 40 from Old Cemetery. |
| **Leon** | The +30 only lasts "during this turn." A slept turn wastes it entirely. |
| **Battle Sense** | Off, while Wobbuffet is Active. |

**Leon is the sharpest one.** Leon reads *"during this turn."* If he plays Leon and then fails his Checkup flip, that Supporter did nothing at all — and it's one of his four.

### What still hurts you

**Royal Blaze one-shots everything you own.** With one Leon in his discard it does 150; your biggest body is a 110 HP Hypno or Gengar. He does not need to win the long game if he wins three coin flips in a row.

**Sudowoodo hits Drowzee, Hypno, and Wobbuffet at full.** Only Gengar and Gourgeist carry the −30 Fighting Resistance. Flail into a 110 HP Hypno is a real threat.

**And two Switch is enough to matter.** He gets two guaranteed escapes from the lock. Make him spend them early on something cheap if you can.

### Honest verdict

**Favourable, but swingier than Build A.** Build A grinds out an advantage that compounds and never gives it back. This deck wins hard when the coin flips cooperate and loses turns in clumps when they don't. It is the more *fun* deck to pilot and the less reliable one.

> [!CAUTION]
> **A word about playing this against a ten-year-old.**
>
> A hard sleep lock is not fun to sit across from. Getting three turns out of six, and losing your Leon to a coin flip, is exactly the kind of game that makes a kid put the cards down.
>
> If you build this one, consider it a **deck to play sparingly** — or trim to 2 Drowzee and treat Sleep as tempo rather than a lock. **Build A is the better regular opponent for him.** It's oppressive in a way he can learn to play around; this one is oppressive in a way he mostly just watches.

---

## What To Buy

```buy
Gengar | Sword & Shield 085 | 3 | The attacker, you want three
Gengar | Lost Origin 066 | 1 | Your ToT 2023 066 is this card
Drowzee | Unbroken Bonds 071 | 4 | Common, cents
Hypno | Unbroken Bonds 072 | 3 | Rare, cheap
Wobbuffet | Phantom Forces 036 | 2 | Common
Gourgeist | Paradox Rift 078 | 2 | Not the print you own, but you do own **Pumpkaboo PAR 077** from that line
Old Cemetery | Chilling Reign 147 | 2 |
Fog Crystal | Chilling Reign 140 | 3 |
Mysterious Treasure | Forbidden Light 113 | 3 | **113**, not the 145 gold Secret print
N | Noble Victories 092 | 3 |
Rare Candy | Mega Evolution 125 | 4 | Shared with the Fire and Dark decks
Ultra Ball | Mega Evolution 131 | 4 | Shared with the Fire and Dark decks
Professor's Research | Prismatic Evolutions 122 | 4 | Shared with the Fire deck
Switch | Mega Evolution 130 | 2 | Shared with the Fire and Dark decks
Basic Psychic Energy | Mega Evolution Energies 005 | 12 | Never rotates
```

The Gastly, Haunter, and Pumpkaboo lines are already covered. Skip **151 093** for Haunter.

**The cheapest of the three Psychic builds by a wide margin.** Build A needs three Chandelure NVI — a 2011 Rare Holo that carries a real price. This deck's most expensive card is a Sword & Shield Gengar you already own one of.

**Not Standard legal and can't be made so.** Unbroken Bonds, Phantom Forces, Noble Victories, Chilling Reign, Forbidden Light, and Lost Origin are all rotated.

---

## Build A or Build B?

| | **A — Witching Hour** *(retired)* | **B — Long Night** |
| :--- | :--- | :--- |
| **Built on** | Gengar LOR 066 | Gengar SSH 085 |
| **Wins by** | Damage counters everywhere, incl. their Bench | Denying turns |
| **Signature card** | Chandelure, *Cursed Shadow* | Drowzee, *Hypnosis* |
| **Main attack cost** | 1 Energy | 3 Energy |
| **Energy count** | 11 | 12 |
| **Reaches their Bench?** | ✅ Yes, every turn, free | ❌ Active only |
| **Consistency** | High — grinds, compounds, forgiving | Swingy — coin flips decide clumps of turns |
| **Cost to build** | Higher (3× Chandelure NVI) | **Lower** |
| **Fun to play against?** | Yes — he can learn to play around it | Not especially |

**My recommendation: build A.** Cursed Shadow reaching the Bench is a genuinely novel thing that neither of the other two decks on your table can do, it teaches Fox a real skill (protect your Basics), and it doesn't depend on coin flips to function.

**Build B is the better *deck* in a vacuum** — turn denial is the strongest effect in the game — and it's cheaper. It's just a worse thing to point at a kid.

If you want a middle path: **run Build A and swap in 2 Drowzee** over the Gourgeist line. You get *Hypnosis* as a turn-one tempo play without committing to the full lock, and Cursed Shadow stays the engine.
