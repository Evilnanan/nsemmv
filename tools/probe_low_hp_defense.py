"""Resolve low-HP defense with actual HP qualification and incoming multipliers.

Explicit integer HP resources feed the native actor update block. This runs
selection, list lifecycle and rate consumers, not full collision or HP damage.
"""
import argparse,itertools,json,math,struct
from pathlib import Path
from native_effect_runtime import BASE,OBJ,STOP,Chain,Inputs,sha
from unicorn.x86_const import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted)
raw=a.extracted.with_suffix('.AttachEffectParam.param').read_bytes();rows=Inputs.table(raw,0x44)
assert sha(raw)=='ae8128ed510a532d0fa7cb56fa9c86e4a44c9d815dd4ee01c05821d5f50a9827'
assert sha(x.param)=='07ec636c5565d4551efeb53e6f08bc633b2aa4f2129f13c61b0638d69b1bc176'
block=x.pe.get_data(0x3e0d94,0x21)
assert block.hex()=='488b87b8010000488b08e83d600400488b8b900100000f28c84c8bc7e81b4a1200'
f32=lambda v:struct.unpack('<f',struct.pack('<f',v))[0]
bound=f32(40*f32(.01))
fields=('neutralDamageCutRate','slashDamageCutRate','blowDamageCutRate','thrustDamageCutRate','magicDamageCutRate','fireDamageCutRate','thunderDamageCutRate','darkDamageCutRate')
families=[];base=x.spells['7012300']
for id,rate,category in ((340800,.6,20),(7012300,.84,10),(7012301,.8,10),(7012302,.76,10),(8660100,.77,10),(8660101,.7,10),(8660102,.63,10)):
 attach=x.x['tables']['AttachEffectParam'][str(id)];r=x.spells[str(id)]
 assert attach['passiveSpEffectId_1']==id and attach['exclusivityId']==-1
 assert all(attach[k]==-1 for k in ('passiveSpEffectId_2','passiveSpEffectId_3','permanentSpEffectId'))
 assert (r['stateInfo'],r['spCategory'],r['effectEndurance'],r['conditionHp'],r['conditionHpRate'])==(49,category,-1,40,-1)
 assert r['cycleOccurrenceSpEffectId']==r['replaceSpEffectId']==-1
 assert all(r['invocationConditionsStateChange'+str(i)]==0 for i in (1,2,3))
 assert all(math.isclose(r[k],rate,rel_tol=1e-6) for k in fields)
 assert {k for k in base if r[k]!=base[k]}<=set(fields)|{'spCategory','displayIconForPermamentEffect','spEffectTextId_1','iconId'}
 # 511350 reads the byte at +351 to optionally restrict the receiver category.
 assert x.rows[id][0x351]==0
 families.append(dict(effect=id,root=id,category=category,rate=r[fields[0]]))
rootmap={f['root']:f for f in families}
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


class Health(Chain):
 def __init__(self):
  super().__init__(x);self.ratios=[]
  self.q(OBJ+0x6190,OBJ);self.q(OBJ+0x61b8,OBJ+0xf000);self.q(OBJ+0xf000,OBJ+0xe000)
 def hook(self,u,address,size,user):
  pc=address-BASE
  if pc==0x3e0da3:self.ratios.append(struct.unpack('<f',(u.reg_read(UC_X86_REG_XMM0)&0xffffffff).to_bytes(4,'little'))[0])
  elif pc==0x3e0db5:u.reg_write(UC_X86_REG_RIP,STOP)
  else:super().hook(u,address,size,user)
 def step(self,current,maximum,dt=0):
  assert 0<=current<=maximum and maximum>0
  self.u.mem_write(OBJ+0xe140,struct.pack('<ii',current,maximum))
  self.u.reg_write(UC_X86_REG_RBX,OBJ+0x6000);self.u.reg_write(UC_X86_REG_RDI,OBJ+0x6000)
  self.invoke(0x3e0d94,[0,0]);self.update(dt)
  assert self.ratios[-1]==f32(f32(current)/f32(maximum))
  assert not self.emitted
 def taken(self,kind=0,category=0,flag=False):
  packet=OBJ+0xb000
  self.u.mem_write(packet,bytes(0x300))
  self.u.mem_write(packet+0x25,bytes([kind]))
  self.u.mem_write(packet+0x264,struct.pack('<I',category))
  self.u.mem_write(packet+0x2b4,bytes([int(flag)]))
  self.invoke(0x503800,[OBJ,OBJ+0x500,OBJ+0x520,OBJ+0x540,packet])
  assert list(struct.unpack('<5f',self.u.mem_read(OBJ+0x520,20)))==[1]*5
  assert list(struct.unpack('<5f',self.u.mem_read(OBJ+0x540,20)))==[1]*5
  return list(struct.unpack('<5f',self.u.mem_read(OBJ+0x500,20)))
 def disable(self):
  ptr=struct.unpack('<Q',self.u.mem_read(OBJ+8,8))[0]
  while ptr:
   self.u.mem_write(ptr+0x68,struct.pack('<I',0x800c0003));ptr=struct.unpack('<Q',self.u.mem_read(ptr+0x38,8))[0]

def retained(roots):
 seen=set();result=[]
 for root in roots:
  if rootmap[root]['category']==20 and root in seen:continue
  seen.add(root);result.append(root)
 return result
