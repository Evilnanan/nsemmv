"""Execute Revenant ghostflame dispatch, hit-side status correction and frostbite.

Original hit reception, grant, immunity/accumulation, HP and defense consumers
run with explicit actors, neutral damage metadata and collision arrivals.
Explosion damage construction, geometry and final HP writes are not simulated.
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
for name in ('exe','extracted','assets','animations','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted)
assets=json.loads(a.assets.read_text());animations=json.loads(a.animations.read_text())
assert assets['hashes']['regulation.bin']==x.x['hashes']['regulation.bin']
assert animations['bundles'][0]['sha256']=='1410035ad79edb410fa41420ec259fcb4a1037d748c9c4a3b6ae8d1366c76d0f'
behaviorraw=a.extracted.with_suffix('.BehaviorParam_PC.param').read_bytes();behaviors=Inputs.table(behaviorraw,0x30)
bulletraw=a.extracted.with_suffix('.Bullet.param').read_bytes();bullets=Inputs.table(bulletraw,0x100)
attackraw=a.extracted.with_suffix('.AtkParam_Pc.param').read_bytes();attacks=Inputs.table(attackraw,0x1d0)
weaponraw=a.assets.with_suffix('.EquipParamWeapon.param').read_bytes();weapons=Inputs.table(weaponraw,0x298)
tae=next(t for b in animations['bundles'] for t in b['taes'] if t['ID']==2905)
taeraw=Path(str(a.animations)+'.2905.tae').read_bytes();assert sha(taeraw)==tae['sha256']
events=[dict(animation=an['ID'],**e) for an in tae['animations'] for e in an['events'] if e['Type']==2 and struct.unpack_from('<H',bytes.fromhex(e['hex']),14)[0]==2032]
assert len(events)==1 and events[0]['animation']==650000 and struct.unpack_from('<i',bytes.fromhex(events[0]['hex']),8)[0]==7281
root,leaf=7011200,1501000
attach=x.x['tables']['AttachEffectParam'][str(root)]
assert attach['passiveSpEffectId_1']==root and attach['exclusivityId']==-1
assert x.spells[str(root)]['spCategory']==20 and x.spells[str(root)]['stateInfo']==2032
r=x.spells[str(leaf)]
assert r['stateInfo']==260 and r['spCategory']==10007 and r['freezeAttackPower']==50
assert r['changeHpRate']==10 and r['changeHpPoint']==50 and r['effectEndurance']==30 and r['motionInterval']==99
assert r['cycleOccurrenceSpEffectId']==502 and x.spells['502']['changeHpRate']==x.spells['502']['changeHpPoint']==0
assert r['isUseStatusAilmentAtkPowerCorrect']==0 and not x.rows[leaf][0x259]&1
assert x.spells['7034602']['isUseStatusAilmentAtkPowerCorrect']==0 and x.spells['7500201']['isUseStatusAilmentAtkPowerCorrect']==1
assert all(math.isclose(r[k+'DamageCutRate'],1.15,rel_tol=1e-6) for k in ('neutral','slash','blow','thrust','magic','fire','thunder','dark'))
behavior=x.x['tables']['BehaviorParam_PC']['700000281'];bullet=x.x['tables']['Bullet']['30905120'];attack=x.x['tables']['AtkParam_Pc']['700000281']
assert behavior['refType']==1 and behavior['refId']==30905120
assert bullet['atkId_Bullet']==700000281 and bullet['spEffectId0']==leaf and bullet['numShoot']==1
assert bullet['hitRadius']==4 and bullet['hitRadiusMax']==10 and bullet['HitBulletID']==-1
assert attack['statusAilmentAtkPowerCorrectRate']==struct.unpack_from('<H',attacks[700000281],0x18c)[0]==0
assert [attack[k] for k in ('selfTarget','friendlyTarget','opposeTarget','disableHitSpEffect')]==[0,0,1,0]
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
            assert id == 700000281
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
   assert u.reg_read(UC_X86_REG_RDX)&0xffffffff==30905120
   self.stubs.add('E87800 actual ghostflame Bullet lookup')
   u.mem_write(OBJ+0xe900,bullets[30905120]);ptr=u.reg_read(UC_X86_REG_RCX)
   u.mem_write(ptr,struct.pack('<QI',OBJ+0xe900,30905120));ret(ptr)
  elif pc==0x347700:
   self.stubs.add('347700 successful projectile recorder, without scene collision')
   self.shots.append(self.frame);ret(1)
  else:super().hook(u,address,size,user)

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
   self.stubs.add('E6D630 actual AtkParam_Pc row lookup');assert u.reg_read(UC_X86_REG_R8)==700000281 and u.reg_read(UC_X86_REG_RDX)==1
   wrapper=u.reg_read(UC_X86_REG_RCX);u.mem_write(OBJ+0x64000,attacks[700000281]);u.mem_write(wrapper,struct.pack('<iii4xQ',700000281,0,1,OBJ+0x64000));ret()
  elif pc==0x3c80a0:
   sp=u.reg_read(UC_X86_REG_RSP);ptr=struct.unpack('<Q',u.mem_read(sp+0x30,8))[0]
   self.sent.append(dict(id=u.reg_read(UC_X86_REG_RDX)&0xffffffff,scales=list(struct.unpack('<15f',u.mem_read(ptr,60)))))
  else:super().hook(u,address,size,user)
 def hit(self,id,scale=0,extra=1,slot=5):
  self.u.mem_write(HIT,bytes(0x400))
  self.u.mem_write(HIT+0x40,struct.pack('<ii',700000281,1))
  self.u.mem_write(HIT+0x70+slot*4,struct.pack('<i',id))
  self.u.mem_write(HIT+0x188,struct.pack('<ff',scale,extra))
  self.u.mem_write(HIT+0x1a4,struct.pack('<7f',*([1]*7)))
  for off in (0x29c,0xd4,0x254):self.u.mem_write(HIT+off,struct.pack('<f',1))
  self.invoke(0x43be60,[C,SOURCE,HIT,0,1,0])

 def defense(self):
  self.u.mem_write(OBJ+0x800,bytes(0x200));self.invoke(0x503800,[OBJ,OBJ+0x500,OBJ+0x520,OBJ+0x540,OBJ+0x800])
  return list(struct.unpack('<5f',self.u.mem_read(OBJ+0x500,20)))

checks=dict(dispatch=[],projectile=[],correction=[],onset=[],damage=[],repeat=[],lifetime=[]);stubs=set()
def record(key,c,**row):checks[key].append(row);stubs.update(c.stubs)
def step(c,fps):c.qualify();c.update(1/fps)
def frozen(c):return [n for n in c.nodes() if n['id']==leaf]
for copies,active in itertools.product(range(4),(0,1)):
 c=Dispatch()
 for _ in range(copies):c.insert(root)
 c.qualify();c.update(0)
 loader=NativeTae(c,taeraw,tae['sha256']);assert loader.id==2905 and loader.bank==255
 ctx=OBJ+0xd100;c.u.mem_write(ctx,bytes(0x40));found=False
 for _ in range(1000):
  if not c.invoke(0x27d0400,[loader.animations[650000],ctx]):break
  if struct.unpack('<I',c.u.mem_read(ctx,4))[0]!=2:continue
  payload=struct.unpack('<Q',c.u.mem_read(ctx+8,8))[0]
  if bytes(c.u.mem_read(payload,len(bytes.fromhex(events[0]['hex']))))!=bytes.fromhex(events[0]['hex']):continue
  c.q(OBJ+0x8018,OBJ+0x6000);c.u.mem_write(ctx+0x18,bytes([active]));c.invoke(0x40cd80,[OBJ+0x8000,ctx]);found=True;break
 assert found and len(c.requests)==int(bool(copies) and bool(active))
 assert sum(n['id']==root for n in c.nodes())==int(bool(copies))
 record('dispatch',c,copies=copies,active=active,requests=c.requests,nodes=c.nodes())
for fps in (30,60,120):
 c=Emitter();slot=OBJ+0x4000
 c.u.mem_write(slot+0x329,b'\1');c.u.mem_write(slot+0x334,struct.pack('<I',30905120));c.u.mem_write(slot+0x494,b'\1')
 for frame in range(fps):c.frame=frame;c.invoke(0x343280,[slot],{UC_X86_REG_XMM1:1/fps})
 assert c.shots==[0];record('projectile',c,fps=fps,shots=c.shots)
# The receiving path must respect the leaf flag, even when the attack's status
# correction is zero. Controls deliberately vary supplied hit metadata; they do
# not claim to construct a complete attack or determine its final direct damage.
for id,kind,base in ((leaf,4,50),(7034602,0,300),(7500201,0,70)):
 for scale,extra,slot in itertools.product((0,.5,1,2),(.5,1),(0,4,5,22)):
  c=Hit(kind,1000);c.hit(id,scale,extra,slot);c.qualify();c.update(0)
  corrected=scale*(extra if slot<5 else 1) if id==7500201 else 1
  amount=int(base*corrected)
  assert c.remaining()==1000-amount and not c.nodes(),(id,scale,extra,slot,c.remaining(),c.nodes())
  assert len(c.sent)==1 and c.sent[0]['scales'][14]==corrected
  record('correction',c,effect=id,scale=scale,extra=extra,slot=slot,appliedScale=corrected,amount=amount,remaining=c.remaining())
for immune,resistance in itertools.product((False,True),(1,49,50,51,100,500)):
 c=Hit(4,resistance)
 if immune:c.grant(9642)
 c.qualify();c.update(0);c.sent.clear();c.hit(leaf);c.qualify();c.update(0)
 expected=not immune and resistance<=50
 assert bool(frozen(c))==expected
 assert c.remaining()==(resistance if immune or expected else resistance-50)
 record('onset',c,immune=immune,resistance=resistance,triggered=expected,remaining=c.remaining(),nodes=c.nodes())
for maximum,copies in itertools.product((99,100,137,1000,10000,12345,100000),(1,2,3)):
 c=Hit(4,50)
 for _ in range(copies):c.hit(leaf)
 c.qualify();c.update(0);packet=c.hp_packet(maximum);rates=c.defense()
 assert packet==[-(int(maximum*.1)+50),0,-(int(maximum*.1)+50),0,-(int(maximum*.1)+50),8,0],(maximum,packet)
 assert all(math.isclose(v,1.15,rel_tol=1e-6) for v in rates) and len(frozen(c))==1
 record('damage',c,maximum=maximum,copies=copies,packet=packet,rates=rates,nodes=c.nodes())
for elapsed in (1,5,15,29):
 c=Hit(4,50);c.hit(leaf);step(c,60)
 for _ in range(elapsed*60):step(c,60)
 before=frozen(c)[0]['lifetime'];c.hit(leaf)
 assert len(frozen(c))==1 and frozen(c)[0]['lifetime']==before
 step(c,60);assert c.hp_packet(10000)[0]==0
 record('repeat',c,elapsed=elapsed,before=before,after=frozen(c)[0]['lifetime'])
for fps in (30,60,120):
 c=Hit(4,50);c.hit(leaf);c.qualify();c.update(0);hits=[];lastActive=0
 for frame in range(32*fps):
  packet=c.hp_packet(10000)
  if packet[0]:hits.append(dict(frame=frame,packet=packet))
  rates=c.defense()
  if frozen(c):
   assert all(math.isclose(v,1.15,rel_tol=1e-6) for v in rates);lastActive=frame
  else:assert rates==[1]*5
  step(c,fps)
 assert len(hits)==1 and hits[0]['frame']==0 and hits[0]['packet'][0]==-1050
 assert abs(lastActive/fps-30)<=3.01/fps and not c.nodes()
 record('lifetime',c,fps=fps,lastActiveFrame=lastActive,hits=hits,remaining=c.nodes())
output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),
 behaviorParamSha256=sha(behaviorraw),bulletParamSha256=sha(bulletraw),attackParamSha256=sha(attackraw),weaponParamSha256=sha(weaponraw),
 animationBundleSha256=animations['bundles'][0]['sha256'],taeSha256=sha(taeraw),events=events,
 root=root,leaf=leaf,rows={str(i):x.spells[str(i)] for i in (root,leaf,502,7034602,7500201)},
 binding=dict(behavior=behavior,bullet=bullet,attack=attack),checks=checks,
 native=dict(relocate='27D0F10',iterate='27D0400',type2='40CD80',behavior='668B30',emitter='343280',hit='43BE60',
   grant='3C80A0 → 3DB410',target='50C6C0 → 52CC60',insert='50D060',status='42D110',immunity='509790',
   accumulation='42CD70',remove='505280',qualify='5057D0',update='50ACD0',hp='506EC0',defense='503800'),
 stubs=sorted(stubs|{'explicit source/recipient actor identities, opposing relation, empty attacker effect list and neutral notification/network objects',
   'hit effects and metadata are fixtures; original 43BE60 reception uses zero direct HP damage with the HP-change input disabled',
   'effect slots and status factors are deliberately varied; complete projectile-to-hit construction, geometry, direct explosion damage and final HP writes are not simulated'}),
 gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(map(len,checks.values())),'native Revenant ghostflame cases')
