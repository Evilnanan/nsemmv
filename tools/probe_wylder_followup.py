"""Trace Wylder's greatsword follow-up selection and temporary hand enchantment.

Original HKS branches, reviewed behavior edges, native TAE dispatch, effect
updates, hand filtering and overwrite run with explicit actor/weapon fixtures.
Full action scheduling, collision and final attack damage are not simulated.
"""
import argparse,json,struct,itertools,math,ctypes,ctypes.util
from pathlib import Path
from native_effect_runtime import *
from native_ailment_runtime import Ailment
from native_animation_runtime import NativeTae
from native_attack_runtime import Type1Attack
from effect_behavior_graph import BehaviorGraph
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','assets','animations','script','behavior','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted)
raws={name:a.extracted.with_suffix('.'+name+'.param').read_bytes() for name in ('AtkParam_Pc','BehaviorParam_PC')}
attacks=Inputs.table(raws['AtkParam_Pc'],0x1d0);behaviors=Inputs.table(raws['BehaviorParam_PC'],0x30)
weaponraw=a.assets.with_suffix('.EquipParamWeapon.param').read_bytes();weapons=Inputs.table(weaponraw,0x298)
assert json.loads(a.assets.read_text())['hashes']['regulation.bin']==x.x['hashes']['regulation.bin']
animations=json.loads(a.animations.read_text());track=next(t for b in animations['bundles'] for t in b['taes'] if t['ID']==2900)
taeraw=Path(str(a.animations)+'.2900.tae').read_bytes();graph=BehaviorGraph(a.behavior)
raw_script=a.script.read_bytes();assert sha(raw_script)=='786f8a7bc89452d9531e2299b224c8945701c422437eca9aacbeb10a57a17f4d'
source=raw_script.decode('utf-8-sig').replace('\r\n','\n')
def function(name):
 start=source.index('function '+name+'(');return source[start:source.index('\nfunction ',start+1)]
root=7020000
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
  elif pc==0xe6d630:
   self.stubs.add('E6D630 actual attack row lookup for supplied context')
   id=u.reg_read(UC_X86_REG_R8)&0xffffffff;ptr=u.reg_read(UC_X86_REG_RCX);u.mem_write(OBJ+0x1b000,attacks[id]);u.mem_write(ptr,struct.pack('<iii4xQ',id,0,1,OBJ+0x1b000));ret(ptr)
  elif pc in (0x3ced90,0x4d1b20):
   self.stubs.add('3CED90/4D1B20 explicit animation-owner context');ret(OBJ+0xd800 if pc==0x3ced90 else 0)
  else:super().hook(u,address,size,user)
 def event(self,id,active=1):
  self.q(OBJ+0xd018,OBJ+0x6000);self.q(OBJ+0xd108,OBJ+0xd200)
  self.u.mem_write(OBJ+0xd100,struct.pack('<I',67));self.u.mem_write(OBJ+0xd118,bytes([active]))
  self.u.mem_write(OBJ+0xd200,struct.pack('<i',id)+bytes(12))
  self.invoke(0x410ca0,[OBJ+0xd000,OBJ+0xd100])
 def cast(self):
  self.event(7020001);self.event(7020003);pump(self)
 def points(self,kind=1):
  out=OBJ+0x8400;self.u.mem_write(out,bytes(0x300));self.u.mem_write(out+0x10,bytes([kind]));self.u.mem_write(out+8,struct.pack('<ii',10000,1))
  self.invoke(0x502830,[OBJ,out,-1,-1]);return [struct.unpack('<f',self.u.mem_read(out+off,4))[0] for off in(0x48,0x5c,0x60,0x64,0x68)]

def pump(c):
 for _ in range(2):c.qualify();c.update(0)
 c.qualify()
