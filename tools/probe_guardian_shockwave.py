"""Trace Guardian ability-guard shockwaves through TAE, native timers and HP.

Actual native TAE dispatch, conditional nodes, emission requests and HP packets
execute with explicit actor/allocator and collision-arrival fixtures. HKS and
pointer-checked behavior selectors establish the ability-guard action path.
"""
import argparse
import itertools
import json
import math
import struct
from pathlib import Path
from native_effect_runtime import BASE,OBJ,STOP,Chain,Inputs,sha
from native_ailment_runtime import Ailment
from native_animation_runtime import NativeTae
from effect_behavior_graph import BehaviorGraph
from unicorn.x86_const import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','animations','behavior','script','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted);animations=json.loads(a.animations.read_text())
graph=BehaviorGraph(a.behavior);script=a.script.read_bytes()
assert sha(script)=='786f8a7bc89452d9531e2299b224c8945701c422437eca9aacbeb10a57a17f4d'
text=script.decode('utf-8-sig').replace('\r\n','\n')
assert 'if env(GetSpEffectID, 701530) == TRUE then\n            SetVariable("IndexGuard", 3)\n        end' in text
assert animations['bundles'][0]['sha256']=='1410035ad79edb410fa41420ec259fcb4a1037d748c9c4a3b6ae8d1366c76d0f'
paths=[]
for selector,expected in ((18834,19450),(18836,19460),(18838,19470)):
 assert graph.selector_binding(selector)['name']=='IndexGuard'
 children=graph.children(selector);assert len(children)==5
 child=children[3];clips=graph.children(child)
 names=[graph.string(graph.reference(i,'animationName')) for i in clips]
 assert names==[f'a000_{expected:06}',f'a015_{expected:06}']
 paths.append(dict(selector=selector,name=graph.name(selector),binding=graph.selector_binding(selector),index=3,child=child,clips=clips,animations=names))
rawtae={};events=[]
for bundle in animations['bundles']:
 for track in bundle['taes']:
  if track['ID'] not in (2000,2015):continue
  raw=a.animations.with_name(a.animations.name+'.'+str(track['ID'])+'.tae').read_bytes()
  assert sha(raw)==track['sha256'];rawtae[track['ID']]=(raw,track['sha256'])
  for animation in track['animations']:
   for event in animation['events']:
    if event['Type']==67 and struct.unpack_from('<i',bytes.fromhex(event['hex']))[0]==7033403:
     assert animation['ID'] in (19450,19460,19470) and event['StartTime']==0
     assert math.isclose(event['EndTime'],2/30,rel_tol=1e-6)
     events.append(dict(tae=track['ID'],animation=animation['ID'],**event))
assert len(events)==6
bullet=x.x['tables']['Bullet']['900503070'];behavior=x.x['tables']['BehaviorParam_PC']['990503070'];attack=x.x['tables']['AtkParam_Pc']['900334000']
assert behavior['refType']==1 and behavior['refId']==900503070
assert bullet['atkId_Bullet']==900334000 and bullet['spEffectId0']==7033405
assert bullet['hitRadius']==2.5 and bullet['hitRadiusMax']==3.5 and math.isclose(bullet['spreadTime'],.1,rel_tol=1e-6)
assert bullet['numShoot']==1 and bullet['shootInterval']==0 and math.isclose(bullet['life'],.3,rel_tol=1e-6)
assert bullet['HitBulletID']==bullet['intervalCreateBulletId']==-1 and bullet['isEndlessHit']==0
assert [attack[k] for k in ('selfTarget','friendlyTarget','opposeTarget','disableHitSpEffect')]==[0,0,1,0]
assert x.x['tables']['AttachEffectParam']['7033400']['passiveSpEffectId_1']==9200000
assert x.x['tables']['AttachEffectParam']['7033400']['exclusivityId']==-1
r=x.spells
assert r['9200000']['cycleOccurrenceSpEffectId']==9200001 and r['9200000']['spCategory']==20
assert r['9200001']['cycleOccurrenceSpEffectId']==7033402 and r['9200001']['replaceSpEffectId']==7033400
assert r['7033402']['stateInfo']==2264
assert r['7033403']['invocationConditionsStateChange1']==r['7033404']['invocationConditionsStateChange1']==2264
assert r['7033403']['replaceSpEffectId']==7033404 and math.isclose(r['7033403']['effectEndurance'],.1,rel_tol=1e-6)
assert r['7033404']['spCategory']==10 and r['7033404']['stateInfo']==275
assert r['7033404']['effectEndurance']==3 and r['7033404']['motionInterval']==4 and r['7033404']['behaviorId']==990503070
assert r['7033405']['spCategory']==0 and r['7033405']['effectEndurance']==0 and r['7033405']['motionInterval']==0
assert math.isclose(r['7033405']['changeHpRate'],.12,rel_tol=1e-6) and r['7033405']['changeHpPoint']==0 and r['7033405']['syncTotalHp']==1
bullet_raw=a.extracted.with_suffix('.Bullet.param').read_bytes();bullets=Inputs.table(bullet_raw,0x100)
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

