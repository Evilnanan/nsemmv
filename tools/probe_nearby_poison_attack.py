"""Trace nearby poison/rot attack bonus through native onset, notifications and consumers.

Actors, impact arrivals and allocator/lookup contexts are explicit fixtures.
Original equipment selection, hit delivery, status onset, effect timers and
attack consumers execute; this is not a running scene or gameplay recording.
"""
import argparse,itertools,json,math,struct
from pathlib import Path
from native_effect_runtime import BASE,OBJ,STOP,Chain,Inputs,sha
from native_ailment_runtime import Ailment
from unicorn.x86_const import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','assets','reinforce','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted);inputs=x;ts=x.x['tables']
raws={name:a.extracted.with_suffix('.'+name+'.param').read_bytes() for name in ('AttachEffectParam','AtkParam_Pc','BehaviorParam_PC','Bullet')}
hashes={'AttachEffectParam':'ae8128ed510a532d0fa7cb56fa9c86e4a44c9d815dd4ee01c05821d5f50a9827','AtkParam_Pc':'1ec1893420053cbfb06e3efb269ade4ba9d6a617d1d3dbb370e837847be05676','BehaviorParam_PC':'f8fa3fd27cb98d45a3e24c69d71d8751df9202e6e379dc34fd77d4ef2e1240bb','Bullet':'ddce4888040a061cf982a237e8f6e3ddce5f2162a238865a072f75d27b5e9d44'}
for name,raw in raws.items():assert sha(raw)==hashes[name]
assert sha(x.param)=='07ec636c5565d4551efeb53e6f08bc633b2aa4f2129f13c61b0638d69b1bc176'
rows=Inputs.table(raws['AttachEffectParam'],0x44);attacks=Inputs.table(raws['AtkParam_Pc'],0x1d0)
behaviors=Inputs.table(raws['BehaviorParam_PC'],0x20);bullets=Inputs.table(raws['Bullet'],0x15c)
for name,table in (('AttachEffectParam',rows),('AtkParam_Pc',attacks),('BehaviorParam_PC',behaviors),('Bullet',bullets)):
 assert len(table)==struct.unpack_from('<H',raws[name],10)[0]
families=[dict(effect=7260800,root=7260802,leaf=7260803,marker=506,state=380,rate=1.12,ailment='poison-or-rot')]
ROOTS=(7260802,);LEAVES=(7260803,);MARKERS=(506,1121)
att=ts['AttachEffectParam']['7260800'];r=x.spells['7260802'];leaf=x.spells['7260803']
assert [att['passiveSpEffectId_'+str(n)] for n in (1,2,3)]==[7260802,-1,-1] and att['exclusivityId']==-1
assert all(v==1 for k,v in att.items() if k.startswith('allow'))
assert (r['spCategory'],r['stateInfo'],r['effectEndurance'],r['motionInterval'],r['cycleOccurrenceSpEffectId'])==(20,0,-1,0,7260803)
assert [r['invocationConditionsStateChange'+str(i)] for i in (1,2,3)]==[380,2064,0]
assert (leaf['spCategory'],leaf['effectEndurance'])==(20,20)
assert all(math.isclose(leaf[k+'AttackRate'],1.12,rel_tol=1e-6) for k in ('physics','magic','fire','thunder','dark'))
assert x.spells['505']==x.spells['7260800'] and x.spells['506']==x.spells['7260801']
assert x.rows[505]==x.rows[7260800] and x.rows[506]==x.rows[7260801]
notifications=[]
for emission,behavior,bid,marker,state in ((505,2105,1005,506,380),(1120,2108,1025,1121,2064)):
 r=x.spells[str(emission)];b=ts['BehaviorParam_PC'][str(behavior)];bullet=ts['Bullet'][str(bid)]
 assert (r['stateInfo'],r['behaviorId'],r['effectEndurance'],r['motionInterval'])==(275,behavior,900,999)
 assert (b['refType'],b['refId'])==(1,bid) and x.spells[str(marker)]['stateInfo']==state
 assert (bullet['atkId_Bullet'],bullet['spEffectId0'],bullet['life'],bullet['hitRadius'],bullet['hitRadiusMax'],bullet['numShoot'],bullet['HitBulletID'],bullet['isEndlessHit'])==(2,marker,.5,7,7,1,-1,0)
 notifications.append(dict(emission=emission,behavior=behavior,bullet=bid,marker=marker,state=state,radius=7))
