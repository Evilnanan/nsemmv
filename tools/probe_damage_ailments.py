"""Execute damage-triggered ailment grants, stacking and bridge rearming.

Uses the original immediate actor grant and recipient accumulation, including
rejected-node removal. Damage input, actor identity and resistance capacity are
explicit fixtures; complete combat, decay and multiplayer are not simulated.
"""
import argparse
import itertools
import json
import struct
from pathlib import Path
from native_effect_runtime import BASE, OBJ, STOP, Inputs, sha
from native_ailment_runtime import Ailment
from unicorn.x86_const import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted)
class Damage(Ailment):
 def __init__(self,kind=0,maximum=500):
  # Reuse the actor setup; explicitly initialize every channel, including the
  # five channels outside the shared helper's original poison/bleed probes.
  super().__init__(x,0,maximum);self.kind=kind;self.grants=[]
  for i in range(7):
   for off in (0x9010,0x902c):self.u.mem_write(OBJ+off+i*4,struct.pack('<i',maximum))
  self.q(OBJ+0x6210,STOP+0x300);self.q(OBJ+0x6790,STOP+0x301)
  for off in (0x118,0x120,0x130,0x150):self.q(OBJ+0x6200+off,STOP+0x302)
  self.q(OBJ+0xf020,OBJ+0x9000)
  self.globalq(0x3c84d4+7+0x384b2c5,OBJ+0x18300)
  self.stubs.add('explicit player identity, actor virtual +590 type 0 and +118/+120/+130/+150 false')
  self.stubs.add('native self-grant mode 7 and local actor; network singleton present with no peer')
  self.stubs.add('3D3390 false special owner predicate; 51B920/6AF640 notification sinks; EA0CA0 absent notification mapping')
  self.stubs.add('2167950/21674E0/2167A40 monotonic notification timestamp fixture')
  self.globalq(0x3c21ec8,OBJ+0x18000);self.u.mem_write(OBJ+0x18010,struct.pack('<i',7))
  self.u.mem_map(OBJ+0x40000,0x20000);self.globalq(0x3c0f0a8,OBJ+0x40000);self.q(OBJ+0x574e8,OBJ+0x6000)
 def globalq(self,rva,value):
  try:self.u.mem_read(BASE+rva,8)
  except:self.mapped(self.u,0,BASE+rva,8,0,None)
  self.q(BASE+rva,value)
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v&0xffffffffffffffff);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if address in (STOP+0x300,STOP+0x301,STOP+0x302):ret({STOP+0x300:1,STOP+0x301:OBJ+0x18100,STOP+0x302:0}[address])
  elif pc==0x3c7fd0:self.grants.append(u.reg_read(UC_X86_REG_RDX)&0xffffffff)  # observe; execute original grant
  elif pc in(0x3d3390,0x732800,0x51b920,0x6af640):ret()
  elif pc in(0x2167950,0x21674e0,0x2167a40):
   self.q(OBJ+0x18200,100);ret(OBJ+0x18200 if pc==0x2167950 else 1 if pc==0x2167a40 else 0)
  elif pc==0xea0ca0:ret(-1)
  else:super().hook(u,address,size,user)
 def grant(self,id):self.invoke(0x3c7fd0,[OBJ+0x6000,id,1])
 def damage(self,value=100,excluded=0):self.invoke(0x504d30,[OBJ,0,0,0,excluded],{UC_X86_REG_XMM1:value})

channels=[(6820000,'poizonAttackPower',0),(6820100,'diseaseAttackPower',1),(6820200,'freezeAttackPower',4),
          (6820300,'bloodAttackPower',2),(6820400,'madnessAttackPower',6),(6820500,'sleepAttackPower',5),(6820600,'curseAttackPower',3)]
