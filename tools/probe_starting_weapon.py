"""Trace starting-weapon infusions through instance assignment and attack filters.

Runs pinned PC code with actual MMV PARAM rows. Equipment handles and PARAM
lookups are fixtures; assignment, effect insertion/removal, per-level matching,
attack getters and attack-effect collection execute original instructions.
"""
import argparse
import json
import math
import struct
from pathlib import Path
from unicorn.x86_const import *
from native_effect_runtime import BASE, OBJ, STOP, Chain, Inputs, sha

p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','assets','output'): p.add_argument(name,type=Path)
a=p.parse_args()
x=Inputs(a.exe,a.extracted)
assets=json.loads(a.assets.read_text())
assert assets['hashes']['regulation.bin']==x.x['hashes']['regulation.bin']
weapon_raw=a.assets.with_suffix('.EquipParamWeapon.param').read_bytes()
w=Inputs.table(weapon_raw,0x298)
assert all(assets['tables']['EquipParamWeapon'][str(i)]['isHeroPointCorrect']==int(bool(row[0x107]&1)) for i,row in w.items())
roots=list(range(7120000,7120601,100))
assert all(x.rows[r]==x.rows[roots[0]] for r in roots)
assert x.spells[str(roots[0])]['stateInfo']==2101

class StartWeapon(Chain):
 def __init__(self,root,slots):
  super().__init__(x);self.root=root;self.slots=slots+[(-1,-1)]*(6-len(slots));self.active=0
  self.q(OBJ+0x6190,OBJ);self.q(OBJ+0x6200+0x258,STOP+0x200);self.q(OBJ+0x6200+0x118,STOP+0x201)
  self.q(OBJ+0x8100,OBJ+0x6000);self.u.mem_write(OBJ+0x8028,struct.pack('<i',root))
 def hook(self,u,address,size,user):
  pc=address-BASE
  if address in (STOP+0x200,STOP+0x201): self.stubs.add("synthetic equipped-slot handles and local actor identity")
  if pc in (0x6a1d70,0x6a1d90): self.stubs.add("weapon-instance wrapper fixture; actual instance getter/setter code")
  if pc==0xea7fc0: self.stubs.add("EA7FC0 actual weapon row lookup with supplied base ID and reinforcement delta")
  if pc==0xea9a60: self.stubs.add("EA9A60 absent auxiliary animation lookup")
  def ret(value=0):
   u.reg_write(UC_X86_REG_RAX,value);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if address==STOP+0x200:
   self.active=u.reg_read(UC_X86_REG_R8);u.mem_write(u.reg_read(UC_X86_REG_RDX),struct.pack('<I',self.active+1));ret(u.reg_read(UC_X86_REG_RDX))
  elif address==STOP+0x201 or pc in [0x6a1d90,0xea9a60]:ret()
  elif pc==0x6a1d70:
   ptr=u.reg_read(UC_X86_REG_RCX);id,root=self.slots[self.active];instance=OBJ+0xe000+self.active*0x100
   self.q(ptr+8,instance);u.mem_write(ptr+0x10,struct.pack('<I',id&0xffffffff));u.mem_write(instance+0x40,struct.pack('<i',root));ret(ptr)
  elif pc==0xea7fc0:
   ptr=u.reg_read(UC_X86_REG_RCX);id=u.reg_read(UC_X86_REG_RDX)&0xffffffff
   assert id in (0xffffffff,1000,3750000,3750001,3750002,3750003,3750004)
   base=id-id%100
   u.mem_write(ptr,struct.pack('<I',id))
   if base in w:u.mem_write(OBJ+0xf000,w[base]);self.q(ptr+8,OBJ+0xf000);u.mem_write(ptr+0x10,struct.pack('<I',base))
   ret(ptr)
  else:super().hook(u,address,size,user)
 def tick(self):
  self.invoke(0x4cbdb0,[OBJ+0x8000,0,OBJ+0x8100],{UC_X86_REG_XMM1:1/60})
  queue=self.emitted[:];self.emitted.clear()
  for id in queue:self.insert(id)
  self.qualify();self.update(0)
  return queue


