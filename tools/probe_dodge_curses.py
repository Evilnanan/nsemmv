"""Trace dodge damage curses through pinned TAE and native counters/consumers.

Actor state, animation time and action selection inputs are explicit fixtures.
This runs isolated original code, not a game session or complete Havok scheduler.
"""
import argparse,itertools,json,math,struct,ctypes,ctypes.util,re
from pathlib import Path
from native_effect_runtime import BASE,OBJ,STOP,Chain,Inputs,sha
from native_ailment_runtime import Ailment
from native_animation_runtime import NativeTae
from effect_behavior_graph import BehaviorGraph
from unicorn.x86_const import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','animations','behavior','script','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted)
raw=a.extracted.with_suffix('.AttachEffectParam.param').read_bytes();rows=Inputs.table(raw,0x44)
script_raw=a.script.read_bytes();assert sha(script_raw)=='96339bb15f57559cd42a940d616fcc2a18a10f50845cfc22b46b356ab66c3b29'
script=script_raw.decode('utf-8-sig').replace('\r\n','\n')
animations=json.loads(a.animations.read_text());bundle=animations['bundles'][0]
assert bundle['sha256']=='806e6b218d747277ab45e14f45ca80b9ecf8c13ada22f89db2d3ef23caa62b2a'
tracks={t['ID']:t for b in animations['bundles'] for t in b['taes']}
families=[]
for id,kind,rate,leaf in ((6850700,'immediate',1.45,-1),(8800100,'immediate',1.15,-1),(8800150,'immediate',1.20,-1),
                         (6850800,'counter',1.35,6850821),(8800200,'counter',1.23,8831221),(8800250,'counter',1.30,8800271)):
 attach=x.x['tables']['AttachEffectParam'][str(id)];r=x.spells[str(id)]
 extras=[attach['passiveSpEffectId_'+str(i)] for i in (2,3)]
 assert attach['passiveSpEffectId_1']==id and attach['exclusivityId']==-1 and attach['permanentSpEffectId']==-1
 assert extras==([-1,-1] if kind=='immediate' else [8800201,8800230])
 assert r['spCategory']==10 and r['invocationConditionsStateChange1']==(2212 if kind=='immediate' else 2215)
 assert r['invocationConditionsStateChange2']==r['invocationConditionsStateChange3']==0
 child=r if kind=='immediate' else x.spells[str(leaf)]
 assert math.isclose(child['neutralDamageCutRate'],rate,rel_tol=1e-6)
 assert all(child[k]==child['neutralDamageCutRate'] for k in ('magicDamageCutRate','fireDamageCutRate','thunderDamageCutRate','darkDamageCutRate','slashDamageCutRate','blowDamageCutRate','thrustDamageCutRate'))
 if kind=='immediate':assert r['effectEndurance']==-1 and r['cycleOccurrenceSpEffectId']==r['replaceSpEffectId']==-1
 else:
  bridge=x.spells[str(r['replaceSpEffectId'])]
  assert r['effectEndurance']==0 and r['cycleOccurrenceSpEffectId']==leaf
  assert bridge['spCategory']==10 and math.isclose(bridge['effectEndurance'],.1,rel_tol=1e-6) and bridge['replaceSpEffectId']==id
  assert child['spCategory']==10 and child['effectEndurance']==15 and child['replaceSpEffectId']==child['cycleOccurrenceSpEffectId']==-1
  assert all(child['invocationConditionsStateChange'+str(i)]==0 for i in (1,2,3))
 families.append(dict(effect=id,root=id,extras=extras,kind=kind,rate=child['neutralDamageCutRate'],leaf=leaf,bridge=r['replaceSpEffectId'],duration=None if kind=='immediate' else 15))
for marker,state in ((8800101,2212),(8800204,2215)):
 r=x.spells[str(marker)];assert (r['stateInfo'],r['spCategory'],r['effectEndurance'])==(state,20,0)
