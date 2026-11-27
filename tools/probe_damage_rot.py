"""Trace damage-triggered rot weapon enchantment and recipient buildup.

Runs original self grants, hand qualification, attack payload selection,
recipient status processing and timers with explicit identity/hit fixtures.
The selected effect IDs bridge isolated attacker and receiver contexts; full
collision and final HP writes are not executed.
"""
import argparse,itertools,json,math,struct,ctypes,ctypes.util,re
from pathlib import Path
from native_effect_runtime import BASE,OBJ,STOP,Inputs,Chain,sha
from native_ailment_runtime import Ailment
from unicorn.x86_const import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','assets','script','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted);inputs=x;t=x.x['tables']
assert sha(x.param)=='07ec636c5565d4551efeb53e6f08bc633b2aa4f2129f13c61b0638d69b1bc176'
assert len(x.rows)==struct.unpack_from('<H',x.param,10)[0]
raw=a.extracted.with_suffix('.AttachEffectParam.param').read_bytes();rows=Inputs.table(raw,0x44)
atkraw=a.extracted.with_suffix('.AtkParam_Pc.param').read_bytes();attacks=Inputs.table(atkraw,0x1d0);atk=attacks
weaponraw=a.assets.with_suffix('.EquipParamWeapon.param').read_bytes();weapons=Inputs.table(weaponraw,0x2a8)
assets=json.loads(a.assets.read_text());assert assets['hashes']['regulation.bin']==x.x['hashes']['regulation.bin']
assert sha(raw)=='ae8128ed510a532d0fa7cb56fa9c86e4a44c9d815dd4ee01c05821d5f50a9827'
assert sha(atkraw)=='1ec1893420053cbfb06e3efb269ade4ba9d6a617d1d3dbb370e837847be05676'
for b,table in ((raw,rows),(atkraw,attacks),(weaponraw,weapons)):assert len(table)==struct.unpack_from('<H',b,10)[0]
script=a.script.read_bytes();assert sha(script)=='96339bb15f57559cd42a940d616fcc2a18a10f50845cfc22b46b356ab66c3b29'
script_text=script.decode('utf-8-sig').replace('\r\n','\n')
style_function=re.search(r'^function SetStyleSpecialEffect\(\).*?(?=^function |\Z)',script_text,re.M|re.S)[0]
EFFECT=7170100;ROOTS=(7170100,7170105)
FAMILIES=[dict(hand=hand,marker=100619+hand,state=324-hand,root=7170100+5*(hand-1),guard=7170101+5*(hand-1),gate=7170104+5*(hand-1),leaf=7170102+5*(hand-1),payload=7170103+5*(hand-1)) for hand in (1,2)]
r=t['AttachEffectParam'][str(EFFECT)]
assert [r['passiveSpEffectId_'+str(n)] for n in (1,2,3)]==[*ROOTS,-1]
assert r['exclusivityId']==r['permanentSpEffectId']==-1 and all(v==1 for k,v in r.items() if k.startswith('allow'))
for f in FAMILIES:
 root,guard,gate,leaf,payload=(x.spells[str(f[k])] for k in ('root','guard','gate','leaf','payload'))
 assert root['spCategory']==guard['spCategory']==gate['spCategory']==0 and root['motionInterval']==1
 assert root['cycleOccurrenceSpEffectId']==f['guard'] and guard['replaceSpEffectId']==f['gate']
 assert guard['deleteCriteriaDamage']==1 and x.rows[f['guard']][0x327]==1
 assert gate['invocationConditionsStateChange1']==f['state'] and gate['effectEndurance']==0 and gate['cycleOccurrenceSpEffectId']==f['leaf']
 assert (leaf['stateInfo'],leaf['spCategory'],leaf['effectEndurance'],leaf['playerHandValue'],leaf['wepParamChange'])==(152,161+f['hand'],12,f['hand'],f['hand'])
 assert leaf['atkOccurrenceSpEffectId']==f['payload'] and struct.unpack_from('<i',x.rows[f['leaf']],0x12c)[0]==f['payload']
 assert leaf['isExtendSpEffectLife']==0 and leaf['isContractSpEffectLife']==1
 assert (payload['stateInfo'],payload['spCategory'],payload['effectEndurance'],payload['diseaseAttackPower'])==(5,10005,40,25)
 assert payload['changeHpPoint']==15 and math.isclose(payload['changeHpRate'],.15,rel_tol=1e-6)
 assert math.isclose(payload['motionInterval'],1.3,rel_tol=1e-6) and payload['isUseStatusAilmentAtkPowerCorrect']==1
 assert (payload['effectTargetSelfTarget'],payload['effectTargetFriendlyTarget'],payload['effectTargetOpposeTarget'])==(0,0,1)
