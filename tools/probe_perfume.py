"""Execute perfume item/weapon filters and repeatedly renewed zero-life branches.

Actual Atk rows construct native attack tags, and the original actor grant runs
immediately during the periodic update. Weapon/Behavior/Bullet bindings are
static evidence; the complete animation, projectile and damage pipeline is not
simulated. Zero-life child renewal must not be mistaken for unbounded stacking.
"""
import argparse
import itertools
import json
import math
import struct
from pathlib import Path
from native_effect_runtime import BASE, OBJ, STOP, Inputs, sha
from native_ailment_runtime import Ailment
from unicorn.x86_const import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','assets','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted);assets=json.loads(a.assets.read_text())
assert assets['hashes']['regulation.bin']==x.x['hashes']['regulation.bin']
atkraw=a.extracted.with_suffix('.AtkParam_Pc.param').read_bytes();atkrows=Inputs.table(atkraw,0x1d0)
wepraw=a.assets.with_suffix('.EquipParamWeapon.param').read_bytes();weprows=Inputs.table(wepraw,0x298)
families=[]
for effect,root,leaf,primary,secondary in ((7043100,8400000,8400005,1.15,1.05),(6043100,8400001,8400006,1.3,1.1)):
 attach=x.x['tables']['AttachEffectParam'][str(effect)]
 assert attach['passiveSpEffectId_1']==root and attach['exclusivityId']==-1
 for id,rate,category,life in ((root,primary,109,-1),(leaf,secondary,251,0)):
  row=x.spells[str(id)]
  assert row['spCategory']==10 and row['stateInfo']==0 and row['effectEndurance']==life and row['motionInterval']==0
  assert row['cycleOccurrenceSpEffectId']==(leaf if id==root else -1)
  assert row['replaceSpEffectId']==row['atkOccurrenceSpEffectId']==-1
  assert x.rows[id][0x158]==0 and not(x.rows[id][0x160]&128 or x.rows[id][0x161]&1 or x.rows[id][0x259]&32)
  assert row['magicSubCategoryChange1']==category and row['magicSubCategoryChange2']==row['magicSubCategoryChange3']==0
  assert all(row['invocationConditionsStateChange'+str(i)]==0 for i in(1,2,3))
  assert all(math.isclose(row[k+'AttackRate'],rate,rel_tol=1e-6) for k in('physics','magic','fire','thunder','dark'))
 families.append(dict(effect=effect,root=root,leaf=leaf,primary=x.spells[str(root)]['physicsAttackRate'],secondary=x.spells[str(leaf)]['physicsAttackRate']))
attacks={}
for key,row in x.x['tables']['AtkParam_Pc'].items():
 tags=[row['subCategory'+str(n)] for n in range(1,6)]
 if not set(tags).intersection({109,251}) and int(key) not in(40000,100000,200000,300000):continue
 assert tags==[atkrows[int(key)][off] for off in(0x4e,0x4f,0x1c8,0x1c9,0x1ca)]
 attacks[int(key)]=[v for v in tags if v]
assert len(attacks)==226 and sum(109 in v for v in attacks.values())==38 and sum(251 in v for v in attacks.values())==184
assert not any(109 in v and 251 in v for v in attacks.values())
bindings=[]
for id in range(61500000,61550000,10000):
 row=assets['tables']['EquipParamWeapon'][str(id)];variation=row['behaviorVariationId'];assert variation==6000+(id-61500000)//10000 and row['wepType']==91
 assert struct.unpack_from('<i',weprows[id],4)[0]==variation and struct.unpack_from('<H',weprows[id],0x1a6)[0]==91
 behavior=next((int(k),r) for k,r in x.x['tables']['BehaviorParam_PC'].items() if r['variationId']==variation and r['refType']==1 and r['behaviorJudgeId']==0)
 bullet=x.x['tables']['Bullet'][str(behavior[1]['refId'])];assert 251 in attacks[bullet['atkId_Bullet']]
 bindings.append(dict(weapon=id,name=assets['texts']['zh_CN']['WeaponName'][str(id)],variation=variation,
                      behavior=behavior[0],bullet=behavior[1]['refId'],attack=bullet['atkId_Bullet']))
goods=x.x['tables']['EquipParamGoods']['3510'];assert goods['spEffectCategory']==0;spark=[]
for field in('refId_default','level2RefId','level3RefId'):
 bullet=int(goods[field]);attack=x.x['tables']['Bullet'][str(bullet)]['atkId_Bullet'];assert 109 in attacks[attack]
 spark.append(dict(field=field,bullet=bullet,attack=attack))
