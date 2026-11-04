"""Trace flask sharing through actual drink events, HKS and native recovery.

Animation scheduling, default-flask arrival and collision arrival are explicit.
The pinned TAE, script, effect lifecycle, hit reception and resource aggregation
execute directly; final resource setters and network transport are not simulated.
"""
import argparse,itertools,json,math,struct
from pathlib import Path
from native_effect_runtime import BASE,OBJ,STACK,STOP,Chain,Inputs,sha
from effect_behavior_graph import BehaviorGraph
from native_ailment_runtime import Ailment
from unicorn.x86_const import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','animations','behavior','script','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted)
attacks=Inputs.table(a.extracted.with_suffix('.AtkParam_Pc.param').read_bytes(),0x1d0)
animations=json.loads(a.animations.read_text());graph=BehaviorGraph(a.behavior)
assert animations['bundles'][0]['sha256']=='1410035ad79edb410fa41420ec259fcb4a1037d748c9c4a3b6ae8d1366c76d0f'
track=next(t for t in animations['bundles'][0]['taes'] if t['ID']==2000)
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

import ctypes,ctypes.util
lua=ctypes.CDLL(ctypes.util.find_library('lua5.4'));lua.luaL_newstate.restype=ctypes.c_void_p
lua.luaL_openlibs.argtypes=[ctypes.c_void_p];lua.luaL_loadstring.argtypes=[ctypes.c_void_p,ctypes.c_char_p]
lua.lua_pcallk.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_ssize_t,ctypes.c_void_p]
lua.lua_tolstring.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.POINTER(ctypes.c_size_t)];lua.lua_tolstring.restype=ctypes.c_char_p
lua.lua_close.argtypes=[ctypes.c_void_p]

script_raw=a.script.read_bytes();assert sha(script_raw)=='786f8a7bc89452d9531e2299b224c8945701c422437eca9aacbeb10a57a17f4d'
script=script_raw.decode('utf-8-sig').replace('\r\n','\n')
start=script.index('function ExecChangeFlask(');function=script[start:script.index('\nfunction ',start+1)]
def execute(c):
 ids=[n['id'] for n in c.nodes() if not n['flags']&0x800c0003]
 program="TRUE=1;FALSE=0;GetSpEffectID=1;AddSpEffect=2;local calls={};local active={"+','.join('['+str(id)+']=true' for id in ids)+"}\n"
 program+="function env(key,id) assert(key==GetSpEffectID);return active[id] and 1 or 0 end\nfunction act(key,id) assert(key==AddSpEffect);table.insert(calls,id) end\n"
 program+=function+"\nExecChangeFlask();return table.concat(calls,',')"
 state=lua.luaL_newstate()
 try:
  lua.luaL_openlibs(state);assert lua.luaL_loadstring(state,program.encode())==0
  status=lua.lua_pcallk(state,0,1,0,0,None);out=lua.lua_tolstring(state,-1,None);assert status==0,out
  result=[int(i) for i in out.decode().split(',') if i]
 finally:lua.lua_close(state)
 for id in result:c.grant(id)
 return result

from native_animation_runtime import NativeTae
raw=a.animations.with_name(a.animations.name+'.2000.tae').read_bytes();assert sha(raw)==track['sha256']
class Animated(Flask):
 def select(self,animation):
  tae=NativeTae(self,raw,track['sha256']);ctx=OBJ+0xd100;self.u.mem_write(ctx,bytes(0x40))
  for _ in range(1000):
   if not self.invoke(0x27d0400,[tae.animations[animation],ctx]):break
   typ=struct.unpack('<I',self.u.mem_read(ctx,4))[0]
   if typ!=67:continue
   payload=struct.unpack('<Q',self.u.mem_read(ctx+8,8))[0]
   if struct.unpack('<i',self.u.mem_read(payload,4))[0]!=7010211:continue
   self.ctx=ctx;self.q(OBJ+0x8018,OBJ+0x6000);return
  raise AssertionError('missing event')
 def event(self):
  self.u.mem_write(self.ctx+0x18,b'\1');self.invoke(0x410ca0,[OBJ+0x8000,self.ctx])

