"""Trace item-sharing selection, conditional emission and recipient values.

Goods/SpEffect/Behavior/Bullet rows and native selection/lifecycle/recipient
routines are real. Hero/upgrade inputs, animation-owner context, scene
collisions and final resource writes are fixtures, not game execution.
"""
import argparse,json,struct,itertools,math
from pathlib import Path
from native_effect_runtime import *
from native_ailment_runtime import Ailment
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted)
raws={name:a.extracted.with_suffix('.'+name+'.param').read_bytes() for name in ('EquipParamGoods','AtkParam_Pc','BehaviorParam_PC','Bullet')}
goods=Inputs.table(raws['EquipParamGoods'],0xe0);attacks=Inputs.table(raws['AtkParam_Pc'],0x1d0);bullets=Inputs.table(raws['Bullet'],0x100)
tables=x.x['tables'];grows=tables['EquipParamGoods'];spells=x.spells
class Goods(Chain):
 def __init__(self,hero=0,level=1):
  super().__init__(x);self.hero=hero;self.level=level
  self.q(OBJ+0x6190,OBJ);self.q(OBJ+0x61b8,OBJ+0xf000)
  for off,token in((0x178,0x200),(0x190,0x201),(0x218,0x202),(0x248,0x203)):self.q(OBJ+0x6200+off,STOP+token)
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if pc==0xe8d840:
   id=u.reg_read(UC_X86_REG_RDX)&0xffffffff;ptr=u.reg_read(UC_X86_REG_RCX);u.mem_write(OBJ+0xa000,goods[id]);u.mem_write(ptr,struct.pack('<IIQ',id,0,OBJ+0xa000));ret(ptr)
  elif pc==0x3d4180:ret(1)
  elif pc==0x20ba90:ret(self.level)
  elif address==STOP+0x200:ret(self.hero)
  elif address==STOP+0x201:ret(OBJ+0xb000)
  elif address==STOP+0x202:
   ptr=u.reg_read(UC_X86_REG_RDX);u.mem_write(ptr,bytes(16));ret(ptr)
  elif address==STOP+0x203:
   u.mem_write(OBJ+0xb800,struct.pack('<i',2));ret(OBJ+0xb800)
  else:super().hook(u,address,size,user)
 def select(self,id):
  ptr=OBJ+0xd000;self.u.mem_write(ptr,bytes(0x200));self.q(ptr,OBJ+0x6000);self.invoke(0x3844c0,[ptr,id]);return dict(type=self.u.mem_read(ptr+0x14,1)[0],ref=struct.unpack('<i',self.u.mem_read(ptr+0x18,4))[0])

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


class Item(Actor):
 def __init__(self):self.frame=0;self.shots=[];super().__init__()
 def hook(self,u,address,size,user):
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  pc=address-BASE
  if pc==0x3ced90:ret(OBJ+0xd000)
  elif pc==0x4d1b20:ret()
  elif pc==0x3975d0:self.shots.append(dict(frame=self.frame,behavior=u.reg_read(UC_X86_REG_RDX)));ret(1)
  else:super().hook(u,address,size,user)

class AttackSetup(Chain):
 def __init__(self):super().__init__(x);self.attacks=[]
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if pc==0x34a890:
   radius=struct.unpack('<f',(u.reg_read(UC_X86_REG_XMM2)&0xffffffff).to_bytes(4,'little'))[0]
   self.attacks.append(dict(id=u.reg_read(UC_X86_REG_RDX)&0xffffffff,radius=radius));ret()
  elif pc in(0x34ad90,0x34b130,0x34dc70):ret()
  else:super().hook(u,address,size,user)

class Recipient(Hit):
 def __init__(self):
  super().__init__();self.u.mem_write(SOURCE+0x74,b'\1');self.u.mem_write(OBJ+0x6074,b'\1')

checks={k:[] for k in ('selection','trigger','radius','attackSetup','arrival','cure','fp','observation','refresh')};stubs=set()
def record(key,c,**row):checks[key].append(row);stubs.update(c.stubs)
def equip(c,copies):
 for _ in range(copies):
  for root in(7050100,7050200,7050300):c.insert(root)
 c.qualify();c.update(0)
def step(c,dt=1/60):c.qualify();c.update(dt)
food_ids=sorted(int(id) for id,r in grows.items() if r['useItemConferBullets']!=-1)
assert food_ids==[820,830,1100,1190,1200,1210]
item_ids=food_ids+[900,910,920,930,940,950,960,1290]
paths=[];used_bullets=set();used_spells={7050100,7050200,7050300}
# Build the actual conditional graph from each selected item's real effect row.
def walk(id,seen=None):
 seen=set() if seen is None else seen
 if id<=0 or id in seen:return seen
 seen.add(id)
 for key in ('replaceSpEffectId','cycleOccurrenceSpEffectId'):walk(spells[str(id)][key],seen)
 return seen
