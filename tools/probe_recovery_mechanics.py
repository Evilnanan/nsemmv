"""Trace Guardian's conditional healing bullets and recipient refresh timing.

Animation dispatch, Behavior resolution, emitter timing, effect insertion and HP
getters execute pinned PC instructions. Character identity and successful in-range
delivery are fixtures; this does not run collision detection or multiplayer.
"""
import argparse
import json
import math
import struct
from pathlib import Path
from unicorn.x86_const import *
from native_effect_runtime import BASE, OBJ, STOP, Chain, Inputs, sha

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('exe', type=Path)
p.add_argument('extracted', type=Path)
p.add_argument('assets', type=Path)
p.add_argument('animations', type=Path)
p.add_argument('output', type=Path)
a = p.parse_args()
inputs = Inputs(a.exe, a.extracted)
assets = json.loads(a.assets.read_text())
tae = json.loads(a.animations.read_text())
assert assets['hashes']['regulation.bin'] == inputs.x['hashes']['regulation.bin']
assert tae['bundles'][0]['sha256'] == '1410035ad79edb410fa41420ec259fcb4a1037d748c9c4a3b6ae8d1366c76d0f'
raw_tables = {name: path.read_bytes() for name, path in (
    ('Bullet', a.extracted.with_suffix('.Bullet.param')),
    ('BehaviorParam_PC', a.extracted.with_suffix('.BehaviorParam_PC.param')),
    ('EquipParamWeapon', a.assets.with_suffix('.EquipParamWeapon.param')))}
bullets = inputs.table(raw_tables['Bullet'], 0x100)
behaviors = inputs.table(raw_tables['BehaviorParam_PC'], 0x30)
weapons = inputs.table(raw_tables['EquipParamWeapon'], 0x298)
bullet = inputs.x['tables']['Bullet']['30901188']
behavior = inputs.x['tables']['BehaviorParam_PC']['700000808']
attack = inputs.x['tables']['AtkParam_Pc']['700000809']
assert behavior['refType'] == 1 and behavior['refId'] == 30901188
assert bullet['atkId_Bullet'] == 700000809 and bullet['spEffectId0'] == 7012002
assert bullet['hitRadius'] == bullet['hitRadiusMax'] == 15
assert bullet['numShoot'] == 1 and bullet['isEndlessHit'] == 0
assert bullet['HitBulletID'] == bullet['intervalCreateBulletId'] == -1
assert all(bullet['spEffectId' + str(i)] == 0 for i in range(1, 5))
assert attack['friendlyTarget'] == attack['selfTarget'] == 1
assert attack['opposeTarget'] == attack['disableHitSpEffect'] == 0
assert struct.unpack_from('<f', bullets[30901188], 0x18)[0] == bullet['shootInterval']
assert struct.unpack_from('<i', bullets[30901188], 0x60)[0] == bullet['spEffectIDForShooter'] == 0
events = []
for bundle in tae['bundles']:
    for track in bundle['taes']:
        if track['ID'] != 2901: continue
        for animation in track['animations']:
            for event in animation['events']:
                raw = bytes.fromhex(event['hex'])
                if event['Type'] == 2 and struct.unpack_from('<i', raw, 8)[0] == 7808:
                    assert struct.unpack_from('<h', raw, 14)[0] == 2046 and raw[13] == 1
                    events.append(dict(tae=2901, animation=animation['ID'], **event))
assert [(e['animation'], e['index']) for e in events] == [(610010, 8), (610011, 3)]