tags={id:sorted(set(row[o] for o in (0x4e,0x4f,0x1c8,0x1c9,0x1ca))-{0}) for id,row in attacks.items()}
for id,ts in tags.items():assert ts==sorted({t['AtkParam_Pc'][str(id)]['subCategory'+str(n)] for n in range(1,6)}-{0})
representatives={}
for id,ts in tags.items():representatives.setdefault(tuple(ts),id)
assert len(representatives)==216
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
class Damage(Ailment):
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

class Enchant(Damage):
 def __init__(self,hand=1,weapon=1000000):
  self.hand=hand;self.weapon=weapon;super().__init__()
  self.q(OBJ+0x6478,STOP+0x800)
  # Actual stance markers selected by SetStyleSpecialEffect: left two-hand or right/default.
  if hand:self.grant(100621 if hand==2 else 100620)
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if address==STOP+0x800:
   self.stubs.add('actor virtual +278 explicit style 0/2 for context-12 hand check');ret(2 if self.hand==2 else 0)
  elif pc==0x3cf020:
   self.stubs.add('3CF020 equipped hand weapon ID supplied by the weapon case');ret(self.weapon)
  elif pc==0xea9a60:
   self.stubs.add('EA9A60 weapon wrapper cleanup');ret()
  elif pc==0xea7fc0:
   self.stubs.add('EA7FC0 actual supplied weapon PARAM lookup');id=u.reg_read(UC_X86_REG_RDX)&0xffffffff
   ptr=u.reg_read(UC_X86_REG_RCX)
   if id in weapons:u.mem_write(OBJ+0x1c000,weapons[id])
   u.mem_write(ptr,struct.pack('<iiQ',id,0,OBJ+0x1c000 if id in weapons else 0));ret(ptr)
  elif pc==0xe6d630:
   self.stubs.add('E6D630 actual AtkParam_Pc lookup for supplied attack context');id=u.reg_read(UC_X86_REG_R8)&0xffffffff;ptr=u.reg_read(UC_X86_REG_RCX);u.mem_write(OBJ+0x1b000,attacks[id]);u.mem_write(ptr,struct.pack('<iii4xQ',id,0,1,OBJ+0x1b000));ret(ptr)
  else:super().hook(u,address,size,user)

class Outgoing(Enchant):
    def outgoing(self, weapon, kind=1, flags=0, attack_category=0, attack=10000):
        vector, ctx = OBJ + 0x8000, OBJ + 0x8400
        self.q(vector + 8, OBJ + 0x8200)
        self.q(vector + 0x10, OBJ + 0x8200)
        self.q(vector + 0x18, OBJ + 0x8300)
        self.u.mem_write(ctx, bytes(0x300))
        self.u.mem_write(ctx + 0x122, bytes([kind]))
        self.u.mem_write(ctx + 0x161, bytes([flags]))
        self.u.mem_write(ctx + 0x190, struct.pack('<i', weapon))
        self.u.mem_write(ctx + 0x40, struct.pack('<iii', attack, 1, attack_category))
        self.u.mem_write(ctx + 0x280, struct.pack('<i', 10))
        self.u.mem_write(OBJ+0xb000,atk[attack]);self.q(OBJ+0xb410,OBJ+0xb000)
        self.invoke(0xe6d530,[OBJ+0xb400,ctx+0x124])
        assert int.from_bytes(self.u.mem_read(ctx+0x124,32),'little')==sum(1<<tag for tag in tags[attack])
        self.invoke(0x50f230, [OBJ+0x8800, ctx])
        self.invoke(0x506200, [OBJ, vector, OBJ+0x8800])
        end = struct.unpack('<Q', self.u.mem_read(vector + 0x10, 8))[0]
        count = (end - (OBJ + 0x8200)) // 4
        assert 0 <= count < 64
        return list(struct.unpack('<' + 'i' * count, self.u.mem_read(OBJ + 0x8200, count * 4)))

    def step(self,dt):self.qualify();self.update(dt)
    def disable(self):
        ptr=struct.unpack('<Q',self.u.mem_read(OBJ+8,8))[0]
        while ptr:
            self.u.mem_write(ptr+0x68,struct.pack('<I',0x800c0003));ptr=struct.unpack('<Q',self.u.mem_read(ptr+0x38,8))[0]

