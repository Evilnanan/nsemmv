"""Execute debuff-qualified attack nullification and the ordinary hit branch.

Pinned eligibility, bounded RNG, flag assignment, death checks and hit reception
run with an explicit pre-branch context. HP writes are recorded, not applied.
"""
import argparse,itertools,json,math,struct
from pathlib import Path
from native_effect_runtime import BASE,OBJ,STACK,STOP,Chain,Inputs,sha
from native_ailment_runtime import Ailment
from unicorn.x86_const import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','systems','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted);systems=json.loads(a.systems.read_text())
assert systems['hashes']['regulation.bin']==x.x['hashes']['regulation.bin']
raw=a.systems.with_suffix('.PlayerCommonParam.param').read_bytes();player=Inputs.table(raw,0x2e8)[0]
attacks=Inputs.table(a.extracted.with_suffix('.AtkParam_Pc.param').read_bytes(),0x1d0)
common=systems['tables']['PlayerCommonParam']['0'];root=7037800
chance,vfx,icon=struct.unpack_from('<3i',player,0x2dc)
assert (chance,vfx,icon)==(20,7037805,7037806)
assert (common['attackNullifyChance'],common['attackNullifyEffectId_Vfx'],common['attackNullifyIconEffectId'])==(chance,vfx,icon)
assert x.x['tables']['AttachEffectParam'][str(root)]['passiveSpEffectId_1']==root
assert x.spells[str(root)]['stateInfo']==2130 and x.spells[str(root)]['effectEndurance']==-1
assert x.spells[str(vfx)]['effectEndurance']==0 and math.isclose(x.spells[str(icon)]['effectEndurance'],.1,abs_tol=1e-7)
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

C=OBJ+0x60000;HIT=OBJ+0x61000;SOURCE=OBJ+0x62000;SEFFECT=OBJ+0x63000
class Hit(Actor):
 def __init__(self,kind=4,maximum=500):
  super().__init__(kind,maximum);self.u.mem_map(C,0x10000);self.q(C+8,OBJ+0x6000);self.sent=[]
  self.q(OBJ+0xf000,OBJ+0xe000);self.q(OBJ+0xf088,OBJ+0xf900);self.q(OBJ+0xf910,OBJ+0xfa00)
  self.u.mem_write(OBJ+0xe140,struct.pack('<i',10000));self.q(OBJ+0x6400,STOP+0x600)
  self.globalq(0x42715d+8+0x37e81d3,OBJ+0xfd00)
  self.q(SOURCE,OBJ+0x6200);self.q(SOURCE+0x190,SEFFECT);self.q(SEFFECT+0x10,SOURCE)
  self.u.mem_write(SOURCE+0x74,b'\1');self.u.mem_write(OBJ+0x6074,b'\6')
  self.q(OBJ+0x7118,STOP+0x601)
  self.globalq(0x1fe1c0+7+0x3a09709,OBJ+0x68000)
  self.stubs.add('explicit local hit-score context in mode 0')
  self.same=False;self.attack=2
 def hook(self,u,address,size,user):
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  pc=address-BASE
  if address==STOP+0x600:
   self.stubs.add('recipient virtual +200 false ordinary hit predicate');ret()
  elif pc==0x214f3e0:
   self.stubs.add('214F3E0 allocator identity for empty attacker effect-vector collection');ret(OBJ+0x7000)
  elif address==STOP+0x601:
   self.stubs.add('allocator virtual +18 explicit valid tag; native empty vector collection');ptr=u.reg_read(UC_X86_REG_RDX);u.mem_write(ptr,struct.pack('<I',32));ret(ptr)
  elif pc==0x3d4180:pass  # execute actual local-player comparison
  elif pc==0x26909a0:
   self.stubs.add('26909A0 security cookie preserves return value');ret(u.reg_read(UC_X86_REG_RAX))
  elif pc==0xe6d630:
   self.stubs.add('E6D630 actual AtkParam_Pc row lookup');assert u.reg_read(UC_X86_REG_R8)==self.attack and u.reg_read(UC_X86_REG_RDX)==1
   wrapper=u.reg_read(UC_X86_REG_RCX);u.mem_write(OBJ+0x64000,attacks[self.attack]);u.mem_write(wrapper,struct.pack('<iii4xQ',self.attack,0,1,OBJ+0x64000));ret()
  elif pc==0x3c80a0:
   sp=u.reg_read(UC_X86_REG_RSP);ptr=struct.unpack('<Q',u.mem_read(sp+0x30,8))[0]
   self.sent.append(dict(id=u.reg_read(UC_X86_REG_RDX)&0xffffffff,scales=list(struct.unpack('<15f',u.mem_read(ptr,60)))))
  else:super().hook(u,address,size,user)
 def hit(self,ids=(503,24240),attack=2,scale=0):
  self.attack=attack
  if isinstance(ids,int):ids=(ids,)
  self.u.mem_write(HIT,bytes(0x400))
  self.u.mem_write(HIT+0x40,struct.pack('<ii',attack,1))
  for slot,id in enumerate(ids,5):self.u.mem_write(HIT+0x70+slot*4,struct.pack('<i',id))
  self.u.mem_write(HIT+0x188,struct.pack('<ff',scale,1))
  self.u.mem_write(HIT+0x1a4,struct.pack('<7f',*([1]*7)))
  for off in (0x29c,0xd4,0x254):self.u.mem_write(HIT+off,struct.pack('<f',1))
  self.invoke(0x43be60,[C,OBJ+0x6000 if self.same else SOURCE,HIT,0,1,0])

