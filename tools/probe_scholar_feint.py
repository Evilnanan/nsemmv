"""Execute Scholar feint event gates and weapon-specific parry dispatch.

Pinned Lua branches and native TAE/Behavior resolution run with explicit actor,
equipped-weapon and input fixtures. No full behavior VM or collision is run.
"""
import argparse,ctypes,ctypes.util,json,struct,itertools,math
from pathlib import Path
from native_effect_runtime import *
from native_attack_runtime import Type1Attack
from native_animation_runtime import NativeTae
from effect_behavior_graph import BehaviorGraph
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','assets','animations','behavior','script','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted)
behaviorraw=a.extracted.with_suffix('.BehaviorParam_PC.param').read_bytes()
weaponraw=a.assets.with_suffix('.EquipParamWeapon.param').read_bytes()
b=Inputs.table(behaviorraw,0x30);w=Inputs.table(weaponraw,0x298)
t=json.loads(a.animations.read_text());assets=json.loads(a.assets.read_text())
assert assets['hashes']['regulation.bin']==x.x['hashes']['regulation.bin']
assert t['bundles'][0]['sha256']=='1410035ad79edb410fa41420ec259fcb4a1037d748c9c4a3b6ae8d1366c76d0f'
root=7036710
assert x.spells[str(root)]['stateInfo']==2033 and x.spells[str(root)]['spCategory']==20
assert x.x['tables']['AttachEffectParam'][str(root)]['passiveSpEffectId_1']==root
assert x.x['tables']['AttachEffectParam'][str(root)]['exclusivityId']==-1
events=[dict(tae=ta['ID'],animation=an['ID'],**e) for bu in t['bundles'] for ta in bu['taes'] for an in ta['animations'] for e in an['events'] if e['Type'] in (0,1) and len(bytes.fromhex(e['hex']))>=16 and struct.unpack_from('<H',bytes.fromhex(e['hex']),14)[0]==2033]
class Feint(Type1Attack):
 def __init__(self,weapon):
  super().__init__(x,b,w,set(b)|{100550591,100503591,100602591})
  self.weapon=weapon;self.lookups=[]
  self.q(OBJ+0x6800,STOP+0x203) # actor vtable +600
  self.q(OBJ+0x9008,OBJ+0xf000);self.q(OBJ+0x6060,OBJ+0xf400);self.q(OBJ+0xf4c8,OBJ+0xf800)
 def hook(self,u,address,size,user):
  if address in (STOP+0x202,STOP+0x203):
   self.stubs.add("explicit equipped weapon and actor virtual +600 null context")
   u.reg_write(UC_X86_REG_RAX,self.weapon if address==STOP+0x202 else 0)
   sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  else:
   if address-BASE==0xe6fcb0:self.lookups.append(u.reg_read(UC_X86_REG_RDX)&0xffffffff)
   super().hook(u,address,size,user)
 def jump(self,e,active):
  self.q(OBJ+0xd018,OBJ+0x6000);self.q(OBJ+0xd108,OBJ+0xd200)
  self.u.mem_write(OBJ+0xd100,struct.pack('<I',0));self.u.mem_write(OBJ+0xd118,bytes([active]))
  self.u.mem_write(OBJ+0xd200,bytes.fromhex(e['hex']))
  self.u.mem_write(OBJ+0xf058,bytes(8));self.invoke(0x410ca0,[OBJ+0xd000,OBJ+0xd100])
  return struct.unpack('<Q',self.u.mem_read(OBJ+0xf058,8))[0]
 def event(self,e,active):
  # Supply the native time pair (start at +0, end at +8) and dispatch at
  # the start time. The request's internal time offset is not a duration.
  self.q(OBJ+0xd018,OBJ+0x6000);self.q(OBJ+0xd108,OBJ+0xd200);self.q(OBJ+0xd120,OBJ+0xd300)
  self.u.mem_write(OBJ+0xd100,struct.pack('<I',1));self.u.mem_write(OBJ+0xd118,bytes([active]))
  self.u.mem_write(OBJ+0xd110,struct.pack('<f',e['StartTime']))
  self.u.mem_write(OBJ+0xd300,struct.pack('<f4xf',e['StartTime'],e['EndTime']))
  self.u.mem_write(OBJ+0xd200,bytes.fromhex(e['hex'])+bytes(16))
  self.invoke(0x414820,[OBJ+0xd000,OBJ+0xd100])

