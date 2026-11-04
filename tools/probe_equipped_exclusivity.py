"""Execute Attach exclusivity selection before fixed attributes and attack rates.

Native relic eligibility, duplicate-key tree, bit selection, passive-root reads,
effect insertion and numeric getters run unchanged. Inventory objects,
allocations and row lookups are explicit fixtures. The two native stages are
connected through their selected root IDs, not a complete live equipment flow.
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

families=[dict(effect=id,root=id,exclusive=exclusive) for id,exclusive in ((7000090,600),(7000190,500),(7000290,700),(7006600,801),(7006700,802))]
for f in families:
 row=x.x['tables']['AttachEffectParam'][str(f['effect'])]
 assert row['exclusivityId']==f['exclusive'] and struct.unpack_from('<i',rows[f['effect']],0x3c)[0]==f['exclusive']
 assert row['passiveSpEffectId_1']==f['root'] and x.spells[str(f['root'])]['spCategory']==10
checks={k:[] for k in ('selection','hero','mixed','groups','attributes','attack')};stubs=set()
def record(key,*contexts,**row):
 checks[key].append(row)
 for c in contexts:stubs.update(c.stubs)
def expected_bits(slots):
 result=[]
 for start in range(0,len(slots),6):
  seen=set()
  for index,row in enumerate(slots[start:start+6],start):
   for slot,id in enumerate(row):
    exclusive=x.x['tables']['AttachEffectParam'][str(id)]['exclusivityId']
    if exclusive>=0 and exclusive in seen:continue
    if exclusive>=0:seen.add(exclusive)
    result.extend((index*6+slot,index*6+slot+3))
 return sorted(result)
for f,hero,layout in itertools.product(families,range(1,11),range(6)):
 id=f['effect'];slots=[[],[[id]],[[id]]*3,[[id]]*6,[[id,id,id]],[[id,id,id]]*6][layout]
 c=Selection(slots,hero);bits=c.select();assert bits==expected_bits(slots)
 record('selection',c,effect=id,hero=hero,layout=layout,slots=slots,bits=bits)
for (effect,allowed),hero in itertools.product(((7011300,2),(7010700,4)),range(1,11)):
 c=Selection([[effect]],hero);bits=c.select();assert bits==([0,3] if hero==allowed else [])
 record('hero',c,effect=effect,hero=hero,allowed=allowed,bits=bits)
# Nonexclusive controls preserve repeated copies, including when combined with
# exclusive attributes. Direct eligibility within a real role is retained.
mixed=[[[7000090,7000190,7000290],[7006600,7006700]],
       [[7006700,7006600],[7000290,7000190,7000090]],
       [[7000090],[6610400],[6610400],[7000000],[7000000],[7000090]],
       [[7000190],[6610500],[6610500],[7000100],[7000100],[7000190]],
       [[7000290],[6610600],[6610600],[7000200],[7000200],[7000290]],
       [[7000090,7000190,7000290]]*6,[[7006600,7006700]]*6]
for slots in mixed:
 c=Selection(slots);bits=c.select();assert bits==expected_bits(slots)
 record('mixed',c,slots=slots,bits=bits)
for f,count in itertools.product(families,(0,6,7,12,24)):
 slots=[[f['effect']]]*count;c=Selection(slots);bits=c.select();assert bits==expected_bits(slots)
 record('groups',c,effect=f['effect'],slotCount=count,bits=bits)
stat_fields=('addLifeForceStatus','addWillpowerStatus','addEndureStatus','addStrengthStatus','addDexterityStatus','addMagicStatus','addFaithStatus','addLuckStatus')
stat_cases=[[[id]]*copies for id in(7000090,7000190,7000290) for copies in(0,1,3,6)]+mixed[:6]
for slots,disabled in itertools.product(stat_cases,(False,True)):
 c,v,accepted,roots=bridge(slots)
 if disabled:
  node=struct.unpack('<Q',v.u.mem_read(OBJ+8,8))[0]
  while node:
   v.u.mem_write(node+0x68,struct.pack('<I',0x800c0003));node=struct.unpack('<Q',v.u.mem_read(node+0x38,8))[0]
 values=v.stats();expected=[sum(x.spells[str(root)][field] for root in roots) if not disabled else 0 for field in stat_fields]
 assert values==expected,(slots,values,expected)
 record('attributes',c,v,slots=slots,disabled=disabled,accepted=accepted,roots=roots,values=values)
representatives={}
for id,row in x.x['tables']['AtkParam_Pc'].items():
 tags={row['subCategory'+str(i)] for i in range(1,6)};key=(130 in tags,bool(tags.intersection({111,112})))
 representatives.setdefault(key,int(id))
assert representatives=={(False,False):0,(True,False):90000,(True,True):100900,(False,True):5000811}
f32=lambda v:struct.unpack('<f',struct.pack('<f',v))[0]
for effects,copies,disabled in itertools.product(((7006600,),(7006700,),(7006600,7006700),(7006700,7006600)),(0,1,3),(False,True)):
 slots=[list(effects)]*copies;c,v,accepted,roots=bridge(slots)
 if disabled:
  node=struct.unpack('<Q',v.u.mem_read(OBJ+8,8))[0]
  while node:
   v.u.mem_write(node+0x68,struct.pack('<I',0x800c0003));node=struct.unpack('<Q',v.u.mem_read(node+0x38,8))[0]
 for (melee,art),attack in representatives.items():
  for kind in range(13):
   values=v.attackrow(attack,kind);expected=1.
   if not disabled and kind not in(3,4,5,10):
    for root in roots:
     if (root==7006600 and melee) or (root==7006700 and art):expected=f32(expected*f32(x.spells[str(root)]['physicsAttackRate']))
   assert all(math.isclose(value,expected,rel_tol=1e-6) for value in values),(effects,copies,attack,kind,values,expected)
   record('attack',c,v,effects=effects,copies=copies,disabled=disabled,accepted=accepted,roots=roots,attack=attack,kind=kind,melee=melee,art=art,values=values)
output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),
 attachParamSha256=sha(raw),attackParamSha256=sha(atkraw),families=families,
 rows={str(f['root']):{key:x.spells[str(f['root'])][key] for key in (*stat_fields,'spCategory','stateInfo','physicsAttackRate','magicAttackRate','fireAttackRate','thunderAttackRate','darkAttackRate','magicSubCategoryChange1','magicSubCategoryChange2','magicSubCategoryChange3')} for f in families},
 attackRows={str(id):{f'subCategory{i}':x.x['tables']['AtkParam_Pc'][str(id)][f'subCategory{i}'] for i in range(1,6)} for id in representatives.values()},checks=checks,
 native=dict(selection='4FEA30',hero='E6E750',roots='E6E150 / E6E3B0',insertion='50D060',qualifier='5057D0',update='50ACD0',attributes='502300',tags='E6D530',attack='502830 → 511010'),
 stubs=sorted(stubs|{'manager virtual +58/+60 inventory handles and valid relics; actor +178 chosen hero',
 '69E570 supplies synthetic relic instance/ordinary Goods ID2000100; 69E5A0 cleanup fixture; actual ID and effect accessors execute',
 '214F3E0 allocator owner, virtual +18 valid allocation tag, 325C40 tree node storage; original tree insert/erase run',
 '2081B0 allocates/zeros144-bit output vector; original qualification and bit writes run; virtual +68 free recorder',
 'E6E430 actual AttachEffect rows; E6D630 actual AtkParam_Pc rows',
 '1FE1C0 mode0; actor +190 absent live stat module',
 'selected roots bridge into separate effect container; no full equipment manager, resource curves/caps, special relic2070, scene hit, networking or gameplay'}),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(map(len,checks.values())),'equipped exclusivity checks',{k:len(v) for k,v in checks.items()},flush=True)
