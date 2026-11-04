"""Trace Duchess dagger-finisher marker, gated emission and Restage damage.

The original hit-effect routing, effect lifecycle, state gate, radius getter,
replay rate and damage consumer execute with actual PARAM rows. Hit metadata
and historical damage records are supplied fixtures, not full game execution.
"""
import argparse,json,struct,itertools,math
from pathlib import Path
from native_effect_runtime import *
from native_ailment_runtime import Ailment
from native_restage_runtime import Restage, f32
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','assets','systems','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted)
raws={name:a.extracted.with_suffix('.'+name+'.param').read_bytes() for name in ('AtkParam_Pc','BehaviorParam_PC','Bullet')}
attacks=Inputs.table(raws['AtkParam_Pc'],0x1d0);behaviors=Inputs.table(raws['BehaviorParam_PC'],0x30);bullets=Inputs.table(raws['Bullet'],0x100)
weaponraw=a.assets.with_suffix('.EquipParamWeapon.param').read_bytes();weapons=Inputs.table(weaponraw,0x298)
playerraw=a.systems.with_suffix('.PlayerCommonParam.param').read_bytes();player=Inputs.table(playerraw,0x140)[0]
for path in (a.assets,a.systems):assert json.loads(path.read_text())['hashes']['regulation.bin']==x.x['hashes']['regulation.bin']
root,marker,emitter,leaf=7010700,7010702,7010703,7010701
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


COMP=OBJ+0x66000;AIL=OBJ+0x67000;HP=OBJ+0x68000
class Dagger(Hit):
 def __init__(self):
  self.routes=[];self.shots=[];self.frame=0;super().__init__()
  self.u.mem_write(SOURCE,bytes(self.u.mem_read(OBJ+0x6000,0x200)))
  self.u.mem_write(SOURCE+0x74,b'\1');self.q(SOURCE+0x190,SEFFECT);self.q(SEFFECT+0x10,SOURCE);self.q(SOURCE+0x1b8,COMP)
  self.q(COMP+0x20,AIL);self.q(AIL+8,SOURCE);self.q(COMP,HP);self.q(HP+8,SOURCE)
  self.q(OBJ+0x574e8,SOURCE)
 def hook(self,u,address,size,user):
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  pc=address-BASE
  if pc==0x3c80a0:self.routes.append(dict(target=hex(u.reg_read(UC_X86_REG_RCX)),effect=u.reg_read(UC_X86_REG_RDX)))
  elif pc==0x3ced90:
   self.stubs.add('3CED90 supplied attacker animation-owner context');ret(OBJ+0xd000)
  elif pc==0x4d1b20:
   self.stubs.add('4D1B20 explicit false actor mode predicate');ret()
  elif pc==0x3975d0:
   self.stubs.add('3975D0 Behavior creation request recorder; no scene collision');self.shots.append(dict(frame=self.frame,behavior=u.reg_read(UC_X86_REG_RDX)));ret(1)
  else:super().hook(u,address,size,user)
 def equip(self,n):
  for _ in range(n):self.invoke(0x3c7fd0,[SOURCE,7010700,1])
 def tick(self,dt):
  self.invoke(0x5057d0,[SEFFECT,0,0],{UC_X86_REG_XMM1:1});self.invoke(0x50acd0,[SEFFECT,0,0],{UC_X86_REG_XMM1:dt});self.invoke(0x50aa20,[SEFFECT])
 def source_nodes(self):
  node=struct.unpack('<Q',self.u.mem_read(SEFFECT+8,8))[0];out=[]
  while node:
   out.append((struct.unpack('<i',self.u.mem_read(node+8,4))[0],struct.unpack('<f',self.u.mem_read(node+0x4c,4))[0],struct.unpack('<I',self.u.mem_read(node+0x68,4))[0]));node=struct.unpack('<Q',self.u.mem_read(node+0x38,8))[0]
  return out

class AttackSetup(Chain):
 def __init__(self):super().__init__(x);self.attacks=[]
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if pc==0x34a890:
   radius=struct.unpack('<f',(u.reg_read(UC_X86_REG_XMM2)&0xffffffff).to_bytes(4,'little'))[0]
   self.attacks.append(dict(id=u.reg_read(UC_X86_REG_RDX)&0xffffffff,radius=radius));ret()
  elif pc in(0x34ad90,0x34b130,0x34dc70):ret()
  else:super().hook(u,address,size,user)