assert len(events)==81
for e in events:
 assert math.isclose(e['StartTime'],4/30,abs_tol=1e-7)
 assert math.isclose(e['EndTime'],9/30 if e['Type']==0 and bytes.fromhex(e['hex'])[0]==18 else 8/30,abs_tol=1e-7)
checks=dict(rawEvents=[],dispatch=[],script=[]);stubs=set();rawhashes={}
# Relocate each actual TAE, iterate every selected animation and verify the
# event payload and time pointers against the extracted snapshot.
for tid in sorted({e['tae'] for e in events}):
 ta=next(ta for bu in t['bundles'] for ta in bu['taes'] if ta['ID']==tid)
 raw=Path(str(a.animations)+'.'+str(tid)+'.tae').read_bytes();rawhashes[str(tid)]=sha(raw)
 c=Feint(5000000);loader=NativeTae(c,raw,ta['sha256']);assert loader.id==tid and loader.bank==255
 for anim in sorted({e['animation'] for e in events if e['tae']==tid}):
  ctx=OBJ+0xd100;c.u.mem_write(ctx,bytes(0x40));found=[]
  while c.invoke(0x27d0400,[loader.animations[anim],ctx]):
   typ=struct.unpack('<I',c.u.mem_read(ctx,4))[0]
   if typ not in (0,1):continue
   ptr=struct.unpack('<Q',c.u.mem_read(ctx+8,8))[0];payload=bytes(c.u.mem_read(ptr,16))
   if struct.unpack_from('<H',payload,14)[0]!=2033:continue
   original=next(e for e in events if e['tae']==tid and e['animation']==anim and e['Type']==typ and bytes.fromhex(e['hex'])[:16]==payload)
   if typ==1:assert c.u.mem_read(ptr+16,1)[0]==0
   times=struct.unpack('<Q',c.u.mem_read(ctx+0x20,8))[0]
   begin,end=struct.unpack('<f4xf',c.u.mem_read(times,12))
   assert math.isclose(begin,original['StartTime'],abs_tol=1e-7) and math.isclose(end,original['EndTime'],abs_tol=1e-7),(begin,end,original)
   found.append(dict(type=typ,payload=payload.hex(),start=begin,end=end))
  assert len(found)==3;checks['rawEvents'].append(dict(tae=tid,animation=anim,events=found))
 stubs.update(c.stubs)

for weapon,copies,active in itertools.product((5000000,6000000),(0,1,3),(0,1)):
 c=Feint(weapon)
 for _ in range(copies):c.insert(root)
 c.qualify();c.update(0)
 assert len(c.nodes())==bool(copies)
 for e in events:
  raw=bytes.fromhex(e['hex']);request=None;flags=0
  if e['Type']==1:
   assert struct.unpack_from('<3i',raw)==(64,0,591)
   c.requests.clear();c.lookups.clear();c.event(e,active)
   assert len(c.requests)==bool(copies)
   if copies:
    request=c.requests[0];assert request['behavior']==(100500591 if weapon==5000000 else 100600591)
    assert request['kind']==64 and request.pop('elapsed')==0
    request['timeOffset']=0
    behavior=x.x['tables']['BehaviorParam_PC'][str(request['behavior'])]
    assert behavior['refType']==0 and behavior['refId']==request['behavior']-100000000
  else:
   jump=struct.unpack_from('<i',raw)[0];assert jump in (18,119)
   flags=c.jump(e,active);assert flags==((0x40 if jump==18 else 0x4000000000) if copies else 0)
  checks['dispatch'].append(dict(tae=e['tae'],animation=e['animation'],type=e['Type'],code=struct.unpack_from('<i',raw)[0],weapon=weapon,copies=copies,active=active,request=request,flags=flags))
 stubs.update(c.stubs)

graph=BehaviorGraph(a.behavior);paths=[]
for state,expected in ((30076,['a279_035100','a281_035100']),(30085,['a039_035950'])):
 gen=graph.reference(state,'generator');clips=[graph.string(graph.reference(ch,'animationName')) for ch in graph.children(gen)]
 assert sorted(clips)==sorted(expected)
 for clip in clips:
  bank,anim=clip.split('_');tid=2000+int(bank[1:]);anim=int(anim)
  assert len([e for e in events if e['tae']==tid and e['animation']==anim])==3
 paths.append(dict(state=state,name=graph.name(state),generator=gen,clips=clips))