def step(c,fps):c.qualify();c.update(1/fps)
def active(c,id):return [n for n in c.nodes() if n['id']==id and not n['flags']&0x800c0003]

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
# Symbolic HKS enum tokens preserve equality and hand selection; they are not
# claimed as the game's numeric constants. Engine responses remain fixtures.
prefix="""
TRUE=1;FALSE=0;HAND_RIGHT='R';HAND_LEFT='L';HAND_BOTH='B';HAND_LEFT_BOTH=2
WEAPON_CATEGORY_LARGE_SWORD='greatsword';GetEquipWeaponCategory='weapon';GetSpEffectID='effect';IsAnimEnd='end';IsFookshotBreak='break';IsTruelyLanding='land';SET_SKILL_HAND_LEFT=0
local variables={};local requests={}
function GetVariable(name) return 0 end
function SetVariable(name,value) variables[name]=value end
function AttackCommonFunction(...) requests={...};return TRUE end
FookShotCommonFunction=AttackCommonFunction
function ExecEventAllBody(name) error('unexpected action '..name) end
"""
functions=['FookShotMove_onUpdate','FookShotMoveBreak_onUpdate','FookShotPull_onUpdate','AirFookShotMove_onUpdate','AirFookShotPull_onUpdate']
checks={k:[] for k in ('script','styleScript','attackDispatch','enchantDispatch','values','timer','overwrite','switchHand')};stubs=set()
def record(key,c,**row):checks[key].append(row);stubs.update(c.stubs)
for name,copies,window,weapon,left in itertools.product(functions,(0,1,3),(0,1),(0,1),(0,1)):
 program=prefix+f"c_Style={2 if left else 0}\n"
 program+=f"""
function env(key,id)
 if key=='effect' then if id==7020000 then return {int(bool(copies))} elseif id==700510 then return {window} else assert(id==700530);return 0 end end
 if key=='weapon' then assert(id=='{'L' if left else 'R'}');return '{'greatsword' if weapon else 'other'}' end
 return 0
end
"""
 program+=function('GetEquipType')+'\n'+function(name)+f"\n{name}(); return tostring(variables['FookShotAdditionalAttack'])..'|'..table.concat(requests,'|',1,6)"
 result=run_lua(program);parts=result.split('|');selected=bool(copies and window and weapon)
 assert (parts[1]=='W_FookShotAdditionalAttack')==selected and (parts[5]=='W_FookShotAdditionalAttack')==selected
 assert parts[0]==(str(int('Pull' in name)) if selected else 'nil')
 assert parts[3:5]==['W_AttackLeftLight1','W_AttackLeftHeavy1']
 checks['script'].append(dict(function=name,copies=copies,window=window,greatsword=weapon,leftBoth=left,selector=parts[0],requests=parts[1:]))
for style,existing in itertools.product((0,2,3),(0,1)):
 program=prefix+f"c_Style={style}\nAddSpEffect='add'\n"
 program+=f"function env(key,id) assert(key=='effect');return {existing} end\nfunction act(key,id) assert(key=='add');table.insert(requests,id) end\n"
 result=run_lua(program+function('SetStyleSpecialEffect')+'\nSetStyleSpecialEffect();return table.concat(requests,",")')
 assert result==('' if existing else '100621' if style==2 else '100620')
 checks['styleScript'].append(dict(style=style,alreadyPresent=existing,grant=result))

assert x.x['tables']['AttachEffectParam'][str(root)]['passiveSpEffectId_1']==root
assert x.spells[str(root)]['stateInfo']==2027
for style,marker,leaf,state in ((100620,7020001,7020002,323),(100621,7020003,7020004,322)):
 assert x.spells[str(style)]['stateInfo']==state and x.spells[str(style)]['spCategory']==158
 r=x.spells[str(marker)];f=x.spells[str(leaf)]
 assert r['invocationConditionsStateChange1']==state and r['cycleOccurrenceSpEffectId']==leaf and r['effectEndurance']==0
 assert f['effectEndurance']==20 and f['fireAttackPower']==20 and f['isUseAtkParamAtkPowerCorrect']==1
 assert f['wepParamChange']==(1 if style==100620 else 2) and f['spCategory']==(162 if style==100620 else 163)
selector=graph.reference(32481,'generator');assert selector==41896
binding=graph.selector_binding(selector);assert binding['name']=='FookShotAdditionalAttack'
clips=[]
for branch in graph.children(selector):
 children=graph.children(branch);assert len(children)==1
 clips.append(graph.string(graph.reference(children[0],'animationName')))
assert clips==['a900_500020','a900_500021']
selected=[an for an in track['animations'] if an['ID'] in(500020,500021)]
attack_events=[dict(animation=an['ID'],**e) for an in selected for e in an['events'] if e['Type']==1]
enchant_events=[dict(animation=an['ID'],**e) for an in selected for e in an['events'] if e['Type']==67]
assert [(e['animation'],e['index']) for e in attack_events]==[(500020,5),(500020,7),(500021,9)]
assert [(e['animation'],e['index']) for e in enchant_events]==[(500020,104),(500020,105),(500021,80),(500021,81)]
for e,enabled in itertools.product(attack_events,(0,1)):
 c=Type1Attack(x,behaviors,weapons,{600000010,600000016});c.event(e,enabled)
 expected=600000000+struct.unpack_from('<i',bytes.fromhex(e['hex']),8)[0]-6000
 assert len(c.requests)==1 and c.requests[0]['behavior']==expected and not c.missing
 record('attackDispatch',c,animation=e['animation'],event=e['index'],enabled=enabled,requests=c.requests)