checks={k:[] for k in ('trigger','emptyPayload','repeat','damage','overwrite','radius','attackSetup')};stubs=set()
def record(key,c,**row):checks[key].append(row);stubs.update(c.stubs)
spells=x.spells;tables=x.x['tables']
assert tables['AttachEffectParam'][str(root)]['passiveSpEffectId_1']==root
assert tables['AttachEffectParam'][str(root)]['exclusivityId']==-1
assert spells[str(root)]['stateInfo']==2018 and spells[str(root)]['spCategory']==20
assert spells[str(marker)]['effectTargetAttacker']==1 and spells[str(marker)]['replaceSpEffectId']==emitter
assert math.isclose(spells[str(marker)]['effectEndurance'],.1,rel_tol=1e-6)
assert spells[str(emitter)]['stateInfo']==275 and spells[str(emitter)]['invocationConditionsStateChange1']==2018
assert spells[str(emitter)]['effectEndurance']==0 and spells[str(emitter)]['behaviorId']==600000180
assert spells[str(leaf)]['stateInfo']==601 and spells[str(leaf)]['effectEndurance']==0
assert math.isclose(spells[str(leaf)]['restageAttackRate'],.4,rel_tol=1e-6)
assert struct.unpack_from('<f',x.rows[leaf],0x3b0)[0]==spells[str(leaf)]['restageAttackRate']
assert tables['BehaviorParam_PC']['600000180']['refType']==1 and tables['BehaviorParam_PC']['600000180']['refId']==30903006
bullet=tables['Bullet']['30903006'];assert bullet['spEffectId0']==leaf and bullet['numShoot']==1
attack_ids=sorted(int(id) for id,r in tables['AtkParam_Pc'].items() if r['spEffectId1']==marker)
assert attack_ids==[100836,102236,150050,150250,150450]
attack_paths=[]
for id in attack_ids:
 paths=[dict(id=int(k),**v) for k,v in tables['BehaviorParam_PC'].items() if v['refType']==0 and v['refId']==id]
 assert len(paths)==1
 attack_paths.append(dict(attack=id,payload=marker,behavior=paths[0]))
for attack,copies,fps in itertools.product(attack_ids,(0,1,3),(30,60,120)):
 c=Dagger();c.equip(copies);c.tick(0)
 for _ in range(60):c.tick(0)
 assert not c.shots
 c.hit(marker,attack,1)
 assert c.routes[-1]==dict(target=hex(SOURCE),effect=marker)
 for frame in range(fps):c.frame=frame;c.tick(1/fps)
 assert len(c.shots)==bool(copies),(attack,copies,fps,c.shots)
 if copies:
  assert c.shots[0]['behavior']==600000180
  assert .1<=(c.shots[0]['frame']+1)/fps<=.1+6/fps
 assert [n[0] for n in c.source_nodes()]==([root] if copies else [])
 assert not any(n['id'] in (marker,emitter,root) for n in c.nodes())
 record('trigger',c,attack=attack,copies=copies,fps=fps,hitRecipient='enemy',markerRecipient='attacker',requests=c.shots,nodes=c.source_nodes())
for copies in(0,1,3):
 c=Dagger();c.equip(copies);c.tick(0);c.hit((),100836,1)
 for frame in range(60):c.frame=frame;c.tick(1/60)
 assert not c.shots
 record('emptyPayload',c,copies=copies,requests=c.shots)
for copies,fps,mode in itertools.product((1,3),(30,60,120),('same-frame','spaced')):
 c=Dagger();c.equip(copies);c.tick(0)
 for frame in range(3*fps):
  c.frame=frame
  if mode=='same-frame' and frame==0:
   for _ in range(3):c.hit(marker,100836,1)
  elif mode=='spaced' and frame%fps==0:c.hit(marker,100836,1)
  c.tick(1/fps)
 assert len(c.shots)==3,(copies,fps,mode,c.shots)
 # Repeated incoming hits can enqueue separate markers even in one frame.
 # These are emission requests, not proof of three final damage applications.
 record('repeat',c,copies=copies,fps=fps,mode=mode,requests=c.shots)
