"""Trace low-health poison/rot curses from native HP ratio to status onset.

The original caller block supplies the computed HP ratio to qualification.
Native selection, self-grants, conditional cycles, resistance, onset and HP
aggregation run on pinned rows. Resource/owner identity and time are fixtures;
no final HP write, natural decay, death/reload or multiplayer is simulated.
"""
import argparse,itertools,json,math,struct
from pathlib import Path
from native_effect_runtime import BASE,OBJ,STOP,Chain,Inputs,sha
from native_ailment_runtime import Ailment
from unicorn.x86_const import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted)
raw=a.extracted.with_suffix('.AttachEffectParam.param').read_bytes();rows=Inputs.table(raw,0x44)
families=[]
for id,kind,field,period,state,category,percent,flat,cycle in (
 (6851300,0,'poizonAttackPower',.22,2,10004,.1,10,505),
 (6851400,1,'diseaseAttackPower',.24,5,10005,.15,15,1120)):
 attach=x.x['tables']['AttachEffectParam'][str(id)];root=x.spells[str(id)];leaf=x.spells[str(id+1)]
 assert attach['passiveSpEffectId_1']==id and attach['exclusivityId']==-1
 assert all(attach[k]==-1 for k in ('passiveSpEffectId_2','passiveSpEffectId_3','permanentSpEffectId'))
 assert root['spCategory']==10 and root['stateInfo']==0 and root['effectEndurance']==-1
 assert root['cycleOccurrenceSpEffectId']==id+1 and root['replaceSpEffectId']==-1
 assert all(root['invocationConditionsStateChange'+str(i)]==0 for i in (1,2,3))
 assert math.isclose(root['conditionHp'],84.99,rel_tol=1e-6) and root['conditionHpRate']==-1
 assert math.isclose(root['motionInterval'],period,rel_tol=1e-6)
 assert (leaf['stateInfo'],leaf['spCategory'],leaf[field],leaf['effectEndurance'],leaf['cycleOccurrenceSpEffectId'],leaf['replaceSpEffectId'])==(state,category,2,40,cycle,-1)
 assert math.isclose(leaf['motionInterval'],1.3,rel_tol=1e-6) and math.isclose(leaf['changeHpRate'],percent,rel_tol=1e-6) and leaf['changeHpPoint']==flat
 assert x.spells[str(cycle)]['changeHpRate']==x.spells[str(cycle)]['changeHpPoint']==0
 families.append(dict(effect=id,root=id,leaf=id+1,kind=kind,field=field,conditionHp=root['conditionHp'],interval=root['motionInterval'],amount=2,
                      duration=40,damageInterval=leaf['motionInterval'],percent=leaf['changeHpRate'],flat=flat,cycle=cycle))
assert x.spells['9642']['disablePoison']==x.spells['9642']['disableDisease']==1
# Pin the original caller block and its target independently of inferred names.
block=x.pe.get_data(0x3e0d94,0x21)
assert block.hex()=='488b87b8010000488b08e83d600400488b8b900100000f28c84c8bc7e81b4a1200'
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


class Health(Actor):
 def __init__(self,kind=0,resistance=10000):
  self.contexts=[];self.shots=[];super().__init__(kind,resistance)
  self.q(OBJ+0xf000,OBJ+0xe000)
  self.stubs.add('3E0D94..3E0DB5 original health-ratio caller block; ordinary actor selected explicitly, alternate-owner selection not executed')
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if pc==0x3e0da3:self.contexts.append(struct.unpack('<f',(u.reg_read(UC_X86_REG_XMM0)&0xffffffff).to_bytes(4,'little'))[0])
  elif pc==0x3e0db5:u.reg_write(UC_X86_REG_RIP,STOP)
  elif pc==0x3ced90:self.stubs.add('3CED90 explicit owner animation context for status emitter');ret(OBJ+0xd000)
  elif pc==0x4d1b20:self.stubs.add('4D1B20 ordinary locally active actor');ret()
  elif pc==0x3975d0:self.stubs.add('3975D0 Behavior emission recorder; no actual effect projectile or collision');self.shots.append(u.reg_read(UC_X86_REG_RDX));ret(1)
  elif pc==0x26909a0:ret(u.reg_read(UC_X86_REG_RAX))
  else:super().hook(u,address,size,user)
 def qualify_health(self,current=800,maximum=1000):
  assert maximum>0
  self.u.mem_write(OBJ+0xe140,struct.pack('<ii',current,maximum))
  self.u.reg_write(UC_X86_REG_RBX,OBJ+0x6000);self.u.reg_write(UC_X86_REG_RDI,OBJ+0x6000)
  self.invoke(0x3e0d94,[0,0])
 def step(self,current=800,maximum=1000,dt=1/60):
  self.qualify_health(current,maximum);self.update(dt)
 def active_leaf(self,id):return [n for n in self.nodes() if n['id']==id and not n['flags']&0x800c0003]

