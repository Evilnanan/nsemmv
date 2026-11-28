"""Trace the three mixed magic fields from animation requests to impact and effects.

Geometry and impact delivery are fixtures. Native animation, request conversion,
recipient qualification and effect consumers run with the pinned game data.
"""
import argparse, itertools, json, struct
from pathlib import Path
from native_effect_runtime import BASE, OBJ, STOP, Chain, Inputs, sha
from native_ailment_runtime import Ailment
from native_animation_runtime import NativeTae
from native_attack_runtime import Type1Attack
from unicorn.x86_const import *

parser = argparse.ArgumentParser(description=__doc__)
for name in ('exe', 'extracted', 'animations', 'assets', 'output'):
    parser.add_argument(name, type=Path)
a = parser.parse_args()
x = Inputs(a.exe, a.extracted)
ts = x.x['tables']
param_hashes = {
    'AtkParam_Pc': '1ec1893420053cbfb06e3efb269ade4ba9d6a617d1d3dbb370e837847be05676',
    'BehaviorParam_PC': 'f8fa3fd27cb98d45a3e24c69d71d8751df9202e6e379dc34fd77d4ef2e1240bb',
    'Bullet': 'ddce4888040a061cf982a237e8f6e3ddce5f2162a238865a072f75d27b5e9d44',
    'Magic': '17742eeafe4fade863f3a7ee5f7ff483bd4897f765802fe4a1954dfa8107b63e',
    'PlayerCommonParam': '2e7b384f9590e6fa3f19b2f93e3826cebf8d399246fe987382086a445f7f096c',
}
raws = {name: a.extracted.with_suffix('.' + name + '.param').read_bytes() for name in param_hashes}
for name, raw in raws.items():
    assert sha(raw) == param_hashes[name]
assert sha(x.param) == '07ec636c5565d4551efeb53e6f08bc633b2aa4f2129f13c61b0638d69b1bc176'
attacks = Inputs.table(raws['AtkParam_Pc'], 0x1d0)
behaviors = Inputs.table(raws['BehaviorParam_PC'], 0x20)
bullets = Inputs.table(raws['Bullet'], 0x15c)
weapon_raw = a.assets.with_suffix('.EquipParamWeapon.param').read_bytes()
assert sha(weapon_raw) == '28adf74850c88ca0b4bb01f355c4f1f8e1b662a56d77894ae74d591b72c1a0ea'
weapons = Inputs.table(weapon_raw, 0x2a8)
assets = json.loads(a.assets.read_text())
assert assets['hashes']['regulation.bin'] == x.x['hashes']['regulation.bin']
common_raw = raws['PlayerCommonParam']
common = common_raw[struct.unpack_from('<Q', common_raw, 0x48)[0]:]
assert struct.unpack_from('<f', common, 0x30)[0] == 1.5
core_path = Path(__file__).resolve().parent.parent / 'data/effect-mixed-magic-evidence.json'
core = json.loads(core_path.read_text())
assert core['effects'] == [7034200, 7034201] and core['root'] == 9200006
assert core['paramHashes']['Magic'] == param_hashes['Magic']

# Track, magic row, behavior, bullet, attack, impact effect, duration, target flags.
field_paths = [
    (2531, 8012, 700000303, 10801203, 81201, 7034205, 3, (1, 1, 0)),
    (2533, 8014, 700000304, 10801401, 81400, 7034206, 8, (1, 1, 0)),
    (2538, 8023, 700000305, 10802302, 82310, 7034208, 20, (0, 0, 1)),
]
for track, magic, behavior, bullet, attack, effect, duration, targets in field_paths:
    assert ts['Magic'][str(magic)]['refType'] == track - 2400
    assert (struct.unpack_from('<B', behaviors[behavior], 9)[0], struct.unpack_from('<i', behaviors[behavior], 12)[0]) == (1, bullet)
    row = ts['Bullet'][str(bullet)]
    assert (row['atkId_Bullet'], row['spEffectId0']) == (attack, effect)
    assert tuple(ts['AtkParam_Pc'][str(attack)][key] for key in ('selfTarget', 'friendlyTarget', 'opposeTarget')) == targets
    assert x.spells[str(effect)]['effectEndurance'] == duration


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



