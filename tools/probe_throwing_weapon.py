"""Verify throwing-weapon attack filters, duplicate equipment and native animation requests.

Pinned native consumers and TAE dispatch; actor, activity and equipment are
explicit fixtures. Projectile creation/collision and final damage are not run.
"""
import argparse,itertools,json,math,struct
from pathlib import Path
from native_effect_runtime import BASE,OBJ,STOP,Chain,Inputs,sha
from native_attack_runtime import Type1Attack
from native_animation_runtime import NativeTae
from unicorn.x86_const import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','assets','animations','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted);inputs=x;ts=x.x['tables']
assets=json.loads(a.assets.read_text());animations=json.loads(a.animations.read_text())
assert assets['hashes']['regulation.bin']==x.x['hashes']['regulation.bin']
raws={name:a.extracted.with_suffix('.'+name+'.param').read_bytes() for name in ('AttachEffectParam','AtkParam_Pc','BehaviorParam_PC','Bullet','EquipParamGoods')}
raws['EquipParamWeapon']=a.assets.with_suffix('.EquipParamWeapon.param').read_bytes()
hashes={'EquipParamGoods':'86e3af06770b3447b13e1e3b471bd173ec172bcfc981ccf9e6dae83a9f97ca87','AttachEffectParam':'ae8128ed510a532d0fa7cb56fa9c86e4a44c9d815dd4ee01c05821d5f50a9827','AtkParam_Pc':'1ec1893420053cbfb06e3efb269ade4ba9d6a617d1d3dbb370e837847be05676','BehaviorParam_PC':'f8fa3fd27cb98d45a3e24c69d71d8751df9202e6e379dc34fd77d4ef2e1240bb','Bullet':'ddce4888040a061cf982a237e8f6e3ddce5f2162a238865a072f75d27b5e9d44','EquipParamWeapon':'28adf74850c88ca0b4bb01f355c4f1f8e1b662a56d77894ae74d591b72c1a0ea'}
for name,raw in raws.items():assert sha(raw)==hashes[name]
assert sha(x.param)=='07ec636c5565d4551efeb53e6f08bc633b2aa4f2129f13c61b0638d69b1bc176'
rows=Inputs.table(raws['AttachEffectParam'],0x44);atk=Inputs.table(raws['AtkParam_Pc'],0x1d0)
behaviors=Inputs.table(raws['BehaviorParam_PC'],0x20);bullets=Inputs.table(raws['Bullet'],0x15c);weapons=Inputs.table(raws['EquipParamWeapon'],0x2a8)
goods=Inputs.table(raws['EquipParamGoods'],0xe0)
for name,table in (('EquipParamGoods',goods),('AttachEffectParam',rows),('AtkParam_Pc',atk),('BehaviorParam_PC',behaviors),('Bullet',bullets),('EquipParamWeapon',weapons)):
 assert len(table)==struct.unpack_from('<H',raws[name],10)[0]
EFFECT=320906;ROOT=20381100;RATE=1.1;TAG=250
attach=ts['AttachEffectParam'][str(EFFECT)];r=x.spells[str(ROOT)]
assert [attach['passiveSpEffectId_'+str(n)] for n in (1,2,3)]==[ROOT,-1,-1]
assert attach['exclusivityId']==attach['permanentSpEffectId']==-1 and all(v==1 for k,v in attach.items() if k.startswith('allow'))
assert (r['stateInfo'],r['spCategory'],r['effectEndurance'],r['magicSubCategoryChange1'])==(0,0,-1,TAG)
assert all(math.isclose(r[k+'AttackRate'],RATE,rel_tol=1e-6) for k in ('physics','magic','fire','thunder','dark'))
assert all(r[k]==-1 for k in ('cycleOccurrenceSpEffectId','replaceSpEffectId','atkOccurrenceSpEffectId'))
tags={int(id):sorted({r['subCategory'+str(n)] for n in range(1,6)}-{0}) for id,r in ts['AtkParam_Pc'].items()}
for id,values in tags.items():assert values==sorted(set(atk[id][off] for off in (0x4e,0x4f,0x1c8,0x1c9,0x1ca))-{0})
positive=sorted(id for id,values in tags.items() if TAG in values);assert len(positive)==196
representatives={}
for id,values in tags.items():representatives.setdefault(tuple(values),id)
assert len(representatives)==216 and not any(set(tags[id])&{108,120,121} for id in positive)
MAN=OBJ+0x8000;OUT=OBJ+0x9000;BITS=OBJ+0x9100
tracks={t['ID']:t for bundle in animations['bundles'] for t in bundle['taes']}
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

