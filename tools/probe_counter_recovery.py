"""Execute counter-hit recovery selection, hit predicates and HP packets.

Original native basic blocks are composed with explicit hit/actor contexts.
TAE relocation and dispatch execute, but the full animation scheduler and
collision pipeline do not. No final current-HP write or complete gameplay.
"""
import argparse,itertools,json,math,struct
from pathlib import Path
from native_effect_runtime import BASE,OBJ,STACK,STOP,Inputs,Chain,sha
from native_ailment_runtime import Ailment
from native_animation_runtime import NativeTae
from unicorn.x86_const import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','animations','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted);inputs=x
attach=a.extracted.with_suffix('.AttachEffectParam.param').read_bytes();rows=Inputs.table(attach,0x44)
assert sha(attach)=='ae8128ed510a532d0fa7cb56fa9c86e4a44c9d815dd4ee01c05821d5f50a9827'
assert len(rows)==struct.unpack_from('<H',attach,10)[0] and len(x.rows)==struct.unpack_from('<H',x.param,10)[0]
assert sha(x.param)=='07ec636c5565d4551efeb53e6f08bc633b2aa4f2129f13c61b0638d69b1bc176'
FAMILIES=[dict(effect=e,root=r,percent=p) for e,r,p in ((7160000,7160000,2.5),(6160000,7160001,3.3),(6160001,7160002,4))]
for f in FAMILIES:
 ar=x.x['tables']['AttachEffectParam'][str(f['effect'])];r=x.spells[str(f['root'])]
 assert ar['passiveSpEffectId_1']==f['root'] and all(ar[k]==-1 for k in ('passiveSpEffectId_2','passiveSpEffectId_3','permanentSpEffectId','exclusivityId'))
 assert (r['spCategory'],r['stateInfo'],r['effectEndurance'],r['motionInterval'],r['invocationConditionsStateChange1'],r['changeHpPoint'])==(0,2203,-1,0,2106,0)
 assert math.isclose(r['changeHpRate'],-f['percent'],rel_tol=1e-6)
assert (x.spells['320']['stateInfo'],x.spells['320']['effectEndurance'],x.spells['320']['spCategory'])==(2106,0,0)
# Pin the actual unity constant loaded into XMM7 by the outer hit function.
assert x.pe.get_data(0x43a2fe,8)==bytes.fromhex('F30F103D9693EB02')
assert struct.unpack('<f',x.pe.get_data(0x32f369c,4))[0]==1
# Raw subtype 2 is thrust: use the real row, not presumed enumeration order.
assert math.isclose(struct.unpack_from('<f',x.rows[31],0x24)[0],x.spells['31']['thrustDamageCutRate'],rel_tol=1e-7)
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
 def insert_target(self,id):return self.invoke(0x50d060,[TARGET,id,OBJ+0xa00,-1,0,0x3f800000,0,0,16])&0xffffffff
 def tick_target(self,dt=0):
  self.invoke(0x5057d0,[TARGET,0,0],{UC_X86_REG_XMM1:1});self.invoke(0x50acd0,[TARGET,0,0],{UC_X86_REG_XMM1:dt})
 def flag(self,typ=2):
  self.u.mem_write(PACKET,bytes(0x400));self.u.mem_write(PACKET+0x25,bytes([typ]))
  for reg,v in ((UC_X86_REG_R15,WRAPPER),(UC_X86_REG_R14,PACKET),(UC_X86_REG_RBP,OUT)):self.u.reg_write(reg,v)
  self.stopAt=0x43a696
  # Both branches stop: no vulnerability jumps past the positive-only block.
  self.invoke(0x43a605,[],{UC_X86_REG_XMM7:1});self.stopAt=None
  return self.u.mem_read(PACKET+0x2c1,1)[0],list(struct.unpack('<5f',self.u.mem_read(OUT-0x60,20)))
 def mark(self,local=True):
  self.q(OBJ+0x574e8,OBJ+0x6000 if local else ACTOR)
  self.u.reg_write(UC_X86_REG_R15,OBJ+0x6000);self.u.reg_write(UC_X86_REG_R14,PACKET)
  self.stopAt=0x43ca60;self.invoke(0x43ca3a,[]);self.stopAt=None
 def pulse(self,maximum=1000,dt=1/60):
  self.qualify();self.update(dt);return self.hp_packet(maximum)[0]
