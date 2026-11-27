"""Verify local rune multipliers and the player award toggle using pinned code.

Actual equipment selection, insertion, eligibility, scalar aggregation, player
award conversion and fixed-effect rune packet block execute. Inventory, actor
identity and the terminal resource write are explicit fixtures, not gameplay.
"""
import argparse,itertools,json,math,struct
from pathlib import Path
from native_effect_runtime import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted)
raw=a.extracted.with_suffix('.AttachEffectParam.param').read_bytes();rows=Inputs.table(raw,0x44)
families=[]
for id,rate,category in ((311100,1.15,0),(6840000,.9,10),(8500000,1.1,10),(8852000,1.06,10),(8852050,1.09,10)):
 attach=x.x['tables']['AttachEffectParam'][str(id)];r=x.spells[str(id)]
 assert attach['passiveSpEffectId_1']==id and attach['exclusivityId']==-1
 assert all(attach[k]==-1 for k in ('passiveSpEffectId_2','passiveSpEffectId_3','permanentSpEffectId'))
 assert (r['spCategory'],r['stateInfo'],r['effectEndurance'],r['wepParamChange'])==(category,76,-1,0)
 assert all(r['invocationConditionsStateChange'+str(i)]==0 for i in (1,2,3))
 assert all(r[k]==-1 for k in ('cycleOccurrenceSpEffectId','replaceSpEffectId','atkOccurrenceSpEffectId'))
 assert math.isclose(r['soulRate'],rate,rel_tol=1e-6)
 assert struct.unpack_from('<f',x.rows[id],0xe0)[0]==r['soulRate']
 families.append(dict(effect=id,root=id,rate=r['soulRate'],category=category))
by_id={f['root']:f for f in families}
# RTTI identifies this table as PlayerIns, rather than inferring its type from
# an arbitrary pointer match. Slot +5D0 is the actual rune award method.
vtable=0x2c307f8
locator=struct.unpack('<Q',x.pe.get_data(vtable-8,8))[0]-BASE
rtti=struct.unpack('<6I',x.pe.get_data(locator,24));assert rtti[0]==1 and rtti[1:3]==(0,0)
assert x.pe.get_data(rtti[3]+16,200).split(b'\0')[0]==b'.?AVPlayerIns@CS@@'
assert struct.unpack('<Q',x.pe.get_data(vtable+0x5d0,8))[0]==BASE+0x668300
# Pin the per-effect fixed-rune packet callsite: multiplier flag is zero.
assert x.pe.get_data(0x6713e6,18).hex()=='4c8b0f4533c08bd0488bcf41ff91d0050000'
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

class Rune(Chain):
 def __init__(self,roots,disabled=False,player=True,purse=True):
  super().__init__(x);self.player=player;self.writes=[]
  self.q(OBJ+0x6190,OBJ);self.q(OBJ+0x65a0,OBJ+0xc000 if purse else 0)
  self.q(OBJ+0x6000,BASE+vtable)
  for id in roots:self.insert(id)
  self.qualify();self.update(0)
  if disabled:
   node=struct.unpack('<Q',self.u.mem_read(OBJ+8,8))[0]
   while node:
    self.u.mem_write(node+0x68,struct.pack('<I',0x800c0003))
    node=struct.unpack('<Q',self.u.mem_read(node+0x38,8))[0]
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v&0xffffffffffffffff);sp=u.reg_read(UC_X86_REG_RSP)
   u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if pc==0x3d4180:
   self.stubs.add('3D4180 explicit player identity');ret(int(self.player))
  elif pc==0x2098c0:
   assert u.reg_read(UC_X86_REG_RCX)==OBJ+0xc000
   self.writes.append(struct.unpack('<i',struct.pack('<I',u.reg_read(UC_X86_REG_RDX)&0xffffffff))[0])
   self.stubs.add('2098C0 terminal rune-resource write recorder; caps and persistence not executed');ret(1)
  elif pc==0x6713f8:
   self.stubs.add('6713D6..6713F8 isolated original fixed-rune packet block boundary');u.reg_write(UC_X86_REG_RIP,STOP)
  else:super().hook(u,address,size,user)
 def rate(self):
  self.invoke(0x508510,[OBJ]);return struct.unpack('<f',(self.u.reg_read(UC_X86_REG_XMM0)&0xffffffff).to_bytes(4,'little'))[0]
 def award(self,base,scale):
  self.writes=[];self.invoke(0x668300,[OBJ+0x6000,base,scale]);return self.writes.copy()
 def fixed(self):
  self.writes=[];self.u.reg_write(UC_X86_REG_RDI,OBJ+0x6000)
  self.invoke(0x6713d6,[]);return self.writes.copy()

