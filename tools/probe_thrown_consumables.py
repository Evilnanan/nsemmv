"""Execute thrown-consumable selection, attack filters and mixed stacking.

Pinned original rows and native instructions; isolated actors/source-kind and
upgrade inputs, not gameplay, collisions or final HP damage.
"""
import argparse,itertools,json,math,struct
from pathlib import Path
from native_effect_runtime import BASE,OBJ,STOP,Chain,Inputs,sha
from unicorn.x86_const import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted);inputs=x;t=x.x['tables']
raws={name:a.extracted.with_suffix('.'+name+'.param').read_bytes() for name in ('AttachEffectParam','AtkParam_Pc','Bullet','EquipParamGoods')}
expected_hashes={'AttachEffectParam':'ae8128ed510a532d0fa7cb56fa9c86e4a44c9d815dd4ee01c05821d5f50a9827','AtkParam_Pc':'1ec1893420053cbfb06e3efb269ade4ba9d6a617d1d3dbb370e837847be05676','Bullet':'ddce4888040a061cf982a237e8f6e3ddce5f2162a238865a072f75d27b5e9d44','EquipParamGoods':'86e3af06770b3447b13e1e3b471bd173ec172bcfc981ccf9e6dae83a9f97ca87'}
assert sha(x.param)=='07ec636c5565d4551efeb53e6f08bc633b2aa4f2129f13c61b0638d69b1bc176'
for name,b in raws.items():assert sha(b)==expected_hashes[name]
rows=Inputs.table(raws['AttachEffectParam'],0x44);atk=Inputs.table(raws['AtkParam_Pc'],0x1d0)
bullets=Inputs.table(raws['Bullet'],0x15c);goods=Inputs.table(raws['EquipParamGoods'],0xe0)
for name,table in (('AttachEffectParam',rows),('AtkParam_Pc',atk),('Bullet',bullets),('EquipParamGoods',goods)):
 assert len(table)==struct.unpack_from('<H',raws[name],10)[0],name
families=[];root_meta={}
for effect,roots in ((7006504,[7040501,7040301,7040401]),(7040300,[7040300]),(6040300,[7040301]),(7040400,[7040400]),(6040400,[7040401]),(7040500,[7040500]),(6040500,[7040501])):
 attach=t['AttachEffectParam'][str(effect)]
 assert [attach['passiveSpEffectId_'+str(n)] for n in (1,2,3)]==(roots+[-1]*3)[:3]
 assert attach['exclusivityId']==attach['permanentSpEffectId']==-1
 assert all(v==1 for k,v in attach.items() if k.startswith('allow'))
 families.append(dict(effect=effect,roots=roots))
 for root in roots:
  r=x.spells[str(root)];tag=r['magicSubCategoryChange1'];rate=r['physicsAttackRate']
  assert tag in (108,120,121) and r['magicSubCategoryChange2']==r['magicSubCategoryChange3']==0
  assert (r['spCategory'],r['stateInfo'],r['effectEndurance'],r['motionInterval'])==(10,0,-1,0)
  assert all(r[k]==-1 for k in ('cycleOccurrenceSpEffectId','replaceSpEffectId','atkOccurrenceSpEffectId'))
  assert all(r[k]==0 for k in ('invocationConditionsStateChange1','invocationConditionsStateChange2','invocationConditionsStateChange3'))
  assert all(r[k+'AttackRate']==rate for k in ('physics','magic','fire','thunder','dark'))
  assert math.isclose(rate,1.3 if root%10 else 1.15,rel_tol=1e-6)
  assert x.rows[root][0x158]==0 and not(x.rows[root][0x160]&128 or x.rows[root][0x161]&1 or x.rows[root][0x259]&32)
  root_meta[root]=dict(tag=tag,rate=rate)
for root in root_meta:
 assert sum(struct.unpack_from('<i',x.param,0x40+i*24)[0]==root for i in range(struct.unpack_from('<H',x.param,10)[0]))==1
tags={int(id):sorted({r['subCategory'+str(i)] for i in range(1,6)}-{0}) for id,r in t['AtkParam_Pc'].items()}
for id,ts in tags.items():assert ts==sorted(set(atk[id][o] for o in (0x4e,0x4f,0x1c8,0x1c9,0x1ca))-{0})
positives=sorted(id for id,ts in tags.items() if set(ts)&{108,120,121})
representatives={}
for id,ts in tags.items():representatives.setdefault(tuple(ts),id)
overlap=[id for id in positives if len(set(tags[id])&{108,120,121})>1];assert overlap==[321330,321340]
assert {tag:sum(tag in ts for ts in tags.values()) for tag in (108,120,121)}=={108:291,120:52,121:53}
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

checks={key:[] for key in ('selection','filters','mixed','kinds','disabled','removal','goods')};stubs=set()
by_effect={f['effect']:f['roots'] for f in families}
def record(key,c,**row):checks[key].append(row);stubs.update(c.stubs)
def expected(roots,attack,kind=0):return 1 if kind in (3,4,5,10) else math.prod(root_meta[r]['rate'] for r in roots if root_meta[r]['tag'] in tags[attack])
def verify(c,roots,attack,kind=0):
 values=c.row(attack,kind);v=expected(roots,attack,kind)
 assert all(math.isclose(n,v,rel_tol=3e-6) for n in values),(roots,attack,kind,values,v)
 return values
def prepare(roots):
 c=Throw(x)
 for r in roots:c.insert(r)
 c.qualify();c.update(0);assert len(c.nodes())==len(roots)
 return c
