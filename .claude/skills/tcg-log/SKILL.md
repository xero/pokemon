---
name: tcg-log
description: Archive and review Pokémon TCG Live battle logs for this deck repo. Use this whenever the user pastes a TCG Live game log (text that opens with "Setup" and reads like "X won the coin toss", "X's Turn", "used Chaotic Pain", "took a Prize card"), points at a log file in logs/, says "here's my last match" or "why did I lose this one", or asks how a deck, a list change, or a card under test is doing across games. It saves the log with the deck and list commit it was played with, prints a turn-by-turn ledger with flags, and reviews the play against the deck page's own rules.
---

# TCG Log

> [!NOTE]
> Reads a pasted TCG Live battle log, archives it in `logs/` with the deck list it was played with, and reviews the game against that deck's page. This skill is a tool for you, not a product for Xero: it makes reading a game fast and consistent, and hands you evidence you can trust. What reaches Xero is your judgment, informed by the report and by whatever the conversation is working on.

---

## Files

- `scripts/parse_log.py` has three commands: `save`, `report`, and `summary`. Run it from the repo root.
- `logs/` is the archive. It is gitignored, so it lives on this machine only.
- `evals/` holds six real logs and `check.py`, which re-runs the parser on them and checks what it should find. When a new log teaches the parser something, add it here with a check. Run `python3 .claude/skills/tcg-log/evals/check.py` after any parser change.

---

## Workflow

### 1. Save the log

Write the pasted text to the scratchpad with the Write tool, exactly as pasted. A shell heredoc or `echo` can mangle the curly apostrophes and accented handles Live prints. Then save it:

```sh
python3 .claude/skills/tcg-log/scripts/parse_log.py save <file> \
  --mode ranked --changes "-1 Hero's Cape, +1 Neo Upper Energy" --opp-deck "Hop's Zacian ex"
```

When the user drops a raw log into `logs/` themselves, run `save` on that file. The archived copy, named `<date>-<deck>-vs-<opponent>.txt`, replaces it. `save` refuses a log it has already archived, whatever the file is called.

The header, and where each field comes from:

| Field | Source |
| --- | --- |
| date | today, or `--date` |
| player, opponent, went, result, how, prizes, turns | the log |
| deck | the registered deck whose Qty tables best match the cards you revealed, or `--deck` |
| commit | the last commit that touched the deck's source; `+dirty` means the working tree's Qty tables differ from it |
| unlisted | cards you played that the committed list doesn't have |
| changes | `--changes`, how the list on Live differs from the committed one |
| mode | `--mode`: ranked, casual, league, home, or friendly |
| opp_deck | `--opp-deck`, the archetype, using the Limitless name when one exists |
| opp_pokemon | the log |
| notes | `--notes` |

**Fill in what the log can't know.** A non-empty `unlisted` means the Live list isn't the committed list, so `changes` needs the whole swap, including what came out, which a log never shows. Take it from the conversation or from earlier archived logs with the same `unlisted`, and ask when neither says. Pass `--mode ranked` unless the user said otherwise, since Xero plays ranked on Live, and mention it in one line instead of asking. Name `opp_deck` yourself from `opp_pokemon`. Fix any field later by editing its header line in place.

The commit matters because deck pages keep changing. A log stamped with a commit is still readable six list revisions later.

### 2. Run the report

```sh
python3 .claude/skills/tcg-log/scripts/parse_log.py report logs/<file>.txt
```

It prints the Prize flow, every turn from both sides, your board and hand at the end of each of your turns, this game's numbers, the flags, and the draw luck. Read all of it before writing anything. The flags only point at turns, and most findings come from reading those turns.

### 3. Check the card text

Before any damage math about the opponent's cards, look them up in the newest `legal-cards-*.json`. Don't work from memory; this repo has shipped wrong card text more than once. The pool strips Retreat Cost and Weakness, so pull those from the pokemontcg.io API, with the mobile user agent, when a line depends on them.

### 4. Read the deck page

