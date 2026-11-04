"""Trace Executor's skill-only attack bonus and hit-triggered damage penalty.

Pinned instructions execute animation dispatch, held status maintenance, effect
qualification, hit filtering, replacement and numeric getters. Hit delivery and
chosen animation inputs are fixtures, not a live combat or network test.
"""
import argparse,json,struct,math
from pathlib import Path
from unicorn.x86_const import *
from native_effect_runtime import BASE,OBJ,Chain,Inputs,sha
p=argparse.ArgumentParser(description=__doc__)
for arg in ('exe','extracted','assets','animations','output'):p.add_argument(arg,type=Path)
a=p.parse_args();inputs=Inputs(a.exe,a.extracted)
assets=json.loads(a.assets.read_text());tae=json.loads(a.animations.read_text())
assert assets['hashes']['regulation.bin']==inputs.x['hashes']['regulation.bin']
assert tae['bundles'][0]['sha256']=='1410035ad79edb410fa41420ec259fcb4a1037d748c9c4a3b6ae8d1366c76d0f'
weapon_raw=a.assets.with_suffix('.EquipParamWeapon.param').read_bytes()
weapons=inputs.table(weapon_raw,0x298)
weapon_ids={}
for id,row in assets['tables']['EquipParamWeapon'].items():weapon_ids.setdefault(int(row['wepType']),int(id))
attack_raw=a.extracted.with_suffix('.AtkParam_Pc.param').read_bytes()
attack_rows=[attack_raw[off:off+0x1d0] for k in range(struct.unpack_from('<H',attack_raw,10)[0])
    if struct.unpack_from('<i',attack_raw,0x40+k*24)[0]==10000
    for off in [struct.unpack_from('<Q',attack_raw,0x48+k*24)[0]]]
assert len(attack_rows)==1
r=inputs.spells
assert r['7034400']['stateInfo']==2269
assert r['7034401']['cycleOccurrenceSpEffectId']==7034402 and r['7034401']['invocationConditionsStateChange1']==2269
assert r['7034402']['invocationConditionsStateChange1']==609 and r['707060']['stateInfo']==609
assert r['7034402']['magicSubCategoryChange1']==122 and r['7034402']['atkOccurrenceSpEffectId']==7034403
assert r['7034402']['effectEndurance']==6 and r['7034403']['effectEndurance']==5
assert r['7034403']['effectTargetAttacker']==1
assert all(r[str(i)]['spCategory']==20 for i in range(7034400,7034404))
events=[dict(tae=t['ID'],animation=an['ID'],**e) for b in tae['bundles'] for t in b['taes']
 for an in t['animations'] for e in an['events'] if e['Type']==67 and
 struct.unpack_from('<i',bytes.fromhex(e['hex']))[0] in (7034401,7034404,707060)]