class Throw(Chain):
 def hook(self,u,address,size,user):
  if address-BASE==0xe6d630:
   id=u.reg_read(UC_X86_REG_R8)&0xffffffff;assert u.reg_read(UC_X86_REG_RDX)==1
   wrapper=u.reg_read(UC_X86_REG_RCX);u.mem_write(OBJ+0xa800,atk[id]);u.mem_write(wrapper,struct.pack('<iii4xQ',id,0,1,OBJ+0xa800))
   sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8);return
  super().hook(u,address,size,user)
 def row(self,id,kind=0):
  self.u.mem_write(OBJ+0x800,bytes(0x300));self.u.mem_write(OBJ+0xa800,atk[id]);self.q(OBJ+0xb010,OBJ+0xa800)
  self.invoke(0xe6d530,[OBJ+0xb000,OBJ+0x814]);assert int.from_bytes(self.u.mem_read(OBJ+0x814,32),'little')==sum(1<<tag for tag in tags[id]);self.u.mem_write(OBJ+0x808,struct.pack('<iiB',id,1,kind));self.invoke(0x502830,[OBJ,OBJ+0x800,-1,-1])
  return [struct.unpack('<f',self.u.mem_read(OBJ+0x800+off,4))[0] for off in (0x90,0xa4,0xa8,0xac,0xb0)]

class All:
 def __contains__(self,id):return True
class Trace(Type1Attack):
 def __init__(self,weapon,hero):super().__init__(x,behaviors,weapons,All());self.weapon=weapon;self.hero=hero;self.lookups=[];self.q(OBJ+0x6378,STOP+0x205)
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if address in (STOP+0x200,STOP+0x201,STOP+0x202,STOP+0x205):ret({STOP+0x200:0,STOP+0x201:1,STOP+0x202:self.weapon,STOP+0x205:self.hero}[address])
  elif pc==0xea76f0:pass
  elif pc==0x27d0640:ret()
  elif pc==0x3975d0:self.requests.append(dict(behavior=u.reg_read(UC_X86_REG_RDX),type=2));ret(1)
  else:
   if pc==0xe6fcb0:self.lookups.append(u.reg_read(UC_X86_REG_RDX)&0xffffffff)
   super().hook(u,address,size,user)

checks={k:[] for k in ('selection','filters','mixed','kinds','disabled','removal','dispatch')};stubs=set()
def record(key,c,**r):checks[key].append(r);stubs.update(c.stubs)
def start(copies=1,combined=0):
 c=Throw(x)
 for root in [ROOT]*copies+[7040501,7040301,7040401]*combined:c.insert(root)
 c.qualify();c.update(0);assert len(c.nodes())==int(bool(copies))+3*combined
 return c
def want(copies,id,combined=0,kind=0):
 if kind in (3,4,5,10):return 1
 return (RATE if copies and TAG in tags[id] else 1)*1.3**(combined*len(set(tags[id])&{108,120,121}))
def verify(c,copies,id,combined=0,kind=0):
 values=c.row(id,kind);assert all(math.isclose(v,want(copies,id,combined,kind),rel_tol=3e-6) for v in values),(copies,id,combined,kind,values)
 return values
for copies,hero in itertools.product((1,2,3,6),range(11)):
 c=Selection([[EFFECT]]*copies,hero);bits=c.select();assert all(i*6 in bits for i in range(copies))
 c.invoke(0xe6e150,[OBJ+0x9200,EFFECT]);roots=[c.invoke(0xe6e3b0,[OBJ+0x9200,i])&0xffffffff for i in range(3)];assert roots==[ROOT,0xffffffff,0xffffffff]
 v=start(copies);values=verify(v,copies,positive[0]);stubs.update(v.stubs)
 record('selection',c,copies=copies,hero=hero,bits=bits,roots=roots,values=values)