assert [ts['AtkParam_Pc']['2'][k] for k in ('selfTarget','friendlyTarget','opposeTarget','disableHitSpEffect')]==[1,0,1,0]
tags={int(id):sorted({r['subCategory'+str(n)] for n in range(1,6)}-{0}) for id,r in ts['AtkParam_Pc'].items()}
representatives={}
for id,values in tags.items():
 assert values==sorted(set(attacks[id][off] for off in (0x4e,0x4f,0x1c8,0x1c9,0x1ca))-{0});representatives.setdefault(tuple(values),id)
assert len(representatives)==216
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
class Attack(Hit):
 def hook(self,u,address,size,user):
  if address-BASE==0xe6d630:
   id=u.reg_read(UC_X86_REG_R8)&0xffffffff;assert u.reg_read(UC_X86_REG_RDX)==1
   wrapper=u.reg_read(UC_X86_REG_RCX);u.mem_write(OBJ+0xa800,attacks[id]);u.mem_write(wrapper,struct.pack('<iii4xQ',id,0,1,OBJ+0xa800))
   sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8);return
  super().hook(u,address,size,user)
 def row(self,id,kind=0):
  self.u.mem_write(OBJ+0x800,bytes(0x300));self.u.mem_write(OBJ+0xa800,attacks[id]);self.q(OBJ+0xb010,OBJ+0xa800)
  self.invoke(0xe6d530,[OBJ+0xb000,OBJ+0x814]);assert int.from_bytes(self.u.mem_read(OBJ+0x814,32),'little')==sum(1<<tag for tag in tags[id]);self.u.mem_write(OBJ+0x808,struct.pack('<iiB',id,1,kind));self.invoke(0x502830,[OBJ,OBJ+0x800,-1,-1])
  return [struct.unpack('<f',self.u.mem_read(OBJ+0x800+off,4))[0] for off in (0x90,0xa4,0xa8,0xac,0xb0)]
checks={k:[] for k in ('selection','recipients','mixed','filters','kinds','lifetime','refresh','onset','projectile','disabled','extension','variants','reinfection','dualMarker','mixedOther','weaponAssembly')};stubs=set()
def record(key,c,**row):checks[key].append(row);stubs.update(c.stubs)
def step(c,fps=60):c.qualify();c.update(1/fps)
def active(c):return sorted(n['id'] for n in c.nodes() if n['id'] in LEAVES and not n['flags']&0x800c0003)
def equip(counts=(3,),sourceType=6,same=False):
 c=Attack();c.same=same;c.u.mem_write(SOURCE+0x74,bytes([sourceType]));c.u.mem_write(OBJ+0x6074,b'\1')
 for root,count in zip(ROOTS,counts):
  for _ in range(count):c.grant(root)
 step(c);return c
def notify(c,markers=MARKERS):
 for marker in markers:c.hit(marker)
 for _ in range(6):step(c)
def expected(c,kind=0):return 1 if kind==5 else math.prod(f['rate'] for f in families if f['leaf'] in active(c))
def verify(c,id=2,kind=0):
 values=c.row(id,kind);assert all(math.isclose(v,expected(c,kind),rel_tol=2e-6) for v in values),(id,kind,active(c),values,expected(c,kind))
 return values
for f,copies,hero in itertools.product(families,(1,2,3,6),range(11)):
 c=Selection([[f['effect']]]*copies,hero);bits=c.select();assert all(i*6 in bits for i in range(copies))
 c.invoke(0xe6e150,[OBJ+0x9200,f['effect']]);roots=[c.invoke(0xe6e3b0,[OBJ+0x9200,n])&0xffffffff for n in range(3)];assert roots==[f['root'],0xffffffff,0xffffffff]
 record('selection',c,effect=f['effect'],copies=copies,hero=hero,bits=bits,roots=roots)
print('PASS selection',len(checks['selection']),flush=True)
for copies,marker,(kind,same) in itertools.product((0,1,3),(*MARKERS,7260801),[(i,False) for i in range(10)]+[(1,True)]):
 c=equip((copies,),kind,same);c.hit(marker);present=any(n['id']==marker for n in c.nodes())
 for _ in range(6):step(c)
 eligible=same or kind in (6,7,8,9)
 assert present==eligible and active(c)==(list(LEAVES) if copies and eligible else [])
 record('recipients',c,copies=copies,marker=marker,sourceType=kind,same=same,markerPresent=present,leaves=active(c),values=verify(c))
for counts in itertools.product((0,1,3),repeat=1):
 c=equip(counts);notify(c);assert active(c)==[f['leaf'] for f,n in zip(families,counts) if n]
 assert all(sum(v['id']==root for v in c.nodes())==int(bool(n)) for root,n in zip(ROOTS,counts))
 record('mixed',c,counts=counts,leaves=active(c),values=verify(c))
