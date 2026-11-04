"""Trace Revenant summon enchantment, attack values and frost payload.

Native TAE dispatch, successful-emission self grant, attack getters, effect
replacement and frost processing run in isolation. Attack/hand contexts and
payload arrivals are fixtures, not a complete weapon collision simulation.
"""
import argparse,json,struct,itertools,math
from pathlib import Path
from native_effect_runtime import *
from native_ailment_runtime import Ailment
from native_animation_runtime import NativeTae
from effect_behavior_graph import BehaviorGraph
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','assets','animations','behavior','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted)
raws={name:a.extracted.with_suffix('.'+name+'.param').read_bytes() for name in ('AtkParam_Pc','BehaviorParam_PC','Bullet')}
attacks=Inputs.table(raws['AtkParam_Pc'],0x1d0);behaviors=Inputs.table(raws['BehaviorParam_PC'],0x30);bullets=Inputs.table(raws['Bullet'],0x100)
weaponraw=a.assets.with_suffix('.EquipParamWeapon.param').read_bytes();weapons=Inputs.table(weaponraw,0x298)
assert json.loads(a.assets.read_text())['hashes']['regulation.bin']==x.x['hashes']['regulation.bin']
animations=json.loads(a.animations.read_text());track=next(t for b in animations['bundles'] for t in b['taes'] if t['ID']==2905)
taeraw=Path(str(a.animations)+'.2905.tae').read_bytes();graph=BehaviorGraph(a.behavior)
root,enchant,frost=7220200,7220201,1809
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
 def __init__(self,success=True):super().__init__();self.success=success;self.shots=[];self.frame=0
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if pc==0xe6d630:
   self.stubs.add('E6D630 actual AtkParam_Pc lookup for supplied attack context');id=u.reg_read(UC_X86_REG_R8)&0xffffffff;ptr=u.reg_read(UC_X86_REG_RCX);u.mem_write(OBJ+0x1b000,attacks[id]);u.mem_write(ptr,struct.pack('<iii4xQ',id,0,1,OBJ+0x1b000));ret(ptr)
  elif pc==0xe87800:
   self.stubs.add('E87800 actual enchant Bullet lookup');id=u.reg_read(UC_X86_REG_RDX)&0xffffffff;assert id==30905101
   u.mem_write(OBJ+0xe900,bullets[id]);ptr=u.reg_read(UC_X86_REG_RCX);u.mem_write(ptr,struct.pack('<QI',OBJ+0xe900,id));ret(ptr)
  elif pc==0x347700:
   self.stubs.add('347700 controlled scene emission outcome; source grant runs natively');self.shots.append(self.frame);ret(int(self.success))
  elif pc==0x518f30:
   self.stubs.add('518F30 supplied projectile source owner');ret(OBJ+0x6000)
  else:super().hook(u,address,size,user)
 def emit(self):
  slot=OBJ+0x1a000;self.u.mem_write(slot,bytes(0x600));self.u.mem_write(slot+0x329,b'\1');self.u.mem_write(slot+0x334,struct.pack('<I',30905101));self.u.mem_write(slot+0x494,b'\1')
  self.invoke(0x343280,[slot],{UC_X86_REG_XMM1:1/60})
 def points(self,kind):
  out=OBJ+0x8400;self.u.mem_write(out,bytes(0x300));self.u.mem_write(out+0x10,bytes([kind]));self.u.mem_write(out+8,struct.pack('<ii',10000,1))
  self.invoke(0x502830,[OBJ,out,-1,-1]);return [struct.unpack('<f',self.u.mem_read(out+off,4))[0] for off in(0x48,0x5c,0x60,0x64,0x68)]

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
            assert id == 600000281
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


checks={k:[] for k in ('dispatch','emission','values','timer','overwrite','correction','onset','damage','frostLifetime')};stubs=set()
def record(key,c,**row):checks[key].append(row);stubs.update(c.stubs)
def step(c,fps):c.qualify();c.update(1/fps)
def active(c,id):return [n for n in c.nodes() if n['id']==id and not n['flags']&0x800c0003]
def defense(c):
 c.u.mem_write(OBJ+0x800,bytes(0x200));c.invoke(0x503800,[OBJ,OBJ+0x500,OBJ+0x520,OBJ+0x540,OBJ+0x800])
 return list(struct.unpack('<5f',c.u.mem_read(OBJ+0x500,20)))
for id in (7220100,7220101):
 assert x.x['tables']['AttachEffectParam'][str(id)]['passiveSpEffectId_1']==root
 assert x.x['tables']['AttachEffectParam'][str(id)]['exclusivityId']==-1
