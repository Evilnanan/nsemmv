"""Trace revival-triggered HP-cap/attack curses and independently timed stacks.

Pinned HKS and behavior paths select actual TAE events. Native selection,
self-grants, qualification, lifetimes and numeric consumers execute with
explicit actor and animation time inputs. Full revival/resource sync is not run.
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
graph=BehaviorGraph(a.behavior)
node=graph.named('NearDeathRevival','hkbStateMachine::StateInfo');selector=graph.reference(node,'generator')
assert graph.item(selector)[0]['Identity']=='hkbManualSelectorGenerator'
binding=graph.selector_binding(selector);assert binding['name']=='IsAutoRevival';paths=[]
for index,child in enumerate(graph.children(selector)):
 assert graph.item(child)[0]['Identity']=='CustomManualSelectorGenerator'
 clips=graph.children(child);assert len(clips)==1
 animation=graph.string(graph.reference(clips[0],'animationName'));assert animation==f'a000_{17650+index:06}'
 paths.append(dict(state='NearDeathRevival',stateItem=node,selector=selector,binding=binding,child=child,clip=clips[0],animation=17650+index))
assert len(paths)==2
animations=json.loads(a.animations.read_text());bundle=animations['bundles'][0]
assert bundle['sha256']=='806e6b218d747277ab45e14f45ca80b9ecf8c13ada22f89db2d3ef23caa62b2a'
track=next(t for t in bundle['taes'] if t['ID']==2000)
rawtae=a.animations.with_name(a.animations.name+'.2000.tae').read_bytes();assert sha(rawtae)==track['sha256']
events=[]
for b in animations['bundles']:
 for t in b['taes']:
  for animation in t['animations']:
   for event in animation['events']:
    if event['Type']==67 and struct.unpack_from('<i',bytes.fromhex(event['hex']))[0]==6851701:
     assert t['ID']==2000 and event['StartTime']==0 and math.isclose(event['EndTime'],1/30,rel_tol=1e-6)
     events.append(dict(animation=animation['ID'],**event))
assert [e['animation'] for e in events]==[17650,17651]
families=[]
for effect,root,field,rate in ((6851700,6851700,'maxHpRate',.75),(6851701,6851710,'physicsAttackRate',.7)):
 attach=x.x['tables']['AttachEffectParam'][str(effect)];r=x.spells[str(root)];bridge=x.spells[str(root+2)];leaf=x.spells[str(root+3)]
 assert attach['passiveSpEffectId_1']==root and attach['exclusivityId']==-1
 assert all(attach[k]==-1 for k in ('passiveSpEffectId_2','passiveSpEffectId_3','permanentSpEffectId'))
 assert (r['spCategory'],r['effectEndurance'],r['cycleOccurrenceSpEffectId'],r['replaceSpEffectId'])==(10,0,root+3,root+2)
 assert [r['invocationConditionsStateChange'+str(i)] for i in (1,2,3)]==[2219,0,0]
 assert bridge['spCategory']==10 and math.isclose(bridge['effectEndurance'],.1,rel_tol=1e-6) and bridge['replaceSpEffectId']==root
 assert leaf['spCategory']==10 and leaf['effectEndurance']==60 and leaf['replaceSpEffectId']==leaf['cycleOccurrenceSpEffectId']==-1
 assert all(leaf['invocationConditionsStateChange'+str(i)]==0 for i in (1,2,3))
 assert math.isclose(leaf[field],rate,rel_tol=1e-6)
 if effect==6851701:assert all(leaf[f]==leaf[field] for f in ('magicAttackRate','fireAttackRate','thunderAttackRate','darkAttackRate'))
 families.append(dict(effect=effect,root=root,bridge=root+2,leaf=root+3,field=field,rate=leaf[field],duration=60))
marker=x.spells['6851701'];assert (marker['stateInfo'],marker['spCategory'],marker['effectEndurance'])==(2219,20,0)
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
   if struct.unpack('<i',self.u.mem_read(payload,4))[0]!=6851701:continue
   self.ctx=ctx;self.q(OBJ+0x8018,OBJ+0x6000);return
  raise AssertionError(('missing event',animation))
 def event(self):
  self.u.mem_write(self.ctx+0x18,b'\1');self.invoke(0x410ca0,[OBJ+0x8000,self.ctx])
 def step(self,fps=60,active=False,native=False):
  if active:
   if native:self.event()
   else:self.grant(6851701)
  self.qualify();self.update(1/fps)
 def taken(self):
  self.u.mem_write(OBJ+0x800,bytes(0x200))
  self.invoke(0x503800,[OBJ,OBJ+0x500,OBJ+0x520,OBJ+0x540,OBJ+0x800])
  return list(struct.unpack('<5f',self.u.mem_read(OBJ+0x500,20)))
def scalar(c,rva,args):
 c.invoke(rva,args);return struct.unpack('<f',(c.u.reg_read(UC_X86_REG_XMM0)&0xffffffff).to_bytes(4,'little'))[0]
def counts(c):return [len([n for n in c.nodes() if n['id']==f['leaf'] and not n['flags']&0x800c0003]) for f in families]
def f32(v):return struct.unpack('<f',struct.pack('<f',v))[0]
def power(rate,copies):
 value=1.
 for _ in range(copies):value=f32(value*rate)
 return value
def values(c):return dict(hp=scalar(c,0x6c9150,[1000,OBJ]),attack=c.attack())
def expected(c,copies):
 val=values(c);assert math.isclose(val['hp'],f32(1000*power(families[0]['rate'],copies[0])),rel_tol=1e-6)
 assert val['attack']==[power(families[1]['rate'],copies[1])]*5,(copies,val)
 return val
checks={k:[] for k in ('selection','dispatch','lifetime','independent','disabled','script')};stubs=set()
def record(group,c=None,**values):
 checks[group].append(values)
 if c is not None:stubs.update(c.stubs)
for f,copies,hero in itertools.product(families,(1,2,3,6),range(11)):
 slots=[[7000000,-1,-1,f['effect']]]*copies;c=Selection(slots,hero);bits=c.select();roots=[]
 for index in range(copies):
  assert index*6+3 in bits
  id=struct.unpack('<i',c.u.mem_read(OBJ+0xa000+index*0x80+0x24,4))[0];assert id==f['effect']
  c.invoke(0xe6e150,[OBJ+0x9200,id]);roots.append(c.invoke(0xe6e3b0,[OBJ+0x9200,0])&0xffffffff)
 assert roots==[f['root']]*copies
 record('selection',c,effect=f['effect'],copies=copies,hero=hero,curseSlot=3,bits=bits,roots=roots)
print('PASS selection',len(checks['selection']),flush=True)
for animation,fps,copies in itertools.product((17650,17651),(30,60,120),(0,1,3)):
 c=Animated()
 for _ in range(copies):
  for f in families:c.grant(f['root'])
 for _ in range(10):c.step(fps)
 assert counts(c)==[0,0];neutral=expected(c,[0,0]);c.select(animation)
 # Dispatch only within the actual window while that caller animation is active.
 dispatches=0
 for frame in range(fps):
  active=frame*30<fps
  c.step(fps,active,True);dispatches+=int(active)
 assert counts(c)==[copies,copies]
 assert all(c.grants.count(f['leaf'])==copies for f in families)
 record('dispatch',c,animation=animation,fps=fps,copies=copies,nativeDispatches=dispatches,neutral=neutral,values=expected(c,[copies,copies]),nodes=c.nodes())
 print('PASS event',animation,fps,copies,flush=True)
# The marker delivery above is proven against actual TAE; timers below use the
# same native self-grant to avoid reparsing the unchanged TAE for each timeline.
for fps,copies in itertools.product((30,60,120),(1,3)):
 c=Animated()
 for _ in range(copies):
  for f in families:c.grant(f['root'])
 transitions=[];last=None
 for frame in range(67*fps):
  active=frame*30<fps or 5*fps<=frame and (frame-5*fps)*30<fps
  c.step(fps,active)
  current=counts(c)
  if current!=last:
   transitions.append(dict(frame=frame,copies=current,values=expected(c,current),nodes=c.nodes()));last=current
 assert [t['copies'] for t in transitions]==[[0,0],[copies,copies],[2*copies,2*copies],[copies,copies],[0,0]],(fps,copies,transitions)
 for change,seconds in zip(transitions[1:],(0,5,60,65)):
  assert abs(change['frame']/fps-seconds)<=4.01/fps,(fps,copies,change['frame'],seconds)
 record('lifetime',c,fps=fps,copies=copies,transitions=transitions)
 print('PASS lifetime',fps,copies,flush=True)
for index,f in enumerate(families):
 for copies in (0,1,2,3):
  c=Animated()
  for _ in range(copies):c.grant(f['root'])
  c.step(active=True)
  for _ in range(9):c.step()
  wanted=[0,0];wanted[index]=copies
  assert counts(c)==wanted
  record('independent',c,effect=f['effect'],copies=copies,values=expected(c,wanted),nodes=c.nodes())
print('PASS independent',len(checks['independent']),flush=True)
for stage in ('root','leaf'):
 c=Animated()
 for _ in range(3):
  for f in families:c.grant(f[stage])
 c.qualify();c.update(0)
 if stage=='root':c.grant(6851701)
 c.qualify()
 ptr=struct.unpack('<Q',c.u.mem_read(OBJ+8,8))[0]
 while ptr:
  id=struct.unpack('<i',c.u.mem_read(ptr+8,4))[0]
  if id in [f[stage] for f in families]:c.u.mem_write(ptr+0x68,struct.pack('<I',0x800c0003))
  ptr=struct.unpack('<Q',c.u.mem_read(ptr+0x38,8))[0]
 c.update(0);val=expected(c,[0,0]);assert counts(c)==[0,0]
 record('disabled',c,stage=stage,values=val)
print('PASS disabled',len(checks['disabled']),flush=True)
lua=ctypes.CDLL(ctypes.util.find_library('lua5.4'));lua.luaL_newstate.restype=ctypes.c_void_p
lua.luaL_openlibs.argtypes=[ctypes.c_void_p];lua.luaL_loadstring.argtypes=[ctypes.c_void_p,ctypes.c_char_p]
lua.lua_pcallk.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_ssize_t,ctypes.c_void_p]
lua.lua_tolstring.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.POINTER(ctypes.c_size_t)];lua.lua_tolstring.restype=ctypes.c_char_p
lua.lua_close.argtypes=[ctypes.c_void_p]
start=script.index('function NearDeathCommonFunction()');function=script[start:script.index('\nfunction ',start+1)]
def branch(ids,health,time,falling,moving):
 prelude='TRUE=1;FALSE=0;DAMAGE_TYPE_DEATH_FALLING=99;SetAllowedThrowDefenseType=1;GetReceivedDamageType=2;GetSpEffectID=3;GetNearDeathTime=4;GetNearDeathHealth=5;IsMoveCancelPossible=6;local calls={};local vars={IsAutoRevival=9,MoveSpeedLevel='+str(int(moving))+'};local ids={'+','.join('['+str(id)+']=true' for id in ids)+'};\n'
 prelude+='function act(key,value) assert(key==SetAllowedThrowDefenseType and value==255) end\nfunction SetVariable(key,value) vars[key]=value end\nfunction GetVariable(key) return vars[key] end\nfunction ExecEventAllBody(event) table.insert(calls,event) end\n'
 prelude+=f'function env(key,id) if key==GetReceivedDamageType then return {99 if falling else 0} elseif key==GetSpEffectID then return ids[id] and TRUE or FALSE elseif key==GetNearDeathTime then return {time} elseif key==GetNearDeathHealth then return {health} elseif key==IsMoveCancelPossible then return {int(moving)} else error(key) end end\n'
 program=prelude+function+'\nNearDeathCommonFunction();return table.concat(calls,",").."|"..vars.IsAutoRevival'
 state=lua.luaL_newstate()
 try:
  lua.luaL_openlibs(state);assert lua.luaL_loadstring(state,program.encode())==0
  status=lua.lua_pcallk(state,0,1,0,0,None);out=lua.lua_tolstring(state,-1,None);assert status==0,out
  event,auto=out.decode().split('|');return event,int(auto)
 finally:lua.lua_close(state)
sets=[[]]+[[id] for id in (102130,102145,102121,102120,102455,705020,6999505,6999105,540150,8970061,102110)]+[[102455,8970061],[102120,8970061],[102130,8970061]]
for ids,health,time,falling,moving in itertools.product(sets,(0,1),(0,1),(False,True),(False,True)):
 event,auto=branch(ids,health,time,falling,moving);expected_auto=0
 if falling or 102130 in ids or 102145 in ids:wanted='W_NearDeathEnd'
 elif 102121 in ids:wanted='W_NearDeathRevival'
 elif time<=0 and 102120 not in ids:wanted='W_NearDeathEnd'
 elif health<=0 and 102455 not in ids:wanted='W_NearDeathRevival'
 elif set(ids)&{705020,6999505,6999105,540150,8970061}:
  wanted='W_NearDeathRevival';expected_auto=int(8970061 in ids)
 elif moving:wanted='W_NearDeathMove'
 elif 102110 in ids:wanted='W_NearDeathIdle'
 else:wanted=''
 assert (event,auto)==(wanted,expected_auto)
 record('script',ids=ids,health=health,time=time,falling=falling,moving=moving,event=event,auto=auto)
output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),attachParamSha256=sha(raw),
 scriptSha256=sha(script_raw),animationBundleSha256=bundle['sha256'],taeSha256=sha(rawtae),behaviorSha256=sha(graph.raw),paths=paths,events=events,
 families=families,marker=6851701,condition=2219,checks=checks,native=dict(selection='4FEA30 → E6E150 → E6E3B0',animation='27D0F10 → 27D0400 → 410CA0',
 lifecycle='3C7FD0 → 50D060 → 5057D0 → 50ACD0',hp='6C9150',attack='502830'),
 stubs=sorted(stubs|{'synthetic inventory: curse slot3 paired with positive7000000; draw legality not asserted',
 'HKS near-death health/time, effect membership, fall/movement flags supplied explicitly; complete near-death resource handling not executed',
 'animation activity/time supplied by caller; actual TAE dispatch verified but no full Havok scheduling or interruptions',
 '60-second timeline reuses proven marker through native self-grant; HP capacity base1000, final current/max HP write and clamp not simulated',
 'actual hit damage, extreme stack counts, equipment changes, death/reload and multiplayer not simulated'}),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',{k:len(v) for k,v in checks.items()},flush=True)