sets=[(0,),(1,),(3,)]
for counts in sets:
 c=equip(counts);notify(c)
 for id in representatives.values():record('filters',c,counts=counts,attack=id,tags=tags[id],values=verify(c,id))
 for kind in range(13):record('kinds',c,counts=counts,kind=kind,values=verify(c,2,kind))
print('PASS recipients/mixed/filters/kinds',len(checks['recipients']),len(checks['mixed']),len(checks['filters']),len(checks['kinds']),flush=True)
for copies,fps in itertools.product((1,3),(30,60,120)):
 c=equip((copies,));c.hit(506);c.hit(1121);changes=[];previous=None
 for frame in range(21*fps):
  step(c,fps);now=active(c);assert now in ([],list(LEAVES))
  if now!=previous:changes.append(dict(frame=frame,leaves=now,values=verify(c)));previous=now
 assert [bool(v['leaves']) for v in changes]==[False,True,False]
 assert abs(changes[-1]['frame']-changes[1]['frame']-20*fps)<=4
 record('lifetime',c,copies=copies,fps=fps,changes=changes);print('PASS lifetime',copies,fps,flush=True)
for marker,times in itertools.product(MARKERS,((0,),(0,1),(0,6),(0,60),(0,300))):
 c=equip();grants=[];changes=[];previous=None
 for frame in range(26*60):
  before=len(c.grants)
  if frame in times:c.hit(marker)
  step(c);grants.extend([dict(frame=frame,id=id) for id in c.grants[before:] if id in LEAVES]);now=active(c)
  assert len(now) in (0,1)
  if now!=previous:changes.append(dict(frame=frame,leaves=now,values=verify(c)));previous=now
 assert [bool(v['leaves']) for v in changes]==[False,True,False] and len(grants)==len(times)
 assert abs(changes[-1]['frame']-grants[-1]['frame']-1200)<=4
 record('refresh',c,marker=marker,hits=times,grants=grants,changes=changes);print('PASS refresh',marker,times,flush=True)
for kind,id,resistance,immune,fps in itertools.product((0,1),(20005,21005),(1,59,60,61),(False,True),(30,60,120)):
 if (kind==0)!=(id==20005):continue
 c=Onset(resistance);c.kind=kind;c.q(OBJ+0x63f8,STOP+0x302)
 c.stubs.add('actor virtual +1F8 returns no auxiliary animation component; original 27AEC0 executes')
 if immune:c.grant(9642)
 c.qualify();c.update(0);c.hit(id,2,scale=1)
 for frame in range(2*fps):c.frame=frame;step(c,fps);c.invoke(0x50aa20,[OBJ])
 notices=[v for v in c.shots if v['behavior']==(2105 if kind==0 else 2108)];triggered=not immune and resistance<=60
 assert len(notices)==int(triggered)
 if triggered:assert abs(notices[0]['frame']-1)<=3
 record('onset',c,kind=kind,effect=id,resistance=resistance,immune=immune,fps=fps,shots=c.shots,nodes=c.nodes())
print('PASS onset',len(checks['onset']),flush=True)
for notification,fps in itertools.product(notifications,(30,60,120)):
 bid=notification['bullet'];c=Projectile(bid);slot=OBJ+0x4000
 c.u.mem_write(slot+0x329,b'\1');c.u.mem_write(slot+0x334,struct.pack('<I',bid));c.u.mem_write(slot+0x494,b'\1')
 for frame in range(fps):c.frame=frame;c.invoke(0x343280,[slot],{UC_X86_REG_XMM1:1/fps})
 assert c.shots==[0];record('projectile',c,bullet=bid,fps=fps,shots=c.shots)
for leaf,mask in itertools.product(LEAVES,(1,2,0x40000,0x80000000)):
 c=Attack();c.insert(leaf);c.qualify();c.update(0);ptr=struct.unpack('<Q',c.u.mem_read(OBJ+8,8))[0];c.u.mem_write(ptr+0x68,struct.pack('<I',mask))
 assert not active(c);record('disabled',c,leaf=leaf,mask=mask,values=verify(c))
for leaf,extra in itertools.product(LEAVES,(None,7006400,8330500)):
 c=Attack()
 if extra is not None:c.grant(extra)
 c.grant(leaf);c.qualify();c.update(0);c.qualify();c.update(1)
 node=next(n for n in c.nodes() if n['id']==leaf);assert math.isclose(node['lifetime'],19,abs_tol=.001)
 record('extension',c,leaf=leaf,otherEffect=extra,node=node,values=verify(c))
