"""Trace madness-animation FP recovery, version stacking and refresh.

Runs native TAE iteration, event delivery, effect maintenance and FP aggregation
with explicit actor inputs. The extracted original ExecDamage function also
runs in Lua 5.4 with environment fixtures, not in the game's HKS VM.
"""
import argparse,ctypes,ctypes.util,itertools,json,math,re,struct
from pathlib import Path
from native_effect_runtime import BASE,OBJ,STOP,Chain,Inputs,sha
from native_ailment_runtime import Ailment
from native_animation_runtime import NativeTae
from effect_behavior_graph import BehaviorGraph
from unicorn.x86_const import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','animations','behavior','script','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted);inputs=x
raw=a.extracted.with_suffix('.AttachEffectParam.param').read_bytes();rows=Inputs.table(raw,0x44)
assert sha(raw)=='ae8128ed510a532d0fa7cb56fa9c86e4a44c9d815dd4ee01c05821d5f50a9827'
assert len(rows)==struct.unpack_from('<H',raw,10)[0]
assert sha(x.param)=='07ec636c5565d4551efeb53e6f08bc633b2aa4f2129f13c61b0638d69b1bc176'
ROOTS=(7035500,7035510);LEAVES=(7035502,7035512)
families=[]
for root,state in zip(ROOTS,(2279,2376)):
 att=x.x['tables']['AttachEffectParam'][str(root)];r=x.spells[str(root)];m=x.spells[str(root+1)];leaf=x.spells[str(root+2)]
 assert [att[k] for k in ('passiveSpEffectId_1','passiveSpEffectId_2','passiveSpEffectId_3','permanentSpEffectId','exclusivityId')]==[root,-1,-1,-1,-1]
 assert all(v==1 for k,v in att.items() if k.startswith('allow'))
 assert (r['stateInfo'],r['spCategory'],r['effectEndurance'])==(state,10,-1)
 assert (m['spCategory'],m['effectEndurance'],m['motionInterval'],m['invocationConditionsStateChange1'],m['cycleOccurrenceSpEffectId'])==(10,0,1,state,root+2)
 assert (leaf['stateInfo'],leaf['spCategory'],leaf['effectEndurance'],leaf['motionInterval'],leaf['changeMpPoint'],leaf['changeMpRate'],leaf['invocationConditionsStateChange1'])==(0,20,25,.5,-1,0,state)
 families.append(dict(effect=root,root=root,marker=root+1,leaf=root+2,state=state))
checks={k:[] for k in ('selection','rawEvents','dispatch','amounts','lifetime','refresh','markerRefresh','removal','extension','disabled','mixed','script')};stubs=set()
def record(key,c=None,**row):
 checks[key].append(row)
 if c is not None:stubs.update(c.stubs)
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

class Recovery(Actor):
 def hook(self,u,address,size,user):
  if address-BASE in (0x3ced90,0x4d1b20):
   u.reg_write(UC_X86_REG_RAX,OBJ+0xd800 if address-BASE==0x3ced90 else 0);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  else:super().hook(u,address,size,user)
 def event(self,payload,active=1):
  self.q(OBJ+0xd018,OBJ+0x6000);self.q(OBJ+0xd108,OBJ+0xd200)
  self.u.mem_write(OBJ+0xd100,struct.pack('<I',67));self.u.mem_write(OBJ+0xd118,bytes([active]));self.u.mem_write(OBJ+0xd200,payload)
  self.invoke(0x410ca0,[OBJ+0xd000,OBJ+0xd100])
