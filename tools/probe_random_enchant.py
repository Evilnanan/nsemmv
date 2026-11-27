"""Trace random weapon enchant selection, hand scope, replacement and attack consumers.

Original PC code and current raw PARAM/TAE rows run with explicit actor,
equipment, activity-window and data-lookup fixtures. Reviewed HKS functions
run in Lua 5.4, not the game's full behavior VM. No live gameplay is claimed.
"""
import argparse,ctypes,ctypes.util,itertools,json,math,struct
from pathlib import Path
from native_effect_runtime import BASE,OBJ,STOP,Chain,Inputs,sha
from native_ailment_runtime import Ailment
from native_animation_runtime import NativeTae
from unicorn.x86_const import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','assets','script','animations','output'):p.add_argument(name,type=Path)
args=p.parse_args();x=Inputs(args.exe,args.extracted);inputs=x;ts=x.x['tables']
raws={name:args.extracted.with_suffix('.'+name+'.param').read_bytes() for name in ('AttachEffectParam','AtkParam_Pc')}
hashes={'AttachEffectParam':'ae8128ed510a532d0fa7cb56fa9c86e4a44c9d815dd4ee01c05821d5f50a9827','AtkParam_Pc':'1ec1893420053cbfb06e3efb269ade4ba9d6a617d1d3dbb370e837847be05676'}
for name,raw in raws.items():assert sha(raw)==hashes[name]
assert sha(x.param)=='07ec636c5565d4551efeb53e6f08bc633b2aa4f2129f13c61b0638d69b1bc176'
rows=Inputs.table(raws['AttachEffectParam'],0x44);attacks=Inputs.table(raws['AtkParam_Pc'],0x1d0)
weapon_raw=args.assets.with_suffix('.EquipParamWeapon.param').read_bytes();w=Inputs.table(weapon_raw,0x2a8)
assert sha(weapon_raw)=='28adf74850c88ca0b4bb01f355c4f1f8e1b662a56d77894ae74d591b72c1a0ea'
assets=json.loads(args.assets.read_text());assert assets['hashes']['regulation.bin']==x.x['hashes']['regulation.bin']
for table,raw in ((rows,raws['AttachEffectParam']),(attacks,raws['AtkParam_Pc']),(w,weapon_raw)):
 assert len(table)==struct.unpack_from('<H',raw,10)[0]
assert all(bool(row[0x106]&128)==bool(assets['tables']['EquipParamWeapon'][str(id)]['isEnhance']) for id,row in w.items())
assert ts['AttachEffectParam']['7035700']['passiveSpEffectId_1']==7035700
assert all(v==1 for k,v in ts['AttachEffectParam']['7035700'].items() if k.startswith('allow'))
root=x.spells['7035700'];assert (root['stateInfo'],root['spCategory'],root['effectEndurance'])==(2272,20,-1)
families=[]
for i,field in enumerate(('magicAttackPower','fireAttackPower','thunderAttackPower','darkAttackPower')):
 for hand in (0,1):
  seed=7035702+4*i+2*hand;leaf=seed+1;r=x.spells[str(seed)];l=x.spells[str(leaf)]
  assert (r['cycleOccurrenceSpEffectId'],r['effectEndurance'],r['invocationConditionsStateChange1'])==(leaf,0,323 if hand==0 else 0)
  assert (l['spCategory'],l['stateInfo'],l['wepParamChange'],l['effectEndurance'],l[field])==(162+hand,(64,62,151,205)[i],1+hand,10,20)
  families.append(dict(hand=hand,seed=seed,leaf=leaf,field=field,power=20,duration=10,category=162+hand))
all_checks={}
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

