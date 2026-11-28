"""Couple thunder/holy cocktail TAE events to real HKS and native effect timers.

The selected animation timeline and Lua AddSpEffect transfer are explicit
fixtures. Havok execution, complete collision and gameplay are not simulated.
"""
import argparse,itertools,json,math,struct,ctypes,ctypes.util,re
from pathlib import Path
from native_effect_runtime import BASE,OBJ,STOP,Chain,Inputs,sha
from native_ailment_runtime import Ailment
from native_animation_runtime import NativeTae
from native_attack_runtime import Type1Attack
from effect_behavior_graph import BehaviorGraph
from unicorn.x86_const import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','animations','behavior','assets','script','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted);ts=x.x['tables']
assert sha(x.param)=='07ec636c5565d4551efeb53e6f08bc633b2aa4f2129f13c61b0638d69b1bc176'
hashes={'Magic':'17742eeafe4fade863f3a7ee5f7ff483bd4897f765802fe4a1954dfa8107b63e','BehaviorParam_PC':'f8fa3fd27cb98d45a3e24c69d71d8751df9202e6e379dc34fd77d4ef2e1240bb'}
raws={k:a.extracted.with_suffix('.'+k+'.param').read_bytes()for k in hashes}
for k,v in raws.items():assert sha(v)==hashes[k]
wepraw=a.assets.with_suffix('.EquipParamWeapon.param').read_bytes();assert sha(wepraw)=='28adf74850c88ca0b4bb01f355c4f1f8e1b662a56d77894ae74d591b72c1a0ea'
behaviors=Inputs.table(raws['BehaviorParam_PC'],0x20);weapons=Inputs.table(wepraw,0x2a8)
core_path=Path(__file__).resolve().parent.parent/'data/effect-mixed-magic-evidence.json';core=json.loads(core_path.read_text());assert core['effects']==[7034200,7034201]and core['root']==9200006
assert ts['Magic']['8015']['refType']==134 and ts['Magic']['8015']['refId3']==1801500
for id,duration,period,cycle,condition in [(1801501,0,0,-1,0),(1801500,15,0,-1,0),(7034207,10,.5,1801500,2047)]:
 r=x.spells[str(id)];assert(r['effectEndurance'],r['motionInterval'],r['cycleOccurrenceSpEffectId'],r['invocationConditionsStateChange1'],r['spCategory'])==(duration,period,cycle,condition,20)
for id in(1801500,7034207):assert x.spells[str(id)]['isExtendSpEffectLife']==x.spells[str(id)]['isContractSpEffectLife']==1
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

class Event(Actor):
 def __init__(self):super().__init__();self.shots=[];self.frame=0
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if pc in(0x3ced90,0x4d1b20):ret(OBJ+0xd800 if pc==0x3ced90 else 0)
  elif pc==0x3975d0:self.shots.append(dict(frame=self.frame,behavior=u.reg_read(UC_X86_REG_RDX)));ret(1)
  else:super().hook(u,address,size,user)
 def event(self,payload):
  self.q(OBJ+0xd018,OBJ+0x6000);self.q(OBJ+0xd108,OBJ+0xd200)
  self.u.mem_write(OBJ+0xd100,struct.pack('<I',67));self.u.mem_write(OBJ+0xd118,b'\1');self.u.mem_write(OBJ+0xd200,payload)
  self.invoke(0x410ca0,[OBJ+0xd000,OBJ+0xd100])
 def defense(self):
  self.u.mem_write(OBJ+0x800,bytes(0x200));self.invoke(0x503800,[OBJ,OBJ+0x500,OBJ+0x520,OBJ+0x540,OBJ+0x800]);return list(struct.unpack('<5f',self.u.mem_read(OBJ+0x500,20)))
