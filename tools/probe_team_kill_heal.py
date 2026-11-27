"""Trace kill-triggered ally healing through original dispatch, emission, impact and HP consumers.

Allocation, actor relations, reward sinks and successful impact arrivals are fixtures.
This is isolated native execution, not a running scene or multiplayer recording.
"""
import argparse,itertools,json,math,struct
from pathlib import Path
from native_effect_runtime import BASE,OBJ,STOP,Chain,Inputs,sha
from native_ailment_runtime import Ailment
from unicorn.x86_const import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted);inputs=x;ts=x.x['tables']
raws={name:a.extracted.with_suffix('.'+name+'.param').read_bytes() for name in ('AttachEffectParam','AtkParam_Pc','BehaviorParam_PC','Bullet')}
hashes={'AttachEffectParam':'ae8128ed510a532d0fa7cb56fa9c86e4a44c9d815dd4ee01c05821d5f50a9827','AtkParam_Pc':'1ec1893420053cbfb06e3efb269ade4ba9d6a617d1d3dbb370e837847be05676','BehaviorParam_PC':'f8fa3fd27cb98d45a3e24c69d71d8751df9202e6e379dc34fd77d4ef2e1240bb','Bullet':'ddce4888040a061cf982a237e8f6e3ddce5f2162a238865a072f75d27b5e9d44'}
for name,raw in raws.items():assert sha(raw)==hashes[name]
assert sha(x.param)=='07ec636c5565d4551efeb53e6f08bc633b2aa4f2129f13c61b0638d69b1bc176'
rows=Inputs.table(raws['AttachEffectParam'],0x44);attacks=Inputs.table(raws['AtkParam_Pc'],0x1d0)
behaviors=Inputs.table(raws['BehaviorParam_PC'],0x20);bullets=Inputs.table(raws['Bullet'],0x15c)
for name,table in (('AttachEffectParam',rows),('AtkParam_Pc',attacks),('BehaviorParam_PC',behaviors),('Bullet',bullets)):
 assert len(table)==struct.unpack_from('<H',raws[name],10)[0]


att=ts['AttachEffectParam']['7090100'];root=x.spells['7090100'];leaf=x.spells['7090102']
assert [att['passiveSpEffectId_'+str(i)] for i in (1,2,3)]==[7090100,-1,-1] and att['exclusivityId']==-1
assert all(v==1 for k,v in att.items() if k.startswith('allow'))
assert (root['stateInfo'],root['spCategory'],root['effectEndurance'],root['applyIdOnGetSoul'],root['applyIdOnKillSp'])==(199,0,-1,7090101,7090103)
for id in (7090101,7090103):
 r=x.spells[str(id)];assert (r['stateInfo'],r['spCategory'],r['effectEndurance'],r['motionInterval'],r['behaviorId'])==(275,10,0,0,990901000)