checks={k:[] for k in ('selection','threshold','timing','transitions','onset','lifetime','repeat','immunity')};stubs=set()
def record(group,c,**values):checks[group].append(values);stubs.update(c.stubs)
def f32(v):return struct.unpack('<f',struct.pack('<f',v))[0]
for f,copies,hero in itertools.product(families,(1,2,3,6),range(11)):
 slots=[[7000000,-1,-1,f['effect']]]*copies;c=Selection(slots,hero);bits=c.select();roots=[]
 for index in range(copies):
  assert index*6+3 in bits
  id=struct.unpack('<i',c.u.mem_read(OBJ+0xa000+index*0x80+0x24,4))[0];assert id==f['effect']
  c.invoke(0xe6e150,[OBJ+0x9200,id]);roots.append(c.invoke(0xe6e3b0,[OBJ+0x9200,0])&0xffffffff)
 assert roots==[f['root']]*copies
 record('selection',c,effect=f['effect'],copies=copies,hero=hero,curseSlot=3,bits=bits,roots=roots)
print('PASS selection',len(checks['selection']),flush=True)
for f,maximum,copies in itertools.product(families,(100,1000,10000,100000),(0,1,3)):
 bound=f32(f['conditionHp']*f32(.01));near=math.floor(bound*maximum)
 for current in (0,near,near+1,maximum):
  c=Health(f['kind'])
  for _ in range(copies):c.grant(f['root'])
  c.step(current,maximum,0);ratio=c.contexts[-1];assert ratio==f32(f32(current)/f32(maximum))
  active=ratio<=bound;amount=10000-c.remaining()
  assert amount==(2*copies if active else 0),(f,current,maximum,copies,ratio,bound,amount)
  assert c.hp_packet(maximum)==[0]*7 and not c.active_leaf(f['leaf'])
  record('threshold',c,effect=f['effect'],current=current,maximum=maximum,copies=copies,ratio=ratio,bound=bound,enabled=active,amount=amount)
print('PASS threshold',len(checks['threshold']),flush=True)
baselines={}
for f,fps,copies in itertools.product(families,(30,60,120),(1,2,3,6)):
 c=Health(f['kind'])
 for _ in range(copies):c.grant(f['root'])
 packets=[]
 for frame in range(3*fps):
  before=c.remaining();c.step(dt=1/fps);amount=before-c.remaining()
  if amount:packets.append(dict(frame=frame,amount=amount))
  assert c.hp_packet(1000)==[0]*7
 if copies==1:baselines[f['root'],fps]=packets
 else:assert packets==[dict(frame=p['frame'],amount=p['amount']*copies) for p in baselines[f['root'],fps]]
 assert all(p['amount']==2*copies for p in packets)
 assert all(abs((b['frame']-a['frame'])/fps-f['interval'])<=2/fps for a,b in zip(packets,packets[1:]))
 assert abs(len(packets)-3/f['interval'])<=1
 record('timing',c,effect=f['effect'],fps=fps,copies=copies,seconds=3,packets=packets,total=10000-c.remaining())
print('PASS timing',len(checks['timing']),flush=True)
for f,fps,copies in itertools.product(families,(30,60,120),(1,3)):
 c=Health(f['kind'])
 for _ in range(copies):c.grant(f['root'])
 phases=[]
 for current in (1000,800,900,800,1000):
  before=c.remaining();packets=[]
  for frame in range(fps):
   old=c.remaining();c.step(current,dt=1/fps)
   if old!=c.remaining():packets.append(dict(frame=frame,amount=old-c.remaining()))
  delta=before-c.remaining();assert (delta>0)==(current==800)
  assert not c.active_leaf(f['leaf']) and c.hp_packet(1000)==[0]*7
  phases.append(dict(current=current,accumulation=delta,packets=packets))
 record('transitions',c,effect=f['effect'],fps=fps,copies=copies,phases=phases)