C=OBJ+0x60000;HIT=OBJ+0x61000;SOURCE=OBJ+0x62000;SEFFECT=OBJ+0x63000
class Hit(Actor):
 def __init__(self,kind=4,maximum=500):
  super().__init__(kind,maximum);self.u.mem_map(C,0x10000);self.q(C+8,OBJ+0x6000);self.sent=[]
  self.q(OBJ+0xf000,OBJ+0xe000);self.q(OBJ+0xf088,OBJ+0xf900);self.q(OBJ+0xf910,OBJ+0xfa00)
  self.u.mem_write(OBJ+0xe140,struct.pack('<i',10000));self.q(OBJ+0x6400,STOP+0x600)
  self.globalq(0x42715d+8+0x37e81d3,OBJ+0xfd00)
  self.q(SOURCE,OBJ+0x6200);self.q(SOURCE+0x190,SEFFECT);self.q(SEFFECT+0x10,SOURCE)
  self.u.mem_write(SOURCE+0x74,b'\1');self.u.mem_write(OBJ+0x6074,b'\6')
  self.q(OBJ+0x7118,STOP+0x601)
  self.globalq(0x1fe1c0+7+0x3a09709,OBJ+0x68000)
  self.stubs.add('explicit local hit-score context in mode 0')
  self.same=False;self.attack=2
 def hook(self,u,address,size,user):
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  pc=address-BASE
  if address==STOP+0x600:
   self.stubs.add('recipient virtual +200 false ordinary hit predicate');ret()
  elif pc==0x214f3e0:
   self.stubs.add('214F3E0 allocator identity for empty attacker effect-vector collection');ret(OBJ+0x7000)
  elif address==STOP+0x601:
   self.stubs.add('allocator virtual +18 explicit valid tag; native empty vector collection');ptr=u.reg_read(UC_X86_REG_RDX);u.mem_write(ptr,struct.pack('<I',32));ret(ptr)
  elif pc==0x3d4180:pass  # execute actual local-player comparison
  elif pc==0x26909a0:
   self.stubs.add('26909A0 security cookie preserves return value');ret(u.reg_read(UC_X86_REG_RAX))
  elif pc==0xe6d630:
   self.stubs.add('E6D630 actual AtkParam_Pc row lookup');assert u.reg_read(UC_X86_REG_R8)==self.attack and u.reg_read(UC_X86_REG_RDX)==1
   wrapper=u.reg_read(UC_X86_REG_RCX);u.mem_write(OBJ+0x64000,attacks[self.attack]);u.mem_write(wrapper,struct.pack('<iii4xQ',self.attack,0,1,OBJ+0x64000));ret()
  elif pc==0x3c80a0:
   sp=u.reg_read(UC_X86_REG_RSP);ptr=struct.unpack('<Q',u.mem_read(sp+0x30,8))[0]
   self.sent.append(dict(id=u.reg_read(UC_X86_REG_RDX)&0xffffffff,scales=list(struct.unpack('<15f',u.mem_read(ptr,60)))))
  else:super().hook(u,address,size,user)
 def hit(self,ids=(503,24240),attack=2,scale=0):
  self.attack=attack
  if isinstance(ids,int):ids=(ids,)
  self.u.mem_write(HIT,bytes(0x400))
  self.u.mem_write(HIT+0x40,struct.pack('<ii',attack,1))
  for slot,id in enumerate(ids,5):self.u.mem_write(HIT+0x70+slot*4,struct.pack('<i',id))
  self.u.mem_write(HIT+0x188,struct.pack('<ff',scale,1))
  self.u.mem_write(HIT+0x1a4,struct.pack('<7f',*([1]*7)))
  for off in (0x29c,0xd4,0x254):self.u.mem_write(HIT+off,struct.pack('<f',1))
  self.invoke(0x43be60,[C,OBJ+0x6000 if self.same else SOURCE,HIT,0,1,0])


class Recipient(Hit):
 def __init__(self):
  super().__init__();self.u.mem_write(SOURCE+0x74,b'\1');self.u.mem_write(OBJ+0x6074,b'\1')
 def hp(self,maximum=1000):
  self.invoke(0x506ec0,[OBJ,maximum,OBJ+0x800,OBJ+0x808,OBJ+0x820,0]);return list(struct.unpack('<7i',self.u.mem_read(OBJ+0x820,28)))