assert (leaf['stateInfo'],leaf['spCategory'],leaf['effectEndurance'],leaf['motionInterval'],leaf['changeHpPoint'],leaf['changeHpRate'])==(0,10,0,.5,-20,0)
b=ts['BehaviorParam_PC']['990901000'];bullet=ts['Bullet']['900901000'];attack=ts['AtkParam_Pc']['900901000']
assert (b['refType'],b['refId'])==(1,900901000)
assert (bullet['atkId_Bullet'],bullet['hitRadius'],bullet['numShoot'],bullet['HitBulletID'],bullet['isEndlessHit'])==(900901000,15,1,-1,0)
assert [bullet['spEffectId'+str(i)] for i in range(5)]==[7090102,0,0,0,0] and bullet['spEffectIDForShooter']==0
assert math.isclose(bullet['life'],.1,abs_tol=1e-7)
assert [attack[k] for k in ('selfTarget','friendlyTarget','opposeTarget','disableHitSpEffect')]==[0,1,0,0]
assert [attack['spEffectId'+str(i)] for i in range(5)]==[-1]*5
MAN=OBJ+0x8000;OUT=OBJ+0x9000;BITS=OBJ+0x9100
class Selection(Chain):
 def __init__(self,slots,hero=1):
  super().__init__(inputs);self.slots=slots;self.hero=hero;self.cache={};self.q(OBJ+0x7118,STOP+0x900)
  self.q(MAN,OBJ+0x8100);self.q(MAN+8,OBJ+0x6000)
  self.q(OBJ+0x8158,STOP+0x901);self.q(OBJ+0x8160,STOP+0x902);self.q(OBJ+0x6378,STOP+0x903)
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v&0xffffffffffffffff);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if pc==0x214f3e0:ret(OBJ+0x7000)
  elif address==STOP+0x900:
   ptr=u.reg_read(UC_X86_REG_RDX);u.mem_write(ptr,struct.pack('<I',32));ret(ptr)
  elif pc==0x2081b0:
   assert u.reg_read(UC_X86_REG_R9)==144
   ptr=u.reg_read(UC_X86_REG_RCX);self.q(ptr+8,BITS);self.q(ptr+0x10,144);self.q(ptr+0x18,160);self.q(ptr+0x20,144);u.mem_write(BITS,bytes(20));ret(ptr)
  elif pc==0x1fe1c0:ret(0)
  elif pc==0x325c40:
   self.allocated+=0x100;ret(self.allocated)
  elif address==STOP+0x901:
   index=u.reg_read(UC_X86_REG_RDX);ret(index+1 if index<len(self.slots) else 0xffffffff)
  elif address==STOP+0x902:ret(int(1<=u.reg_read(UC_X86_REG_RDX)<=len(self.slots)))
  elif address==STOP+0x903:ret(self.hero)
  elif pc==0x69e570:
   ptr=u.reg_read(UC_X86_REG_RCX);handle=struct.unpack('<I',u.mem_read(u.reg_read(UC_X86_REG_RDX),4))[0]
   effects=self.slots[handle-1];instance=OBJ+0xa000+(handle-1)*0x80
   u.mem_write(instance+0x18,struct.pack('<6i',*(effects+[-1]*6)[:6]));u.mem_write(ptr,bytes(24));self.q(ptr+8,instance);u.mem_write(ptr+0x10,struct.pack('<I',0x80000000|2000100));ret(ptr)
  elif pc==0x69e5a0:ret()
  elif pc==0xe6e430:
   ptr=u.reg_read(UC_X86_REG_RCX);id=u.reg_read(UC_X86_REG_RDX)&0xffffffff
   if id in rows and id not in self.cache:
    self.cache[id]=OBJ+0x10000+len(self.cache)*0x100;u.mem_write(self.cache[id],rows[id])
   self.q(ptr,self.cache.get(id,0));u.mem_write(ptr+8,struct.pack('<I',id));ret(ptr)
  else:super().hook(u,address,size,user)
 def select(self):
  self.invoke(0x4fea30,[MAN,OUT]);bits=int.from_bytes(self.u.mem_read(BITS,20),'little');return [i for i in range(144) if bits>>i&1]

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
   self.stubs.add('3CED90/4D1B20 explicit neutral animation actor context');ret(OBJ+0xd000 if pc==0x3ced90 else 0)
  elif pc==0x3975d0:
   self.stubs.add('3975D0 Behavior request recorder; original state-275 emission gate')
   self.shots.append(dict(frame=self.frame,behavior=u.reg_read(UC_X86_REG_RDX),payload=bytes(u.mem_read(u.reg_read(UC_X86_REG_R9),8)).hex()));ret(1)
  else:super().hook(u,address,size,user)
class Projectile(Chain):
 def __init__(self,bid):super().__init__(x);self.bid=bid;self.frame=0;self.shots=[]
 def hook(self,u,address,size,user):
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  pc=address-BASE
  if pc==0xe87800:
   assert u.reg_read(UC_X86_REG_RDX)&0xffffffff==self.bid
   self.stubs.add('E87800 actual ailment-notification Bullet lookup')
   u.mem_write(OBJ+0xe900,bullets[self.bid]);ptr=u.reg_read(UC_X86_REG_RCX)
   u.mem_write(ptr,struct.pack('<QI',OBJ+0xe900,self.bid));ret(ptr)
  elif pc==0x347700:
   self.stubs.add('347700 projectile recorder; no scene collision');self.shots.append(self.frame);ret(1)
  else:super().hook(u,address,size,user)
