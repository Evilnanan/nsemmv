"""Trace Recluse's self-bleed qualification, HP settlement and attack lifecycle.

Runs pinned native accumulation, immunity, removal, HP getter/setter and effect
container code. Actor identity, network transport, neutral death-protection flags
and absent resistance-growth assets are fixtures, not a running expedition.
"""
import argparse
import json
import math
import struct
from pathlib import Path
from native_effect_runtime import BASE, OBJ, STOP, Chain, Inputs, sha
from unicorn.x86_const import *

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('exe', type=Path)
p.add_argument('extracted', type=Path)
p.add_argument('animations', type=Path)
p.add_argument('output', type=Path)
a = p.parse_args()
inputs = Inputs(a.exe, a.extracted)
tae = json.loads(a.animations.read_text())
assert tae['bundles'][0]['sha256'] == '1410035ad79edb410fa41420ec259fcb4a1037d748c9c4a3b6ae8d1366c76d0f'
r = inputs.spells
assert r['7032900']['stateInfo'] == r['7032901']['invocationConditionsStateChange1'] == 2206
assert r['7032901']['cycleOccurrenceSpEffectId'] == 7032902 and r['7032901']['effectEndurance'] == 0
assert r['7032902']['bloodAttackPower'] == 9999 and r['7032902']['changeHpRate'] == 20
assert r['7032902']['replaceSpEffectId'] == 7032903 and r['7032902']['stateInfo'] == 6
assert r['7032903']['spCategory'] == 10 and r['7032903']['effectEndurance'] == 30
assert math.isclose(r['7032903']['physicsAttackRate'], 1.16, abs_tol=1e-6)
assert r['9642']['disableBlood'] == 1

events = []
for bundle in tae['bundles']:
    for track in bundle['taes']:
        for animation in track['animations']:
            for e in animation['events']:
                if e['Type'] == 67 and struct.unpack_from('<i', bytes.fromhex(e['hex']))[0] == 7032901:
                    events.append(dict(tae=track['ID'], animation=animation['ID'], **e))
assert [(e['tae'],e['animation'],e['index']) for e in events] == [(2906,660000,3)]


class Bleed(Chain):
    def __init__(self, maximum=500, immune=False, equipment=1):
        super().__init__(inputs)
        self.q(OBJ + 0x6190, OBJ)
        self.q(OBJ + 0x63a0, STOP + 0x200)  # owner virtual +1a0: no growth params
        self.q(OBJ + 0x6410, STOP + 0x201)  # owner virtual +210: no damage exclusion
        self.q(OBJ + 0x9008, OBJ + 0x6000)  # ailment controller owner
        self.q(OBJ + 0xe008, OBJ + 0x6000)  # HP data owner
        self.q(OBJ + 0x61b8, OBJ + 0xf000)
        self.q(OBJ + 0xf008, OBJ + 0xf400)
        # Queue/debug-singleton identities only. Original branch predicates run.
        for address, value in [(BASE + 0x42d85f + 7 + 0x37f4662, OBJ + 0xe800),
                               (BASE + 0x427bfa + 8 + 0x37e7736, OBJ + 0xf800)]:
            self.mapped(self.u, 0, address, 8, 0, None)
            self.q(address, value)
        for off in (0x9018, 0x9034):
            self.u.mem_write(OBJ + off, struct.pack('<i', maximum))
        for _ in range(equipment): self.insert(7032900)
        if immune: self.insert(9642)
        self.qualify(); self.update(0)
        self.stubs.add('empty actor/HP/ailment objects; neutral death-protection flags and supplied starting resistance')

    def hook(self, u, address, size, user):
        pc = address - BASE
        def finish(value=0):
            u.reg_write(UC_X86_REG_RAX, value)
            sp = u.reg_read(UC_X86_REG_RSP)
            u.reg_write(UC_X86_REG_RIP, struct.unpack('<Q', u.mem_read(sp, 8))[0])
            u.reg_write(UC_X86_REG_RSP, sp + 8)
        if address in (STOP + 0x200, STOP + 0x201):
            self.stubs.add('owner virtual +1a0 no resistance-growth params; +210 no damage exclusion')
            finish()
        elif pc == 0x6ada30:
            self.stubs.add('6ADA30 ordinary resource-setter context')
            finish()
        elif pc == 0x3d4180:
            self.stubs.add('3D4180 player identity')
            finish(1)
        elif pc in (0x4e78a0, 0x4e78c0, 0xdf24d0):
            self.stubs.add(hex(pc) + ' network-message identity/transport only; no remote delivery')
            finish()
        else:
            super().hook(u, address, size, user)

    def apply_bleed(self):
        # Mirror 3DB410: insert first, then run status processing. A true return
        # removes that exact node immediately, without expiry replacement.
        index = self.insert(7032902)
        assert index < 0x80000000
        self.q(OBJ + 0x9800, self.lookup[7032902])
        self.u.mem_write(OBJ + 0x9908, struct.pack('<f', 1))
        self.u.mem_write(OBJ + 0x9938, struct.pack('<f', 1))
        rejected = bool(self.invoke(0x42d110, [OBJ + 0x9000, OBJ + 0x9800, OBJ + 0x9900]) & 255)
        if rejected: self.invoke(0x505280, [OBJ, index])
        return rejected

    def remaining(self):
        return struct.unpack('<i', self.u.mem_read(OBJ + 0x9018, 4))[0]

    def hp_packet(self, maximum):
        # No physical-owner invulnerability/remote state while aggregating. The
        # actual effect list and native bloodDamageRate multiplier remain live.
        self.q(OBJ + 0x10, 0)
        self.invoke(0x506ec0, [OBJ, maximum, OBJ + 0x800, OBJ + 0x808, OBJ + 0x820, 0])
        self.q(OBJ + 0x10, OBJ + 0x6000)
        return list(struct.unpack('<7i', self.u.mem_read(OBJ + 0x820, 28)))

    def hp_settle(self, current, maximum, delta):
        self.u.mem_write(OBJ + 0xe140, struct.pack('<ii', current, maximum))
        # Actual 431DDF caller arguments: R8=1, R9=0, restore-bar scale=0,
        # time scale=1, final flag=1. Other packet slots are metadata here.
        self.invoke(0x426130, [OBJ + 0xe000, delta, 1, 0, 0, 0x3f800000, 1])
        return struct.unpack('<i', self.u.mem_read(OBJ + 0xe140, 4))[0]