class Enchant(Actor):
 def __init__(self,weapon):super().__init__();self.weapon=weapon;self.hands=[];self.q(OBJ+0x6450,STOP+0x800)
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v&0xffffffffffffffff);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if address==STOP+0x800:self.hands.append(u.reg_read(UC_X86_REG_RDX)&0xffffffff);ret(self.weapon);return
  if pc==0xea7fc0:
   ptr=u.reg_read(UC_X86_REG_RCX);id=u.reg_read(UC_X86_REG_RDX)&0xffffffff
   if id in w:u.mem_write(OBJ+0x19000,w[id])
   u.mem_write(ptr,struct.pack('<I4xQI',id,OBJ+0x19000 if id in w else 0,id));ret(ptr);return
  if pc==0xea9a60:ret(u.reg_read(UC_X86_REG_RCX));return
  super().hook(u,address,size,user)
class Attack(Enchant):
 def hook(self,u,address,size,user):
  if address-BASE==0xe6d630:
   id=u.reg_read(UC_X86_REG_R8)&0xffffffff;assert u.reg_read(UC_X86_REG_RDX)==1
   wrapper=u.reg_read(UC_X86_REG_RCX);u.mem_write(OBJ+0xa800,attacks[id]);u.mem_write(wrapper,struct.pack('<iii4xQ',id,0,1,OBJ+0xa800))
   sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8);return
  super().hook(u,address,size,user)
def attack(c,weapon,attached,kind):
 out=OBJ+0x8400;c.u.mem_write(out,bytes(0x300));c.u.mem_write(out+8,struct.pack('<iiB',2,1,kind))
 c.u.mem_write(OBJ+0xa800,attacks[2]);c.q(OBJ+0xb010,OBJ+0xa800);c.invoke(0xe6d530,[OBJ+0xb000,out+0x14])
 c.u.mem_write(out+0xe8,struct.pack('<i',weapon));c.invoke(0x502830,[OBJ,out,weapon,attached])
 return dict(points=[struct.unpack('<f',c.u.mem_read(out+off,4))[0] for off in (0x48,0x5c,0x60,0x64,0x68)])

SEEDS=tuple(range(7035702,7035717,2));LEAVES={s+1 for s in SEEDS}
checks={k:[] for k in ('seeds','overlap','timing','grease','extension','disabled','selection')}
def step(c,dt=1/60):c.qualify();c.update(dt)
def active(c):return sorted(n['id'] for n in c.nodes() if n['id'] in LEAVES and not n['flags']&0x800c0003)
def equip(copies=1,weapon=1000500,marker=100620):
 c=Attack(weapon)
 for _ in range(copies):c.grant(7035700)
 if marker:c.grant(marker)
 step(c,0);return c
def trigger(c,seed):
 c.grant(seed)
 for i in range(3):step(c)
def points(c,hand):return attack(c,c.weapon,-1,hand+1)['points']
for hero,copies in itertools.product(range(11),(0,1,3)):
 c=Selection([[7035700] for _ in range(copies)],hero);selected=c.select()
 assert all(i*6 in selected for i in range(copies)),(hero,copies,selected)
 checks['selection'].append(dict(hero=hero,copies=copies,selected=selected))
