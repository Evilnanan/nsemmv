"""Trace knockback protection through the native damage-reaction caller and timers.

Explicit attack packet, component and equipment fixtures drive pinned original
instructions; no full collision, animation scheduler or gameplay is simulated.
"""
import argparse,itertools,json,math,struct
from pathlib import Path
from native_effect_runtime import BASE,OBJ,STOP,Inputs,Chain,sha
from native_ailment_runtime import Ailment
from unicorn.x86_const import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted);inputs=x
raw=a.extracted.with_suffix('.AttachEffectParam.param').read_bytes();rows=Inputs.table(raw,0x44)
assert sha(raw)=='ae8128ed510a532d0fa7cb56fa9c86e4a44c9d815dd4ee01c05821d5f50a9827'
assert sha(x.param)=='07ec636c5565d4551efeb53e6f08bc633b2aa4f2129f13c61b0638d69b1bc176'
assert len(rows)==struct.unpack_from('<H',raw,10)[0] and len(x.rows)==struct.unpack_from('<H',x.param,10)[0]
EFFECT=7240000;ROOTS=(7240000,7240003,7240006);LEAF=7240013;KINDS=(4,7,9,10,11);GUARDS=(7240001,7240004,7240010,7240011,7240012)
attach=x.x['tables']['AttachEffectParam'][str(EFFECT)]
assert [attach['passiveSpEffectId_'+str(n)] for n in (1,2,3)]==list(ROOTS) and attach['exclusivityId']==-1
assert all(v==1 for k,v in attach.items() if k.startswith('allow'))
for root in ROOTS:
 r=x.spells[str(root)];assert (r['spCategory'],r['stateInfo'],r['effectEndurance'],r['motionInterval'],r['cycleOccurrenceSpEffectId'])==(0,0,-1,1,root+1)
for guard,kind in zip(GUARDS,KINDS):
 r=x.spells[str(guard)];assert r['triggerEffectOnKnockback_unk']==x.rows[guard][0x3a7]==kind
 assert (r['spCategory'],r['effectEndurance'],r['replaceSpEffectId'])==(0,-1,LEAF)
for bridge,child,next_id in ((7240007,7240010,7240008),(7240008,7240011,7240009),(7240009,7240012,-1)):
 r=x.spells[str(bridge)];assert math.isclose(r['effectEndurance'],.05,rel_tol=1e-6)
 assert (r['cycleOccurrenceSpEffectId'],r['replaceSpEffectId'],r['motionInterval'])==(child,next_id,1)
r=x.spells[str(LEAF)];assert (r['spCategory'],r['stateInfo'],r['effectEndurance'])==(20,0,20)
assert all(math.isclose(r[k+'DamageCutRate'],.8,rel_tol=1e-6) for k in ('neutral','magic','fire','thunder','dark','toughness'))
assert r['saReceiveDamageRate']==1
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

class Defense(Damage):
 def values(self):
  self.u.mem_write(OBJ+0x800,bytes(0x200));self.invoke(0x503800,[OBJ,OBJ+0x500,OBJ+0x520,OBJ+0x540,OBJ+0x800])
  rates=list(struct.unpack('<5f',self.u.mem_read(OBJ+0x500,20)));self.invoke(0x502270,[OBJ,0]);return dict(rates=rates,poise=struct.unpack('<f',(self.u.reg_read(UC_X86_REG_XMM0)&0xffffffff).to_bytes(4,'little'))[0])
class Caller(Defense):
 def __init__(self):
  self.stopAt=None;self.notified=[];super().__init__();self.q(OBJ+0x61b8,OBJ+0xf000);self.q(OBJ+0xf040,OBJ+0xf400);self.q(OBJ+0xf048,0);self.q(OBJ+0xf400,OBJ+0xf500);self.q(OBJ+0xf510,STOP+0xb00)
  self.q(OBJ+0x1b008,OBJ+0x6000)
 def hook(self,u,address,size,user):
  if address==STOP+0xb00:
   u.reg_write(UC_X86_REG_XMM0,0);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  elif address-BASE==self.stopAt:u.reg_write(UC_X86_REG_RIP,STOP)
  else:
   if address-BASE==0x504e30:self.notified.append(u.reg_read(UC_X86_REG_RDX)&255)
   super().hook(u,address,size,user)
 def call(self,kind,mode,excluded):
  packet=OBJ+0x1a000;self.u.mem_write(packet,bytes(0x400));self.u.mem_write(packet+0x24,bytes([kind]));self.u.mem_write(packet+0x121,bytes([mode]))
  for off in excluded:self.u.mem_write(packet+off,b'\1')
  self.u.reg_write(UC_X86_REG_R14,OBJ+0x1b000);self.u.reg_write(UC_X86_REG_RSI,packet);self.u.reg_write(UC_X86_REG_R15,0);self.stopAt=0x43da77
  self.invoke(0x43da28,[]);self.stopAt=None