for item,level in itertools.product(item_ids,(1,2,3)):
 row=grows[str(item)];field={1:'refId_default',2:'level2RefId',3:'level3RefId'}[level]
 if item in food_ids:
  field={1:'itemConferBulletId',2:'level2_itemConferBulletId',3:'level3_itemConferBulletId'}[level]
  bid=row[field];used_bullets.add(bid);sp=tables['Bullet'][str(bid)]['spEffectId0'];used_spells.update(walk(sp))
  paths.append(dict(item=item,level=level,kind='food',bullet=bid,leaf=sp,seed=row[{1:'refId_default',2:'level2RefId',3:'level3RefId'}[level]]))
 else:
  seed=row[field];nodes=walk(seed);used_spells.update(nodes)
  emitters=[id for id in nodes if spells[str(id)]['stateInfo']==275]
  assert len(emitters)==1,(item,level,emitters)
  emitter=emitters[0];state=spells[str(emitter)]['invocationConditionsStateChange1'];assert state==(2013 if item==1290 else 2014)
  behavior=spells[str(emitter)]['behaviorId'];br=tables['BehaviorParam_PC'][str(behavior)];assert br['refType']==1
  bid=br['refId'];used_bullets.add(bid);leaf=tables['Bullet'][str(bid)]['spEffectId0'];used_spells.update(walk(leaf))
  paths.append(dict(item=item,level=level,kind='fp' if item==1290 else 'bolus',seed=seed,emitter=emitter,state=state,behavior=behavior,bullet=bid,leaf=leaf))
# Also check unsupported reference substitutions with actual ordinary rows.
for item,hero,level,copies in itertools.product(item_ids,(0,9),(1,2,3),(0,1,3)):
 c=Goods(hero,level);equip(c,copies);result=c.select(item)
 actual_level=level if hero==9 else 1
 path=next(p for p in paths if p['item']==item and p['level']==actual_level)
 expected=dict(type=1,ref=path['bullet']) if copies and item in food_ids else dict(type=2,ref=path['seed'])
 assert result==expected,(item,hero,level,copies,result,expected)
 record('selection',c,item=item,hero=hero,level=level,copies=copies,result=result)
print('PASS item selection',flush=True)
for path,copies,fps in itertools.product([p for p in paths if p['kind']!='food'],(0,1,3),(30,120)):
 c=Item();equip(c,copies);c.grant(path['seed']);packets=[]
 for frame in range(fps):
  c.frame=frame;step(c,1/fps);c.invoke(0x50aa20,[OBJ]);fp=c.fp(1000)
  if any(fp):packets.append(dict(frame=frame,fp=fp))
 assert [r['behavior'] for r in c.shots]==([path['behavior']] if copies else []),(path,copies,c.shots)
 if path['kind']=='fp':assert sum(r['fp'][0] for r in packets)==(600 if path['level']==1 else 700)
 else:assert not packets
 record('trigger',c,item=path['item'],level=path['level'],copies=copies,fps=fps,seed=path['seed'],requests=c.shots,fpPackets=packets)
print('PASS conditional item chains',flush=True)
for bid in sorted(used_bullets):
 c=AttackSetup();param=OBJ+0x9000;c.u.mem_write(param,bullets[bid]);c.q(OBJ+0x4008,param);row=tables['Bullet'][str(bid)]
 assert row['hitRadius']==15 and row['numShoot']==1
 for fraction in(0,.5,1):
  c.invoke(0x363600,[OBJ+0x4008],{UC_X86_REG_XMM1:fraction})
  radius=struct.unpack('<f',(c.u.reg_read(UC_X86_REG_XMM0)&0xffffffff).to_bytes(4,'little'))[0]
  assert radius==15;record('radius',c,bullet=bid,fraction=fraction,radius=radius)
 c.invoke(0x362c10,[OBJ+0x4000,OBJ+0x8000]);assert c.attacks==[dict(id=row['atkId_Bullet'],radius=15)]
 record('attackSetup',c,bullet=bid,requests=c.attacks)
# One receipt per actual payload. This starts at the hit-delivery boundary;
# physical collision, team resolution and emitting positions are not simulated.
for path,same in itertools.product(paths,(False,True)):
 c=Recipient();c.same=same;attack=tables['Bullet'][str(path['bullet'])]['atkId_Bullet']
 if path['kind']=='bolus':c.u.mem_write(OBJ+0x9010,struct.pack('<7i',*([250]*7)))
 c.hit(path['leaf'],attack=attack);step(c,0)
 if path['kind']=='bolus':
  for _ in range(10):step(c)
  kind={900:0,910:2,920:4,930:5,940:1,950:3,960:6}[path['item']]
  accepted=struct.unpack('<i',c.u.mem_read(OBJ+0x9010+kind*4,4))[0]==500
 else:accepted=any(n['id']==path['leaf'] for n in c.nodes())
 expected=not same or bool(spells[str(path['leaf'])]['effectTargetSelfTarget'])
 assert accepted==expected,(path,same,c.sent)
 record('arrival',c,item=path['item'],level=path['level'],same=same,leaf=path['leaf'],attack=attack,accepted=accepted)