def make():
 c=Hit();c.u.mem_write(OBJ+0x6074,b'\1')
 c.q(OBJ+0x65000,OBJ+0x6200);c.q(OBJ+0x65190,OBJ+0x66000);c.q(OBJ+0x66010,OBJ+0x65000);c.u.mem_write(OBJ+0x65074,b'\2')
 c.q(OBJ+0x69000,OBJ+0x69100)
 return c
def hit(c,second=False):
 global SOURCE
 old=SOURCE
 try:
  if second:SOURCE=OBJ+0x65000
  c.hit(7090102,attack=900901000)
 finally:SOURCE=old
class Reward(Onset):
 def __init__(self):
  super().__init__(1);self.rewards=[];self.q(OBJ+0x67d0,STOP+0x701)
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if pc in (0x4d1ae0,0x4b3b50):ret(0)
  elif address==STOP+0x701:
   value=u.reg_read(UC_X86_REG_RDX);self.rewards.append(value);ret(value)
  else:super().hook(u,address,size,user)
class Filter(Chain):
 def __init__(self,attack):
  super().__init__(x);self.attack=attack;self.calls=[]
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(value=0):
   u.reg_write(UC_X86_REG_RAX,value);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if pc==0x535bf9:u.reg_write(UC_X86_REG_RIP,STOP)
  elif pc==0x63f840:self.calls.append(u.reg_read(UC_X86_REG_RCX));ret(0)
  elif pc==0xe6d630:
   assert u.reg_read(UC_X86_REG_R8)==self.attack and u.reg_read(UC_X86_REG_RDX)==1
   row=OBJ+0xb000;u.mem_write(row,attacks[self.attack]);wrapper=u.reg_read(UC_X86_REG_RCX);u.mem_write(wrapper,struct.pack('<iii4xQ',self.attack,0,1,row));ret()
  else:super().hook(u,address,size,user)

checks={k:[] for k in ('selection','dispatch','recipients','timing','repeat','amounts','projectile','disabled','mixed','connected','upstream','filter')};stubs=set()
def record(key,c,**row):checks[key].append(row);stubs.update(c.stubs)
def step(c,fps=60):c.qualify();c.update(1/fps)
def hp(c,maximum=1000):return c.hp_packet(maximum)
def packet(amount):return [amount,0,amount,0,0,0,0]
for copies,hero in itertools.product((1,2,3),range(11)):
 c=Selection([[7090100]]*copies,hero);chosen=c.select();assert all(i*6 in chosen for i in range(copies))
 c.invoke(0xe6e150,[OBJ+0x9200,7090100]);roots=[c.invoke(0xe6e3b0,[OBJ+0x9200,n])&0xffffffff for n in range(3)]
 assert roots==[7090100,0xffffffff,0xffffffff]
 record('selection',c,copies=copies,hero=hero,selected=chosen,roots=roots)
for copies,special,fps in itertools.product((0,1,3),(0,1),(30,60,120)):
 c=Onset(1)
 for _ in range(copies):c.grant(7090100)
 c.qualify();c.update(0);before=len(c.grants);c.invoke(0x50a150,[OBJ,OBJ+0x6000,special]);children=c.grants[before:]
 for frame in range(fps):c.frame=frame;step(c,fps);c.invoke(0x50aa20,[OBJ])
 assert children==([7090103 if special else 7090101] if copies else [])
 assert len(c.shots)==int(bool(copies)) and all(v['behavior']==990901000 for v in c.shots)
 assert [n['id'] for n in c.nodes()]==([7090100] if copies else [])
 record('dispatch',c,copies=copies,special=special,fps=fps,children=children,shots=c.shots,nodes=c.nodes())
for (source,same),copies in itertools.product([(i,False) for i in range(10)]+[(1,True)],(1,3)):
 c=make();c.same=same;c.u.mem_write(SOURCE+0x74,bytes([source]))
 for _ in range(copies):hit(c)
 step(c);v=hp(c);assert v==packet(20*copies if source in (1,2,4) else 0)
 record('recipients',c,source=source,recipient=1,sameActor=same,hits=copies,values=v)