fields={7034205:(10801203,81201),7034206:(10801401,81400),7034208:(10802302,82310)}
class Recipient(Hit):
 def values(self,maximum=1000):
  self.invoke(0x5066a0,[OBJ]);stamina=struct.unpack('<f',(self.u.reg_read(UC_X86_REG_XMM0)&0xffffffff).to_bytes(4,'little'))[0]
  self.u.mem_write(OBJ+0x800,bytes(0x200));self.invoke(0x503800,[OBJ,OBJ+0x500,OBJ+0x520,OBJ+0x540,OBJ+0x800]);defense=list(struct.unpack('<5f',self.u.mem_read(OBJ+0x500,20)))
  return dict(stamina=stamina,defense=defense,hp=self.hp_packet(maximum))
 def place(self,id):
  bullet,atk=fields[id];assert ts['Bullet'][str(bullet)]['atkId_Bullet']==atk and ts['Bullet'][str(bullet)]['spEffectId0']==id
  self.hit(id,attack=atk)

class Filter(Chain):
 def __init__(self,attack):
  super().__init__(x);self.attack=attack;self.calls=[]
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(value=0):
   u.reg_write(UC_X86_REG_RAX,value);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if pc==0x535bf9:u.reg_write(UC_X86_REG_RIP,STOP)
  elif pc==0x63f840:self.calls.append(u.reg_read(UC_X86_REG_RCX));ret(0)
  elif pc==0xe6d630:
   assert u.reg_read(UC_X86_REG_R8)==self.attack and u.reg_read(UC_X86_REG_RDX)==1
   row=OBJ+0xb000;u.mem_write(row,attacks[self.attack]);wrapper=u.reg_read(UC_X86_REG_RCX);u.mem_write(wrapper,struct.pack('<iii4xQ',self.attack,0,1,row));ret()
  else:super().hook(u,address,size,user)



class Cost(Chain):
 def __init__(self,roots,disabled=False):
  super().__init__(x);self.blocked=False;self.actor_flag=0;self.base_flag=0
  for root in roots:self.insert(root)
  self.qualify();self.update(0)
  if disabled:
   node=struct.unpack('<Q',self.u.mem_read(OBJ+8,8))[0]
   while node:
    self.u.mem_write(node+0x68,struct.pack('<I',0x800c0003));node=struct.unpack('<Q',self.u.mem_read(node+0x38,8))[0]
  self.actor=OBJ+0xd000;self.resource=OBJ+0xe800
  self.q(self.actor,OBJ+0xe000);self.q(OBJ+0xe190,STOP+0x210);self.q(self.actor+0x190,OBJ)
  assert len(common)<0x10000;self.u.mem_map(OBJ+0x80000,0x10000);self.u.mem_write(OBJ+0x80000,common)
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(value=0):
   u.reg_write(UC_X86_REG_RAX,value&0xffffffffffffffff);sp=u.reg_read(UC_X86_REG_RSP)
   u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  ptr=u.reg_read(UC_X86_REG_RCX)
  if pc==0xea7fc0:
   id=u.reg_read(UC_X86_REG_RDX)&0xffffffff
   u.mem_write(OBJ+0xc100,weapons[id]);self.q(ptr+8,OBJ+0xc100);ret(ptr)
   self.stubs.add('EA7FC0 actual weapon row lookup')
  elif pc==0xea9a60:
   self.q(ptr+8,0);ret(ptr);self.stubs.add('EA9A60 no reinforcement row')
  elif pc==0xe81650:
   self.q(ptr,OBJ+0x80000);ret(ptr);self.stubs.add('E81650 actual PlayerCommon row')
  elif pc==0x3ced90:
   ret(OBJ+0xf000);self.stubs.add('3CED90 explicit actor context')
  elif pc==0x4d1b20:
   ret(int(self.blocked));self.stubs.add('4D1B20 explicit actor early-exit predicate')
  elif pc==0x3d4960:
   ret(self.actor_flag);self.stubs.add('3D4960 explicit actor flag, not equated with weapon correction mask')
  elif address==STOP+0x210:
   ret(self.resource);self.stubs.add('actor virtual+190 explicit resource object, native +10C threshold comparison')
  else:super().hook(u,address,size,user)
 def number(self):return struct.unpack('<f',(self.u.reg_read(UC_X86_REG_XMM0)&0xffffffff).to_bytes(4,'little'))[0]
 def rate(self):self.invoke(0x5066a0,[OBJ]);return self.number()
 def cost(self,base,weapon,value,mask,base_flag=0,actor_flag=0,blocked=False):
  self.blocked=blocked;self.actor_flag=actor_flag
  self.u.mem_write(self.resource+0x10c,struct.pack('<i',value))
  result=self.invoke(0x668730,[self.actor,base,weapon,base_flag,mask])
  return struct.unpack('<i',struct.pack('<I',result&0xffffffff))[0]

