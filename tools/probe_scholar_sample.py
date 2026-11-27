"""Execute Scholar sample deduplication, reward grants and fixed rune awards.

Explicit resolved targets enter actual native predicate and tree/counter blocks.
The real effect selection, self grants, reward aggregation and player award
conversion execute; the terminal resource write is recorded, not persisted.
"""
import argparse,itertools,json,struct
from pathlib import Path
from native_effect_runtime import BASE,OBJ,STACK,STOP,Inputs,Chain,sha
from native_ailment_runtime import Ailment
from unicorn.x86_const import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted);inputs=x
raw=a.extracted.with_suffix('.AttachEffectParam.param').read_bytes();rows=Inputs.table(raw,0x44)
assert sha(raw)=='ae8128ed510a532d0fa7cb56fa9c86e4a44c9d815dd4ee01c05821d5f50a9827'
assert sha(x.param)=='07ec636c5565d4551efeb53e6f08bc633b2aa4f2129f13c61b0638d69b1bc176'
assert len(rows)==struct.unpack_from('<H',raw,10)[0]
attach=x.x['tables']['AttachEffectParam']['7036500'];r=x.spells['7036500'];leaf=x.spells['7036501']
assert attach['passiveSpEffectId_1']==7036500 and attach['exclusivityId']==-1
assert all(attach[k]==-1 for k in ('passiveSpEffectId_2','passiveSpEffectId_3','permanentSpEffectId'))
assert (r['stateInfo'],r['spCategory'],r['effectEndurance'],r['analyzeAcquire_effectId'])==(2125,20,-1,7036501)
assert struct.unpack_from('<i',x.rows[7036500],0x3ec)[0]==7036501
assert (leaf['spCategory'],leaf['soul'],leaf['effectEndurance'])==(10,1300,0)
assert x.pe.get_data(0x6713e6,18).hex()=='4c8b0f4533c08bd0488bcf41ff91d0050000'
assert struct.unpack('<Q',x.pe.get_data(0x2c307f8+0x5d0,8))[0]==BASE+0x668300
MAN=OBJ+0x8000;SELECT_OUT=OBJ+0x9000;BITS=OBJ+0x9100
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
  self.invoke(0x4fea30,[MAN,SELECT_OUT]);bits=int.from_bytes(self.u.mem_read(BITS,20),'little');return [i for i in range(144) if bits>>i&1]

class Damage(Ailment):
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

TARGET,PACKET,WRAPPER,ACTOR,OUT=OBJ+0x80000,OBJ+0x81000,OBJ+0x82000,OBJ+0x82100,OBJ+0x83000
class Counter(Damage):
 def __init__(self):
  self.stopAt=None;super().__init__();self.u.mem_map(TARGET,0x10000)
  self.q(TARGET+0x10,ACTOR);self.q(ACTOR,OBJ+0x6200);self.q(ACTOR+0x190,TARGET);self.q(WRAPPER+8,ACTOR)
 def hook(self,u,address,size,user):
  pc=address-BASE
  if pc==self.stopAt or self.stopAt==0x43a696 and pc==0x43a72b:u.reg_write(UC_X86_REG_RIP,STOP)
  elif pc==0x3d4180:pass
  else:super().hook(u,address,size,user)
