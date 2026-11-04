"""Trace Scholar ailment amplification from animation to hit and native resources.

Actual TAE gates, parameter lookups, hit receipt, link removal, timers and HP/FP
aggregation execute pinned game instructions. Collision arrivals, actor identity,
resource maxima and onset rows are explicit fixtures; no full gameplay is run.
"""
import argparse,json,struct,itertools,math
from pathlib import Path
from native_effect_runtime import *
from native_ailment_runtime import Ailment
from native_animation_runtime import NativeTae
from effect_behavior_graph import BehaviorGraph
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','assets','systems','animations','behavior','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted)
raws={name:a.extracted.with_suffix('.'+name+'.param').read_bytes() for name in ('AtkParam_Pc','BehaviorParam_PC','Bullet')}
attacks=Inputs.table(raws['AtkParam_Pc'],0x1d0);behaviors=Inputs.table(raws['BehaviorParam_PC'],0x30);bullets=Inputs.table(raws['Bullet'],0x100)
weaponraw=a.assets.with_suffix('.EquipParamWeapon.param').read_bytes();weapons=Inputs.table(weaponraw,0x298)
commonraw=a.systems.with_suffix('.PlayerCommonParam.param').read_bytes();off=struct.unpack_from('<Q',commonraw,0x48)[0];common=commonraw[off:]
for path in (a.assets,a.systems):assert json.loads(path.read_text())['hashes']['regulation.bin']==x.x['hashes']['regulation.bin']
animations=json.loads(a.animations.read_text());track=next(t for b in animations['bundles'] for t in b['taes'] if t['ID']==2908)
taeraw=Path(str(a.animations)+'.2908.tae').read_bytes()
graph=BehaviorGraph(a.behavior);state=graph.state('JointChainStart');assert state['animation']=='a908_680000'
root,leaf=7036700,7036701
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

class Dispatch(Chain):
    def __init__(self):
        super().__init__(x)
        self.requests, self.emissions, self.frame = [], [], 0
        # Real Behavior resolver at +328; the other virtuals supply a synthetic
        # equipped weapon / owner identity. No state predicate is substituted.
        for off, ptr in [(0x118, STOP + 0x201), (0x190, STOP + 0x200), (0x260, STOP + 0x200),
                         (0x328, BASE + 0x668b30), (0x320, STOP + 0x201),
                         (0x250, STOP + 0x202), (0x28, STOP + 0x201), (0x178, STOP + 0x200)]:
            self.q(OBJ + 0x6200 + off, ptr)
        self.q(OBJ + 0x6190, OBJ)

    def hook(self, u, address, size, user):
        pc = address - BASE
        def finish(value=0):
            u.reg_write(UC_X86_REG_RAX, value)
            sp = u.reg_read(UC_X86_REG_RSP)
            u.reg_write(UC_X86_REG_RIP, struct.unpack('<Q', u.mem_read(sp, 8))[0])
            u.reg_write(UC_X86_REG_RSP, sp + 8)
        if address in (STOP + 0x200, STOP + 0x201, STOP + 0x202):
            self.stubs.add('synthetic player virtuals and equipped weapon 1000')
            finish({STOP + 0x200: 0, STOP + 0x201: 1, STOP + 0x202: 1000}[address])
        elif pc in (0x4d1b20, 0x3d4180, 0x3d4c10, 0xea9a60, 0xea76f0, 0x66b2d0, 0x27d0640):
            self.stubs.add(hex(pc) + ' isolated actor context / hand identity / empty animation reference list')
            finish()
        elif pc == 0x3ced90:
            self.stubs.add('3CED90 isolated actor context')
            finish(OBJ + 0xd000)
        elif pc == 0xea7fc0:
            self.stubs.add('EA7FC0 actual equipped-weapon row lookup')
            id = u.reg_read(UC_X86_REG_RDX) & 0xffffffff
            u.mem_write(OBJ + 0xb000, weapons[id])
            u.mem_write(u.reg_read(UC_X86_REG_RCX), struct.pack('<IIQ', id, 0, OBJ + 0xb000))
            finish()
        elif pc == 0xe6fcb0:
            self.stubs.add('E6FCB0 actual Behavior row lookup')
            id = u.reg_read(UC_X86_REG_RDX) & 0xffffffff
            assert id in (700000400,700000401)
            u.mem_write(OBJ + 0xb800, behaviors[id])
            self.q(u.reg_read(UC_X86_REG_RCX) + 8, OBJ + 0xb800)
            finish()
        elif pc == 0x3975d0:
            self.stubs.add('3975D0 Behavior request recorder; active/stop and conditional-state gates are native')
            payload = bytes(u.mem_read(u.reg_read(UC_X86_REG_R9), 18))
            self.requests.append(dict(behavior=u.reg_read(UC_X86_REG_RDX),
                                      active=bool(payload[16]), instant=bool(payload[17]), payload=payload.hex()))
            finish(1)
        else:
            super().hook(u, address, size, user)