def f32(v):return struct.unpack('<f',struct.pack('<f',v))[0]
def expected_rate(roots):
 rate=1.
 for id in roots:rate=f32(rate*x.spells[str(id)]['consumeStaminaRate'])
 return rate


class Emitter(Type1Attack):
 def __init__(self):
  super().__init__(x,behaviors,weapons,{700000303,700000304,700000305});self.shots=[];self.behaviorRequests=[];self.bulletLookups=[]
  self.q(OBJ+0x6100,OBJ+0x6000);self.u.mem_write(OBJ+0x61f6,b"\x40");self.q(OBJ+0x66b8,STOP+0x201);self.q(OBJ+0x6320,STOP+0x200);self.q(OBJ+0x6418,STOP+0x210);self.q(OBJ+0x6548,STOP+0x211);self.q(OBJ+0x6550,STOP+0x211);self.q(OBJ+0x90e8,OBJ+0xa000)
 def hook(self,u,address,size,user):
  pc=address-BASE
  rcx=u.reg_read(UC_X86_REG_RCX);rdx=u.reg_read(UC_X86_REG_RDX)
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if pc==0x3975d0:
   self.behaviorRequests.append(rdx);return
  if pc in (0x27d0640,0x484500,0x3d74f0,0x33e650,0x384a30,0x383ba0):ret()
  elif pc==0xe87800:
   self.bulletLookups.append(rdx)
   u.mem_write(OBJ+0xb000,bullets[rdx]);self.q(rcx,OBJ+0xb000);u.mem_write(rcx+8,struct.pack('<I',rdx));ret(rcx)
  elif pc==0xe875a0:u.reg_write(UC_X86_REG_XMM0,0);ret()
  elif pc==0x3d15b0:u.mem_write(rdx,struct.pack('<16f',*[int(i%5==0) for i in range(16)]));ret(rdx)
  elif pc==0x4b1b90:ret(OBJ+0xb800)
  elif address==STOP+0x210:u.mem_write(rdx,struct.pack('<4f',1,1,1,1));ret(rdx)
  elif address==STOP+0x211:u.reg_write(UC_X86_REG_XMM0,0);ret()
  elif pc==0x4b77c0:
   request=bytes(u.mem_read(rdx,0x110));behavior=struct.unpack_from('<I',request,8)[0];self.shots.append(dict(behavior=behavior,request=request.hex()));ret(1)
  else:super().hook(u,address,size,user)

anims=json.loads(a.animations.read_text())
assert anims['bundles'][0]['sha256']=='806e6b218d747277ab45e14f45ca80b9ecf8c13ada22f89db2d3ef23caa62b2a'
launches=[];stubs=set()
for tid,copies,active in itertools.product((2531,2533,2538),(0,1,3),(False,True)):
 c=Emitter();t=next(t for b in anims['bundles']for t in b['taes']if t['ID']==tid)
 for _ in range(copies):c.insert(7034200)
 c.qualify();c.update(0)
 loader=NativeTae(c,Path(str(a.animations)+'.'+str(tid)+'.tae').read_bytes(),t['sha256']);ctx=OBJ+0xd100;c.u.mem_write(ctx,bytes(0x40));found=False
 while c.invoke(0x27d0400,[loader.animations[45010],ctx]):
  if struct.unpack('<I',c.u.mem_read(ctx,4))[0]!=2:continue
  ptr=struct.unpack('<Q',c.u.mem_read(ctx+8,8))[0];raw=bytes(c.u.mem_read(ptr,32))
  if raw[14:16]!=b'\xff\x07':continue
  tp=struct.unpack('<Q',c.u.mem_read(ctx+0x20,8))[0];start,end=struct.unpack('<f4xf',c.u.mem_read(tp,12))
  found=True;c.q(OBJ+0xd018,OBJ+0x6000);c.u.mem_write(ctx+0x18,bytes([active]));c.invoke(0x40cd80,[OBJ+0xd000,ctx]);break
 assert found
 expected=700000303+(2531,2533,2538).index(tid)
 assert [r["behavior"]for r in c.shots]==([expected]if copies and active else []),(c.behaviorRequests,c.shots,behaviors[expected].hex())
 assert c.bulletLookups==([field_paths[(2531,2533,2538).index(tid)][3]] if copies and active else [])
 assert c.behaviorRequests==([expected] if copies and (active or tid==2538) else [])
 stubs.update(c.stubs)
 launches.append(dict(event={'start':start,'end':end,'payload':raw.hex(),'taeSha256':t['sha256']},bulletLookups=c.bulletLookups,tae=tid,copies=copies,active=active,behaviorRequests=c.behaviorRequests,queued=c.shots));print('PASS',tid,copies,active,len(c.behaviorRequests),len(c.shots),flush=True)