assert any(e['tae']==2907 and e['animation']==571000 and e['index']==26 for e in events)
class Blade(Chain):
    def __init__(self):
        super().__init__(inputs)
        self.tae_requests = []
        self.q(OBJ + 0x6190, OBJ)
        self.q(OBJ + 0xe018, OBJ + 0x6000)
        self.q(OBJ + 0xe108, OBJ + 0xe200)

    def event(self, id):
        self.u.mem_write(OBJ + 0xe200, struct.pack('<i', id) + bytes(12))
        self.invoke(0x40ff20, [OBJ + 0xe000, OBJ + 0xe100, 1])
        for id in self.tae_requests: self.insert(id)
        self.tae_requests.clear()

    def tagged_attack(self, tag=122, kind=0):
        self.u.mem_write(OBJ+0x800, bytes(0x200))
        self.u.mem_write(OBJ+0x808, struct.pack('<iiB',40000,1,kind))
        self.u.mem_write(OBJ+0x814, (1 << tag if tag else 0).to_bytes(32,'little'))
        self.invoke(0x502830,[OBJ,OBJ+0x800,-1,-1])
        return [struct.unpack('<f',self.u.mem_read(OBJ+0x800+k,4))[0] for k in (0x90,0xa4,0xa8,0xac,0xb0)]

    def defense(self):
        self.u.mem_write(OBJ+0x800, bytes(0x200))
        self.invoke(0x503800,[OBJ,OBJ+0x500,OBJ+0x520,OBJ+0x540,OBJ+0x800])
        return list(struct.unpack('<5f',self.u.mem_read(OBJ+0x500,20)))

    def hook(self, u, address, size, user):
        pc = address - BASE
        def finish(value=0):
            u.reg_write(UC_X86_REG_RAX, value)
            sp = u.reg_read(UC_X86_REG_RSP)
            u.reg_write(UC_X86_REG_RIP, struct.unpack('<Q', u.mem_read(sp, 8))[0])
            u.reg_write(UC_X86_REG_RSP, sp + 8)
        if pc in (0x3ced90, 0x4d1b20, 0x3c8be0):
            self.stubs.add('3CED90/4D1B20 neutral animation owner; 3C8BE0 next-qualification grant recorder')
            if pc == 0x3c8be0: self.tae_requests.append(u.reg_read(UC_X86_REG_RDX) & 0xffffffff)
            finish(OBJ + 0xd000 if pc == 0x3ced90 else 0)
        elif pc == 0xe6d630:
            if u.reg_read(UC_X86_REG_R8) == 40000:
                self.stubs.add('E6D630 absent damage-row lookup for isolated attack getter')
                finish(u.reg_read(UC_X86_REG_RCX))
                return
            assert u.reg_read(UC_X86_REG_R8) == 10000 and u.reg_read(UC_X86_REG_RDX) == 1
            self.stubs.add('E6D630 unique actual AtkParam_Pc/10000 row lookup')
            wrapper = u.reg_read(UC_X86_REG_RCX)
            u.mem_write(OBJ + 0xb000, attack_rows[0])
            self.q(wrapper + 0x10, OBJ + 0xb000)
            finish(wrapper)
        elif pc == 0xea7fc0:
            id = u.reg_read(UC_X86_REG_RDX) & 0xffffffff
            self.stubs.add('EA7FC0 actual EquipParamWeapon row lookup')
            wrapper = u.reg_read(UC_X86_REG_RCX)
            u.mem_write(OBJ + 0xb800, weapons[id])
            self.q(wrapper + 8, OBJ + 0xb800)
            finish(wrapper)
        elif pc == 0xea9a60:
            self.stubs.add('EA9A60 empty auxiliary animation-reference lookup')
            finish(u.reg_read(UC_X86_REG_RCX))
        else:
            super().hook(u, address, size, user)

    def hit(self, weapon, kind=1, flags=0, attack_category=0, tag=122):
        vector, ctx = OBJ + 0x8000, OBJ + 0x8400
        self.q(vector + 8, OBJ + 0x8200)
        self.q(vector + 0x10, OBJ + 0x8200)
        self.q(vector + 0x18, OBJ + 0x8300)
        self.u.mem_write(ctx, bytes(0x300))
        self.u.mem_write(ctx + 0x122, bytes([kind]))
        self.u.mem_write(ctx + 0x124, (1 << tag if tag else 0).to_bytes(32, "little"))
        self.u.mem_write(ctx + 0x161, bytes([flags]))
        self.u.mem_write(ctx + 0x190, struct.pack('<i', weapon))
        self.u.mem_write(ctx + 0x40, struct.pack('<iii', 10000, 1, attack_category))
        self.u.mem_write(ctx + 0x280, struct.pack('<i', 10))
        self.invoke(0x505e90, [OBJ, vector, ctx])
        end = struct.unpack('<Q', self.u.mem_read(vector + 0x10, 8))[0]
        count = (end - (OBJ + 0x8200)) // 4
        assert 0 <= count < 64
        return list(struct.unpack('<' + 'i' * count, self.u.mem_read(OBJ + 0x8200, count * 4)))

    def hp(self):
        self.q(OBJ + 0x10, 0)
        self.invoke(0x50b860, [OBJ] + [OBJ + 0x800 + k * 0x20 for k in range(11)] + [0])
        self.q(OBJ + 0x10, OBJ + 0x6000)
        return list(struct.unpack('<2f', self.u.mem_read(OBJ + 0x880, 8)))



checks=dict(filter=[],lifecycle=[],penalty=[]);stubs=set()
# Isolate the skill-state and hit-tag predicates, keeping all native filters.
for state in (False,True):
 for copies in (1,3):
  c=Blade()
  for _ in range(copies):c.insert(7034400)
  if state:c.event(707060)
  c.qualify();c.update(0)
  for _ in range(copies):c.insert(7034402)
  if state:c.event(707060)
  c.qualify();c.update(0)
  for tag in (0,16,122,130):
   for kind in (0,1,2,3,4,5,11,12):
    attacks=c.tagged_attack(tag,kind)
    hits=c.hit(weapon_ids[1],kind=kind,tag=tag)
    expect=state and tag==122
    # Check each entry point separately; a hit-side grant does not prove that
    # the damage getter accepts the same source context.
    assert all(math.isclose(v,1.35 if expect and kind in (0,1,2,11,12) else 1,rel_tol=1e-6) for v in attacks),(state,copies,tag,kind,attacks,c.nodes())
    assert hits==([7034403] if expect and kind in (0,1,2,5,11,12) else []),(state,tag,kind,hits)
    checks['filter'].append(dict(skillState=state,copies=copies,tag=tag,kind=kind,attack=attacks,hitEffects=hits))
  stubs.update(c.stubs)

