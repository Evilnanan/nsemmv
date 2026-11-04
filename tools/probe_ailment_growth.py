"""Execute ailment-gauge attack growth, tier selection and delayed clearing.

Native local-player update, resistance/state queries, timer, grant, category-206
selection and attack arithmetic use pinned inputs. This is not gameplay.
"""
import argparse,itertools,json,math,struct
from pathlib import Path
from native_effect_runtime import BASE,OBJ,STOP,Chain,Inputs,sha
from native_ailment_runtime import Ailment
from unicorn.x86_const import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','systems','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted);systems=json.loads(a.systems.read_text())
assert systems['hashes']['regulation.bin']==x.x['hashes']['regulation.bin']
raw=a.systems.with_suffix('.PlayerCommonParam.param').read_bytes();player=Inputs.table(raw,0x2dc)[0]
common=systems['tables']['PlayerCommonParam']['0']
interval,maximum,seed,marker=struct.unpack_from('<fiii',player,0x2cc)
assert (interval,maximum,seed,marker)==(20,10,7039900,7037701)
assert (common['statusGaugeStackTriggerInterval'],common['statusGaugeMaxStack'],common['statusGaugeStackEffectId'],common['statusGaugeEffectId_Vfx'])==(interval,maximum,seed,marker)
assert x.pe.get_data(0x6668d8,10)==bytes.fromhex('C78658060000000080BF')
states=list(struct.unpack('<7H',x.pe.get_data(0x6708e9+7+0x33382b8,14)))
assert states==[2,5,6,116,260,436,437]
assert x.spells['7037700']['stateInfo']==2129 and x.spells['7037702']['stateInfo']==2209
assert x.x['tables']['AttachEffectParam']['7037700']['passiveSpEffectId_1']==7037700
assert x.x['tables']['AttachEffectParam']['7037700']['passiveSpEffectId_2']==7037702
ladder=list(range(seed,seed+10));rates=[1.035,1.07,1.11,1.155,1.2,1.25,1.3,1.35,1.4,1.45]
for id,rate in zip(ladder,rates):
 r=x.spells[str(id)]
 assert r['spCategory']==206 and r['invocationConditionsStateChange1']==2209 and r['effectEndurance']==-1
 assert all(math.isclose(r[k+'AttackRate'],rate,rel_tol=1e-6) for k in ('physics','magic','fire','thunder','dark'))
assert x.spells[str(marker)]['spCategory']==10 and x.spells[str(marker)]['invocationConditionsStateChange1']==2209
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

class Growth(Actor):
 def __init__(self,copies=1):
  super().__init__();self.u.mem_map(OBJ+0x80000,0x10000);self.u.mem_write(OBJ+0x80000,player)
  self.stubs.add("native constructor 6668D8 initializes actor +658 timer to -1; actor fixture supplies this field")
  self.u.mem_write(OBJ+0x6658,struct.pack('<f',-1))
  for _ in range(copies):self.grant(7037700);self.grant(7037702)
  self.qualify();self.update(0)
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if pc==0xe81650:
   self.stubs.add('E81650 actual PlayerCommon PARAM lookup');ptr=u.reg_read(UC_X86_REG_RCX);self.q(ptr,OBJ+0x80000);ret(ptr)
  elif pc==0xdf0ac0:self.stubs.add('DF0AC0 no network peer for clear notification');ret()
  else:super().hook(u,address,size,user)
 def step(self,dt):
  self.invoke(0x670840,[OBJ+0x6000],{UC_X86_REG_XMM1:dt});self.qualify();self.update(dt)
 def build(self,channel,value):self.u.mem_write(OBJ+0x9010+channel*4,struct.pack('<i',500-value))
checks=dict(gauges=[],activeStates=[],growth=[],numeric=[],timeline=[],clear=[]);stubs=set()
def record(key,c,**row):checks[key].append(row);stubs.update(c.stubs)
def count(c):return c.invoke(0x505e20,[OBJ])&0xffffffff
def buffs(c):return [n['id'] for n in c.nodes() if n['id'] in ladder]
for copies,channel,buildup in itertools.product((0,1,3),range(7),(0,1,499)):
 c=Growth(copies);c.build(channel,buildup);c.step(.01)
 expected=bool(copies and buildup)
 assert count(c)==int(expected) and buffs(c)==([seed] if expected else [])
 assert all(math.isclose(v,rates[0] if expected else 1,rel_tol=1e-6) for v in c.attack())
 record('gauges',c,copies=copies,channel=channel,buildup=buildup,count=count(c),rates=c.attack())
