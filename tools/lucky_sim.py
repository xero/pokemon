#!/usr/bin/env python3
"""Build-order experiments for dark-lucky.md, on the dark-gang simulator.

Plays Lucky Haunt's list through tools/dark_gang_sim.py and changes one
decision at a time. Like the simulator, the numbers are relative: compare rows
to each other, never to a real win rate.

    python3 tools/lucky_sim.py order                       # what the board builds first
    python3 tools/lucky_sim.py call                        # Call for Family's first two picks
    python3 tools/lucky_sim.py call --scenario dog --n 5000

order   Changes the Basic bench order, and whether Dawn and Poke Pad go for the
        Chansey line before the engine and an attacker are up.

call    Forces an opening of one Toxel in the Active Spot and a Basic Darkness
        Energy in hand, with no Poffin or Poke Pad in the opening seven. The
        dog scenario also puts an Okidogi ex on the Bench. Only the first Call
        for Family's two picks change, and only games whose first call found
        the Bench as the scenario set it are scored. The right half of each
        table is the games where the calling Toxel was knocked out on the
        opponent's next turn.

Metrics, beyond the simulator's own:
  tox by T3/T4  a Toxtricity in play by your turn 3 or 4
  surges        Sinister Surges used in 8 turns
  happy         Happy Switches used in 8 turns

Blind spots, on top of the simulator's. It barely uses Happy Switch (about
0.1 a game), because its opponent knocks out the Active every turn and the
ferry never gets going, so it measures what building Blissey early costs, not
what Blissey gives back. Only the race opponent attacks your Active on its
turn 2; gust and stall spend that turn on your Bench, so the calling Toxel
only dies in race, and race does it 40% of the time. A real deck that can hit
70 on its turn 2 takes the Toxel more often than that.
"""
import argparse, collections, random
from contextlib import contextmanager

import dark_gang_sim as sim

# dark-lucky.md's list: the Gengar Gang with Neo Upper for the Cape, and two
# Chansey and two Blissey ex for an Okidogi ex, a Toxel, a Boss's Orders, and
# an Energy Recycler. Update it when the Qty tables change.
LUCKY = sim.variant(Cape=-1, NeoUpper=+1, Okidogi=-1, Toxel=-1, Boss=-1, Recycler=-1,
                    Chansey=+2, Blissey=+2)
CHANSEY_LINE = ('Chansey', 'Blissey')


def side(r, k, pct=True):
    """'going first/going second' for one metric."""
    a, b = r
    return f"{a[k] * 100:4.1f}/{b[k] * 100:4.1f}" if pct else f"{a[k]:.2f}/{b[k]:.2f}"


# ------------------------------------------------------------------ order
@contextmanager
def chansey_hidden(g):
    """Make the simulator's Chansey branches act as if a Chansey line is already out."""
    real = g.count_line
    g.count_line = lambda names: 1 if names == CHANSEY_LINE else real(names)
    try:
        yield
    finally:
        del g.count_line


def order_policy(order, gate):
    """A Game whose bench order is order, and whose searches reach for Chansey only when gate allows.

    gate: 'always'  whenever no Chansey is out (the simulator's default)
          'engine'  once a Toxtricity is in play
          'attack'  once a Toxtricity and a Gengar ex or Mega are in play
          'never'   never searched; a drawn Chansey is still benched
    """
    class Policy(sim.Game):
        BENCH_ORDER = order

        def chansey_ok(s):
            tox = s.has_in_play('Toxtricity')
            return {'always': True, 'never': False, 'engine': tox,
                    'attack': tox and (s.has_in_play('GengarEx') or s.has_in_play('Mega'))}[gate]

        def play_dawn(s):
            if s.chansey_ok():
                return sim.Game.play_dawn(s)
            with chansey_hidden(s):
                return sim.Game.play_dawn(s)

        def pad_target(s):
            if s.chansey_ok():
                return sim.Game.pad_target(s)
            with chansey_hidden(s):
                return sim.Game.pad_target(s)
    return Policy


