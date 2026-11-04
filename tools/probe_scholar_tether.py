"""Trace Scholar tether DOT through animation, detach/rejoin and native HP packets.

Actual TAE/PARAM rows, condition gates, map/list updates, self-grants and timers
run unchanged. Actor/handle identities, allocator storage, collision arrivals and
resource maxima are explicit fixtures; this is not full gameplay validation.
"""
import argparse
import itertools
import json
import math
import struct
from pathlib import Path
from native_effect_runtime import BASE, OBJ, STOP, Chain, Inputs, sha
from native_ailment_runtime import Ailment
from native_animation_runtime import NativeTae
from unicorn.x86_const import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','assets','animations','common','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted)
assets=json.loads(a.assets.read_text());animations=json.loads(a.animations.read_text());systems=json.loads(a.common.read_text())
assert assets['hashes']['regulation.bin']==systems['hashes']['regulation.bin']==x.x['hashes']['regulation.bin']
behaviorraw=a.extracted.with_suffix('.BehaviorParam_PC.param').read_bytes();behaviors=Inputs.table(behaviorraw,0x30)
bulletraw=a.extracted.with_suffix('.Bullet.param').read_bytes();bullets=Inputs.table(bulletraw,0x100)
weaponraw=a.assets.with_suffix('.EquipParamWeapon.param').read_bytes();weapons=Inputs.table(weaponraw,0x298)
commonraw=a.common.with_suffix('.PlayerCommonParam.param').read_bytes();off=struct.unpack_from('<Q',commonraw,0x48)[0];common=commonraw[off:]
assert [struct.unpack_from('<i',common,i)[0] for i in (0x1c8,0x1cc,0x1d0,0x1d4,0x1d8)]==[708100,708101,708110,708120,708121]
tae=next(t for b in animations['bundles'] for t in b['taes'] if t['ID']==2908)
taeraw=Path(str(a.animations)+'.2908.tae').read_bytes();assert sha(taeraw)==tae['sha256']
events=[dict(animation=an['ID'],**e) for an in tae['animations'] for e in an['events'] if e['Type']==2 and struct.unpack_from('<H',bytes.fromhex(e['hex']),14)[0]==2061]
assert len(events)==1 and events[0]['animation']==680000 and struct.unpack_from('<i',bytes.fromhex(events[0]['hex']),8)[0]==7410
C=OBJ+0x60000;SOURCE=OBJ+0x61000;H=OBJ+0x62000;N=OBJ+0x62100
R=OBJ+0x63000;L=OBJ+0x63100;E=OBJ+0x63200;EVENT=OBJ+0x64000;ALLOC=OBJ+0x65000;VT=OBJ+0x65100;ROW=OBJ+0x66000
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
            assert id == 700000410
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
   self.stubs.add('42C120 explicit source actor identity');assert u.reg_read(UC_X86_REG_RCX)==C;ret(SOURCE)
  elif pc==0x519140:self.stubs.add('519140 explicit network-handle recipient lookup');ret(OBJ+0x6000)
  elif pc==0xe81650:
   self.stubs.add('E81650 actual PlayerCommon row lookup');wrapper=u.reg_read(UC_X86_REG_RCX);self.q(wrapper,ROW);ret(wrapper)
  elif address==STOP+0x500:self.freed.append(u.reg_read(UC_X86_REG_RDX));ret()
  elif address==STOP+0x501:
   size=u.reg_read(UC_X86_REG_RDX);assert size in (0x18,0x30),size
   self.stubs.add('tether map/list allocator interface with exact 48/24-byte requests; native insert/erase maintained');self.newptr+=0x100;ret(self.newptr)
  else:super().hook(u,address,size,user)
class Emitter(Chain):
 def __init__(self):super().__init__(x);self.frame=0;self.shots=[]
 def hook(self,u,address,size,user):
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP)
   u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  pc=address-BASE
  if pc==0xe87800:
   assert u.reg_read(UC_X86_REG_RDX)&0xffffffff==30908110
   self.stubs.add('E87800 actual tether DOT Bullet lookup')
   u.mem_write(OBJ+0xe900,bullets[30908110]);ptr=u.reg_read(UC_X86_REG_RCX)
   u.mem_write(ptr,struct.pack('<QI',OBJ+0xe900,30908110));ret(ptr)
  elif pc==0x347700:
   self.stubs.add('347700 successful projectile recorder, without scene collision')
   self.shots.append(self.frame);ret(1)
  else:super().hook(u,address,size,user)

