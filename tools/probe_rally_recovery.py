"""Execute the pinned rally HP pool, attack metadata, hit reception and recovery.

Full hit reception and HP writes run natively. Attack metadata and outgoing
recovery enter named inner branches with explicit contexts; collision is absent.
"""
import argparse,itertools,json,math,struct
from pathlib import Path
from native_effect_runtime import BASE,OBJ,STACK,STOP,Inputs,sha
from native_ailment_runtime import Ailment
from unicorn.x86_const import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','assets','npc','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted)
assets=json.loads(a.assets.read_text());npc=json.loads(a.npc.read_text())
for src in (assets,npc):assert src['hashes']['regulation.bin']==x.x['hashes']['regulation.bin']
atkraw=a.extracted.with_suffix('.AtkParam_Pc.param').read_bytes()
npcraw=a.npc.with_suffix('.AtkParam_Npc.param').read_bytes()
wepraw=a.assets.with_suffix('.EquipParamWeapon.param').read_bytes()
attacks=Inputs.table(atkraw,0x1d0);npcattacks=Inputs.table(npcraw,0x1d0)
weapons=Inputs.table(wepraw,0x298)
f32=lambda value:struct.unpack('<f',struct.pack('<f',value))[0]
roots={7005600:7005600,6005600:7005601,6005601:7005602,9090200:8981200}
for effect,root in roots.items():
 assert x.x['tables']['AttachEffectParam'][str(effect)]['passiveSpEffectId_1']==root
 assert x.spells[str(root)]['stateInfo']==449 and x.spells[str(root)]['effectEndurance']==-1
assert struct.unpack('<f',x.pe.get_data(0x398c290,4))[0]==4
assert struct.unpack('<f',x.pe.get_data(0x398c294,4))[0]==1
assert math.isclose(struct.unpack('<f',x.pe.get_data(0xe707ea+9+0x1d89839,4))[0],.01,abs_tol=1e-9)
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

class Rally(Hit):
 def __init__(self,maximum=1000,current=None):
  self.stopAt=set();self.recoveries=[];self.attackType=1;super().__init__()
  self.u.mem_map(OBJ+0x80000,0x10000)
  self.q(C,OBJ+0x88200);self.q(OBJ+0x88250,STOP+0x701)
  self.u.mem_write(OBJ+0xe140,struct.pack('<ii',maximum if current is None else current,maximum))
  self.u.mem_write(OBJ+0x88530,b'\xff')
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if pc in self.stopAt:u.reg_write(UC_X86_REG_RIP,STOP)
  elif address==STOP+0x701:self.stubs.add('hit module virtual +50 notification sink');ret()
  elif pc==0x27f2470:
   assert u.reg_read(UC_X86_REG_RDX)==22
   self.stubs.add('27F2470 explicit actor component identity 22; native 4BFCF0 source/slot comparison remains live');ret(OBJ+0x88500)
  elif pc==0x4b3d40:self.stubs.add('4B3D40 deferred hit-target notification sink after HP recovery queue');ret()
  elif pc==0x3da510:self.recoveries.append(u.reg_read(UC_X86_REG_RDX)&0xffffffff)
  elif pc==0xe6d630:
   kind=u.reg_read(UC_X86_REG_RDX);id=u.reg_read(UC_X86_REG_R8)
   assert kind==self.attackType and id==self.attack
   raw=(attacks if kind==1 else npcattacks)[id]
   self.stubs.add('E6D630 actual PC/NPC AtkParam lookup')
   wrapper=u.reg_read(UC_X86_REG_RCX);u.mem_write(OBJ+0x64000,raw);u.mem_write(wrapper,struct.pack('<iii4xQ',id,0,kind,OBJ+0x64000));ret()
  else:super().hook(u,address,size,user)
 def state(self):
  values=struct.unpack('<4f',self.u.mem_read(OBJ+0xe168,16))
  return dict(hp=struct.unpack('<i',self.u.mem_read(OBJ+0xe140,4))[0],pool=values[0],protected=values[1],timer=values[2],pending=values[3])
 def build(self,attack=0,weapon=1000000,kind=1):
  self.attack=attack;self.attackType=kind
  self.u.mem_write(HIT,bytes(0x400));self.u.mem_write(HIT+0x40,struct.pack('<ii',attack,kind))
  self.u.mem_write(OBJ+0x80000,(attacks if kind==1 else npcattacks)[attack]);self.u.mem_write(OBJ+0x81000,weapons[weapon])
  self.u.reg_write(UC_X86_REG_RSI,HIT);self.stopAt={0xe70cde}
  self.invoke(0xe70c45,[OBJ+0x80000,0,OBJ+0x81000],{UC_X86_REG_XMM6:0,UC_X86_REG_XMM7:1,UC_X86_REG_XMM8:.01})
  self.stopAt=set()
  rate,time,base=struct.unpack('<3f',self.u.mem_read(HIT+0x194,12))
  return dict(rate=rate,time=time,base=base,slot=struct.unpack('<b',self.u.mem_read(HIT+0x1a0,1))[0])
 def receive(self,damage=300):
  self.u.mem_write(HIT+0x280,struct.pack('<i',damage))
  self.invoke(0x43be60,[C,SOURCE,HIT,0,0,0])
  return self.state()
 def attack_hit(self,damage=100,scaled=False,scale=1):
  self.u.mem_write(HIT+0x280,struct.pack('<i',damage));self.u.mem_write(HIT+0x2b4,bytes([scaled]))
  self.u.mem_write(HIT+0x26c,struct.pack('<f',scale));self.stopAt={0x43f3f2,0x43f281}
  for reg,value in {UC_X86_REG_R14:OBJ+0x6000,UC_X86_REG_RDI:HIT,UC_X86_REG_RSI:SOURCE,UC_X86_REG_RBP:STACK+0x9000}.items():self.u.reg_write(reg,value)
  self.invoke(0x43f37d,[]);self.stopAt=set()
  return self.state()
 def tick(self,dt):
  self.invoke(0x4289c0,[OBJ+0xe000],{UC_X86_REG_XMM1:dt});return self.state()

