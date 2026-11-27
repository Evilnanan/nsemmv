"""Verify attack stamina curse stacking and complete native cost calculation.

Equipment selection, effect aggregation, weapon threshold predicate, weapon
factor and common correction execute original code with pinned rows. Actor
resource value, attack base cost and caller flags are explicit inputs; the
actual stamina setter and complete action dispatch are not executed.
"""
import argparse,itertools,json,math,struct
from pathlib import Path
from native_effect_runtime import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','assets','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted)
raw=a.extracted.with_suffix('.AttachEffectParam.param').read_bytes();rows=Inputs.table(raw,0x44)
assets=json.loads(a.assets.read_text());assert assets['hashes']['regulation.bin']==x.x['hashes']['regulation.bin']
weapon_raw=a.assets.with_suffix('.EquipParamWeapon.param').read_bytes();weapons=Inputs.table(weapon_raw,0x2a8)
common_raw=a.extracted.with_suffix('.PlayerCommonParam.param').read_bytes()
assert struct.unpack_from('<H',common_raw,10)[0]==1
common=common_raw[struct.unpack_from('<Q',common_raw,0x48)[0]:]
low_rate=x.x['tables']['PlayerCommonParam']['0']['lowStatus_ConsumeStaminaRate']
assert struct.unpack_from('<f',common,0x30)[0]==low_rate==1.5
families=[]
for id,rate in ((6850600,1.13),(6850601,1.07),(6850602,1.1)):
 attach=x.x['tables']['AttachEffectParam'][str(id)];r=x.spells[str(id)]
 assert attach['passiveSpEffectId_1']==id and attach['exclusivityId']==-1
 assert all(attach[k]==-1 for k in ('passiveSpEffectId_2','passiveSpEffectId_3','permanentSpEffectId'))
 assert (r['spCategory'],r['stateInfo'],r['effectEndurance'],r['wepParamChange'])==(10,0,-1,0)
 assert all(r['invocationConditionsStateChange'+str(i)]==0 for i in (1,2,3))
 assert all(r[k]==-1 for k in ('cycleOccurrenceSpEffectId','replaceSpEffectId','atkOccurrenceSpEffectId'))
 assert struct.unpack_from('<f',x.rows[id],0x1f4)[0]==r['consumeStaminaRate']
 assert math.isclose(r['consumeStaminaRate'],rate,rel_tol=1e-6)
 families.append(dict(effect=id,root=id,rate=r['consumeStaminaRate']))
weapon_reps={}
for key,r in assets['tables']['EquipParamWeapon'].items():weapon_reps.setdefault(r['staminaConsumptionRate'],int(key))
assert len(weapon_reps)==10
weapon_info=[]
for rate,id in weapon_reps.items():
 r=assets['tables']['EquipParamWeapon'][str(id)];assert struct.unpack_from('<f',weapons[id],0x1f4)[0]==rate
 threshold=struct.unpack_from('<h',weapons[id],0xe0)[0]
 # Retain the decoded schema name without assuming it describes the native
 # resource +10C threshold's current gameplay meaning.
 assert threshold==r['throwAtkRate']
 weapon_info.append(dict(id=id,rate=rate,threshold=threshold))
vtable=0x2c307f8
locator=struct.unpack('<Q',x.pe.get_data(vtable-8,8))[0]-BASE
rtti=struct.unpack('<6I',x.pe.get_data(locator,24));assert rtti[0]==1 and rtti[1:3]==(0,0)
assert x.pe.get_data(rtti[3]+16,200).split(b'\0')[0]==b'.?AVPlayerIns@CS@@'
assert struct.unpack('<Q',x.pe.get_data(vtable+0x348,8))[0]==BASE+0x668730
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

class Cost(Chain):
 def __init__(self,roots,disabled=False):
  super().__init__(x);self.blocked=False;self.actor_flag=0;self.base_flag=0
  for root in roots:self.insert(root)
  self.qualify();self.update(0)
  if disabled:
   node=struct.unpack('<Q',self.u.mem_read(OBJ+8,8))[0]
   while node:
    self.u.mem_write(node+0x68,struct.pack('<I',0x800c0003));node=struct.unpack('<Q',self.u.mem_read(node+0x38,8))[0]
  self.actor=OBJ+0xd000;self.resource=OBJ+0xe800
  self.q(self.actor,OBJ+0xe000);self.q(OBJ+0xe190,STOP+0x210);self.q(self.actor+0x190,OBJ)
  assert len(common)<0x10000;self.u.mem_map(OBJ+0x80000,0x10000);self.u.mem_write(OBJ+0x80000,common)
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(value=0):
   u.reg_write(UC_X86_REG_RAX,value&0xffffffffffffffff);sp=u.reg_read(UC_X86_REG_RSP)
   u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  ptr=u.reg_read(UC_X86_REG_RCX)
  if pc==0xea7fc0:
   id=u.reg_read(UC_X86_REG_RDX)&0xffffffff
   u.mem_write(OBJ+0xc100,weapons[id]);self.q(ptr+8,OBJ+0xc100);ret(ptr)
   self.stubs.add('EA7FC0 actual weapon row lookup')
  elif pc==0xea9a60:
   self.q(ptr+8,0);ret(ptr);self.stubs.add('EA9A60 no reinforcement row')
  elif pc==0xe81650:
   self.q(ptr,OBJ+0x80000);ret(ptr);self.stubs.add('E81650 actual PlayerCommon row')
  elif pc==0x3ced90:
   ret(OBJ+0xf000);self.stubs.add('3CED90 explicit actor context')
  elif pc==0x4d1b20:
   ret(int(self.blocked));self.stubs.add('4D1B20 explicit actor early-exit predicate')
  elif pc==0x3d4960:
   ret(self.actor_flag);self.stubs.add('3D4960 explicit actor flag, not equated with weapon correction mask')
  elif address==STOP+0x210:
   ret(self.resource);self.stubs.add('actor virtual+190 explicit resource object, native +10C threshold comparison')
  else:super().hook(u,address,size,user)
 def number(self):return struct.unpack('<f',(self.u.reg_read(UC_X86_REG_XMM0)&0xffffffff).to_bytes(4,'little'))[0]
 def rate(self):self.invoke(0x5066a0,[OBJ]);return self.number()
 def cost(self,base,weapon,value,mask,base_flag=0,actor_flag=0,blocked=False):
  self.blocked=blocked;self.actor_flag=actor_flag
  self.u.mem_write(self.resource+0x10c,struct.pack('<i',value))
  result=self.invoke(0x668730,[self.actor,base,weapon,base_flag,mask])
  return struct.unpack('<i',struct.pack('<I',result&0xffffffff))[0]

