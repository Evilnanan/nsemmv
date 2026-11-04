"""Execute Executor ability recovery and amplification after status removal.

Player identity, expired-status inputs and next-frame grant delivery are fixtures.
The native identity predicate, removal dispatch, real PARAM selection, effect
container, qualification, timers and numeric getters execute unchanged.
"""
import argparse
import json
import math
import struct
from pathlib import Path
from unicorn.x86_const import *
from native_effect_runtime import BASE, OBJ, Chain, Inputs, sha

p = argparse.ArgumentParser(description=__doc__)
for name in ('exe', 'extracted', 'systems', 'output'):
    p.add_argument(name, type=Path)
a = p.parse_args()
inputs = Inputs(a.exe, a.extracted)
systems = json.loads(a.systems.read_text())
assert systems['hashes']['regulation.bin'] == inputs.x['hashes']['regulation.bin']
system_raw = a.systems.with_suffix('.PlayerCommonParam.param').read_bytes()
assert struct.unpack_from('<H', system_raw, 10)[0] == 1
assert struct.unpack_from('<i', system_raw, 0x40)[0] == 0
offset = struct.unpack_from('<Q', system_raw, 0x48)[0]
system_row = system_raw[offset:offset + 0x400]
for field, off, id in [('tenacityEffectId', 0x178, 707070), ('tenacityRelicAddEffectId', 0x188, 7501000)]:
    assert systems['tables']['PlayerCommonParam']['0'][field] == id
    assert struct.unpack_from('<i', system_row, off)[0] == id
spells = inputs.spells
assert spells['7500700']['stateInfo'] == 2397
assert spells['7501100']['stateInfo'] == 2083
assert spells['7501000']['replaceSpEffectId'] == 7500701
assert spells['7501000']['cycleOccurrenceSpEffectId'] == 7501101
assert spells['7500701']['replaceSpEffectId'] == 7500702
assert spells['7501101']['replaceSpEffectId'] == 7501102
assert spells['707070']['replaceSpEffectId'] == 707071
for id in (7500701, 7500702):
    r = spells[str(id)]
    assert r['invocationConditionsStateChange1'] == 2397
    assert math.isclose(r['changeHpRate'], -.27, rel_tol=1e-6)
    assert r['changeHpPoint'] == -3 and r['motionInterval'] == 1
assert spells['7500701']['effectEndurance'] + spells['7500702']['effectEndurance'] == 60
for id in (7501101, 7501102):
    assert spells[str(id)]['invocationConditionsStateChange1'] == 2083
assert spells['7501101']['effectEndurance'] + spells['7501102']['effectEndurance'] == 20
attack_fields = ('physicsAttackRate', 'magicAttackRate', 'fireAttackRate', 'thunderAttackRate', 'darkAttackRate')
for id, rate in [(707070, 1.2), (707071, 1.2), (7501101, 1.05), (7501102, 1.05)]:
    assert all(math.isclose(spells[str(id)][k], rate, rel_tol=1e-6) for k in attack_fields)
resist_fields = ('changePoisonResistPoint', 'changeDiseaseResistPoint', 'changeBloodResistPoint',
                'changeCurseResistPoint', 'changeFreezeResistPoint', 'changeSleepResistPoint', 'changeMadnessResistPoint')
assert all(spells['7501100'][k] == -80 for k in resist_fields)


class Tenacity(Chain):
    def __init__(self, hero=8):
        super().__init__(inputs)
        # Actual PlayerIns vtable entries +148 and +178: predicate compares the
        # real hero getter to 8; only the backing player-data byte is a fixture.
        self.q(OBJ + 0x6348, BASE + 0x66d800)
        self.q(OBJ + 0x6378, BASE + 0x66c320)
        self.q(OBJ + 0x65a0, OBJ + 0xe000)
        self.u.mem_write(OBJ + 0xe0c7, bytes([hero]))
        self.stubs.add('synthetic PlayerIns owner +5A0 player-data pointer; hero byte +C7')

    def hook(self, u, address, size, user):
        if address - BASE == 0xe81650:
            self.stubs.add('E81650 actual PlayerCommonParam row 0 lookup')
            ptr = u.reg_read(UC_X86_REG_RCX)
            u.mem_write(OBJ + 0xf000, system_row)
            u.mem_write(ptr, struct.pack('<QI', OBJ + 0xf000, 0))
            u.reg_write(UC_X86_REG_RAX, ptr)
            sp = u.reg_read(UC_X86_REG_RSP)
            u.reg_write(UC_X86_REG_RIP, struct.unpack('<Q', u.mem_read(sp, 8))[0])
            u.reg_write(UC_X86_REG_RSP, sp + 8)
        else:
            super().hook(u, address, size, user)

    def hp(self):
        # Optional owner handling concerns damage reactions/HUD, not recovery.
        self.q(OBJ + 0x10, 0)
        self.invoke(0x50b860, [OBJ] + [OBJ + 0x800 + i * 0x20 for i in range(11)] + [0])
        self.q(OBJ + 0x10, OBJ + 0x6000)
        return [round(v, 6) for v in struct.unpack('<2f', self.u.mem_read(OBJ + 0x880, 8))]

    def resistance(self):
        result = []
        for kind in range(7):
            self.invoke(0x507de0, [OBJ, kind])
            result.append(struct.unpack('<f', self.u.reg_read(UC_X86_REG_XMM0).to_bytes(16, 'little')[:4])[0])
        return result