variants=[(20005,'hit',0,2105),(21005,'hit',1,2108),(6820002,'self',0,2105),(6820102,'self',1,2108),
 (6851301,'self',0,2105),(6851401,'self',1,2108),(7170103,'hit',1,2108),(107004,'hit',1,2105)]
for (id,mode,kind,behavior),fps in itertools.product(variants,(30,60,120)):
 c=Onset(1);c.kind=kind;c.q(OBJ+0x63f8,STOP+0x302);c.qualify();c.update(0)
 if mode=='hit':c.hit(id,2,scale=1)
 else:c.grant(id)
 for frame in range(3*fps):c.frame=frame;step(c,fps);c.invoke(0x50aa20,[OBJ])
 notices=[v['frame'] for v in c.shots if v['behavior']==behavior];assert notices==[1],(id,mode,notices)
 record('variants',c,effect=id,delivery=mode,kind=kind,fps=fps,shots=c.shots,nodes=c.nodes())
for source,kind,behavior,emitter in ((20005,0,2105,505),(21005,1,2108,1120)):
 for fps in (30,60,120):
  c=Onset(1);c.kind=kind;c.q(OBJ+0x63f8,STOP+0x302);c.qualify();c.update(0);samples=[]
  for frame in range(48*fps):
   if frame in (0,45*fps):c.hit(source,2,scale=1)
   c.frame=frame;step(c,fps);c.invoke(0x50aa20,[OBJ])
   if frame in (0,1,41*fps,45*fps+1):samples.append(dict(frame=frame,nodes=c.nodes()))
  assert [v['frame'] for v in c.shots if v['behavior']==behavior]==[1,45*fps+1]
  assert all(n['id']!=emitter for sample in samples if sample['frame']==41*fps for n in sample['nodes'])
  record('reinfection',c,effect=source,fps=fps,shots=c.shots,samples=samples)
for markers in ((506,1121),(1121,506),(506,506),(1121,1121),(506,1121,7260801)):
 c=equip();notify(c,markers);assert active(c)==list(LEAVES)
 record('dualMarker',c,markers=markers,leaves=active(c),values=verify(c))
for counts in itertools.product((0,1,3),repeat=3):
 c=equip((counts[0],))
 for root,n in zip((7600000,7600010),counts[1:]):
  for _ in range(n):c.grant(root)
 step(c);notify(c,(506,1121,1101));values=c.row(2)
 expectedRate=math.prod(v for v,n in zip((1.12,1.12,1.22),counts) if n)
 assert all(math.isclose(v,expectedRate,rel_tol=2e-6) for v in values)
 record('mixedOther',c,counts=counts,values=values,nodes=c.nodes())
print('PASS variants/reinfection/dual/mixed',*[len(checks[k]) for k in ('variants','reinfection','dualMarker','mixedOther')],flush=True)
weaponRaw=a.assets.with_suffix('.EquipParamWeapon.param').read_bytes();reinforceRaw=a.reinforce.with_suffix('.ReinforceParamWeapon.param').read_bytes()
assert sha(weaponRaw)=='28adf74850c88ca0b4bb01f355c4f1f8e1b662a56d77894ae74d591b72c1a0ea'
assert sha(reinforceRaw)=='3d21d0bb1803fbe9df43b083414e365bdd62fa9d13e71c5282898136caae48fd'
weapons=json.loads(a.assets.read_text())['tables']['EquipParamWeapon'];reinforce=json.loads(a.reinforce.read_text())['tables']['ReinforceParamWeapon']
for path in (a.assets,a.reinforce):assert json.loads(path.read_text())['hashes']['regulation.bin']==x.x['hashes']['regulation.bin']
for raw,size,table in ((weaponRaw,0x2a8,weapons),(reinforceRaw,0x84,reinforce)):
 assert len(Inputs.table(raw,size))==struct.unpack_from('<H',raw,10)[0]==len(table)
class Lookup(Chain):
 def __init__(self):
  super().__init__(x);self.tables={}
  self.mapped(self.u,0,BASE+0x3c28880,8,0,None);self.q(BASE+0x3c28880,OBJ+0x7000)
  for kind,path in [(0,a.assets.with_suffix('.EquipParamWeapon.param')),(4,a.reinforce.with_suffix('.ReinforceParamWeapon.param'))]:
   raw=Path(path).read_bytes();count=struct.unpack_from('<H',raw,10)[0];off=(len(raw)+15)&~15
   start=0x40000000+kind*0x1000000;self.u.mem_map(start,(off+count*8+0x3000)&~4095);base=start+0x1000
   self.u.mem_write(base,raw);self.u.mem_write(base-16,struct.pack('<ii',off,count))
   index=sorted((struct.unpack_from('<i',raw,0x40+i*24)[0],i) for i in range(count))
   self.u.mem_write(base+off,b''.join(struct.pack('<ii',*v) for v in index))
   self.tables[kind]=start;self.q(start+0x80,start+0x100);self.q(start+0x180,base)
 def hook(self,u,address,size,user):
  if address==BASE+0xe9e680:
   kind=u.reg_read(UC_X86_REG_RDX);assert kind in self.tables
   u.reg_write(UC_X86_REG_RAX,self.tables[kind]);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  else:super().hook(u,address,size,user)