checks={key:[] for key in ('branches','projectile','amounts','targets','sourceModifiers','timeline')};stubs=set()
def record(group,c,**values):checks[group].append(values);stubs.update(c.stubs)
f32=lambda v:struct.unpack('<f',struct.pack('<f',v))[0]
paths=[];events=[]
for state in (50173,83047):
 selector=graph.reference(state,'generator');assert graph.selector_binding(selector)['name']=='IsBaphometBuff'
 clips=[]
 for child in graph.children(selector):
  children=graph.children(child);assert len(children)==1
  clips.append(graph.string(graph.reference(children[0],'animationName')))
 assert clips==['a000_050111','a000_050116']
 paths.append(dict(state=state,name=graph.name(state),selector=selector,clips=clips))
for animation in track['animations']:
 for event in animation['events']:
  if event['Type']==67 and struct.unpack_from('<i',bytes.fromhex(event['hex']))[0]==7010211:
   assert animation['ID'] in (50111,50116) and math.isclose(event['StartTime'],8/30,abs_tol=1e-7) and math.isclose(event['EndTime'],.3,abs_tol=1e-7)
   events.append(dict(animation=animation['ID'],**event))
assert len(events)==2
for effect,root in ((11001,7010200),(7010200,7010200),(8440200,8440200)):
 assert x.x['tables']['AttachEffectParam'][str(effect)]['passiveSpEffectId_1']==root
seed=x.spells['7010211']
assert seed['changeHpEstusFlaskCorrectRate']==0 and seed['replaceSpEffectId']==7010299
assert [seed['invocationConditionsStateChange'+str(i)] for i in (1,2,3)]==[2344,2015,2262]
assert 'function ItemDrinking_Upper_onUpdate()\n    local blend_type, lower_state = GetHalfBlendInfo()\n    ExecChangeFlask()' in script
branches=list(itertools.product((50111,50116),(0,1,3),(False,True),(False,True),(60,)))
branches+=list(itertools.product((50111,50116),(1,3),(False,),(False,),(30,120)))
for animation,copies,gradual,fpflag,fps in branches:
 c=Animated()
 for id in [7010200]*copies+([8440200] if gradual else [])+([8970020] if fpflag else []):c.grant(id)
 c.qualify();c.update(0);c.select(animation);packets=[];shots=[];calls=[]
 first=math.ceil(8*fps/30)
 for frame in range(fps):
  if frame==first:c.grant(501000) # explicit default consumable effect arrival
  if 8*fps<=frame*30<9*fps:c.event()
  emitted=execute(c);c.qualify();c.update(1/fps);c.invoke(0x50aa20,[OBJ]);hp=c.hp();fp=c.fp(100)
  if hp[1] or fp[1]:packets.append(dict(frame=frame,hp=hp[1],fp=fp[1]))
  shots+=c.shots;c.shots=[]
  if emitted:calls.append(dict(frame=frame,ids=emitted))
 expected=100 if gradual else 500 if copies else 600
 assert sum(p['hp'] for p in packets)==expected and sum(p['fp'] for p in packets)==(30 if fpflag else 0)
 ally=[i for i in shots if i!=1500]
 wanted=(([900102240,900102241] if gradual else [900102221])+([900102260] if fpflag else [])) if copies else []
 assert ally==wanted and len(calls)==bool(copies or gradual or fpflag)
 record('branches',c,animation=animation,copies=copies,gradual=gradual,fp=fpflag,fps=fps,packets=packets,allyBehaviors=ally,scriptCalls=calls)
print('PASS animation/script branches',len(checks['branches']),flush=True)

bullet_raw=a.extracted.with_suffix('.Bullet.param').read_bytes();bullets=Inputs.table(bullet_raw,0x100)
emissions={7010280:900102221,7010281:900102240,7010282:900102241,7010283:900102260}
leaves={900102221:7010221,900102240:7010240,900102241:7010241,900102260:7010260}
for emitter,behavior in emissions.items():
 row=x.spells[str(emitter)];b=x.x['tables']['BehaviorParam_PC'][str(behavior)];bullet=x.x['tables']['Bullet'][str(behavior)]
 assert row['stateInfo']==275 and row['behaviorId']==behavior and row['effectEndurance']==0
 assert b['refType']==1 and b['refId']==behavior
 assert bullet['atkId_Bullet']==800000100 and bullet['spEffectId0']==leaves[behavior]
 assert bullet['hitRadius']==15 and bullet['hitRadiusMax']==-1 and bullet['numShoot']==1 and bullet['isEndlessHit']==0
 assert bullet['HitBulletID']==bullet['intervalCreateBulletId']==-1 and math.isclose(bullet['life'],.1,abs_tol=1e-7)
