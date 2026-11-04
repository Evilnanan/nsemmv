"""Trace guard-animation aggro effects into the native AI target score.

Actual HKS, reviewed graph edges, raw TAE, effect lifecycle and AI priority
arithmetic execute. Input/actor context and unrelated score terms are fixtures;
full animation scheduling, enemy target selection and gameplay do not execute.
"""
import argparse,json,struct,itertools,ctypes,ctypes.util,math
from pathlib import Path
from native_effect_runtime import *
from native_ailment_runtime import Ailment
from native_animation_runtime import NativeTae
from effect_behavior_graph import BehaviorGraph
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','animations','script','behavior','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted)
graph=BehaviorGraph(a.behavior);animations=json.loads(a.animations.read_text())
tracks={t['ID']:t for b in animations['bundles'] for t in b['taes'] if t['ID'] in(2000,2015)}
raws={id:Path(str(a.animations)+'.'+str(id)+'.tae').read_bytes() for id in tracks}
raw_script=a.script.read_bytes();assert sha(raw_script)=='786f8a7bc89452d9531e2299b224c8945701c422437eca9aacbeb10a57a17f4d'
source=raw_script.decode('utf-8-sig').replace('\r\n','\n')
start=source.index('function ExecGuard(');guard_function=source[start:source.index('\nfunction ',start+1)]
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

class Fire(Actor):
 def __init__(self,hand=0):
  self.hand=hand;super().__init__();self.q(OBJ+0x6478,STOP+0x800)
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if address==STOP+0x800:
   self.stubs.add('actor virtual +278 explicit style 0/2 for context-12 hand check');ret(self.hand)
  elif pc in (0x3ced90,0x4d1b20):
   self.stubs.add('3CED90/4D1B20 explicit animation-owner context');ret(OBJ+0xd800 if pc==0x3ced90 else 0)
  else:super().hook(u,address,size,user)
 def event(self,id,active=1):
  self.q(OBJ+0xd018,OBJ+0x6000);self.q(OBJ+0xd108,OBJ+0xd200)
  self.u.mem_write(OBJ+0xd100,struct.pack('<I',67));self.u.mem_write(OBJ+0xd118,bytes([active]))
  self.u.mem_write(OBJ+0xd200,struct.pack('<i',id)+bytes(12))
  self.invoke(0x410ca0,[OBJ+0xd000,OBJ+0xd100])

def pump(c):
 for _ in range(2):c.qualify();c.update(0)
 c.qualify()
def step(c,fps):c.qualify();c.update(1/fps)
def active(c,id):return [n for n in c.nodes() if n['id']==id and not n['flags']&0x800c0003]

class Score(Fire):
 def __init__(self,base=100):
  super().__init__();self.base=base;self.u.mem_map(OBJ+0x60000,0x10000)
  self.record=OBJ+0x60000;self.context=OBJ+0x61000;self.vtable=OBJ+0x62000
  self.u.mem_write(self.record+0x14,struct.pack('<i',1));self.q(self.record+0x80,self.vtable)
  self.q(self.vtable+0x20,STOP+0x900);self.q(self.vtable+0xa0,STOP+0x901)
  self.q(self.vtable+0x208,STOP+0x902);self.q(self.vtable+0xf0,BASE+0x2de580)
  self.q(OBJ+0xf038,OBJ+0x63000);self.q(OBJ+0x63008,OBJ+0x6000)
 def hook(self,u,address,size,user):
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  pc=address-BASE
  if pc in(0x2fe510,0x2ee910,0x2ee990,0x2fe7a0,0x2fe4b0,0x2fe7f0):
   value=self.base if pc==0x2fe510 else 0
   u.reg_write(UC_X86_REG_XMM0,int.from_bytes(struct.pack('<f',value),'little'));ret()
  elif address==STOP+0x900:ret(1)
  elif address==STOP+0x901:
   ptr=u.reg_read(UC_X86_REG_RDX);u.mem_write(ptr,bytes(16));ret(ptr)
  elif address==STOP+0x902:ret(OBJ+0x6000)
  elif pc==0x26909a0:ret(u.reg_read(UC_X86_REG_RAX))
  else:super().hook(u,address,size,user)
 def score(self):
  self.invoke(0x2efb50,[self.record,self.context]);return struct.unpack('<f',(self.u.reg_read(UC_X86_REG_XMM0)&0xffffffff).to_bytes(4,'little'))[0]