assert x.spells[str(root)]['stateInfo']==2053 and x.spells[str(root)]['spCategory']==20
r=x.spells[str(enchant)];f=x.spells[str(frost)]
assert r['magicAttackPower']==60 and r['effectEndurance']==20 and r['playerHandValue']==1
assert r['stateInfo']==64 and r['spCategory']==162 and r['atkOccurrenceSpEffectId']==frost
assert r['isUseAtkParamAtkPowerCorrect']==1
assert f['freezeAttackPower']==40 and f['effectEndurance']==30 and f['changeHpRate']==10 and f['changeHpPoint']==50
assert f['isUseStatusAilmentAtkPowerCorrect']==1 and f['stateInfo']==260 and f['spCategory']==10007
assert all(math.isclose(f[k+'DamageCutRate'],1.15,rel_tol=1e-6) for k in ('neutral','slash','blow','thrust','magic','fire','thunder','dark'))
behavior=x.x['tables']['BehaviorParam_PC']['600000281'];bullet=x.x['tables']['Bullet']['30905101']
assert behavior['refType']==1 and behavior['refId']==30905101
assert bullet['spEffectIDForShooter']==enchant and bullet['numShoot']==1 and bullet['atkId_Bullet']==-1
# Pointer-checked normal/alternate clips and the graph variable are recorded;
# do not infer summon success from a selector variable's English name.
graph_states=[]
for state_id in (32002,32003,32004,41350,41351,41352):
 selector=graph.reference(state_id,'generator');binding=graph.selector_binding(selector)
 assert binding['name']=='IsEnableSummonAct'
 clips=[]
 for branch in graph.children(selector):
  children=graph.children(branch);assert len(children)==1
  clips.append(graph.string(graph.reference(children[0],'animationName')))
 expected=551010+10*((state_id-32002) if state_id<41350 else state_id-41350)
 assert clips==[f'a905_{expected}',f'a905_{expected+1}']
 graph_states.append(dict(state=graph.name(state_id),stateItem=state_id,binding=binding,clips=clips))
events=[dict(animation=an['ID'],**e) for an in track['animations'] for e in an['events']
        if e['Type']==2 and struct.unpack_from('<H',bytes.fromhex(e['hex']),14)[0]==2053]
assert [(e['animation'],e['index']) for e in events]==[(551010,37),(551020,37),(551030,37)]
assert all(struct.unpack_from('<i',bytes.fromhex(e['hex']),8)[0]==6281 for e in events)
for copies,enabled in itertools.product((0,1,3),(0,1)):
 c=Dispatch()
 for _ in range(copies):c.insert(root)
 c.qualify();c.update(0);loader=NativeTae(c,taeraw,track['sha256']);assert loader.id==2905
 for event in events:
  ctx=OBJ+0xd100;c.u.mem_write(ctx,bytes(0x40));found=0
  while c.invoke(0x27d0400,[loader.animations[event['animation']],ctx]):
   if struct.unpack('<I',c.u.mem_read(ctx,4))[0]!=2:continue
   ptr=struct.unpack('<Q',c.u.mem_read(ctx+8,8))[0]
   if bytes(c.u.mem_read(ptr,32))!=bytes.fromhex(event['hex']):continue
   c.q(OBJ+0x8018,OBJ+0x6000);c.u.mem_write(ctx+0x18,bytes([enabled]));c.requests.clear()
   c.invoke(0x40cd80,[OBJ+0x8000,ctx]);expected=bool(copies and enabled)
   assert len(c.requests)==expected
   if expected:assert c.requests[0]['behavior']==600000281 and c.requests[0]['instant']
   record('dispatch',c,copies=copies,enabled=bool(enabled),animation=event['animation'],requests=c.requests[:]);found+=1
  assert found==1
for success,fps in itertools.product((False,True),(30,60,120)):
 c=Enchant(success);slot=OBJ+0x1a000
 c.u.mem_write(slot,bytes(0x600));c.u.mem_write(slot+0x329,b'\1');c.u.mem_write(slot+0x334,struct.pack('<I',30905101));c.u.mem_write(slot+0x494,b'\1')
 for frame in range(fps):
  c.frame=frame;c.invoke(0x343280,[slot],{UC_X86_REG_XMM1:1/fps});step(c,fps)
 assert len(active(c,enchant))==int(success)
 if success:assert c.shots==[0] and abs(active(c,enchant)[0]['lifetime']-19)<.001
 record('emission',c,success=success,fps=fps,attempts=c.shots,nodes=c.nodes())
for copies in (0,1,3):
 c=Enchant()
 for _ in range(copies):c.emit()
 c.qualify();c.update(0)
 for kind in range(13):
  points=c.points(kind);expected=60 if copies and kind in (1,11,12) else 0
  assert points==[0,expected,0,0,0]
  record('values',c,copies=copies,attack=10000,kind=kind,points=points)
