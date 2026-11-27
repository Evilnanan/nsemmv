"""Trace Recluse cocktail amplification, FP-cost rates and duplicate maintenance.

This probe runs native equipment selection, grants, timers, attack filters and
FP-rate getters. Full casting/collision and the separate cocktail-specific
secondary effects are outside these numeric/stacking claims.
"""
import argparse,itertools,json,math,struct
from pathlib import Path
from native_effect_runtime import BASE,OBJ,STOP,Chain,Inputs,sha
from native_ailment_runtime import Ailment
from unicorn.x86_const import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted);inputs=x;ts=x.x['tables']
hashes={'AttachEffectParam':'ae8128ed510a532d0fa7cb56fa9c86e4a44c9d815dd4ee01c05821d5f50a9827','AtkParam_Pc':'1ec1893420053cbfb06e3efb269ade4ba9d6a617d1d3dbb370e837847be05676','Magic':'17742eeafe4fade863f3a7ee5f7ff483bd4897f765802fe4a1954dfa8107b63e'}
raws={name:a.extracted.with_suffix('.'+name+'.param').read_bytes() for name in hashes}
for name,raw in raws.items():assert sha(raw)==hashes[name]
assert sha(x.param)=='07ec636c5565d4551efeb53e6f08bc633b2aa4f2129f13c61b0638d69b1bc176'
rows=Inputs.table(raws['AttachEffectParam'],0x44);attacks=Inputs.table(raws['AtkParam_Pc'],0x1d0);magicrows=Inputs.table(raws['Magic'],0xac)
for id in (7034200,7034201):
 r=ts['AttachEffectParam'][str(id)];assert r['passiveSpEffectId_1']==9200006 and r['exclusivityId']==-1
 assert [k for k,v in r.items() if k.startswith('allow') and v]==['allowRecluse']
for id,cycle,replace,duration,period in [(9200006,9200007,-1,-1,.2),(9200007,7034201,7034200,.11,.1)]:
 r=x.spells[str(id)];assert (r['cycleOccurrenceSpEffectId'],r['replaceSpEffectId'],r['spCategory'])==(cycle,replace,20)
 assert math.isclose(r['effectEndurance'],duration,abs_tol=1e-7) and math.isclose(r['motionInterval'],period,abs_tol=1e-7)
for id,state in ((7034200,2047),(7034201,71)):
 r=x.spells[str(id)];assert (r['spCategory'],r['effectEndurance'],r['stateInfo'])==(20,3,state)
assert all(math.isclose(x.spells['7034200'][k+'ConsumptionRate'],1.3,abs_tol=1e-6) for k in ('magic','miracle','shaman'))
assert all(math.isclose(x.spells['7034201'][k+'AttackRate'],1.35,abs_tol=1e-6) for k in ('physics','magic','fire','thunder','dark'))
assert x.spells['7034201']['magicSubCategoryChange1']==16
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

class Attack(Actor):
 def hook(self,u,address,size,user):
  if address-BASE==0xe6d630:
   id=u.reg_read(UC_X86_REG_R8)&0xffffffff;assert u.reg_read(UC_X86_REG_RDX)==1
   wrapper=u.reg_read(UC_X86_REG_RCX);u.mem_write(OBJ+0xa800,attacks[id]);u.mem_write(wrapper,struct.pack('<iii4xQ',id,0,1,OBJ+0xa800))
   sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8);return
  super().hook(u,address,size,user)
def attack(c,weapon,attached,kind):
 out=OBJ+0x8400;c.u.mem_write(out,bytes(0x300));c.u.mem_write(out+8,struct.pack('<iiB',2,1,kind))
 c.u.mem_write(OBJ+0xa800,attacks[2]);c.q(OBJ+0xb010,OBJ+0xa800);c.invoke(0xe6d530,[OBJ+0xb000,out+0x14])
 c.u.mem_write(out+0xe8,struct.pack('<i',weapon));c.invoke(0x502830,[OBJ,out,weapon,attached])
 return dict(points=[struct.unpack('<f',c.u.mem_read(out+off,4))[0] for off in (0x48,0x5c,0x60,0x64,0x68)])

class Mixed(Attack):
 def cost(self):
  values=[]
  for rva in (0x507310,0x507410,0x5081e0,0x5061b0):
   self.invoke(rva,[OBJ]);values.append(struct.unpack('<f',(self.u.reg_read(UC_X86_REG_XMM0)&0xffffffff).to_bytes(4,'little'))[0])
  return values
 def rates(self,id,kind=0):
  out=OBJ+0x8400;self.u.mem_write(out,bytes(0x300));self.u.mem_write(out+8,struct.pack('<iiB',id,1,kind))
  self.u.mem_write(OBJ+0xa800,attacks[id]);self.q(OBJ+0xb010,OBJ+0xa800);self.invoke(0xe6d530,[OBJ+0xb000,out+0x14])
  self.invoke(0x502830,[OBJ,out,-1,-1])
  return [struct.unpack('<f',self.u.mem_read(out+off,4))[0] for off in (0x90,0xa4,0xa8,0xac,0xb0)]

checks={k:[] for k in ('selection','maintenance','filters','kinds','mixed','disabled','extension','removal')};stubs=set()
def record(key,c,**values):checks[key].append(values);stubs.update(c.stubs)
def start(copies=1,fps=60):
 c=Mixed()
 for _ in range(copies):c.grant(9200006)
 for _ in range(fps):c.qualify();c.update(1/fps)
 return c