G1, G2, G3 = ('Gastly', 1), ('Gastly', 2), ('Gastly', 3)
T1, T2 = ('Toxel', 1), ('Toxel', 2)
C1, O1 = ('Chansey', 1), ('Okidogi', 1)

ORDERS = [
    ('simulator default', [G1, T1, C1, G2, T2, G3, O1], 'always'),
    ('Chansey first', [C1, G1, T1, G2, T2, G3, O1], 'always'),
    ('Toxel first', [T1, G1, C1, G2, T2, G3, O1], 'always'),
    ('Chansey once Toxtricity is up', [G1, T1, C1, G2, T2, G3, O1], 'engine'),
    ('Blissey last', [G1, T1, G2, T2, G3, O1, C1], 'attack'),
    ('two Toxel before Chansey', [G1, T1, T2, C1, G2, G3, O1], 'engine'),
    ('two Gastly before Chansey', [G1, T1, G2, C1, T2, G3, O1], 'engine'),
    ('never search Chansey', [G1, T1, G2, T2, G3, O1, C1], 'never'),
]


def cmd_order(a):
    deck = sim.build(LUCKY)
    for opp in a.opp.split(','):
        print(f"\n### opponent: {opp}, {a.n} games per side (first/second)")
        print(f"{'build order':32s} | {'first<=3':>11s} | {'rearm':>11s} | {'atk/8':>9s} | "
              f"{'strand':>9s} | {'dry':>9s} | {'happy':>9s}")
        for name, order, gate in ORDERS:
            G = order_policy(order, gate)
            r = (sim.run(deck, n=a.n, first=True, opp=opp, seed=a.seed, game=G),
                 sim.run(deck, n=a.n, first=False, opp=opp, seed=a.seed + 1, game=G))
            for x in r:
                x['happy'] = x['stats']['happy_switch'] / a.n
            print(f"{name:32s} | {side(r, 'first<=3'):>11s} | {side(r, 'rearm'):>11s} | "
                  f"{side(r, 'atk/8', False):>9s} | {side(r, 'stranded/game', False):>9s} | "
                  f"{side(r, 'dry/game', False):>9s} | {side(r, 'happy', False):>9s}")


# ------------------------------------------------------------------- call
NO_OPEN = set(sim.POKE) | {'Poffin', 'Pad'}
SKIP = 'nothing'


class ForcedCall(sim.Game):
    """An opening Toxel that calls first, with the first call's picks fixed."""
    SCENARIO = 'lone'
    PICKS = None

    def setup(s):
        s.shuffle()
        s.deck.remove('Toxel'); s.deck.remove('D')
        hand = ['D']
        if s.SCENARIO == 'dog':
            s.deck.remove('Okidogi')
        rest = [c for c in s.deck if c not in NO_OPEN]
        s.rng.shuffle(rest)
        for c in rest[:5]:
            s.deck.remove(c); hand.append(c)
        s.hand = hand
        s.active = sim.Mon('Toxel', 0)
        if s.SCENARIO == 'dog':
            s.put_bench('Okidogi')
        s.shuffle()
        s.prizes = [s.deck.pop() for _ in range(6)]
        s.first_call = True
        s.scored = False
        s.call_turn = None
        s.caller_died = False
        s.surges = 0
        s.tox_at = None

    def cff_pick(s, avail, got):
        if s.first_call and got == 0:
            s.scored = len(s.bench) == (1 if s.SCENARIO == 'dog' else 0) and s.t <= 2
            s.call_turn = s.t
        if s.first_call and s.PICKS:
            want = s.PICKS[got]
            if got == 1:
                s.first_call = False
            if want == SKIP:
                return None
            if want in avail:
                return want
        return sim.Game.cff_pick(s, avail, got)

    def KO_mon(s, m):
        if s.call_turn is not None and s.t == s.call_turn and m.name == 'Toxel' and m is s.active:
            s.caller_died = True
        return sim.Game.KO_mon(s, m)

    def our_turn(s):
        r = sim.Game.our_turn(s)
        s.surges += s.surges_done
        if s.tox_at is None and s.has_in_play('Toxtricity'):
            s.tox_at = s.t
        return r