for copies in (0,1,2,3,6):
 c=start(copies)
 for id in sorted(set(positive)|set(representatives.values())):record('filters',c,copies=copies,attack=id,tags=tags[id],values=verify(c,copies,id))
for copies,combined in itertools.product(range(4),repeat=2):
 c=start(copies,combined);values={id:verify(c,copies,id,combined) for id in representatives.values()}
 record('mixed',c,copies=copies,combined=combined,values=values)
for copies,kind in itertools.product((0,1,3),range(13)):
 c=start(copies)
 for id in (positive[0],next(id for id,ts in tags.items() if TAG not in ts)):
  record('kinds',c,copies=copies,kind=kind,attack=id,values=verify(c,copies,id,kind=kind))
for mask in (1,2,0x40000,0x80000000):
 c=start();ptr=struct.unpack('<Q',c.u.mem_read(OBJ+8,8))[0];c.u.mem_write(ptr+0x68,struct.pack('<I',mask))
 record('disabled',c,mask=mask,values=verify(c,0,positive[0]))
for copies in (1,3,6):
 c=start(copies);c.invoke(0x505280,[OBJ,0]);c.qualify();c.update(0);assert not c.nodes()
 record('removal',c,copies=copies,values=verify(c,0,positive[0]))
print('PASS effect consumers',{k:len(v) for k,v in checks.items()},flush=True)
# Pin direct PARAM references, then execute their Type2 animation requests.
# This is not proof that every motion in each file is selected by gameplay.
bindings=[]
for key,b in ts['BehaviorParam_PC'].items():
 if b['refType']!=1:continue
 bullet=ts['Bullet'].get(str(b['refId']))
 if not bullet or bullet['atkId_Bullet'] not in positive:continue
 assert struct.unpack_from('<i',bullets[b['refId']],0)[0]==bullet['atkId_Bullet']
 bindings.append(dict(behavior=int(key),variation=b['variationId'],judge=b['behaviorJudgeId'],bullet=b['refId'],attack=bullet['atkId_Bullet']))
goods_bindings=[]
for id in (300,1700):
 for field,off in (('refId_default',4),('level2RefId',0xb8),('level3RefId',0xc0)):
  bid=ts['EquipParamGoods'][str(id)][field];assert struct.unpack_from('<i',goods[id],off)[0]==bid
  attack=ts['Bullet'][str(bid)]['atkId_Bullet'];assert struct.unpack_from('<i',bullets[bid],0)[0]==attack
  assert TAG not in tags[attack] and set(tags[attack])&{108,120,121}
  c=start();values=verify(c,1,attack);assert values==[1]*5;stubs.update(c.stubs)
  goods_bindings.append(dict(goods=id,name=x.x['texts']['zh_CN']['GoodsName'][str(id)],field=field,bullet=bid,attack=attack,tags=tags[attack],values=values))
wep_bindings=[];animation_hashes={}