checks={name:[] for name in ('builders','recovery','pool','timeline','repeat','healing','controls')};stubs=set()
def record(group,c,**values):checks[group].append(values);stubs.update(c.stubs)
def equipped(ids=(7005600,),**kwargs):
 c=Rally(**kwargs)
 for id in ids:c.grant(id)
 c.qualify();c.update(0);return c
def expected_base(attack,weapon,kind=1):
 row=(x.x if kind==1 else npc)['tables']['AtkParam_Pc' if kind==1 else 'AtkParam_Npc'][str(attack)]
 value=assets['tables']['EquipParamWeapon'][str(weapon)]['wepRegainHp']
 return f32(f32(f32(row['wepRegainHpScale']*f32(.01))*value)+row['atkRegainHp'])
# Every distinct PC attack recovery coefficient pair, with three actual weapons.
groups={}
for id,row in x.x['tables']['AtkParam_Pc'].items():groups.setdefault((row['wepRegainHpScale'],row['atkRegainHp']),int(id))
for attack,weapon in itertools.product(groups.values(),(1000000,5000000,3000000)):
 c=equipped();packet=c.build(attack,weapon)
 assert packet['base']==expected_base(attack,weapon) and packet['rate']==packet['time']==1
 record('builders',c,attack=attack,weapon=weapon,packet=packet)
# Genuine grants distinguish same-row duplication, different levels and blessing.
sets=[[],[7005600],[7005601],[7005602],[7005600]*3,[7005601]*3,[7005602]*3,
 [7005600,7005601,7005602],[7005602,7005601],[7005602,8981200],[8981200]*3]
for ids,attack,damage in itertools.product(sets,(0,820,210782001,300000790),(1,10000)):
 c=equipped(ids);c.build();c.receive();packet=c.build(attack)
 rate=1
 for node in c.nodes():rate=f32(rate*x.spells[str(node['id'])]['regainRate'])
 amount=int(f32(packet['base']*rate));before=c.attack_hit(damage);after=c.tick(1/60)
 assert c.recoveries==[amount]
 assert before['pending']==(min(300,amount) if ids else 0)
 assert after['hp']==700+(min(300,amount) if ids else 0)
 record('recovery',c,ids=ids,attack=attack,damage=damage,base=packet['base'],rate=rate,amount=amount,queued=before,after=after)
# Use actual NPC rows for the zero-pool and zero-preservation-time exceptions.
for ids,attack,damage in itertools.product(([],[7005600],[7005602]*3),(0,7000000,8000015),(100,300)):
 c=equipped(ids);packet=c.build(attack,kind=0);after=c.receive(damage)
 expected=damage*packet['rate'] if ids else 0
 assert after['hp']==1000-damage and after['pool']==after['protected']==expected
 assert after['timer']==(4*packet['time'] if expected else 0)
 record('pool',c,ids=ids,attack=attack,damage=damage,packet=packet,after=after)
