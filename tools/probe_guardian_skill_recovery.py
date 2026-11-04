"""Trace Guardian skill healing, its action gates and overlapping arrivals.

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
bullet = inputs.x['tables']['Bullet']['30901071']
behavior = inputs.x['tables']['BehaviorParam_PC']['600000071']
attack = inputs.x['tables']['AtkParam_Pc']['600000071']
leaf = inputs.spells['7011301']
assert inputs.spells['7011300']['stateInfo'] == 2081
assert behavior['refType'] == 1 and behavior['refId'] == 30901071
assert bullet['atkId_Bullet'] == 600000071 and bullet['spEffectId0'] == 7011301
assert bullet['hitRadius'] == 8 and bullet['numShoot'] == 1
assert bullet['shootInterval'] == 1 and bullet['spEffectIDForShooter'] == 0
assert bullet['HitBulletID'] == bullet['intervalCreateBulletId'] == -1
assert all(bullet['spEffectId' + str(i)] == 0 for i in range(1, 5))
assert attack['friendlyTarget'] == attack['selfTarget'] == 1
assert attack['opposeTarget'] == attack['disableHitSpEffect'] == 0
assert leaf['effectTargetSelfTarget'] == leaf['effectTargetFriendlyTarget'] == 1
assert leaf['effectTargetOpposeTarget'] == leaf['effectTargetPcDeceased'] == 0
assert leaf['changeHpRate'] == -15 and leaf['changeHpPoint'] == 0
assert math.isclose(leaf['effectEndurance'],.1,abs_tol=1e-6)
assert math.isclose(leaf['motionInterval'],.2,abs_tol=1e-6)
assert leaf['spCategory'] == 20
assert struct.unpack_from('<f',bullets[30901071],0x18)[0] == 1
assert struct.unpack_from('<i',bullets[30901071],0x60)[0] == 0
events = []
for bundle in tae['bundles']:
    for track in bundle['taes']:
        if track['ID'] != 2901: continue
        for animation in track['animations']:
            for event in animation['events']:
                raw = bytes.fromhex(event['hex'])
                if event['Type'] == 2 and struct.unpack_from('<i',raw,8)[0] == 6071:
                    assert struct.unpack_from('<h',raw,14)[0] == 2081 and raw[13] == 0
                    events.append(dict(tae=2901,animation=animation['ID'],**event))
assert [(e['animation'],e['index']) for e in events] == [(510000,85),(510005,74)]

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
            assert id == 600000071
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
            assert id == 30901071
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


checks = dict(trigger=[], emissionAndRecovery=[], hp=[], arrival=[])
stubs = set()
for event in events:
    for copies in (0,1,3):
        for active in (0,1):
            c = Recovery()
            for _ in range(copies): c.insert(7011300)
            c.qualify(); c.update(0)
            c.q(OBJ+0x8018,OBJ+0x6000);c.q(OBJ+0x8108,OBJ+0x8200)
            c.u.mem_write(OBJ+0x8118,bytes([active]));c.u.mem_write(OBJ+0x811a,struct.pack('<H',0x27))
            c.q(OBJ+0x8120,OBJ+0x8300);c.u.mem_write(OBJ+0x8200,bytes.fromhex(event['hex']))
            c.invoke(0x40cd80,[OBJ+0x8000,OBJ+0x8100])
            assert len(c.requests) == bool(copies and active)
            if c.requests: assert c.requests[0]['behavior'] == 600000071 and c.requests[0]['instant']
            checks['trigger'].append(dict(animation=event['animation'],equipmentCopies=copies,active=active,requests=c.requests))
            stubs.update(c.stubs)

for fps in (30,60,120):
    for copies in (1,3):
        c = Recovery();slot = OBJ+0x4000
        c.u.mem_write(slot+0x329,b'\x01');c.u.mem_write(slot+0x334,struct.pack('<I',30901071))
        c.u.mem_write(slot+0x494,b'\x01')
        pending, heals = False, []
        for frame in range(fps*2):
            if pending:
                for _ in range(copies): c.insert(7011301)
                pending = False
            c.frame = frame;c.qualify();c.update(1/fps)
            hp = c.hp()
            if any(hp): heals.append(dict(frame=frame,hp=hp))
            c.invoke(0x343280,[slot],{UC_X86_REG_XMM1:1/fps})
            if c.emissions and c.emissions[-1] == frame: pending = True
        assert c.emissions == [0] and heals == [dict(frame=1,hp=[-15.,0.])]
        assert c.nodes() == []
        checks['emissionAndRecovery'].append(dict(fps=fps,simultaneousSources=copies,emissions=c.emissions,heals=heals))
        stubs.update(c.stubs)

for maximum in (1,99,137,1000):
    c = Recovery();c.insert(7011301);c.qualify();c.update(0)
    c.q(OBJ+0x10,0)
    c.invoke(0x506ec0,[OBJ,maximum,OBJ+0x800,OBJ+0x808,OBJ+0x820,0])
    packet = list(struct.unpack('<7i',c.u.mem_read(OBJ+0x820,28)))
    assert packet[0] == math.trunc(maximum*.15)
    checks['hp'].append(dict(maximum=maximum,packet=packet))
    stubs.update(c.stubs)
for arrivals in ([0],[0,0,0],[0,3],[0,6],[0,12],list(range(0,31,3))):
    c = Recovery();heals=[]
    for frame in range(90):
        for _ in range(arrivals.count(frame)):c.insert(7011301)
        c.qualify();c.update(1/60)
        hp = c.hp()
        if any(hp):heals.append(dict(frame=frame,hp=hp))
    assert all(h['hp'] == [-15.,0.] for h in heals)
    assert c.nodes() == []
    if arrivals in ([0],[0,0,0],[0,3]):assert heals == [dict(frame=0,hp=[-15.,0.])]
    if arrivals == [0,12]:assert [h['frame'] for h in heals] == [0,12]
    checks['arrival'].append(dict(arrivals=arrivals,fps=60,heals=heals))
    stubs.update(c.stubs)
output = dict(schema=1,exeSha256=sha(inputs.raw),regulationSha256=inputs.x['hashes']['regulation.bin'],
    paramSha256=sha(inputs.param),animationSha256=tae['bundles'][0]['sha256'],
    root=7011300,leaf=7011301,events=events,behavior=behavior,
    bullet={k:bullet[k] for k in ['hitRadius','shootInterval','life','spEffectId0','spEffectIDForShooter','atkId_Bullet']},
    targetFlags={k:attack[k] for k in ['selfTarget','friendlyTarget','opposeTarget']},
    checks=checks,stubs=sorted(stubs),gameplayVerified=False)
a.output.write_text(json.dumps(output,indent=2)+'\n')
print('PASS:',{k:len(v) for k,v in checks.items()},'Guardian skill recovery checks')
