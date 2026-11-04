"""Trace nearby-frost concealment through native onset, delivery and lifetime.

Explicit actors and collision arrivals drive original hit reception, relation
filters, grants, conditional effects and timers. No running game or geometry.
"""
import argparse,itertools,json,math,struct
from pathlib import Path
from native_effect_runtime import BASE,OBJ,STOP,Chain,Inputs,sha
from native_ailment_runtime import Ailment
from unicorn.x86_const import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted)
attacks=Inputs.table(a.extracted.with_suffix('.AtkParam_Pc.param').read_bytes(),0x1d0)
bullets=Inputs.table(a.extracted.with_suffix('.Bullet.param').read_bytes(),0x100)
root,marker,leaf=7260702,503,7260703
assert x.x['tables']['AttachEffectParam']['7260700']['passiveSpEffectId_1']==root
assert x.x['tables']['AttachEffectParam']['7260700']['exclusivityId']==800
r=x.spells[str(root)]
assert r['spCategory']==10 and r['effectEndurance']==-1 and r['invocationConditionsStateChange1']==2280 and r['cycleOccurrenceSpEffectId']==leaf
r=x.spells[str(marker)];assert r['stateInfo']==2280 and r['effectEndurance']==0
assert [r[k] for k in ('effectTargetSelfTarget','effectTargetFriendlyTarget','effectTargetOpposeTarget')]==[1,0,1]
r=x.spells[str(leaf)];assert r['spCategory']==20 and r['stateInfo']==600 and r['effectEndurance']==5
assert r['sightSearchEnemyRate']==r['hearingSearchEnemyRate']==1
r=x.spells['502'];assert r['stateInfo']==467 and r['behaviorId']==2101 and r['invocationConditionsStateChange1']==260
behavior=x.x['tables']['BehaviorParam_PC']['2101'];bullet=x.x['tables']['Bullet']['1010'];attack=x.x['tables']['AtkParam_Pc']['2']
assert behavior['refType']==1 and behavior['refId']==1010
assert bullet['atkId_Bullet']==2 and bullet['spEffectId0']==marker and bullet['spEffectId1']==24240
assert bullet['life']==.5 and bullet['hitRadius']==bullet['hitRadiusMax']==7 and bullet['numShoot']==1 and bullet['HitBulletID']==-1
assert [attack[k] for k in ('selfTarget','friendlyTarget','opposeTarget','disableHitSpEffect')]==[1,0,1,0]
class Actor(Ailment):
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

C=OBJ+0x60000;HIT=OBJ+0x61000;SOURCE=OBJ+0x62000;SEFFECT=OBJ+0x63000
class Hit(Actor):
 def __init__(self,kind=4,maximum=500):
  super().__init__(kind,maximum);self.u.mem_map(C,0x10000);self.q(C+8,OBJ+0x6000);self.sent=[]
  self.q(OBJ+0xf000,OBJ+0xe000);self.q(OBJ+0xf088,OBJ+0xf900);self.q(OBJ+0xf910,OBJ+0xfa00)
  self.u.mem_write(OBJ+0xe140,struct.pack('<i',10000));self.q(OBJ+0x6400,STOP+0x600)
  self.globalq(0x42715d+8+0x37e81d3,OBJ+0xfd00)
  self.q(SOURCE,OBJ+0x6200);self.q(SOURCE+0x190,SEFFECT);self.q(SEFFECT+0x10,SOURCE)
  self.u.mem_write(SOURCE+0x74,b'\1');self.u.mem_write(OBJ+0x6074,b'\6')
  self.q(OBJ+0x7118,STOP+0x601)
  self.globalq(0x1fe1c0+7+0x3a09709,OBJ+0x68000)
  self.stubs.add('explicit local hit-score context in mode 0')
  self.same=False;self.attack=2
 def hook(self,u,address,size,user):
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  pc=address-BASE
  if address==STOP+0x600:
   self.stubs.add('recipient virtual +200 false ordinary hit predicate');ret()
  elif pc==0x214f3e0:
   self.stubs.add('214F3E0 allocator identity for empty attacker effect-vector collection');ret(OBJ+0x7000)
  elif address==STOP+0x601:
   self.stubs.add('allocator virtual +18 explicit valid tag; native empty vector collection');ptr=u.reg_read(UC_X86_REG_RDX);u.mem_write(ptr,struct.pack('<I',32));ret(ptr)
  elif pc==0x3d4180:pass  # execute actual local-player comparison
  elif pc==0x26909a0:
   self.stubs.add('26909A0 security cookie preserves return value');ret(u.reg_read(UC_X86_REG_RAX))
  elif pc==0xe6d630:
   self.stubs.add('E6D630 actual AtkParam_Pc row lookup');assert u.reg_read(UC_X86_REG_R8)==self.attack and u.reg_read(UC_X86_REG_RDX)==1
   wrapper=u.reg_read(UC_X86_REG_RCX);u.mem_write(OBJ+0x64000,attacks[self.attack]);u.mem_write(wrapper,struct.pack('<iii4xQ',self.attack,0,1,OBJ+0x64000));ret()
  elif pc==0x3c80a0:
   sp=u.reg_read(UC_X86_REG_RSP);ptr=struct.unpack('<Q',u.mem_read(sp+0x30,8))[0]
   self.sent.append(dict(id=u.reg_read(UC_X86_REG_RDX)&0xffffffff,scales=list(struct.unpack('<15f',u.mem_read(ptr,60)))))
  else:super().hook(u,address,size,user)
 def hit(self,ids=(503,24240),attack=2,scale=0):
  self.attack=attack
  if isinstance(ids,int):ids=(ids,)
  self.u.mem_write(HIT,bytes(0x400))
  self.u.mem_write(HIT+0x40,struct.pack('<ii',attack,1))
  for slot,id in enumerate(ids,5):self.u.mem_write(HIT+0x70+slot*4,struct.pack('<i',id))
  self.u.mem_write(HIT+0x188,struct.pack('<ff',scale,1))
  self.u.mem_write(HIT+0x1a4,struct.pack('<7f',*([1]*7)))
  for off in (0x29c,0xd4,0x254):self.u.mem_write(HIT+off,struct.pack('<f',1))
  self.invoke(0x43be60,[C,OBJ+0x6000 if self.same else SOURCE,HIT,0,1,0])