C=OBJ+0x60000;HIT=OBJ+0x61000;SOURCE=OBJ+0x62000;SEFFECT=OBJ+0x63000
class Hit(Damage):
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

assert sha(weaponraw)=='28adf74850c88ca0b4bb01f355c4f1f8e1b662a56d77894ae74d591b72c1a0ea'
checks={k:[] for k in ('style','selection','trigger','contexts','tags','weapons','composed','correction','targets','onset','damage','periodic','lifetime','refresh','overwrite','switch','disabled','continuous')};stubs=set()
def record(key,c=None,**row):
 checks[key].append(row)
 if c:stubs.update(c.stubs)
def step(c,dt=0):c.qualify();c.update(dt)
def active(c,id):return [n for n in c.nodes() if n['id']==id and not n['flags']&0x800c0003]
def prepare(copies=1,hand=1,weapon=1000000):
 c=Outgoing(hand=hand,weapon=weapon)
 for _ in range(copies):
  for root in ROOTS:c.grant(root)
 step(c);step(c)
 return c
def trigger(c,damage=1,excluded=0):
 before=len(c.grants);c.damage(damage,excluded)
 for _ in range(5):step(c)
 return c.grants[before:]
def family(hand):return FAMILIES[hand-1]
for style,existing in itertools.product(('neutral','right','right-both','left-both'),(0,1)):
 program=f"TRUE=1;FALSE=0;HAND_LEFT_BOTH='left-both';c_Style='{style}';GetSpEffectID='effect';AddSpEffect='add';local requests={{}}\n"
 program+=f"function env(key,id) assert(key=='effect');return {existing} end\nfunction act(key,id) assert(key=='add');table.insert(requests,id) end\n"
 result=run_lua(program+style_function+'\nSetStyleSpecialEffect();return table.concat(requests,",")')
 assert result==('' if existing else '100621' if style=='left-both' else '100620')
 record('style',style=style,alreadyPresent=existing,grant=result)
for copies,hero in itertools.product((1,2,3,6),range(11)):
 c=Selection([[EFFECT]]*copies,hero);bits=c.select();assert all(i*6 in bits for i in range(copies))
 roots=[]
 for _ in range(copies):
  c.invoke(0xe6e150,[OBJ+0x9200,EFFECT]);decoded=[c.invoke(0xe6e3b0,[OBJ+0x9200,n])&0xffffffff for n in (0,1,2)]
  assert decoded==[*ROOTS,0xffffffff];roots.extend(decoded[:2])
 v=prepare(copies);grants=trigger(v);assert len(active(v,7170102))==1;stubs.update(v.stubs)
 record('selection',c,copies=copies,hero=hero,bits=bits,roots=roots,grants=grants,nodes=v.nodes())
for copies,hand,damage,excluded in itertools.product((0,1,3,6),(0,1,2),(-1,0,1,10000),(0,1)):
 c=prepare(copies,hand);grants=trigger(c,damage,excluded);expected=family(hand)['leaf'] if copies and hand and damage>0 else None
 found=[n['id'] for n in c.nodes() if n['id'] in (7170102,7170107)]
 assert found==([expected] if expected else []),(copies,hand,damage,excluded,found)
 record('trigger',c,copies=copies,hand=hand,damage=damage,excluded=excluded,grants=grants,leaves=found)
print('PASS style/selection/trigger',len(checks['style']),len(checks['selection']),len(checks['trigger']),flush=True)
for hand,copies in itertools.product((1,2),(0,1,3)):
 c=prepare(copies,hand);trigger(c);f=family(hand)
 for kind,flags,category in itertools.product(range(13),(0,32),(0,6)):
  payloads=c.outgoing(1000000,kind,flags,category)
  assert payloads==([f['payload']] if copies and kind in (hand,11,12) else [])
  record('contexts',c,hand=hand,copies=copies,kind=kind,flags=flags,category=category,payloads=payloads)
for hand in (1,2):
 c=prepare(1,hand);trigger(c);f=family(hand)
 for attack in representatives.values():
  payloads=c.outgoing(1000000,hand,attack=attack);assert payloads==[f['payload']]
  record('tags',c,hand=hand,attack=attack,payloads=payloads)
 accepted=[];rejected=[]
 for weapon,row in weapons.items():
  payloads=c.outgoing(weapon,hand)
  allowed=bool(assets['tables']['EquipParamWeapon'][str(weapon)]['isEnhance'])
  assert payloads==([f['payload']] if allowed else []),(weapon,hand,payloads,allowed)
  (accepted if allowed else rejected).append(weapon)
 record('weapons',c,hand=hand,accepted=accepted,rejected=rejected)