lua_library=ctypes.util.find_library('lua5.4');assert lua_library,'liblua5.4 is required for isolated script checks'
lib=ctypes.CDLL(lua_library)
lib.luaL_newstate.restype=ctypes.c_void_p;lib.luaL_openlibs.argtypes=[ctypes.c_void_p];lib.lua_close.argtypes=[ctypes.c_void_p]
lib.luaL_loadbufferx.argtypes=[ctypes.c_void_p,ctypes.c_char_p,ctypes.c_size_t,ctypes.c_char_p,ctypes.c_char_p];lib.luaL_loadbufferx.restype=ctypes.c_int
lib.lua_pcallk.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_ssize_t,ctypes.c_void_p];lib.lua_pcallk.restype=ctypes.c_int
lib.lua_tolstring.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.POINTER(ctypes.c_size_t)];lib.lua_tolstring.restype=ctypes.c_char_p
script=a.script.read_bytes();assert sha(script)=='96339bb15f57559cd42a940d616fcc2a18a10f50845cfc22b46b356ab66c3b29'
script_text=script.decode('utf-8-sig').replace('\r\n','\n')
s=next(m[0] for m in re.finditer(r'^function (\w+)\([^\n]*\).*?(?=^function |\Z)',script_text,re.M|re.S) if m[1]=='ExecDamage')
assert 'env(GetDamageSpecialAttribute, STATUS_EFFECT_MADNESS)' in s and 'ExecEventAllBody("W_DamageMad")' in s
def run(overrides):
 ctx=', '.join('["'+k+'"]='+str(v) for k,v in overrides.items())
 prefix='''TRUE=1;FALSE=0;local calls={};local reads={};local overrides={OVERRIDES}
setmetatable(_G,{__index=function(_,key)return key end})
function env(key,arg)
 reads[#reads+1]=key..':'..tostring(arg)
 if overrides[key..':'..tostring(arg)]~=nil then return overrides[key..':'..tostring(arg)] end
 if overrides[key]~=nil then return overrides[key] end
 if key=='GetHP' then return 1000 end
 if key=='HasReceivedAnyDamage' then return 1 end
 if key=='GetDamageSpecialAttribute' and arg=='STATUS_EFFECT_MADNESS' then return 1 end
 return 0
end
function act(...)end
function SetVariable(...)end
function ExecEventAllBody(name)calls[#calls+1]=name end
'''.replace('OVERRIDES',ctx)
 text=(prefix+s+"\nlocal result=ExecDamage(FALSE,FALSE); return tostring(result)..'|'..table.concat(calls,',')..'|'..table.concat(reads,',')").encode();L=lib.luaL_newstate();lib.luaL_openlibs(L)
 try:
  rc=lib.luaL_loadbufferx(L,text,len(text),b'ExecDamage-fixture',None)
  if not rc:rc=lib.lua_pcallk(L,0,1,0,0,None)
  output=lib.lua_tolstring(L,-1,None).decode();assert rc==0,output
  return output
 finally:lib.lua_close(L)

for overrides in ({},{'IsDamageMotionOff':1},{'GetSpEffectID:102551':1},{'Unknown426':1},{'Unknown1012':1},{'GetSpEffectID:708050':1}):
 result=run(overrides);parts=result.split('|');assert parts[:2]==(['1','W_DamageMad'] if not overrides else ['0','']),result
 record('script',overrides=overrides,result=parts[0],events=parts[1],reads=parts[2].split(','))
graph=BehaviorGraph(a.behavior);binding=graph.state('DamageMad');assert binding['animation']=='a000_005850'
anim=json.loads(a.animations.read_text());assert anim['bundles'][0]['sha256']=='806e6b218d747277ab45e14f45ca80b9ecf8c13ada22f89db2d3ef23caa62b2a'
ta=next(t for b in anim['bundles'] for t in b['taes'] if t['ID']==2000)
expectedEvents=[e for a in ta['animations'] if a['ID']==5850 for e in a['events'] if e['Type']==67 and struct.unpack('<i',bytes.fromhex(e['hex'])[:4])[0] in (7035501,7035511)]
assert len(expectedEvents)==2
c=Recovery();taeraw=Path(str(a.animations)+'.2000.tae').read_bytes();loader=NativeTae(c,taeraw,ta['sha256']);ctx=OBJ+0xd100;c.u.mem_write(ctx,bytes(0x40));events=[]
while c.invoke(0x27d0400,[loader.animations[5850],ctx]):
 if struct.unpack('<I',c.u.mem_read(ctx,4))[0]!=67:continue
 ptr=struct.unpack('<Q',c.u.mem_read(ctx+8,8))[0];id=struct.unpack('<i',c.u.mem_read(ptr,4))[0]
 if id not in (7035501,7035511):continue
 payload=bytes(c.u.mem_read(ptr,16));times=struct.unpack('<Q',c.u.mem_read(ctx+0x20,8))[0];start,end=struct.unpack('<f4xf',c.u.mem_read(times,12))
 event=dict(id=id,payload=payload.hex(),start=start,end=end);assert any(payload==bytes.fromhex(e['hex']) and math.isclose(start,e['StartTime'],abs_tol=1e-7) and math.isclose(end,e['EndTime'],abs_tol=1e-7) for e in expectedEvents)
 events.append(event);record('rawEvents',c,**event)
assert len(events)==2 and all(e['start']==0 and math.isclose(e['end'],.1,rel_tol=1e-6) for e in events)
def equip(counts=(1,1),extra=()):
 c=Recovery()
 for root,n in zip(ROOTS,counts):
  for _ in range(n):c.grant(root)
 for id in extra:c.grant(id)
 c.qualify();c.update(0);return c