class Onset(Hit):
 def __init__(self,maximum):super().__init__(4,maximum);self.shots=[];self.frame=0
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if pc in(0x3ced90,0x4d1b20):
   self.stubs.add('3CED90/4D1B20 explicit frozen actor context');ret(OBJ+0xd000 if pc==0x3ced90 else 0)
  elif pc==0x3975d0:
   self.stubs.add('3975D0 Behavior request recorder; original state-467 emission gate')
   self.shots.append(dict(frame=self.frame,behavior=u.reg_read(UC_X86_REG_RDX),payload=bytes(u.mem_read(u.reg_read(UC_X86_REG_R9),8)).hex()));ret(1)
  else:super().hook(u,address,size,user)
class Projectile(Chain):
 def __init__(self):super().__init__(x);self.frame=0;self.shots=[]
 def hook(self,u,address,size,user):
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  pc=address-BASE
  if pc==0xe87800:
   assert u.reg_read(UC_X86_REG_RDX)&0xffffffff==1010
   self.stubs.add('E87800 actual frost-notification Bullet lookup')
   u.mem_write(OBJ+0xe900,bullets[1010]);ptr=u.reg_read(UC_X86_REG_RCX)
   u.mem_write(ptr,struct.pack('<QI',OBJ+0xe900,1010));ret(ptr)
  elif pc==0x347700:
   self.stubs.add('347700 projectile recorder; no scene collision');self.shots.append(self.frame);ret(1)
  else:super().hook(u,address,size,user)
checks=dict(onset=[],projectile=[],recipients=[],lifetime=[],repeat=[],sourceVariants=[]);stubs=set()
def record(key,c,**row):checks[key].append(row);stubs.update(c.stubs)
def step(c,fps=60):c.qualify();c.update(1/fps)
def hidden(c):return bool(c.invoke(0x508e20,[OBJ,600])&255)
def leaves(c):return [n for n in c.nodes() if n['id']==leaf and not n['flags']&0x800c0003]
def equip(copies,sourceType=6,same=False):
 c=Hit();c.same=same;c.u.mem_write(SOURCE+0x74,bytes([sourceType]));c.u.mem_write(OBJ+0x6074,b'\1')
 for _ in range(copies):c.grant(root)
 c.qualify();c.update(0)
 return c
for immune,resistance in itertools.product((False,True),(1,49,50,51,100,500)):
 c=Onset(resistance)
 if immune:c.grant(9642)
 c.qualify();c.update(0);c.hit(1501000,700000281)
 for frame in range(60):c.frame=frame;step(c);c.invoke(0x50a8d0,[OBJ])
 expected=not immune and resistance<=50
 assert len(c.shots)==int(expected),(immune,resistance,c.shots,c.nodes())
 if expected:assert c.shots[0]['behavior']==2101 and c.shots[0]['payload']=='dc00000002ff0000'
 record('onset',c,immune=immune,resistance=resistance,triggered=expected,shots=c.shots,nodes=c.nodes())
