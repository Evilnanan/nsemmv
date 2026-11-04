"""Trace Guardian skill protection, its action gates and overlapping arrivals.

Animation dispatch, Behavior resolution, emitter timing, effect insertion and defense
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
bullet = inputs.x['tables']['Bullet']['30901070']
behavior = inputs.x['tables']['BehaviorParam_PC']['600000070']
attack = inputs.x['tables']['AtkParam_Pc']['600000070']
leaf=inputs.spells['7500101']
assert inputs.spells['7500100']['stateInfo']==2392
assert behavior['refType']==1 and behavior['refId']==30901070
assert bullet['atkId_Bullet']==600000070 and bullet['spEffectId0']==7500101
assert bullet['hitRadius']==8 and bullet['numShoot']==1 and bullet['life']==1
assert bullet['shootInterval']==1 and bullet['spEffectIDForShooter']==0
assert bullet['HitBulletID']==bullet['intervalCreateBulletId']==-1
assert all(bullet['spEffectId'+str(i)]==0 for i in range(1,5))
assert attack['friendlyTarget']==attack['selfTarget']==1
assert attack['opposeTarget']==attack['disableHitSpEffect']==0
assert leaf['effectTargetSelfTarget']==leaf['effectTargetFriendlyTarget']==1
assert leaf['effectTargetOpposeTarget']==leaf['effectTargetPcDeceased']==0
assert leaf['spCategory']==20 and leaf['effectEndurance']==30
assert all(math.isclose(leaf[k],.82,rel_tol=1e-6) for k in
 ['neutralDamageCutRate','slashDamageCutRate','blowDamageCutRate','thrustDamageCutRate',
  'magicDamageCutRate','fireDamageCutRate','thunderDamageCutRate','darkDamageCutRate'])
events=[]
for bundle in tae['bundles']:
 for track in bundle['taes']:
  if track['ID']!=2901:continue
  for animation in track['animations']:
   for event in animation['events']:
    raw=bytes.fromhex(event['hex'])
    if event['Type']==2 and struct.unpack_from('<i',raw,8)[0]==6070:
     assert struct.unpack_from('<h',raw,14)[0]==2392 and raw[13]==0
     events.append(dict(tae=2901,animation=animation['ID'],**event))
assert [(e['animation'],e['index']) for e in events]==[(510000,21),(510005,3)]
class Protection(Chain):
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
            assert id == 600000070
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
            assert id == 30901070
            u.mem_write(OBJ + 0xb000, bullets[id])
            ptr = u.reg_read(UC_X86_REG_RCX)
            u.mem_write(ptr, struct.pack('<QI', OBJ + 0xb000, id))
            finish(ptr)
        elif pc == 0x347700:
            self.stubs.add('347700 successful projectile-emission recorder; receiver arrivals are separate fixtures')
            self.emissions.append(self.frame)
            finish(1)
        else:
            super().hook(u, address, size, user)

    def defense(self):
        self.u.mem_write(OBJ+0x800,bytes(0x200))
        self.invoke(0x503800,[OBJ,OBJ+0x500,OBJ+0x520,OBJ+0x540,OBJ+0x800])
        return list(struct.unpack('<5f',self.u.mem_read(OBJ+0x500,20)))

checks=dict(trigger=[],emission=[],lifecycle=[]);stubs=set()
for event in events:
    for copies in (0,1,3):
        for active in (0,1):
            c = Protection()
            for _ in range(copies): c.insert(7500100)
            c.qualify(); c.update(0)
            c.q(OBJ+0x8018,OBJ+0x6000);c.q(OBJ+0x8108,OBJ+0x8200)
            c.u.mem_write(OBJ+0x8118,bytes([active]));c.u.mem_write(OBJ+0x811a,struct.pack('<H',0x27))
            c.q(OBJ+0x8120,OBJ+0x8300);c.u.mem_write(OBJ+0x8200,bytes.fromhex(event['hex']))
            c.invoke(0x40cd80,[OBJ+0x8000,OBJ+0x8100])
            assert len(c.requests) == bool(copies and active)
            if c.requests: assert c.requests[0]['behavior'] == 600000070 and c.requests[0]['instant']
            checks['trigger'].append(dict(animation=event['animation'],equipmentCopies=copies,active=active,requests=c.requests))
            stubs.update(c.stubs)

for fps in (30,60,120):
 c=Protection();slot=OBJ+0x4000
 c.u.mem_write(slot+0x329,b'\x01');c.u.mem_write(slot+0x334,struct.pack('<I',30901070))
 c.u.mem_write(slot+0x494,b'\x01')
 for frame in range(fps*2):
  c.frame=frame;c.invoke(0x343280,[slot],{UC_X86_REG_XMM1:1/fps})
 assert c.emissions==[0]
 checks['emission'].append(dict(fps=fps,emissions=c.emissions));stubs.update(c.stubs)
for copies in (1,3):
 for arrivals in ([0],[0,0,0],[0,80]):
  c=Protection();changes=[];previous=None
  for tick in range(220):
   for _ in range(arrivals.count(tick)*copies):c.insert(7500101)
   c.qualify();c.update(.25);values=[round(v,5) for v in c.defense()]
   if values!=previous:changes.append(dict(tick=tick,incoming=values));previous=values
  assert c.nodes()==[] and len(changes)==2
  assert changes[0]['incoming']==[.82]*5 and changes[-1]['incoming']==[1]*5
  assert abs(changes[-1]['tick']*.25-(max(arrivals)*.25+30))<=.5
  checks['lifecycle'].append(dict(copies=copies,arrivals=arrivals,dt=.25,changes=changes));stubs.update(c.stubs)
output=dict(schema=1,exeSha256=sha(inputs.raw),regulationSha256=inputs.x['hashes']['regulation.bin'],
 paramSha256=sha(inputs.param),animationSha256=tae['bundles'][0]['sha256'],root=7500100,leaf=7500101,
 events=events,behavior=behavior,bullet={k:bullet[k] for k in ['hitRadius','shootInterval','life','spEffectId0','spEffectIDForShooter','atkId_Bullet']},
 targetFlags={k:attack[k] for k in ['selfTarget','friendlyTarget','opposeTarget']},checks=checks,stubs=sorted(stubs),gameplayVerified=False)
a.output.write_text(json.dumps(output,indent=2)+'\n')
print('PASS:',{k:len(v) for k,v in checks.items()})