def step(c,fps=60):c.qualify();c.update(1/fps)
def active(c):return sorted(n['id'] for n in c.nodes() if n['id'] in LEAVES and not n['flags']&0x800c0003)
def fire(c,which=(0,1),flag=1):
 for i in which:c.event(bytes.fromhex(events[i]['payload']),flag)
def timeline(c,fps,starts=(0,),seconds=26,which=(0,1)):
 pulses=[];changes=[];prev=None;grants=[]
 for frame in range(seconds*fps):
  before=len(c.grants)
  if any(t<=frame<t+round(.1*fps) for t in starts):fire(c,which)
  step(c,fps);grants.extend(dict(frame=frame,id=id) for id in c.grants[before:] if id in LEAVES)
  now=active(c);values=c.fp(1000)
  if now!=prev:changes.append(dict(frame=frame,leaves=now));prev=now
  if any(values):pulses.append(dict(frame=frame,values=values))
 return dict(pulses=pulses,changes=changes,grants=grants)
sets=[[ROOTS[0]],[ROOTS[1]],[ROOTS[0]]*3,[ROOTS[1]]*3,list(ROOTS),list(ROOTS)*3]
for ids,hero in itertools.product(sets,range(11)):
 c=Selection([[e] for e in ids],hero);bits=c.select();accepted=[]
 for i,id in enumerate(ids):
  if 6*i in bits:
   c.invoke(0xe6e150,[OBJ+0x9200,id]);accepted.append(c.invoke(0xe6e3b0,[OBJ+0x9200,0])&0xffffffff)
 assert accepted==ids;record('selection',c,effects=ids,hero=hero,bits=bits,roots=accepted)
for counts,flag,which in itertools.product(itertools.product((0,1,3),repeat=2),(0,1),((0,),(1,),(0,1))):
 c=equip(counts);fire(c,which,flag)
 for _ in range(6):step(c)
 expected=[LEAVES[i] for i,n in enumerate(counts) if n and i in which]
 assert active(c)==expected;record('dispatch',c,counts=counts,eventActive=flag,which=which,leaves=active(c),nodes=c.nodes())
for counts,maximum in itertools.product(itertools.product((0,1,3),repeat=2),(1,99,1000,2345)):
 c=equip(counts);fire(c);step(c);step(c);values=c.fp(maximum)
 assert values==[sum(bool(n) for n in counts),0]
 record('amounts',c,counts=counts,maximum=maximum,values=values)
print('PASS selection/dispatch/amounts',*[len(checks[k]) for k in ('selection','dispatch','amounts')],flush=True)
for counts,fps in itertools.product(((1,0),(0,1),(1,1),(3,3)),(30,60,120)):
 c=equip(counts);result=timeline(c,fps);units=sum(bool(n) for n in counts);changes=result['changes'];pulses=result['pulses']
 assert [bool(v['leaves']) for v in changes]==[False,True,False]
 assert abs(changes[-1]['frame']-changes[1]['frame']-25*fps)<=4
 assert len(pulses)==51 and pulses[0]['frame']==changes[1]['frame']
 assert all(v['values']==[units,0] for v in pulses)
 assert all(abs(b['frame']-a['frame']-.5*fps)<=1 for a,b in zip(pulses,pulses[1:]))
 record('lifetime',c,counts=counts,fps=fps,**result);print('PASS lifetime',counts,fps,flush=True)
for counts,starts in itertools.product(((1,1),(3,3)),((0,),(0,60),(0,300))):
 c=equip(counts);result=timeline(c,60,starts,31);changes=result['changes'];pulses=result['pulses']
 assert [bool(v['leaves']) for v in changes]==[False,True,False]
 assert abs(changes[-1]['frame']-starts[-1]-1500)<=4
 assert all(v['values']==[2,0] and v['frame']==1+30*i for i,v in enumerate(pulses))
 assert len(result['grants'])==2*len(starts)
 record('refresh',c,counts=counts,starts=starts,**result)
for times in ((0,),(0,1),(0,6),(0,60),(0,300)):
 c=equip((1,0));grants=[]
 for frame in range(times[-1]+10):
  before=len(c.grants)
  if frame in times:fire(c,(0,))
  step(c);grants.extend(dict(frame=frame,id=id) for id in c.grants[before:] if id in LEAVES)
 assert [v['frame'] for v in grants]==([0] if times==(0,1) else list(times))
 record('markerRefresh',c,arrivals=times,grants=grants,nodes=c.nodes())