lua=ctypes.CDLL(ctypes.util.find_library('lua5.4'))
lua.luaL_newstate.restype=ctypes.c_void_p
lua.luaL_openlibs.argtypes=[ctypes.c_void_p]
lua.luaL_loadstring.argtypes=[ctypes.c_void_p,ctypes.c_char_p]
lua.lua_pcallk.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_ssize_t,ctypes.c_void_p]
lua.lua_tolstring.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.POINTER(ctypes.c_size_t)]
lua.lua_tolstring.restype=ctypes.c_char_p
lua.lua_close.argtypes=[ctypes.c_void_p]
def run_lua(program):
 state=lua.luaL_newstate()
 try:
  lua.luaL_openlibs(state);assert lua.luaL_loadstring(state,program.encode())==0
  status=lua.lua_pcallk(state,0,1,0,0,None);result=lua.lua_tolstring(state,-1,None)
  assert status==0,result
  return result.decode()
 finally:lua.lua_close(state)
checks={k:[] for k in ('script','graph','dispatch','qualification','timer','score')};stubs=set()
def record(key,c=None,**row):
 checks[key].append(row)
 if c:stubs.update(c.stubs)
def priority(c):
 c.invoke(0x505b40,[OBJ]);return struct.unpack('<f',(c.u.reg_read(UC_X86_REG_XMM0)&0xffffffff).to_bytes(4,'little'))[0]
prefix="""
TRUE=1;FALSE=0;HERO_TANK=2;GUARD_STYLE_HIGHGUARD=5;GUARD_STYLE_DEFAULT=0
HAND_LEFT=1;HAND_RIGHT=0;HAND_LEFT_BOTH=2;HAND_RIGHT_BOTH=3
ALLBODY=0;UPPER=1;LOWER=2;c_IsStealth=FALSE
ActionDuration='duration';ActionRequest='request';GetStamina='stamina';GetHeroID='hero';GetSpEffectID='effect'
GetEquipWeaponCategory='weapon';GetEquipWeaponSpecialCategoryNumber='special';GetGuardMotionCategory='guard';GetStayAnimCategory='stay'
ACTION_ARM_ACTION='action';ACTION_ARM_L1='guard'
WEAPON_CATEGORY_DUELING_SHIELD=10;WEAPON_CATEGORY_TORCH=11
local variables={};local requests={}
function GetVariable(name) assert(name=='AddFookShotBlend');return 0 end
function SetVariable(name,value) variables[name]=value end
function GetEquipType(...) return FALSE end
function IsDemonSwordMode() return FALSE end
function MoveStart(...) return FALSE end
function ExecEventHalfBlend(...) requests={...} end
"""
for hero,buff,button,stamina,enabled,style in itertools.product((0,2),(0,1),(0,1),(0,100),(0,1),(0,3)):
 program=prefix+f"c_Style={style};function IsEnableGuard() return {enabled} end\n"
 program+=f"""
function env(key,id)
 if key=='hero' then return {hero} elseif key=='effect' then assert(id==701530 or id==172);return id==701530 and {buff} or 0
 elseif key=='request' then assert(id=='guard');return {button} elseif key=='duration' then return 0
 elseif key=='stamina' then return {stamina} elseif key=='weapon' or key=='special' or key=='guard' or key=='stay' then return 0 end
 error('unexpected environment query '..tostring(key))
end
"""
 result=run_lua(program+guard_function+"\nlocal result=ExecGuard('GuardOn',0,FALSE);return tostring(result)..'|'..tostring(variables.IndexGuardStyle)..'|'..table.concat(requests,',')")
 ok=bool(button and stamina and enabled);selection=5 if hero==2 and buff else 0
 assert result==(f'1|{selection}|GuardOn,0,0' if ok else '0|nil|'),result
 record('script',hero=hero,ability=buff,button=button,stamina=stamina,enabled=enabled,style=style,result=result)