attack=x.x['tables']['AtkParam_Pc']['800000100']
assert [attack[k] for k in ('selfTarget','friendlyTarget','opposeTarget','disableHitSpEffect')]==[0,1,0,0]
class Projectile(Chain):
 def __init__(self,id):self.bullet=id;self.frame=0;self.shots=[];super().__init__(x)
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if pc==0xe87800:
   assert u.reg_read(UC_X86_REG_RDX)&0xffffffff==self.bullet
   self.stubs.add('E87800 actual flask Bullet lookup');u.mem_write(OBJ+0xe900,bullets[self.bullet]);ptr=u.reg_read(UC_X86_REG_RCX)
   u.mem_write(ptr,struct.pack('<QI',OBJ+0xe900,self.bullet));ret(ptr)
  elif pc==0x347700:self.stubs.add('347700 projectile creation recorder; no scene geometry');self.shots.append(self.frame);ret(1)
  else:super().hook(u,address,size,user)
for bullet,fps in itertools.product(leaves,(30,120)):
 c=Projectile(bullet);slot=OBJ+0x4000
 c.u.mem_write(slot+0x329,b'\1');c.u.mem_write(slot+0x334,struct.pack('<I',bullet));c.u.mem_write(slot+0x494,b'\1')
 for frame in range(fps):c.frame=frame;c.invoke(0x343280,[slot],{UC_X86_REG_XMM1:1/fps})
 assert c.shots==[0];record('projectile',c,bullet=bullet,fps=fps,shots=c.shots)

self_leaves=(7010220,7010230,7010231,7010250);ally_leaves=tuple(leaves.values())
for leaf,mods,maximum in itertools.product(self_leaves+ally_leaves,([], [7611400], [6840100], [7611400,6840100]),(101,1000)):
 c=Flask() if leaf in self_leaves else Recipient()
 for id in mods:c.grant(id)
 c.qualify();c.update(0)
 if leaf in self_leaves:c.grant(leaf)
 else:c.hit(leaf,attack=800000100)
 c.qualify();c.update(0);hp=c.hp(maximum);fp=c.fp(maximum);row=x.spells[str(leaf)]
 multiplier=1
 for id in mods:multiplier=f32(multiplier*x.spells[str(id)]['changeHpEstusFlaskCorrectRate'])
 instant=math.trunc(f32(-f32(f32(maximum*f32(row['changeHpEstusFlaskRate']*multiplier))*f32(.01))))
 gradual=math.trunc(f32(-f32(maximum*f32(row['changeHpRate']*f32(.01)))))
 mana=math.trunc(f32(-f32(f32(maximum*row['changeMpEstusFlaskRate'])*f32(.01))))
 assert hp==[gradual,instant,gradual,0,0,0,0] and fp==[0,mana],(leaf,mods,maximum,hp,fp,instant,gradual,mana)
 record('amounts',c,leaf=leaf,mods=mods,maximum=maximum,hp=hp,fp=fp)
for leaf,typ in itertools.product(ally_leaves,range(10)):
 c=Recipient();c.u.mem_write(SOURCE+0x74,bytes([typ]));c.hit(leaf,attack=800000100);c.qualify();c.update(0)
 active=any(n['id']==leaf for n in c.nodes());assert active==(typ in (1,2,4))
 record('targets',c,leaf=leaf,sourceType=typ,same=False,accepted=active)
for leaf in ally_leaves:
 c=Recipient();c.same=True;c.hit(leaf,attack=800000100);c.qualify();c.update(0)
 assert not c.nodes();record('targets',c,leaf=leaf,same=True,accepted=False)