checks={k:[] for k in ('selection','caller','overrides','lifetime','refresh','rearm','mixedTriggers','disabled','extension')};stubs=set()
def record(key,c,**row):checks[key].append(row);stubs.update(c.stubs)
def step(c,dt=1/60):c.qualify();c.update(dt)
def start(copies=1,fps=None,extra=None):
 fps=fps or 10
 c=Caller()
 for _ in range(copies):
  for root in ROOTS:c.grant(root)
 if extra is not None:c.grant(extra)
 for _ in range(math.ceil(1.2*fps)):step(c,1/fps)
 assert all(sum(n['id']==root for n in c.nodes())==int(bool(copies)) for root in ROOTS)
 return c
def active(c):return any(n['id']==LEAF and not n['flags']&0x800c0003 for n in c.nodes())
def verify(c,expected):
 values=c.values();assert all(math.isclose(v,expected,rel_tol=1e-6) for v in values['rates']) and math.isclose(values['poise'],expected,rel_tol=1e-6),values
 return values
for copies,hero in itertools.product((1,2,3,6),range(11)):
 c=Selection([[EFFECT]]*copies,hero);bits=c.select();assert all(i*6 in bits for i in range(copies))
 c.invoke(0xe6e150,[OBJ+0x9200,EFFECT]);selected=[c.invoke(0xe6e3b0,[OBJ+0x9200,n])&0xffffffff for n in range(3)];assert selected==list(ROOTS)
 record('selection',c,copies=copies,hero=hero,bits=bits,roots=selected)
for copies,mode,excluded,kind in itertools.product((0,1,3),(0,3),((),(0x2b4,),(0x2b9,),(0x2ba,)),range(16)):
 c=start(copies);c.call(kind,mode,excluded);step(c);step(c)
 assert c.notified==([] if excluded else [kind])
 record('caller',c,copies=copies,mode=mode,excluded=excluded,kind=kind,notified=c.notified,values=verify(c,.8 if copies and not excluded and kind in KINDS else 1))
print('PASS selection/caller',len(checks['selection']),len(checks['caller']),flush=True)
# Actual category1001 rows and native conversion table, not invented overrides.
conversion=list(x.pe.get_data(0x2cae0b8,13))
for extra,mode,kind in itertools.product((40,1650),(0,3),range(12)):
 c=start();c.grant(extra);c.qualify();c.call(kind,mode,());c.update(1/60);step(c)
 replacement=x.rows[extra][0x148+kind];expected=kind if mode==3 or not replacement else conversion[replacement]
 assert c.notified==[expected],(extra,mode,kind,c.notified,expected)
 leaf_rate=.8 if expected in KINDS else 1;assert active(c)==(expected in KINDS)
 values=c.values();other_active=any(n['id']==extra and not n['flags']&0x800c0003 for n in c.nodes())
 other=x.spells[str(extra)]
 expected_rates=[leaf_rate*(other[k+'DamageCutRate'] if other_active else 1) for k in ('neutral','magic','fire','thunder','dark')]
 expected_poise=leaf_rate*(other['toughnessDamageCutRate'] if other_active else 1)
 assert all(math.isclose(v,w,rel_tol=1e-6) for v,w in zip(values['rates'],expected_rates)) and math.isclose(values['poise'],expected_poise,rel_tol=1e-6),(extra,mode,kind,values,expected_rates,expected_poise)
 record('overrides',c,otherEffect=extra,mode=mode,kind=kind,replacement=replacement,notified=c.notified,leafActive=active(c),otherActive=other_active,values=values)
print('PASS overrides',len(checks['overrides']),flush=True)
for copies,fps in itertools.product((1,3),(30,60,120)):
 c=start(copies,fps);c.call(4,0,());changes=[];previous=None
 for frame in range(21*fps):
  step(c,1/fps);present=active(c)
  if present!=previous:
   changes.append(dict(frame=frame,active=present,values=verify(c,.8 if present else 1)));previous=present
 assert [v['active'] for v in changes]==[False,True,False],(copies,fps,changes)
 assert abs(changes[-1]['frame']-changes[1]['frame']-20*fps)<=4
 record('lifetime',c,copies=copies,fps=fps,changes=changes)
 print('PASS lifetime',copies,fps,flush=True)