class Perfume(Ailment):
 def __init__(self,kind=0,maximum=500):
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
  elif pc==0xe6d630:
   id=u.reg_read(UC_X86_REG_R8)&0xffffffff;assert u.reg_read(UC_X86_REG_RDX)==1
   wrapper=u.reg_read(UC_X86_REG_RCX);u.mem_write(OBJ+0xa800,atkrows[id])
   u.mem_write(wrapper,struct.pack('<iii4xQ',id,0,1,OBJ+0xa800));ret()
   self.stubs.add('E6D630 actual AtkParam_Pc row lookup')
  else:super().hook(u,address,size,user)
 def grant(self,id):self.invoke(0x3c7fd0,[OBJ+0x6000,id,1])
 def attackrow(self,id,kind=None):
  if kind is None:kind=1 if 251 in attacks[id] else 0
  self.u.mem_write(OBJ+0xa800,atkrows[id]);self.q(OBJ+0xb010,OBJ+0xa800)
  self.invoke(0xe6d530,[OBJ+0xb000,OBJ+0x814])
  tags={r for r in [x.x['tables']['AtkParam_Pc'][str(id)]['subCategory'+str(n)] for n in range(1,6)] if r}
  assert int.from_bytes(self.u.mem_read(OBJ+0x814,32),'little')==sum(1<<n for n in tags)
  self.u.mem_write(OBJ+0x808,struct.pack('<iiB',id,1,kind))
  self.invoke(0x502830,[OBJ,OBJ+0x800,-1,-1])
  return [struct.unpack('<f',self.u.mem_read(OBJ+0x800+o,4))[0] for o in(0x90,0xa4,0xa8,0xac,0xb0)]

checks=dict(filters=[],kinds=[],disabled=[],lifecycle=[]);stubs=set()
def expected(normal,upgraded,attack,child=True):
 tags=attacks[attack];v=1.
 if 109 in tags:v*=families[0]['primary']**normal*families[1]['primary']**upgraded
 if 251 in tags and child:v*=families[0]['secondary']**normal*families[1]['secondary']**upgraded
 return v
def verify(values,multiplier):assert all(math.isclose(v,multiplier,rel_tol=2e-6) for v in values),(values,multiplier)
def start(normal,upgraded):
 c=Perfume()
 for f,count in zip(families,(normal,upgraded)):
  for _ in range(count):c.grant(f['root'])
 return c
def step(c,dt):c.qualify();c.update(dt)
def record(key,c,**row):checks[key].append(row);stubs.update(c.stubs)
for normal,upgraded in itertools.product(range(4),repeat=2):
 c=start(normal,upgraded)
 for _ in range(3):step(c,1/60)
 for attack in attacks:
  values=c.attackrow(attack);verify(values,expected(normal,upgraded,attack))
  record('filters',c,normal=normal,upgraded=upgraded,attack=attack,values=values)
 # Disabled-node negative control without another qualification/update.
 node=struct.unpack('<Q',c.u.mem_read(OBJ+8,8))[0]
 while node:
  c.u.mem_write(node+0x68,struct.pack('<I',0x800c0003));node=struct.unpack('<Q',c.u.mem_read(node+0x38,8))[0]
 for attack in(10351000,6150000,40000):
  values=c.attackrow(attack);verify(values,1)
  record('disabled',c,normal=normal,upgraded=upgraded,attack=attack,values=values)
for normal,upgraded in((0,0),(1,0),(0,1),(1,1)):
 c=start(normal,upgraded)
 for _ in range(3):step(c,1/60)
 for attack,kind in itertools.product((10351000,6150000,40000),range(13)):
  values=c.attackrow(attack,kind);verify(values,1 if kind in (3,4,5,10) else expected(normal,upgraded,attack))
  record('kinds',c,normal=normal,upgraded=upgraded,attack=attack,kind=kind,values=values)
for normal,upgraded,fps in itertools.product(range(4),range(4),(30,60,120)):
 c=start(normal,upgraded);frames=[]
 for frame in range(20):
  step(c,1/fps)
  values={id:c.attackrow(id) for id in(10351000,6150000,40000)}
  for id,v in values.items():verify(v,expected(normal,upgraded,id,frame>0))
  nodes=c.nodes();count=normal+upgraded
  assert len(nodes)==count*(2 if frame==0 else 3)
  assert sum(n['id'] in (8400005,8400006) and not(n['flags']&0x800c0003) for n in nodes)==(count if frame else 0)
  if frame in(0,1,19):frames.append(dict(frame=frame,values=values,nodes=nodes))
 # Force only the roots to expire, then execute native removal and leaf expiry.
 # This is a renewal-stop fixture, not a simulation of inventory unequipping.
 node=struct.unpack('<Q',c.u.mem_read(OBJ+8,8))[0]
 while node:
  if struct.unpack('<i',c.u.mem_read(node+8,4))[0] in (8400000,8400001):c.u.mem_write(node+0x4c,struct.pack('<f',0))
  node=struct.unpack('<Q',c.u.mem_read(node+0x38,8))[0]
 for _ in range(3):step(c,1/fps)
 assert not c.nodes()
 for id in(10351000,6150000,40000):verify(c.attackrow(id),1)
 record('lifecycle',c,normal=normal,upgraded=upgraded,fps=fps,frames=frames,afterStop=c.nodes())
output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),
 atkParamSha256=sha(atkraw),weaponParamSha256=sha(wepraw),messageSha256=assets['hashes']['msg/zhocn/item_dlc01.msgbnd.dcx'],
 families=families,attacks=attacks,weaponBindings=bindings,sparkAromatic=dict(goods=3510,name=x.x['texts']['zh_CN']['GoodsName']['3510'],levels=spark),
 checks=checks,native=dict(tags='E6D530 → E6D3E0',filter='511010 → EA1B00 / EA1D40',damage='502830',
 grant='3C7FD0 → 3C80A0 → 3DB410 → 50A4C0 → 50D060',update='50ACD0 → 511B80'),
 stubs=sorted(stubs|{'explicit attack packet kind; full animation/projectile/damage pipeline not executed',
 'root lifetime forced to zero to stop renewal; inventory unequip flow not executed'}),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(map(len,checks.values())),'native perfume cases')
