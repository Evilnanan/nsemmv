"""Trace Revenant ultimate ally attack buff through original event, reception and attack consumers.

Actor identities, event scheduling and successful hit arrivals are explicit fixtures.
This is isolated native execution, not a running multiplayer scene.
"""
import argparse,itertools,json,math,struct
from pathlib import Path
from native_effect_runtime import BASE,OBJ,STOP,Chain,Inputs,sha
from native_ailment_runtime import Ailment
from unicorn.x86_const import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','animations','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted);inputs=x;ts=x.x['tables']
raws={name:a.extracted.with_suffix('.'+name+'.param').read_bytes() for name in ('AttachEffectParam','AtkParam_Pc','BehaviorParam_PC','Bullet')}
hashes={'AttachEffectParam':'ae8128ed510a532d0fa7cb56fa9c86e4a44c9d815dd4ee01c05821d5f50a9827','AtkParam_Pc':'1ec1893420053cbfb06e3efb269ade4ba9d6a617d1d3dbb370e837847be05676','BehaviorParam_PC':'f8fa3fd27cb98d45a3e24c69d71d8751df9202e6e379dc34fd77d4ef2e1240bb','Bullet':'ddce4888040a061cf982a237e8f6e3ddce5f2162a238865a072f75d27b5e9d44'}
for name,raw in raws.items():assert sha(raw)==hashes[name]
assert sha(x.param)=='07ec636c5565d4551efeb53e6f08bc633b2aa4f2129f13c61b0638d69b1bc176'
rows=Inputs.table(raws['AttachEffectParam'],0x44);attacks=Inputs.table(raws['AtkParam_Pc'],0x1d0)
behaviors=Inputs.table(raws['BehaviorParam_PC'],0x20);bullets=Inputs.table(raws['Bullet'],0x15c)
for name,table in (('AttachEffectParam',rows),('AtkParam_Pc',attacks),('BehaviorParam_PC',behaviors),('Bullet',bullets)):
 assert len(table)==struct.unpack_from('<H',raws[name],10)[0]



att=ts['AttachEffectParam']['7031200'];root=x.spells['7031200'];marker=x.spells['7031201'];leaf=x.spells['7031202']
assert [att['passiveSpEffectId_'+str(i)] for i in (1,2,3)]==[7031200,-1,-1] and att['exclusivityId']==-1
assert {k for k,v in att.items() if k.startswith('allow') and v}=={'allowRevenant'}
assert (root['stateInfo'],root['spCategory'],root['effectEndurance'])==(2020,20,-1)
assert (marker['stateInfo'],marker['spCategory'],marker['effectEndurance'],marker['motionInterval'],marker['invocationConditionsStateChange1'],marker['behaviorId'])==(275,20,0,1.5,2020,600000280)
assert (leaf['stateInfo'],leaf['spCategory'],leaf['effectEndurance'],leaf['motionInterval'])==(0,20,30,0)
assert all(leaf[k+'AttackRate']==1.25 for k in ('physics','magic','fire','thunder','dark'))
assert [leaf[k] for k in ('effectTargetOpposeTarget','effectTargetFriendlyTarget','effectTargetSelfTarget')]==[0,1,0]
assert x.rows[7031202][0x16c]&7==2
# The original same-relation method chooses flag[2] for the same actor, flag[1] otherwise.
assert x.pe.get_data(0x52c910,15).hex()=='4584c074050fb64202c30fb64201c3'
b=ts['BehaviorParam_PC']['600000280'];bullet=ts['Bullet']['30905100'];ar=ts['AtkParam_Pc']['790000006']
assert (b['refType'],b['refId'])==(1,30905100)
assert (bullet['atkId_Bullet'],bullet['hitRadius'],bullet['hitRadiusMax'],bullet['numShoot'],bullet['HitBulletID'],bullet['isEndlessHit'])==(790000006,30,30,1,-1,0)
assert [bullet['spEffectId'+str(i)] for i in range(5)]==[7031202,0,0,0,0] and bullet['spEffectIDForShooter']==0
assert math.isclose(bullet['life'],.2,abs_tol=1e-7)
assert [ar[k] for k in ('selfTarget','friendlyTarget','opposeTarget','disableHitSpEffect')]==[0,1,0,0]
tags={int(id):sorted({r['subCategory'+str(n)] for n in range(1,6)}-{0}) for id,r in ts['AtkParam_Pc'].items()}
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
from native_animation_runtime import NativeTae
class Event(Onset):
 def hook(self,u,address,size,user):
  if address-BASE==0x3ced90:
   u.reg_write(UC_X86_REG_RAX,OBJ+0xd800);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  else:super().hook(u,address,size,user)
 def event(self,payload):
  self.q(OBJ+0xd018,OBJ+0x6000);self.q(OBJ+0xd108,OBJ+0xd200)
  self.u.mem_write(OBJ+0xd100,struct.pack('<I',67));self.u.mem_write(OBJ+0xd118,b'\1');self.u.mem_write(OBJ+0xd200,payload)
  self.invoke(0x410ca0,[OBJ+0xd000,OBJ+0xd100])