print('PASS contexts/tags/weapons',len(checks['contexts']),len(checks['tags']),sum(len(r['accepted'])+len(r['rejected']) for r in checks['weapons']),flush=True)
for hand,copies,kind in itertools.product((1,2),(0,1,3),range(13)):
 c=prepare(copies,hand);trigger(c);payloads=c.outgoing(1000000,kind);v=Hit(1,500)
 v.hit(tuple(payloads),10000,1);step(v);assert v.remaining()==500-25*bool(payloads)
 record('composed',c,hand=hand,copies=copies,kind=kind,payloads=payloads,remaining=v.remaining(),sent=v.sent);stubs.update(v.stubs)
for f,scale in itertools.product(FAMILIES,(0,.25,.5,1,2)):
 c=Hit(1,500);c.hit(f['payload'],10000,scale);step(c)
 assert c.remaining()==500-int(25*scale) and not active(c,f['payload'])
 record('correction',c,payload=f['payload'],scale=scale,remaining=c.remaining(),sent=c.sent)
for f,target in itertools.product(FAMILIES,('self','friendly','opposing')):
 c=Hit(1,500);c.same=target=='self'
 if target=='friendly':c.u.mem_write(SOURCE+0x74,b'\6')
 c.hit(f['payload'],10000,1);step(c);assert c.remaining()==(475 if target=='opposing' else 500)
 record('targets',c,payload=f['payload'],target=target,remaining=c.remaining(),sent=c.sent)
for f,maximum in itertools.product(FAMILIES,(25,26,50,51,500)):
 c=Hit(1,maximum);count=math.ceil(maximum/25)
 for hit in range(1,count+1):
  c.hit(f['payload'],10000,1);step(c)
  assert bool(active(c,f['payload']))==(hit==count)
  assert c.remaining()==(maximum if hit==count else maximum-hit*25)
 # Existing rot does not build up or refresh on a further hit.
 step(c,5);before=active(c,f['payload'])[0]['lifetime'];c.hit(f['payload'],10000,1);step(c)
 assert active(c,f['payload'])[0]['lifetime']==before and c.remaining()==maximum
 record('onset',c,payload=f['payload'],resistance=maximum,hits=count,remaining=c.remaining(),lifeBefore=before,lifeAfter=active(c,f['payload'])[0]['lifetime'])
for f,maximum in itertools.product(FAMILIES,(1,137,1000,10000)):
 c=Hit(1,25);c.hit(f['payload'],10000,1);step(c);packet=c.hp_packet(maximum)
 assert packet[0]==-int(maximum*.0015+15),(maximum,packet)
 record('damage',c,payload=f['payload'],maximum=maximum,packet=packet)
print('PASS composed/recipients',len(checks['composed']),len(checks['correction']),len(checks['targets']),len(checks['onset']),len(checks['damage']),flush=True)
for f,fps in itertools.product(FAMILIES,(30,60,120)):
 c=Hit(1,25);c.hit(f['payload'],10000,1);packets=[];expired=None
 for frame in range(40*fps+6):
  step(c,1/fps);packet=c.hp_packet(1000)
  if packet[0]:
   assert packet[0]==-16;packets.append(frame)
  if not active(c,f['payload']):expired=frame;break
 assert expired is not None and abs(expired-40*fps)<=4,(f,fps,expired)
 assert packets[0]==0 and len(packets)==31,(f,fps,packets)
 assert all(abs((b-a)/fps-1.3)<=1/fps for a,b in zip(packets,packets[1:]))
 record('periodic',c,payload=f['payload'],fps=fps,packetFrames=packets,amount=-16,expiredFrame=expired)
print('PASS periodic',len(checks['periodic']),flush=True)
for f,copies,fps,extension in itertools.product(FAMILIES,(1,3),(30,60,120),(0,3)):
 c=prepare(copies,f['hand'])
 for _ in range(extension):c.grant(7006400)
 trigger(c);assert active(c,f['leaf'])[0]['lifetime']==12
 expired=None
 for frame in range(1,12*fps+6):
  step(c,1/fps)
  if not active(c,f['leaf']):expired=frame;break
 assert expired is not None and abs(expired-12*fps)<=3
 record('lifetime',c,hand=f['hand'],copies=copies,fps=fps,extension=extension,expiredFrame=expired)