class Shock(Actor):
 def __init__(self):
  self.free=[];self.frame=0;self.shots=[]
  super().__init__()
 def hook(self,u,address,size,user):
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP)
   u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  pc=address-BASE
  if pc==0x3ced90:
   self.stubs.add('3CED90 synthetic animation-owner context');ret(OBJ+0xd000)
  elif pc==0x4d1b20:
   self.stubs.add('4D1B20 ordinary locally active actor');ret()
  elif pc==0x26909a0:
   self.stubs.add('26909A0 security cookie');ret(u.reg_read(UC_X86_REG_RAX))
  elif pc==0x3975d0:
   self.stubs.add('3975D0 records native emission request; full collision is not simulated')
   payload=bytes(u.mem_read(u.reg_read(UC_X86_REG_R9),8))
   self.shots.append(dict(frame=self.frame,behavior=u.reg_read(UC_X86_REG_RDX),payload=payload.hex()));ret(1)
  elif address==STOP+0x108:
   ptr=u.reg_read(UC_X86_REG_RDX)
   assert OBJ+0x20000<=ptr<OBJ+0x40000 and ptr not in self.free
   self.free.append(ptr);ret()
  elif pc==0x214e8d0 and self.free:
   assert u.reg_read(UC_X86_REG_RCX)==0x88
   ret(self.free.pop())
  else:super().hook(u,address,size,user)
 def select(self,event):
  raw,hash=rawtae[event['tae']];tae=NativeTae(self,raw,hash)
  assert tae.id==event['tae'] and tae.bank==255
  ctx=OBJ+0xd100;self.u.mem_write(ctx,bytes(0x40))
  for _ in range(1000):
   if not self.invoke(0x27d0400,[tae.animations[event['animation']],ctx]):break
   typ=struct.unpack('<I',self.u.mem_read(ctx,4))[0]
   if typ!=67:continue
   payload=struct.unpack('<Q',self.u.mem_read(ctx+8,8))[0]
   if struct.unpack('<i',self.u.mem_read(payload,4))[0]!=7033403:continue
   assert bytes(self.u.mem_read(payload,16))==bytes.fromhex(event['hex'])
   self.ctx=ctx;self.q(OBJ+0x8018,OBJ+0x6000);return
  raise AssertionError('missing native Type 67 event')
 def event(self):
  # Type 67 is maintained by the caller during its active animation window;
  # its own dispatch does not use ctx.active as an on/off condition.
  self.u.mem_write(self.ctx+0x18,b'\1')
  self.invoke(0x410ca0,[OBJ+0x8000,self.ctx])
 def emit(self):self.invoke(0x50aa20,[OBJ])

class Recipient(Chain):
 def hp(self,maximum):
  self.q(OBJ+0x10,0)
  self.invoke(0x506ec0,[OBJ,maximum,OBJ+0x800,OBJ+0x808,OBJ+0x820,0])
  self.q(OBJ+0x10,OBJ+0x6000)
  return list(struct.unpack('<7i',self.u.mem_read(OBJ+0x820,28)))
 def target(self,typ,same=False):
  self.u.mem_write(OBJ+0x6074,b'\1');self.u.mem_write(OBJ+0xb074,bytes([typ]))
  self.u.mem_write(OBJ+0xc000,x.rows[7033405]);self.q(OBJ+0xb800,OBJ+0xc000)
  return bool(self.invoke(0x52cc60,[OBJ+0x6000,OBJ+0x6000 if same else OBJ+0xb000,OBJ+0xb800])&255)

class Emitter(Chain):
 def __init__(self):super().__init__(x);self.frame=0;self.shots=[]
 def hook(self,u,address,size,user):
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP)
   u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  pc=address-BASE
  if pc==0xe87800:
   assert u.reg_read(UC_X86_REG_RDX)&0xffffffff==900503070
   self.stubs.add('E87800 actual shockwave Bullet lookup')
   u.mem_write(OBJ+0xe900,bullets[900503070]);ptr=u.reg_read(UC_X86_REG_RCX)
   u.mem_write(ptr,struct.pack('<QI',OBJ+0xe900,900503070));ret(ptr)
  elif pc==0x347700:
   self.stubs.add('347700 successful projectile recorder, without scene collision')
   self.shots.append(self.frame);ret(1)
  else:super().hook(u,address,size,user)

checks=dict(trigger=[],repeat=[],projectile=[],target=[],damage=[]);stubs=set()
def record(key,c,**row):checks[key].append(row);stubs.update(c.stubs)
def step(c,fps):c.qualify();c.update(1/fps)
def start(event,copies,fps):
 c=Shock()
 for _ in range(copies):c.grant(9200000)
 for _ in range(fps):step(c,fps)
 assert sum(n['id']==9200000 for n in c.nodes())==bool(copies)
 assert bool(c.invoke(0x508e20,[OBJ,2264])&255)==bool(copies)
 c.select(event);return c