for name,copies,hits,stop,cancel,restart in [
 ('no-equipment',0,[30],120,None,None),
 ('no-hit',1,[],120,None,None),
 ('one-hit',1,[30],120,None,None),
 ('duplicate-equipment',3,[30],120,None,None),
 ('repeat-hit',1,[30,90],120,None,None),
 ('after-sheathing',1,[30,180],120,None,None),
 ('cancel-marker-only',1,[30,210],240,120,None),
 ('skill-restart',1,[30,300],120,None,240),
]:
 c=Blade()
 for _ in range(copies):c.insert(7034400)
 c.qualify();c.update(0)
 changes=[];grants=[];previous=None
 for frame in range(660):
  pending,c.emitted=c.emitted,[]
  for id in pending:c.insert(id)
  active=frame<stop or restart is not None and restart<=frame<restart+120
  if active:c.event(707060)
  if frame<6 or restart is not None and restart<=frame<restart+6:c.event(7034401)
  if cancel is not None and cancel<=frame<cancel+6:c.event(7034404)
  c.qualify();c.update(1/60)
  if frame in hits:
   triggered=c.hit(weapon_ids[1])
   c.emitted.extend(triggered);grants.append(dict(frame=frame,ids=triggered))
  rate=round(c.tagged_attack()[0],5);defense=[round(v,5) for v in c.defense()]
  now=(rate,defense)
  if now!=previous:changes.append(dict(frame=frame,attack=rate,incoming=defense));previous=now
 checks['lifecycle'].append(dict(name=name,copies=copies,fps=60,skillStop=stop,skillRestart=restart,
  cancel=cancel,hits=hits,grants=grants,changes=changes,finalNodes=c.nodes()))
 stubs.update(c.stubs)

# A separate animation's marker alone must not be mistaken for skill exit.
cases={c['name']:c for c in checks['lifecycle']}
assert cases['no-equipment']['changes']==[dict(frame=0,attack=1.0,incoming=[1.0]*5)]
assert cases['one-hit']['changes']==cases['duplicate-equipment']['changes']
assert all(c['incoming']==[1.0]*5 for c in cases['no-hit']['changes'])
assert cases['after-sheathing']['grants'][-1]['ids']==[]
assert cases['cancel-marker-only']['grants'][-1]['ids']==[7034403]
assert [c['attack'] for c in cases['skill-restart']['changes']]==[1,1.35,1.35,1,1.35,1,1]
assert cases['repeat-hit']['changes'][-1]['frame']-cases['one-hit']['changes'][-1]['frame']==60
assert any(c['attack']==1 and c['incoming']==[1.4]*5 for c in cases['one-hit']['changes'])

# Penalty duration is independent of the skill state, and refreshes on re-hit.
for copies in (1,3):
 for arrivals in ([0],[0,0,0],[0,240]):
  c=Blade();changes=[];previous=None
  for frame in range(600):
   for _ in range(arrivals.count(frame)*copies):c.insert(7034403)
   c.qualify();c.update(1/60)
   values=[round(v,5) for v in c.defense()]
   if values!=previous:changes.append(dict(frame=frame,incoming=values));previous=values
  assert all(n['id']!=7034403 for n in c.nodes())
  assert changes[0]['incoming']==[1.4]*5 and changes[-1]['incoming']==[1]*5
  assert len(changes)==2 and abs(changes[-1]['frame']/60-(max(arrivals)/60+5))<=2/60
  checks['penalty'].append(dict(copies=copies,arrivals=arrivals,fps=60,changes=changes))
  stubs.update(c.stubs)
# Preserve the actual five category bytes for every Cursed Sword attack row;
# the native tag predicate is also run against each row's complete tag set.
checks['attackRows']=[]
for id,row in inputs.x['tables']['AtkParam_Pc'].items():
 if not 960000<=int(id)<970000:continue
 raw_rows=[attack_raw[off:off+0x1d0] for k in range(struct.unpack_from('<H',attack_raw,10)[0])
  if struct.unpack_from('<i',attack_raw,0x40+k*24)[0]==int(id)
  for off in [struct.unpack_from('<Q',attack_raw,0x48+k*24)[0]]]
 assert len(raw_rows)==1
 tags=[int(row['subCategory'+str(k)]) for k in range(1,6)]
 assert tags==[raw_rows[0][k] for k in (0x4e,0x4f,0x1c8,0x1c9,0x1ca)]
 c=Blade();c.event(707060);c.qualify();c.update(0);c.insert(7034402)
 c.event(707060);c.qualify();c.update(0)
 c.u.mem_write(OBJ+0x800,bytes(0x200));c.u.mem_write(OBJ+0x808,struct.pack('<iiB',40000,1,0))
 for tag in tags:
  if tag:c.invoke(0xe6d3e0,[OBJ+0x814,tag])
 c.invoke(0x502830,[OBJ,OBJ+0x800,-1,-1])
 rate=struct.unpack('<f',c.u.mem_read(OBJ+0x890,4))[0]
 assert math.isclose(rate,1.35 if 122 in tags else 1,rel_tol=1e-6)
 checks['attackRows'].append(dict(attack=int(id),tags=tags,rate=rate))
 stubs.update(c.stubs)
assert len(checks['attackRows'])==34
output=dict(schema=1,exeSha256=sha(inputs.raw),regulationSha256=inputs.x['hashes']['regulation.bin'],
 paramSha256=sha(inputs.param),weaponParamSha256=sha(weapon_raw),attackParamSha256=sha(attack_raw),
 animationSha256=tae['bundles'][0]['sha256'],root=7034400,events=events,checks=checks,
 stubs=sorted(stubs),gameplayVerified=False)
a.output.write_text(json.dumps(output,indent=2)+'\n')
print('PASS:',{k:len(v) for k,v in checks.items()})
for c in checks['lifecycle']:print(c['name'],c['grants'],c['changes'])