lua_library=ctypes.util.find_library('lua5.4');assert lua_library,'liblua5.4 is required for isolated script checks'
lib=ctypes.CDLL(lua_library)
lib.luaL_newstate.restype=ctypes.c_void_p;lib.luaL_openlibs.argtypes=[ctypes.c_void_p];lib.lua_close.argtypes=[ctypes.c_void_p]
lib.luaL_loadbufferx.argtypes=[ctypes.c_void_p,ctypes.c_char_p,ctypes.c_size_t,ctypes.c_char_p,ctypes.c_char_p];lib.luaL_loadbufferx.restype=ctypes.c_int
lib.lua_pcallk.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_ssize_t,ctypes.c_void_p];lib.lua_pcallk.restype=ctypes.c_int
lib.lua_tolstring.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.POINTER(ctypes.c_size_t)];lib.lua_tolstring.restype=ctypes.c_char_p

lib.lua_settop.argtypes=[ctypes.c_void_p,ctypes.c_int]
script=a.script.read_bytes();assert sha(script)=='96339bb15f57559cd42a940d616fcc2a18a10f50845cfc22b46b356ab66c3b29'
text=script.decode('utf-8-sig').replace('\r\n','\n');function=next(m[0]for m in re.finditer(r'^function (\w+)\([^\n]*\).*?(?=^function |\Z)',text,re.M|re.S)if m[1]=='MagicFireRight_Upper_onUpdate')
start=text.index('    if env(GetHeroID) == HERO_MAGIC and GetVariable("AddAutoParryBlend") == 1 and env(GetSpEffectID, 1801500) == FALSE then');end=text.index('\n    end',start)+len('\n    end');cleanup=text[start:end]
class Script:
 def __init__(self):
  self.L=lib.luaL_newstate();lib.luaL_openlibs(self.L)
  self.run('''TRUE=1;FALSE=0;calls={};blend=0;marker=0;buff=0;rightMagic=1;rightHero=1
setmetatable(_G,{__index=function(_,key)return key end})
function act(key,id) calls[#calls+1]=key..":"..id end
function SetVariable(key,v) assert(key=="AddAutoParryBlend");blend=v end
function GetVariable(key) return blend end
function GetHalfBlendInfo() return 0,0 end
function MagicCommonFunction(...) return TRUE end
function env(key,id)
 if key==GetMagicAnimType then return rightMagic==1 and MAGIC_REQUEST_CREATEMAGIC_THUNDER_HOLY or 0 end
 if key==GetHeroID then return rightHero==1 and HERO_MAGIC or 0 end
 if key==GetSpEffectID and id==1801501 then return marker end
 if key==GetSpEffectID and id==1801500 then return buff end
 return 0 end
'''+function+'\nfunction cleanup()\n'+cleanup+'\nend\nreturn "ready"')
 def run(self,s):
  lib.lua_settop(self.L,0);code=s.encode();rc=lib.luaL_loadbufferx(self.L,code,len(code),b'coupled-parry',None)
  if not rc:rc=lib.lua_pcallk(self.L,0,1,0,0,None)
  out=lib.lua_tolstring(self.L,-1,None).decode();assert rc==0,out;return out
 def tick(self,c):
  marker=c.invoke(0x509150,[OBJ,1801501]);cmds=self.run(f'marker={marker};calls={{}};MagicFireRight_Upper_onUpdate();return table.concat(calls,";")')
  if cmds:assert cmds=='AddSpEffect:1801500';c.grant(1801500)
  buff=c.invoke(0x509150,[OBJ,1801500]);blend=int(self.run(f'buff={buff};cleanup();return tostring(blend)'));return marker,blend,bool(cmds)
 def close(self):lib.lua_close(self.L)
anims=json.loads(a.animations.read_text());t=next(t for b in anims['bundles']for t in b['taes']if t['ID']==2534);meta=next(a for a in t['animations']if a['ID']==45010)
events=[e for e in meta['events']if e['Type']in(66,67)and struct.unpack_from('<i',bytes.fromhex(e['hex']))[0]in(1801501,7034207)];assert len(events)==2
# Confirm both exact event payloads through actual native iteration too.
c=Event();loader=NativeTae(c,Path(str(a.animations)+'.2534.tae').read_bytes(),t['sha256']);ctx=OBJ+0xd100;c.u.mem_write(ctx,bytes(0x40));native=[]
while c.invoke(0x27d0400,[loader.animations[45010],ctx]):
 typ=struct.unpack('<I',c.u.mem_read(ctx,4))[0]
 if typ not in(66,67):continue
 ptr=struct.unpack('<Q',c.u.mem_read(ctx+8,8))[0];payload=bytes(c.u.mem_read(ptr,16))
 if struct.unpack_from('<i',payload)[0]in(1801501,7034207):native.append((typ,payload.hex().lower()))