for seed,weapon,marker,copies in itertools.product(SEEDS,(1000500,7130000),(None,100620,100621),(1,3)):
 c=equip(copies,weapon,marker);trigger(c,seed);actual=active(c)
 eligible=weapon==1000500 and (seed%4==0 or marker==100620)
 assert actual==([seed+1] if eligible else []),(seed,weapon,marker,copies,actual)
 vals=[points(c,hand) for hand in (0,1)]
 expected=[[0.]*5,[0.]*5]
 if eligible:expected[(seed-7035702)%4//2][1+(seed-7035702)//4]=20.
 assert vals==expected,(seed,vals,expected)
 checks['seeds'].append(dict(seed=seed,weapon=weapon,marker=marker,copies=copies,active=actual,points=vals))
print('seed checks',len(checks['seeds']),flush=True)
for first,second in itertools.product(SEEDS,repeat=2):
 c=equip();trigger(c,first)
 for _ in range(60):step(c)
 trigger(c,second);actual=active(c)
 same=first%4==second%4;expected=[second+1] if same else sorted((first+1,second+1))
 assert actual==expected,(first,second,actual)
 vals=[points(c,hand) for hand in (0,1)];expect=[[0.]*5,[0.]*5]
 for leaf in expected:expect[(leaf-7035703)%4//2][1+(leaf-7035703)//4]=20.
 assert vals==expect,(first,second,vals,expect)
 assert math.isclose(next(n['lifetime'] for n in c.nodes() if n['id']==second+1),10-2/60,abs_tol=1e-5)
 checks['overlap'].append(dict(first=first,second=second,active=actual,points=vals))
print('overlap checks',len(checks['overlap']),flush=True)
for seed,fps in itertools.product(SEEDS,(30,60,120)):
 c=equip();c.grant(seed);seen=None;ended=None
 for frame in range(1,11*fps+1):
  step(c,1/fps);a=active(c)
  if a and seen is None:seen=frame
  if seen and not a:ended=frame;break
 assert seen==2 and abs((ended-seen)/fps-10)<3/fps,(seed,fps,seen,ended)
 assert points(c,0)==points(c,1)==[0.]*5
 checks['timing'].append(dict(seed=seed,fps=fps,firstFrame=seen,endFrame=ended))
print('timing checks',len(checks['timing']),flush=True)
for seed,extension in itertools.product(SEEDS,(7006400,8330500,7030940)):
 c=equip();c.grant(extension);step(c,0);trigger(c,seed);step(c,1)
 life=next(n['lifetime'] for n in c.nodes() if n['id']==seed+1)
 assert math.isclose(life,10-2/60-1,abs_tol=1e-5),(seed,extension,life)
 checks['extension'].append(dict(seed=seed,extension=extension,lifetime=life))
for seed,mask in itertools.product(SEEDS,(1,2,0x40000,0x80000000)):
 c=equip();trigger(c,seed);ptr=struct.unpack('<Q',c.u.mem_read(OBJ+8,8))[0]
 while ptr:
  if struct.unpack('<i',c.u.mem_read(ptr+8,4))[0]==seed+1:
   flags=struct.unpack('<I',c.u.mem_read(ptr+0x68,4))[0];c.u.mem_write(ptr+0x68,struct.pack('<I',flags|mask));break
  ptr=struct.unpack('<Q',c.u.mem_read(ptr+0x38,8))[0]
 assert ptr
 vals=[points(c,h) for h in (0,1)];assert vals==[[0.]*5]*2
 checks['disabled'].append(dict(seed=seed,mask=mask,points=vals))
for seed,grease,reverse in itertools.product(SEEDS,(3160,3162),(False,True)):
 c=equip()
 if reverse:c.grant(grease);step(c,0);trigger(c,seed)
 else:trigger(c,seed);c.grant(grease);step(c,0)
 checks['grease'].append(dict(seed=seed,grease=grease,reverse=reverse,nodes=c.nodes(),points=[points(c,h) for h in (0,1)]))

for r in checks['grease']:
 seed,grease=r['seed'],r['grease'];hand=(seed-7035702)%4//2;gHand=0 if grease==3160 else 1
 expected=[[0.]*5,[0.]*5]
 if hand!=gHand or r['reverse']:expected[hand][1+(seed-7035702)//4]=20.
 if hand!=gHand or not r['reverse']:expected[gHand][2]=35.
 assert r['points']==expected,r
 ids=[n['id'] for n in r['nodes'] if n['id'] in (seed+1,grease)]
 wanted=sorted((seed+1,grease)) if hand!=gHand else [seed+1 if r['reverse'] else grease]
 assert sorted(ids)==wanted,r
all_checks.update(checks)

lua = ctypes.CDLL(ctypes.util.find_library('lua5.4'))
lua.luaL_newstate.restype = ctypes.c_void_p
lua.luaL_openlibs.argtypes = [ctypes.c_void_p]
lua.luaL_loadstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
lua.lua_pcallk.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_ssize_t, ctypes.c_void_p]
lua.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_size_t)]
lua.lua_tolstring.restype = ctypes.c_char_p
lua.lua_close.argtypes = [ctypes.c_void_p]

