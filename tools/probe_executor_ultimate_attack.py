"""Verify Executor ultimate attack multiplier selection and duplicate handling.

This executes the original equip selector, effect container and attack consumer.
It does not establish transformed c0010 action reachability or owner transfer.
"""
import argparse,itertools,json,math,struct
from pathlib import Path
from native_effect_runtime import BASE,OBJ,STOP,Chain,Inputs,sha
from unicorn.x86_const import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted);inputs=x;t=x.x['tables']
raws={name:a.extracted.with_suffix('.'+name+'.param').read_bytes() for name in ('AttachEffectParam','AtkParam_Pc')}
expected_hashes={'AttachEffectParam':'ae8128ed510a532d0fa7cb56fa9c86e4a44c9d815dd4ee01c05821d5f50a9827','AtkParam_Pc':'1ec1893420053cbfb06e3efb269ade4ba9d6a617d1d3dbb370e837847be05676'}
assert sha(x.param)=='07ec636c5565d4551efeb53e6f08bc633b2aa4f2129f13c61b0638d69b1bc176'
for name,b in raws.items():assert sha(b)==expected_hashes[name]
rows=Inputs.table(raws['AttachEffectParam'],0x44);atk=Inputs.table(raws['AtkParam_Pc'],0x1d0)
for name,table in (('AttachEffectParam',rows),('AtkParam_Pc',atk)):
 assert len(table)==struct.unpack_from('<H',raws[name],10)[0],name
EFFECTS=(7034900,7034901);ROOT=7501200;TAG=123
r=x.spells[str(ROOT)];RATE=r['physicsAttackRate']
for effect in EFFECTS:
 attach=t['AttachEffectParam'][str(effect)]
 assert [attach['passiveSpEffectId_'+str(n)] for n in (1,2,3)]==[ROOT,-1,-1]
 assert attach['exclusivityId']==attach['permanentSpEffectId']==-1
 assert {k:v for k,v in attach.items() if k.startswith('allow')}=={k:int(k=='allowExecutor') for k in attach if k.startswith('allow')}
assert (r['spCategory'],r['stateInfo'],r['effectEndurance'],r['motionInterval'])==(20,0,-1,0)
assert [r['magicSubCategoryChange'+str(n)] for n in (1,2,3)]==[TAG,0,0]
assert all(r[k]==-1 for k in ('cycleOccurrenceSpEffectId','replaceSpEffectId','atkOccurrenceSpEffectId'))
assert all(r[k]==0 for k in ('invocationConditionsStateChange1','invocationConditionsStateChange2','invocationConditionsStateChange3'))
assert all(r[k+'AttackRate']==RATE for k in ('physics','magic','fire','thunder','dark')) and math.isclose(RATE,1.2,rel_tol=1e-6)
assert sum(struct.unpack_from('<i',x.param,0x40+i*24)[0]==ROOT for i in range(struct.unpack_from('<H',x.param,10)[0]))==1
tags={int(id):sorted({r['subCategory'+str(i)] for i in range(1,6)}-{0}) for id,r in t['AtkParam_Pc'].items()}
for id,ts in tags.items():assert ts==sorted(set(atk[id][o] for o in (0x4e,0x4f,0x1c8,0x1c9,0x1ca))-{0})
positives=sorted(id for id,ts in tags.items() if TAG in ts);assert len(positives)==59
representatives={}
for id,ts in tags.items():representatives.setdefault(tuple(ts),id)
assert len(representatives)==216
samples=(positives[0],next(id for id,ts in tags.items() if 250 in ts and TAG not in ts))
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

class Attack(Chain):
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

checks={key:[] for key in ('selection','filters','mixed','kinds','disabled','removal','lifetime')};stubs=set()
def record(key,c,**row):checks[key].append(row);stubs.update(c.stubs)
def verify(c,copies,attack,kind=1):
 values=c.row(attack,kind);expected=RATE if copies and TAG in tags[attack] and kind not in (3,4,5,10) else 1
 assert all(math.isclose(n,expected,rel_tol=3e-6) for n in values),(copies,attack,kind,values,expected)
 return values
def prepare(copies):
 c=Attack(x)
 for _ in range(copies):c.insert(ROOT)
 c.qualify();c.update(0);assert [n['id'] for n in c.nodes()]==([ROOT] if copies else [])
 return c
