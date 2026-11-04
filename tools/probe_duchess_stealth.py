"""Trace Duchess critical-animation stealth through native grants and expiry.

Actual TAE event dispatch, effect insertion, maintenance, replacement, timers
and perception getters execute with explicit actor and animation inputs.
This does not simulate complete throw selection, AI perception or gameplay.
"""
import argparse,itertools,json,math,struct
from pathlib import Path
from native_effect_runtime import BASE,OBJ,STOP,Chain,Inputs,sha
from native_ailment_runtime import Ailment
from native_animation_runtime import NativeTae
from unicorn.x86_const import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','animations','throws','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted)
t=json.loads(a.animations.read_text());throws=json.loads(a.throws.read_text())
assert t['bundles'][0]['sha256']=='1410035ad79edb410fa41420ec259fcb4a1037d748c9c4a3b6ae8d1366c76d0f'
assert throws['hashes']['regulation.bin']==x.x['hashes']['regulation.bin']
root,marker,leaf=9200002,7031801,7031803
assert x.x['tables']['AttachEffectParam']['7031800']['passiveSpEffectId_1']==root
assert x.x['tables']['AttachEffectParam']['7031800']['exclusivityId']==-1
r=x.spells[str(root)];assert r['spCategory']==20 and r['effectEndurance']==-1 and r['cycleOccurrenceSpEffectId']==7031800
r=x.spells['7031800'];assert r['effectEndurance']==3 and r['invocationConditionsStateChange1']==2038 and r['cycleOccurrenceSpEffectId']==7031802
r=x.spells[str(marker)];assert r['stateInfo']==2038 and r['effectEndurance']==0
r=x.spells['7031802'];assert r['spCategory']==0 and r['stateInfo']==600 and math.isclose(r['effectEndurance'],.1,abs_tol=1e-7) and r['replaceSpEffectId']==leaf
r=x.spells[str(leaf)];assert r['spCategory']==20 and r['stateInfo']==8 and r['effectEndurance']==10 and r['motionInterval']==11
assert math.isclose(r['sightSearchEnemyRate'],.01,abs_tol=1e-7) and r['hearingSearchEnemyRate']==0
assert struct.unpack_from('<2f',x.rows[leaf],0xfc)==(r['sightSearchEnemyRate'],0)
events=[dict(tae=ta['ID'],animation=an['ID'],**e) for bu in t['bundles'] for ta in bu['taes'] for an in ta['animations'] for e in an['events'] if e['Type']==67 and struct.unpack_from('<i',bytes.fromhex(e['hex']))[0]==marker]
assert len(events)==30 and all(e['animation']==31710 and e['StartTime']==0 and math.isclose(e['EndTime'],.1,abs_tol=1e-7) for e in events)
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

class Stealth(Actor):
 def hook(self,u,address,size,user):
  if address-BASE in (0x3ced90,0x4d1b20):
   self.stubs.add("3CED90/4D1B20 explicit animation-owner context")
   u.reg_write(UC_X86_REG_RAX,OBJ+0xd800 if address-BASE==0x3ced90 else 0)
   sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  else:super().hook(u,address,size,user)
 def event(self,active):
  self.q(OBJ+0xd018,OBJ+0x6000);self.q(OBJ+0xd108,OBJ+0xd200)
  self.u.mem_write(OBJ+0xd100,struct.pack('<I',67));self.u.mem_write(OBJ+0xd118,bytes([active]))
  self.u.mem_write(OBJ+0xd200,struct.pack('<i',7031801)+bytes(12))
  self.invoke(0x410ca0,[OBJ+0xd000,OBJ+0xd100])
 def rates(self):
  self.invoke(0x508890,[OBJ,0]);hear=struct.unpack('<f',struct.pack('<I',self.u.reg_read(UC_X86_REG_XMM0)&0xffffffff))[0]
  self.invoke(0x508a30,[OBJ,0,OBJ+0xd900,OBJ+0xd908,OBJ+0xd910])
  return (struct.unpack('<f',self.u.mem_read(OBJ+0xd900,4))[0],hear)

checks=dict(rawEvents=[],dispatch=[],lifetime=[],repeat=[],damage=[]);stubs=set();rawhashes={}
def record(key,c,**row):checks[key].append(row);stubs.update(c.stubs)
def step(c,fps):c.qualify();c.update(1/fps)
def equip(copies):
 c=Stealth()
 for _ in range(copies):c.grant(root)
 c.qualify();c.update(0)
 return c
def live(c):return [n for n in c.nodes() if n['id']==leaf and not n['flags']&0x800c0003]
def concealed(c):
 rates=c.rates();assert rates in ((1.,1.),(x.spells[str(leaf)]['sightSearchEnemyRate'],0.)),rates
 return rates[1]==0
