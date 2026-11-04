"""Trace native starting-weapon art and spell replacement selection.

Inventory handles/row lookups are fixtures; original slot scanning, eligibility,
compatibility, effect traversal and weapon-instance writes execute. Casting,
full expedition initialization and live DLL patches are not simulated.
"""
import argparse,json,struct,itertools
from pathlib import Path
from native_effect_runtime import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','assets','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted)
assets=json.loads(a.assets.read_text());assert assets['hashes']['regulation.bin']==x.x['hashes']['regulation.bin']
raws={name:a.extracted.with_suffix('.'+name+'.param').read_bytes() for name in ('Magic','SwordArtsParam')}
raws['EquipParamWeapon']=a.assets.with_suffix('.EquipParamWeapon.param').read_bytes()
w=Inputs.table(raws['EquipParamWeapon'],0x298);magic=Inputs.table(raws['Magic'],0xac);arts=Inputs.table(raws['SwordArtsParam'],0x3c)
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
   assert id==0xffffffff or id in w
   base=id-id%100
   self.q(ptr+8,0)
   u.mem_write(ptr,struct.pack('<I',id))
   if base in w:u.mem_write(OBJ+0xf000,w[base]);self.q(ptr+8,OBJ+0xf000);u.mem_write(ptr+0x10,struct.pack('<I',base))
   ret(ptr)
  else:super().hook(u,address,size,user)



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

class Replacement(Assignment):
 def __init__(self,slots):
  self.writes=[];super().__init__(0,[(id,-1) for id in slots]);self.q(OBJ+0x65a0,OBJ+0xd000)
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if pc in(0x6a23a0,0x6a23b0):
   self.writes.append(dict(slot=self.active,kind='magic' if pc==0x6a23a0 else 'arts',value=u.reg_read(UC_X86_REG_RDX)&0xffffffff))
  elif pc in(0xe926c0,0xea2340):
   ptr=u.reg_read(UC_X86_REG_RCX);id=u.reg_read(UC_X86_REG_RDX)&0xffffffff;table=magic if pc==0xe926c0 else arts
   self.q(ptr+8,0)
   if id in table:
    u.mem_write(OBJ+0x11000,table[id]);u.mem_write(ptr,struct.pack('<IiQ',id,6 if pc==0xe926c0 else 0,OBJ+0x11000))
   ret(ptr)
  else:super().hook(u,address,size,user)
 def run(self,roots):
  for root in roots:self.insert(root)
  self.qualify();self.update(0);self.invoke(0x673f40,[OBJ+0x6000])
  return [dict(weapon=id,arts=struct.unpack('<i',self.u.mem_read(OBJ+0xe000+i*0x100+0x1c,4))[0],magic=struct.unpack('<i',self.u.mem_read(OBJ+0xe000+i*0x100+0x2c,4))[0]) for i,(id,r) in enumerate(self.slots) if id!=-1]
 def compatible(self,root,weapon):
  row=x.spells[str(root)];weaponrow=w[weapon]
  if row['stateInfo']==2128:
   return bool(weaponrow[0x195]&1 and ((weaponrow[0x105]&128) or (weaponrow[0x106]&2)) and row['startMagicId'] in magic)
  if not weaponrow[0x107]&1:return False
  return self.art_compatible(row['startSwordArtsId'],struct.unpack_from('<H',weaponrow,0x1a6)[0])
 def art_compatible(self,id,kind):
  ptr=OBJ+0x12000;self.q(ptr+8,OBJ+0x13000);self.u.mem_write(OBJ+0x13000,arts[id])
  return bool(self.invoke(0xea2380,[ptr,kind])&255)

research=json.loads((Path(__file__).resolve().parents[1]/'data/effect-research.json').read_text())
source=json.loads((Path(__file__).resolve().parents[1]/'data/effect-detail-source.json').read_text())
families=[]
for id,r in research['effects'].items():
 if r['obtainable'] and any(state in(2105,2128) for state in r['states']):
  root=list(source['effects'][id]['roots'].values())[0];row=x.spells[str(root)];kind='arts' if row['stateInfo']==2105 else 'magic'
  families.append(dict(effect=int(id),root=root,kind=kind,target=row['startSwordArtsId' if kind=='arts' else 'startMagicId']))
assert len(families)==35 and sum(f['kind']=='arts' for f in families)==20
weapons=sorted(id for id,r in w.items() if r[0x107]&1 or r[0x195]&1);assert len(weapons)==31
checks={k:[] for k in ('compatibility','baseline','matrix','repeat','order','scope')};stubs=set()
def record(key,c,**row):checks[key].append(row);stubs.update(c.stubs)
baseline={}
for weapon in weapons+[1000]:
 c=Replacement([weapon]);baseline[weapon]=c.run([])[0];record('baseline',c,weapon=weapon,result=baseline[weapon],writes=c.writes)