for key,w in assets['tables']['EquipParamWeapon'].items():
 variations={w['behaviorVariationId'],w['heroBehaviorVariationID']}-{0,-1}
 if not any(b['variation'] in variations for b in bindings):continue
 weapon=int(key)
 assert struct.unpack_from('<i',weapons[weapon],4)[0]==w['behaviorVariationId']
 assert weapons[weapon][0x292]==w['heroID'] and struct.unpack_from('<i',weapons[weapon],0x294)[0]==w['heroBehaviorVariationID']
 # Baseline/hero variants use their own source tracks where available.
 tids={2000+w['wepmotionCategory'],2000+w['spAtkcategory'],2000+w['heroMovesetOverrideID']}-{2000}
 judges={b['judge'] for b in bindings if b['variation'] in variations}
 wep_bindings.append(dict(weapon=weapon,name=assets['texts']['zh_CN']['WeaponName'].get(key),variations=sorted(variations),tracks=sorted(tids)))
 for tid in sorted(tids):
  if tid not in tracks:continue
  events=[dict(animation=an['ID'],**e) for an in tracks[tid]['animations'] for e in an['events'] if e['Type']==2 and struct.unpack_from('<i',bytes.fromhex(e['hex']),8)[0] in judges]
  if not events:continue
  raw=Path(str(a.animations)+'.'+str(tid)+'.tae').read_bytes();animation_hashes[tid]=tracks[tid]['sha256']
  for hero in (1,5):
   c=Trace(weapon,hero);loader=NativeTae(c,raw,tracks[tid]['sha256'])
   for event in events:
    for enabled in (False,True):
     ctx=OBJ+0xd100;c.u.mem_write(ctx,bytes(0x40));found=False
     while c.invoke(0x27d0400,[loader.animations[event['animation']],ctx]):
      if struct.unpack('<I',c.u.mem_read(ctx,4))[0]!=2:continue
      ptr=struct.unpack('<Q',c.u.mem_read(ctx+8,8))[0]
      if bytes(c.u.mem_read(ptr,len(bytes.fromhex(event['hex']))))!=bytes.fromhex(event['hex']):continue
      c.q(OBJ+0xd018,OBJ+0x6000);c.u.mem_write(ctx+0x18,bytes([enabled]));c.requests.clear();c.lookups.clear()
      c.invoke(0x40cd80,[OBJ+0xd000,ctx]);found=True;requests=[]
      if not enabled:assert not c.requests
      for request in c.requests:
       b=ts['BehaviorParam_PC'][str(request['behavior'])];assert b['refType'] in (0,1)
       attack=b['refId'] if b['refType']==0 else ts['Bullet'][str(b['refId'])]['atkId_Bullet']
       # Native dispatch outputs select real rows, then the original attack
       # getter consumes the matching packet in a separate isolated actor.
       v=start();values=verify(v,1,attack);stubs.update(v.stubs)
       requests.append(dict(behavior=request['behavior'],referenceType=b['refType'],reference=b['refId'],attack=attack,tags=tags[attack],values=values))
      record('dispatch',c,weapon=weapon,hero=hero,track=tid,animation=event['animation'],event=event['index'],enabled=enabled,lookups=c.lookups[:],requests=requests)
      break
     assert found,event
   print('PASS dispatch',weapon,tid,hero,len(events),flush=True)
assert any(row['requests'] for row in checks['dispatch'])
output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),paramHashes=hashes,animationHashes=animation_hashes,
 effect=EFFECT,root=ROOT,rate=RATE,tag=TAG,positiveAttacks=positive,tagSets=len(representatives),weaponBindings=wep_bindings,behaviorBindings=bindings,goodsControls=goods_bindings,checks=checks,
 native=dict(selection='4FEA30 → E6E150 → E6E3B0',attack='E6D530 → 502830',list='50D060 → 5057D0 → 50ACD0',animation='27D0F10 → 27D0400 → 40CD80 → 668B30 / EA76F0',request='3975D0 recorder'),
 stubs=sorted(stubs|{'Actor virtuals supply actual equipped weapon ID and hero1/5; raw weapon/Behavior lookups are table fixtures.',
 'Explicit animation activity and frame; clip/scene reference sink; Behavior requests are recorded; attack/projectile instantiation is not executed.',
 'Selected Behavior attack rows are forwarded to an isolated native attack getter; complete projectile packet construction is not simulated.'}),
 limitations=['No full motion-selection graph, collision, final damage, DLL hooks, equipment rebuild, multiplayer, death or reload.',
 'Weapon bindings identify candidate motion files; not every motion or every attack on those weapons is claimed to benefit.',
 'Indirect projectile children and black-night-claw special attacks are not fully traced.',
 'Source kinds3/4/5/10 are excluded; no unsupported player-action mapping of internal types.'],gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n');print('PASS', {k:len(v) for k,v in checks.items()},sum(map(len,checks.values())),flush=True)
