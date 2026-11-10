"""Check critical-attack stacking after actual equipment selection.

Selection/Values fixtures follow probe_equipped_exclusivity.py. Native selection,
root insertion and attack multiplication execute unchanged. The critical attack
context flag is supplied explicitly; full scene combat is not simulated.
"""
import argparse,json,struct,itertools,math
from pathlib import Path
from native_effect_runtime import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted)
raw=a.extracted.with_suffix('.AttachEffectParam.param').read_bytes();rows=Inputs.table(raw,0x44)
atkraw=a.extracted.with_suffix('.AtkParam_Pc.param').read_bytes();atkrows=Inputs.table(atkraw,0x1d0)
MAN=OBJ+0x8000;OUT=OBJ+0x9000;BITS=OBJ+0x9100
class Selection(Chain):
 def __init__(self,slots,hero=1):
  super().__init__(x);self.slots=slots;self.hero=hero;self.cache={};self.q(OBJ+0x7118,STOP+0x900)
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
   u.mem_write(instance+0x18,struct.pack('<3i',*(effects+[-1]*3)[:3]));u.mem_write(ptr,bytes(24));self.q(ptr+8,instance);u.mem_write(ptr+0x10,struct.pack('<I',0x80000000|2000100));ret(ptr)
  elif pc==0x69e5a0:ret()
  elif pc==0xe6e430:
   ptr=u.reg_read(UC_X86_REG_RCX);id=u.reg_read(UC_X86_REG_RDX)&0xffffffff
   if id in rows and id not in self.cache:
    self.cache[id]=OBJ+0x10000+len(self.cache)*0x100;u.mem_write(self.cache[id],rows[id])
   self.q(ptr,self.cache.get(id,0));u.mem_write(ptr+8,struct.pack('<I',id));ret(ptr)
  else:super().hook(u,address,size,user)
 def select(self):
  self.invoke(0x4fea30,[MAN,OUT]);bits=int.from_bytes(self.u.mem_read(BITS,20),'little');return [i for i in range(144) if bits>>i&1]
class Values(Chain):
 def __init__(self):super().__init__(x);self.q(OBJ+0x6390,STOP+0x904)
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if address==STOP+0x904:ret()
  elif pc==0xe6d630:
   id=u.reg_read(UC_X86_REG_R8)&0xffffffff;assert u.reg_read(UC_X86_REG_RDX)==1
   wrapper=u.reg_read(UC_X86_REG_RCX);u.mem_write(OBJ+0xa800,atkrows[id]);u.mem_write(wrapper,struct.pack('<iii4xQ',id,0,1,OBJ+0xa800));ret()
  else:super().hook(u,address,size,user)
 def stats(self):
  self.invoke(0x502300,[OBJ,OBJ+0x800]);return list(struct.unpack('<8i',self.u.mem_read(OBJ+0x800,32)))
 def attackrow(self,id,kind=0):
  self.u.mem_write(OBJ+0xa800,atkrows[id]);self.q(OBJ+0xb010,OBJ+0xa800);self.invoke(0xe6d530,[OBJ+0xb000,OBJ+0x814]);self.u.mem_write(OBJ+0x808,struct.pack('<iiB',id,1,kind));self.invoke(0x502830,[OBJ,OBJ+0x800,-1,-1]);return [struct.unpack('<f',self.u.mem_read(OBJ+0x800+o,4))[0] for o in(0x90,0xa4,0xa8,0xac,0xb0)]
def bridge(slots,hero=1):
 c=Selection(slots,hero);bits=c.select();accepted=[id for i,row in enumerate(slots) for n,id in enumerate(row) if i*6+n in bits]
 roots=[]
 for id in accepted:
  ptr=OBJ+0x9200;c.invoke(0xe6e150,[ptr,id])
  for i in range(3):
   root=c.invoke(0xe6e3b0,[ptr,i])&0xffffffff
   if root!=0xffffffff:roots.append(root)
 v=Values()
 for root in roots:v.insert(root)
 v.qualify();v.update(0)
 return c,v,accepted,roots

checks=[];stubs=set()
cases=[[],[7040200],[7040200]*2,[7040200]*3,[7040200]*6,
       [7040201],[7040201]*2,[7040201]*6,[7040200,7040201],
       [7040201,7040200],[7040200]*2+[7040201],[7040201,7040200,7040201]]
for ids,critical,disabled in itertools.product(cases,(False,True),(False,True)):
 c,v,accepted,roots=bridge([[id] for id in ids])
 assert accepted.count(7040200)==ids.count(7040200)
 assert accepted.count(7040201)==min(1,ids.count(7040201))
 assert [row['id'] for row in v.nodes()]==roots==accepted
 # 50F2A0 copies attack +10D into eligibility +24; 511010 tests this
 # when SpEffect +164 bit3 (throwAttackParamChange) is set.
 v.u.mem_write(OBJ+0x90d,bytes([critical]))
 if disabled:
  node=struct.unpack('<Q',v.u.mem_read(OBJ+8,8))[0]
  while node:
   v.u.mem_write(node+0x68,struct.pack('<I',0x800c0003))
   node=struct.unpack('<Q',v.u.mem_read(node+0x38,8))[0]
 for kind in range(13):
  values=v.attackrow(0,kind)
  expected=1.0
  if critical and not disabled and kind not in (3,4,5,10):
   for root in roots:expected*=x.spells[str(root)]['physicsAttackRate']
  assert all(math.isclose(value,expected,rel_tol=1e-6) for value in values),(ids,critical,disabled,kind,values,expected)
  checks.append(dict(effects=ids,accepted=accepted,critical=critical,disabled=disabled,kind=kind,values=values))
 stubs.update(c.stubs);stubs.update(v.stubs)
output=dict(schema=1,regulationSha256=x.x['hashes']['regulation.bin'],exeSha256=sha(x.raw),
 paramSha256=sha(x.param),attachParamSha256=sha(raw),atkParamSha256=sha(atkraw),
 routines={'selection':'4FEA30','roots':'E6E3B0','insert':'50D060','attack':'502830','context':'50F2A0','eligibility':'511010'},
 families=[dict(effect=id,root=id,exclusive=x.x['tables']['AttachEffectParam'][str(id)]['exclusivityId'],rate=x.spells[str(id)]['physicsAttackRate']) for id in (7040200,7040201)],
 checks=checks,stubs=sorted(stubs|{'same inventory, allocation, parameter and mode fixtures as probe_equipped_exclusivity.py',
 'explicit attack +10D critical flag; no complete Throw selection, scene damage, multiplayer or gameplay',
 'selected roots bridge to a separate effect container; only one six-relic equipment group'}),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',len(checks),'critical attack checks')