CALLS = {
    'lone': [
        ('dog + Gastly', ('Okidogi', 'Gastly')),
        ('dog + Toxel', ('Okidogi', 'Toxel')),
        ('Gastly + Toxel', ('Gastly', 'Toxel')),
        ('Gastly only', ('Gastly', SKIP)),
    ],
    'dog': [
        ('two Gastly', ('Gastly', 'Gastly')),
        ('Gastly + Toxel', ('Gastly', 'Toxel')),
        ('Gastly only', ('Gastly', SKIP)),
        ('Gastly + Chansey', ('Gastly', 'Chansey')),
        ('Toxel + Chansey', ('Toxel', 'Chansey')),
    ],
}


def play_call(scenario, picks, first, opp, n, seed):
    G = type('G', (ForcedCall,), {'SCENARIO': scenario, 'PICKS': picks})
    rng = random.Random(seed)
    deck = sim.build(LUCKY)
    games = []
    for _ in range(n):
        g = G(deck, first, opp, rng)
        g.play()
        if g.scored:
            games.append(g)
    return games


def score(games):
    k = len(games)
    if not k:
        return None
    agg = collections.Counter()
    for g in games:
        agg.update(g.stats)
    by = lambda attr, t: sum(1 for g in games if getattr(g, attr) is not None and getattr(g, attr) <= t) / k
    return {
        'n': k,
        'first<=3': by('first_attack', 3),
        'rearm': agg['rearm_hit'] / max(1, agg['rearm_n']),
        'atk/8': sum(len(g.attacks_by) for g in games) / k,
        'tox<=3': by('tox_at', 3),
        'tox<=4': by('tox_at', 4),
        'surges': sum(g.surges + g.stats['surge_build'] for g in games) / k,
        'died': sum(g.caller_died for g in games) / k,
    }


def cmd_call(a):
    scenarios = ['lone', 'dog'] if a.scenario == 'both' else [a.scenario]
    for scenario in scenarios:
        for first in (False, True):
            for opp in a.opp.split(','):
                seed = a.seed if first else a.seed + 1
                rows = [(name, play_call(scenario, p, first, opp, a.n, seed)) for name, p in CALLS[scenario]]
                head = score(rows[0][1])
                print(f"\n### {scenario}, going {'first' if first else 'second'}, opponent {opp}: "
                      f"{head['n']} scored games, caller knocked out next turn in {head['died'] * 100:.0f}%")
                print(f"{'first call':18s} | {'atk by T3':>9s} | {'rearm':>6s} | {'atk/8':>5s} | "
                      f"{'tox by T3':>9s} | {'tox by T4':>9s} | {'surges':>6s} || caller died: "
                      f"{'atk by T3':>9s} | {'tox by T4':>9s} | {'surges':>6s} | {'atk/8':>5s}")
                for name, games in rows:
                    s, d = score(games), score([g for g in games if g.caller_died])
                    died = (f"{d['first<=3'] * 100:8.1f}% | {d['tox<=4'] * 100:8.1f}% | "
                            f"{d['surges']:6.2f} | {d['atk/8']:5.2f}") if d else '-'
                    print(f"{name:18s} | {s['first<=3'] * 100:8.1f}% | {s['rearm'] * 100:5.1f}% | "
                          f"{s['atk/8']:5.2f} | {s['tox<=3'] * 100:8.1f}% | {s['tox<=4'] * 100:8.1f}% | "
                          f"{s['surges']:6.2f} || {'':13s}{died}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    o = sub.add_parser('order', help='what the board builds first')
    o.add_argument('--n', type=int, default=6000, help='games per side (default 6000)')
    c = sub.add_parser('call', help="Call for Family's first two picks")
    c.add_argument('--scenario', choices=('lone', 'dog', 'both'), default='both')
    c.add_argument('--n', type=int, default=20000,
                   help='openings per side; about a third score as lone, more as dog (default 20000)')
    for x in (o, c):
        x.add_argument('--opp', default='race,gust,stall', help='opponent models, comma-separated')
        x.add_argument('--seed', type=int, default=35)
    a = p.parse_args()
    {'order': cmd_order, 'call': cmd_call}[a.cmd](a)


if __name__ == '__main__':
    main()