for f in [f for f in families if f['kind']=='arts']:
 c=Replacement([])
 for kind in range(89):
  result=c.art_compatible(f['target'],kind);record('compatibility',c,effect=f['effect'],art=f['target'],weaponType=kind,compatible=result)
for f,weapon in itertools.product(families,weapons):
 c=Replacement([weapon]);compatible=c.compatible(f['root'],weapon);result=c.run([f['root']])[0]
 expected={**baseline[weapon],**({f['kind']:f['target']} if compatible else {})}
 assert result==expected,(f,weapon,result,expected)
 writes=[r for r in c.writes if r['kind']==f['kind']]
 baseline_count=next(len([r for r in row['writes'] if r['kind']==f['kind']]) for row in checks['baseline'] if row['weapon']==weapon)
 assert len(writes)==baseline_count+int(compatible)
 record('matrix',c,effect=f['effect'],weapon=weapon,compatible=compatible,result=result,writes=c.writes)
print('PASS all starting replacement compatibility and weapon assignments',flush=True)
for f,copies in itertools.product(families,(0,1,3)):
 c=Replacement([]);weapon=next(wid for wid in weapons if c.compatible(f['root'],wid))
 c=Replacement([weapon]);result=c.run([f['root']]*copies)[0]
 expected={**baseline[weapon],**({f['kind']:f['target']} if copies else {})};assert result==expected
 c.writes=[];repeat=c.run([])[0];assert repeat==result
 for _ in range(copies):c.invoke(0x504e80,[OBJ,f['root']])
 c.qualify();c.update(0);c.writes=[];removed=c.run([])[0];assert removed==baseline[weapon]
 record('repeat',c,effect=f['effect'],weapon=weapon,copies=copies,result=result,repeat=repeat,removed=removed)
# Adjacent pairs cover every replacement, in both orders. Incompatible later
# arts cannot erase an earlier compatible result; magic and prayer share a field.
orders=[]
for kind in('arts','magic'):
 fs=[f for f in families if f['kind']==kind]
 for left,right in zip(fs,fs[1:]+fs[:1]):orders.extend(((left['root'],right['root']),(right['root'],left['root'])))
orders.extend(((7122700,7361200),(7361200,7122700),(7122700,7124700),(7124700,7122700)))
for order,weapon in itertools.product(orders,(3750000,41750000,7270000)):
 c=Replacement([weapon]);result=c.run(order)[0];expected=baseline[weapon].copy()
 # Traverse the ACTUAL resulting effect list; insertion order and category
 # replacement must not be silently equated with preset order.
 ids=[n['id'] for n in c.nodes()];chosen=[]
 for root in ids:
  f=next(f for f in families if f['root']==root)
  if c.compatible(root,weapon):expected[f['kind']]=f['target'];chosen.append(root)
 assert result==expected,(order,ids,weapon,result,expected)
 record('order',c,order=order,effectList=ids,weapon=weapon,chosen=chosen,result=result)
# Distinct branches select the first eligible equipped weapon. A non-initial
# weapon and later initial weapons remain untouched in this isolated setup.
slot_cases=[[],[1000],[1000,3750000],[3750000,3980000],[3980000,3750000],[7270000,33750000,34750000],
 [34750000,33750000,7270000],[3750000,7270000],[7270000,3750000],[1000,33750000,3750000]]
for slots in slot_cases:
 c=Replacement(slots);result=c.run([7122700,7361200]);expected=[dict(weapon=id,arts=0,magic=0) for id in slots]
 for kind,flag,root in(('arts',0x107,7122700),('magic',0x195,7361200)):
  index=next((i for i,id in enumerate(slots) if w[id][flag]&1),None)
  if index is None:continue
  weapon=slots[index];expected[index][kind]=baseline[weapon][kind]
  if c.compatible(root,weapon):expected[index][kind]=x.spells[str(root)]['startSwordArtsId' if kind=='arts' else 'startMagicId']
 assert result==expected,(slots,result,expected)
 record('scope',c,slots=slots,result=result,writes=c.writes)
fields=('stateInfo','spCategory','effectEndurance','startSwordArtsId','startMagicId')
output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),
 assetHashes={k:sha(v) for k,v in raws.items()},families=families,weapons=weapons,
 rows={str(f['root']):{k:x.spells[str(f['root'])][k] for k in fields} for f in families},checks=checks,
 native=dict(assignment='673F40',artCompatibility='EA2380',magicEligibility='66D350 / 66D370',artWrite='6A23B0 +1C',magicWrite='6A23A0 +2C'),
 stubs=sorted(stubs|{'inventory handles and raw PARAM wrappers are fixtures; real selection and instance setters execute',
 'EA2340 real SwordArts rows; E926C0 real Magic rows, wrapper version6',
 'ordinary initial instance fields zero and infusion -1; actual handler applies real weapon defaults',
 'EA9A60 missing auxiliary animation metadata; full expedition queue, UI order, casting, live DLL patches and gameplay not simulated'}),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(map(len,checks.values())),'starting replacement checks',{k:len(v) for k,v in checks.items()},flush=True)