for event,copies,fps in itertools.product(events,(0,1,3),(30,60,120)):
 c=start(event,copies,fps)
 for frame in range(fps*4):
  c.frame=frame
  if frame*30<fps*2:c.event()
  step(c,fps);c.emit();c.grants.clear()
 assert len(c.shots)==bool(copies),(event,copies,fps,c.shots)
 if c.shots:assert c.shots[0]['behavior']==990503070 and 0<c.shots[0]['frame']/fps<.3
 assert not any(n['id'] in (7033403,7033404) for n in c.nodes())
 record('trigger',c,tae=event['tae'],animation=event['animation'],copies=copies,fps=fps,shots=c.shots)

# Several new guard reactions inside the emitter node's three-second lifetime
# produce separate requests. Four-second motionInterval is not a guard cooldown.
for copies,fps in itertools.product((1,3),(30,60,120)):
 c=start(events[0],copies,fps);arrivals=[0,fps//2,fps]
 for frame in range(5*fps):
  c.frame=frame
  if any(0<=(frame-arrival)*30<fps*2 for arrival in arrivals):c.event()
  step(c,fps);c.emit();c.grants.clear()
 assert len(c.shots)==3 and all(s['behavior']==990503070 for s in c.shots)
 assert not any(n['id'] in (7033403,7033404) for n in c.nodes())
 record('repeat',c,copies=copies,fps=fps,arrivalFrames=arrivals,shots=c.shots)

for fps in (30,60,120):
 c=Emitter();slot=OBJ+0x4000
 c.u.mem_write(slot+0x329,b'\1');c.u.mem_write(slot+0x334,struct.pack('<I',900503070));c.u.mem_write(slot+0x494,b'\1')
 for frame in range(fps):c.frame=frame;c.invoke(0x343280,[slot],{UC_X86_REG_XMM1:1/fps})
 assert c.shots==[0]
 record('projectile',c,fps=fps,shots=c.shots)

for relation,typ,same in (('self',1,True),('friendly',2,False),('opposing',6,False),('neutral',0,False)):
 c=Recipient(x);allowed=c.target(typ,same)
 assert allowed==(relation=='opposing')
 record('target',c,relation=relation,allowed=allowed)

# A zero-life extra-HP packet, independently of the attack's physical damage.
# Arrival is supplied after collision; the physical-attack formula is not run.
for copies,maximum in itertools.product(range(4),(100,1000,10000,100000)):
 c=Recipient(x)
 for _ in range(copies):c.insert(7033405)
 c.qualify();c.update(0);packet=c.hp(maximum)
 expected={100:[0,0,0,0],1000:[0,1,2,3],10000:[0,12,24,35],100000:[0,120,240,360]}[maximum][copies]
 assert packet==[-expected,0,-expected,0,-expected,0,0]
 for _ in range(3):step(c,60)
 assert c.hp(maximum)==[0]*7 and not c.nodes()
 record('damage',c,copies=copies,maximum=maximum,packet=packet,afterExpiration=c.hp(maximum))

output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),
            scriptSha256=sha(script),behaviorSha256=graph.metadata['hkxSha256'],bulletParamSha256=sha(bullet_raw),
            taeSha256={str(id):hash for id,(_,hash) in rawtae.items()},paths=paths,events=events,
            effect=7033400,root=9200000,seed=7033403,emitter=7033404,leaf=7033405,
            behavior=dict(id=990503070,refType=behavior['refType'],refId=behavior['refId']),
            bullet={k:bullet[k] for k in ('hitRadius','hitRadiusMax','spreadTime','life','atkId_Bullet','spEffectId0','numShoot','shootInterval','isEndlessHit')},
            attack={k:attack[k] for k in ('atkPhys','atkPhysCorrection','atkSuperArmor','atkSuperArmorCorrection','selfTarget','friendlyTarget','opposeTarget')},
            rows={str(id):{k:r[str(id)][k] for k in ('stateInfo','spCategory','effectEndurance','motionInterval','cycleOccurrenceSpEffectId',
                    'replaceSpEffectId','invocationConditionsStateChange1','behaviorId','changeHpRate','changeHpPoint','syncTotalHp')}
                  for id in (9200000,9200001,*range(7033400,7033406))},
            checks=checks,native=dict(animation='27D0F10 / 27D0400 → 410CA0 → 40FF20',
            grant='3C8BE0 / 3C7FD0 → 3C80A0 → 3DB410 → 50D060',emitter='50AA20 → 397570 → 3975D0',
            projectile='343280',relation='52CC60 → 3D1B30',hp='506EC0'),stubs=sorted(stubs|{
                'active TAE windows and guard-reaction scheduling are inputs; full animation/behavior VM not executed',
                'HP getter has no physical-owner invulnerability context; collision arrival supplied; physical attack damage not executed'}),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(map(len,checks.values())),'native Guardian shockwave cases')
