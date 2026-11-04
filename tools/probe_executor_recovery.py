"""Execute the Executor unlock accumulator and its conditional HP recovery chain.

Uses actual PARAM rows and original insertion, state, counter, queue, tick and HP
instructions. Animation grants and next-frame character delivery are fixtures;
this is not a live parry, collision or multiplayer test.
"""
import argparse
import json
import struct
from pathlib import Path
from native_effect_runtime import OBJ, Chain, Inputs, sha

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('exe', type=Path)
p.add_argument('extracted', type=Path)
p.add_argument('animations', type=Path)
p.add_argument('hks', type=Path)
p.add_argument('output', type=Path)
a = p.parse_args()
inputs = Inputs(a.exe, a.extracted)
spells = inputs.spells
tae = json.loads(a.animations.read_text())
hks = a.hks.read_bytes()
assert sha(hks) == '786f8a7bc89452d9531e2299b224c8945701c422437eca9aacbeb10a57a17f4d'
assert tae['bundles'][0]['sha256'] == '1410035ad79edb410fa41420ec259fcb4a1037d748c9c4a3b6ae8d1366c76d0f'
assert b'if env(GetSpEffectID, 707051) == TRUE then' in hks
assert spells['7034500']['stateInfo'] == spells['7034502']['invocationConditionsStateChange1'] == 2019
assert spells['7034502']['changeHpRate'] == -5 and spells['7034502']['changeHpPoint'] == -100
assert spells['7034502']['effectEndurance'] == 1
assert abs(spells['7034502']['motionInterval'] - 1.1) < 1e-6
for id, nxt in [(707050, 707051), (707051, 707057)]:
    assert spells[str(id)]['accumuOverVal'] == 50 and spells[str(id)]['accumuOverFireId'] == nxt
    assert spells[str(id)]['dedupeAccumuTrigger'] == 1
assert spells['707057']['replaceSpEffectId'] == 7034501
assert spells['7034501']['replaceSpEffectId'] == 7034502
assert spells['707052']['replaceSpEffectId'] == 707050
assert spells['707052']['accumuVal'] == spells['707057']['accumuVal'] == -99999
amounts = {707053: 5, 707055: 15, 707056: 20}
for id, amount in amounts.items():
    assert spells[str(id)]['accumuVal'] == amount and spells[str(id)]['stateInfo'] == 312

# Only actual Type 67 grants enter the source evidence. No inferred root+1 links.
events = []
for bundle in tae['bundles']:
    for track in bundle['taes']:
        for animation in track['animations']:
            for event in animation['events']:
                if event['Type'] != 67: continue
                id = struct.unpack_from('<i', bytes.fromhex(event['hex']))[0]
                if id in (707052, *amounts):
                    events.append(dict(tae=track['ID'], animation=animation['ID'], effect=id, **event))
assert {e['effect'] for e in events} == {707052, *amounts}
assert [(e['tae'], e['animation'], e['index']) for e in events if e['effect'] == 707052] == [(2907, 571020, 11)]


class Executor(Chain):
    def __init__(self):
        super().__init__(inputs)
        # Ten initially empty accumulator slots (states 303..312) and preallocated
        # request vectors. Updates/thresholds/deduplication are never substituted.
        self.control = OBJ + 0xc000
        self.q(OBJ + 0x18, self.control)
        self.q(self.control, OBJ)
        self.q(self.control + 0x38, 10)
        self.q(self.control + 0x188, 10)
        for k in range(10):
            queue, storage = self.control + 0x40 + k * 0x20, OBJ + 0xd000 + k * 0x100
            self.q(queue, OBJ + 0x7000)
            self.q(queue + 8, storage)
            self.q(queue + 0x10, storage)
            self.q(queue + 0x18, storage + 0x100)
        self.stubs.add('empty ten-slot accumulator storage and preallocated request-vector capacity')

    def hp(self):
        self.q(OBJ + 0x10, 0)
        self.invoke(0x50b860, [OBJ] + [OBJ + 0x800 + k * 0x20 for k in range(11)] + [0])
        self.q(OBJ + 0x10, OBJ + 0x6000)
        return list(struct.unpack('<2f', self.u.mem_read(OBJ + 0x880, 8)))

    def counter(self):
        return struct.unpack('<i', self.u.mem_read(self.control + 8 + 9 * 4, 4))[0]