assert sorted(native)==sorted((e['Type'],e['hex'].lower())for e in events)
timing=[];stubs=set()
cases=[(copies,fps,order,[],None)for copies,fps,order in itertools.product((0,1,3),(30,60,120),('before','after'))]
cases += [(1,60,'before',ext,None)for ext in([7006400],[7006400]*3,[8330500],[8330500]*3,[7006400,8330500])]
cases += [(copies,60,'before',[],recast)for copies,recast in itertools.product((0,1,3),(5,11))]
for copies,fps,order,extensions,recast in cases:
 c=Event();lua=Script()
 for root in [9200006]*copies+extensions:c.grant(root)
 for _ in range(fps):c.qualify();c.update(1/fps)
 scale=1+(.5 if 7006400 in extensions else 0)+extensions.count(8330500);first={};last={};firstBlend=None;lastBlend=None;scriptGrants=[];samples=[]
 total=math.ceil(27*scale+(recast or 0));starts=[0]+([recast]if recast is not None else [])
 for frame in range(total*fps):
  time=frame/fps
  for cast in starts:
   for e in events:
    if e['StartTime']-1e-7<=time-cast<e['EndTime']-1e-7:
     c.q(OBJ+0xd018,OBJ+0x6000);c.q(OBJ+0xd108,OBJ+0xd200);c.u.mem_write(OBJ+0xd100,struct.pack('<I',e['Type']));c.u.mem_write(OBJ+0xd118,b'\1');c.u.mem_write(OBJ+0xd200,bytes.fromhex(e['hex']));c.invoke(0x410ca0,[OBJ+0xd000,OBJ+0xd100])
  if order=='after':c.qualify();c.update(1/fps)
  marker,blend,granted=lua.tick(c)
  if granted:scriptGrants.append(frame)
  if blend:
   if firstBlend is None:firstBlend=frame
   lastBlend=frame
  if order=='before':c.qualify();c.update(1/fps)
  for n in c.nodes():
   if n['id']in(1801500,1801501,7034207)and not n['flags']&0x800c0003:first.setdefault(n['id'],frame);last[n['id']]=frame
  if frame%fps==0 and(frame//fps in(0,1,5,10,11,15,20,25,30,35,50,100)):samples.append(dict(frame=frame,blend=blend,nodes=[n for n in c.nodes()if n['id']in(1801500,1801501,7034207)]))
 assert firstBlend is not None and lastBlend<total*fps-1
 expected=15*scale if not copies else 25*scale
 if recast is not None:expected=15+recast if not copies else 25 if recast<10 else recast+25
 elapsed=(lastBlend-firstBlend)/fps
 assert abs(elapsed-expected)<.7,(copies,fps,order,extensions,recast,elapsed,expected)
 timing.append(dict(copies=copies,fps=fps,order=order,extensions=extensions,recast=recast,first=first,last=last,firstBlend=firstBlend,lastBlend=lastBlend,elapsed=elapsed,scriptGrants=scriptGrants,samples=samples));stubs.update(c.stubs);lua.close();print('PASS',copies,fps,order,extensions,recast,elapsed,flush=True)


g=BehaviorGraph(a.behavior);bindings=[]
for name in('MagicFireRight_CMSG','MagicFireRight_CMSG_Upper'):
 selector=g.named(name,'CustomManualSelectorGenerator');clips=[i for i in g.children(selector)if g.item(i)[0]['Identity']=='hkbClipGenerator'and g.string(g.reference(i,'animationName'))=='a534_045010'];assert len(clips)==1
 bindings.append(dict(selector=name,item=selector,clip=clips[0],animation='a534_045010'))
root=g.named('AutoParryBlend','hkbBlenderGenerator');children=g.blender_children(root);assert len(children)==2
for child,suffix in zip(children,('049980','049981')):
 clips=g.children(child['generator']);assert len(clips)==1 and g.string(g.reference(clips[0],'animationName'))=='a534_'+suffix
 bindings.append(dict(generator=root,child=child['child'],clip=clips[0],animation='a534_'+suffix))
# Pinned reference verifies the actual parent weight reads AddAutoParryBlend.
assert g.reference(16935,'generator')==root
binding=g.reference(g.reference(16935,'variableBindingSet'),'bindings');bt,bo,bn=g.item(binding);assert bt['Identity']=='hkbVariableBindingSet::Binding'and bn==1
assert g.string(struct.unpack_from('<Q',g.data,bo)[0])=='weight'and struct.unpack_from('<i',g.data,bo+28)[0]==436
string_set=next(i for i,(typ,_,n)in enumerate(g.items)if typ and n==1 and g.types[typ&0xffffff]['Identity']=='hkbBehaviorGraphStringData');_,no,nn=g.item(g.reference(string_set,'variableNames'));assert nn>436 and g.string(struct.unpack_from('<Q',g.data,no+436*8)[0])=='AddAutoParryBlend'
scriptChecks=[]
for right,marker in itertools.product((0,1),repeat=2):
 l=Script();out=l.run(f'rightMagic={right};marker={marker};calls={{}};MagicFireRight_Upper_onUpdate();return table.concat(calls,";")');assert out==('AddSpEffect:1801500'if right and marker else'');scriptChecks.append(dict(case='grant',rightMagic=right,marker=marker,output=out));l.close()
for hero,blend,buff in itertools.product((0,1),repeat=3):
 l=Script();out=int(l.run(f'rightHero={hero};blend={blend};buff={buff};cleanup();return tostring(blend)'));assert out==(0 if hero and blend and not buff else blend);scriptChecks.append(dict(case='cleanup',hero=hero,blend=blend,buff=buff,output=out));l.close()
d=Type1Attack(x,behaviors,weapons,{600000310});loader=NativeTae(d,Path(str(a.animations)+'.2534.tae').read_bytes(),t['sha256']);ctx=loader.select(49980,1);d.q(OBJ+0xd018,OBJ+0x6000);d.u.mem_write(ctx+0x18,b'\1');d.invoke(0x40ca20,[OBJ+0xd000,ctx]);assert d.requests==[dict(behavior=600000310,kind=64,slot=0,hand=0,elapsed=0)]
assert ts['BehaviorParam_PC']['600000310']['refId']==81500 and ts['BehaviorParam_PC']['600000310']['refType']==0
stubs.update(d.stubs);checks=dict(timing=timing,script=scriptChecks,attack=d.requests);assert {k:len(v)for k,v in checks.items()}==dict(timing=29,script=12,attack=1)
a.output.write_text(json.dumps(dict(schema=1,effects=[7034200,7034201],root=9200006,magic=8015,baseline=1801500,bonus=7034207,marker=1801501,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),paramHashes=hashes,weaponSha256=sha(wepraw),scriptSha256=sha(script),coreEvidenceSha256=sha(core_path.read_bytes()),animationBundleSha256=anims['bundles'][0]['sha256'],taeSha256=t['sha256'],behaviorBundleSha256=g.metadata['bundleSha256'],behaviorSha256=g.metadata['hkxSha256'],events=events,bindings=bindings,checks=checks,stubs=sorted(stubs|{'Selected animation windows, Lua AddSpEffect transfer to the native actor, symbolic Lua API identifiers, and a successful MagicCommonFunction early return are explicit fixtures.','Both before/after script-update orderings are exercised. Blend variable is observed; Havok, complete collision, DLL, network, death/reload/unequip are not executed.'}),gameplayVerified=False),ensure_ascii=False,indent=2)+'\n');print('PASS',sum(map(len,checks.values())))