def f32(v):return struct.unpack('<f',struct.pack('<f',v))[0]
def actual_roots(roots):
 out=[]
 for id in roots:
  if by_id.get(id,{}).get('category')==0 and id in out:continue
  out.append(id)
 return out
def expected(roots):
 v=1.
 for id in actual_roots(roots):v=f32(v*x.spells[str(id)]['soulRate'])
 return v
checks={k:[] for k in ('selection','multipliers','awards','disabled','fixed','identity')};stubs=set()
def record(kind,c,**row):checks[kind].append(row);stubs.update(c.stubs)
for f in families:
 for copies,hero in itertools.product((1,2,3,6),range(11)):
  effects=[f['effect']]*copies
  curse=f['effect']==6840000;position=3 if curse else 0
  slots=[[7000000,-1,-1,id] if curse else [id] for id in effects]
  c=Selection(slots,hero);bits=c.select();roots=[]
  for index,id in enumerate(effects):
   if index*6+position in bits:
    assert struct.unpack('<i',c.u.mem_read(OBJ+0xa000+index*0x80+0x18+position*4,4))[0]==id
    c.invoke(0xe6e150,[OBJ+0x9200,id]);roots.append(c.invoke(0xe6e3b0,[OBJ+0x9200,0])&0xffffffff)
  assert roots==effects
  record('selection',c,effects=effects,hero=hero,position=position,slots=slots,bits=bits,roots=roots)
cases=[]
for counts in itertools.product(range(3),repeat=len(families)):
 roots=[f['root'] for f,n in zip(families,counts) for _ in range(n)]
 # At most six relevant instances; synthetic inventory layout and parameter
 # selection do not assert that a combination can be drawn as a legal relic.
 if len(roots)<=6:cases.append(roots)
for f in families:
 for copies in (3,6):cases.append([f['root']]*copies)
for roots in cases:
 for reverse in (False,True):
  roots_order=list(reversed(roots)) if reverse else roots
  c=Rune(roots_order);rate=c.rate();want=expected(roots_order)
  assert rate==want and [n['id'] for n in c.nodes()]==actual_roots(roots_order)
  record('multipliers',c,roots=roots_order,rate=rate,nodes=c.nodes())
  for base,scale in itertools.product((1,3,100,101,999,10000),(0,1)):
   values=c.award(base,scale);wanted=int(f32(f32(base)*rate)) if scale else base
   assert values==[wanted],(roots_order,base,scale,rate,values,wanted)
   record('awards',c,roots=roots_order,base=base,scale=bool(scale),rate=rate,values=values)
# Mixing curse copies with the existing ten-stage tower/temple rune reward.
for stage,copies in itertools.product(range(1,11),range(7)):
 roots=[7069300+stage]+[6840000]*copies;c=Rune(roots);rate=c.rate();assert rate==expected(roots)
 record('multipliers',c,roots=roots,rate=rate,nodes=c.nodes())
for f in families:
 c=Rune([f['root']]*3,disabled=True);assert c.rate()==1 and c.award(101,1)==[101]
 record('disabled',c,root=f['root'],rate=c.rate(),values=c.writes)
# Fixed event rewards run their actual caller block with multiplier disabled,
# including the known critical-hit and Scholar-analysis flat-rune leaves.
for packets,copies in itertools.product(([],[7031901],[7036501],[7031901,7036501]),range(7)):
 roots=[6840000]*copies+([7031900] if 7031901 in packets else []);c=Rune(roots)
 for packet in packets:c.insert(packet)
 c.qualify();c.update(0);writes=c.fixed()
 wanted=sum(x.spells[str(id)]['soul'] for id in packets)
 assert writes==([wanted] if wanted else []),(roots,writes,wanted)
 record('fixed',c,copies=copies,packets=packets,values=writes)
for player,purse in itertools.product((False,True),repeat=2):
 c=Rune([6840000],player=player,purse=purse);writes=c.award(100,1)
 assert writes==([90] if player and purse else [])
 record('identity',c,player=player,purse=purse,values=writes)
output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),attachParamSha256=sha(raw),
 families=families,vtable=dict(rva=hex(vtable),type='PlayerIns',slot='5D0',award='668300'),checks=checks,
 native=dict(selection='4FEA30 → E6E150 → E6E3B0',lifecycle='50D060 → 5057D0 → 50ACD0',rate='508510',award='668300 → 2098C0',fixedPacket='6713D6 → 505AF0 → PlayerIns.vtable+5D0'),
 stubs=sorted(stubs|{'equipment six-slot inventory and allocation fixtures; curse occupies slot3 paired with positive7000000; roll legality not asserted; rune award base and multiplier toggle are explicit inputs',
 'enemy/reward/item/script callsites beyond fixed-effect block are not enumerated',
 'team aura source/recipient propagation, terminal rune caps, death/drop/recovery/save and multiplayer are not executed'}),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',{k:len(v) for k,v in checks.items()})