def execute_lua(program):
    state = lua.luaL_newstate()
    try:
        lua.luaL_openlibs(state)
        assert lua.luaL_loadstring(state, program.encode()) == 0
        status = lua.lua_pcallk(state, 0, 1, 0, 0, None)
        result = lua.lua_tolstring(state, -1, None)
        assert status == 0, result
        return json.loads(result)
    finally:
        lua.lua_close(state)

raw=args.script.read_bytes();source=raw.decode('utf-8-sig').replace('\r\n','\n')
assert sha(raw)=='96339bb15f57559cd42a940d616fcc2a18a10f50845cfc22b46b356ab66c3b29'
begin=source.index('function SetStyleSpecialEffect(');body=source[begin:source.index('\nfunction ',begin+1)]
# Extract through the final end; following globals are harmless original code.
def style(c,which):
 present={n['id'] for n in c.nodes() if not n['flags']&0x800c0003}
 pre='TRUE=1;FALSE=0;GetSpEffectID=1;AddSpEffect=2;HAND_LEFT_BOTH=2;c_Style=%d;local added={};local present={%s}\nfunction env(_,id)return present[id] and TRUE or FALSE end\nfunction act(_,id)table.insert(added,id)end\n' % (which,','.join('[%d]=true'%id for id in present))
 added=execute_lua(pre+body+'\nSetStyleSpecialEffect()\nreturn "["..table.concat(added,",").."]"')
 for id in added:c.grant(id)
 c.qualify();c.update(0);return added
checks=[]
for initial,target in itertools.product(range(4),repeat=2):
 c=Attack(1000500);c.grant(7035700);first=style(c,initial);second=style(c,target)
 active_markers=[n['id'] for n in c.nodes() if n['id'] in (100620,100621) and not n['flags']&0x800c0003]
 assert active_markers==([100621] if target==2 else [100620]),(initial,target,active_markers)
 for seed in (7035702,7035704):
  c.grant(seed)
  for _ in range(3):c.qualify();c.update(1/60)
 leaves=sorted(n['id'] for n in c.nodes() if 7035703<=n['id']<=7035705 and not n['flags']&0x800c0003)
 assert leaves==([7035705] if target==2 else [7035703,7035705]),(initial,target,leaves)
 checks.append(dict(initial=initial,target=target,first=first,second=second,active=active_markers,leaves=leaves))

all_checks['style']=checks
script_hash=sha(raw);style_function_hash=sha(body.encode())

class HandAttack(Attack):
 def __init__(self,weapon,style):super().__init__(weapon);self.style=style;self.q(OBJ+0x6478,STOP+0x801)
 def hook(self,u,address,size,user):
  if address==STOP+0x801:
   u.reg_write(UC_X86_REG_RAX,self.style);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8);return
  super().hook(u,address,size,user)
 def points(self,id,kind,weapon):
  out=OBJ+0x8400;self.u.mem_write(out,bytes(0x300));self.u.mem_write(out+8,struct.pack('<iiB',id,1,kind))
  self.u.mem_write(OBJ+0xa800,attacks[id]);self.q(OBJ+0xb010,OBJ+0xa800);self.invoke(0xe6d530,[OBJ+0xb000,out+0x14])
  self.u.mem_write(out+0xe8,struct.pack('<i',weapon));self.invoke(0x502830,[OBJ,out,-1,-1])
  return [struct.unpack('<f',self.u.mem_read(out+off,4))[0] for off in (0x48,0x5c,0x60,0x64,0x68)]