class Assignment(StartWeapon):
 def hook(self,u,address,size,user):
  pc=address-BASE
  if pc in (0x1f2730,0x381190,0x1f20d0): self.stubs.add("inventory slots/handle lookup fixtures")
  def ret(value=0):
   u.reg_write(UC_X86_REG_RAX,value);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if pc==0x1f2730:
   self.active=u.reg_read(UC_X86_REG_RDX);ret(self.slots[self.active][0]&0xffffffff)
  elif pc==0x381190:ret(self.active)
  elif pc==0x1f20d0:
   ptr=u.reg_read(UC_X86_REG_RDX);u.mem_write(ptr,struct.pack('<I',self.active+1));ret(ptr)
  else:super().hook(u,address,size,user)

checks=dict(component=[],assignment=[],attack=[],status=[],binding=[]);stubs=set()
for root in range(7120000,7120601,100):
 for levels in [[0],[1],[2],[3],[4],[0,0],[0,2]]:
  c=StartWeapon(root,[(3750000+i,root) for i in levels]);added=c.tick();second=c.tick()
  expected=sorted({root+1+min(i,3) for i in levels});assert added==expected and second==[],(root,levels,added,second)
  c.slots=[(-1,-1)]*6;c.tick();c.qualify();c.update(0)
  assert c.nodes()==[],c.nodes()
  checks["component"].append(dict(root=root,levels=levels,added=added,repeat=second,afterUnequip=c.nodes()));stubs.update(c.stubs)
for root in range(7120000,7120601,100):
 for id,attached in [(1000,root),(3750000,-1),(3750000,root+100)]:
  c=StartWeapon(root,[(id,attached)]);assert c.tick()==[]
  checks["component"].append(dict(root=root,weapon=id,attached=attached,added=[]));stubs.update(c.stubs)

for equipped_roots in [[],[7120000],[7120000]*3,[7120000,7120100],[7120100,7120000],[7120400,7000000,7120600]]:
 for old in [-1,7120200]:
  c=Assignment(0,[(3750000,old)]);c.q(OBJ+0x65a0,OBJ+0xd000)
  for root in equipped_roots:c.insert(root)
  c.qualify();c.update(0)
  eligible=[n['id'] for n in c.nodes() if x.spells[str(n['id'])]['stateInfo']==2101]
  c.invoke(0x673f40,[OBJ+0x6000]);actual=struct.unpack('<i',c.u.mem_read(OBJ+0xe040,4))[0]
  assert actual==(eligible[-1] if eligible else -1),(equipped_roots,old,actual,eligible)
  checks["assignment"].append(dict(roots=equipped_roots,old=old,containerOrder=eligible,attached=actual));stubs.update(c.stubs)

def attack(c,weapon,attached,kind):
 out=OBJ+0x8400;c.u.mem_write(out,bytes(0x300));c.u.mem_write(out+0x10,bytes([kind]))
 c.u.mem_write(out+0xc,struct.pack('<i',-1))
 c.invoke(0x502830,[OBJ,out,weapon,attached])
 return dict(points=[struct.unpack('<f',c.u.mem_read(out+off,4))[0] for off in (0x48,0x5c,0x60,0x64,0x68)],
             rates=[struct.unpack('<f',c.u.mem_read(out+off,4))[0] for off in (0x6c,0x80,0x84,0x88,0x8c)])

def hit_effects(c,weapon,attached,kind):
 ctx,flt,vec=OBJ+0x8400,OBJ+0x8800,OBJ+0x8900
 c.u.mem_write(ctx,bytes(0x300));c.u.mem_write(ctx+0x122,bytes([kind]))
 c.u.mem_write(ctx+0x190,struct.pack('<i',weapon));c.u.mem_write(ctx+0xf8,struct.pack('<i',attached))
 c.u.mem_write(ctx+0x40,struct.pack('<iii',-1,1,0))
 c.invoke(0x50f230,[flt,ctx])
 for off in (8,16):c.q(vec+off,OBJ+0x8a00)
 c.q(vec+24,OBJ+0x8b00)
 c.invoke(0x506200,[OBJ,vec,flt])
 end=struct.unpack('<Q',c.u.mem_read(vec+16,8))[0];n=(end-(OBJ+0x8a00))//4
 assert 0<=n<64
 return list(struct.unpack('<'+'i'*n,c.u.mem_read(OBJ+0x8a00,n*4)))