for f,copies in itertools.product(FAMILIES,(1,3)):
 c=prepare(copies,f['hand']);trigger(c)
 for _ in range(4*60):step(c,1/60)
 grants=trigger(c);assert grants.count(f['leaf'])==1 and len(active(c,f['leaf']))==1 and active(c,f['leaf'])[0]['lifetime']==12
 record('refresh',c,hand=f['hand'],copies=copies,afterSeconds=4,grants=grants,lifetime=active(c,f['leaf'])[0]['lifetime'])
print('PASS lifetime/refresh',len(checks['lifetime']),len(checks['refresh']),flush=True)
# Actual Fire Grease goods row selects these right/left effect IDs.
grease=t['EquipParamGoods']['1400'];assert grease['refId_default']==3160 and grease['refId_1']==3162
for f in FAMILIES:
 for order in ((f['leaf'],3160 if f['hand']==1 else 3162),(3160 if f['hand']==1 else 3162,f['leaf']),(f['leaf'],f['leaf'])):
  c=Outgoing(hand=0)
  for id in order:c.grant(id);step(c)
  assert [n['id'] for n in c.nodes()]==[order[-1]]
  record('overwrite',c,order=order,nodes=c.nodes())
for first,second in ((1,2),(2,1)):
 c=prepare(1,first);trigger(c);c.hand=second;c.grant(family(second)['marker']);step(c)
 for _ in range(65):step(c,1/60)
 trigger(c)
 assert len(active(c,7170102))==len(active(c,7170107))==1
 record('switch',c,first=first,second=second,nodes=c.nodes(),right=c.outgoing(1000000,1),left=c.outgoing(1000000,2))
for f in FAMILIES:
 c=prepare(1,f['hand']);trigger(c);ptr=struct.unpack('<Q',c.u.mem_read(OBJ+8,8))[0]
 while struct.unpack('<i',c.u.mem_read(ptr+8,4))[0]!=f['leaf']:ptr=struct.unpack('<Q',c.u.mem_read(ptr+0x38,8))[0]
 c.u.mem_write(ptr+0x68,struct.pack('<I',0x40000));payloads=c.outgoing(1000000,f['hand']);assert payloads==[]
 record('disabled',c,hand=f['hand'],payloads=payloads)
for f,fps in itertools.product(FAMILIES,(30,60,120)):
 events_by_copies={}
 for copies in (1,3):
  c=prepare(copies,f['hand']);events=[]
  for frame in range(3*fps):
   c.qualify();c.damage();before=len(c.grants);c.update(1/fps)
   if f['leaf'] in c.grants[before:]:events.append(frame)
  assert 2<=len(events)<fps and len(active(c,f['leaf']))==1
  events_by_copies[copies]=events
  record('continuous',c,hand=f['hand'],fps=fps,copies=copies,leafFrames=events)
 assert events_by_copies[1]==events_by_copies[3]
print('PASS overwrite/switch/disabled/continuous',len(checks['overwrite']),len(checks['switch']),len(checks['disabled']),len(checks['continuous']),flush=True)
out=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),attachParamSha256=sha(raw),attackParamSha256=sha(atkraw),weaponParamSha256=sha(weaponraw),scriptSha256=sha(script),styleFunctionSha256=sha(style_function.encode()),
 effect=EFFECT,roots=ROOTS,families=FAMILIES,enchantDuration=12,buildup=25,rotDuration=40,rotInterval=1.3,rotHpPercent=.15,rotHpPoints=15,tagSets=len(representatives),weaponCount=len(weapons),checks=checks,
 native=dict(selection='4FEA30 → E6E150 → E6E3B0',damage='504D30',update='5057D0 → 50ACD0',grant='3C7FD0 → 3C80A0 → 3DB410',payload='E6D530 → 50F230 → 506200 → 511010',recipient='43BE60 → 3C80A0 → 42D110',hp='506EC0 → 50B860'),stubs=sorted(stubs),
 limitations=['Full collision, final HP write, complete equipment rebuild/death/reload, DLL hooks and multiplayer are not executed.',
 'The native outgoing vector is copied into an explicit incoming hit packet; full attack packet construction and motion correction extraction remain outside the fixture.',
 'Weapon IDs and actor hand-style virtuals are explicit inputs. All 2663 raw weapon rows are checked; not all are obtainable player weapons.',
 'Ordinary Fire Grease overwrite is verified; other special enchantments may have different category priorities.',
 'Ailment resistance is an explicit fixture, with no NPC resistance growth parameters; full enemy-specific immunities/growth and other rot sources remain untraced.',
 'Effect 1120 is emitted at rot onset; this does not claim all downstream resistance-growth behavior was executed.'],gameplayVerified=False)
a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('PASS total',sum(map(len,checks.values())),flush=True)