def close(values,expected):assert all(math.isclose(v,e,abs_tol=2e-6) for v,e in zip(values,expected)),(values,expected)
tags={int(id):sorted({r['subCategory'+str(i)] for i in range(1,6)}-{0}) for id,r in ts['AtkParam_Pc'].items()}
representatives={}
for id,values in tags.items():representatives.setdefault(tuple(values),id)
assert len(representatives)==216
magic_bindings=[]
for id,r in ts['Magic'].items():
 if 16 not in (r['subCategory1'],r['subCategory2']):continue
 assert magicrows[int(id)][0x28]==r['spEffectCategory']==3
 magic_bindings.append(dict(magic=int(id),motion=r['refType'],kind=r['spEffectCategory'],tags=[r['subCategory1'],r['subCategory2']]))
assert len(magic_bindings)==14
for slots,hero in itertools.product(([[7034200]],[[7034201]],[[7034200],[7034201],[7034200,7034201]]),range(11)):
 c=Selection(slots,hero);chosen=c.select();roots=[]
 for i,slot in enumerate(slots):
  for j,id in enumerate(slot):
   if i*6+j not in chosen:continue
   c.invoke(0xe6e150,[OBJ+0x9200,id]);roots.append(c.invoke(0xe6e3b0,[OBJ+0x9200,0])&0xffffffff)
 assert roots==([9200006]*sum(map(len,slots)) if hero in (0,7) else [])
 record('selection',c,slots=slots,hero=hero,selected=chosen,roots=roots)
for copies,fps in itertools.product((0,1,3,6),(30,60,120)):
 c=start(copies,fps);costs=c.cost();close(costs,[1.3 if copies else 1]*3+[1])
 close(c.rates(210741000,3),[1.35 if copies else 1]*5);close(c.rates(2,3),[1]*5)
 assert sum(n['id']==9200006 for n in c.nodes())==bool(copies)
 assert all(sum(n['id']==leaf for n in c.nodes())==bool(copies) for leaf in (7034200,7034201))
 record('maintenance',c,copies=copies,fps=fps,costs=costs,nodes=c.nodes())
for copies in (0,1,3,6):
 c=start(copies)
 for values,id in representatives.items():
  rates=c.rates(id,3);close(rates,[1.35 if copies and 16 in values else 1]*5)
  record('filters',c,copies=copies,attack=id,tags=values,rates=rates)
 for kind in range(13):
  rates=c.rates(210741000,kind);close(rates,[1.35 if copies and kind in (3,4,10) else 1]*5)
  record('kinds',c,copies=copies,kind=kind,rates=rates)
for copies,extra in itertools.product((0,1,3),(330800,7610700,7610701,7610702,8330600,8330602)):
 c=start(copies);c.grant(extra);c.qualify();c.update(0);costs=c.cost()
 expected=[x.spells[str(extra)][field]*(1.3 if copies and i<3 else 1) for i,field in enumerate(('magicConsumptionRate','miracleConsumptionRate','shamanConsumptionRate','artsConsumptionRate'))]
 close(costs,expected);record('mixed',c,copies=copies,extra=extra,costs=costs)
for leaf,mask in itertools.product((7034200,7034201),(1,2,0x40000,0x80000000)):
 c=start();ptr=struct.unpack('<Q',c.u.mem_read(OBJ+8,8))[0]
 while ptr:
  if struct.unpack('<i',c.u.mem_read(ptr+8,4))[0]==leaf:c.u.mem_write(ptr+0x68,struct.pack('<I',mask))
  ptr=struct.unpack('<Q',c.u.mem_read(ptr+0x38,8))[0]
 costs=c.cost();rates=c.rates(210741000,3);close(costs,([1]*4 if leaf==7034200 else [1.3]*3+[1]));close(rates,[1 if leaf==7034201 else 1.35]*5)
 record('disabled',c,leaf=leaf,mask=mask,costs=costs,rates=rates)
for leaf,extension in itertools.product((7034200,7034201),(None,7006400,8330500)):
 c=Mixed()
 if extension:c.grant(extension)
 c.grant(leaf);c.qualify();c.update(1);node=next(n for n in c.nodes() if n['id']==leaf);assert node['lifetime']==2
 record('extension',c,leaf=leaf,extension=extension,node=node)
for copies,fps in itertools.product((1,3),(30,60,120)):
 c=start(copies,fps);c.invoke(0x504e80,[OBJ,9200006]);samples=[]
 for frame in range(4*fps):
  c.qualify();c.update(1/fps)
  if frame in (0,2*fps-1,3*fps-1,4*fps-1):samples.append(dict(frame=frame,nodes=c.nodes(),costs=c.cost(),rates=c.rates(210741000,3)))
 assert not c.nodes();close(c.cost(),[1]*4);close(c.rates(210741000,3),[1]*5)
 record('removal',c,copies=copies,fps=fps,samples=samples)
counts={k:len(v) for k,v in checks.items()}
assert counts==dict(selection=33,maintenance=12,filters=864,kinds=52,mixed=18,disabled=8,extension=6,removal=6)
a.output.write_text(json.dumps(dict(schema=1,effects=[7034200,7034201],root=9200006,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),paramHashes=hashes,magicBindings=magic_bindings,checks=checks,native=dict(selection='4FEA30 → E6E150 → E6E3B0',grant='3C7FD0 → 3C80A0 → 3DB410',upkeep='50D060 → 5057D0 → 50ACD0',attack='E6D530 → 502830',cost=['507310','507410','5081E0','5061B0']),stubs=sorted(stubs|{'Actual Magic kind and attack tags are supplied to the original consumers; complete cast/bullet construction and resource deduction are not simulated.','Direct root removal is an explicit input, not a complete unequip/death/reload workflow.','Secondary cocktail effects, animation reachability, collision, DLL overrides and multiplayer remain separate research questions.'}),gameplayVerified=False),ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(counts.values()),counts)