samples=(10030000,10170000,10303000,210318000,321330,1210100,40000)
for f,copies,hero in itertools.product(families,(1,2,3,6),range(11)):
 c=Selection([[f['effect']]]*copies,hero);bits=c.select();selected=[]
 assert all(i*6 in bits for i in range(copies)),(f,copies,hero,bits)
 for i in range(copies):
  c.invoke(0xe6e150,[OBJ+0x9200,f['effect']])
  selected.extend(c.invoke(0xe6e3b0,[OBJ+0x9200,j])&0xffffffff for j in range(len(f['roots'])))
 assert selected==f['roots']*copies
 v=prepare(selected);values={id:verify(v,selected,id) for id in samples[:3]};stubs.update(v.stubs)
 record('selection',c,effect=f['effect'],copies=copies,hero=hero,selectionBits=bits,selected=selected,instances=len(v.nodes()),values=values)
print('PASS selection',len(checks['selection']),flush=True)
sets=[[],*[f['roots'] for f in families],by_effect[7006504]*3]
for roots in sets:
 c=prepare(roots)
 for attack in sorted(set(positives)|set(representatives.values())):
  record('filters',c,roots=roots,attack=attack,values=verify(c,roots,attack))
print('PASS filters',len(checks['filters']),flush=True)
for normal,upgraded,combined,tag in itertools.product(range(4),range(4),range(4),(108,120,121)):
 base={108:7040300,120:7040400,121:7040500}[tag]
 roots=[base]*normal+[base+1]*upgraded+by_effect[7006504]*combined;c=prepare(roots)
 values={id:verify(c,roots,id) for id in samples}
 record('mixed',c,normal=normal,upgraded=upgraded,combined=combined,tag=tag,roots=roots,values=values)
print('PASS mixed',len(checks['mixed']),flush=True)
for f,copies in itertools.product(families,(1,3)):
 roots=f['roots']*copies;c=prepare(roots)
 for attack,kind in itertools.product(samples,range(13)):
  record('kinds',c,effect=f['effect'],copies=copies,attack=attack,kind=kind,values=verify(c,roots,attack,kind))
 ptr=struct.unpack('<Q',c.u.mem_read(OBJ+8,8))[0]
 while ptr:
  c.u.mem_write(ptr+0x68,struct.pack('<I',0x800c0003));ptr=struct.unpack('<Q',c.u.mem_read(ptr+0x38,8))[0]
 for attack in samples:record('disabled',c,effect=f['effect'],copies=copies,attack=attack,values=verify(c,[],attack))
print('PASS kinds/disabled',len(checks['kinds']),len(checks['disabled']),flush=True)
# 505280 takes the CURRENT list index, not a stable handle. Remove tail to head.
for roots in (by_effect[7006504]*3,[7040300,7040301,*by_effect[7006504]],[7040500,7040501,*by_effect[7006504]]):
 c=Throw(x);indices=[c.insert(r) for r in roots];c.qualify();c.update(0)
 remaining=list(roots)
 for index in reversed(indices):
  c.invoke(0x505280,[OBJ,index]);remaining.pop();c.qualify();c.update(0)
  assert [n["id"] for n in c.nodes()]==remaining
  record('removal',c,roots=roots,remaining=list(remaining),values={id:verify(c,remaining,id) for id in samples})
print('PASS removal',len(checks['removal']),flush=True)
# Decode every directly linked throwing item and all three grade references.
# Native selection below proves Scholar-specific upgrades; it does not spawn bullets.
bindings=[]
for key,r in t['EquipParamGoods'].items():
 id=int(key)
 for level,field,off in ((1,'refId_default',4),(2,'level2RefId',0xb8),(3,'level3RefId',0xc0)):
  assert struct.unpack_from('<i',goods[id],off)[0]==r[field]
  bid=r[field];br=t['Bullet'].get(str(bid));attack=br['atkId_Bullet'] if br else -1
  if attack not in tags or not(set(tags[attack])&{108,120,121}):continue
  assert struct.unpack_from('<i',bullets[bid],0)[0]==attack
  bindings.append(dict(goods=id,name=x.x['texts']['zh_CN']['GoodsName'].get(key),level=level,bullet=bid,attack=attack,tags=tags[attack]))
for item,hero,level in itertools.product((300,1700,3030,2003180),range(11),(1,2,3)):
 c=Goods(hero,level);result=c.select(item);actual_level=level if hero==9 else 1
 b=next(b for b in bindings if b['goods']==item and b['level']==actual_level)
 assert result==dict(type=1,ref=b['bullet']),(item,hero,level,result,b)
 attack=b['attack'];v=prepare(by_effect[7006504]);values=verify(v,by_effect[7006504],attack);stubs.update(v.stubs)
 record('goods',c,goods=item,hero=hero,level=level,result=result,attack=attack,values=values)
print('PASS goods',len(checks['goods']),flush=True)
out=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),
 paramHashes=expected_hashes,families=families,roots=root_meta,attacks={id:tags[id] for id in sorted(set(positives)|set(representatives.values()))},
 overlap=overlap,goodsBindings=bindings,checks=checks,
 native=dict(selection='4FEA30 → E6E150 → E6E3B0',insert='50D060',tags='E6D530 → E6D3E0',attack='502830 → 511010',goods='3844C0',remove='505280'),
 stubs=sorted(stubs|{'E6D630 actual AtkParam_Pc lookup','E8D840 actual EquipParamGoods lookup','explicit actor identity / Scholar upgrade count and item usability; allocation and notification fixtures'}),
 limitations=['Isolated source-kind inputs, not full damage delivery or final HP writes.', 'Goods selection executes but projectile creation, collision and attack reachability do not.', 'Double-tag rows 321330/321340 have unresolved weapon/action reachability; not named as usable consumables.', 'No DLL hooks, equipment rebuild, death, reload or network session executed.'],gameplayVerified=False)
a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('PASS total',sum(map(len,checks.values())),flush=True)