for selector in (44372,58040,96490):
 binding=graph.selector_binding(selector);assert binding['name']=='IndexGuardStyle' and binding['variable']==42
 for index in(0,5):
  branch=graph.children(selector)[index];clips=[graph.string(graph.reference(clip,'animationName')) for clip in graph.children(branch)]
  suffix=('023080' if index==5 else '023000') if selector==96490 else ('000160' if index==5 else '000100')
  styles=[0,15] if index==5 else [0,2,3,10,11,12,13,15]+([16] if selector==96490 else [])
  assert clips==[f'a{style:03}_'+suffix for style in styles],clips
  record('graph',selector=selector,binding=binding,index=index,branch=branch,clips=clips)
# Confirm the real virtual accessor slot; do not infer a getter from a nearby
# immediate or from another object with a coincidentally identical slot number.
for vtable in(0x2bf8ae8,0x2bf9180,0x2c040f8,0x2c04320):
 offset=x.pe.get_offset_from_rva(vtable+0xf0)
 assert struct.unpack_from('<Q',x.raw,offset)[0]==BASE+0x2de580
families=[dict(effects=[7030700],root=7030700,state=2010,marker=7030701,leaf=7030702,priority=450,duration=4),
          dict(effects=[7011300,7011301],root=7033300,state=2265,marker=7033301,leaf=7033302,priority=600,duration=2)]
for f in families:
 for id in f['effects']:assert x.x['tables']['AttachEffectParam'][str(id)]['passiveSpEffectId_1']==f['root']
 for id in(f['marker'],f['leaf']):assert x.spells[str(id)]['invocationConditionsStateChange1']==f['state']
 assert x.spells[str(f['root'])]['stateInfo']==f['state']
 leaf=x.spells[str(f['leaf'])];assert leaf['targetPriority']==f['priority'] and leaf['effectEndurance']==f['duration']
 assert struct.unpack_from('<f',x.rows[f['leaf']],0xf8)[0]==f['priority']
events=[dict(track=t['ID'],animation=an['ID'],**e) for t in tracks.values() for an in t['animations'] for e in an['events']
        if e['Type']==67 and struct.unpack_from('<i',bytes.fromhex(e['hex']))[0] in(7030701,7033301)]
assert len(events)==39
assert len({(e['track'],e['animation'],e['hex']) for e in events})==39
# Relocate each large TAE once. Preserve the native event context/payload for
# independent actor runs; repeating file relocation does not add coverage.
contexts={}
for track in tracks:
 decoder=Score();loader=NativeTae(decoder,raws[track],tracks[track]['sha256'])
 for animation in sorted({e['animation'] for e in events if e['track']==track}):
  ctx=OBJ+0xd100;decoder.u.mem_write(ctx,bytes(0x40))
  while decoder.invoke(0x27d0400,[loader.animations[animation],ctx]):
   if struct.unpack('<I',decoder.u.mem_read(ctx,4))[0]!=67:continue
   ptr=struct.unpack('<Q',decoder.u.mem_read(ctx+8,8))[0];payload=bytes(decoder.u.mem_read(ptr,16))
   if struct.unpack_from('<i',payload)[0] not in(7030701,7033301):continue
   key=(track,animation,payload.hex().upper());assert key not in contexts
   contexts[key]=bytes(decoder.u.mem_read(ctx,0x40))
 stubs.update(decoder.stubs)
assert len(contexts)==39
print('PASS native TAE decoding',flush=True)
for e,copies in itertools.product(events,(0,1,3)):
 marker=struct.unpack_from('<i',bytes.fromhex(e['hex']))[0];f=next(f for f in families if f['marker']==marker)
 c=Score()
 for _ in range(copies):c.grant(f['root'])
 pump(c);ctx=OBJ+0xd100
 c.u.mem_write(ctx,contexts[(e['track'],e['animation'],e['hex'].upper())])
 c.u.mem_write(OBJ+0xd200,bytes.fromhex(e['hex']));c.q(ctx+8,OBJ+0xd200)
 c.q(OBJ+0xd018,OBJ+0x6000);c.invoke(0x410ca0,[OBJ+0xd000,ctx])
 for _ in range(30):step(c,60)
 result=priority(c);assert result==(f['priority'] if copies else 0)
 assert c.score()==100+result
 record('dispatch',c,track=e['track'],animation=e['animation'],event=e['index'],marker=marker,copies=copies,priority=result,score=c.score())