# Zero-life actual marker rows are made active by the real initial update.
# These test the state predicate, not the process of developing each ailment.
stateRows=dict(zip(states,(103,104,102,109,105,108,107)))
for copies,(state,id) in itertools.product((0,1),stateRows.items()):
 c=Growth(copies);c.insert(id);c.qualify();c.update(0)
 assert c.invoke(0x508e20,[OBJ,state])&255
 c.step(.01);assert count(c)==int(bool(copies))
 record('activeStates',c,copies=copies,state=state,marker=id,count=count(c),rates=c.attack())
for copies,multiple in itertools.product((0,1,3),(False,True)):
 c=Growth(copies)
 for channel in (range(7) if multiple else [0]):c.build(channel,1)
 steps=[]
 for index in range(12):
  c.step(.01 if index==0 else 20.01);level=min(index+1,10) if copies else 0
  assert count(c)==level and buffs(c)==([seed+level-1] if level else [])
  assert all(math.isclose(v,rates[level-1] if level else 1,rel_tol=1e-6) for v in c.attack())
  steps.append(dict(index=index,level=level,rates=c.attack(),buffs=buffs(c)))
 record('growth',c,copies=copies,multiple=multiple,steps=steps,nodes=c.nodes())
for level,kind in itertools.product(range(1,11),(0,1,2,4,5)):
 c=Growth();c.grant(seed+level-1);c.qualify();c.update(0);values=c.attack(kind)
 assert all(math.isclose(v,1 if kind==5 else rates[level-1],rel_tol=1e-6) for v in values),(level,kind,values)
 record('numeric',c,level=level,kind=kind,rates=values)
for fps in (30,60,120):
 c=Growth();c.build(0,1);history=[];previous=None
 for frame in range(42*fps):
  if frame==10*fps:c.build(0,0)
  if frame==19*fps:c.build(0,1)
  if frame==25*fps:c.build(0,0)
  if frame==41*fps:c.build(0,1)
  c.step(1/fps);level=count(c)
  if level!=previous:history.append(dict(frame=frame,time=frame/fps,level=level,rates=c.attack()));previous=level
 assert [r['level'] for r in history]==[1,2,0,1]
 for row,expected in zip(history,(0,20,40,41)):assert abs(row['time']-expected)<=3.01/fps
 record('timeline',c,fps=fps,transitions=history)
for copies,level in itertools.product((1,3),(1,5,10)):
 c=Growth(copies);c.build(0,1)
 for index in range(level):c.step(.01 if index==0 else 20.01)
 c.build(0,0);c.step(19);assert count(c)==level
 before=c.attack();c.step(1);assert count(c)==level # equality is not expiry
 c.step(.001);assert count(c)==0 and buffs(c)==[] and c.attack()==[1]*5
 record('clear',c,copies=copies,level=level,before=before,after=c.attack(),remaining=c.nodes())
output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),
 playerParamSha256=sha(raw),effect=7037700,roots=[7037700,7037702],interval=interval,maximum=maximum,seed=seed,marker=marker,ladder=ladder,rates=rates,states=states,
 rows={str(id):x.spells[str(id)] for id in [7037700,7037702,marker]+ladder},checks=checks,
 native=dict(update='670840',timerConstructor='6668D8',anyBuildup='42D080',state='508E20 (AL)',count='505E20',clear='505190',
 grant='3C7FD0',insert='50D060',qualify='5057D0',effectUpdate='50ACD0',attack='502830'),
 stubs=sorted(stubs|{'explicit resistance-channel inputs and active state-marker arrivals; full natural buildup/decay, death, reload and network behavior not simulated',
 '20.01-second updates isolate tier progression; separate 30/60/120 Hz timelines check real-sized update steps'}),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS', {k:len(v) for k,v in checks.items()}, 'ailment-gauge growth cases')