class Emitter(Chain):
 def __init__(self):super().__init__(x);self.frame=0;self.shots=[]
 def hook(self,u,address,size,user):
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP)
   u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  pc=address-BASE
  if pc==0xe87800:
   assert u.reg_read(UC_X86_REG_RDX)&0xffffffff==30908011
   self.stubs.add('E87800 actual Scholar ailment Bullet lookup')
   u.mem_write(OBJ+0xe900,bullets[30908011]);ptr=u.reg_read(UC_X86_REG_RCX)
   u.mem_write(ptr,struct.pack('<QI',OBJ+0xe900,30908011));ret(ptr)
  elif pc==0x347700:
   self.stubs.add('347700 successful projectile recorder, without scene collision')
   self.shots.append(self.frame);ret(1)
  else:super().hook(u,address,size,user)

TSOURCE=OBJ+0x61000;H=OBJ+0x62000;N=OBJ+0x62100
R=OBJ+0x63000;L=OBJ+0x63100;E=OBJ+0x63200;EVENT=OBJ+0x64000;ALLOC=OBJ+0x65000;VT=OBJ+0x65100;ROW=OBJ+0x66000
class Tether(Actor):
 def __init__(self,reason=0,index=2):
  super().__init__();self.u.mem_map(OBJ+0x60000,0x20000);self.freed=[];self.newptr=OBJ+0x68000
  self.u.mem_write(ROW,common);self.u.mem_write(EVENT,struct.pack('<IIBBB',0x1234,0x55,index,0,reason))
  key=self.invoke(0x4e7d50,[EVENT])
  self.q(C+0x30,ALLOC);self.q(C+0x38,H);self.q(C+0x40,1)
  for d in (0,8,0x10):self.q(H+d,N);self.q(N+d,H)
  self.u.mem_write(H+0x18,b'\x01\x01');self.u.mem_write(N+0x18,b'\x01\x00');self.q(N+0x20,key)
  self.u.mem_write(N+0x28,bytes(self.u.mem_read(EVENT,8)))
  self.q(OBJ+0xf000+0x1b0,R);self.q(R+0x10,ALLOC);self.q(R+0x18,L);self.q(R+0x20,1)
  self.q(L,E);self.q(L+8,E);self.q(E,L);self.q(E+8,L);self.u.mem_write(E+0x10,struct.pack('<i',index))
  self.stubs.add('explicit one-target source map and recipient link list; original detach/rejoin execute unchanged');self.q(ALLOC,VT);self.q(VT+0x68,STOP+0x500);self.q(VT+0x50,STOP+0x501)
 def hook(self,u,address,size,user):
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  pc=address-BASE
  if pc==0x42c120:
   self.stubs.add('42C120 explicit source actor identity');assert u.reg_read(UC_X86_REG_RCX)==C;ret(TSOURCE)
  elif pc==0x519140:self.stubs.add('519140 explicit network-handle recipient lookup');ret(OBJ+0x6000)
  elif pc==0xe81650:
   self.stubs.add('E81650 actual PlayerCommon row lookup');wrapper=u.reg_read(UC_X86_REG_RCX);self.q(wrapper,ROW);ret(wrapper)
  elif address==STOP+0x500:self.freed.append(u.reg_read(UC_X86_REG_RDX));ret()
  elif address==STOP+0x501:
   size=u.reg_read(UC_X86_REG_RDX);assert size in (0x18,0x30),size
   self.stubs.add('tether map/list allocator interface with exact 48/24-byte requests; native insert/erase maintained');self.newptr+=0x100;ret(self.newptr)
  else:super().hook(u,address,size,user)