checks = dict(onset=[], hp=[], lifecycle=[])
stubs = set()
for immune in (False, True):
    for maximum in (500, 9998, 9999, 10000):
        c = Bleed(maximum, immune)
        rejected = c.apply_bleed()
        assert rejected == (immune or maximum > 9999)
        assert c.remaining() == (maximum if immune or maximum <= 9999 else 1)
        grants = []
        for frame in range(20):
            pending, c.emitted = c.emitted, []
            for id in pending: c.insert(id)
            c.qualify(); c.update(1 / 60)
            if c.emitted: grants.append(dict(frame=frame, ids=c.emitted.copy()))
        assert any(7032903 in g['ids'] for g in grants) == (not rejected)
        rate = c.attack()[0]
        assert math.isclose(rate, 1 if rejected else 1.16, abs_tol=1e-6)
        checks['onset'].append(dict(immune=immune, startingResistance=maximum, rejected=rejected,
                                   remaining=c.remaining(), grants=grants, attack=rate))
        stubs.update(c.stubs)

for maximum, current in [(99,99),(100,100),(137,137),(1000,1000),(100,21),(100,20),(100,1)]:
    c = Bleed()
    assert not c.apply_bleed()
    c.qualify(); c.update(0)
    packet = c.hp_packet(maximum)
    expected = -math.trunc(maximum * .2)
    assert packet == [expected, 0, expected, 0, expected, 4, 0]
    after = c.hp_settle(current, maximum, packet[0])
    assert after == max(0, current + expected)
    c.qualify(); c.update(1 / 60)
    assert c.hp_packet(maximum)[0] == 0
    checks['hp'].append(dict(maximum=maximum, current=current, packet=packet, after=after))
    stubs.update(c.stubs)

for name, equipment, immune, resistance, casts in [
        ('no-equipment',0,False,500,[0]), ('single',1,False,500,[0]),
        ('repeat',1,False,500,[0,300]), ('duplicate-equipment',3,False,500,[0,300]),
        ('immune',1,True,500,[0]), ('below-onset',1,False,10000,[0]),
        ('later-onset',1,False,10000,[0,300])]:
    c = Bleed(resistance, immune, equipment)
    attack_changes, attempts, damage = [], [], []
    previous = 1.0
    for frame in range(2200):
        pending, c.emitted = c.emitted, []
        for id in pending:
            if id == 7032902:
                attempts.append(dict(frame=frame, rejected=c.apply_bleed()))
            else:
                c.insert(id)
        if frame in casts: c.insert(7032901)
        c.qualify(); c.update(1 / 60)
        packet = c.hp_packet(1000)
        if packet[0]: damage.append(dict(frame=frame, delta=packet[0]))
        rate = c.attack()[0]
        if not math.isclose(rate, previous, abs_tol=1e-6):
            attack_changes.append(dict(frame=frame, rate=rate,
                count=sum(n['id'] == 7032903 for n in c.nodes())))
        previous = rate
    success = sum(not t['rejected'] for t in attempts)
    expected = 0 if not equipment or immune else len(casts) - int(resistance > 9999)
    assert success == expected and len(damage) == expected
    assert all(d['delta'] == -200 for d in damage)
    assert [r['count'] for r in attack_changes] == ([1,2,1,0] if expected == 2 else ([1,0] if expected == 1 else []))
    assert all(math.isclose(r['rate'], 1.16 ** r['count'], abs_tol=1e-6) for r in attack_changes)
    checks['lifecycle'].append(dict(name=name, equipmentCopies=equipment, immune=immune,
        startingResistance=resistance, casts=casts, fps=60, attempts=attempts,
        damage=damage, attackChanges=attack_changes))
    stubs.update(c.stubs)

output = dict(schema=1, exeSha256=sha(inputs.raw), regulationSha256=inputs.x['hashes']['regulation.bin'],
    paramSha256=sha(inputs.param), animationSha256=tae['bundles'][0]['sha256'],
    root=7032900, seeds=[7032901], leaves=[7032902,7032903], events=events,
    checks=checks, stubs=sorted(stubs), gameplayVerified=False)
a.output.write_text(json.dumps(output, indent=2) + '\n')
print('PASS:', {k: len(v) for k,v in checks.items()}, 'Recluse self-bleed checks')