print('PASS transitions',len(checks['transitions']),flush=True)
for f,resistance,maximum in itertools.product(families,(1,2,3,4,5),(101,1000)):
 c=Health(f['kind'],resistance);steps=[]
 for n in range(math.ceil(resistance/2)):
  c.grant(f['leaf']);c.step(maximum=maximum,current=maximum,dt=0)
  hp=c.hp_packet(maximum);triggered=n==math.ceil(resistance/2)-1
  expected=math.trunc(f32(-f32(f32(maximum*f['percent'])*f32(.01))-f['flat'])) if triggered else 0
  assert hp[0]==expected,(f,resistance,maximum,n,hp,expected)
  assert bool(c.active_leaf(f['leaf']))==triggered
  assert c.remaining()==(resistance if triggered else resistance-2*(n+1))
  steps.append(dict(grants=n+1,remaining=c.remaining(),hp=hp,nodes=c.nodes()))
 record('onset',c,effect=f['effect'],resistance=resistance,maximum=maximum,steps=steps)
print('PASS onset',len(checks['onset']),flush=True)
for f,fps in itertools.product(families,(30,60,120)):
 c=Health(f['kind'],2);c.grant(f['root']);c.step(800,dt=0);c.step(1000,dt=0);packets=[];expired=None
 for frame in range(42*fps):
  hp=c.hp_packet(1000)[0]
  if hp:packets.append(dict(frame=frame,hp=hp))
  if not c.active_leaf(f['leaf']):expired=frame;break
  c.step(1000,dt=1/fps)
 assert expired is not None and abs(expired/fps-40)<=3.01/fps,(f,fps,expired)
 assert len(packets)==31,(f,fps,len(packets),packets)
 assert all(p['hp']==(-11 if f['kind']==0 else -16) for p in packets)
 assert all(abs((b['frame']-a['frame'])/fps-1.3)<=3.01/fps for a,b in zip(packets,packets[1:]))
 record('lifetime',c,effect=f['effect'],fps=fps,expiredFrame=expired,packets=packets,nodes=c.nodes())
print('PASS lifetime',len(checks['lifetime']),flush=True)
# Repeated root pulses and explicit duplicate leaves while already poisoned do
# not multiply damage or refresh the 40-second ailment duration.
for f,copies in itertools.product(families,(1,3,6)):
 c=Health(f['kind'],2)
 for _ in range(copies):c.grant(f['root'])
 packets=[];lifetimes=[]
 for frame in range(2*60):
  c.step(dt=1/60);hp=c.hp_packet(1000)[0]
  if hp:packets.append(dict(frame=frame,hp=hp))
  if frame in (1,60,119):lifetimes.append(c.active_leaf(f['leaf'])[0]['lifetime'])
 assert len(c.active_leaf(f['leaf']))==1 and lifetimes[0]>lifetimes[1]>lifetimes[2]
 assert [p['hp'] for p in packets]==([-11,-11] if f['kind']==0 else [-16,-16]),(f,copies,packets)
 record('repeat',c,effect=f['effect'],copies=copies,packets=packets,lifetimes=lifetimes)
for f in families:
 c=Health(f['kind'],2);c.grant(9642)
 for _ in range(3):c.grant(f['root'])
 for _ in range(120):c.step()
 assert c.remaining()==2 and not c.active_leaf(f['leaf']) and c.hp_packet(1000)==[0]*7
 record('immunity',c,effect=f['effect'],immunity=9642,remaining=c.remaining(),nodes=c.nodes())
print('PASS repeat/immunity',len(checks['repeat']),len(checks['immunity']),flush=True)
output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),attachParamSha256=sha(raw),
 families=families,checks=checks,native=dict(selection='4FEA30 → E6E150 → E6E3B0',health='3E0D94..3E0DB5 → 426DE0 → 5057D0',
 cycle='50ACD0 → 3C7FD0',status='42D110 / 42CD70',hp='506EC0'),
 stubs=sorted(stubs|{'synthetic inventory: curse slot3 paired with positive7000000; draw legality not asserted',
 'initial HP/max HP, resistance and ordinary actor identity are fixtures; complete actor selection/death and HP writes not executed',
 'health caller block stopped at its exact boundary without popping a synthetic return overwritten by callee home space',
 'qualification and cycles run at explicit frame rates; natural resistance decay, growth, cures, external poison/rot conflicts, save/load and network not executed'}),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',{k:len(v) for k,v in checks.items()})