class Assembly(Lookup):
 def hook(self,u,address,size,user):
  if address==BASE+0x6a307e:u.reg_write(UC_X86_REG_RIP,STOP)
  else:super().hook(u,address,size,user)
 def effects(self,weapon):
  self.u.mem_write(OBJ+0x9000,b'\0'*48);self.invoke(0xea7fc0,[OBJ+0x9000,weapon]);w=bytes(self.u.mem_read(OBJ+0x9000,48));wp=struct.unpack_from('<Q',w,8)[0];rp=struct.unpack_from('<Q',w,32)[0];rid=struct.unpack_from('<i',w,24)[0]
  bp=OBJ+0xa100;out=OBJ+0xb000;self.u.mem_write(out,b'\0'*0x200);self.q(bp-17,wp);self.q(bp+7,rp)
  for reg,value in [(UC_X86_REG_RAX,rp),(UC_X86_REG_RBP,bp),(UC_X86_REG_RDI,out)]:self.u.reg_write(reg,value)
  self.invoke(0x6a2fe0,[wp]);count=self.u.mem_read(out+0xf1,1)[0];effects=list(struct.unpack('<'+'i'*count,self.u.mem_read(out+0xa8,count*4)))
  return dict(weapon=weapon,reinforceId=rid,reinforcePresent=bool(rp),effects=effects)
c=Assembly()
weaponIds=sorted(int(id) for id,w in weapons.items() if any(107000<=w['spEffectBehaviorId'+str(i)]<=107275 for i in range(3)))
assert len(weaponIds)==34
for base,level in itertools.product(weaponIds,range(6)):
 row=c.effects(base+level);rp=reinforce.get(str(row['reinforceId']));w=weapons[str(base)]
 assert row['reinforceId']==w['reinforceTypeId']+level and row['reinforcePresent']==bool(rp)
 expectedIds=[w['spEffectBehaviorId'+str(i)]+(rp['spEffectId'+str(i+1)] if rp else 0) for i in range(3)];expectedIds=[v for v in expectedIds if v>=0]
 assert row['effects']==expectedIds
 row['rotEffects']=[dict(id=e,cycle=x.spells[str(e)]['cycleOccurrenceSpEffectId']) for e in row['effects'] if str(e) in x.spells and x.spells[str(e)]['stateInfo']==5]
 assert row['rotEffects'] and all(e['cycle']==1120 for e in row['rotEffects'])
 record('weaponAssembly',c,**row)
print('PASS weaponAssembly',len(checks['weaponAssembly']),flush=True)
out=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),paramHashes=hashes,
 weaponSha256=sha(weaponRaw),reinforceSha256=sha(reinforceRaw),families=families,notifications=notifications,duration=20,tagSets=len(representatives),checks=checks,
 native=dict(selection='4FEA30 → E6E150 → E6E3B0',hit='43BE60 → 3C80A0 → 3DB410',onset='42D110',
 emission='50AA20 → 397570 → 3975D0',projectile='343280 → 347700',relation='52CC60 → 3D1B30',
 grant='3C7FD0',insert='50D060',qualify='5057D0',update='50ACD0',attack='E6D530 → 502830'),
 stubs=sorted(stubs|{'Notification impacts are explicit arrivals, not geometric projectile collision or actor search.',
 'Equipment assembly 6A2FE0..6A307E has an explicit block input/output fixture; weapon and reinforcement lookup EA7FC0/EA9A60 execute with original rows and a synthetic PARAM ownership/index context.',
 'Variant delivery mode is an explicit fixture. Rejected delivery does not establish that the status never triggers in gameplay.'}),
 limitations=['Full scene collision, exact boundary distances, actual actor-faction construction and enemy/allied availability are not simulated.',
 'Only listed source variants and input contexts are traced; absence in one delivery context is not universal failure.',
 'Full equipment rebuild/removal, animation interruption, DLL rewrites, final damage, death, reload and multiplayer remain untraced.'],gameplayVerified=False)
a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print('PASS counts',{k:len(v) for k,v in checks.items()},sum(map(len,checks.values())),flush=True)