Open the deck's `.md` and read the sections that govern decisions. For dark-gang those are The Hard Rules (which Stage 2 gets the Candy, where the Energy goes, who *Chaotic Pain* hits, when to stand and when to pull), The Prize Tax, and the `### Versus` section for this opponent. Search the page for the opponent's archetype and for league regulars' names.

The review measures the game against the page's own rules. A rule that was right and got broken is a finding. A rule that was followed and still lost is a bigger one.

### 5. Write the review

Write it in chat, not in a file. These sections are a checklist for your reading of the game, in the order Xero likes to read them; skip one that has nothing in it.

1. **Verdict.** The result, then what decided it, in one or two sentences.
2. **Misplays.** A numbered list, biggest first. Each one names the turn, what you did, what to do instead, and what that changes: a Prize, a turn, a knockout. If the game had none, say so in one line.
3. **What's working.** Cards and lines that earned their place in this game, each with its evidence from the report's numbers.
4. **What's not working.** Problems no play could have fixed: a card that sat dead in hand, an out the hand never had, a body that gave away Prizes. These are deck problems, not play problems.
5. **What would have changed it.** Optional. When one card at one turn would have flipped the game, name it: the turn, the card, and what it does there. "A Switch on turn 2 brings up the loaded Gengar ex for *Chaotic Pain*." Draw these from the flags, especially the stranded turns and the Energy shortfalls. Say what the card would have done, not what to cut for it.
6. **Luck.** The number from the report, and whether it decided anything.
7. **Matchup notes.** When the page has no Versus section for this opponent, give the few facts that matter and offer to write one.

**A misplay needs a legal alternative.** Before calling a play a mistake, check the ledger's hand and board for that turn and confirm the better line was really there: the card in hand, the Energy on the body, the Supporter not yet played, the target in range. A turn where the right card simply wasn't in hand goes under What's not working or What would have changed it. Mixing the two tells the user to play differently when the deck is what needs to change.

**Check every attack's target.** For an attack that can hit anything, like *Chaotic Pain*, ask whether a better target was in reach: the Pokémon taking your Prizes, a two-Prize body two hits from dead, or a draw or Energy engine. A knockout on a single-Prize body while their main attacker never takes a counter is a misplay, even when each knockout looked fine on its own turn.

**Look for the earlier win.** Count the Prizes each side needed, then ask whether holding a resource, like a Boss's Orders, a Switch, or an Energy, sets up the last knockout a turn sooner. A spent Boss's Orders that bought nothing is often the difference.

**The review is about this game.** Deck building beyond it, like a list change being tested, a card to cut, or which ACE SPEC to run, belongs to the conversation, not the review's standing sections. Bring it in only when the user asked about it or the session is working on it, and keep it to what this game shows. When a card under test is involved, its `owned` flag in `cards.csv` says whether it can be in the paper list yet. Deck page changes follow the spitball-first rule: propose, then wait for the go-ahead.

Say "turn 4" for your fourth turn, the way the ledger counts.

---

## Reading the numbers

The report's "This game's numbers" section is the evidence for What's working and What's not working.

- **Your attacks** lists each attack with its knockouts and Prizes. The attacker carrying the game is working. A setup attack used over and over is a sign the real attackers weren't ready.
- **Your losses** lists each Pokémon you lost and the Prizes it cost. A body that gave up 2 Prizes without swinging is a problem. A Toxtricity that gave up 0 under Shadowy Concealment is the tax working.
- **In hand at the end of 3+ of your turns in a row** lists cards that sat unplayed. A Supporter or Stage 2 sitting for four turns is a dead card or a missing piece; say which. Copies can rotate, so read it as "a copy was always there", and check the turn lines before calling one card dead.

## Reading the flags

Flags point at turns worth a look. They are not verdicts.