for root in roots:
 for level in range(4):
  weapon=3750000+level;c=StartWeapon(root,[(weapon,root)]);c.tick()
  for kind in (0,1,2,3,4,5,11,12):
   for supplied_weapon,supplied_root in ((weapon,root),(1000,root),(weapon,root+100)):
    result=attack(c,supplied_weapon,supplied_root,kind)
    eligible=kind in (0,1,2,11,12) and supplied_weapon==weapon and supplied_root==root
    points=[0.0]*5;rates=[1.0]*5
    if eligible:
     if root<7120400:points[0]=-(30+10*level);points[1+(root-7120000)//100]=33+11*level
     else:rates=[.85]*5
    assert result['points']==points,(root,level,kind,supplied_weapon,supplied_root,result)
    assert all(math.isclose(v,e,rel_tol=1e-6) for v,e in zip(result['rates'],rates)),result
    checks['attack'].append(dict(root=root,level=level,kind=kind,weapon=supplied_weapon,attached=supplied_root,**result))
    if root>=7120400:
     effects=hit_effects(c,supplied_weapon,supplied_root,kind)
     # Context binding trusts the supplied attachment ID; unlike the panel
     # getter it does not recheck isHeroPointCorrect. A deliberately forged
     # ordinary-weapon context at level 0 still matches. Preserve this result.
     context_level=supplied_weapon%100
     context_matches=supplied_root==root and context_level==level
     expected=[root+5+level] if context_matches and kind in (1,2,11,12) else []
     assert effects==expected,(root,level,kind,supplied_weapon,supplied_root,effects)
     checks['status'].append(dict(root=root,level=level,kind=kind,weapon=supplied_weapon,attached=supplied_root,effects=effects))
  if root>=7120400:
   effects=hit_effects(c,1000,-1,1)
   assert effects==[]
   checks['status'].append(dict(root=root,level=level,kind=1,weapon=1000,attached=-1,effects=effects))
  stubs.update(c.stubs)
 # Multiple rarity stages can be resident, but only the actual weapon's leaf matches.
 c=StartWeapon(root,[(3750000,root),(3750002,root)]);c.tick()
 for level in range(4):
  result=attack(c,3750000+level,root,1)
  expected_points=[0.0]*5;expected_rates=[1.0]*5
  if level in (0,2):
   if root<7120400:expected_points[0]=-(30+10*level);expected_points[1+(root-7120000)//100]=33+11*level
   else:expected_rates=[.85]*5
  assert result['points']==expected_points
  assert all(math.isclose(v,e,rel_tol=1e-6) for v,e in zip(result['rates'],expected_rates))
  checks['binding'].append(dict(root=root,residentLevels=[0,2],weaponLevel=level,**result))
 stubs.update(c.stubs)

fields=['spCategory','stateInfo','effectEndurance','playerHandValue','spAttribute','atkOccurrenceSpEffectId',
        'physicsAttackPower','magicAttackPower','fireAttackPower','thunderAttackPower','darkAttackPower',
        'physicsAttackPowerRate','magicAttackPowerRate','fireAttackPowerRate','thunderAttackPowerRate','darkAttackPowerRate',
        'freezeAttackPower','poizonAttackPower','bloodAttackPower']
rows={str(root+n):{k:x.spells[str(root+n)][k] for k in fields}
      for root in roots for n in range(1,9 if root>=7120400 else 5)}
for root,field,amount in ((7120400,'freezeAttackPower',35),(7120500,'poizonAttackPower',35),(7120600,'bloodAttackPower',25)):
 assert all(rows[str(root+n)][field]==amount for n in range(5,9))
output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],
 paramSha256=sha(x.param),weaponParamSha256=sha(weapon_raw),roots=roots,rows=rows,
 native=dict(assignment='673F40',instanceSet='6A23D0',instanceGet='6A2040',componentLookup='4B2E40',
             componentUpdate='4CBDB0',presence='3D2100',remove='504E80',attack='502830',filter='511010',
             explicitBinding='6A2580',contextBinding='6A24E0',hitContext='50F230',attackEffects='506200'),
 checks=checks,stubs=sorted(stubs|{'attack contexts supplied; no full hit/damage/abnormality/network simulation',
     'grant requests delivered on next fixture step; actual effect constructor, insertion and qualification',
     'PARAM weapon base lookup is supplied; this does not test reinforcement menus or arbitrary weapon aliases'}),
 gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS:',{k:len(v) for k,v in checks.items()})