for removal in ((ROOTS[0],),(ROOTS[1],),ROOTS):
 c=equip();fire(c)
 for _ in range(31):step(c)
 for index in reversed([i for i,n in enumerate(c.nodes()) if n['id'] in removal]):c.invoke(0x505280,[OBJ,index])
 samples=[]
 for frame in range(65):
  step(c);values=c.fp(1000);present=active(c)
  assert present==[leaf for root,leaf in zip(ROOTS,LEAVES) if root not in removal]
  assert values[0] in (0,2-len(removal)) and values[1]==0
  if frame in (0,1,30,64):samples.append(dict(frame=frame,values=values,nodes=c.nodes()))
 for root in removal:c.grant(root)
 resumed=[]
 for frame in range(2):
  step(c);resumed.append(dict(frame=frame,leaves=active(c),values=c.fp(1000)))
 assert active(c)==list(LEAVES)
 record('removal',c,removed=removal,samples=samples,resumed=resumed,readded=c.nodes())
for family,extra in itertools.product(families,(None,7006400,8330500)):
 c=equip(extra=(() if extra is None else (extra,)));c.grant(family['leaf']);c.qualify();c.update(0);c.qualify();c.update(1)
 node=next(n for n in c.nodes() if n['id']==family['leaf']);assert math.isclose(node['lifetime'],24,abs_tol=.001)
 record('extension',c,leaf=family['leaf'],extra=extra,node=node)
for family,mask in itertools.product(families,(1,2,0x40000,0x80000000)):
 c=equip();c.grant(family['leaf']);c.qualify();c.update(0);assert c.fp(1000)==[1,0]
 ptr=struct.unpack('<Q',c.u.mem_read(OBJ+8,8))[0]
 while struct.unpack('<i',c.u.mem_read(ptr+8,4))[0]!=family['leaf']:ptr=struct.unpack('<Q',c.u.mem_read(ptr+0x38,8))[0]
 flags=struct.unpack('<I',c.u.mem_read(ptr+0x68,4))[0];c.u.mem_write(ptr+0x68,struct.pack('<I',flags|mask));values=c.fp(1000);assert values==[0,0]
 record('disabled',c,leaf=family['leaf'],mask=mask,originalFlags=flags,values=values)
print('PASS refresh/marker/removal/extension/disabled',*[len(checks[k]) for k in ('refresh','markerRefresh','removal','extension','disabled')],flush=True)
# Compare complete native packets per frame against isolated-source baselines.
base={}
for counts in itertools.product((0,1,3),repeat=3):
 c=equip(counts[:2],(7006506,)*counts[2]);values=[]
 for frame in range(6*60):
  if frame<6:fire(c)
  step(c);values.append(c.fp(1000))
 if sum(bool(v) for v in counts)<=1:base[counts]=values
 expected=[[sum(base[tuple(counts[j] if j==i else 0 for j in range(3))][frame][channel] for i in range(3)) for channel in range(2)] for frame in range(360)]
 assert values==expected,(counts,values[:3],expected[:3])
 record('mixed',c,counts=counts,pulses=[dict(frame=i,values=v) for i,v in enumerate(values) if any(v)])
print('PASS mixed',len(checks['mixed']),flush=True)
out=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),attachParamSha256=sha(raw),
 animationBundleSha256=anim['bundles'][0]['sha256'],taeSha256=sha(taeraw),behaviorBundleSha256=graph.metadata['bundleSha256'],hkxSha256=graph.metadata['hkxSha256'],scriptSha256=sha(script),
 families=families,binding=binding,events=events,amount=1,interval=.5,duration=25,checks=checks,
 native=dict(selection='4FEA30 → E6E150 → E6E3B0',tae='27D0F10 → 27D0400',event='410CA0 → 40FF20 → 3C8BE0 → 3C80A0',
 grant='3C7FD0',insert='50D060',qualify='5057D0',update='50ACD0',fp='507460',remove='505280'),
 scriptExecution='Lua 5.4 executes the extracted original ExecDamage function with explicit env/helper fixtures; not the game HKS VM.',
 stubs=sorted(stubs|{'Native event scheduling time/activity and actor identity are explicit fixtures.', 'Behavior graph reads reviewed, patched references; no full Havok VM.'}),
 limitations=['Full damage dispatch/onset-to-animation scheduling, alternate or interrupted actions, all guard combinations, final current FP write/cap and overflow are not simulated.',
 'Removing and readding roots tests raw effect-container qualification/pause only, not the full equipment teardown or rebuild.',
 'DLL rewrites, death/reload and multiplayer remain untraced.'],gameplayVerified=False)
a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print('PASS counts',{k:len(v) for k,v in checks.items()},sum(map(len,checks.values())),flush=True)