checks={k:[] for k in ('dispatch','projectile','targets','damage','buildup','unlink','refresh','late')};stubs=set()
def record(key,c,**row):checks[key].append(row);stubs.update(c.stubs)
def step(c,fps=60):c.qualify();c.update(1/fps)
def active(c,id):return [n for n in c.nodes() if n['id']==id and not n['flags']&0x800c0003]
f32=lambda v:struct.unpack('<f',struct.pack('<f',v))[0]
for id in (7036700,7036701):
 assert x.x['tables']['AttachEffectParam'][str(id)]['passiveSpEffectId_1']==root
 assert x.x['tables']['AttachEffectParam'][str(id)]['exclusivityId']==-1
r=x.spells[str(leaf)]
fields=('poisonDamageRate','diseaseDamageRate','bloodDamageRate','freezeDamageRate','sleepDamageRate','madnessDamageRate')
assert all(r[k]==130 for k in fields)
assert r['spCategory']==20 and r['effectEndurance']==20 and r['stateInfo']==0
assert all(r['invocationConditionsStateChange'+str(i)]==0 for i in (1,2,3))
assert x.spells[str(root)]['stateInfo']==2028 and x.spells[str(root)]['spCategory']==20
b=x.x['tables']['BehaviorParam_PC']['700000401'];bullet=x.x['tables']['Bullet']['30908011'];attack=x.x['tables']['AtkParam_Pc']['700000410']
assert b['refType']==1 and b['refId']==30908011
assert bullet['atkId_Bullet']==700000410 and bullet['spEffectId0']==leaf
assert bullet['hitRadius']==30 and bullet['numShoot']==1 and bullet['isEndlessHit']==0
assert bullet['HitBulletID']==bullet['intervalCreateBulletId']==-1 and math.isclose(bullet['life'],.1,abs_tol=1e-7)
assert [attack[k] for k in ('selfTarget','friendlyTarget','opposeTarget','disableHitSpEffect','subCategory1')]==[0,0,1,0,123]
events=[dict(animation=an['ID'],**e) for an in track['animations'] if an['ID']==680000 for e in an['events'] if e['Type']==2 and struct.unpack_from('<i',bytes.fromhex(e['hex']),8)[0] in (7400,7401)]
assert len(events)==2 and [e['index'] for e in events]==[4,61]
assert all(math.isclose(e['StartTime'],2.5,abs_tol=1e-7) for e in events)
for copies,enabled in itertools.product((0,1,3),(0,1)):
 c=Dispatch()
 for _ in range(copies):c.insert(root)
 c.qualify();c.update(0);loader=NativeTae(c,taeraw,track['sha256']);assert loader.id==2908
 ctx=OBJ+0xd100;c.u.mem_write(ctx,bytes(0x40));found=[]
 while c.invoke(0x27d0400,[loader.animations[680000],ctx]):
  if struct.unpack('<I',c.u.mem_read(ctx,4))[0]!=2:continue
  ptr=struct.unpack('<Q',c.u.mem_read(ctx+8,8))[0];raw=bytes(c.u.mem_read(ptr,32))
  match=next((e for e in events if bytes.fromhex(e['hex'])==raw),None)
  if match is None:continue
  c.q(OBJ+0x8018,OBJ+0x6000);c.u.mem_write(ctx+0x18,bytes([enabled]));c.requests.clear();c.invoke(0x40cd80,[OBJ+0x8000,ctx])
  judge=struct.unpack_from('<i',raw,8)[0];expected=bool(enabled and (copies or judge==7400))
  assert len(c.requests)==expected,(copies,enabled,judge,c.requests)
  if expected:assert c.requests[0]['behavior']==700000400+(judge-7400)
  found.append(judge);record('dispatch',c,copies=copies,enabled=enabled,event=match,requests=c.requests[:])
 assert found==[7400,7401]