class Nullify(Hit):
 def __init__(self,roll=0):
  self.roll=roll;self.inBranch=False;self.hpWrites=[];self.rollCalls=0;self.stopAt=0x43d6ae;super().__init__()
  self.u.mem_map(OBJ+0x80000,0x10000);self.u.mem_write(OBJ+0x80000,player)
  self.q(C,OBJ+0x88200);self.q(OBJ+0x88250,STOP+0x701)
  self.q(OBJ+0x88000,OBJ+0x88100);self.q(OBJ+0x88108,STOP+0x700)
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v&0xffffffffffffffff);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if pc==0xe81650:
   self.stubs.add('E81650 actual PlayerCommon PARAM lookup');ptr=u.reg_read(UC_X86_REG_RCX);self.q(ptr,OBJ+0x80000);ret(ptr)
  elif pc==0x6af4f0:self.stubs.add('6AF4F0 explicit RNG identity');ret(OBJ+0x88000)
  elif address==STOP+0x700:
   self.stubs.add('RNG virtual +8 supplies raw sample; native F563C0 interval mapping remains live');self.rollCalls+=1;ret(self.roll)
  elif address==STOP+0x701:self.stubs.add('hit module virtual +50 notification sink');ret()
  elif pc==self.stopAt and self.inBranch:u.reg_write(UC_X86_REG_RIP,STOP)
  elif pc==0x426130:
   self.stubs.add('426130 HP write request recorder; no final HP mutation')
   value=u.reg_read(UC_X86_REG_RDX)&0xffffffff;self.hpWrites.append(value if value<0x80000000 else value-0x100000000);ret()
  else:super().hook(u,address,size,user)
 def branch(self, effect=7034602, scale=1, damage=100, hp=10000, excluded=0, hitFlags=0):
  self.u.mem_write(HIT,bytes(0x400));self.u.mem_write(HIT+0x40,struct.pack('<ii',2,1))
  self.u.mem_write(HIT+0x280,struct.pack('<i',damage));self.u.mem_write(OBJ+0xe140,struct.pack('<i',hp));self.u.mem_write(HIT+0x160,bytes([hitFlags]))
  for reg,value in ((UC_X86_REG_RBX,SOURCE),(UC_X86_REG_R12,SOURCE),(UC_X86_REG_RBP,STACK+0x9000),(UC_X86_REG_R14,C),(UC_X86_REG_RSI,HIT),(UC_X86_REG_R15,0),(UC_X86_REG_R13,excluded)):self.u.reg_write(reg,value)
  self.u.mem_write(STACK+0x8008+0x40,bytes(0x18));self.u.mem_write(STACK+0x907f,b'\0')
  self.u.mem_write(HIT+0x70+5*4,struct.pack('<i',effect))
  for off in (0x29c,0xd4,0x254):self.u.mem_write(HIT+off,struct.pack('<f',1))
  self.u.mem_write(HIT+0x188,struct.pack('<ff',scale,1));self.u.mem_write(HIT+0x1a4,struct.pack('<7f',*([1]*7)))
  self.inBranch=True
  self.invoke(0x43d541,[])
  self.inBranch=False
  return bool(self.u.mem_read(HIT+0x2c3,1)[0]&2)
checks=dict(predicate=[],rolls=[],controls=[],ailments=[],repeat=[]);stubs=set()
def record(key,c,**row):checks[key].append(row);stubs.update(c.stubs)
def equipped(copies=1,debuff=7036602,protect=None,roll=0):
 c=Nullify(roll)
 for _ in range(copies):c.grant(root)
 for id in (debuff,protect):
  if id:c.insert(id)
 c.qualify();c.update(0);return c