poise_rate=struct.unpack_from('<f',player,0xd4)[0]
for copies,values,flags in itertools.product((0,1,3),([], [0], [1], [2], [3], [5], [9], [99], [100], [999], [1,1,1], [3,7,11], [100,200,300]),(0,1,4,15)):
 c=Restage(x,player,weapons,behaviors);c.boost(copies);rate=c.apply(leaf)
 assert math.isclose(rate,.4,rel_tol=1e-6)
 records=[(v,12.5 if v else 0,flags) for v in values];result=c.consume(records)
 damage=0;poise=0.
 for v,p,f in records:damage=int(f32(f32(f32(v)*rate)+f32(damage)));poise=f32(poise+f32(f32(p)*poise_rate))
 eligible=damage>0 or poise>0
 assert result['hp']==([-damage] if damage>0 else [])
 assert result['poise']==([poise] if eligible else [])
 assert result['statuses']==([703600+i for i in range(4) if flags&(1<<i)] if eligible else [])
 record('damage',c,skillBoostCopies=copies,rate=rate,values=values,statusBits=flags,result=result)
# Each request writes one replay rate; pending requests are not independently
# scheduled here. Do not infer same-frame gameplay ordering from these sequences.
for order in ((leaf,leaf,leaf),(703540,leaf),(7290001,leaf),(leaf,703540),(leaf,7290001)):
 c=Restage(x,player,weapons,behaviors);rates=[c.apply(id) for id in order]
 assert math.isclose(rates[-1],.5 if order[-1]==703540 else spells[str(order[-1])]['restageAttackRate'],rel_tol=1e-6)
 result=c.consume([(100,10,0)]);assert result['hp']==[-int(f32(100*rates[-1]))]
 record('overwrite',c,order=order,rates=rates,result=result)
c=AttackSetup();param=OBJ+0x9000;c.u.mem_write(param,bullets[30903006]);c.q(OBJ+0x4008,param)
assert bullet['hitRadius']==bullet['hitRadiusMax']==15
for fraction in(-.5,0,.5,1,2):
 c.invoke(0x363600,[OBJ+0x4008],{UC_X86_REG_XMM1:fraction})
 radius=struct.unpack('<f',(c.u.reg_read(UC_X86_REG_XMM0)&0xffffffff).to_bytes(4,'little'))[0];assert radius==15
 record('radius',c,fraction=fraction,radius=radius)
c.invoke(0x362c10,[OBJ+0x4000,OBJ+0x8000]);assert c.attacks==[dict(id=600000150,radius=15)]
c.stubs.add('34A890 attack creation recorder; 34AD90/34B130 visual sinks; 34DC70 false mode predicate')
record('attackSetup',c,requests=c.attacks)
fields=('stateInfo','spCategory','effectEndurance','effectTargetAttacker','replaceSpEffectId','invocationConditionsStateChange1','behaviorId','motionInterval','restageAttackRate')
output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),
 assetHashes={**{k:sha(v) for k,v in raws.items()},'weapon':sha(weaponraw),'playerCommon':sha(playerraw)},
 effects=[root],root=root,marker=marker,emitter=emitter,leaf=leaf,rate=spells[str(leaf)]['restageAttackRate'],poiseRate=poise_rate,
 rows={str(id):{k:spells[str(id)][k] for k in fields} for id in (root,marker,emitter,leaf)},attackPaths=attack_paths,
 bullet={k:bullet[k] for k in ('atkId_Bullet','life','numShoot','hitRadius','hitRadiusMax','spEffectId0','HitBulletID')},
 checks=checks,stubs=sorted(stubs|{'hit payload populated from actual Atk row, but attack construction, animation/moveset selection and collision not executed',
 '43BE60 call argument 5 skips primary HP damage while running hit-effect delivery; native attacker routing and grant execute',
 'synthetic source/recipient actors and fixed source component pointers; explicit source local-player identity',
 'explicit historical records; history recorder, time window, scheduling, target selection and final caps not simulated',
 'pending overlapping Restage requests, complete scene emissions, multiplayer and game execution not simulated'}),
 native=dict(hit='43BE60 → 3C80A0',grant='3C7FD0',lifecycle='5057D0 / 50ACD0',emission='50AA20 → 3975D0',radius='363600',
 attackSetup='362C10 → 34A890',restage='3CE5B3..3CE5E9 → 44A340',consume='449AAC..449C6D → 430F50'),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(map(len,checks.values())),'native Duchess dagger checks',{k:len(v) for k,v in checks.items()},flush=True)
