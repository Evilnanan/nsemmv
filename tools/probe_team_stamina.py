"""Trace the team stamina aura through original selection, emission, impact and speed consumers.

Actor relations, allocation and successful impact arrivals are explicit fixtures.
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

att=ts['AttachEffectParam']['7050000'];root=x.spells['7050000'];leaf=x.spells['7050001']
assert [att['passiveSpEffectId_'+str(i)] for i in (1,2,3)]==[7050000,-1,-1] and att['exclusivityId']==-1
assert all(v==1 for k,v in att.items() if k.startswith('allow'))
assert (root['stateInfo'],root['spCategory'],root['effectEndurance'],root['motionInterval'],root['behaviorId'])==(275,0,-1,1,990500000)
assert (leaf['stateInfo'],leaf['spCategory'],leaf['effectEndurance'],leaf['motionInterval'],leaf['staminaRecoverChangeSpeed'])==(0,20,1,1,4)
b=ts['BehaviorParam_PC']['990500000'];bullet=ts['Bullet']['900500000'];attack=ts['AtkParam_Pc']['800000100']
assert (b['refType'],b['refId'])==(1,900500000)
assert (bullet['atkId_Bullet'],bullet['spEffectId0'],bullet['hitRadius'],bullet['numShoot'],bullet['HitBulletID'],bullet['isEndlessHit'])==(800000100,7050001,10,1,-1,0)
assert math.isclose(bullet['life'],.1,abs_tol=1e-7)
assert [attack[k] for k in ('selfTarget','friendlyTarget','opposeTarget','disableHitSpEffect')]==[0,1,0,0]
assert struct.unpack('<f',x.pe.get_data(0x39a8b80,4))[0]==45
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
  c.hit(7050001,attack=800000100)
 finally:SOURCE=old
def pc_speed(c):
 old=bytes(c.u.mem_read(OBJ+0x61b8,8));c.q(OBJ+0x61b8,OBJ+0x69000)
 try:
  c.invoke(0x66caa0,[OBJ+0x6000]);return struct.unpack('<f',struct.pack('<I',c.u.reg_read(UC_X86_REG_XMM0)&0xffffffff))[0]
 finally:c.u.mem_write(OBJ+0x61b8,old)

checks={k:[] for k in ('selection','recipients','timing','emission','projectile','disabled','extension','mixed','connected')};stubs=set()
def record(key,c,**row):checks[key].append(row);stubs.update(c.stubs)
def step(c,fps=60):c.qualify();c.update(1/fps)
def speed(c):
 c.invoke(0x505aa0,[OBJ]);return struct.unpack('<f',struct.pack('<I',c.u.reg_read(UC_X86_REG_XMM0)&0xffffffff))[0]
for copies,hero in itertools.product((1,2,3),range(11)):
 c=Selection([[7050000]]*copies,hero);chosen=c.select();assert all(i*6 in chosen for i in range(copies))
 c.invoke(0xe6e150,[OBJ+0x9200,7050000]);roots=[c.invoke(0xe6e3b0,[OBJ+0x9200,n])&0xffffffff for n in range(3)]
 assert roots==[7050000,0xffffffff,0xffffffff]
 record('selection',c,copies=copies,hero=hero,selected=chosen,roots=roots)
print('PASS selection',len(checks['selection']),flush=True)
for (source,same),copies in itertools.product([(i,False) for i in range(10)]+[(1,True)],(1,3)):
 c=make();c.same=same;c.u.mem_write(SOURCE+0x74,bytes([source]))
 for _ in range(copies):hit(c)
 step(c);v=pc_speed(c);expected=49 if source in (1,2,4) else 45
 assert v==expected and speed(c)==expected-45
 record('recipients',c,source=source,recipient=1,sameActor=same,hits=copies,value=v,nodes=c.nodes())
for fps,times,second in itertools.product((30,60,120),('once','same-frame','half-second','one-second'),(False,True)):
 c=make();assert pc_speed(c)==45
 hits={'once':[0],'same-frame':[0,0],'half-second':[0,fps//2],'one-second':[0,fps]}[times]
 transitions=[];last=None
 for frame in range(3*fps+6):
  for nth,arrival in enumerate(hits):
   if frame==arrival:hit(c,second and nth>0)
  step(c,fps);value=pc_speed(c);assert value in (45,49)
  assert len([n for n in c.nodes() if n['id']==7050001])<=1
  if value!=last:transitions.append(dict(frame=frame,value=value));last=value
 assert [r['value'] for r in transitions]==[49,45]
 assert abs(transitions[-1]['frame']-max(hits)-fps)<=3
 record('timing',c,fps=fps,arrivals=hits,secondCaster=second,transitions=transitions)
print('PASS recipients/timing',len(checks['recipients']),len(checks['timing']),flush=True)
for copies,fps in itertools.product((1,3),(30,60,120)):
 c=Onset(1)
 for _ in range(copies):c.grant(7050000)
 for frame in range(3*fps+6):c.frame=frame;step(c,fps);c.invoke(0x50aa20,[OBJ])
 assert len(c.shots)==4 and all(r['behavior']==990500000 for r in c.shots)
 assert c.shots[0]['frame']==0 and all(abs(r['frame']-i*fps)<=1 for i,r in enumerate(c.shots))
 record('emission',c,copies=copies,fps=fps,shots=c.shots,nodes=c.nodes())
for fps in (30,60,120):
 c=Projectile(900500000);slot=OBJ+0x4000
 c.u.mem_write(slot+0x329,b'\1');c.u.mem_write(slot+0x334,struct.pack('<I',900500000));c.u.mem_write(slot+0x494,b'\1')
 for frame in range(fps):c.frame=frame;c.invoke(0x343280,[slot],{UC_X86_REG_XMM1:1/fps})
 assert c.shots==[0];record('projectile',c,fps=fps,shots=c.shots)
for mask in (1,2,0x40000,0x80000000):
 c=make();hit(c);step(c);assert pc_speed(c)==49
 ptr=struct.unpack('<Q',c.u.mem_read(OBJ+8,8))[0];flags=struct.unpack('<I',c.u.mem_read(ptr+0x68,4))[0];c.u.mem_write(ptr+0x68,struct.pack('<I',flags|mask))
 assert pc_speed(c)==45;record('disabled',c,mask=mask,flags=flags|mask,value=pc_speed(c))
for extra in (None,7006400,8330500):
 c=make()
 if extra:c.grant(extra)
 hit(c);c.qualify();c.update(.25);node=next(n for n in c.nodes() if n['id']==7050001)
 assert math.isclose(node['lifetime'],.75,abs_tol=1e-6) and pc_speed(c)==49
 record('extension',c,extra=extra,node=node,value=pc_speed(c))
for counts in itertools.product((0,1,3),repeat=4):
 c=make()
 for root,count in zip((7035100,7035110,7035120),counts[1:]):
  for _ in range(count):c.grant(root)
 c.qualify();c.update(0)
 for leaf,count in zip((7035102,7035112,7035122),counts[1:]):
  for _ in range(count):c.grant(leaf)
 for _ in range(counts[0]):hit(c)
 for _ in range(3):step(c)
 expected=45+sum(v for v,n in zip((4,10,17,20),counts) if n)
 assert pc_speed(c)==expected
 record('mixed',c,counts=counts,value=pc_speed(c),nodes=c.nodes())
for copies,fps in itertools.product((1,3),(30,60,120)):
 source=Onset(1);target=make()
 for _ in range(copies):source.grant(7050000)
 changes=[];last=None
 for frame in range(5*fps):
  before=len(source.shots);source.frame=frame
  if frame<3*fps:step(source,fps);source.invoke(0x50aa20,[OBJ])
  if len(source.shots)>before:hit(target)
  step(target,fps);v=pc_speed(target)
  if v!=last:changes.append(dict(frame=frame,value=v));last=v
 assert [r['value'] for r in changes]==[49,45]
 assert abs(changes[-1]['frame']-source.shots[-1]['frame']-fps)<=3
 record('connected',target,copies=copies,fps=fps,emissions=source.shots,changes=changes)
 stubs.update(source.stubs)
print('PASS counts',{k:len(v) for k,v in checks.items()},sum(map(len,checks.values())),flush=True)
out=dict(schema=1,effect=7050000,root=7050000,leaf=7050001,amount=4,radius=10,lease=1,interval=1,
 exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),paramHashes=hashes,
 checks=checks,native=dict(selection='4FEA30 → E6E150 → E6E3B0',emission='50AA20 → 397570 → 3975D0',
 projectile='343280 → 347700',hit='43BE60 → 3C80A0 → 3DB410',relation='52CC60 → 3D1B30',
 grant='3C7FD0',insert='50D060',qualify='5057D0',update='50ACD0',speed='505AA0 → 66CAA0 → 6CABB0'),
 stubs=sorted(stubs|{'Two explicit source actors of relation classes 1 and 2; recipient class 1.',
 'PC getter actor+1B8 supplies explicit neutral stat context; restored before impact delivery.',
 'Impact arrivals are fixtures, not projectile candidate selection or scene collision.',
 'Connected timeline delivers a successful impact on each actual emission; no spatial/network latency.'}),
 limitations=['Forced same-actor impact bypasses upstream selfTarget=0; it cannot establish that the aura affects its caster.',
 'No full spatial candidate search/collision, distance-boundary tests, network latency or final stamina integration.',
 'Speed is an additive parameter, not a claimed percentage or per-second final recovery.',
 'DLL rewrites, full equipment rebuild, death, reload and multiplayer are not simulated.'],gameplayVerified=False)
a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