class Window(Counter):
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if pc in (0x3ced90,0x4d1b20):ret(OBJ+0xd800 if pc==0x3ced90 else 0)
  elif pc==0x26909a0:ret(u.reg_read(UC_X86_REG_RAX))
  else:super().hook(u,address,size,user)
 def context(self,tae,animation):
  ctx=OBJ+0xd100;self.u.mem_write(ctx,bytes(0x40))
  for _ in range(10000):
   if not self.invoke(0x27d0400,[tae.animations[animation],ctx]):break
   if struct.unpack('<I',self.u.mem_read(ctx,4))[0]!=66:continue
   payload=struct.unpack('<Q',self.u.mem_read(ctx+8,8))[0]
   if struct.unpack('<i',self.u.mem_read(payload,4))[0]==31:return ctx
  raise AssertionError((animation,'no Type66 row31'))
 def event(self,tae,animation=40000):
  ctx=self.context(tae,animation);self.q(OBJ+0xd018,OBJ+0x6000)
  self.invoke(0x410ca0,[OBJ+0xd000,ctx])

checks={k:[] for k in ('selection','composed','mixed','hp','repeat','disabled','animation')};stubs=set()
def record(key,c,**row):checks[key].append(row);stubs.update(c.stubs)
def start(roots):
 c=Counter()
 for root in roots:c.grant(root)
 c.qualify();c.update(0);return c
def pulses(c,maximum=1000,fps=60,n=5):return [c.pulse(maximum,1/fps) for _ in range(n)]
for f,copies,hero in itertools.product(FAMILIES,(1,2,3,6),range(11)):
 c=Selection([[f['effect']]]*copies,hero);bits=c.select();assert all(i in bits for i in range(0,copies*6,6)),(f,copies,hero,bits)
 c.invoke(0xe6e150,[OBJ+0x9200,f['effect']]);decoded=[c.invoke(0xe6e3b0,[OBJ+0x9200,n])&0xffffffff for n in range(3)]
 assert decoded==[f['root'],0xffffffff,0xffffffff]
 v=start([f['root']]*copies);v.grant(320);values=pulses(v);assert values==[0,round(f['percent']*10),0,0,0]
 stubs.update(v.stubs);record('selection',c,effect=f['effect'],copies=copies,hero=hero,bits=bits,decoded=decoded,hp=values)
print('PASS selection',len(checks['selection']),flush=True)
for f,target,typ,local in itertools.product(FAMILIES,(None,31,99008),range(5),(True,False)):
 c=start([f['root']])
 if target:c.insert_target(target)
 c.tick_target();flag,rates=c.flag(typ);c.mark(local);values=pulses(c)
 eligible=target==99008 or target==31 and typ==2
 assert bool(flag&128)==eligible
 assert values==[0,round(f['percent']*10) if eligible and local else 0,0,0,0]
 record('composed',c,effect=f['effect'],target=target,physicalType=typ,local=local,flag=flag,counterRates=rates,hp=values)
for counts in itertools.product(range(4),repeat=3):
 c=start([f['root'] for f,n in zip(FAMILIES,counts) for _ in range(n)]);before=pulses(c);assert not any(before)
 c.insert_target(31);c.tick_target();c.flag(2);c.mark();values=pulses(c)
 assert sum(values)==sum(round(f['percent']*10) for f,n in zip(FAMILIES,counts) if n)
 record('mixed',c,counts=counts,hp=values)
for f,maximum,copies,fps in itertools.product(FAMILIES,(1,137,1000,10000),(1,3),(30,60,120)):
 c=start([f['root']]*copies);c.grant(320);values=pulses(c,maximum,fps)
 expected={1:[0,0,0],137:[3,4,5],1000:[25,33,40],10000:[250,330,400]}[maximum][FAMILIES.index(f)]
 assert values==[0,expected,0,0,0],(f,maximum,copies,fps,values)
 record('hp',c,effect=f['effect'],maximum=maximum,copies=copies,fps=fps,hp=values)