for kind,hits in itertools.product((4,11),((0,),(0,1),(0,60),(0,300))):
 c=start(3);changes=[];previous=None;grant_frames=[]
 for frame in range(26*60):
  if frame in hits:c.call(kind,0,())
  count=c.grants.count(LEAF);step(c);grant_frames.extend([frame]*(c.grants.count(LEAF)-count));present=active(c)
  assert sum(n['id']==LEAF for n in c.nodes())<=1
  if present!=previous:changes.append([frame,present]);previous=present;verify(c,.8 if present else 1)
 assert [v[1] for v in changes]==[False,True,False],(kind,hits,changes)
 assert len(grant_frames)==(1 if hits in ((0,),(0,1)) else 2),(kind,hits,grant_frames)
 assert abs(changes[-1][0]-grant_frames[-1]-1200)<=5
 record('refresh',c,kind=kind,hits=hits,grantFrames=grant_frames,changes=changes)
 print('PASS refresh',kind,hits,flush=True)
for kind,fps in itertools.product(KINDS,(30,60,120)):
 c=start(3,fps);frames=[]
 for frame in range(3*fps):
  count=c.grants.count(LEAF);c.call(kind,0,());step(c,1/fps);frames.extend([frame]*(c.grants.count(LEAF)-count))
 assert len(frames) in (3,4),(kind,fps,frames)
 assert frames[0]<=3 and 0<frames[1]-frames[0]<=fps+5,(kind,fps,frames)
 assert all(abs(b-a-fps)<=5 for a,b in zip(frames[1:],frames[2:])),(kind,fps,frames)
 record('rearm',c,kind=kind,fps=fps,grantFrames=frames,values=verify(c,.8))
 print('PASS rearm',kind,fps,frames,flush=True)
for first,second in itertools.product(KINDS,repeat=2):
 # Warm at 60 Hz so both hits precede the next rearm boundary for every kind.
 # Same-kind hits across that boundary can refresh even less than 0.1 s apart.
 c=start(3,fps=60);frames=[]
 for frame in range(12):
  before=c.grants.count(LEAF)
  if frame in (0,6):c.call(first if frame==0 else second,0,())
  step(c);frames.extend([frame]*(c.grants.count(LEAF)-before))
 assert len(frames)==(1 if first==second else 2),(first,second,frames)
 record('mixedTriggers',c,first=first,second=second,grantFrames=frames,values=verify(c,.8))
print('PASS mixedTriggers',len(checks['mixedTriggers']),flush=True)
for mask in (1,2,0x40000,0x80000000):
 c=Caller();c.insert(LEAF);step(c);ptr=struct.unpack('<Q',c.u.mem_read(OBJ+8,8))[0];c.u.mem_write(ptr+0x68,struct.pack('<I',mask))
 record('disabled',c,mask=mask,values=verify(c,1))
for extra in (None,7006400,8330500):
 c=Caller()
 if extra is not None:c.grant(extra)
 c.grant(LEAF);step(c,0);step(c,1)
 node=next(n for n in c.nodes() if n['id']==LEAF);assert math.isclose(node['lifetime'],19,abs_tol=.001),node
 record('extension',c,otherEffect=extra,node=node,values=verify(c,.8))
out=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),attachParamSha256=sha(raw),effect=EFFECT,roots=ROOTS,leaf=LEAF,
 guards=[dict(id=id,kind=kind) for id,kind in zip(GUARDS,KINDS)],rate=.8,duration=20,period=1,conversionTable=conversion,checks=checks,
 native=dict(selection='4FEA30 → E6E150 → E6E3B0',caller='43DA28..43DA77 → 42C120 → 6D1BE0 → 504E30',conversion='48D8F0 / 48D920 / 507C40 → EA0CF0 / E6D510',update='5057D0 → 50ACD0',grant='3C7FD0 → 3C80A0 → 3DB410',incoming='503800',poise='502270'),
 stubs=sorted(stubs|{'Explicit reaction byte, source mode and three exclusion bytes; component+40 has neutral resources and virtual+10 returns float0; component+48 absent.',
 'Native caller block starts after outer hit gates. Full collision, HP changes and animation reactions are not simulated.'}),
 limitations=['The preceding full-hit gates and origins of packet exclusions/source mode remain untraced.',
 'Only neutral reaction components and two actual override rows are exercised; alternate component+48 branch is not covered.',
 'No full equipment rebuild/unequip, scene collision, final HP, animation selection, DLL, multiplayer, death or reload.'],gameplayVerified=False)
a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print('PASS counts',{k:len(v) for k,v in checks.items()},sum(map(len,checks.values())),flush=True)