checks = dict(trigger=[], lifecycle=[], hp=[], resistance=[])
stubs = set()
statuses = {103: 2, 104: 5, 102: 6, 109: 116, 105: 260, 108: 436, 107: 437}
for hero in range(11):
    for ids in [*[ [id] for id in statuses ], [100], list(statuses)]:
        c = Tenacity(hero)
        for id in ids: c.insert(id)
        assert all(spells[str(id)]['effectEndurance'] == 0 for id in ids)
        for _ in range(3): c.qualify(); c.update(.1)
        assert c.emitted == ([707070, 7501000] if hero == 8 and ids != [100] else [])
        checks['trigger'].append(dict(hero=hero, expiredIds=ids, emitted=c.emitted.copy()))
        stubs.update(c.stubs)


def lifecycle(recovery, boost, arrivals, fps=10):
    c = Tenacity()
    for _ in range(recovery): c.insert(7500700)
    for _ in range(boost): c.insert(7501100)
    c.qualify(); c.update(0)
    heals, grants, rates = [], [], []
    previous = None
    for tick in range(max(arrivals) + 63 * fps):
        pending, c.emitted = c.emitted, []
        for id in pending: c.insert(id)
        for _ in range(arrivals.count(tick)): c.insert(103)
        c.qualify(); c.update(1 / fps)
        if c.emitted: grants.append(dict(tick=tick, ids=c.emitted.copy()))
        hp = c.hp()
        if any(hp): heals.append(dict(tick=tick, hp=hp))
        if tick % fps == 0:
            values = [round(v, 6) for v in c.attack()]
            if values != previous: rates.append(dict(tick=tick, rates=values))
            previous = values
    assert all(n['id'] in (7500700, 7501100) or
               (not boost and n['id'] == 7501101 and n['flags'] & 1) for n in c.nodes())
    assert bool(heals) == bool(recovery)
    if recovery:
        assert 59 <= (heals[-1]['tick'] - max(arrivals)) / fps <= 61
        assert all(h['hp'][1] in (-3, -6) for h in heals)
    maximum = max(v['rates'][0] for v in rates)
    expected = 1.26 if boost else 1.2
    if len(set(arrivals)) > 1 and max(arrivals) < 19 * fps: expected **= 2
    assert math.isclose(maximum, expected, rel_tol=1e-6), (recovery, boost, arrivals, rates)
    assert c.resistance() == ([-80.] * 7 if boost else [0.] * 7)
    stubs.update(c.stubs)
    return dict(recoveryCopies=recovery, boostCopies=boost, arrivals=arrivals, fps=fps,
                heals=heals, grants=grants, attackChanges=rates, finalNodes=c.nodes())


for recovery, boost in [(0, 0), (1, 0), (0, 1), (1, 1), (3, 3)]:
    checks['lifecycle'].append(lifecycle(recovery, boost, [0]))
for copies in (1, 3):
    for arrivals in ([0, 0], [0, 50], [0, 200]):
        checks['lifecycle'].append(lifecycle(copies, copies, arrivals))
for fps in (30, 60):
    checks['lifecycle'].append(lifecycle(1, 1, [0], fps))
single = next(c for c in checks['lifecycle'] if c['recoveryCopies'] == c['boostCopies'] == 1 and c['arrivals'] == [0])
triple = next(c for c in checks['lifecycle'] if c['recoveryCopies'] == 3 and c['arrivals'] == [0])
assert single['heals'] == triple['heals'] and single['attackChanges'] == triple['attackChanges']
for copies in (1, 3):
    repeated = next(c for c in checks['lifecycle'] if c['recoveryCopies'] == copies and c['arrivals'] == [0, 50])
    assert any(h['hp'] == [-.54, -6.] for h in repeated['heals'])
    assert any(all(math.isclose(v, 1.5876, abs_tol=1e-6) for v in r['rates']) for r in repeated['attackChanges'])
for copies in (0, 1, 3):
    c = Tenacity()
    for _ in range(copies): c.insert(7501100)
    c.qualify(); c.update(0)
    actual = c.resistance()
    assert actual == ([-80.] * 7 if copies else [0.] * 7)
    checks['resistance'].append(dict(copies=copies, values=actual))
    stubs.update(c.stubs)
for maximum in (1, 99, 137, 1000, 2345):
    c = Tenacity(); c.insert(7500700); c.qualify(); c.update(0)
    c.insert(7500701); c.qualify(); c.update(0)
    c.q(OBJ + 0x10, 0)
    c.invoke(0x506ec0, [OBJ, maximum, OBJ + 0x800, OBJ + 0x808, OBJ + 0x820, 0])
    packet = list(struct.unpack('<7i', c.u.mem_read(OBJ + 0x820, 28)))
    assert packet[0] == math.trunc(maximum * .0027 + 3), (maximum, packet)
    checks['hp'].append(dict(maximum=maximum, packet=packet))
    stubs.update(c.stubs)
fields = ('stateInfo', 'spCategory', 'effectEndurance', 'motionInterval', 'replaceSpEffectId',
          'cycleOccurrenceSpEffectId', 'invocationConditionsStateChange1', 'changeHpRate',
          'changeHpPoint', *attack_fields, *resist_fields)
output = dict(schema=1, exeSha256=sha(inputs.raw), regulationSha256=inputs.x['hashes']['regulation.bin'],
    paramSha256=sha(inputs.param), playerCommonSha256=sha(system_raw), roots=[7500700, 7501100],
    playerCommon={k: systems['tables']['PlayerCommonParam']['0'][k] for k in ('tenacityEffectId', 'tenacityRelicAddEffectId')},
    statusTypes=statuses, rows={str(id): {k: spells[str(id)][k] for k in fields} for id in
        [7500700, 7501100, 7501000, 7500701, 7500702, 7501101, 7501102, 707070, 707071]},
    checks=checks, stubs=sorted(stubs), gameplayVerified=False)
a.output.write_text(json.dumps(output, indent=2) + '\n')
print('PASS:', {k: len(v) for k, v in checks.items()}, flush=True)
