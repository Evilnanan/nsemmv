"""Trace flask curses through pinned animation events and native effect consumers.

The animation caller's active state is explicit, not a full Havok scheduler.
Native selection, TAE relocation/dispatch, condition checks, cycle self-grants,
resistance accumulation and incoming multiplier aggregation execute directly.
"""
import argparse,itertools,json,math,struct,ctypes,ctypes.util
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
graph=BehaviorGraph(a.behavior);paths=[]
expected={'ItemDrinkStart':[50110,50115],'ItemDrinking':[50111,50116],'ItemDrinkEnd':[50112,50117],
          'ItemDrinkEmpty':[50113],'ItemDrinkNothing':[50114],'ItemDrinkStartMP':[50110],'ItemDrinkingMP':[50111]}
for state,ids in expected.items():
 for suffix in ('','_Upper'):
  name=state+suffix;node=graph.named(name,'hkbStateMachine::StateInfo');gen=graph.reference(node,'generator')
  typ=graph.item(gen)[0]['Identity'];binding=None
  if typ=='CustomManualSelectorGenerator':clips=graph.children(gen)
  else:
   assert typ=='hkbManualSelectorGenerator';binding=graph.selector_binding(gen);assert binding['name']=='IsBaphometBuff'
   clips=[c for child in graph.children(gen) for c in graph.children(child)]
  names=[graph.string(graph.reference(c,'animationName')) for c in clips]
  assert names==[f'a000_{id:06}' for id in ids]
  paths.append(dict(state=name,node=node,generator=gen,binding=binding,animations=ids))
animations=json.loads(a.animations.read_text());bundle=animations['bundles'][0]
assert bundle['sha256']=='806e6b218d747277ab45e14f45ca80b9ecf8c13ada22f89db2d3ef23caa62b2a'
track=next(t for t in bundle['taes'] if t['ID']==2000)
rawtae=a.animations.with_name(a.animations.name+'.2000.tae').read_bytes();assert sha(rawtae)==track['sha256']
events=[]
for animation in track['animations']:
 for event in animation['events']:
  if event['Type']==67 and struct.unpack_from('<i',bytes.fromhex(event['hex']))[0]==8801001:
   assert event['StartTime']==0 and event['EndTime']==100
   events.append(dict(animation=animation['ID'],**event))
assert [e['animation'] for e in events]==list(range(50110,50118))
families=[]
for id,rate in ((6850900,1.45),(8801000,1.33),(8801050,1.46),(6851100,1.0)):
 attach=x.x['tables']['AttachEffectParam'][str(id)];r=x.spells[str(id)]
 assert attach['passiveSpEffectId_1']==id and attach['exclusivityId']==-1
 assert all(attach[k]==-1 for k in ('passiveSpEffectId_2','passiveSpEffectId_3','permanentSpEffectId'))
 assert (r['spCategory'],r['effectEndurance'],r['stateInfo'])==(10,-1,0)
 assert [r['invocationConditionsStateChange'+str(i)] for i in (1,2,3)]==[2352,0,0]
 assert r['replaceSpEffectId']==-1
 # Physical uses the same native aggregate as the other four damage kinds.
 actual=r['magicDamageCutRate'];assert math.isclose(actual,rate,rel_tol=1e-6)
 families.append(dict(effect=id,root=id,kind='madness' if id==6851100 else 'damage',rate=actual))
assert x.spells['8801001']['stateInfo']==2352 and x.spells['8801001']['effectEndurance']==0
assert x.spells['6851100']['cycleOccurrenceSpEffectId']==6851101
assert math.isclose(x.spells['6851100']['motionInterval'],.1,rel_tol=1e-6)
leaf=x.spells['6851101'];assert (leaf['stateInfo'],leaf['madnessAttackPower'],leaf['effectEndurance'],leaf['motionInterval'],leaf['cycleOccurrenceSpEffectId'],leaf['replaceSpEffectId'])==(437,8,1,2,49060,1110)
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


class Flask(Actor):
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