# A damage-derived pool persists, then decays at maximum HP per second.
for maximum,fps,copies in itertools.product((1000,2000),(30,60,120),(1,3)):
 c=equipped([7005600]*copies,maximum=maximum);c.build();c.receive(300)
 snapshots=[];decayAt=None;emptyAt=None;previous=c.state()
 for frame in range(1,5*fps+1):
  state=c.tick(1/fps)
  if state['pool']<previous['pool']:
   if decayAt is None:decayAt=frame/fps
   assert math.isclose(previous['pool']-state['pool'],min(previous['pool'],maximum/fps),abs_tol=.0001)
  if emptyAt is None and state['pool']==0:emptyAt=frame/fps
  if frame in (fps,3*fps,4*fps,5*fps):snapshots.append(dict(time=frame/fps,**state))
  assert state['hp']==maximum-300
  previous=state
 assert abs(decayAt-4)<=1.01/fps and abs(emptyAt-(4+300/maximum))<=2.01/fps
 record('timeline',c,maximum=maximum,fps=fps,copies=copies,decayAt=decayAt,emptyAt=emptyAt,snapshots=snapshots)
# New independent hits keep the new loss protected while old loss can decay;
# repeated non-negative source/slot identity retains the protected total.
slot_attack=next(int(id) for id,row in x.x['tables']['AtkParam_Pc'].items() if row['regainableSlotId']==1)
for attack in (0,slot_attack):
 c=equipped();c.build(attack);first=c.receive(300);c.tick(1)
 c.build(attack);second=c.receive(100);after=c.tick(.1)
 protected=400 if attack==slot_attack else 100
 assert first['protected']==300 and second['pool']==400 and second['protected']==protected and second['timer']==4
 assert math.isclose(after['pool'],400 if attack==slot_attack else 300,abs_tol=.0001)
 record('repeat',c,attack=attack,first=first,second=second,after=after)
# Existing missing HP is not recoverable; ordinary healing clamps the pool.
for initial,heal in ((800,0),(800,100),(800,400),(1000,500)):
 c=equipped(current=initial);c.build();c.receive(300)
 if heal:c.invoke(0x426130,[OBJ+0xe000,heal,0,0,0,0x3f800000,0])
 before=c.state();c.build(300000790)
 for _ in range(4):c.attack_hit();c.tick(0)
 after=c.state();expected=min(1000,initial-300+heal+min(300,max(0,1000-(initial-300+heal))))
 assert after['hp']==expected and after['pool']==0
 record('healing',c,initial=initial,heal=heal,before=before,after=after)
for damage,scaled,scale in ((0,False,1),(-100,False,1),(100,True,.5),(100,True,0),(100,False,.5)):
 c=equipped([7005601]);c.build();c.receive();c.build()
 c.attack_hit(damage,scaled,scale);after=c.tick(0)
 amount=0 if damage<=0 else int(int(f32(35*1.25))*(scale if scaled else 1))
 assert after['hp']==700+amount and c.recoveries==([] if damage<=0 else [amount])
 record('controls',c,damage=damage,scaled=scaled,scale=scale,amount=amount,after=after)
c=equipped();c.build();before=c.receive(1000);c.build();c.attack_hit();after=c.tick(0)
assert before['hp']==after['hp']==0 and after['pending']==35
record('controls',c,name='zero-hp-does-not-recover',before=before,after=after)
rows={str(id):x.spells[str(id)] for id in roots.values()}
output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),
 attackParamSha256=sha(atkraw),npcAttackParamSha256=sha(npcraw),weaponParamSha256=sha(wepraw),effects=roots,rows=rows,
 attackFields={str(id):{k:x.x['tables']['AtkParam_Pc'][str(id)][k] for k in ('wepRegainHpScale','atkRegainHp','regainableTimeScale','regainableHpRateScale','regainableSlotId')} for id in set(groups.values())|{slot_attack}},
 npcFields={str(id):{k:npc['tables']['AtkParam_Npc'][str(id)][k] for k in ('regainableTimeScale','regainableHpRateScale','regainableSlotId')} for id in (0,7000000,8000015)},
 weaponFields={str(id):assets['tables']['EquipParamWeapon'][str(id)]['wepRegainHp'] for id in (1000000,5000000,3000000)},
 preservationSeconds=4,decayMaxHpPerSecond=1,checks=checks,
 native=dict(metadata='E70C45..E70CDE within E70350',hit='43BE60',hp='426130 → 427BC0 → 426B00',
 recovery='43F37D..43F3F2 within 43ED80 → 50F230 → 507BC0 → 3DA510 → 4275A0',update='4289C0 → 269D000',repeat='4B2D50 → 4BFCF0'),
 stubs=sorted(stubs|{'attack metadata and outgoing-hit inner branches use explicit contexts; full collision and outer attack construction/dispatch are not simulated',
 'incoming damage amount is supplied; native HP loss, pool, timer, queue and integer recovery writes execute',
 'source/slot identity is supplied; actual attack animation usage, full death/reload and network synchronization remain unverified'}),gameplayVerified=False)
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(map(len,checks.values())),'native rally checks', {k:len(v) for k,v in checks.items()})