for source_mod,recipient_mod in itertools.product((None,7611400,6840100),repeat=2):
 c=Recipient()
 if source_mod:
  c.invoke(0x50d060,[SEFFECT,source_mod,OBJ+0xa00,-1,0,0x3f800000,0,0,16])
  c.invoke(0x5057d0,[SEFFECT,0,0],{UC_X86_REG_XMM1:1});c.invoke(0x50acd0,[SEFFECT,0,0],{UC_X86_REG_XMM1:0})
  node=struct.unpack('<Q',c.u.mem_read(SEFFECT+8,8))[0]
  assert struct.unpack('<i',c.u.mem_read(node+8,4))[0]==source_mod and not struct.unpack('<I',c.u.mem_read(node+0x68,4))[0]&0x800c0003
 if recipient_mod:c.grant(recipient_mod)
 c.qualify();c.update(0);c.hit(7010221,attack=800000100);c.qualify();c.update(0);hp=c.hp()
 assert hp[1]=={None:300,7611400:330,6840100:255}[recipient_mod]
 record('sourceModifiers',c,source=source_mod,recipient=recipient_mod,hp=hp)
print('PASS creation, recipients and amounts',flush=True)

baseline={}
for leaf,fps,copies,refresh in itertools.product((7010231,7010241),(30,60,120),(1,3),(False,True)):
 c=Flask() if leaf==7010231 else Recipient()
 def arrive():
  if leaf==7010231:c.grant(leaf)
  else:c.hit(leaf,attack=800000100)
 for _ in range(copies):arrive()
 c.qualify();c.update(0);pulses=[];life=x.spells[str(leaf)]['effectEndurance'];refreshed=None
 for frame in range(int((life+3)*fps)+1):
  if frame:
   if refresh and frame==2*fps:arrive()
   c.qualify();c.update(1/fps)
  hp=c.hp()
  if any(hp):assert hp==[10,0,10,0,0,0,0];pulses.append(frame)
  if refresh and frame==2*fps:refreshed=next(n['lifetime'] for n in c.nodes() if n['id']==leaf)
 assert pulses[0]==0 and abs(pulses[-1]/fps-(life+(2 if refresh else 0)))<.15
 assert len(pulses) in (int((life+(2 if refresh else 0))*10),int((life+(2 if refresh else 0))*10)+1)
 if refresh:assert math.isclose(refreshed,life-1/fps,abs_tol=1e-5)
 key=(leaf,fps,refresh)
 if copies==1:baseline[key]=pulses
 else:assert pulses==baseline[key]
 record('timeline',c,leaf=leaf,fps=fps,copies=copies,refresh=refresh,pulseFrames=pulses,amount=10,refreshedLifetime=refreshed)
fields=('stateInfo','spCategory','effectEndurance','motionInterval','replaceSpEffectId','cycleOccurrenceSpEffectId',
 'changeHpRate','changeHpPoint','changeHpEstusFlaskRate','changeHpEstusFlaskCorrectRate','changeMpEstusFlaskRate','effectTargetSelf','effectTargetFriend','effectTargetEnemy',
 'invocationConditionsStateChange1','invocationConditionsStateChange2','invocationConditionsStateChange3','behaviorId','dmypolyId')
ids={7010200,8440200,8970020,501000,501025,7010211,7010299,*self_leaves,*ally_leaves,*emissions}
output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),
 scriptSha256=sha(script_raw),animationBundleSha256=animations['bundles'][0]['sha256'],taeSha256=sha(raw),
 behaviorBundleSha256=graph.metadata['bundleSha256'],bulletParamSha256=sha(bullet_raw),effects=[11001,7010200],root=7010200,
 rows={str(id):{k:x.spells[str(id)][k] for k in fields} for id in sorted(ids)},
 emissions=emissions,leaves=leaves,radius=15,paths=paths,events=events,checks=checks,
 native=dict(event='410CA0',grant='3C7FD0',update='5057D0 → 50ACD0',emission='50AA20 → 3975D0',projectile='343280',
 recipient='43BE60 → 3C80A0',hp='506EC0 → 50B860',fp='507460'),
 stubs=sorted(stubs|{'explicit TAE window scheduling and default 501000 consumable arrival; full item consumption and animation interruption are not simulated',
 'actual HKS ExecChangeFlask runs in Lua with env queries bridged to native active node IDs and act calls bridged to genuine native self-grants',
 'actual friendly hit arrives after explicit collision; geometry, final HP/FP setters, overheal, death/reload and network synchronization remain unverified'}),gameplayVerified=False)
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(map(len,checks.values())),'native/script flask-sharing checks', {k:len(v) for k,v in checks.items()})