def defense(c):
 c.u.mem_write(OBJ+0x800,bytes(0x200));c.invoke(0x503800,[OBJ,OBJ+0x500,OBJ+0x520,OBJ+0x540,OBJ+0x800])
 return list(struct.unpack('<5f',c.u.mem_read(OBJ+0x500,20)))
for copies,debuff,protect in itertools.product((0,1,3),(None,7036602,1501000,99008),(None,7011401)):
 c=equipped(copies,debuff,protect);eligible=bool(c.invoke(0x504520,[OBJ])&255)
 assert eligible==bool(copies and debuff in (7036602,1501000))
 record('predicate',c,copies=copies,debuff=debuff,protect=protect,eligible=eligible,rates=defense(c))
for copies,roll in itertools.product((1,3),range(100)):
 c=equipped(copies,roll=roll);success=c.branch()
 assert success==(roll<chance) and c.rollCalls==1
 assert c.hpWrites==([] if success else [-100])
 assert struct.unpack('<i',c.u.mem_read(OBJ+0x9010,4))[0]==200
 record('rolls',c,copies=copies,rawSample=roll,success=success,draws=c.rollCalls,hpWrites=c.hpWrites,poisonRemaining=200)
for name,copies,debuff,damage,hp,excluded,hitFlags in (
 ('no-equipment',0,7036602,100,10000,0,0),('no-debuff',1,None,100,10000,0,0),
 ('state-110',1,99008,100,10000,0,0),('nonpositive-damage',1,7036602,0,10000,0,0),
 ('negative-damage',1,7036602,-100,10000,0,0),('dead',1,7036602,100,0,0,0),
 ('excluded-input',1,7036602,100,10000,1,0),('hit-flag-20',1,7036602,100,10000,0,0x20)):
 c=equipped(copies,debuff);c.stopAt=0x43d64a
 assert not c.branch(damage=damage,hp=hp,excluded=excluded,hitFlags=hitFlags) and c.rollCalls==0
 record('controls',c,name=name,draws=c.rollCalls,nodes=c.nodes())
# Actual status rows and explicit neutral hit metadata compare the same packet
# with/without nullification; this does not invent an attack that owns all rows.
for (effect,channel,amount),roll in itertools.product(((7034602,0,300),(1501000,4,50),(7500002,2,55)),(0,19,20,99,100,119,120)):
 c=equipped(roll=roll);success=c.branch(effect=effect)
 remaining=struct.unpack('<i',c.u.mem_read(OBJ+0x9010+channel*4,4))[0]
 assert success==(roll%100<20) and remaining==500-amount
 assert c.hpWrites==([] if success else [-100])
 record('ailments',c,effect=effect,channel=channel,rawSample=roll,success=success,amount=amount,remaining=remaining,hpWrites=c.hpWrites)
for copies in (1,3):
 c=equipped(copies);results=[]
 for index,roll in enumerate((0,0,20,0,99,0)):
  c.roll=roll;c.hpWrites=[];before=c.rollCalls
  # Keep an ordinary non-onset status input across repeated hits.
  c.u.mem_write(OBJ+0x9010,struct.pack('<i',500))
  success=c.branch();assert success==(roll<20) and c.rollCalls==before+1
  c.qualify();c.update(0)
  results.append(dict(index=index,success=success,draws=c.rollCalls,hpWrites=c.hpWrites))
 record('repeat',c,copies=copies,hits=results)
output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),
 playerParamSha256=sha(raw),effect=root,chance=chance,vfx=vfx,icon=icon,checks=checks,
 rows={str(id):x.spells[str(id)] for id in (root,vfx,icon)},
 native=dict(eligible='504520 → EA0980',branch='43D541..43D6AE within 43D260',boundedRandom='F563C0',
 hit='43BE60',hpRequest='426130',status='3C80A0 → 42D110',grant='3C7FD0',defense='503800'),
 stubs=sorted(stubs|{'explicit normal pre-hit branch context, raw RNG samples, neutral attack/status metadata and supplied HP; full collision and outer 43D260 entry not simulated',
 'final HP writes recorded only; feedback, full hit reaction, geometry, death/reload and network synchronization unverified',
 'zero-life VFX and 0.1-second icon are not invulnerability windows or cooldowns'}),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS', {k:len(v) for k,v in checks.items()}, 'attack nullification cases')