for fps in (30,60,120):
 c=Emitter();slot=OBJ+0x4000;c.u.mem_write(slot+0x329,b'\1');c.u.mem_write(slot+0x334,struct.pack('<I',30908011));c.u.mem_write(slot+0x494,b'\1')
 for frame in range(fps):c.frame=frame;c.invoke(0x343280,[slot],{UC_X86_REG_XMM1:1/fps})
 assert c.shots==[0];record('projectile',c,fps=fps,shots=c.shots)
for recipient in range(10):
 c=Hit();c.u.mem_write(OBJ+0x6074,bytes([recipient]));c.hit(leaf,700000410);step(c)
 accepted=bool(active(c,leaf));assert accepted==(recipient in (6,7,8,9)),(recipient,accepted,c.nodes())
 record('targets',c,sourceType=1,recipientType=recipient,accepted=accepted)
print('PASS animation, emission and target selection',flush=True)

# The onset effects below are real rows supplied as already-triggered effects;
# HP/FP aggregation is native. Buildup/onset input is checked separately below.
ailments={0:834,1:3128,2:870,4:829,5:1745,6:920}
for copies,id,maximum in itertools.product((0,1,3),ailments.values(),(101,1000,10000)):
 c=Hit()
 for _ in range(copies):c.hit(leaf,700000410)
 c.qualify();c.update(0);c.insert(id);c.qualify();c.update(0)
 hp=c.hp_packet(maximum);fp=c.fp(maximum);row=x.spells[str(id)]
 rate=f32(1.3) if copies else 1
 percent=f32(row['changeHpRate']*rate);flat=f32(row['changeHpPoint']*rate)
 expected=math.trunc(f32(-f32(f32(maximum*percent)*f32(.01))-flat))
 mana=math.trunc(f32(-f32(f32(maximum*row['changeMpRate'])*f32(.01))-row['changeMpPoint']))
 assert hp[0]==expected and fp==[mana,0],(copies,id,maximum,hp,fp,expected,mana)
 assert len(active(c,leaf))==bool(copies)
 record('damage',c,copies=copies,onset=id,maximum=maximum,hp=hp,fp=fp)
for copies,(kind,id) in itertools.product((0,1,3),ailments.items()):
 c=Hit(kind=kind,maximum=500)
 for _ in range(copies):c.hit(leaf,700000410)
 c.qualify();c.update(0);rejected=c.apply(id);remaining=c.remaining()
 attack_field={0:'poizonAttackPower',1:'diseaseAttackPower',2:'bloodAttackPower',4:'freezeAttackPower',5:'sleepAttackPower',6:'madnessAttackPower'}[kind]
 assert rejected and remaining==500-x.spells[str(id)][attack_field],(copies,kind,id,rejected,remaining)
 record('buildup',c,copies=copies,kind=kind,effect=id,incoming=x.spells[str(id)][attack_field],remaining=remaining)
print('PASS native HP, FP and accumulation',flush=True)

