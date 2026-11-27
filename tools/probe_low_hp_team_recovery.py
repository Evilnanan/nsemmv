"""Trace low-HP team recovery through integer HP qualification, aura emission and healing.

Allocation, actor identities, HP resources and impact arrivals are explicit fixtures.
Original qualification, effects and recovery consumers execute; no full scene is run.
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



f32=lambda v:struct.unpack('<f',struct.pack('<f',v))[0]
assert x.pe.get_data(0x3e0d94,0x21).hex()=='488b87b8010000488b08e83d600400488b8b900100000f28c84c8bc7e81b4a1200'
att=ts['AttachEffectParam']['7012200'];root=x.spells['7012200'];leaf=x.spells['7012201'];emitter=x.spells['7012202']
assert [att['passiveSpEffectId_'+str(i)] for i in (1,2,3)]==[7012200,-1,-1] and att['exclusivityId']==-1
assert all(v==1 for k,v in att.items() if k.startswith('allow'))
assert (root['stateInfo'],root['spCategory'],root['effectEndurance'],root['conditionHp'],root['conditionHpRate'],root['motionInterval'],root['cycleOccurrenceSpEffectId'])==(2307,0,-1,40,-1,0,7012202)
assert (emitter['stateInfo'],emitter['spCategory'],emitter['effectEndurance'],emitter['invocationConditionsStateChange1'],emitter['behaviorId'])==(275,20,50,2307,990902000)
assert math.isclose(emitter['motionInterval'],50.1,abs_tol=1e-5)
assert (leaf['stateInfo'],leaf['spCategory'],leaf['effectEndurance'],leaf['motionInterval'],leaf['changeHpPoint'],leaf['changeHpRate'],leaf['conditionHp'],leaf['conditionHpRate'])==(50,20,50,1,-1,-.5,-1,-1)
assert all(leaf['invocationConditionsStateChange'+str(i)]==0 for i in (1,2,3))
b=ts['BehaviorParam_PC']['990902000'];bullet=ts['Bullet']['900902000'];attack=ts['AtkParam_Pc']['900902000']
assert (b['refType'],b['refId'])==(1,900902000)
assert (bullet['atkId_Bullet'],bullet['hitRadius'],bullet['numShoot'],bullet['HitBulletID'],bullet['isEndlessHit'])==(900902000,15,1,-1,0)
assert [bullet['spEffectId'+str(i)] for i in range(5)]==[7012201,0,0,0,0] and bullet['spEffectIDForShooter']==0
assert math.isclose(bullet['life'],.1,abs_tol=1e-7)
assert [attack[k] for k in ('selfTarget','friendlyTarget','opposeTarget','disableHitSpEffect')]==[1,1,0,0]
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
  c.hit(7012201,attack=900902000)
 finally:SOURCE=old
class HealthOnset(Onset):
 def __init__(self):super().__init__(1);self.ratios=[]
 def hook(self,u,address,size,user):
  pc=address-BASE
  if pc==0x3e0da3:self.ratios.append(struct.unpack('<f',(u.reg_read(UC_X86_REG_XMM0)&0xffffffff).to_bytes(4,'little'))[0])
  elif pc==0x3e0db5:u.reg_write(UC_X86_REG_RIP,STOP)
  else:super().hook(u,address,size,user)
 def health_step(self,current,maximum,dt=1/60):
  self.u.mem_write(OBJ+0xe140,struct.pack('<ii',current,maximum));self.u.reg_write(UC_X86_REG_RBX,OBJ+0x6000);self.u.reg_write(UC_X86_REG_RDI,OBJ+0x6000)
  self.invoke(0x3e0d94,[0,0]);self.update(dt);self.invoke(0x50aa20,[OBJ])
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


checks={k:[] for k in ('selection','threshold','emission','recipients','healing','refresh','reenter','amounts','projectile','disabled','extension','mixed','connected','filter')};stubs=set()
def record(key,c,**row):checks[key].append(row);stubs.update(c.stubs)
def step(c,fps=60):c.qualify();c.update(1/fps)
def packet(v):return [v,0,v,0,0,0,0]
def active(c):return any(n['id']==7012201 and not n['flags']&0x800c0003 for n in c.nodes())
for copies,hero in itertools.product((1,2,3),range(11)):
 c=Selection([[7012200]]*copies,hero);chosen=c.select();assert all(i*6 in chosen for i in range(copies))
 c.invoke(0xe6e150,[OBJ+0x9200,7012200]);roots=[c.invoke(0xe6e3b0,[OBJ+0x9200,n])&0xffffffff for n in range(3)]
 assert roots==[7012200,0xffffffff,0xffffffff]
 record('selection',c,copies=copies,hero=hero,selected=chosen,roots=roots)
for (current,maximum),copies in itertools.product(((1,2),(39,100),(40,100),(399,1000),(400,1000),(401,1000),(999,1000),(3999,10000),(4000,10000)),(0,1,3)):
 c=HealthOnset()
 for _ in range(copies):c.grant(7012200)
 for frame in range(6):c.frame=frame;c.health_step(current,maximum)
 expected=f32(f32(current)/f32(maximum));assert c.ratios==[expected]*6
 assert len(c.shots)==int(bool(copies) and expected<=f32(40*f32(.01)))
 assert sum(n['id']==7012200 for n in c.nodes())==int(bool(copies))
 record('threshold',c,current=current,maximum=maximum,copies=copies,ratios=c.ratios,shots=c.shots,nodes=c.nodes())
print('PASS selection/threshold',len(checks['selection']),len(checks['threshold']),flush=True)
for copies,mode in itertools.product((1,3),('low','rise','return')):
 c=HealthOnset()
 for _ in range(copies):c.grant(7012200)
 samples=[]
 for frame in range(110*60):
  t=frame/60;current=300 if mode=='low' or t<5 or (mode=='return' and t>=20) else 800
  c.frame=frame;c.health_step(current,1000)
  if frame in (0,1,2,60,299,300,301,302,600,1199,1200,1201,1202,3000,6000):samples.append(dict(frame=frame,current=current,nodes=c.nodes()))
 expected={'low':[1,3008,6014],'rise':[1],'return':[1,1201,4208]}[mode]
 assert [r['frame'] for r in c.shots]==expected
 assert all(r['behavior']==990902000 for r in c.shots)
 if mode!='low':assert all(n['id']!=7012202 for r in samples if r['frame'] in (301,302,600,1199) for n in r['nodes'])
 record('emission',c,copies=copies,mode=mode,shots=c.shots,samples=samples);print('PASS emission',copies,mode,flush=True)
for source,same in [(i,False) for i in range(10)]+[(1,True)]:
 c=make();c.same=same;c.u.mem_write(SOURCE+0x74,bytes([source]));hit(c)
 for dt in (0,1.01,0):c.qualify();c.update(dt)
 v=c.hp_packet(1000);assert v==packet(6 if source in (1,2,4) else 0)
 record('recipients',c,source=source,sameActor=same,values=v)
for fps,copies in itertools.product((30,60,120),(1,3)):
 c=make();pulses=[];changes=[];last=None
 for _ in range(copies):hit(c)
 for frame in range(52*fps):
  step(c,fps);v=c.hp_packet(1000);now=active(c)
  if now!=last:changes.append(dict(frame=frame,active=now));last=now
  assert v in (packet(0),packet(6))
  if any(v):pulses.append(dict(frame=frame,values=v))
 assert [r['active'] for r in changes]==[True,False] and abs(changes[-1]['frame']-50*fps)<=3
 assert abs(pulses[0]['frame']-fps)<=1 and all(b['frame']-a['frame']==fps for a,b in zip(pulses,pulses[1:]))
 assert len(pulses) in (49,50)
 record('healing',c,fps=fps,copies=copies,pulses=pulses,changes=changes);print('PASS healing',fps,copies,flush=True)
for times,second in itertools.product(((0,),(0,1),(0,6),(0,60),(0,300)),(False,True)):
 c=make();pulses=[];changes=[];last=None
 for frame in range(56*60):
  for n,at in enumerate(times):
   if at==frame:hit(c,second and n>0)
  step(c);v=c.hp_packet(1000);now=active(c)
  if now!=last:changes.append(dict(frame=frame,active=now));last=now
  assert v in (packet(0),packet(6))
  if any(v):pulses.append(dict(frame=frame,values=v))
 assert [r['active'] for r in changes]==[True,False] and abs(changes[-1]['frame']-max(times)-3000)<=3
 assert [p['frame'] for p in pulses]==[61+60*i for i in range(len(pulses))]
 record('refresh',c,arrivals=times,secondCaster=second,pulses=pulses,changes=changes)
print('PASS refresh',len(checks['refresh']),flush=True)
for fps,gap,copies in itertools.product((30,60,120),(1,2,6),(1,3)):
 c=HealthOnset()
 for _ in range(copies):c.grant(7012200)
 for frame in range(6*fps):
  c.frame=frame;current=800 if 5*fps<=frame<5*fps+gap else 300;c.health_step(current,1000,1/fps)
 assert [r['frame'] for r in c.shots]==[1,5*fps+gap+1]
 record('reenter',c,fps=fps,gap=gap,copies=copies,shots=c.shots)
for maximum,extra,copies in itertools.product((1,99,100,199,200,201,999,1000,1001,2345),(None,7611400,6840100),(1,3)):
 c=make()
 if extra:c.grant(extra)
 for _ in range(copies):hit(c)
 for dt in (0,1.01,0):c.qualify();c.update(dt)
 v=c.hp_packet(maximum);assert v==packet(int(1+maximum*.005))
 record('amounts',c,maximum=maximum,extra=extra,copies=copies,values=v)
for fps in (30,60,120):
 c=Projectile(900902000);slot=OBJ+0x4000
 c.u.mem_write(slot+0x329,b'\1');c.u.mem_write(slot+0x334,struct.pack('<I',900902000));c.u.mem_write(slot+0x494,b'\1')
 for frame in range(fps):c.frame=frame;c.invoke(0x343280,[slot],{UC_X86_REG_XMM1:1/fps})
 assert c.shots==[0];record('projectile',c,fps=fps,shots=c.shots)
for mask in (1,2,0x40000,0x80000000):
 c=make();hit(c)
 for dt in (0,1.01,0):c.qualify();c.update(dt)
 assert c.hp_packet(1000)==packet(6)
 ptr=struct.unpack('<Q',c.u.mem_read(OBJ+8,8))[0];flags=struct.unpack('<I',c.u.mem_read(ptr+0x68,4))[0];c.u.mem_write(ptr+0x68,struct.pack('<I',flags|mask));v=c.hp_packet(1000)
 assert v==packet(0);record('disabled',c,mask=mask,flags=flags|mask,values=v)
for extra in (None,7006400,8330500):
 c=make()
 if extra:c.grant(extra)
 hit(c);c.qualify();c.update(0);c.qualify();c.update(5);node=next(n for n in c.nodes() if n['id']==7012201)
 assert math.isclose(node['lifetime'],45,abs_tol=.001);record('extension',c,extra=extra,node=node)
cache={}
def timeline(copies,regen):
 if (copies,regen) in cache:return cache[copies,regen]
 c=make()
 for _ in range(regen):c.grant(7001100)
 for _ in range(copies):hit(c)
 samples=[]
 for frame in range(6*60):step(c);samples.append(c.hp_packet(1000))
 stubs.update(c.stubs);cache[copies,regen]=samples;return samples
for copies,regen in itertools.product((0,1,3),repeat=2):
 actual=timeline(copies,regen);base=timeline(copies,0);other=timeline(0,regen)
 assert all(a==[v+w for v,w in zip(b,c)] for a,b,c in zip(actual,base,other))
 checks['mixed'].append(dict(copies=copies,regen=regen,pulses=[dict(frame=i,values=v) for i,v in enumerate(actual) if any(v)]))
for copies,mode in itertools.product((1,3),('low','rise','return')):
 source=HealthOnset();target=make();pulses=[];changes=[];last=None
 for _ in range(copies):source.grant(7012200)
 for frame in range(65*60):
  t=frame/60;current=300 if mode=='low' or t<5 or (mode=='return' and t>=20) else 800
  source.frame=frame;before=len(source.shots);source.health_step(current,1000)
  for shot in source.shots[before:]:hit(target)
  step(target);v=target.hp_packet(1000);now=active(target)
  if now!=last:changes.append(dict(frame=frame,active=now));last=now
  assert v in (packet(0),packet(6))
  if any(v):pulses.append(dict(frame=frame,values=v))
 assert pulses and pulses[0]['frame']==62
 assert any(p['frame']>300 for p in pulses)  # Healing persists after the source rises above 40%.
 if mode=='rise':assert [r['active'] for r in changes]==[False,True,False] and len(pulses)==50
 elif mode=='return':assert [r['active'] for r in changes]==[False,True] and all(p['frame']==62+i*60 for i,p in enumerate(pulses))
 else:assert [r['frame'] for r in source.shots]==[1,3008]
 record('connected',source,copies=copies,mode=mode,shots=source.shots,pulses=pulses,changes=changes);stubs.update(target.stubs)
for attack in (2,900902000,900901000):
 c=Filter(attack);p=OBJ+0xa000;c.q(p+8,OBJ+0xa800);c.q(p+0x30,0x10000001)
 for off in (0x28,0x1ec):c.u.mem_write(p+off,struct.pack('<i',-1))
 c.u.mem_write(p+0x78,struct.pack('<ii',attack,1));c.invoke(0x535a60,[p],{UC_X86_REG_XMM1:1/60})
 value=struct.unpack('<I',c.u.mem_read(p+0x28,4))[0];selfTarget=ts['AtkParam_Pc'][str(attack)]['selfTarget'];assert value>>26==(0 if selfTarget else 1)
 record('filter',c,attack=attack,selfTarget=selfTarget,value=value,sourceHandle=0x10000001)
print('PASS counts',{k:len(v) for k,v in checks.items()},sum(map(len,checks.values())),flush=True)
out=dict(schema=1,effect=7012200,root=7012200,emitter=7012202,leaf=7012201,amount=1,percent=.5,radius=15,duration=50,interval=1,emissionInterval=emitter['motionInterval'],
 exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),paramHashes=hashes,
 checks=checks,native=dict(selection='4FEA30 → E6E150 → E6E3B0',health='3E0D94..3E0DB5 → 426DE0 → 5057D0',emission='50AA20 → 397570 → 3975D0',
 projectile='343280 → 347700',hit='43BE60 → 3C80A0 → 3DB410',relation='52CC60 → 3D1B30',
 filter='535A60..535BF9 → E6D630 / 536870',insert='50D060',qualify='5057D0',update='50ACD0',hp='506EC0'),
 stubs=sorted(stubs|{'Source current/max HP integers are explicit inputs to the original actor qualification block, not an actual scene HP write loop.',
 'Two explicit source actors of relation classes 1 and 2; recipient class 1.',
 'Impact arrivals are fixtures, not projectile candidate selection or scene collision.',
 'Connected timeline delivers a successful impact on each actual emission; no spatial/network latency.',
 '535A60..535BF9 executes original filter construction with actual attack rows, an explicit owner handle and absent 63F840 owner lookup. The collision consumer is not executed.'}),
 limitations=['No complete spatial candidate search/collision, distance-boundary tests, current HP write/cap or automatic HP-driven feedback loop.',
 'The final pulse depends on update boundaries (49/50 pulses in tested frame rates); no universal total healing is claimed.',
 'Only listed modifier and effect combinations are tested.',
 'DLL rewrites, full equipment rebuild, death, reload and multiplayer are not simulated.'],gameplayVerified=False)
a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