class Animated(Flask):
 def __init__(self):
  super().__init__();self.kind=6
  for i in range(7):
   for off in (0x9010,0x902c):self.u.mem_write(OBJ+off+i*4,struct.pack('<i',10000))
  self.tae=None
 def select(self,animation):
  if self.tae is None:self.tae=NativeTae(self,rawtae,track['sha256'])
  ctx=OBJ+0xd100;self.u.mem_write(ctx,bytes(0x40))
  for _ in range(1000):
   if not self.invoke(0x27d0400,[self.tae.animations[animation],ctx]):break
   typ=struct.unpack('<I',self.u.mem_read(ctx,4))[0]
   if typ!=67:continue
   payload=struct.unpack('<Q',self.u.mem_read(ctx+8,8))[0]
   if struct.unpack('<i',self.u.mem_read(payload,4))[0]!=8801001:continue
   self.ctx=ctx;self.q(OBJ+0x8018,OBJ+0x6000);return
  raise AssertionError(('missing event',animation))
 def event(self):
  self.u.mem_write(self.ctx+0x18,b'\1');self.invoke(0x410ca0,[OBJ+0x8000,self.ctx])
 def step(self,fps=60,active=False,native=False):
  if active:
   if native:self.event()
   else:self.grant(8801001)
  self.qualify();self.update(1/fps)
 def taken(self):
  self.u.mem_write(OBJ+0x800,bytes(0x200))
  self.invoke(0x503800,[OBJ,OBJ+0x500,OBJ+0x520,OBJ+0x540,OBJ+0x800])
  return list(struct.unpack('<5f',self.u.mem_read(OBJ+0x500,20)))
checks={k:[] for k in ('selection','dispatch','multipliers','timeline','leaf','disabled','onset','script')};stubs=set()
def record(group,c=None,**values):
 checks[group].append(values)
 if c is not None:stubs.update(c.stubs)
def f32(v):return struct.unpack('<f',struct.pack('<f',v))[0]
def rate(roots):
 value=1.
 for id in roots:value=f32(value*x.spells[str(id)]['magicDamageCutRate'])
 return value
for family,copies,hero in itertools.product(families,(1,2,3,6),range(11)):
 slots=[[7000000,-1,-1,family['effect']]]*copies;c=Selection(slots,hero);bits=c.select();roots=[]
 for index in range(copies):
  assert index*6+3 in bits
  id=struct.unpack('<i',c.u.mem_read(OBJ+0xa000+index*0x80+0x24,4))[0];assert id==family['effect']
  c.invoke(0xe6e150,[OBJ+0x9200,id]);roots.append(c.invoke(0xe6e3b0,[OBJ+0x9200,0])&0xffffffff)
 assert roots==[family['root']]*copies
 record('selection',c,effect=family['effect'],copies=copies,hero=hero,curseSlot=3,bits=bits,roots=roots)
print('PASS selection',len(checks['selection']),flush=True)
# Reuse a single native-relocated TAE across all eight actual drink animations.
c=Animated();c.grant(6850900);c.grant(6851100)
for event in events:
 c.select(event['animation']);before=c.remaining();grants=len(c.grants)
 for frame in range(30):c.step(active=True,native=True)
 active=c.taken();delta=before-c.remaining();assert active==[f32(1.45)]*5 and delta==40
 for _ in range(90):c.step()
 assert c.taken()==[1.]*5 and c.remaining()==before-delta
 emitted=c.grants[grants:];assert emitted.count(6851101)==5
 assert 49060 not in emitted and 1110 not in emitted
 record('dispatch',c,animation=event['animation'],frames=30,fps=60,active=active,accumulation=delta,nativeDispatches=30,leafGrants=5,after=c.taken(),nodes=c.nodes())
print('PASS dispatch',len(checks['dispatch']),flush=True)
cases=[[]]+[[f['root']]*n for f in families if f['kind']=='damage' for n in (1,2,3,6)]+[[6850900,8801000,8801050],[8801050,8801000,6850900]]
for roots in cases:
 c=Animated()
 for id in roots:c.grant(id)
 for _ in range(10):c.step()
 assert c.taken()==[1.]*5
 for _ in range(12):c.step(active=True)
 active=c.taken();assert active==[rate(roots)]*5,(roots,active,rate(roots))
 for _ in range(10):c.step()
 assert c.taken()==[1.]*5
 record('multipliers',c,roots=roots,active=active,after=c.taken())