assert x.spells['8800230']['stateInfo']==2220
assert x.spells['8800201']['accumuOverVal']==7000000 and x.spells['8800201']['accumuOverFireId']==8800205
assert x.spells['8800202']['accumuVal']==3000000 and x.spells['8800202']['invocationConditionsStateChange1']==2220
assert x.spells['8800203']['accumuVal']==-1000000
assert x.spells['8800205']['accumuVal']==-99999999 and x.spells['8800205']['replaceSpEffectId']==8800204
assert x.spells['8800210']['motionInterval']==1 and x.spells['8800210']['cycleOccurrenceSpEffectId']==8800203
assert all(x.spells[str(i)]['stateInfo']==309 for i in (8800201,8800202,8800203,8800205))
events=[];event_ids=(8800101,8800210,8800202)
for t in tracks.values():
 for an in t['animations']:
  selected=[dict(tae=t['ID'],animation=an['ID'],seed=struct.unpack_from('<i',bytes.fromhex(e['hex']))[0],**e)
            for e in an['events'] if e['Type']==67 and struct.unpack_from('<i',bytes.fromhex(e['hex']))[0] in event_ids]
  if not selected:continue
  assert [e['seed'] for e in selected]==list(event_ids)
  for e,start,end in zip(selected,(0,0,1/30),(100,1/30,2/30)):
   assert math.isclose(e['StartTime'],start,rel_tol=1e-6) and math.isclose(e['EndTime'],end,rel_tol=1e-6)
  events.extend(selected)
assert len(events)==546
used_tracks=sorted({e['tae'] for e in events});assert used_tracks==[2000,2002,2003,2010,2012,2013,2014,2015,2016,2527]
rawtaes={id:a.animations.with_name(a.animations.name+'.'+str(id)+'.tae').read_bytes() for id in used_tracks}
for id,data in rawtaes.items():assert sha(data)==tracks[id]['sha256']
graph=BehaviorGraph(a.behavior);paths=[];bindings={}
def walk(node,trail):
 typ=graph.item(node)[0]['Identity'];trail=trail+[(node,typ,graph.name(node))]
 if typ=='hkbClipGenerator':
  name=graph.string(graph.reference(node,'animationName'));m=re.fullmatch(r'a(\d+)_(\d+)(?:[._]hkx)?',name);assert m,name
  pair=(2000+int(m[1]),int(m[2]));present=[e['seed'] for e in events if (e['tae'],e['animation'])==pair]
  paths.append(dict(path=trail,animation=name,tae=pair[0],id=pair[1],events=present))
 elif typ in ('hkbManualSelectorGenerator','CustomManualSelectorGenerator'):
  if typ=='hkbManualSelectorGenerator':bindings[node]=graph.selector_binding(node)
  for child in graph.children(node):walk(child,trail)
 elif typ=='hkbBlenderGenerator':
  for child in graph.blender_children(node):walk(child['generator'],trail)
 elif typ=='hkbModifierGenerator':walk(graph.reference(node,'generator'),trail)
 else:raise AssertionError((typ,trail))
for name in ('Rolling','Rolling_Selftrans','Rolling_Selftrans2','SwordArtsRolling'):
 node=graph.named(name,'hkbStateMachine::StateInfo');walk(graph.reference(node,'generator'),[(node,'state',name)])
assert len(paths)==372 and len(bindings)==59
selector=graph.named('Rolling_Variation_Selector','hkbManualSelectorGenerator')
assert graph.selector_binding(selector)['name']=='RollingVariationIndex'
assert [graph.name(c) for c in graph.children(selector)][5:7]==['Power_SmashAttackStep_Selector','Tank_HighGuardStep_Selector']
highguard=[p for p in paths if any('Tank_HighGuardStep' in (n or '') for _,_,n in p['path'])]
assert len(highguard)==16 and all(not p['events'] for p in highguard)
# No PARAM-linked grant silently substitutes these TAE markers.
for row in x.spells.values():
 assert not any(v in event_ids for k,v in row.items() if 'SpEffectId' in k)
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


class AnimationActor(Actor):
 def __init__(self):
  self.shots=[];super().__init__()
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if pc==0x3ced90:self.stubs.add('3CED90 explicit animation-owner context');ret(OBJ+0xd000)
  elif pc==0x4d1b20:self.stubs.add('4D1B20 ordinary locally active actor');ret()
  elif pc==0x3975d0:self.stubs.add('3975D0 native Behavior emission recorder; no collision');self.shots.append(u.reg_read(UC_X86_REG_RDX));ret(1)
  elif pc==0x26909a0:self.stubs.add('26909A0 security cookie preserves return value');ret(u.reg_read(UC_X86_REG_RAX))
  else:super().hook(u,address,size,user)
 def hp(self,maximum=1000):
  self.invoke(0x506ec0,[OBJ,maximum,OBJ+0x800,OBJ+0x808,OBJ+0x820,0]);return list(struct.unpack('<7i',self.u.mem_read(OBJ+0x820,28)))