def verify(c,roots,current,maximum,kind=0,category=0,flag=False):
 nodes=c.nodes();expectedRoots=retained(roots)
 assert [n['id'] for n in nodes]==expectedRoots
 active=f32(f32(current)/f32(maximum))<=bound
 assert all(bool(n['flags']&0x800c0003)!=active for n in nodes)
 assert all(n['lifetime']==-1 for n in nodes)
 rate=math.prod(rootmap[root]['rate'] for root in expectedRoots) if active else 1
 values=c.taken(kind,category,flag)
 expected=[rate if kind<4 else 1]+[rate]*4
 assert all(math.isclose(v,e,rel_tol=1e-6,abs_tol=1e-7) for v,e in zip(values,expected)),(values,expected)
 return dict(ratio=c.ratios[-1],active=active,values=values,nodeCount=len(nodes))
checks={k:[] for k in ('selection','threshold','mixed','transitions','disabled','context')};stubs=set()
def record(group,c,**row):checks[group].append(row);stubs.update(c.stubs)
for f,copies,hero in itertools.product(families,(1,2,3,6),range(11)):
 c=Selection([[f['effect']]]*copies,hero);bits=c.select();selected=[]
 for index in range(copies):
  assert index*6 in bits
  id=struct.unpack('<i',c.u.mem_read(OBJ+0xa000+index*0x80+0x18,4))[0];assert id==f['effect']
  c.invoke(0xe6e150,[OBJ+0x9200,id]);selected.append(c.invoke(0xe6e3b0,[OBJ+0x9200,0])&0xffffffff)
 assert selected==[f['root']]*copies
 v=Health()
 for root in selected:v.insert(root)
 v.step(399,1000);values=verify(v,selected,399,1000)
 record('selection',c,effect=f['effect'],copies=copies,hero=hero,selected=selected,**values);stubs.update(v.stubs)
print('PASS selection',len(checks['selection']),flush=True)
for f,copies,maximum in itertools.product(families,(0,1,2,3,6),(5,100,101,1000,1001,10000,1000000)):
 near=maximum*2//5
 for current in (0,near-1,near,near+1,maximum):
  c=Health();roots=[f['root']]*copies
  for root in roots:c.insert(root)
  c.step(current,maximum);values=verify(c,roots,current,maximum)
  # These representative integer resources never hit a float-rounding ambiguity.
  assert values['active']==(current*5<maximum*2)
  record('threshold',c,effect=f['effect'],copies=copies,current=current,maximum=maximum,**values)
print('PASS threshold',len(checks['threshold']),flush=True)
mixed=[]
for group in ([7012300,7012301,7012302],[8660100,8660101,8660102],list(rootmap)):
 for n in range(2,min(len(group),3)+1):mixed.extend(map(list,itertools.combinations(group,n)))
mixed.extend([list(rootmap),list(reversed(rootmap)),list(rootmap)*2,[340800]*6+[7012302]*6])
for roots,current in itertools.product(mixed,(399,400,1000)):
 c=Health()
 for root in roots:c.insert(root)
 c.step(current,1000);values=verify(c,roots,current,1000)
 record('mixed',c,roots=roots,current=current,maximum=1000,**values)
print('PASS mixed',len(checks['mixed']),flush=True)
steps=[(1000,1000),(400,1000),(399,1000),(1,1000),(400,1000),(399,1000),(1000,1000),(400,1200),(400,1000),(999,3000),(999,1000)]
for f,copies,dt in itertools.product(families,(1,3),(0,1/30,1/60,1/120,5)):
 c=Health();roots=[f['root']]*copies
 for root in roots:c.insert(root)
 timeline=[]
 for current,maximum in steps:
  c.step(current,maximum,dt);timeline.append(dict(current=current,maximum=maximum,**verify(c,roots,current,maximum)))
 record('transitions',c,effect=f['effect'],copies=copies,dt=dt,timeline=timeline)
print('PASS transitions',len(checks['transitions']),flush=True)
for f,copies,current in itertools.product(families,(1,3),(399,400,1000)):
 c=Health()
 for _ in range(copies):c.insert(f['root'])
 c.step(current,1000);c.disable();values=c.taken();assert values==[1]*5
 record('disabled',c,effect=f['effect'],copies=copies,current=current,values=values)
print('PASS disabled',len(checks['disabled']),flush=True)
# Context fields read by 503800: physical subtype, receiver category and flag.
# Include unknown physical subtypes as explicit fallback checks, not gameplay claims.
for f,current in itertools.product(families,(399,400)):
 c=Health();roots=[f['root']]*3
 for root in roots:c.insert(root)
 c.step(current,1000)
 for kind,category,flag in itertools.product((0,1,2,3,4,255),(0,1,255),(False,True)):
  values=verify(c,roots,current,1000,kind,category,flag)
  record('context',c,effect=f['effect'],current=current,kind=kind,category=category,flag=flag,**values)
print('PASS context',len(checks['context']),flush=True)
output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),attachParamSha256=sha(raw),
 families=families,checks=checks,hpThreshold=bound,callsite=dict(start='3E0D94',end='3E0DB5',sha256=sha(block)),
 native=dict(selection='4FEA30 → E6E150 → E6E3B0',hp='3E0D94 → 426DE0 → 5057D0',lifecycle='50D060 → 50ACD0',context='50F370 → 511350',damage='503800 → EA0980'),
 stubs=sorted(stubs|{'synthetic inventory in positive slot0; draw legality not asserted',
 'explicit integer current/max HP resource and actor pointers at HP qualification basic-block boundary; surrounding character scheduler not run',
 'explicit incoming damage context with physical subtype, receiver category and flag; full construction, collision and final HP write not run',
 'no real hit crossing threshold, death/reload, equipment rebuild or multiplayer; HP=0 is a qualification boundary, not a death simulation'}),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',{k:len(v) for k,v in checks.items()},flush=True)