root,leaf=7036400,7036401
attach=x.x['tables']['AttachEffectParam'][str(root)]
assert attach['passiveSpEffectId_1']==root and attach['exclusivityId']==-1
assert x.spells[str(root)]['spCategory']==20 and x.spells[str(root)]['stateInfo']==2061
r=x.spells[str(leaf)]
assert r['changeHpPoint']==15 and r['changeHpRate']==0 and r['effectEndurance']==20 and r['motionInterval']==1
assert r['spCategory']==10 and r['stateInfo']==0 and r['invocationConditionsStateChange1']==2222
assert r['invocationConditionsStateChange2']==r['invocationConditionsStateChange3']==0
assert r['cycleOccurrenceSpEffectId']==r['replaceSpEffectId']==-1
for marker in (708100,708110):assert x.spells[str(marker)]['stateInfo']==2222 and x.spells[str(marker)]['spCategory']==205
behavior=x.x['tables']['BehaviorParam_PC']['700000410'];bullet=x.x['tables']['Bullet']['30908110'];attack=x.x['tables']['AtkParam_Pc']['700000410']
assert behavior['refType']==1 and behavior['refId']==30908110
assert bullet['atkId_Bullet']==700000410 and bullet['spEffectId0']==leaf and bullet['hitRadius']==30 and bullet['numShoot']==1
assert [attack[k] for k in ('selfTarget','friendlyTarget','opposeTarget','disableHitSpEffect')]==[0,0,1,0]
checks=dict(dispatch=[],projectile=[],damage=[],unlink=[],late=[],repeat=[]);stubs=set()
def record(key,c,**row):checks[key].append(row);stubs.update(c.stubs)
def step(c,fps):c.qualify();c.update(1/fps)
def hp(c,maximum=10000):return c.hp_packet(maximum)
def dots(c):return [n for n in c.nodes() if n['id']==leaf]
def counts(c):return [struct.unpack('<Q',c.u.mem_read(addr,8))[0] for addr in (C+0x40,R+0x20)]
for copies,active in itertools.product(range(4),(0,1)):
 c=Dispatch()
 for _ in range(copies):c.insert(root)
 c.qualify();c.update(0)
 loader=NativeTae(c,taeraw,tae['sha256']);assert loader.id==2908 and loader.bank==255
 ctx=OBJ+0xd100;c.u.mem_write(ctx,bytes(0x40));found=False
 for _ in range(1000):
  if not c.invoke(0x27d0400,[loader.animations[680000],ctx]):break
  if struct.unpack('<I',c.u.mem_read(ctx,4))[0]!=2:continue
  payload=struct.unpack('<Q',c.u.mem_read(ctx+8,8))[0]
  event=bytes(c.u.mem_read(payload,len(bytes.fromhex(events[0]['hex']))))
  if event!=bytes.fromhex(events[0]['hex']):continue
  c.q(OBJ+0x8018,OBJ+0x6000);c.u.mem_write(ctx+0x18,bytes([active]));c.invoke(0x40cd80,[OBJ+0x8000,ctx]);found=True;break
 assert found and len(c.requests)==int(bool(copies) and bool(active))
 assert sum(n['id']==root for n in c.nodes())==int(bool(copies))
 record('dispatch',c,copies=copies,active=active,requests=c.requests,nodes=c.nodes())
for fps in (30,60,120):
 c=Emitter();slot=OBJ+0x4000
 c.u.mem_write(slot+0x329,b'\1');c.u.mem_write(slot+0x334,struct.pack('<I',30908110));c.u.mem_write(slot+0x494,b'\1')
 for frame in range(fps):c.frame=frame;c.invoke(0x343280,[slot],{UC_X86_REG_XMM1:1/fps})
 assert c.shots==[0];record('projectile',c,fps=fps,shots=c.shots)
for marker,copies,maximum,fps in itertools.product((None,708100,708110),(1,3),(100,10000),(30,60,120)):
 c=Actor()
 if marker:c.grant(marker)
 for _ in range(copies):c.grant(leaf)
 hits=[]
 for frame in range(22*fps):
  step(c,fps);packet=hp(c,maximum)
  if any(packet):
   assert packet==[-15*copies,0,-15*copies,0,-15*copies,0,0]
   hits.append(dict(frame=frame,packet=packet))
 if marker:
  assert 20<=len(hits)<=21 and not dots(c)
  assert hits[0]['frame']<=2 and abs(hits[-1]['frame']/fps-(len(hits)-1))<=3/fps
 else:assert not hits and len(dots(c))==copies and all(n['lifetime']==20 for n in dots(c))
 record('damage',c,marker=marker,copies=copies,maximum=maximum,fps=fps,hits=hits,remaining=dots(c))