def scenario(name, copies, increment, count, reset_at=None, extras=False):
    c = Executor()
    for _ in range(copies): c.insert(7034500)
    c.insert(707052)
    schedule = {90 + n * 30: increment for n in range(count)}
    if extras:
        schedule.update({500 + n * 30: increment for n in range(count)})
    if reset_at is not None:
        schedule[reset_at] = 707052
    heals, grants, counters, unlocks = [], [], [], []
    last_count, last_unlocked = None, False
    for frame in range(1000 if extras else 600):
        pending, c.emitted = c.emitted, []
        for id in pending: c.insert(id)
        if frame in schedule: c.insert(schedule[frame])
        c.qualify(); c.update(1 / 60)
        hp = c.hp()
        if any(hp): heals.append(dict(frame=frame, hp=hp))
        if c.emitted: grants.append(dict(frame=frame, ids=c.emitted.copy()))
        counter = c.counter()
        if counter != last_count: counters.append(dict(frame=frame, value=counter))
        last_count = counter
        unlocked = any(n['id'] == 707051 for n in c.nodes())
        if unlocked != last_unlocked: unlocks.append(dict(frame=frame, unlocked=unlocked))
        last_unlocked = unlocked
    reached = count * amounts[increment] >= 50
    # During the reset node's one-second lifetime, its higher-priority category
    # suppresses the first attempted increment in the late-reset fixture.
    repeats = 2 if reset_at == 400 else 1
    expected = repeats if reached and copies else 0
    assert len(heals) == expected, (name, copies, heals)
    assert all(h['hp'] == [-5, -100] for h in heals)
    assert sum(n['id'] == 7034500 for n in c.nodes()) == bool(copies)
    assert len([g for g in grants if 707057 in g['ids']]) == (repeats if reached else 0)
    return dict(name=name, equipmentCopies=copies, incrementEffect=increment, count=count,
                fps=60, resetAt=reset_at, extraAttempts=extras, heals=heals, grants=grants,
                counters=counters, unlocks=unlocks), c.stubs


checks, stubs = [], set()
for increment, counts in [(707053, (9, 10)), (707055, (3, 4)), (707056, (2, 3))]:
    for count in counts:
        for copies in (0, 1, 3):
            record, used = scenario('threshold', copies, increment, count)
            checks.append(record); stubs.update(used)
for copies in (1, 3):
    for reset in (None, 400, 450):
        name = {None: 'already-unlocked', 400: 'reset-and-repeat', 450: 'reset-warmup'}[reset]
        record, used = scenario(name, copies, 707055, 4,
                                reset_at=reset, extras=True)
        checks.append(record); stubs.update(used)

fields = ('stateInfo', 'spCategory', 'categoryPriority', 'effectEndurance', 'motionInterval',
          'invocationConditionsStateChange1', 'accumuVal', 'accumuOverVal', 'accumuOverFireId',
          'dedupeAccumuTrigger', 'replaceSpEffectId', 'changeHpRate', 'changeHpPoint')
output = dict(schema=1, exeSha256=sha(inputs.raw), regulationSha256=inputs.x['hashes']['regulation.bin'],
    paramSha256=sha(inputs.param), animationSha256=tae['bundles'][0]['sha256'], hksSha256=sha(hks),
    root=7034500, leaf=7034502, events=events,
    rows={str(id): {k: spells[str(id)][k] for k in fields} for id in
          [7034500, 7034501, 7034502, 707050, 707051, 707052, 707053, 707055, 707056, 707057]},
    checks=checks, stubs=sorted(stubs), gameplayVerified=False)
a.output.write_text(json.dumps(output, indent=2) + '\n')
print('PASS:', len(checks), 'Executor recovery chains')
