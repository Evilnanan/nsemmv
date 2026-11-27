"""Trace nearby scarlet-rot recovery through native onset, notifications and healing.

Actors, impact arrivals and allocator/lookup contexts are explicit fixtures.
Original equipment selection, hit delivery, status onset, effect timers and
HP consumers execute; this is not a running scene or gameplay recording.
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
EFFECT=7260900;ROOT=7260900;LEAF=7260901;MARKER=1121;EMITTER=1120;BEHAVIOR=2108;BULLET=1025
att=ts['AttachEffectParam'][str(EFFECT)];r=x.spells[str(ROOT)];leaf=x.spells[str(LEAF)];emitter=x.spells[str(EMITTER)]
assert [att['passiveSpEffectId_'+str(n)] for n in (1,2,3)]==[ROOT,-1,-1] and att['exclusivityId']==-1
assert all(v==1 for k,v in att.items() if k.startswith('allow'))
assert (r['spCategory'],r['effectEndurance'],r['motionInterval'],r['cycleOccurrenceSpEffectId'],r['invocationConditionsStateChange1'])==(20,-1,0,LEAF,2064)
assert (leaf['spCategory'],leaf['stateInfo'],leaf['effectEndurance'],leaf['changeHpPoint'])==(20,50,15,-15)
assert math.isclose(leaf['motionInterval'],1.3,rel_tol=1e-6) and math.isclose(leaf['changeHpRate'],-.15,rel_tol=1e-6)
assert (emitter['stateInfo'],emitter['effectEndurance'],emitter['motionInterval'],emitter['invocationConditionsStateChange1'],emitter['behaviorId'])==(275,900,999,5,BEHAVIOR)
b=ts['BehaviorParam_PC'][str(BEHAVIOR)];bullet=ts['Bullet'][str(BULLET)];assert (b['refType'],b['refId'])==(1,BULLET)
assert (bullet['atkId_Bullet'],bullet['spEffectId0'],bullet['life'],bullet['hitRadius'],bullet['hitRadiusMax'],bullet['numShoot'],bullet['HitBulletID'],bullet['isEndlessHit'])==(2,MARKER,.5,7,7,1,-1,0)
assert x.spells[str(MARKER)]['stateInfo']==2064
assert [ts['AtkParam_Pc']['2'][k] for k in ('selfTarget','friendlyTarget','opposeTarget','disableHitSpEffect')]==[1,0,1,0]
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
   self.stubs.add('3975D0 Behavior request recorder; original state-467 emission gate')
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
checks={k:[] for k in ('selection','recipients','onset','amounts','lifetime','refresh','mixed','reinfection','disabled','extension','variants','projectile')};stubs=set()
def record(key,c,**row):checks[key].append(row);stubs.update(c.stubs)
def step(c,fps=60):c.qualify();c.update(1/fps)
def active(c):return any(n['id']==LEAF and not n['flags']&0x800c0003 for n in c.nodes())
def equip(copies=1,sourceType=6,same=False):
 c=Hit();c.same=same;c.u.mem_write(SOURCE+0x74,bytes([sourceType]));c.u.mem_write(OBJ+0x6074,b'\1')
 for _ in range(copies):c.grant(ROOT)
 step(c);return c
def hp(c,maximum=1000):return c.hp_packet(maximum)
def onset(resistance=1):
 c=Onset(resistance);c.kind=1;c.q(OBJ+0x63f8,STOP+0x302)
 c.stubs.add('actor virtual +1F8 returns no auxiliary animation component; native 27AEC0 executes')
 return c
def emit_step(c,fps=60):step(c,fps);c.invoke(0x50aa20,[OBJ])
for copies,hero in itertools.product((1,2,3,6),range(11)):
 c=Selection([[EFFECT]]*copies,hero);bits=c.select();assert all(i*6 in bits for i in range(copies))
 c.invoke(0xe6e150,[OBJ+0x9200,EFFECT]);roots=[c.invoke(0xe6e3b0,[OBJ+0x9200,n])&0xffffffff for n in range(3)];assert roots==[ROOT,0xffffffff,0xffffffff]
 record('selection',c,copies=copies,hero=hero,bits=bits,roots=roots)
for copies,(kind,same) in itertools.product((0,1,3),[(i,False) for i in range(10)]+[(1,True)]):
 c=equip(copies,kind,same);c.hit(MARKER);present=any(n['id']==MARKER for n in c.nodes())
 for _ in range(6):step(c)
 eligible=same or kind in (6,7,8,9);assert present==eligible and active(c)==bool(copies and eligible)
 assert sum(n['id']==ROOT for n in c.nodes())==int(bool(copies))
 record('recipients',c,copies=copies,sourceType=kind,same=same,markerPresent=present,active=active(c),nodes=c.nodes())
for resistance,immune,fps in itertools.product((1,59,60,61),(False,True),(30,60,120)):
 c=onset(resistance)
 if immune:c.grant(9642)
 c.qualify();c.update(0);c.hit(21005,2,scale=1)
 for frame in range(3*fps):c.frame=frame;emit_step(c,fps)
 expected=not immune and resistance<=60;assert len(c.shots)==int(expected)
 if expected:assert c.shots[0]['behavior']==BEHAVIOR and c.shots[0]['frame']<=3
 record('onset',c,resistance=resistance,immune=immune,fps=fps,shots=c.shots,nodes=c.nodes())
print('PASS selection/recipients/onset',len(checks['selection']),len(checks['recipients']),len(checks['onset']),flush=True)
for copies,maximum,extra in itertools.product((0,1,3),(1,99,100,333,499,500,666,667,999,1000,1001,2000,10000),(None,7611400,6840100)):
 c=Hit()
 if extra is not None:c.grant(extra)
 for _ in range(copies):c.grant(LEAF)
 # Advance past the first interval, then process its due tick in the next update.
 for dt in (0,1.31,0):c.qualify();c.update(dt)
 values=hp(c,maximum);amount=int(15+maximum*.0015) if copies else 0
 assert values==[amount,0,amount,0,0,0,0],(copies,maximum,extra,values)
 record('amounts',c,copies=copies,maximum=maximum,otherEffect=extra,values=values)
for copies,fps in itertools.product((1,3),(30,60,120)):
 c=equip(copies);c.hit(MARKER);changes=[];pulses=[];previous=None
 for frame in range(16*fps):
  step(c,fps);present=active(c);values=hp(c)
  assert sum(n['id']==LEAF for n in c.nodes())<=1
  if any(values):assert values==[16,0,16,0,0,0,0];pulses.append(dict(frame=frame,values=values))
  if present!=previous:changes.append(dict(frame=frame,active=present));previous=present
 assert [v['active'] for v in changes]==[False,True,False] and len(pulses)==11
 assert abs(changes[-1]['frame']-changes[1]['frame']-15*fps)<=4
 assert abs(pulses[0]['frame']-changes[1]['frame']-1.3*fps)<=3
 assert all(abs(b['frame']-a['frame']-1.3*fps)<=1 for a,b in zip(pulses,pulses[1:]))
 record('lifetime',c,copies=copies,fps=fps,changes=changes,pulses=pulses);print('PASS lifetime',copies,fps,flush=True)
for copies,times in itertools.product((1,3),((0,),(0,1),(0,6),(0,60),(0,300))):
 c=equip(copies);changes=[];pulses=[];previous=None
 for frame in range(21*60):
  if frame in times:c.hit(MARKER)
  step(c);present=active(c);values=hp(c)
  if any(values):assert values==[16,0,16,0,0,0,0];pulses.append(dict(frame=frame,values=values))
  if present!=previous:changes.append(dict(frame=frame,active=present));previous=present
 assert [v['active'] for v in changes]==[False,True,False]
 assert abs(changes[-1]['frame']-times[-1]-900)<=5
 assert [v['frame'] for v in pulses]==list(range(81,changes[-1]['frame'],78))
 record('refresh',c,copies=copies,hits=times,changes=changes,pulses=pulses);print('PASS refresh',copies,times,flush=True)
traces={}
for copies,other in itertools.product((0,1,3),repeat=2):
 c=Hit()
 for _ in range(copies):c.grant(LEAF)
 for _ in range(other):c.grant(7001100)
 c.qualify();c.update(0);trace=[]
 for frame in range(16*60):step(c);trace.append(hp(c))
 traces[copies,other]=trace
 if copies and other:
  assert trace==[[a+b for a,b in zip(v,w)] for v,w in zip(traces[copies,0],traces[0,other])]
 record('mixed',c,copies=copies,otherEffect=7001100,otherCopies=other,pulses=[dict(frame=i,values=v) for i,v in enumerate(trace) if any(v)])
print('PASS mixed',len(checks['mixed']),flush=True)
for fps in (30,60,120):
 c=onset();snapshots=[];c.qualify();c.update(0)
 for frame in range(48*fps):
  c.frame=frame
  if frame in (0,45*fps):c.hit(21005,2,scale=1)
  emit_step(c,fps)
  if frame in (2,44*fps,45*fps+2):snapshots.append(dict(frame=frame,nodes=c.nodes()))
 assert len(c.shots)==2 and all(v['behavior']==BEHAVIOR for v in c.shots)
 assert c.shots[0]['frame']<=3 and abs(c.shots[1]['frame']-45*fps)<=3
 assert not snapshots[1]['nodes']
 record('reinfection',c,fps=fps,shots=c.shots,snapshots=snapshots);print('PASS reinfection',fps,flush=True)
for mask in (1,2,0x40000,0x80000000):
 c=Hit();c.grant(LEAF)
 for dt in (0,1.31,0):c.qualify();c.update(dt)
 assert hp(c)==[16,0,16,0,0,0,0]
 ptr=struct.unpack('<Q',c.u.mem_read(OBJ+8,8))[0];flags=struct.unpack('<I',c.u.mem_read(ptr+0x68,4))[0];assert flags&4
 c.u.mem_write(ptr+0x68,struct.pack('<I',flags|mask));values=hp(c);assert values==[0]*7
 record('disabled',c,mask=mask,originalFlags=flags,values=values)
for extra in (None,7006400,8330500):
 c=Hit()
 if extra is not None:c.grant(extra)
 c.grant(LEAF)
 for dt in (0,1):c.qualify();c.update(dt)
 node=next(n for n in c.nodes() if n['id']==LEAF);assert math.isclose(node['lifetime'],14,abs_tol=.001)
 record('extension',c,otherEffect=extra,node=node)
for id,mode in ((21005,'hit'),(7170103,'hit'),(6820102,'self'),(6851401,'self')):
 c=onset();c.qualify();c.update(0)
 if mode=='hit':c.hit(id,2,scale=1)
 else:c.grant(id)
 for frame in range(180):c.frame=frame;emit_step(c)
 assert len(c.shots)==1 and c.shots[0]['behavior']==BEHAVIOR and c.shots[0]['frame']<=3,(id,mode,c.shots,c.nodes())
 record('variants',c,effect=id,delivery=mode,shots=c.shots,nodes=c.nodes())
for fps in (30,60,120):
 c=Projectile(BULLET);slot=OBJ+0x4000;c.u.mem_write(slot+0x329,b'\1');c.u.mem_write(slot+0x334,struct.pack('<I',BULLET));c.u.mem_write(slot+0x494,b'\1')
 for frame in range(fps):c.frame=frame;c.invoke(0x343280,[slot],{UC_X86_REG_XMM1:1/fps})
 assert c.shots==[0];record('projectile',c,fps=fps,shots=c.shots)
out=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),paramHashes=hashes,
 effect=EFFECT,root=ROOT,leaf=LEAF,marker=MARKER,emitter=EMITTER,behavior=BEHAVIOR,bullet=BULLET,duration=15,interval=1.3,flat=15,percent=.15,
 checks=checks,native=dict(selection='4FEA30 → E6E150 → E6E3B0',hit='43BE60 → 3C80A0 → 3DB410',onset='42D110',
 emission='50AA20 → 397570 → 3975D0',projectile='343280 → 347700',relation='52CC60 → 3D1B30',grant='3C7FD0',
 insert='50D060',qualify='5057D0',update='50ACD0',hp='506EC0'),
 stubs=sorted(stubs|{'Notification impacts are explicit arrivals, not geometric projectile collisions.',
 'HP packet calculation temporarily omits the optional physical owner; native effect modifiers and rounding still execute.'}),
 limitations=['Scene collision, exact boundary distances, faction construction and other status sources are untraced.',
 'HP packets are computed, not finally applied to current HP; caps, overheal, final resource write and full combat are not simulated.',
 'Full equipment rebuild/removal, animation interruption, DLL rewrites, death, reload and multiplayer remain untraced.'],gameplayVerified=False)
a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print('PASS counts',{k:len(v) for k,v in checks.items()},sum(map(len,checks.values())),flush=True)
