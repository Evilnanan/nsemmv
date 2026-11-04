"""Execute complete reviewed effect chains in pinned PC code.

The owner identity, allocator, PARAM lookup and delivery queue are fixtures.
Insertion, eligibility, damage expiry, timer/cycle/replacement dispatch, unlinking
and numeric getters run unchanged. This is not gameplay or network validation.
"""
import argparse
import json
import math
import struct
from pathlib import Path
from unicorn.x86_const import *
from native_effect_runtime import OBJ, Chain, Inputs, sha

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('exe', type=Path)
p.add_argument('extracted', type=Path)
p.add_argument('output', type=Path)
a = p.parse_args()
inputs = Inputs(a.exe, a.extracted)
raw, x, param, rows, spells = inputs.raw, inputs.x, inputs.param, inputs.rows, inputs.spells

checks = {'revenant': [], 'fp': [], 'duchess': [], 'attack': []}
all_stubs = set()
for id in range(7220300, 7220307):
    row = spells[str(id)]
    assert struct.unpack_from('<f', rows[id], 0xa4)[0] == row['changeMpRate']
assert spells['7220305']['physicsAttackRate'] == spells['7220305']['magicAttackRate']
assert spells['7220305']['effectEndurance'] == 20

scenarios = [
    ('no-equipment', [60, 120, 124], 17, 1, 0),
    ('no-damage', [], 17, 1, 1),
    ('zero-damage', [60, 120, 124], 17, 0, 1),
    ('paired-hit', [60, 61], 3, 1, 1),
    ('rearm-boundary', [120, 124], 3, 1, 1),
    ('dense-hits', list(range(60, 900)), 17, 1, 1),
    ('duplicate-equipment', [120, 124], 3, 1, 3),
    ('independent-expiry', [60, 300], 23, 1, 1),
]
for name, hits, seconds, damage, copies in scenarios:
    c = Chain(inputs)
    for _ in range(copies): c.insert(7220300)
    c.qualify(); c.update(0)
    assert [n['id'] for n in c.nodes()] == ([7220300] if copies else [])
    c.insert(7220301)
    c.qualify(); c.update(0)
    grants, restores, attack_changes = [], [], []
    previous_rate = 1
    for frame in range(seconds * 60):
        incoming, c.emitted = c.emitted, []
        for id in incoming: c.insert(id)
        if incoming: grants.append(dict(frame=frame, ids=incoming))
        c.qualify()
        if frame in hits:
            c.invoke(0x504d30, [OBJ, 0, 0, 0, 0], {UC_X86_REG_XMM1: damage})
        c.update(1 / 60)
        amount, flask = c.fp(1000)
        assert flask == 0
        if amount:
            assert amount == 100
            restores.append(dict(frame=frame, amount=amount))
        rates = c.attack()
        count = sum(n['id'] == 7220305 and not n['flags'] & 0x800c0003 for n in c.nodes())
        assert all(math.isclose(v, 1.15 ** count, rel_tol=1e-6) for v in rates)
        if not math.isclose(rates[0], previous_rate, rel_tol=1e-6):
            attack_changes.append(dict(frame=frame, count=count, rate=rates[0]))
            previous_rate = rates[0]
    expected = {'no-equipment': 0, 'no-damage': 1, 'zero-damage': 1, 'paired-hit': 1, 'rearm-boundary': 2,
                'dense-hits': 8, 'duplicate-equipment': 2, 'independent-expiry': 3}[name]
    assert len(restores) == expected
    if name in ('no-damage', 'zero-damage'): assert restores[0]['frame'] > 900
    if name in ('rearm-boundary', 'duplicate-equipment'): assert restores[1]['frame'] - restores[0]['frame'] < 10
    if name == 'independent-expiry': assert [v['count'] for v in attack_changes] == [1, 2, 3, 2]
    checks['revenant'].append(dict(name=name, fps=60, hits=hits, damage=damage, equipmentCopies=copies,
        seconds=seconds, grants=grants, restores=restores, attackChanges=attack_changes, finalNodes=c.nodes()))
    all_stubs.update(c.stubs)

for special in (0, 1):
    for name, kills, seconds, copies in [
        ('no-equipment', [60], 3, 0),
        ('one-kill', [60], 3, 1), ('repeat-kill', [60, 61], 3, 1),
        ('duplicate-equipment', [60, 61], 3, 3), ('after-window', [780], 14, 1),
        ('independent-expiry', [60, 300], 33, 1),
    ]:
        c = Chain(inputs)
        for _ in range(copies): c.insert(7032700)
        c.qualify(); c.update(0)
        assert [n['id'] for n in c.nodes()] == ([7032700] if copies else [])
        c.insert(7032701)
        c.qualify(); c.update(0)
        grants, attack_changes = [], []
        previous_rate = 1
        leaf = 7032706 if special else 7032704
        for frame in range(seconds * 60):
            incoming, c.emitted = c.emitted, []
            for id in incoming: c.insert(id)
            if incoming: grants.append(dict(frame=frame, ids=incoming))
            c.qualify()
            if frame in kills: c.invoke(0x50a150, [OBJ, OBJ + 0x6000, special])
            c.update(1 / 60)
            count = sum(n['id'] == leaf and not n['flags'] & 0x800c0003 for n in c.nodes())
            rates = c.attack()
            assert all(math.isclose(v, (1.05 if special else 1.15) ** count, rel_tol=1e-6) for v in rates)
            if not math.isclose(rates[0], previous_rate, rel_tol=1e-6):
                attack_changes.append(dict(frame=frame, count=count, rate=rates[0]))
                previous_rate = rates[0]
        expected = {'no-equipment': [], 'one-kill': [1], 'repeat-kill': [1, 2], 'duplicate-equipment': [1, 2],
                    'after-window': [], 'independent-expiry': [1, 2, 1]}[name]
        assert [v['count'] for v in attack_changes] == expected
        checks['duchess'].append(dict(name=name, fps=60, kills=kills, special=special, equipmentCopies=copies,
            seconds=seconds, grants=grants, attackChanges=attack_changes, finalNodes=c.nodes()))
        all_stubs.update(c.stubs)

for leaf in (7220305, 7032704, 7032706):
    c = Chain(inputs)
    c.insert(leaf); c.qualify(); c.update(0)
    for kind in range(6):
        values = c.attack(kind)
        expected = spells[str(leaf)]['physicsAttackRate'] if kind < 5 else 1
        assert all(math.isclose(v, expected, abs_tol=1e-6) for v in values)
        checks['attack'].append(dict(leaf=leaf, kind=kind, rates=values))
    all_stubs.update(c.stubs)

for copies in (1, 2, 3):
    for maximum in (0, 1, 99, 100, 137, 1000):
        c = Chain(inputs)
        for _ in range(copies): c.insert(7220306)
        c.qualify(); c.update(0)
        value = c.fp(maximum)
        assert value == [math.trunc(maximum * copies * .1), 0]
        c.qualify(); c.update(1 / 60)
        assert c.fp(maximum) == [0, 0]
        checks['fp'].append(dict(copies=copies, maximum=maximum, first=value, nextFrame=[0, 0]))
        all_stubs.update(c.stubs)

a.output.write_text(json.dumps(dict(schema=1, exeSha256=sha(raw), regulationSha256=x['hashes']['regulation.bin'],
    paramSha256=sha(param), checks=checks, stubs=sorted(all_stubs), gameplayVerified=False), indent=2) + '\n')
print('PASS:', {k: len(v) for k, v in checks.items()})