for fps in (30,60,120):
 c=Projectile();slot=OBJ+0x4000
 c.u.mem_write(slot+0x329,b'\1');c.u.mem_write(slot+0x334,struct.pack('<I',1010));c.u.mem_write(slot+0x494,b'\1')
 for frame in range(fps):c.frame=frame;c.invoke(0x343280,[slot],{UC_X86_REG_XMM1:1/fps})
 assert c.shots==[0];record('projectile',c,fps=fps,shots=c.shots)
# Both recipient and source identity are explicit. No relation predicate or
# eligibility result is stubbed; same-actor and opposing/friendly paths execute.
for copies,(sourceType,same) in itertools.product((0,1,3),[(i,False) for i in range(10)]+[(1,True)]):
 c=equip(copies,sourceType,same);c.hit();markerPresent=any(n['id']==marker for n in c.nodes())
 for _ in range(8):step(c)
 eligible=same or sourceType in (6,7,8,9)
 assert markerPresent==eligible,(copies,sourceType,same,c.nodes())
 assert hidden(c)==bool(copies and eligible)
 assert len(leaves(c))==int(bool(copies and eligible))
 record('recipients',c,copies=copies,sourceType=sourceType,same=same,eligible=eligible,markerPresent=markerPresent,hidden=hidden(c),nodes=c.nodes())
for fps,copies,same in itertools.product((30,60,120),(0,1,3),(False,True)):
 c=equip(copies,same=same);c.hit();first=None;last=None
 for frame in range(7*fps):
  step(c,fps)
  if hidden(c):
   first=frame if first is None else first;last=frame;assert len(leaves(c))==1
 assert bool(first is not None)==bool(copies)
 if copies:assert abs((last-first+1)/fps-5)<=3.01/fps
 assert not hidden(c) and not leaves(c)
 record('lifetime',c,fps=fps,copies=copies,same=same,first=first,last=last,remaining=c.nodes())
for copies,same,starts in itertools.product((1,3),(False,True),([0],[0,1],[0,3],[0,6])):
 c=equip(copies,same=same);transitions=[];previous=False;lifetimes=[]
 for frame in range((starts[-1]+7)*60):
  if frame in [start*60 for start in starts]:c.hit()
  step(c);now=hidden(c)
  if now!=previous:transitions.append(dict(frame=frame,hidden=now));previous=now
  if frame in [start*60+8 for start in starts]:
   assert len(leaves(c))==1 and 4.8<leaves(c)[0]['lifetime']<=5
   lifetimes.append(dict(frame=frame,lifetime=leaves(c)[0]['lifetime']))
 assert not hidden(c) and abs(transitions[-1]['frame']/60-(starts[-1]+5))<.1
 record('repeat',c,copies=copies,same=same,starts=starts,transitions=transitions,lifetimes=lifetimes)
# Some candidate rows omit the notification cycle. Record the actual full hit
# path, but do not infer their current availability or promise every frost source.
for id in (1501000,107500,107504,1692100,1702000,20000874):
 c=Onset(1);c.hit(id,700000281,scale=1)
 for frame in range(60):c.frame=frame;step(c);c.invoke(0x50a8d0,[OBJ])
 expected=x.spells[str(id)]['cycleOccurrenceSpEffectId']==502
 assert any(n['id']==id for n in c.nodes()) and len(c.shots)==int(expected),(id,c.shots,c.nodes())
 record('sourceVariants',c,effect=id,cycle=x.spells[str(id)]['cycleOccurrenceSpEffectId'],shots=c.shots,nodes=c.nodes())
output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),
 effect=7260700,root=root,marker=marker,leaf=leaf,behavior=behavior,bullet=bullet,attack=attack,
 rows={str(id):x.spells[str(id)] for id in (root,marker,leaf,502,24240,24245,1501000)},checks=checks,
 native=dict(hit='43BE60',grant='3C80A0 / 3C7FD0',onset='42D110',emission='50A8D0 → 397570 → 3975D0',
 projectile='343280 → 347700',relation='52CC60 → 3D1B30',insert='50D060',qualify='5057D0',update='50ACD0',state='508E20 (AL)'),
 stubs=sorted(stubs|{'explicit neutral hit metadata, Bullet payload delivery and relation identities; no geometry, collision construction or network delivery',
 'state-600 query only; final AI/render behavior, full actions and interruption cleanup not simulated',
 'source variants use explicit status correction 1 to compare their notification cycles, not a claim about the ghostflame attack inheriting these rows; availability and alternate paths remain unverified'}),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS', {k:len(v) for k,v in checks.items()}, 'nearby-frost concealment cases')