class Recovery(Chain):
    def __init__(self):
        super().__init__(inputs)
        self.requests, self.emissions, self.frame = [], [], 0
        # Real Behavior resolver at +328; the other virtuals supply a synthetic
        # equipped weapon / owner identity. No state predicate is substituted.
        for off, ptr in [(0x118, STOP + 0x201), (0x190, STOP + 0x200), (0x260, STOP + 0x200),
                         (0x328, BASE + 0x668b30), (0x320, STOP + 0x201),
                         (0x250, STOP + 0x202), (0x28, STOP + 0x201), (0x178, STOP + 0x200)]:
            self.q(OBJ + 0x6200 + off, ptr)
        self.q(OBJ + 0x6190, OBJ)

    def hook(self, u, address, size, user):
        pc = address - BASE
        def finish(value=0):
            u.reg_write(UC_X86_REG_RAX, value)
            sp = u.reg_read(UC_X86_REG_RSP)
            u.reg_write(UC_X86_REG_RIP, struct.unpack('<Q', u.mem_read(sp, 8))[0])
            u.reg_write(UC_X86_REG_RSP, sp + 8)
        if address in (STOP + 0x200, STOP + 0x201, STOP + 0x202):
            self.stubs.add('synthetic player virtuals and equipped weapon 1000')
            finish({STOP + 0x200: 0, STOP + 0x201: 1, STOP + 0x202: 1000}[address])
        elif pc in (0x4d1b20, 0x3d4180, 0x3d4c10, 0xea9a60, 0xea76f0, 0x66b2d0, 0x27d0640):
            self.stubs.add(hex(pc) + ' isolated actor context / hand identity / empty animation reference list')
            finish()
        elif pc == 0x3ced90:
            self.stubs.add('3CED90 isolated actor context')
            finish(OBJ + 0xd000)
        elif pc == 0xea7fc0:
            self.stubs.add('EA7FC0 actual equipped-weapon row lookup')
            id = u.reg_read(UC_X86_REG_RDX) & 0xffffffff
            u.mem_write(OBJ + 0xb000, weapons[id])
            u.mem_write(u.reg_read(UC_X86_REG_RCX), struct.pack('<IIQ', id, 0, OBJ + 0xb000))
            finish()
        elif pc == 0xe6fcb0:
            self.stubs.add('E6FCB0 actual Behavior row lookup')
            id = u.reg_read(UC_X86_REG_RDX) & 0xffffffff
            assert id == 700000808
            u.mem_write(OBJ + 0xb800, behaviors[id])
            self.q(u.reg_read(UC_X86_REG_RCX) + 8, OBJ + 0xb800)
            finish()
        elif pc == 0x3975d0:
            self.stubs.add('3975D0 Behavior request recorder; active/stop and conditional-state gates are native')
            payload = bytes(u.mem_read(u.reg_read(UC_X86_REG_R9), 18))
            self.requests.append(dict(behavior=u.reg_read(UC_X86_REG_RDX),
                                      active=bool(payload[16]), instant=bool(payload[17]), payload=payload.hex()))
            finish(1)
        elif pc == 0xe87800:
            self.stubs.add('E87800 actual Bullet row lookup')
            id = u.reg_read(UC_X86_REG_RDX) & 0xffffffff
            assert id == 30901188
            u.mem_write(OBJ + 0xb000, bullets[id])
            ptr = u.reg_read(UC_X86_REG_RCX)
            u.mem_write(ptr, struct.pack('<QI', OBJ + 0xb000, id))
            finish(ptr)
        elif pc == 0x347700:
            self.stubs.add('347700 successful projectile-emission recorder; collision delivery is a next-frame fixture')
            self.emissions.append(self.frame)
            finish(1)
        else:
            super().hook(u, address, size, user)

    def hp(self):
        # The optional physical owner affects damage/HUD paths, not these HP
        # restoration rows. Keep the live effect list intact in the real getter.
        self.q(OBJ + 0x10, 0)
        self.invoke(0x50b860, [OBJ] + [OBJ + 0x800 + i * 0x20 for i in range(11)] + [0])
        self.q(OBJ + 0x10, OBJ + 0x6000)
        return list(struct.unpack('<2f', self.u.mem_read(OBJ + 0x880, 8)))


checks = {'trigger': [], 'emissionAndRecovery': [], 'arrival': []}
stubs = set()
for event in events:
    for copies in (0, 1, 3):
        for active in (0, 1):
            c = Recovery()
            for _ in range(copies): c.insert(7012000)
            c.qualify(); c.update(0)
            c.q(OBJ + 0x8018, OBJ + 0x6000)
            c.q(OBJ + 0x8108, OBJ + 0x8200)
            c.u.mem_write(OBJ + 0x8118, bytes([active]))
            c.u.mem_write(OBJ + 0x811a, struct.pack('<H', 0x27))
            c.q(OBJ + 0x8120, OBJ + 0x8300)
            c.u.mem_write(OBJ + 0x8200, bytes.fromhex(event['hex']))
            c.invoke(0x40cd80, [OBJ + 0x8000, OBJ + 0x8100])
            assert len(c.requests) == bool(copies)
            if copies:
                assert c.requests[0]['behavior'] == 700000808
                assert c.requests[0]['active'] == bool(active) and not c.requests[0]['instant']
            checks['trigger'].append(dict(animation=event['animation'], equipmentCopies=copies,
                                           active=active, requests=c.requests))
            stubs.update(c.stubs)