script=a.script.read_bytes();assert sha(script)=='786f8a7bc89452d9531e2299b224c8945701c422437eca9aacbeb10a57a17f4d'
source=script.decode('utf-8-sig').replace('\r\n','\n');functions=[]
for name in ('GetEquipType','IsEnableBackStepCancel','AttackLeftHeavy1_onUpdate'):
 start=source.index('function '+name+'(');functions.append(source[start:source.index('\nfunction ',start+1)])
lua=ctypes.CDLL(ctypes.util.find_library('lua5.4'));lua.luaL_newstate.restype=ctypes.c_void_p
lua.luaL_openlibs.argtypes=[ctypes.c_void_p];lua.luaL_loadstring.argtypes=[ctypes.c_void_p,ctypes.c_char_p]
lua.lua_pcallk.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_ssize_t,ctypes.c_void_p]
lua.lua_tolstring.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.POINTER(ctypes.c_size_t)];lua.lua_tolstring.restype=ctypes.c_char_p
lua.lua_close.argtypes=[ctypes.c_void_p]
for hero,category,pressed,window,style in itertools.product((0,9),(3,7,15,16),(0,1),(0,1),(0,3)):
 program='''
TRUE=1;FALSE=0;HAND_RIGHT=0;HAND_LEFT=1;HAND_BOTH=2;HAND_LEFT_BOTH=3
HERO_BUFFER=9;WEAPON_CATEGORY_RAPIER=15;WEAPON_CATEGORY_LARGE_RAPIER=16
GetHeroID=1;GetEquipWeaponCategory=2;ActionDuration=3;GetSpEffectID=4;ACTION_ARM_SP_MOVE=5
local hero,category,pressed,window=%d,%d,%d,%d;c_Style=%d;local event=''
function env(key,id)
 if key==GetHeroID then return hero end
 if key==GetEquipWeaponCategory then assert(id==HAND_LEFT);return category end
 if key==ActionDuration then assert(id==ACTION_ARM_SP_MOVE);return pressed end
 if key==GetSpEffectID then assert(id==708200);return window end
 error('unexpected env')
end
function ExecEventAllBody(name) event=name end
function ExecTravelMagnification(...) end
function AttackCommonFunction(...) return FALSE end
'''%(hero,category,pressed,window,style)
 program+='\n'.join(functions)+'\nAttackLeftHeavy1_onUpdate();return event'
 state=lua.luaL_newstate()
 try:
  lua.luaL_openlibs(state);assert lua.luaL_loadstring(state,program.encode())==0
  status=lua.lua_pcallk(state,0,1,0,0,None);out=lua.lua_tolstring(state,-1,None);assert status==0,out
  result=out.decode()
 finally:lua.lua_close(state)
 expected=('W_MirrorAttackRightSpecial1' if category==16 else 'W_AttackLeftBackStepCancel') if hero==9 and category in (15,16) and pressed and window else ''
 assert result==expected
 checks['script'].append(dict(hero=hero,category=category,pressed=pressed,window=window,style=style,event=result))

stubs.discard('synthetic animation-owner virtuals and equipped weapon 1000')
stubs.add('synthetic animation-owner virtuals; actual equipped weapon 5000000 or 6000000 supplied by this probe')
output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),
 behaviorParamSha256=sha(behaviorraw),weaponParamSha256=sha(weaponraw),animationBundleSha256=t['bundles'][0]['sha256'],
 taeSha256=rawhashes,scriptSha256=sha(script),behaviorBundleSha256=graph.metadata['bundleSha256'],root=root,
 events=events,paths=paths,checks=checks,
 native=dict(relocate='27D0F10',iterate='27D0400',type0='410CA0 → 40D390',type1='414820 → 40CA20',state='508E20',behavior='668B30',attackRequest='4341D0',parryFlag='40D608',cancelFlag='40D887'),
 stubs=sorted(stubs|{'Lua 5.4 source branch execution with explicit actor/category/input fixtures; not the game HKS VM',
 'TAE activity/time is explicit; full animation scheduling, hit construction, collision, stamina charging and network are not simulated',
 'left-hand HKS branch and graph edges verified; right/two-hand nil hand argument behavior is unresolved'}),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS', {k:len(v) for k,v in checks.items()}, 'Scholar feint checks')