for copies,reapply,fps in itertools.product((1,3),(False,True),(30,60,120)):
 c=Enchant()
 for _ in range(copies):c.emit()
 c.qualify();c.update(0);remaining_after=None
 for frame in range(1,27*fps):
  if reapply and frame==5*fps:c.emit();remaining_after=next(n['lifetime'] for n in c.nodes() if n['id']==enchant)
  step(c,fps)
  if not active(c,enchant):break
 assert abs(frame/fps-(25 if reapply else 20))<=4/fps,(copies,reapply,fps,frame,remaining_after,c.nodes())
 if reapply:assert remaining_after==20
 assert c.points(1)==[0]*5
 # Allow normal expiry cleanup before the next independent application.
 for _ in range(3):step(c,fps)
 c.emit();c.qualify();c.update(0)
 assert active(c,enchant) and active(c,enchant)[0]['lifetime']==20 and c.points(1)==[0,60,0,0,0],(copies,reapply,fps,frame,c.nodes())
 record('timer',c,copies=copies,reapply=reapply,fps=fps,expiryFrame=frame,remainingAfterReapply=remaining_after,newLifetime=20)
for pair in ((enchant,881),(881,enchant),(enchant,enchant),(enchant,1627),(1627,enchant)):
 c=Enchant()
 for id in pair:c.grant(id);c.qualify();c.update(0)
 assert [n['id'] for n in c.nodes()]==[pair[-1]]
 record('overwrite',c,order=pair,nodes=c.nodes(),right=c.points(1),left=c.points(2))
for scale in (0,.5,1,2):
 c=Hit(4,500);c.hit(frost,10000,scale);c.qualify();c.update(0)
 assert c.remaining()==500-int(40*scale) and len(c.sent)==1 and c.sent[0]['scales'][14]==scale
 record('correction',c,scale=scale,remaining=c.remaining(),sent=c.sent)
for maximum in (40,41,100,500):
 c=Actor(4,maximum);onset=False
 for hit in range(3):
  result=c.apply(frost);c.qualify();c.update(0);packet=c.hp_packet(1000)
  expected_onset=not onset and (hit+1)*40>=maximum
  assert bool(packet[0])==expected_onset
  if expected_onset:assert packet[0]==-150;onset=True
  assert c.remaining()==(maximum if onset else maximum-40*(hit+1))
  record('onset',c,resistance=maximum,hit=hit+1,result=result,remaining=c.remaining(),hp=packet[0])
for maximum in (1,137,1000,10000):
 c=Actor(4,40);assert c.apply(frost) is False;c.qualify();c.update(0)
 packet=c.hp_packet(maximum);cuts=defense(c)
 assert packet[0]==-int(maximum*.1+50)
 assert all(math.isclose(v,1.15,rel_tol=1e-6) for v in cuts)
 record('damage',c,maximum=maximum,hp=packet[0],damageMultipliers=cuts)
for fps in (30,60,120):
 c=Actor(4,40);c.apply(frost);c.qualify();c.update(0);again=None
 for frame in range(1,32*fps):
  if frame==5*fps:again=c.apply(frost);assert again=='existing'
  step(c,fps)
  if not active(c,frost):break
 assert abs(frame/fps-30)<=4/fps
 assert defense(c)==[1]*5
 record('frostLifetime',c,fps=fps,reapplyAt=5,reapplyResult=again,expiryFrame=frame)
fields=('stateInfo','spCategory','playerHandValue','effectEndurance','magicAttackPower','atkOccurrenceSpEffectId','arrowBehaviorOffset',
        'isUseAtkParamAtkPowerCorrect','isUseStatusAilmentAtkPowerCorrect','freezeAttackPower','changeHpRate','changeHpPoint',
        'neutralDamageCutRate','magicDamageCutRate','fireDamageCutRate','thunderDamageCutRate','darkDamageCutRate')
output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),
 assetHashes={**{k:sha(v) for k,v in raws.items()},'weapon':sha(weaponraw),'tae':sha(taeraw),'behaviorGraph':graph.metadata['hkxSha256']},
 effects=[7220100,7220101],root=root,enchant=enchant,frost=frost,events=events,graphStates=graph_states,
 rows={str(id):{k:x.spells[str(id)][k] for k in fields} for id in (root,enchant,frost,881,1627)},
 checks=checks,stubs=sorted(stubs|{'attack kind and 10000 attack row supplied; weapon/arrow hit-data construction and actual payload binding not executed',
 'frost payload supplied in hit slot 5; 43BE60 argument 5 skips physical HP damage while native effect delivery executes',
 'full summon eligibility, game behavior VM, physical spawn and multiplayer not executed'}),
 native=dict(animation='27D0F10 / 27D0400 → 40CD80 → 668B30',selfGrant='343280 → 3C7F40 → 3C80A0',attack='502830 → 511010',
             hit='43BE60 → 3C80A0',ailment='50D060 → 42D110 / 505280',hp='506EC0 → 50B860',defense='503800'),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(map(len,checks.values())),'native Revenant enchantment checks',{k:len(v) for k,v in checks.items()},flush=True)