families=[]
for root,field,kind in channels:
 r=x.spells[str(root)];bridge=x.spells[str(root+1)];leaf=x.spells[str(root+2)]
 assert x.x['tables']['AttachEffectParam'][str(root)]['exclusivityId']==-1
 assert r['spCategory']==bridge['spCategory']==10 and r['deleteCriteriaDamage']==12
 assert r['effectEndurance']==-1 and r['replaceSpEffectId']==root+1
 assert abs(bridge['effectEndurance']-.1)<1e-6 and bridge['motionInterval']==1
 assert bridge['replaceSpEffectId']==root and bridge['cycleOccurrenceSpEffectId']==root+2
 assert bridge['deleteCriteriaDamage']==0
 families.append(dict(root=root,bridge=root+1,leaf=root+2,field=field,channel=kind,amount=leaf[field]))
checks=dict(trigger=[],window=[],continuous=[],mixed=[]);stubs=set()

def start(family,copies):
 c=Damage(family['channel'],10000)
 for _ in range(copies):c.grant(family['root'])
 c.qualify();c.update(0)
 return c

def step(c,fps):c.qualify();c.update(1/fps)
def record(kind,c,**row):checks[kind].append(row);stubs.update(c.stubs)

for family,copies,damage,excluded in itertools.product(families,range(4),(-1,0,1,10000),(0,1)):
 c=start(family,copies);before=len(c.grants);c.damage(damage,excluded)
 for _ in range(30):step(c,60)
 fired=damage>0 and not excluded
 assert c.remaining()==10000-(copies*family['amount'] if fired else 0)
 grants=c.grants[before:]
 assert all(grants.count(id)==(copies if fired else 0) for id in (family['root'],family['bridge'],family['leaf']))
 assert len(grants)==(copies*3 if fired else 0)
 assert len(c.nodes())==copies and all(n['id']==family['root'] and n['lifetime']==-1 for n in c.nodes())
 record('trigger',c,root=family['root'],copies=copies,damage=damage,excluded=bool(excluded),grants=grants,remaining=c.remaining())
for family,copies,fps in itertools.product(families,(1,2,3),(30,60,120)):
 c=start(family,copies);c.damage()
 for _ in range(2):step(c,fps)
 assert all(n['id']==family['bridge'] for n in c.nodes())
 first=c.remaining();assert first==10000-copies*family['amount']
 c.damage()  # second hit while every copy is the bridge, not the armed root
 rearm=None
 for frame in range(3,fps//2+1):
  step(c,fps)
  if all(n['id']==family['root'] and n['lifetime']<0 for n in c.nodes()):rearm=frame;break
 assert rearm is not None and c.remaining()==first and len(c.nodes())==copies
 c.damage()
 for _ in range(fps//2):step(c,fps)
 assert c.remaining()==10000-2*copies*family['amount'] and len(c.nodes())==copies
 record('window',c,root=family['root'],copies=copies,fps=fps,rearmFrame=rearm,firstRemaining=first,remaining=c.remaining())
for family,copies in itertools.product(families,(1,2,3)):
 c=start(family,copies);before=len(c.grants)
 for _ in range(120):
  c.damage();step(c,60)
 for _ in range(30):step(c,60)
 grants=c.grants[before:];arrivals=grants.count(family['leaf'])
 assert 0<arrivals<120*copies and arrivals%copies==0
 assert c.remaining()==10000-arrivals*family['amount'] and len(c.nodes())==copies
 record('continuous',c,root=family['root'],copies=copies,damageCalls=120,arrivals=arrivals,remaining=c.remaining())
c=Damage(0,10000)
for f in families:c.grant(f['root'])
c.qualify();c.update(0);c.damage()
for _ in range(30):step(c,60)
remaining=list(struct.unpack('<7i',c.u.mem_read(OBJ+0x9010,28)))
assert all(remaining[f['channel']]==10000-f['amount'] for f in families)
assert sorted(n['id'] for n in c.nodes())==sorted(f['root'] for f in families)
record('mixed',c,roots=[f['root'] for f in families],remaining=remaining)
output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),
            families=families,checks=checks,native=dict(damage='504D30',update='50ACD0',grant='3C7FD0 → 3C80A0 → 3DB410',
            insert='50A4C0 → 50D060',status='42D110 → 509790 / 42CD70',reject='505280'),
            stubs=sorted(stubs),capacityFixture=10000,naturalDecayExecuted=False,gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(map(len,checks.values())),'native damage ailment cases')