for marker,reason,fps in itertools.product((708100,708110),(0,1),(30,60,120)):
 c=Tether(reason);c.grant(marker);c.grant(leaf)
 for _ in range(fps):step(c,fps)
 before=dots(c)[0]['lifetime'];c.grants.clear();c.invoke(0x4507c0,[C,EVENT])
 removal=c.grants.copy();assert removal==[708120 if reason else 708121] and counts(c)==[0,0]
 assert set(c.freed)=={N,E}
 for _ in range(3*fps):step(c,fps);assert not any(hp(c))
 paused=dots(c)[0]['lifetime'];assert paused==before
 c.grants.clear();c.invoke(0x450680,[C,EVENT]);joined=c.grants.copy()
 assert joined==[708110] and counts(c)==[1,1]
 resumed=[]
 for frame in range(3*fps):
  step(c,fps);packet=hp(c)
  if any(packet):resumed.append(dict(frame=frame,packet=packet))
 assert 2<=len(resumed)<=3 and all(r['packet']==[-15,0,-15,0,-15,0,0] for r in resumed)
 after=dots(c)[0]['lifetime'];assert abs(after-(before-3))<3/fps
 record('unlink',c,marker=marker,reason=reason,fps=fps,before=before,paused=paused,after=after,unlinkEffects=removal,rejoinEffects=joined,resumed=resumed)
for marker,fps in itertools.product((708100,708110),(30,60,120)):
 c=Actor();c.grant(leaf)
 for _ in range(2*fps):step(c,fps);assert not any(hp(c))
 before=dots(c)[0]['lifetime'];assert before==20
 c.grant(marker);hits=[]
 for frame in range(2*fps):
  step(c,fps);packet=hp(c)
  if any(packet):hits.append(dict(frame=frame,packet=packet))
 assert len(hits)==2 and abs(dots(c)[0]['lifetime']-18)<3/fps
 record('late',c,marker=marker,fps=fps,waitingTime=2,before=before,after=dots(c)[0]['lifetime'],hits=hits)
for fps,gap in itertools.product((30,60,120),(5,25)):
 c=Tether();hits=[];peak=0;nodePeak=0
 for frame in range((gap+23)*fps):
  if frame in (0,gap*fps):c.invoke(0x450680,[C,EVENT]);c.grant(leaf)
  step(c,fps);packet=hp(c);peak=max(peak,-packet[0]);nodePeak=max(nodePeak,len(dots(c)))
  if any(packet):hits.append(dict(frame=frame,packet=packet))
 # Each application keeps its own pulse phase. Overlap can double the damage
 # per second without producing a single 30-point packet on the same frame.
 windowDamage=sum(-r['packet'][0] for r in hits if (gap+2)*fps<=r['frame']<(gap+4)*fps)
 assert windowDamage==(60 if gap<20 else 30) and nodePeak==(2 if gap<20 else 1),(fps,gap,peak,nodePeak,windowDamage,dots(c))
 assert not dots(c)
 record('repeat',c,fps=fps,gap=gap,peak=peak,nodePeak=nodePeak,windowSeconds=2,windowDamage=windowDamage,hits=hits,remaining=dots(c))
output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),
 commonParamSha256=sha(commonraw),taeSha256=sha(taeraw),behaviorParamSha256=sha(behaviorraw),bulletParamSha256=sha(bulletraw),weaponParamSha256=sha(weaponraw),
 root=root,leaf=leaf,markers=[708100,708110],events=events,checks=checks,
 rows={str(i):{k:x.spells[str(i)][k] for k in ('stateInfo','spCategory','categoryPriority','effectEndurance','motionInterval','changeHpPoint','changeHpRate','invocationConditionsStateChange1')} for i in (root,leaf,708100,708101,708110,708120,708121)},
 bullet={k:bullet[k] for k in ('atkId_Bullet','life','hitRadius','numShoot','spEffectId0','HitBulletID')},
 attack={k:attack[k] for k in ('selfTarget','friendlyTarget','opposeTarget','disableHitSpEffect')},
 native=dict(animation='27D0F10 / 27D0400 → 40CD80 → 668B30',projectile='343280',
 unlink='4507C0 → 44F180 / 452870 / 44B800 → 3C7FD0',rejoin='450680 → 44F230 / 44DF30 → 3C7FD0',
 update='50D060 / 5057D0 / 50ACD0',hp='506EC0'),
 stubs=sorted(stubs|{'network messages and linked recipient identity are supplied; original source map and recipient list insertion/erase are executed',
 'collision arrivals, maximum HP and unprotected recipient are supplied; final current HP write, full battle and multiplayer transport are not simulated'}),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(map(len,checks.values())),'native Scholar tether DOT scenarios')