print('PASS multipliers',len(checks['multipliers']),flush=True)
for copies,fps in itertools.product((0,1,2,3,6),(30,60,120)):
 c=Animated()
 for _ in range(copies):c.grant(6851100)
 for _ in range(fps):c.step(fps)
 assert c.remaining()==10000
 packets=[]
 for frame in range(2*fps):
  before=c.remaining();c.step(fps,True)
  if before!=c.remaining():packets.append(dict(frame=frame,amount=before-c.remaining()))
 total=10000-c.remaining();assert total==160*copies,(copies,fps,total,packets)
 after=[]
 for frame in range(2*fps):
  before=c.remaining();c.step(fps)
  if before!=c.remaining():after.append(dict(frame=frame,amount=before-c.remaining()))
 assert not after and not any(n['id']==6851101 for n in c.nodes())
 assert 49060 not in c.grants and 1110 not in c.grants
 record('timeline',c,copies=copies,fps=fps,seconds=2,packets=packets,accumulation=total,afterPackets=after,nodes=c.nodes())
print('PASS timeline',len(checks['timeline']),flush=True)
# A state437 grant consumes the accumulation immediately; its PARAM lifetime
# and replacement/cycle links must not be presented as a lingering debuff.
for copies in (1,2,3,6):
 c=Animated()
 for _ in range(copies):c.grant(6851101)
 immediate=10000-c.remaining();assert immediate==8*copies
 assert not any(n['id']==6851101 for n in c.nodes())
 for _ in range(180):c.step()
 assert 10000-c.remaining()==immediate and 49060 not in c.grants and 1110 not in c.grants
 record('leaf',c,copies=copies,immediate=immediate,after=10000-c.remaining(),nodes=c.nodes())
for family in families:
 c=Animated()
 for _ in range(3):c.grant(family['root'])
 c.qualify();c.update(0)
 for _ in range(30):
  c.grant(8801001);c.qualify()
  node=struct.unpack('<Q',c.u.mem_read(OBJ+8,8))[0]
  while node:
   id=struct.unpack('<i',c.u.mem_read(node+8,4))[0]
   if id==family['root']:c.u.mem_write(node+0x68,struct.pack('<I',0x800c0003))
   node=struct.unpack('<Q',c.u.mem_read(node+0x38,8))[0]
  c.update(1/60)
 assert c.taken()==[1.]*5 and c.remaining()==10000
 record('disabled',c,effect=family['effect'],taken=c.taken(),accumulation=0)
print('PASS disabled',len(checks['disabled']),flush=True)
# Actual state437 accumulation reaches threshold before HP/FP packets appear.
for threshold,maximum in itertools.product((8,9,16,17),(101,1000)):
 c=Animated()
 for off in (0x9010,0x902c):c.u.mem_write(OBJ+off+6*4,struct.pack('<i',threshold))
 needed=math.ceil(threshold/8);steps=[]
 for n in range(needed):
  c.grant(6851101);c.qualify();c.update(0)
  hp=c.hp_packet(maximum);fp=c.fp(maximum);triggered=n==needed-1
  want_hp=math.trunc(f32(-f32(f32(maximum*15)*f32(.01))-100)) if triggered else 0
  want_fp=math.trunc(f32(-f32(f32(maximum*10)*f32(.01))-30)) if triggered else 0
  assert hp[0]==want_hp and fp==[want_fp,0],(threshold,maximum,n,hp,fp)
  assert c.remaining()==(threshold if triggered else threshold-8*(n+1))
  steps.append(dict(grants=n+1,remaining=c.remaining(),hp=hp,fp=fp,nodes=c.nodes()))
 assert c.grants.count(49060)==1
 # Duplicate packets during an active proc do not restart it or repeat damage.
 c.step();before=c.nodes()[0]['lifetime']
 for _ in range(3):c.grant(6851101)
 assert c.hp_packet(maximum)[0]==0 and c.fp(maximum)==[0,0]
 assert len([n for n in c.nodes() if n['id']==6851101])==1
 for _ in range(120):c.step()
 assert not c.nodes() and c.grants.count(1110)==1
 record('onset',c,threshold=threshold,maximum=maximum,steps=steps,postProcRemaining=c.remaining(),expiredNodes=c.nodes())
print('PASS onset',len(checks['onset']),flush=True)