for animation,style,enabled in itertools.product((500020,500021),(0,100620,100621),(0,1)):
 c=Fire(2 if style==100621 else 0)
 if style:c.grant(style)
 pump(c);loader=NativeTae(c,taeraw,track['sha256']);ctx=OBJ+0xd100;c.u.mem_write(ctx,bytes(0x40));seen=[]
 while c.invoke(0x27d0400,[loader.animations[animation],ctx]):
  if struct.unpack('<I',c.u.mem_read(ctx,4))[0]!=67:continue
  ptr=struct.unpack('<Q',c.u.mem_read(ctx+8,8))[0];id=struct.unpack('<i',c.u.mem_read(ptr,4))[0]
  assert id in(7020001,7020003);seen.append(id)
  c.q(OBJ+0xd018,OBJ+0x6000);c.u.mem_write(ctx+0x18,bytes([enabled]));c.invoke(0x410ca0,[OBJ+0xd000,ctx])
 pump(c);assert seen==[7020001,7020003]
 leaves=[n for n in c.nodes() if n['id'] in(7020002,7020004)]
 expected=7020002 if style==100620 else 7020004
 assert len(leaves)==bool(style),(animation,style,enabled,c.nodes(),c.grants)
 if leaves:assert leaves[0]['id']==expected and leaves[0]['lifetime']==20
 record('enchantDispatch',c,animation=animation,style=style,activityByte=enabled,leaves=leaves)
for style,copies in itertools.product((100620,100621),(1,3)):
 c=Fire(2 if style==100621 else 0);c.grant(style)
 for _ in range(copies):c.grant(root)
 pump(c)
 for _ in range(copies):c.cast()
 for kind in range(13):
  points=c.points(kind);expected=20 if kind in((1,11,12) if style==100620 else(2,11,12)) else 0
  assert points==[0,0,expected,0,0],(style,copies,kind,points)
  record('values',c,style=style,copies=copies,kind=kind,points=points)
for style,fps,reapply in itertools.product((100620,100621),(30,60,120),(False,True)):
 c=Fire(2 if style==100621 else 0);c.grant(style);pump(c);c.cast();leaf=7020002 if style==100620 else 7020004
 reset=None
 for frame in range(1,27*fps):
  step(c,fps)
  if reapply and frame==5*fps:
   c.cast();reset=active(c,leaf)[0]['lifetime'];assert reset==20
  if not active(c,leaf):break
 assert abs(frame/fps-(25 if reapply else 20))<=4/fps,(style,fps,reapply,frame)
 record('timer',c,style=style,fps=fps,reapply=reapply,remainingAfterReapply=reset,expiryFrame=frame)
for leaf,other in ((7020002,881),(7020002,1627),(7020004,883),(7020004,1629)):
 for order in ((leaf,other),(other,leaf)):
  c=Fire(2 if leaf==7020004 else 0)
  for id in order:c.grant(id);pump(c)
  assert [n['id'] for n in c.nodes()]==[order[-1]]
  record('overwrite',c,order=order,nodes=c.nodes())
for order in ((100620,100621),(100621,100620)):
 c=Fire()
 for style in order:c.hand=2 if style==100621 else 0;c.grant(style);pump(c);c.cast()
 assert {n['id'] for n in c.nodes()}=={order[-1],7020002,7020004}
 assert c.points(1)==c.points(2)==[0,0,20,0,0]
 record('switchHand',c,styleOrder=order,nodes=c.nodes(),right=c.points(1),left=c.points(2))
fields=('stateInfo','spCategory','wepParamChange','effectEndurance','fireAttackPower','isUseAtkParamAtkPowerCorrect','invocationConditionsStateChange1','cycleOccurrenceSpEffectId')
output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),
 assetHashes={**{k:sha(v) for k,v in raws.items()},'weapon':sha(weaponraw),'tae':sha(taeraw),'hks':sha(raw_script),'behaviorGraph':graph.metadata['hkxSha256']},
 effects=[root],root=root,leaves=[7020002,7020004],graph=dict(state=32481,selector=selector,binding=binding,clips=clips),attackEvents=attack_events,enchantEvents=enchant_events,
 rows={str(id):{k:x.spells[str(id)][k] for k in fields} for id in(root,100620,100621,7020001,7020002,7020003,7020004)},checks=checks,
 stubs=sorted(stubs|{'Lua engine responses for window, equipment category, root presence and active hand; original functions execute',
 'Type 1 attack and Type 67 grant handlers use supplied selected events; HKS performs eligibility, not these unconditional events',
 'Type 67 always calls 40FF20 with apply=true; activity byte is not a grant-once gate, full scheduler not simulated',
 'animation time inputs and attack context 10000 supplied; no complete behavior VM, physical collision, weapon switch or final attack damage'}),
 native=dict(type1='414820 → 40CA20 → 668B30',type67='27D0F10 / 27D0400 → 410CA0',grant='3C7FD0 / 3C8BE0',
 qualifier='5057D0',update='50ACD0',attack='502830 → 511010'),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(map(len,checks.values())),'Wylder follow-up checks',{k:len(v) for k,v in checks.items()},flush=True)