checks=[]
for leaf,style in itertools.product(range(7035703,7035718,2),range(4)):
 c=HandAttack(1000500,style);c.grant(leaf);c.qualify();c.update(0)
 for kind,weapon in itertools.product(range(13),(1000500,7130000)):
  vals=c.points(2,kind,weapon);hand=(leaf-7035703)%4//2
  eligible=(kind in (1,11,12) if hand==0 else kind in (2,11) or kind==12 and style==2) and weapon==1000500
  expect=[0.]*5
  if eligible:expect[1+(leaf-7035703)//4]=20.
  assert vals==expect,(leaf,style,kind,weapon,vals,expect)
  checks.append(dict(leaf=leaf,style=style,kind=kind,weapon=weapon,points=vals))

all_checks['attack']=checks

representatives={}
for id,row in ts['AtkParam_Pc'].items():representatives.setdefault((tuple(sorted({row['subCategory'+str(i)] for i in range(1,6)}-{0})),row['spEffectAtkPowerCorrectRate_byPoint']),int(id))
checks=[]
for leaf in range(7035703,7035718,2):
 c=HandAttack(1000500,0);c.grant(leaf);c.qualify();c.update(0)
 hand=(leaf-7035703)%4//2;expected=[0.]*5;expected[1+(leaf-7035703)//4]=20.
 for (tags,correct),id in representatives.items():
  vals=c.points(id,hand+1,1000500);expect=[v*correct/100 for v in expected];assert all(math.isclose(a,b,abs_tol=1e-5) for a,b in zip(vals,expect)),(leaf,id,tags,correct,vals,expect)
  checks.append(dict(leaf=leaf,attack=id,tags=tags,pointCorrection=correct,points=vals))

all_checks['tags']=checks

class Window(Attack):
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if pc in (0x3ced90,0x4d1b20):ret(OBJ+0xd800 if pc==0x3ced90 else 0)
  elif pc==0x26909a0:ret(u.reg_read(UC_X86_REG_RAX))
  else:super().hook(u,address,size,user)
 def context(self,tae,animation):
  ctx=OBJ+0xd100;self.u.mem_write(ctx,bytes(0x40))
  for _ in range(10000):
   if not self.invoke(0x27d0400,[tae.animations[animation],ctx]):break
   if struct.unpack('<I',self.u.mem_read(ctx,4))[0]!=66:continue
   payload=struct.unpack('<Q',self.u.mem_read(ctx+8,8))[0]
   if struct.unpack('<i',self.u.mem_read(payload,4))[0]!=7035701:continue
   self.u.mem_write(ctx+0x18,b'\1');return ctx
  raise AssertionError(animation)
checks=[]
meta=json.loads(args.animations.read_text())
for bundle in meta['bundles']:
 for track in bundle['taes']:
  if track['ID'] not in (2000,2002,2003):continue
  c=Window(1000500);raw=args.animations.with_name(args.animations.name+'.'+str(track['ID'])+'.tae').read_bytes();tae=NativeTae(c,raw,track['sha256'])
  for copies,animation in itertools.product((0,1,3),(29020,29021,29022,29023,29050,29051,29052,29053)):
   c.invoke(0x504e80,[OBJ,7035700]);c.invoke(0x504e80,[OBJ,7035701])
   for _ in range(copies):c.grant(7035700)
   c.qualify();c.update(0);ctx=c.context(tae,animation);c.q(OBJ+0xd018,OBJ+0x6000)
   c.invoke(0x410ca0,[OBJ+0xd000,ctx]);c.qualify();c.update(0)
   active_marker=[n['id'] for n in c.nodes() if n['id']==7035701 and not n['flags']&0x800c0003]
   assert bool(active_marker)==bool(copies),(track['ID'],animation,copies,c.nodes())
   checks.append(dict(tae=track['ID'],animation=animation,copies=copies,active=active_marker))

all_checks['events']=checks

checks={k:[] for k in ('weaponChange','styleChange','rootRemoval')}
for seed in SEEDS:
 for replacement in (1000500,7130000):
  c=equip();trigger(c,seed);c.weapon=replacement;step(c)
  changed=c.nodes();vals=[points(c,h) for h in (0,1)];c.weapon=1000500;step(c)
  checks['weaponChange'].append(dict(seed=seed,replacement=replacement,changed=changed,restored=c.nodes(),points=vals))
 c=equip();trigger(c,seed);c.grant(100621);step(c)
 checks['styleChange'].append(dict(seed=seed,nodes=c.nodes(),points=[points(c,h) for h in (0,1)]))
 c=equip();trigger(c,seed);c.invoke(0x504e80,[OBJ,7035700]);step(c)
 checks['rootRemoval'].append(dict(seed=seed,nodes=c.nodes(),points=[points(c,h) for h in (0,1)]))

for key,rs in checks.items():
 for r in rs:
  leaf=r['seed']+1;nodes=r.get('changed',r.get('nodes'))
  assert any(n['id']==leaf and not n['flags']&0x800c0003 for n in nodes)
  expected=[[0.]*5,[0.]*5]
  if key!='weaponChange' or r['replacement']==1000500:expected[(leaf-7035703)%4//2][1+(leaf-7035703)//4]=20.
  assert r['points']==expected
  if key=='weaponChange':assert any(n['id']==leaf and not n['flags']&0x800c0003 for n in r['restored'])
  if key=='rootRemoval':assert not any(n['id']==7035700 for n in nodes)
all_checks.update(checks)

counts={k:len(v) for k,v in all_checks.items()}
assert counts==dict(seeds=96,overlap=64,timing=24,grease=32,extension=24,disabled=32,selection=33,style=16,attack=832,tags=3160,events=72,weaponChange=16,styleChange=8,rootRemoval=8)
args.output.write_text(json.dumps(dict(schema=1,effect=7035700,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),paramHashes=hashes,weaponSha256=sha(weapon_raw),scriptSha256=script_hash,styleFunctionSha256=style_function_hash,
 taeSha256={str(track['ID']):track['sha256'] for bundle in meta['bundles'] for track in bundle['taes'] if track['ID'] in (2000,2002,2003)},families=families,attackGroups=len(representatives),checks=all_checks,
 native=dict(selection='4FEA30 → E6E150 → E6E3B0',event='27D0F10 → 27D0400 → 410CA0 → 3C8BE0',grant='3C7FD0 → 3C80A0 → 3DB410',weapon='3CF020 → virtual +250 → EA7FC0',container='50D060 → 5057D0 → 50ACD0',attack='E6D530 → 502830 → 511010 → EA1B00 / EA1D40'),
 stubs=sorted(c.stubs|{'Explicit inventory slots/handles, hero IDs, allocator and AttachEffect lookup for selection; original selection logic executes.',
 'Actor virtual +250 supplies the selected hand weapon ID; +278 supplies the holding style. Actual weapon and attack PARAM bytes are supplied by lookup fixtures.',
 'EA9A60 absent auxiliary lookup; 3CED90 neutral action context; 4D1B20 false activity predicate; 26909A0 security-cookie return preserves RAX.',
 'Native Type66 event activity flag is explicitly enabled; raw TAE relocation, iteration and dispatch execute. Full animation scheduling and continuous keepalive are not simulated.',
 'Actual SetStyleSpecialEffect executes in Lua 5.4 with current native active-effect presence; emitted effects are delivered through the native grant path.',
 'Attack kind, current weapon and actual attack PARAM row are explicit inputs; the original attack consumer performs hand, tag and enhancement checks.',
 'Direct root removal and weapon/style field changes are isolated operations, not full inventory rebuilds, death, reload or multiplayer.'}),
 gameplayVerified=False),ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(counts.values()),counts)