print('PASS guard script/graph/TAE dispatch',flush=True)
for root,marker,activity in itertools.product((0,7030700,7033300),(7030701,7033301),(0,1)):
 c=Score()
 if root:c.grant(root)
 pump(c);c.event(marker,activity)
 for _ in range(30):step(c,60)
 f=next(f for f in families if f['marker']==marker);result=priority(c)
 assert result==(f['priority'] if root==f['root'] else 0)
 record('qualification',c,root=root,marker=marker,activityByte=activity,priority=result)
for f,fps,reapply in itertools.product(families,(30,60,120),(False,True)):
 c=Score();c.grant(f['root']);pump(c);c.event(f['marker']);start=None;last=None;refresh=None
 for frame in range(1,8*fps):
  step(c,fps);value=priority(c)
  if value and start is None:start=frame
  if reapply and frame==fps:c.event(f['marker'])
  if reapply and frame==int(1.5*fps):refresh=active(c,f['leaf']);assert len(refresh)==1 and refresh[0]['lifetime']>f['duration']-.6
  if start and not value:last=frame;break
 assert start and last
 assert abs((last-start)/fps-(f['duration']+int(reapply)))<=4/fps,(f,fps,reapply,start,last)
 record('timer',c,root=f['root'],fps=fps,reapply=reapply,startFrame=start,expiryFrame=last,refresh=refresh)
for base,order,copies in itertools.product((0,100,1234.5),((7030700,),(7033300,),(7030700,7033300),(7033300,7030700)),(1,3)):
 c=Score(base)
 for root in order:
  for _ in range(copies):c.grant(root)
 pump(c)
 for root in order:c.event(next(f['marker'] for f in families if f['root']==root))
 for _ in range(30):step(c,60)
 delta=sum(f['priority'] for f in families if f['root'] in order)
 assert priority(c)==delta and c.score()==base+delta
 record('score',c,baseline=base,order=order,copies=copies,priority=priority(c),score=c.score())
fields=('stateInfo','spCategory','effectEndurance','motionInterval','replaceSpEffectId','cycleOccurrenceSpEffectId','invocationConditionsStateChange1','targetPriority')
output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),
 assetHashes={**{str(id):sha(raw) for id,raw in raws.items()},'hks':sha(raw_script),'behaviorGraph':graph.metadata['hkxSha256']},
 families=families,events=events,rows={str(id):{k:x.spells[str(id)][k] for k in fields} for f in families for id in(f['root'],f['marker'],f['leaf'])},
 checks=checks,stubs=sorted(stubs|{'Lua input, stamina, weapon, ability and actor responses are fixtures; actual ExecGuard executes',
 'Type 67 always calls 40FF20 with apply=true; activity byte does not suppress grants',
 '2FE510 provides explicit unrelated baseline; 2EE910/2EE990/2FE7A0/2FE4B0/2FE7F0 return zero unrelated score terms',
 'target virtual +20 accepts, +A0 returns zero position, +208 supplies actor; actual +F0 getter executes',
 '26909A0 security-cookie stub preserves return value',
 'full animation scheduling, guard release cadence, damage interruptions, enemy target selection, multiplayer and game execution not simulated'}),
 native=dict(type67='27D0F10 / 27D0400 → 410CA0 → 40FF20',grant='3C7FD0',lifecycle='5057D0 / 50ACD0',
 priority='505B40',accessor='2DE580 → 4249F0 → 42C120 → 505B40',score='2EFB50 / 2EFCB0 / 7586307'),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(map(len,checks.values())),'guard aggro checks',{k:len(v) for k,v in checks.items()},flush=True)