lua=ctypes.CDLL(ctypes.util.find_library('lua5.4'));lua.luaL_newstate.restype=ctypes.c_void_p
lua.luaL_openlibs.argtypes=[ctypes.c_void_p];lua.luaL_loadstring.argtypes=[ctypes.c_void_p,ctypes.c_char_p]
lua.lua_pcallk.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_ssize_t,ctypes.c_void_p]
lua.lua_tolstring.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.POINTER(ctypes.c_size_t)];lua.lua_tolstring.restype=ctypes.c_char_p
lua.lua_close.argtypes=[ctypes.c_void_p]
def transition(name,end,flag,empty,buff,cancel):
 start=script.index('function '+name+'_Upper_onUpdate()');function=script[start:script.index('\nfunction ',start+1)]
 prelude='TRUE=1;FALSE=0;ITEM_NO_DRINK=99;GetSpEffectID=1;IsAnimEnd=2;GetEventEzStateFlag=3;GetItemAnimType=4;local calls={};\n'
 for state in expected:prelude+=f'Event_{state}="{state}";\n'
 prelude+='function GetHalfBlendInfo() return 0,0 end\nfunction ExecChangeFlask() end\n'
 prelude+=f'function ItemCommonFunction() return {int(cancel)} end\n'
 prelude+='function HalfBlendUpperCommonFunction() return FALSE end\nfunction HalfBlendLowerCommonFunction() return FALSE end\n'
 prelude+='function ExecEventHalfBlendNoReset(event,blend) table.insert(calls,event) end\n'
 prelude+=f'function env(key,id) if key==GetSpEffectID then return {int(buff)} elseif key==IsAnimEnd then return {int(end)} elseif key==GetEventEzStateFlag then return {int(flag)} elseif key==GetItemAnimType then return {99 if empty else 0} else error(key) end end\n'
 program=prelude+function+'\n'+name+'_Upper_onUpdate();return table.concat(calls,",")'
 state=lua.luaL_newstate()
 try:
  lua.luaL_openlibs(state);assert lua.luaL_loadstring(state,program.encode())==0
  status=lua.lua_pcallk(state,0,1,0,0,None);out=lua.lua_tolstring(state,-1,None);assert status==0,out
  return out.decode().split(',') if out else []
 finally:lua.lua_close(state)
for state,end,flag,empty,buff,cancel in itertools.product(expected,(False,True),(False,True),(False,True),(False,True),(False,True)):
 actual=transition(state,end,flag,empty,buff,cancel);wanted=[]
 if not cancel:
  if state=='ItemDrinkStart' and (end or flag):
   if buff or not empty:wanted=['ItemDrinking']
   elif end:wanted=['ItemDrinkEmpty']
  elif state=='ItemDrinkStartMP' and flag:wanted=['ItemDrinkingMP']
  elif state in ('ItemDrinking','ItemDrinkingMP') and end:wanted=['ItemDrinkEnd']
 assert actual==wanted,(state,end,flag,empty,buff,cancel,actual,wanted)
 record('script',state=state,end=end,eventFlag=flag,empty=empty,baphomet=buff,cancel=cancel,transitions=actual)
print('PASS script',len(checks['script']),flush=True)
output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),attachParamSha256=sha(raw),
 scriptSha256=sha(script_raw),animationBundleSha256=bundle['sha256'],taeSha256=sha(rawtae),behaviorBundleSha256=graph.metadata['bundleSha256'],behaviorSha256=sha(graph.raw),
 families=families,marker=8801001,condition=2352,leaf=6851101,amount=8,interval=x.spells['6851100']['motionInterval'],events=events,paths=paths,checks=checks,
 native=dict(selection='4FEA30 → E6E150 → E6E3B0',animation='27D0F10 → 27D0400 → 410CA0',lifecycle='3C7FD0 → 50D060 → 5057D0 → 50ACD0',damage='503800',madness='state437 native self-grant'),
 stubs=sorted(stubs|{'synthetic inventory: curse slot3 paired with positive7000000; draw legality not asserted',
 'animation activity/time supplied by caller; eight actual TAE events dispatched, no full Havok scheduler or damage/cancel arbitration',
 'HKS upper-update functions run in Lua with explicit common-cancel/end/event/buff inputs; complete item admission and common functions not executed',
 'damage getter executed; final hit calculation/HP write not executed',
 'buildup resistance10000 avoids proc in timing tests; separate thresholds8/9/16/17 run real onset and HP/FP getters; immunity, natural decay, actual resource writes, death/reload and multiplayer not exercised',
 'disabled test applies inactive bits after qualification; equipment removal/rebuild not simulated'}),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',{k:len(v) for k,v in checks.items()},flush=True)