def actor():
 c=Attack();c.u.mem_write(OBJ+0x6074,b'\1');c.q(OBJ+0x65000,OBJ+0x6200);c.q(OBJ+0x65190,OBJ+0x66000);c.q(OBJ+0x66010,OBJ+0x65000);c.u.mem_write(OBJ+0x65074,b'\2');return c
def notify(c,second=False):
 global SOURCE
 old=SOURCE
 try:
  if second:SOURCE=OBJ+0x65000
  c.hit(7031202,attack=790000006)
 finally:SOURCE=old
checks={k:[] for k in ('selection','trigger','recipients','lifetime','refresh','filters','kinds','extension','disabled','mixed','projectile','filter','connected')};stubs=set()
def record(key,c,**row):checks[key].append(row);stubs.update(c.stubs)
def step(c,fps=60):c.qualify();c.update(1/fps)
def active(c):return any(n['id']==7031202 and not n['flags']&0x800c0003 for n in c.nodes())
for copies,hero in itertools.product((1,2,3),range(11)):
 c=Selection([[7031200]]*copies,hero);chosen=c.select();assert all((i*6 in chosen)==(hero in (0,6)) for i in range(copies))
 c.invoke(0xe6e150,[OBJ+0x9200,7031200]);roots=[c.invoke(0xe6e3b0,[OBJ+0x9200,n])&0xffffffff for n in range(3)]
 assert roots==[7031200,0xffffffff,0xffffffff];record('selection',c,copies=copies,hero=hero,selected=chosen,roots=roots)
anim=json.loads(a.animations.read_text());ta=next(t for b in anim['bundles'] for t in b['taes'] if t['ID']==2905)
assert anim['bundles'][0]['sha256']=='806e6b218d747277ab45e14f45ca80b9ecf8c13ada22f89db2d3ef23caa62b2a'
c=Event(1);loader=NativeTae(c,Path(str(a.animations)+'.2905.tae').read_bytes(),ta['sha256']);ctx=OBJ+0xd100;c.u.mem_write(ctx,bytes(0x40));events=[]
while c.invoke(0x27d0400,[loader.animations[650000],ctx]):
 if struct.unpack('<I',c.u.mem_read(ctx,4))[0]!=67:continue
 ptr=struct.unpack('<Q',c.u.mem_read(ctx+8,8))[0];id=struct.unpack('<i',c.u.mem_read(ptr,4))[0]
 if id!=7031201:continue
 payload=bytes(c.u.mem_read(ptr,16));tp=struct.unpack('<Q',c.u.mem_read(ctx+0x20,8))[0];start,end=struct.unpack('<f4xf',c.u.mem_read(tp,12));events.append(dict(id=id,payload=payload.hex(),start=start,end=end))
assert len(events)==1;event=events[0];assert math.isclose(event['start'],1.4,abs_tol=1e-6) and event['end']==1.5
stubs.update(c.stubs)
for copies,mode,fps in itertools.product((0,1,3),('once','window'),(30,60,120)):
 c=Event(1)
 for _ in range(copies):c.grant(7031200)
 sent=False;calls=[]
 for frame in range(2*fps):
  c.frame=frame;t=frame/fps
  if event['start']<=t<event['end'] and (mode=='window' or not sent):c.event(bytes.fromhex(event['payload']));sent=True;calls.append(frame)
  step(c,fps);c.invoke(0x50aa20,[OBJ])
 assert [s['frame'] for s in c.shots]==([round(1.4*fps)] if copies else [])
 assert all(s['behavior']==600000280 for s in c.shots)
 assert [n['id'] for n in c.nodes()]==([7031200] if copies else [])
 record('trigger',c,copies=copies,mode=mode,fps=fps,eventFrames=calls,shots=c.shots,nodes=c.nodes())