for fps,schedule,second in itertools.product((30,60,120),('once','same-frame','one-frame','tenth-second','one-second'),(False,True)):
 c=make();pulses=[];arrivals={'once':[0],'same-frame':[0,0],'one-frame':[0,1],'tenth-second':[0,fps//10],'one-second':[0,fps]}[schedule]
 for frame in range(2*fps+6):
  for n,at in enumerate(arrivals):
   if frame==at:hit(c,second and n>0)
  step(c,fps);v=hp(c)
  assert v==packet(20*arrivals.count(frame))
  if any(v):pulses.append(dict(frame=frame,values=v))
 assert not c.nodes();record('timing',c,fps=fps,arrivals=arrivals,secondCaster=second,pulses=pulses)
print('PASS selection/dispatch/recipients/timing',*[len(checks[k]) for k in ('selection','dispatch','recipients','timing')],flush=True)
for fps,special,copies,schedule in itertools.product((30,60,120),(0,1),(1,3),('once','same-frame','one-frame','tenth-second','one-second')):
 c=Onset(1)
 for _ in range(copies):c.grant(7090100)
 c.qualify();c.update(0);arrivals={'once':[0],'same-frame':[0,0],'one-frame':[0,1],'tenth-second':[0,fps//10],'one-second':[0,fps]}[schedule]
 for frame in range(2*fps+6):
  c.frame=frame
  for at in arrivals:
   if at==frame:c.invoke(0x50a150,[OBJ,OBJ+0x6000,special])
  step(c,fps);c.invoke(0x50aa20,[OBJ])
 assert [r['frame'] for r in c.shots]==arrivals
 record('repeat',c,fps=fps,special=special,copies=copies,kills=arrivals,shots=c.shots)
for maximum,extra,hits in itertools.product((1,99,1000,2345),(None,7611400,6840100),(1,3)):
 c=make()
 if extra:c.grant(extra)
 c.qualify();c.update(0)
 for _ in range(hits):hit(c)
 step(c);v=hp(c,maximum);assert v==packet(20*hits)
 record('amounts',c,maximum=maximum,extra=extra,hits=hits,values=v)
for fps in (30,60,120):
 c=Projectile(900901000);slot=OBJ+0x4000
 c.u.mem_write(slot+0x329,b'\1');c.u.mem_write(slot+0x334,struct.pack('<I',900901000));c.u.mem_write(slot+0x494,b'\1')
 for frame in range(fps):c.frame=frame;c.invoke(0x343280,[slot],{UC_X86_REG_XMM1:1/fps})
 assert c.shots==[0];record('projectile',c,fps=fps,shots=c.shots)
for id,mask in itertools.product((7090100,7090102),(1,2,0x40000,0x80000000)):
 c=Onset(1) if id==7090100 else make()
 if id==7090100:c.grant(id)
 else:hit(c)
 step(c);ptr=struct.unpack('<Q',c.u.mem_read(OBJ+8,8))[0];flags=struct.unpack('<I',c.u.mem_read(ptr+0x68,4))[0]
 c.u.mem_write(ptr+0x68,struct.pack('<I',flags|mask))
 if id==7090100:
  before=len(c.grants);c.invoke(0x50a150,[OBJ,OBJ+0x6000,0]);assert c.grants[before:]==[]
  record('disabled',c,id=id,mask=mask,flags=flags|mask,children=[])
 else:
  assert hp(c)==packet(0);record('disabled',c,id=id,mask=mask,flags=flags|mask,values=hp(c))
cache={}
def timeline(hits,regen):
 if (hits,regen) in cache:return cache[hits,regen]
 c=make()
 for _ in range(regen):c.grant(7001100)
 samples=[]
 for frame in range(3*60):
  if frame in (0,1,60):
   for _ in range(hits):hit(c)
  step(c);samples.append(hp(c))
 stubs.update(c.stubs);cache[hits,regen]=samples;return samples
for hits,regen in itertools.product((0,1,3),repeat=2):
 actual=timeline(hits,regen);base=timeline(hits,0);other=timeline(0,regen)
 assert all(a==[v+w for v,w in zip(b,c)] for a,b,c in zip(actual,base,other))
 checks['mixed'].append(dict(hits=hits,regen=regen,pulses=[dict(frame=i,values=v) for i,v in enumerate(actual) if any(v)]))
for fps,special,copies in itertools.product((30,60,120),(0,1),(1,3)):
 c=Onset(1);target=make();arrivals=[0,0,1,fps];pulses=[]
 for _ in range(copies):c.grant(7090100)
 c.qualify();c.update(0)
 for frame in range(2*fps+6):
  c.frame=frame;before=len(c.shots)
  for at in arrivals:
   if at==frame:c.invoke(0x50a150,[OBJ,OBJ+0x6000,special])
  step(c,fps);c.invoke(0x50aa20,[OBJ])
  for shot in c.shots[before:]:hit(target)
  step(target,fps);v=hp(target);assert v==packet(20*arrivals.count(frame))
  if any(v):pulses.append(dict(frame=frame,values=v))
 record('connected',c,fps=fps,special=special,copies=copies,kills=arrivals,shots=c.shots,pulses=pulses);stubs.update(target.stubs)
for amount,special in itertools.product((-1,0,.4,.6,1,1000),(0,1)):
 c=Reward();c.grant(7090100);c.qualify();c.update(0);before=len(c.grants)
 c.invoke(0x668380,[OBJ+0x6000,0,OBJ+0x68000,special],{UC_X86_REG_XMM1:amount});children=c.grants[before:]
 assert children==[7090103 if special else 7090101]
 # Selected positive fractions are above the native ~5e-6 rounding tolerance.
 assert c.rewards==([] if amount<=0 else [math.ceil(amount)])
 record('upstream',c,amount=amount,special=special,rewards=c.rewards,children=children)
for attack in (2,800000100,900901000):
 c=Filter(attack);p=OBJ+0xa000;c.q(p+8,OBJ+0xa800);c.q(p+0x30,0x10000001)
 for off in (0x28,0x1ec):c.u.mem_write(p+off,struct.pack('<i',-1))
 c.u.mem_write(p+0x78,struct.pack('<ii',attack,1));c.invoke(0x535a60,[p],{UC_X86_REG_XMM1:1/60})
 value=struct.unpack('<I',c.u.mem_read(p+0x28,4))[0];selfTarget=ts['AtkParam_Pc'][str(attack)]['selfTarget']
 assert value>>26==(0 if selfTarget else 1)
 record('filter',c,attack=attack,selfTarget=selfTarget,value=value,sourceHandle=0x10000001,ownerLookups=c.calls)
print('PASS counts',{k:len(v) for k,v in checks.items()},sum(map(len,checks.values())),flush=True)
out=dict(schema=1,effect=7090100,root=7090100,emitters=[7090101,7090103],leaf=7090102,amount=20,radius=15,
 exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),paramHashes=hashes,
 checks=checks,native=dict(selection='4FEA30 → E6E150 → E6E3B0',kill='668380 → 50A150 → 3C7FD0',emission='50AA20 → 397570 → 3975D0',
 projectile='343280 → 347700',hit='43BE60 → 3C80A0 → 3DB410',relation='52CC60 → 3D1B30',
 filter='535A60..535BF9 → E6D630 / 536870',insert='50D060',qualify='5057D0',update='50ACD0',hp='506EC0'),
 stubs=sorted(stubs|{'Two explicit source actors of relation classes 1 and 2; recipient class 1.',
 'Impact arrivals are fixtures, not projectile candidate selection or scene collision.',
 'Connected timeline delivers a successful impact on each actual emission; no spatial/network latency.',
 '668380 reward and notification sinks are recorded; 4D1AE0 is an explicit false predicate. Enemy death/reward ownership and saved-reward replay are not simulated.',
 '535A60..535BF9 executes original filter construction with actual attack rows, an explicit owner handle and absent 63F840 owner lookup. The collision consumer is not executed.'}),
 limitations=['Forced same-actor impact bypasses upstream selfTarget=0; it cannot establish that this heal applies to the killer.',
 'No full spatial candidate search/collision, distance-boundary tests, final current HP write/cap or network latency.',
 'The kill branch flag is an explicit input, not a last-hit ownership flag. Both branches use the same current healing payload.',
 'DLL rewrites, full equipment rebuild, death, reload and multiplayer are not simulated.'],gameplayVerified=False)
a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