MAP,HEAD=OBJ+0x84000,OBJ+0x84100
class Samples(Counter):
 def __init__(self):
  super().__init__();self.nextTree=OBJ+0x87000
  self.q(WRAPPER+8,OBJ+0x6000);self.q(WRAPPER+0x38,MAP)
  self.q(MAP,OBJ+0x85000);self.q(OBJ+0x85000,OBJ+0x85100);self.q(OBJ+0x85150,STOP+0xa00)
  self.q(MAP+8,HEAD)
  for offset in (0,8,0x10):self.q(HEAD+offset,HEAD)
  self.u.mem_write(HEAD+0x18,b'\1\1')
 def hook(self,u,address,size,user):
  if address==STOP+0xa00:
   assert u.reg_read(UC_X86_REG_RDX)==32 and u.reg_read(UC_X86_REG_R8)==8
   self.nextTree+=32;u.reg_write(UC_X86_REG_RAX,self.nextTree)
   sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  else:super().hook(u,address,size,user)
 def collect(self,key,count=0):
  self.u.mem_write(ACTOR+0x1b0,struct.pack('<I',key))
  for reg,v in ((UC_X86_REG_R13,WRAPPER),(UC_X86_REG_R12,count),(UC_X86_REG_RSI,ACTOR),(UC_X86_REG_RDI,0),(UC_X86_REG_RBP,OUT)):self.u.reg_write(reg,v)
  self.stopAt=0x3edf18;self.invoke(0x3edead,[]);self.stopAt=None
  return self.u.reg_read(UC_X86_REG_R12)&255
 def grant_samples(self,count):
  self.u.reg_write(UC_X86_REG_R13,WRAPPER);self.u.reg_write(UC_X86_REG_R12,count)
  self.stopAt=0x3ee10b;self.invoke(0x3ee0ca,[]);self.stopAt=None
  out=[]
  for _ in range(4):self.qualify();self.update(1/60);out.append(self.invoke(0x505af0,[OBJ]))
  return out
class Award(Samples):
 def __init__(self):
  super().__init__();self.writes=[];self.q(OBJ+0x65a0,OBJ+0x88000);self.q(OBJ+0x67d0,BASE+0x668300)
 def hook(self,u,address,size,user):
  if address-BASE==0x2098c0:
   assert u.reg_read(UC_X86_REG_RCX)==OBJ+0x88000
   self.writes.append(u.reg_read(UC_X86_REG_RDX)&0xffffffff)
   u.reg_write(UC_X86_REG_RAX,1);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  else:super().hook(u,address,size,user)
 def fixed(self):
  self.writes=[];self.u.reg_write(UC_X86_REG_RDI,OBJ+0x6000)
  self.stopAt=0x6713f8;self.invoke(0x6713d6,[]);self.stopAt=None
  return self.writes[:]
 def reward(self,count):
  self.u.reg_write(UC_X86_REG_R13,WRAPPER);self.u.reg_write(UC_X86_REG_R12,count)
  self.stopAt=0x3ee10b;self.invoke(0x3ee0ca,[]);self.stopAt=None
  packets=[]
  for _ in range(4):self.qualify();self.update(1/60);packets.append(self.fixed())
  return packets

checks={k:[] for k in ('selection','deduplication','eligibility','awards','disabled')};stubs=set()
def record(key,c,**row):checks[key].append(row);stubs.update(c.stubs)
def start(copies,other=None):
 c=Award()
 for _ in range(copies):c.grant(7036500)
 if other:c.grant(other)
 c.qualify();c.update(0);return c
for copies,hero in itertools.product((1,2,3,6),range(11)):
 c=Selection([[7036500]]*copies,hero);bits=c.select();selected=[i for i in range(copies) if i*6 in bits]
 assert selected==(list(range(copies)) if hero in (0,9) else [])
 c.invoke(0xe6e150,[OBJ+0x9200,7036500]);decoded=[c.invoke(0xe6e3b0,[OBJ+0x9200,n])&0xffffffff for n in range(3)]
 assert decoded==[7036500,0xffffffff,0xffffffff]
 v=start(len(selected));count=v.collect(100);values=v.reward(count);assert values==([[1300],[],[],[]] if selected else [[],[],[],[]])
 stubs.update(v.stubs);record('selection',c,copies=copies,hero=hero,selected=selected,decoded=decoded,awards=values)