# Real detach notifications clear the link marker; the ailment amplification
# stays active and its independent 20-second clock continues.
for marker,reason,fps in itertools.product((708100,708110),(0,1),(30,60,120)):
 c=Tether(reason);c.grant(marker);c.grant(leaf)
 for _ in range(2*fps):step(c,fps)
 before=active(c,leaf)[0]['lifetime'];c.grants.clear();c.invoke(0x4507c0,[C,EVENT]);removal=c.grants[:]
 for _ in range(3*fps):step(c,fps)
 after=active(c,leaf)[0]['lifetime'];linked=c.invoke(0x508e20,[OBJ,2222])&255
 assert not linked and abs(after-15)<3/fps and abs(before-after-3)<3/fps,(marker,reason,before,after,linked)
 record('unlink',c,marker=marker,reason=reason,fps=fps,before=before,after=after,linked=bool(linked),removal=removal)
for copies,refresh,fps in itertools.product((1,3),(False,True),(30,60,120)):
 c=Hit()
 for _ in range(copies):c.hit(leaf,700000410)
 c.qualify();c.update(0);expired=None;refreshed=None
 for frame in range(1,27*fps):
  if refresh and frame==5*fps:
   c.hit(leaf,700000410);refreshed=next(n['lifetime'] for n in c.nodes() if n['id']==leaf)
  step(c,fps)
  if not active(c,leaf):expired=frame;break
 # Float timer crossing, expiry marking and next-frame qualification can
 # retain the node for up to three simulation frames past its nominal life.
 assert expired is not None and abs(expired/fps-(25 if refresh else 20))<=4/fps,(copies,refresh,fps,expired,c.nodes())
 if refresh:assert abs(refreshed-20)<1e-5
 record('refresh',c,copies=copies,refresh=refresh,fps=fps,expiryFrame=expired,refreshLifetime=refreshed)
for fps in (30,60,120):
 c=Hit();c.insert(834);pulses=[]
 for frame in range(24*fps):
  if frame==2*fps:c.hit(leaf,700000410)
  step(c,fps);hp=c.hp_packet(1000)[0]
  if hp:pulses.append(dict(frame=frame,hp=hp))
 assert all(p['hp']==(-14 if 2*fps<=p['frame']<22*fps else -11) for p in pulses),pulses
 assert {p['hp'] for p in pulses}=={-11,-14}
 record('late',c,fps=fps,debuffArrivalSeconds=2,pulses=pulses)
output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),
 assetHashes={**{k:sha(v) for k,v in raws.items()},'weapon':sha(weaponraw),'common':sha(commonraw),'tae':sha(taeraw),'behaviorGraph':graph.metadata['hkxSha256']},
 root=root,leaf=leaf,effects=[7036700,7036701],state=state,events=events,
 rows={str(id):{k:x.spells[str(id)][k] for k in ('stateInfo','spCategory','effectEndurance','motionInterval','invocationConditionsStateChange1','invocationConditionsStateChange2','invocationConditionsStateChange3','changeHpRate','changeHpPoint','changeMpRate','changeMpPoint',*fields)} for id in (root,leaf,*ailments.values())},
 bullet={k:bullet[k] for k in ('atkId_Bullet','spEffectId0','life','hitRadius','numShoot','isEndlessHit')},
 checks=checks,stubs=sorted(stubs|{'actual onset rows are explicitly inserted for isolated HP/FP amounts; buildup input is separately exercised',
 '43BE60 argument 5 is 1: physical HP damage is skipped while effect delivery runs',
 'collision arrivals, actor/team identity and projectile ownership supplied; complete target acquisition, geometry, resource setters and multiplayer transport not executed'}),
 native=dict(animation='27D0F10 / 27D0400 → 40CD80 → 668B30',hit='43BE60 → 3C80A0',buildup='42D110',unlink='4507C0 → 44F180 / 452870 / 44B800 → 3C7FD0',hp='506EC0 → 50B860',fp='507460'),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(map(len,checks.values())),'native Scholar ailment checks',{k:len(v) for k,v in checks.items()},flush=True)