for path in [p for p in paths if p['kind']=='bolus']:
 c=Recipient();c.u.mem_write(OBJ+0x9010,struct.pack('<7i',*([250]*7)))
 c.hit(path['leaf'],attack=800000100)
 for _ in range(10):step(c)
 remaining=list(struct.unpack('<7i',c.u.mem_read(OBJ+0x9010,28)))
 kind={900:0,910:2,920:4,930:5,940:1,950:3,960:6}[path['item']]
 expected=[250]*7;expected[kind]=500
 assert remaining==expected,(path,remaining,expected)
 record('cure',c,item=path['item'],level=path['level'],kind=kind,remaining=remaining)
for leaf,maximum in itertools.product((7050102,708503),(101,1000,1723)):
 c=Recipient();c.hit(leaf,attack=800000100);step(c,0);packet=c.fp(maximum)
 rate=spells[str(leaf)]['changeMpRate'];expected=math.trunc(struct.unpack('<f',struct.pack('<f',maximum*(-rate*.01)))[0])
 assert packet==[expected,0],(leaf,maximum,packet,expected)
 record('fp',c,leaf=leaf,maximum=maximum,packet=packet)
for leaf,copies in itertools.product((3970,7050303,708400),(1,3)):
 c=Item()
 for _ in range(copies):c.grant(leaf)
 step(c,0);c.invoke(0x5071b0,[OBJ]);raw=struct.unpack('<f',(c.u.reg_read(UC_X86_REG_XMM0)&0xffffffff).to_bytes(4,'little'))[0]
 display=c.invoke(0x6c7e40,[0,OBJ])&0xffffffff
 assert math.isclose(raw,spells[str(leaf)]['itemDropRate'],rel_tol=1e-6)
 f32=lambda value:struct.unpack('<f',struct.pack('<f',value))[0]
 c.invoke(0x6c7f30,[0,OBJ]);ratio=struct.unpack('<f',(c.u.reg_read(UC_X86_REG_XMM0)&0xffffffff).to_bytes(4,'little'))[0]
 assert ratio==f32(1+raw) and display==math.ceil(f32(ratio*100)),(leaf,copies,raw,ratio,display)
 record('observation',c,leaf=leaf,copies=copies,raw=raw,neutralRatio=ratio,neutralDisplay=display)
for leaf in sorted({p['leaf'] for p in paths if p['kind']=='food'}):
 c=Item();c.grant(leaf);step(c,0)
 life=spells[str(leaf)]['effectEndurance'];assert life in(30,60)
 for _ in range(300):step(c,1/60)
 c.grant(leaf);step(c,0);nodes=[n for n in c.nodes() if n['id']==leaf]
 assert len(nodes)==1 and math.isclose(nodes[0]['lifetime'],life,abs_tol=1e-5)
 record('refresh',c,leaf=leaf,afterSeconds=5,lifetime=life,nodes=nodes)
fields=('stateInfo','spCategory','effectEndurance','motionInterval','replaceSpEffectId','cycleOccurrenceSpEffectId','invocationConditionsStateChange1','behaviorId','changeMpRate','changeMpPoint','itemDropRate','isContractSpEffectLife')
output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),assetHashes={k:sha(v) for k,v in raws.items()},
 bullets={str(bid):{**{k:tables['Bullet'][str(bid)][k] for k in ('life','numShoot','hitRadius','hitRadiusMax','atkId_Bullet','spEffectId0')},'targets':{k:tables['AtkParam_Pc'][str(tables['Bullet'][str(bid)]['atkId_Bullet'])][k] for k in ('selfTarget','friendlyTarget','opposeTarget')}} for bid in sorted(used_bullets)},
 effects=[7050100],roots=[7050100,7050200,7050300],paths=paths,names={str(id):x.x['texts']['zh_CN']['GoodsName'][str(id)] for id in item_ids},
 rows={str(id):{k:spells[str(id)][k] for k in fields} for id in sorted(used_spells|{3970,708400,708401})},
 checks=checks,stubs=sorted(stubs|{'E8D840 lookup uses actual Goods rows; hero ID, local actor, pose and 20BA90 upgrade level are explicit inputs',
 '3CED90 animation-owner context; 4D1B20 false ordinary mode; 3975D0 records Behavior requests',
 '34A890 records attack creation; 34AD90/34B130 visuals and 34DC70 mode predicate are fixtures',
 'source payload supplied from actual Bullet; collision/team relation/positions/final resource writes are not simulated',
 'forced same-actor hit tests only SpEffect routing; actual Bullet Atk selfTarget collision filters may exclude that hit earlier',
 'full consumable actions, scholar proficiency accumulation, duration modifiers, same-frame multi-use, multiplayer and game execution not simulated'}),
 native=dict(selection='3844C0 → 508E20 / E8D4F0 / E8D510 / E8D540',grant='3C7FD0',lifecycle='5057D0 / 50ACD0',emit='50AA20 → 3975D0',
 radius='363600',attackSetup='362C10 → 34A890',arrival='43BE60 → 3C80A0',fp='507460',observation='5071B0 / 6C7E40'),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(map(len,checks.values())),'native item-sharing checks',{k:len(v) for k,v in checks.items()},flush=True)