print('PASS selection/trigger',flush=True)
for (source,same),copies in itertools.product([(i,False) for i in range(10)]+[(1,True)],(1,3)):
 c=actor();c.same=same;c.u.mem_write(SOURCE+0x74,bytes([source]))
 for _ in range(copies):notify(c)
 for _ in range(3):step(c)
 values=c.row(2);accepted=source in (1,2,4) and not same
 assert values==[1.25 if accepted else 1]*5 and len(c.nodes())==int(accepted)
 record('recipients',c,source=source,recipient=1,sameActor=same,copies=copies,values=values,nodes=c.nodes())
for fps,copies in itertools.product((30,60,120),(1,3)):
 c=actor();changes=[];last=None
 for _ in range(copies):notify(c)
 for frame in range(32*fps):
  step(c,fps);now=active(c)
  if now!=last:changes.append(dict(frame=frame,active=now,values=c.row(2)));last=now
 assert [r['active'] for r in changes]==[True,False] and changes[0]['frame']==0
 assert abs(changes[-1]['frame']-30*fps)<=3
 assert [r['values'] for r in changes]==[[1.25]*5,[1]*5]
 record('lifetime',c,fps=fps,copies=copies,changes=changes)
for times,second in itertools.product(((0,),(0,1),(0,6),(0,60),(0,300)),(False,True)):
 c=actor();changes=[];last=None
 for frame in range(37*60):
  for n,at in enumerate(times):
   if frame==at:notify(c,second and n>0)
  step(c);now=active(c);assert len(c.nodes())<=1
  if now!=last:changes.append(dict(frame=frame,active=now,values=c.row(2)));last=now
 assert [r['active'] for r in changes]==[True,False] and abs(changes[-1]['frame']-max(times)-1800)<=3
 assert [r['values'] for r in changes]==[[1.25]*5,[1]*5]
 record('refresh',c,arrivals=times,secondCaster=second,changes=changes)
print('PASS recipients/lifetime/refresh',flush=True)
representatives={}
for id,v in tags.items():representatives.setdefault(tuple(v),id)
assert len(representatives)==216
for copies in (0,1,3):
 c=actor()
 for _ in range(copies):notify(c)
 step(c)
 for attack in representatives.values():
  values=c.row(attack);assert values==[1.25 if copies else 1]*5
  record('filters',c,copies=copies,attack=attack,tags=tags[attack],values=values)
 for kind in range(13):
  values=c.row(2,kind);assert values==[1.25 if copies and kind!=5 else 1]*5
  record('kinds',c,copies=copies,kind=kind,values=values)
for extra in (None,7006400,8330500):
 c=actor()
 if extra:c.grant(extra)
 notify(c);c.qualify();c.update(0);c.qualify();c.update(1)
 node=next(n for n in c.nodes() if n['id']==7031202);values=c.row(2)
 assert node['lifetime']==29 and values==[1.25]*5
 record('extension',c,extra=extra,node=node,values=values)
for mask in (1,2,0x40000,0x80000000):
 c=actor();notify(c);c.qualify();c.update(0);assert c.row(2)==[1.25]*5
 ptr=struct.unpack('<Q',c.u.mem_read(OBJ+8,8))[0];flags=struct.unpack('<I',c.u.mem_read(ptr+0x68,4))[0];c.u.mem_write(ptr+0x68,struct.pack('<I',flags|mask))
 values=c.row(2);assert values==[1]*5;record('disabled',c,mask=mask,values=values)
for counts in itertools.product((0,1,3),repeat=3):
 c=actor()
 for root,count in zip((7600000,7600010),counts[1:]):
  for _ in range(count):c.grant(root)
 c.qualify();c.update(0);c.u.mem_write(SOURCE+0x74,b'\6');c.hit(1101,attack=2);c.u.mem_write(SOURCE+0x74,b'\1')
 for _ in range(counts[0]):notify(c)
 for _ in range(6):step(c)
 values=c.row(2);expected=math.prod(v for v,n in zip((1.25,1.12,1.22),counts) if n)
 assert all(math.isclose(v,expected,rel_tol=2e-6) for v in values)
 record('mixed',c,counts=counts,values=values,nodes=c.nodes())