print('PASS composed/mixed/hp',len(checks['composed']),len(checks['mixed']),len(checks['hp']),flush=True)
for f,frames,burst,fps in itertools.product(FAMILIES,([0],[0,1],[0,2],[0,5],list(range(10))),(1,3),(30,60,120)):
 c=start([f['root']]);c.insert_target(31);c.tick_target();c.flag(2);values=[]
 for frame in range(15):
  if frame in frames:
   for _ in range(burst):c.mark()
  values.append(c.pulse(1000,1/fps))
 assert values==[round(f['percent']*10) if frame-1 in frames else 0 for frame in range(15)]
 record('repeat',c,effect=f['effect'],hitFrames=frames,sameFrameHits=burst,fps=fps,hp=values)
for f in FAMILIES:
 c=start([f['root']]);c.grant(320);c.pulse();c.qualify();c.update(1/60)
 ptr=struct.unpack('<Q',c.u.mem_read(OBJ+8,8))[0]
 while struct.unpack('<i',c.u.mem_read(ptr+8,4))[0]!=f['root']:ptr=struct.unpack('<Q',c.u.mem_read(ptr+0x38,8))[0]
 for mask in (1,2,0x40000,0x80000000):
  c.u.mem_write(ptr+0x68,struct.pack('<I',mask));value=c.hp_packet(1000)[0];assert value==0
  record('disabled',c,effect=f['effect'],mask=mask,hp=value)
print('PASS repeat/disabled',len(checks['repeat']),len(checks['disabled']),flush=True)
animations=json.loads(a.animations.read_text());bundle=animations['bundles'][0]
assert bundle['sha256']=='806e6b218d747277ab45e14f45ca80b9ecf8c13ada22f89db2d3ef23caa62b2a'
tae=next(t for t in bundle['taes'] if t['ID']==2000)
raw=Path(str(a.animations)+'.2000.tae').read_bytes()
for animation in (40000,40005,40060,40590,41021,41141):
 c=Window();native=NativeTae(c,raw,tae['sha256']);ctx=c.context(native,animation)
 payload=struct.unpack('<Q',c.u.mem_read(ctx+8,8))[0];assert struct.unpack('<i',c.u.mem_read(payload,4))[0]==31
 c.event(native,animation);c.qualify();c.update(0);assert [n['id'] for n in c.nodes()]==[31]
 # Compose dispatch with counter predicate using this actor as the receiver.
 c.q(ACTOR+0x190,OBJ);flag,rates=c.flag(2);assert flag==128 and math.isclose(rates[0],1.1,rel_tol=1e-6)
 record('animation',c,tae=2000,animation=animation,eventType=66,nodes=c.nodes(),counterRates=rates)
print('PASS animation',len(checks['animation']),flush=True)
out=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),attachParamSha256=sha(attach),
 animationSha256=bundle['sha256'],taeSha256=sha(raw),families=FAMILIES,marker=320,checks=checks,
 native=dict(selection='4FEA30 → E6E150 → E6E3B0',window='27D0F10 → 27D0400 → 410CA0 → 40FF20 → 3C8BE0',predicate='43A605..43A696/43A72B → 503800 → EA0980',marker='43CA3A..43CA60 → 3D4180 → 3C7FD0',grant='3C7FD0 → 3C80A0 → 3DB410',update='5057D0 → 50ACD0',hp='506EC0'),
 stubs=sorted(stubs|{'Explicit independent receiver container, runtime physical subtype and local identity; native caller blocks composed, not full collision.', 'HP aggregation temporarily has no physical owner; final current HP is not written.', '3CED90/4D1B20 explicit ordinary animation-owner context; security-cookie sink.'}),
 limitations=['No complete collision pipeline, attack PARAM-to-runtime subtype construction, outer hit eligibility, final HP cap/write or healing modifiers.',
 'Type66 dispatch and raw event payload verified; full scheduling, per-frame keepalive and attack-window reachability are not simulated.',
 'State110 row99008 is a parameter control, not claimed to be a reachable wider counter source.',
 'Same-update marker grants merge; a complete game scheduling boundary may differ from the explicit update ordering.',
 'No DLL hooks, equipment rebuild, death, reload or multiplayer.'],gameplayVerified=False)
a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('PASS total',sum(map(len,checks.values())),flush=True)