class Combo(AnimationActor):
    def __init__(self):
        self.free=[]
        super().__init__()
        self.manager=OBJ+0xa000
        self.q(OBJ+0x18,self.manager)
        # 5014E0 constructs this manager with 50DFE0: ten counters and ten
        # vector queues. Reserve storage here; predicates and arithmetic run
        # natively. Reclaimed effect nodes are reused by the allocator fixture.
        self.q(self.manager,OBJ)
        self.q(self.manager+0x38,10);self.q(self.manager+0x188,10)
        for i in range(10):
            slot=self.manager+0x40+i*0x20;buf=OBJ+0xb000+i*0x100
            self.q(slot+8,buf);self.q(slot+0x10,buf);self.q(slot+0x18,buf+0x100)
        self.stubs.add('ten native-layout accumulation counters/queues with preallocated vector storage')

    def hook(self,u,address,size,user):
        def ret(v=0):
            u.reg_write(UC_X86_REG_RAX,v)
            sp=u.reg_read(UC_X86_REG_RSP)
            u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0])
            u.reg_write(UC_X86_REG_RSP,sp+8)
        if address==STOP+0x108:
            ptr=u.reg_read(UC_X86_REG_RDX)
            assert OBJ+0x20000<=ptr<OBJ+0x40000 and ptr not in self.free
            self.free.append(ptr);ret()
        elif address-BASE==0x214e8d0 and self.free:
            assert u.reg_read(UC_X86_REG_RCX)==0x88
            ret(self.free.pop())
        else:super().hook(u,address,size,user)

    def counter(self):return self.invoke(0x50e570,[self.manager,6])&0xffffffff
    def add(self,amount):self.invoke(0x50e240,[self.manager,6,amount])
    def queue(self):
        slot=self.manager+0x40+6*0x20
        begin,end=struct.unpack('<QQ',self.u.mem_read(slot+8,16))
        return list(struct.unpack('<'+'i'*((end-begin)//4),self.u.mem_read(begin,end-begin)))




def f32(v):return struct.unpack('<f',struct.pack('<f',v))[0]
class Animated(Combo):
 def __init__(self,tae_id=None):
  super().__init__();self.ctxs=[];self.tae_id=tae_id
  self.tae=None if tae_id is None else NativeTae(self,rawtaes[tae_id],tracks[tae_id]['sha256'])
  self.q(OBJ+0x8018,OBJ+0x6000)
 def select(self,animation):
  assert self.tae is not None
  self.ctxs=[];ctx=OBJ+0xd100;self.u.mem_write(ctx,bytes(0x40))
  wanted=[e for e in events if e['tae']==self.tae_id and e['animation']==animation]
  for _ in range(1000):
   if not self.invoke(0x27d0400,[self.tae.animations[animation],ctx]):break
   typ=struct.unpack('<I',self.u.mem_read(ctx,4))[0]
   if typ!=67:continue
   payload=struct.unpack('<Q',self.u.mem_read(ctx+8,8))[0];id=struct.unpack('<i',self.u.mem_read(payload,4))[0]
   if id not in event_ids:continue
   ev=next(e for e in wanted if e['seed']==id)
   assert bytes(self.u.mem_read(payload,len(bytes.fromhex(ev['hex']))))==bytes.fromhex(ev['hex'])
   address=OBJ+0xd200+len(self.ctxs)*0x80;self.u.mem_write(address,bytes(self.u.mem_read(ctx,0x40)))
   self.ctxs.append((id,address,ev['StartTime'],ev['EndTime']))
  assert [c[0] for c in self.ctxs]==[e['seed'] for e in wanted]
  return [c[0] for c in self.ctxs]
 def event(self,time):
  for id,ctx,start,end in self.ctxs:
   if f32(start)<=f32(time)<f32(end):
    self.u.mem_write(ctx+0x18,b'\1');self.invoke(0x410ca0,[OBJ+0x8000,ctx])
 def step(self,fps=60,time=None,marker=None):
  if time is not None:self.event(time)
  if marker is not None:self.grant(marker)
  self.qualify();self.update(1/fps)
 def taken(self):
  self.u.mem_write(OBJ+0x800,bytes(0x200))
  self.invoke(0x503800,[OBJ,OBJ+0x500,OBJ+0x520,OBJ+0x540,OBJ+0x800])
  return list(struct.unpack('<5f',self.u.mem_read(OBJ+0x500,20)))
 def equip(self,f,copies=1):
  for _ in range(copies):
   for id in [f['root']]+f['extras']:
    if id!=-1:self.grant(id)
 def leaves(self):return [sum(n['id']==f['leaf'] and not n['flags']&0x800c0003 for n in self.nodes()) for f in families[3:]]
 def expect(self,rate):
  values=self.taken();assert all(math.isclose(v,rate,rel_tol=1e-6) for v in values),(rate,values)
  return values
checks={k:[] for k in ('selection','events','dispatch','multipliers','counter','lifetime','independent','disabled','script')};stubs=set()
def record(group,c=None,**values):
 checks[group].append(values)
 if c is not None:stubs.update(c.stubs)
for f,copies,hero in itertools.product(families,(1,2,3,6),range(11)):
 c=Selection([[7000000,-1,-1,f['effect']]]*copies,hero);bits=c.select();roots=[]
 for index in range(copies):
  assert index*6+3 in bits
  id=struct.unpack('<i',c.u.mem_read(OBJ+0xa000+index*0x80+0x24,4))[0];assert id==f['effect']
  c.invoke(0xe6e150,[OBJ+0x9200,id]);selected=[]
  for slot in range(3):
   value=c.invoke(0xe6e3b0,[OBJ+0x9200,slot])&0xffffffff
   selected.append(value if value<0x80000000 else value-0x100000000)
  assert selected==[f['root']]+f['extras'];roots.append(selected)
 record('selection',c,effect=f['effect'],copies=copies,hero=hero,bits=bits,roots=roots)
print('PASS selection',len(checks['selection']),flush=True)
for tae_id in used_tracks:
 c=Animated(tae_id)
 ids=sorted({e['animation'] for e in events if e['tae']==tae_id})
 for id in ids:record('events',c,tae=tae_id,animation=id,nativeSelected=c.select(id))
 c.select(ids[0]);c.equip(families[0]);c.equip(families[3])
 for frame in range(20):c.step(time=frame/60)
 assert c.counter()==3000000 and c.leaves()==[0,0,0]
 during=c.expect(families[0]['rate'])
 for frame in range(120):c.step()
 assert c.counter()==1000000 and c.leaves()==[0,0,0]
 record('dispatch',c,tae=tae_id,animation=ids[0],during=during,after=c.expect(1),counter=c.counter())
 print('PASS track',tae_id,len(ids),flush=True)
# High-guard animations in raw TAE2000/2015 do not deliver any curse event.
for tae_id in (2000,2015):
 c=Animated(tae_id);c.equip(families[0]);c.equip(families[3])
 for animation in range(27200,27204):
  assert c.select(animation)==[]
  for frame in range(30):c.step(time=frame/60)
  assert c.counter()==0 and c.leaves()==[0,0,0]
  record('dispatch',c,tae=tae_id,animation=animation,during=c.expect(1),counter=c.counter())
cases=[[]]+[[f]*n for f in families[:3] for n in (1,2,3,6)]+[families[:3],list(reversed(families[:3]))]
for fs in cases:
 c=Animated()
 for f in fs:c.equip(f)
 for _ in range(10):c.step()
 c.expect(1)
 for _ in range(12):c.step(marker=8800101)
 rate=math.prod(f['rate'] for f in fs);active=c.expect(rate)
 for _ in range(10):c.step()
 record('multipliers',c,roots=[f['root'] for f in fs],active=active,after=c.expect(1))
print('PASS multipliers',len(checks['multipliers']),flush=True)
for fps,copies,spacing in itertools.product((30,60,120),(1,3),(.5,1,2,4)):
 c=Animated(2000);c.select(27100);c.equip(families[0],copies);c.equip(families[3],copies)
 interval=round(spacing*fps);changes=[];last=None
 for frame in range(interval*5+fps):
  local=frame%interval;active=frame//interval<5 and local<fps//3
  c.step(fps,local/fps if active else None)
  val=(c.counter(),c.grants.count(families[3]['leaf']))
  if val!=last:changes.append(dict(frame=frame,counter=val[0],grants=val[1]));last=val
 assert c.grants.count(families[3]['leaf'])==(0 if spacing==4 else copies),(fps,copies,spacing,changes)
 increments=[r['counter']-p['counter'] for p,r in zip(changes,changes[1:]) if r['counter']>p['counter']]
 assert all(v in (2000000,3000000) for v in increments),(fps,copies,spacing,increments)
 maximum=max(r['counter'] for r in changes)
 assert maximum==3000000 if spacing==4 else 7000000<=maximum<=9000000,(fps,copies,spacing,changes)
 record('counter',c,fps=fps,copies=copies,spacing=spacing,actions=5,changes=changes)
 print('PASS counter',fps,copies,spacing,flush=True)
for copies in (1,3):
 c=Animated(2000);c.select(27100)
 for f in families[3:]:c.equip(f,copies)
 for frame in range(180):
  local=frame%15;active=frame//15<6 and local<12
  c.step(time=local/60 if active else None)
 assert c.leaves()==[2*copies]*3,(copies,c.leaves(),c.grants)
 record('counter',c,copies=copies,spacing=.25,actions=6,fps=60,mixed=True,leaves=c.leaves(),values=c.expect(math.prod(f['rate']**(2*copies) for f in families[3:])))
for amount in (0,6000000,6999999,7000000,9000000):
 c=Animated();c.equip(families[3])
 for _ in range(5):c.step()
 c.add(amount)
 for _ in range(12):c.step()
 assert c.counter()==(amount if amount<7000000 else 0)
 assert c.leaves()==([0,0,0] if amount<7000000 else [1,0,0])
 record('independent',c,initialCounter=amount,counter=c.counter(),leaves=c.leaves())
c=Animated();c.equip(families[3])
for _ in range(5):c.step()
c.add(2000000);values=[]
for _ in range(5):
 c.step(marker=8800203);values.append(c.counter())
assert values==[1000000,0,0,0,0],values
record('independent',c,initialCounter=2000000,decays=values)

# Raw event dispatch is verified above; use the same marker through native
# self-grant for independent timer checks without reparsing the large TAE.
for fps,copies in itertools.product((30,60,120),(1,3)):
 c=Animated()
 for f in families[3:]:c.equip(f,copies)
 changes=[];last=None
 for frame in range(22*fps):
  active=frame*30<fps or 5*fps<=frame and (frame-5*fps)*30<fps
  c.step(fps,marker=8800204 if active else None)
  val=c.leaves()
  if val!=last:
   values=c.expect(math.prod(f['rate']**n for f,n in zip(families[3:],val)))
   changes.append(dict(frame=frame,copies=val,values=values));last=val
 assert [r['copies'] for r in changes]==[[0]*3,[copies]*3,[2*copies]*3,[copies]*3,[0]*3],(fps,copies,changes)
 for change,seconds in zip(changes[1:],(0,5,15,20)):
  assert abs(change['frame']/fps-seconds)<=4.01/fps,(fps,copies,change,seconds)
 record('lifetime',c,fps=fps,copies=copies,changes=changes)
 print('PASS lifetime',fps,copies,flush=True)
for index,f in enumerate(families[3:]):
 for copies in (0,1,2,3):
  c=Animated();c.equip(f,copies)
  c.step(marker=8800204)
  for _ in range(9):c.step()
  wanted=[0]*3;wanted[index]=copies;assert c.leaves()==wanted
  record('independent',c,effect=f['effect'],copies=copies,values=c.expect(f['rate']**copies),leaves=c.leaves())
# Counter enabling, threshold, nonnegative floor and re-arming are native.
for extras in ([],[8800201],[8800230],[8800201,8800230]):
 c=Animated()
 for id in extras:c.grant(id)
 for _ in range(10):c.step()
 for marker in (8800202,8800202,8800202):
  c.step(marker=marker)
  for _ in range(10):c.step()
 assert c.counter()==0,(extras,c.counter())
 assert (8800204 in c.grants)==(extras==[8800201,8800230]),(extras,c.grants)
 record('independent',c,extras=extras,counter=c.counter(),grants=c.grants)
for stage in ('immediate','root','leaf'):
 c=Animated()
 ids=[f['root'] for f in families[:3]] if stage=='immediate' else [f[stage] for f in families[3:]]
 for id in ids:c.grant(id)
 c.step();c.grant(8800101 if stage=='immediate' else 8800204);c.qualify()
 ptr=struct.unpack('<Q',c.u.mem_read(OBJ+8,8))[0]
 while ptr:
  id=struct.unpack('<i',c.u.mem_read(ptr+8,4))[0]
  if id in ids:c.u.mem_write(ptr+0x68,struct.pack('<I',0x800c0003))
  ptr=struct.unpack('<Q',c.u.mem_read(ptr+0x38,8))[0]
 c.update(0)
 record('disabled',c,stage=stage,values=c.expect(1),leaves=c.leaves())
lua=ctypes.CDLL(ctypes.util.find_library('lua5.4'));lua.luaL_newstate.restype=ctypes.c_void_p
lua.luaL_openlibs.argtypes=[ctypes.c_void_p];lua.luaL_loadstring.argtypes=[ctypes.c_void_p,ctypes.c_char_p]
lua.lua_pcallk.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_ssize_t,ctypes.c_void_p]
lua.lua_tolstring.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.POINTER(ctypes.c_size_t)];lua.lua_tolstring.restype=ctypes.c_char_p
lua.lua_close.argtypes=[ctypes.c_void_p]
start=script.index('    if env(GetHeroID) == HERO_MAGIC and env(GetSpEffectID, 1800200) == TRUE then',script.index('function ExecEvasion('))
branch=script[start:script.index('    if request == ATTACK_REQUEST_ROLLING then',start)]
constants=script[script.index('ROLLING_DEFAULT = 0'):script.index('HERO_WYLDER =')]
# The original selection branch is executed; action request admission and its
# high-guard/weapon predicate are explicit inputs, not a complete script VM.
for hero,heavy,highguard,hook,demon,ids in itertools.product(range(1,11),(False,True),(False,True),(False,True),(False,True),([], [1800200], [709000], [709010])):
 prelude='TRUE=1;FALSE=0;HERO_MAGIC=7;HERO_TANK=2;HERO_SPEED=4;HERO_BUFFER=9;HERO_ATTACKER=10;EVASION_WEIGHT_INDEX_HEAVY=1;GetHeroID=1;GetSpEffectID=2;local result=-1;\n'+constants
 prelude+='local ids={'+','.join('['+str(id)+']=true' for id in ids)+'};\n'
 prelude+=f'function env(k,id) if k==GetHeroID then return {hero} elseif k==GetSpEffectID then return ids[id] and TRUE or FALSE else error(k) end end\n'
 prelude+=f'function IsEnableHighGuard() return {int(highguard)} end\nfunction IsGuard() return 1 end\nfunction IsNodeActive(k) assert(k=="FookShotMove_CMSG");return {int(hook)} end\nfunction IsDemonSwordMode() return {int(demon)} end\nfunction GetVariable(k) assert(k=="EvasionWeightIndex");return {int(heavy)} end\nfunction SetVariable(k,v) assert(k=="RollingVariationIndex");result=v end\n'
 state=lua.luaL_newstate()
 try:
  lua.luaL_openlibs(state);assert lua.luaL_loadstring(state,(prelude+branch+'\nreturn tostring(result)').encode())==0
  status=lua.lua_pcallk(state,0,1,0,0,None);out=lua.lua_tolstring(state,-1,None);assert status==0,out
  actual=int(out)
 finally:lua.lua_close(state)
 wanted=8 if hero==7 and 1800200 in ids else 6 if highguard else 4 if hero==7 and not heavy else 3 if hook and not heavy else 2 if hero==4 and not heavy else 1 if hero==2 and not heavy else 9 if demon and not heavy else 10 if hero==9 and not heavy else 11 if hero==10 and set(ids)&{709000,709010} and not heavy else 0
 assert actual==wanted
 record('script',hero=hero,heavy=heavy,highGuard=highguard,hook=hook,demon=demon,effects=ids,variation=actual)
output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),attachParamSha256=sha(raw),
 scriptSha256=sha(script_raw),animationBundleSha256=bundle['sha256'],taeSha256={id:sha(data) for id,data in rawtaes.items()},behaviorSha256=sha(graph.raw),
 paths=paths,bindings=list(bindings.values()),events=events,families=families,checks=checks,
 native=dict(selection='4FEA30 → E6E150 → E6E3B0',animation='27D0F10 → 27D0400 → 410CA0',lifecycle='3C7FD0 → 50D060 → 5057D0 → 50ACD0',
 counter='50E240 → 50E570 (state309, index6)',incoming='503800'),
 stubs=sorted(stubs|{'synthetic inventory: curse slot3 paired with positive7000000; draw legality not asserted',
 'animation activity/time supplied by caller; actual TAE dispatch verified but no full Havok scheduling or interruptions',
 'explicit HKS branch inputs; all 372 graph paths catalogued but not every sword-art/alternate state proven reachable',
 '15-second timeline reuses proven state2215 marker through native self-grant',
 'actual hit damage, extreme stack counts, equipment changes, death/reload and multiplayer not simulated'}),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',{k:len(v) for k,v in checks.items()},flush=True)