def f32(v):return struct.unpack('<f',struct.pack('<f',v))[0]
def expected_rate(roots):
 rate=1.
 for id in roots:rate=f32(rate*x.spells[str(id)]['consumeStaminaRate'])
 return rate
checks={k:[] for k in ('selection','multipliers','costs','disabled','flags')};stubs=set()
def record(kind,c,**row):checks[kind].append(row);stubs.update(c.stubs)
for f,copies,hero in itertools.product(families,(1,2,3,6),range(11)):
 slots=[[7000000,-1,-1,f['effect']]]*copies;c=Selection(slots,hero);bits=c.select();roots=[]
 for index in range(copies):
  assert index*6+3 in bits
  id=struct.unpack('<i',c.u.mem_read(OBJ+0xa000+index*0x80+0x24,4))[0]
  assert id==f['effect'];c.invoke(0xe6e150,[OBJ+0x9200,id]);roots.append(c.invoke(0xe6e3b0,[OBJ+0x9200,0])&0xffffffff)
 assert roots==[f['root']]*copies
 record('selection',c,effect=f['effect'],copies=copies,hero=hero,curseSlot=3,bits=bits,roots=roots)
cases=[[]]+[[f['root']]*copies for f in families for copies in (1,2,3,6)]+[[6850600,6850601,6850602],[6850602,6850601,6850600]]
for roots in cases:
 c=Cost(roots);rate=c.rate();assert rate==expected_rate(roots)
 assert [n['id'] for n in c.nodes()]==roots
 record('multipliers',c,roots=roots,rate=rate,nodes=c.nodes())
 for w,delta,mask,base in itertools.product(weapon_info,(-1,0,1),(0,1,3,4),(0,1,31,101)):
  value=w['threshold']+delta;weapon_rate=w['rate'] if mask&3 else 1
  condition_rate=low_rate if delta<0 else 1
  expected=int(f32(f32(f32(f32(base)*rate)*weapon_rate)*condition_rate))
  actual=c.cost(base,w['id'],value,mask)
  assert actual==expected,(roots,w,delta,mask,base,rate,actual,expected)
  record('costs',c,roots=roots,weapon=w['id'],resourceValue=value,weaponMask=mask,base=base,rate=rate,weaponRate=weapon_rate,conditionRate=condition_rate,result=actual)
for f in families:
 c=Cost([f['root']]*3,disabled=True);assert c.rate()==1
 actual=c.cost(101,1000,0,1);assert actual==101
 record('disabled',c,effect=f['effect'],rate=c.rate(),result=actual)
for blocked,base_flag,actor_flag in itertools.product((False,True),(0,1),(0,1,2,3)):
 c=Cost([6850600]);actual=c.cost(101,1000,0,1,base_flag,actor_flag,blocked)
 assert actual==(0 if blocked else 114)
 record('flags',c,blocked=blocked,baseFlag=base_flag,actorFlag=actor_flag,result=actual)
output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),attachParamSha256=sha(raw),weaponParamSha256=sha(weapon_raw),commonParamSha256=sha(common_raw),
 families=families,weaponRepresentatives=weapon_info,lowStatusRate=low_rate,checks=checks,
 native=dict(selection='4FEA30 → E6E150 → E6E3B0',aggregate='5066A0 → 50FEF0',cost='PlayerIns.vtable+348 → 668730 → 6C5A10',threshold='6D0080'),
 stubs=sorted(stubs|{'synthetic inventory: curse slot3 paired with positive7000000; draw legality not asserted',
 'attack base, caller mask/flags and resource+10C value are explicit inputs; full action/TAE dispatch not simulated',
 'actual stamina write, attack admission/zero-stamina behavior, save/load and multiplayer not executed',
 'weapon+E0 decoded as throwAtkRate but compared to resource+10C; gameplay meaning not inferred from legacy schema name'}),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',{k:len(v) for k,v in checks.items()})