for fps in (30, 60, 120):
    for copies in (1, 3):
        c = Recovery()
        slot = OBJ + 0x4000
        c.u.mem_write(slot + 0x329, b'\x01')
        c.u.mem_write(slot + 0x334, struct.pack('<I', 30901188))
        # Type 2 Enable=1 -> non-instant request -> +494=0. The constructor
        # starts the emission timer at zero. End of the source is external here.
        c.u.mem_write(slot + 0x494, b'\0')
        pending, heals, max_nodes = False, [], 0
        for frame in range(fps * 5):
            c.frame = frame
            if pending:
                for _ in range(copies): c.insert(7012002)
            c.qualify(); c.update(1 / fps)
            hp = c.hp()
            if any(hp):
                assert hp == [-10, -12]
                heals.append(dict(frame=frame, hp=hp))
            max_nodes = max(max_nodes, len(c.nodes()))
            before = len(c.emissions)
            if frame < fps * 3:
                c.invoke(0x343280, [slot], {UC_X86_REG_XMM1: 1 / fps})
            pending = len(c.emissions) > before
        assert max_nodes == 1 and c.nodes() == []
        assert len(c.emissions) == 10 and len(heals) == 4
        assert all(abs((right - left) / fps - .3) <= 1 / fps + 1e-6
                   for left, right in zip(c.emissions, c.emissions[1:]))
        assert all(abs((right['frame'] - left['frame']) / fps - 1) <= 1 / fps + 1e-6
                   for left, right in zip(heals, heals[1:]))
        assert heals[-1]['frame'] / fps > 3
        assert heals[-1]['frame'] / fps - (c.emissions[-1] + 1) / fps <= .7 + 2 / fps
        checks['emissionAndRecovery'].append(dict(fps=fps, simultaneousSources=copies, sourceStopsAt=3,
            emissions=c.emissions, heals=heals, maximumRecipientNodes=max_nodes, finalNodes=c.nodes()))
        stubs.update(c.stubs)

for arrivals in ([0], [0, 12], [0, 60], [0, 12, 24, 36, 48, 60, 72]):
    c = Recovery()
    heals = []
    for frame in range(180):
        if frame in arrivals: c.insert(7012002)
        c.qualify(); c.update(1 / 60)
        hp = c.hp()
        if any(hp): heals.append(dict(frame=frame, hp=hp))
    expected_count = 1 if arrivals in ([0], [0, 12]) else 2
    assert len(heals) == expected_count and all(h['hp'] == [-10, -12] for h in heals)
    if arrivals == [0, 60]: assert [h['frame'] for h in heals] == [0, 60]
    checks['arrival'].append(dict(fps=60, arrivals=arrivals, heals=heals, finalNodes=c.nodes()))
    stubs.update(c.stubs)

output = dict(schema=1, exeSha256=sha(inputs.raw), regulationSha256=inputs.x['hashes']['regulation.bin'],
    paramSha256=sha(inputs.param), companionSha256={k: sha(v) for k, v in raw_tables.items()},
    animationSha256=tae['bundles'][0]['sha256'], root=7012000, leaf=7012002, events=events,
    behaviorId=700000808, behavior={k: behavior[k] for k in ('refType', 'refId')},
    bulletId=30901188, bullet={k: bullet[k] for k in ('atkId_Bullet', 'spEffectId0', 'hitRadius',
        'hitRadiusMax', 'life', 'shootInterval', 'numShoot', 'isEndlessHit', 'HitBulletID', 'intervalCreateBulletId')},
    attack={k: attack[k] for k in ('friendlyTarget', 'selfTarget', 'opposeTarget', 'disableHitSpEffect')},
    checks=checks, stubs=sorted(stubs), gameplayVerified=False)
a.output.write_text(json.dumps(output, indent=2) + '\n')
print('PASS:', {k: len(v) for k, v in checks.items()})