| Flag | What to check |
| --- | --- |
| no attack; loaded on the Bench | the switching problem: Switch, AZ's, retreat Energy, or Pecharunt in hand or reachable |
| no attack; the Active could pay | why it didn't swing |
| no attack; the Active was N Energy short | where the missing Energy could have come from: Janine's, a Surge that can't reach the Active, an attachment spent elsewhere |
| setup attack while loaded on the Bench | whether the loaded body could have come up instead |
| held an Energy with no attachment | whether any body could use it; an unplayed attachment is gone for good |
| held a Basic with Bench space open | the evolution clock, since a Basic can't evolve the turn it lands; holding is right only when something punishes a fuller Bench, so read the opponent's attack text |
| Ability used k of n | often a Toxtricity evolved that turn, which can Surge at once; the flag can't see conditions like an empty deck |

"Loaded" means able to pay for an attack worth 100 or more, or 10 or more damage counters. The held-card flags read the hand at the moment of the attack, so a Prize card the attack took doesn't count against the turn.

KO lines carry the damage story, such as `lost Gengar ex (took 60 + 180 + 130 = 370 of 280 HP)`. Hold that against Hero's Cape's +100 and against the page's breakpoint tables.

The luck section counts cards that reached the hand by chance: the opening hand, turn draws, draw effects, and Prize cards. Searches don't count. It names the Supporters seen, because two Boss's Orders are not two draw Supporters. When Lillie's reshuffles cards back in, the odds are approximate.

---

## Log format notes

Live's log is mostly plain English. These are its traps:

- "drew 2 cards" under Hilda, Dawn, Petrel, or Poké Pad is a search. The parser decides by the card's text.
- Your Prize cards are named, as in "Rare Candy was added to xer0style's hand." The opponent's never are.
- *Chaotic Pain*'s counter line calls the target yours. "xer0style put 13 damage counters on xer0style's Hop's Wooloo" hit their Wooloo. Risky Ruins' activation line does the same. Their Pain is labeled the same way in reverse, so in a mirror, where both boards hold a Toxel, the parser goes by whose attack it was, not by the name.
- Under *Void Gale* or Handheld Fan, "- X attached Basic Darkness Energy to Y" is a move off the Active, not a new Energy.
- "- X discarded Risky Ruins" under the other player's Stadium play is the Stadium leaving play, not a card from the hand.
- A mulligan prints the hand that was sent back, so it shows part of the opponent's list.
- **Your own mulligan hides your hand.** Live prints the mulliganed seven as your opening hand and never shows the seven you kept, so the report says the hand lines cover only what the log revealed afterward. Treat held-card flags and luck as partial in that game.
- Happy Switch and Energy Switch lines name where the Energy went, never where it came from. The ledger guesses a benched donor and labels the guess; check it against the next attack before building a finding on it.
- A hit into Weakness adds a second sentence to the attack line, like "Mew ex took 260 more damage because of Darkness Weakness".
- Damage breakdown bullets list every modifier on a hit.
- *Chaotic Pain* hits one Pokémon, but Live prints a line for every Pokémon that couldn't take it: "Battle Cage was activated", *Hide 'n' Sneak*, *So Submerged*. These lines show what was protected, not where the counters went. The counters line names the target.
- A Prize line can come before its KO line, when an effect like Legacy Energy's discard runs between them. The parser matches the two up.
- Endings read "Opponent took all of their Prize cards. X wins.", "All Prize cards taken. X wins.", or "Opponent was inactive for too long. X wins." The last is a timeout. Record the win, and say the game was unfinished.
- The log names cards, never printings, so the deck match works by name. Live prints are picked for art. Live spells Poké Pad with the accent, and the repo uses TCGplayer's Poke Pad; the parser folds accents and curly quotes.
- The player whose opening hand is printed owns the log. Xero plays as xer0style. Fox's games carry his own handle, and the deck match finds his deck.

When the report prints tracking warnings, the ledger lost the hand or the board at that point, usually after hand disruption like Judge, Iono, or Unfair Stamp, or after an effect the parser doesn't know. Trust the log over the ledger from there on. If the line will come up again, teach the parser and add the log to `evals/`.

---

## Across games

```sh
python3 .claude/skills/tcg-log/scripts/parse_log.py summary
```

It totals wins and losses by deck, list commit, and `changes`, lists the opponents under each, and counts the flags per game. Use it for questions like "how's the Neo Upper test going". Say how many games the answer rests on, because three games is an anecdote.