receiver_checks=[]
for id,(dest,source,same) in itertools.product(fields,[(1,i,False)for i in range(10)]+[(1,1,True),(6,1,False)]):
 c=Recipient();c.same=same;c.u.mem_write(OBJ+0x6074,bytes([dest]));c.u.mem_write(SOURCE+0x74,bytes([source]));c.place(id);c.qualify();c.update(1/60)
 r=dict(id=id,dest=dest,source=source,same=same,nodes=c.nodes(),sent=[s['id']for s in c.sent],values=c.values());expected=(dest==1 and (same or source in (1,2,4))) if id!=7034208 else (same or (dest==1 and source in (6,7,8,9)) or (dest,source)==(6,1))
 assert bool(r['nodes'])==expected,(r,expected)
 receiver_checks.append(r);stubs.update(c.stubs)


timelines=[]
for id,fps,hits in itertools.product(fields,(30,60,120),((0,),(0,0,0),(0,.2),(0,.5,1,1.5,2),(0,2))):
 c=Recipient();c.u.mem_write(OBJ+0x6074,b'\6' if id==7034208 else b'\1');arrivals=[round(t*fps)for t in hits];life=ts['SpEffectParam'][str(id)]['effectEndurance'];pulses=[];nodes=[];previous=None;peak=0
 for frame in range(round((life+max(hits)+1)*fps)):
  for _ in range(arrivals.count(frame)):c.place(id)
  c.qualify();c.update(1/fps);active=[n for n in c.nodes()if n['id']==id and not n['flags']&0x800c0003];peak=max(peak,len(active));assert peak==1
  if bool(active)!=previous or frame in arrivals:nodes.append(dict(frame=frame,active=active));previous=bool(active)
  if id==7034205:
   hp=c.hp_packet(1000)[0]
   if hp:pulses.append([frame,hp])
  elif frame in arrivals or not active:
   v=c.values();expected=(.65 if active and id==7034206 else 1);assert abs(v['stamina']-expected)<1e-6
   assert all(abs(a-b)<1e-6 for a,b in zip(v['defense'],[1]+[1.2 if active and id==7034208 else 1]*4))
 assert abs(nodes[-1]['frame']-(max(hits)+life)*fps)<=4,(id,fps,hits,nodes)
 if id==7034205:
  assert pulses[0]==[0,20] and all(v==20 for _,v in pulses)
  assert all(abs(b[0]-a[0]-.5*fps)<=1 for a,b in zip(pulses,pulses[1:]))
 timelines.append(dict(id=id,fps=fps,hits=hits,nodes=nodes,pulses=pulses));stubs.update(c.stubs)


checks={k:[]for k in ('heal','stamina','extension')}
for maximum,repeats in itertools.product((1,99,100,199,200,999,1000,2345,9999),(1,3)):
 c=Recipient();c.u.mem_write(OBJ+0x6074,b'\1')
 for _ in range(repeats):c.place(7034205)
 c.qualify();c.update(1/60);v=c.hp_packet(maximum)[0];assert v==10+maximum//100,(maximum,v)
 stubs.update(c.stubs)
 checks['heal'].append(dict(maximum=maximum,repeats=repeats,heal=v))
for roots,cost,mask,delta in itertools.product(([],[7034206],[7034206]*3,[6850600],[7034206,6850600],[7034206,6850600,6850601,6850602]),(10,31,100,101),(0,1),(-1,0)):
 c=Cost(roots);rate=c.rate();expect=expected_rate([id for n,id in enumerate(roots)if id!=7034206 or n==roots.index(id)])
 assert rate==expect,(roots,rate,expect)
 id=1000;r=assets['tables']['EquipParamWeapon'][str(id)];v=c.cost(cost,id,r['throwAtkRate']+delta,mask);expected=int(f32(f32(f32(f32(cost)*rate)*(r['staminaConsumptionRate'] if mask else 1))*(1.5 if delta<0 else 1)))
 assert v==expected,(roots,cost,mask,delta,v,expected)
 stubs.update(c.stubs)
 checks['stamina'].append(dict(roots=roots,cost=cost,mask=mask,delta=delta,rate=rate,result=v))