print('PASS filters/kinds/extension/disabled/mixed',flush=True)
for fps in (30,60,120):
 c=Projectile(30905100);slot=OBJ+0x4000
 c.u.mem_write(slot+0x329,b'\1');c.u.mem_write(slot+0x334,struct.pack('<I',30905100));c.u.mem_write(slot+0x494,b'\1')
 for frame in range(fps):c.frame=frame;c.invoke(0x343280,[slot],{UC_X86_REG_XMM1:1/fps})
 assert c.shots==[0];record('projectile',c,fps=fps,shots=c.shots)
for attack in (2,790000006,900902000):
 c=Filter(attack);p=OBJ+0xa000;c.q(p+8,OBJ+0xa800);c.q(p+0x30,0x10000001)
 for off in (0x28,0x1ec):c.u.mem_write(p+off,struct.pack('<i',-1))
 c.u.mem_write(p+0x78,struct.pack('<ii',attack,1));c.invoke(0x535a60,[p],{UC_X86_REG_XMM1:1/60})
 value=struct.unpack('<I',c.u.mem_read(p+0x28,4))[0];selfTarget=ts['AtkParam_Pc'][str(attack)]['selfTarget'];assert value>>26==(0 if selfTarget else 1)
 record('filter',c,attack=attack,selfTarget=selfTarget,value=value)
for copies,same in itertools.product((0,1,3),(False,True)):
 source=Event(1);target=actor();target.same=same;changes=[];last=None
 for _ in range(copies):source.grant(7031200)
 for frame in range(34*60):
  if frame<120:
   source.frame=frame
   if frame==84:source.event(bytes.fromhex(event['payload']))
   before=len(source.shots);step(source);source.invoke(0x50aa20,[OBJ])
   for shot in source.shots[before:]:notify(target)
  step(target);now=active(target)
  if now!=last:changes.append(dict(frame=frame,active=now,values=target.row(2)));last=now
 if copies and not same:
  assert [r['active'] for r in changes]==[False,True,False] and changes[1]['frame']==84 and abs(changes[2]['frame']-1884)<=3
  assert changes[1]['values']==[1.25]*5
 else:assert changes==[dict(frame=0,active=False,values=[1]*5)]
 record('connected',source,copies=copies,sameActor=same,shots=source.shots,changes=changes);stubs.update(target.stubs)
print('PASS counts',{k:len(v) for k,v in checks.items()},sum(map(len,checks.values())),flush=True)
out=dict(schema=1,effect=7031200,root=7031200,emitter=7031201,leaf=7031202,radius=30,duration=30,multiplier=1.25,
 exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),paramHashes=hashes,
 animationBundleSha256=anim['bundles'][0]['sha256'],taeSha256=ta['sha256'],event=event,checks=checks,
 native=dict(selection='4FEA30 → E6E150 → E6E3B0',animation='27D0F10 → 27D0400 → 410CA0',emission='50AA20 → 397570 → 3975D0',
 projectile='343280 → 347700',hit='43BE60 → 3C80A0 → 3DB410',relation='52CC60 → 3D1B30 → 52C910',
 filter='535A60..535BF9 → E6D630 / 536870',insert='50D060',qualify='5057D0',update='50ACD0',attack='E6D530 → 502830'),
 stubs=sorted(stubs|{'Event active inputs are supplied at actual TAE timestamps; no complete Havok/action scheduler.',
 'Two explicit source actors of relation classes 1 and 2; recipient class 1. Numeric relation classes are not assigned gameplay names.',
 'Impact arrivals are fixtures, not projectile candidate selection or scene collision.',
 'Connected timeline delivers one impact on each original state-275 emission; Behavior-to-Bullet link is read from pinned parameters, no spatial/network latency.',
 '535A60..535BF9 executes original filter construction with actual attack rows and explicit owner handle; the collision consumer is not executed.'}),
 limitations=['No complete spatial candidate search/collision, distance-boundary tests, family actor construction or final scene damage.',
 'Attack kind 5 bypasses this multiplier; its gameplay meaning is not established and is not named in the UI.',
 'Only listed modifier/effect combinations tested. Full action interruptions, DLL rewrites, equipment rebuild, death, reload and multiplayer are not simulated.'],gameplayVerified=False)
a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