for effect,copies,hero in itertools.product(EFFECTS,(1,2,3,6),range(11)):
 c=Selection([[effect]]*copies,hero);bits=c.select();allowed=hero in (0,8)
 assert all((i*6 in bits)==allowed for i in range(copies)),(effect,copies,hero,bits)
 selected=[]
 for i in range(copies):
  if i*6 not in bits:continue
  c.invoke(0xe6e150,[OBJ+0x9200,effect]);selected.append(c.invoke(0xe6e3b0,[OBJ+0x9200,0])&0xffffffff)
 assert selected==([ROOT]*copies if allowed else [])
 v=prepare(len(selected));values={id:verify(v,len(selected),id) for id in samples};stubs.update(v.stubs)
 record('selection',c,effect=effect,copies=copies,hero=hero,selectionBits=bits,selected=selected,instances=len(v.nodes()),values=values)
print('PASS selection',len(checks['selection']),flush=True)
for copies in (0,1,2,3,6):
 c=prepare(copies)
 for attack in sorted(set(positives)|set(representatives.values())):
  record('filters',c,copies=copies,attack=attack,values=verify(c,copies,attack))
print('PASS filters',len(checks['filters']),flush=True)
for first,second in itertools.product(range(4),repeat=2):
 effects=[EFFECTS[0]]*first+[EFFECTS[1]]*second
 c=Selection([[e] for e in effects],8);bits=c.select();assert all(i*6 in bits for i in range(len(effects)))
 selected=[]
 for e in effects:
  c.invoke(0xe6e150,[OBJ+0x9200,e]);selected.append(c.invoke(0xe6e3b0,[OBJ+0x9200,0])&0xffffffff)
 assert selected==[ROOT]*len(effects)
 v=prepare(len(selected));stubs.update(v.stubs)
 record('mixed',c,first=first,second=second,selected=selected,instances=len(v.nodes()),values={id:verify(v,len(selected),id) for id in samples})
print('PASS mixed',len(checks['mixed']),flush=True)
for copies in (0,1,3):
 c=prepare(copies)
 for attack,kind in itertools.product(samples,range(13)):
  record('kinds',c,copies=copies,attack=attack,kind=kind,values=verify(c,copies,attack,kind))
for copies,mask in itertools.product((1,3),(1,2,0x40000,0x80000000)):
 c=prepare(copies);ptr=struct.unpack('<Q',c.u.mem_read(OBJ+8,8))[0];c.u.mem_write(ptr+0x68,struct.pack('<I',mask))
 for attack in samples:record('disabled',c,copies=copies,mask=hex(mask),attack=attack,values=verify(c,0,attack))
print('PASS kinds/disabled',len(checks['kinds']),len(checks['disabled']),flush=True)
for copies in (1,2,3,6):
 c=prepare(copies);c.invoke(0x505280,[OBJ,0]);c.qualify();c.update(0);assert c.nodes()==[]
 record('removal',c,copies=copies,phase='removed',values={id:verify(c,0,id) for id in samples})
 c.insert(ROOT);c.qualify();c.update(0);assert len(c.nodes())==1
 record('removal',c,copies=copies,phase='reinserted',values={id:verify(c,1,id) for id in samples})
for copies in (1,3,6):
 c=prepare(copies)
 for elapsed in (1,40,300):
  c.qualify();c.update(elapsed);assert len(c.nodes())==1
  record('lifetime',c,copies=copies,stepSeconds=elapsed,values={id:verify(c,copies,id) for id in samples})
print('PASS removal/lifetime',len(checks['removal']),len(checks['lifetime']),flush=True)
out=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),paramHashes=expected_hashes,
 effects=list(EFFECTS),root=ROOT,tag=TAG,rate=RATE,category=20,positiveAttacks=positives,tagSets=len(representatives),
 attacks={id:tags[id] for id in sorted(set(positives)|set(representatives.values()))},checks=checks,
 native=dict(selection='4FEA30 → E6E150 → E6E3B0',insert='50D060',qualification='5057D0 → 50ACD0',tags='E6D530 → E6D3E0',attack='502830 → 511010',remove='505280'),
 stubs=sorted(stubs|{'E6D630 actual AtkParam_Pc lookup','explicit actor identity / allocation / inventory enumeration and notifications'}),
 limitations=['Only same-root duplicate handling and tagged native attack multipliers are established.',
 'c0010 animation/behavior binders are in absent data3; transformed attacks and owner-to-beast effect transfer remain unresolved.',
 'The 59 matching PC rows include other heroes: tag 123 is not a unique Executor identifier.',
 'No complete animation, collision, final HP write, DLL hooks, equipment rebuild, death, reload or multiplayer executed.'],gameplayVerified=False)
a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('PASS total',sum(map(len,checks.values())),flush=True)