print('PASS selection',len(checks['selection']),flush=True)
for copies in (0,1,3):
 c=start(copies);seen=set()
 for keys in ([100],[100],[200,300,100],[300,200],[65535,0,65536],[100,400,500,600]):
  count=0;expected=0
  for key in keys:
   count=c.collect(key,count)
   if key&65535 not in seen:seen.add(key&65535);expected+=1
  assert count==expected
  values=c.reward(count);assert sum(sum(v) for v in values)==expected*1300*bool(copies)
  size=struct.unpack('<Q',c.u.mem_read(MAP+0x10,8))[0];assert size==len(seen)
  record('deduplication',c,copies=copies,keys=keys,newSamples=count,recordCount=size,awards=values)
for copies,kind,flags in itertools.product((0,1,3),(0,1,6,77),(0,128)):
 c=start(copies);c.u.mem_write(OBJ+0x6074,b'\6');c.u.mem_write(ACTOR+0x74,bytes([kind]));c.u.mem_write(ACTOR+0x1f8,bytes([flags]));c.u.mem_write(ACTOR+0x1b0,struct.pack('<I',100))
 for reg,v in ((UC_X86_REG_R13,WRAPPER),(UC_X86_REG_R12,0),(UC_X86_REG_RSI,ACTOR),(UC_X86_REG_RBP,OUT)):c.u.reg_write(reg,v)
 c.stopAt=0x3edf18;c.invoke(0x3eddf6,[]);c.stopAt=None
 count=c.u.reg_read(UC_X86_REG_R12)&255;assert count==int(kind==1 and flags==0)
 values=c.reward(count);assert sum(sum(v) for v in values)==count*1300*bool(copies)
 record('eligibility',c,copies=copies,targetKind=kind,targetFlags=flags,newSamples=count,awards=values)
for copies,modifier in itertools.product((0,1,3),(None,6840000,311100)):
 c=start(copies,modifier)
 for keys in ([100,200,100],[100,300],[300,200]):
  count=0
  for key in keys:count=c.collect(key,count)
  values=c.reward(count);assert sum(sum(v) for v in values)==count*1300*bool(copies)
  record('awards',c,copies=copies,modifier=modifier,keys=keys,newSamples=count,awards=values)
for mask in (1,2,0x40000,0x80000000):
 c=start(3);ptr=struct.unpack('<Q',c.u.mem_read(OBJ+8,8))[0];c.u.mem_write(ptr+0x68,struct.pack('<I',mask))
 count=c.collect(100);values=c.reward(count);assert values==[[],[],[],[]]
 record('disabled',c,mask=mask,newSamples=count,awards=values)
print('PASS checks',{k:len(v) for k,v in checks.items()},flush=True)
out=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),attachParamSha256=sha(raw),
 effect=7036500,root=7036500,leaf=7036501,runesPerSample=1300,checks=checks,
 native=dict(selection='4FEA30 → E6E150 → E6E3B0',target='3EDDF6..3EDF18 → 52C990/52CB00 → 3D1B30',identity='3CED70',deduplication='3EDEAD..3EDF18 → 3EB550 → 3F1D10/3F10B0',grant='3EE0CA..3EE10B → 505C80 → 3C7FD0 → 3C80A0 → 3DB410',fixedAward='6713D6..6713F8 → 505AF0 → 668300'),
 stubs=sorted(stubs|{'Explicit resolved target, actor+1B0 identity, initial empty sample tree and caller registers; full scan collection not executed.',
 'Tree allocator virtual+50 supplies aligned32-byte nodes; native search, insert and balancing execute.',
 'Actor virtual+118 is false; faction/identity comparisons execute on explicit actor fields.',
 '2098C0 terminal rune-resource write recorder; final caps and persistence not executed.'}),
 limitations=['No complete skill target scan, range, animation scheduling, target identity lifecycle or reset of the sample record.',
 'Actor+1B0 low16bits form the deduplication key; no unsupported identification as enemy species or unique enemy instance.',
 'No complete game session, DLL runtime patches, multiplayer, death, reload or equipment rebuild.',
 'Sample count is a byte in the native caller; only small valid counts exercised, not all extreme or capacity cases.'],gameplayVerified=False)
a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('PASS total',sum(map(len,checks.values())),flush=True)