for tid in (2020,2274,2279):
 c=equip(1);ta=next(ta for bu in t['bundles'] for ta in bu['taes'] if ta['ID']==tid)
 raw=Path(str(a.animations)+'.'+str(tid)+'.tae').read_bytes();rawhashes[str(tid)]=sha(raw)
 loader=NativeTae(c,raw,ta['sha256']);assert loader.id==tid and loader.bank==255
 ctx=OBJ+0xd100;c.u.mem_write(ctx,bytes(0x40));found=[]
 while c.invoke(0x27d0400,[loader.animations[31710],ctx]):
  if struct.unpack('<I',c.u.mem_read(ctx,4))[0]!=67:continue
  ptr=struct.unpack('<Q',c.u.mem_read(ctx+8,8))[0]
  if struct.unpack('<i',c.u.mem_read(ptr,4))[0]!=marker:continue
  payload=bytes(c.u.mem_read(ptr,16));assert payload==bytes.fromhex(events[0]['hex'])
  times=struct.unpack('<Q',c.u.mem_read(ctx+0x20,8))[0];start,end=struct.unpack('<f4xf',c.u.mem_read(times,12))
  assert start==0 and math.isclose(end,.1,abs_tol=1e-7)
  c.q(OBJ+0xd018,OBJ+0x6000);c.u.mem_write(ctx+0x18,b'\x01')
  c.invoke(0x410ca0,[OBJ+0xd000,ctx]);found.append(dict(payload=payload.hex(),start=start,end=end))
 assert len(found)==(2 if tid==2274 else 1)
 assert len([n for n in c.nodes() if n['id']==marker])==1
 record('rawEvents',c,tae=tid,events=found,nodes=c.nodes())

# The event's active byte is not a grant-once switch; repeated notifications
# maintain the zero-life marker through the actual 0.1-second animation span.
for copies,active,duplicates in itertools.product((0,1,3),(0,1),(1,2)):
 c=equip(copies);states=[]
 for frame in range(30):
  if frame<6:
   for _ in range(duplicates):c.event(active)
  step(c,60)
  states.append(dict(frame=frame,marker=bool(c.invoke(0x508e20,[OBJ,2038])&255),transition=bool(c.invoke(0x508e20,[OBJ,600])&255),concealed=concealed(c)))
 assert concealed(c)==bool(copies)
 assert len(live(c))==bool(copies)
 assert not states[-1]['marker'] and not states[-1]['transition']
 record('dispatch',c,copies=copies,active=active,duplicates=duplicates,states=states,nodes=c.nodes())
for fps,copies in itertools.product((30,60,120),(0,1,3)):
 c=equip(copies);first=None;last=None;transitions=[];previous=None
 for frame in range(12*fps):
  if frame/fps<.1:c.event(1)
  step(c,fps);visible=concealed(c)
  if visible:
   first=frame if first is None else first;last=frame
   assert len(live(c))==1
  state=(visible,bool(c.invoke(0x508e20,[OBJ,600])&255))
  if state!=previous:transitions.append(dict(frame=frame,concealed=state[0],fullHide=state[1]));previous=state
 assert (first is not None)==bool(copies)
 if copies:assert abs((last-first+1)/fps-10)<=3.01/fps
 assert not live(c) and not concealed(c)
 record('lifetime',c,fps=fps,copies=copies,first=first,last=last,transitions=transitions,remaining=c.nodes())
for copies,starts in itertools.product((1,3),([0],[0,1],[0,3],[0,9],[0,11])):
 c=equip(copies);previous=False;transitions=[];lifeAfter=[]
 for frame in range((starts[-1]+12)*60):
  if any(start*60<=frame<start*60+6 for start in starts):c.event(1)
  step(c,60);visible=concealed(c)
  if visible!=previous:transitions.append(dict(frame=frame,concealed=visible));previous=visible
  if frame in [start*60+30 for start in starts]:
   assert len(live(c))==1 and 9.3<live(c)[0]['lifetime']<=10
   lifeAfter.append(dict(frame=frame,lifetime=live(c)[0]['lifetime']))
 assert not concealed(c)
 assert abs(transitions[-1]['frame']/60-(starts[-1]+10))<.5
 record('repeat',c,copies=copies,starts=starts,transitions=transitions,lifeAfter=lifeAfter)
for amount,elapsed in itertools.product((0,1,1000),(1,5,9)):
 c=equip(1)
 for frame in range(elapsed*60):
  if frame<6:c.event(1)
  step(c,60)
 assert concealed(c);before=live(c)[0]['lifetime'];c.damage(amount);step(c,60)
 assert concealed(c) and len(live(c))==1 and abs(live(c)[0]['lifetime']-(before-1/60))<1e-5
 record('damage',c,amount=amount,elapsed=elapsed,before=before,after=live(c)[0]['lifetime'],rates=c.rates())

# This is a representative backstab binding, not a claim that every Throw row
# or enemy-specific critical variant has been evaluated by the behavior VM.
throw=throws['tables']['ThrowParam']['10000000']
assert throw['AtkChrId']==0 and throw['atkAnimId']==31710 and throw['throwType']==1
output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),
 animationBundleSha256=t['bundles'][0]['sha256'],taeSha256=rawhashes,throwParamSha256=sha(a.throws.with_suffix('.ThrowParam.param').read_bytes()),
 effect=7031800,root=root,marker=marker,leaf=leaf,events=events,throwBinding=dict(id=10000000,row=throw),
 rows={str(id):x.spells[str(id)] for id in (root,7031800,marker,7031802,leaf)},checks=checks,
 native=dict(relocate='27D0F10',iterate='27D0400',event='410CA0 → 40FF20',grant='3C8BE0 → 3C80A0 / 3C7FD0',
 insert='50D060',qualify='5057D0',update='50ACD0',state='508E20 (AL)',damage='504D30',sight='508A30',hearing='508890'),
 stubs=sorted(stubs|{'explicit critical-animation event arrivals during its first 0.1 seconds; full throw selection and collision not simulated',
 'actor damage notification only; full hit processing, attack actions, stealth rendering and actual AI perception not simulated'}),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS', {k:len(v) for k,v in checks.items()}, 'Duchess stealth cases')