for id,extension in itertools.product(fields,([], [7006400],[8330500],[8330500]*3,[7006400,8330500])):
 c=Recipient();c.u.mem_write(OBJ+0x6074,b'\6' if id==7034208 else b'\1')
 for root in extension:c.grant(root)
 c.qualify();c.update(0);c.place(id);c.qualify();c.update(1);node=next(n for n in c.nodes()if n['id']==id)
 multiplier=(1+(.5 if 7006400 in extension else 0)+extension.count(8330500)) if id==7034206 else 1
 assert abs(node['lifetime']-(ts['SpEffectParam'][str(id)]['effectEndurance']-1/multiplier))<1e-5
 stubs.update(c.stubs)
 checks['extension'].append(dict(id=id,roots=extension,multiplier=multiplier,node=node))


filter_checks=[]
for id,(bullet,attack) in fields.items():
 c=Filter(attack);p=OBJ+0xa000;c.q(p+8,OBJ+0xa800);c.q(p+0x30,0x10000001)
 for off in (0x28,0x1ec):c.u.mem_write(p+off,struct.pack('<i',-1))
 c.u.mem_write(p+0x78,struct.pack('<ii',attack,1));c.invoke(0x535a60,[p],{UC_X86_REG_XMM1:1/60})
 value=struct.unpack('<I',c.u.mem_read(p+0x28,4))[0];self_target=ts['AtkParam_Pc'][str(attack)]['selfTarget'];assert value>>26==(0 if self_target else 1)
 filter_checks.append(dict(id=id,bullet=bullet,attack=attack,selfTarget=bool(self_target),excludedSelfMask=value>>26))


connected_checks=[]
for launch in launches:
 id=7034205+(2531,2533,2538).index(launch['tae']);id=7034208 if id==7034207 else id
 dest=6 if id==7034208 else 1
 c=Recipient();c.u.mem_write(OBJ+0x6074,bytes([dest]));delivered=[]
 for request in launch['queued']:
  behavior=ts['BehaviorParam_PC'][str(request['behavior'])];assert behavior['refType']==1
  assert behavior['refId']==fields[id][0]
  # Scene contact and spatial candidate selection are explicit fixtures.
  c.place(id);delivered.append(id)
 c.qualify();c.update(1/60);assert [n['id']for n in c.nodes()]==delivered
 values=c.values();on=bool(delivered)
 assert values['hp'][0]==(20 if on and id==7034205 else 0)
 assert abs(values['stamina']-(.65 if on and id==7034206 else 1))<1e-6
 assert all(abs(v-e)<1e-6 for v,e in zip(values['defense'],[1]+[1.2 if on and id==7034208 else 1]*4))
 connected_checks.append(dict(id=id,tae=launch['tae'],copies=launch['copies'],active=launch['active'],impact=delivered,values=values))



checks.update(launch=launches, recipient=receiver_checks, timing=timelines,
              filter=filter_checks, connected=connected_checks)
assert {key: len(rows) for key, rows in checks.items()} == dict(
    heal=18, stamina=96, extension=15, launch=18, recipient=36,
    timing=45, filter=3, connected=18,
)
a.output.write_text(json.dumps(dict(
    schema=1, effects=[7034200, 7034201], root=9200006,
    exeSha256=sha(x.raw), regulationSha256=x.x['hashes']['regulation.bin'],
    paramSha256=sha(x.param), paramHashes=param_hashes, weaponSha256=sha(weapon_raw),
    coreEvidenceSha256=sha(core_path.read_bytes()),
    animationBundleSha256=anims['bundles'][0]['sha256'], fieldPaths=field_paths,
    native=dict(launch='40CD80 → 668B30 → 3975D0 → 384340 → 383ED0 → 384BC0',
                impact='43BE60 → 3C80A0', filter='535A60..535BF9',
                recovery='506EC0', stamina='668730 → 5066A0', incoming='503800'),
    checks=checks, gameplayVerified=False, stubs=sorted(stubs | {
        'Type 2 is supplied from the selected native TAE event at an explicit active/inactive window. State 2047 is explicitly supplied by its actual maintenance leaf.',
        'Actor vtable, attachment transform, hand and resource identity are fixtures. Native request assembly stops at 4B77C0. Projectile allocation, geometry, network and collision dispatch are not replayed.',
        'Projectile requests are bridged to actual Bullet/AtkParam IDs and explicitly delivered as hits to a separate recipient. Final resource and damage writes remain outside the probe.',
    }),
), ensure_ascii=False, indent=2) + '\n')
print('PASS TOTAL', sum(map(len, checks.values())))
