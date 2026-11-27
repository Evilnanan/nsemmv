"""Trace Ironeye periodic melee growth, damage reset and cached skill cooldown.

Original selection, self delivery, growth, tagged attack getters, damage
notification and skill recharge blocks run with pinned inputs. Explicit actor,
source and charge state fixtures do not constitute full gameplay.
"""
import argparse,itertools,json,math,struct
from pathlib import Path
from native_effect_runtime import BASE,OBJ,STACK,STOP,Inputs,Chain,sha
from native_ailment_runtime import Ailment
from unicorn.x86_const import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','combat','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted);inputs=x
raws={name:a.extracted.with_suffix('.'+name+'.param').read_bytes() for name in ('AttachEffectParam','AtkParam_Pc')}
hashes={'AttachEffectParam':'ae8128ed510a532d0fa7cb56fa9c86e4a44c9d815dd4ee01c05821d5f50a9827','AtkParam_Pc':'1ec1893420053cbfb06e3efb269ade4ba9d6a617d1d3dbb370e837847be05676'}
for name,raw in raws.items():assert sha(raw)==hashes[name]
rows=Inputs.table(raws['AttachEffectParam'],0x44);atk=Inputs.table(raws['AtkParam_Pc'],0x1d0)
assert sha(x.param)=='07ec636c5565d4551efeb53e6f08bc633b2aa4f2129f13c61b0638d69b1bc176'
for name,table in (('AttachEffectParam',rows),('AtkParam_Pc',atk)):assert len(table)==struct.unpack_from('<H',raws[name],10)[0]
combat=json.loads(a.combat.read_text());assert combat['hashes']['regulation.bin']==x.x['hashes']['regulation.bin']
hero_raw=a.combat.with_suffix('.HeroParam.param').read_bytes();hero_bytes=Inputs.table(hero_raw,0xb0)[3];hero=combat['tables']['HeroParam']['3']
assert hero['characterAbilityCooldown']==struct.unpack_from('<f',hero_bytes,0x74)[0]==10 and hero['characterAbilityUsageCount']==hero_bytes[0x78]==1
EFFECTS=(7037200,7037201);ROOT=7280320;LADDER=list(range(7280301,7280311));FIELDS=[k+'AttackRate' for k in ('physics','magic','fire','thunder','dark')]
for effect in EFFECTS:
 ar=x.x['tables']['AttachEffectParam'][str(effect)]
 assert (ar['passiveSpEffectId_1'],ar['passiveSpEffectId_2'],ar['passiveSpEffectId_3'],ar['exclusivityId'])==(ROOT,-1,-1,-1)
 # This reference is consumed by native count/level readers; not a grant.
 assert ar['permanentSpEffectId']==struct.unpack_from('<i',rows[effect],0x40)[0]==LADDER[0]
 assert ar['isPersistentEffect']==rows[effect][0x27]==1
r=x.spells[str(ROOT)];assert (r['spCategory'],r['effectEndurance'],r['motionInterval'],r['cycleOccurrenceSpEffectId'])==(20,-1,10,LADDER[0])
assert [int(id) for id,r in x.spells.items() if r['spCategory']==204 and r['categoryPriority']==7]==LADDER
for stage,id in enumerate(LADDER,1):
 r=x.spells[str(id)];assert (r['stateInfo'],r['effectEndurance'],r['magicSubCategoryChange1'],r['deleteCriteriaDamage'],r['characterSkillCooldownReduction'])==(0,-1,130,1,1.5)
 assert all(math.isclose(r[k],1.03**stage,rel_tol=1e-6) for k in FIELDS)
 assert r['cycleOccurrenceSpEffectId']==r['replaceSpEffectId']==-1
assert LADDER[-1]+1 not in x.rows
tags={int(id):sorted({r['subCategory'+str(n)] for n in range(1,6)}-{0}) for id,r in x.x['tables']['AtkParam_Pc'].items()}
representatives={}
for id,ts in tags.items():representatives.setdefault(tuple(ts),id)
assert len(representatives)==216
POS=next(id for id,ts in tags.items() if 130 in ts);NEG=next(id for id,ts in tags.items() if 130 not in ts)
MAN=OBJ+0x8000;SELECT_OUT=OBJ+0x9000;BITS=OBJ+0x9100
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
  self.invoke(0x4fea30,[MAN,SELECT_OUT]);bits=int.from_bytes(self.u.mem_read(BITS,20),'little');return [i for i in range(144) if bits>>i&1]

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

TARGET,PACKET,WRAPPER,ACTOR,OUT=OBJ+0x80000,OBJ+0x81000,OBJ+0x82000,OBJ+0x82100,OBJ+0x83000
class Counter(Damage):
 def __init__(self):
  self.stopAt=None;super().__init__();self.u.mem_map(TARGET,0x10000)
  self.q(TARGET+0x10,ACTOR);self.q(ACTOR,OBJ+0x6200);self.q(ACTOR+0x190,TARGET);self.q(WRAPPER+8,ACTOR)
 def hook(self,u,address,size,user):
  pc=address-BASE
  if pc==self.stopAt or self.stopAt==0x43a696 and pc==0x43a72b:u.reg_write(UC_X86_REG_RIP,STOP)
  elif pc==0x3d4180:pass
  else:super().hook(u,address,size,user)
class Attack(Counter):
 def hook(self,u,address,size,user):
  if address-BASE==0xe6d630:
   id=u.reg_read(UC_X86_REG_R8)&0xffffffff;assert u.reg_read(UC_X86_REG_RDX)==1
   wrapper=u.reg_read(UC_X86_REG_RCX);u.mem_write(OBJ+0xa800,atk[id]);u.mem_write(wrapper,struct.pack('<iii4xQ',id,0,1,OBJ+0xa800))
   sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8);return
  super().hook(u,address,size,user)
 def row(self,id,kind=0):
  self.u.mem_write(OBJ+0x800,bytes(0x300));self.u.mem_write(OBJ+0xa800,atk[id]);self.q(OBJ+0xb010,OBJ+0xa800)
  self.invoke(0xe6d530,[OBJ+0xb000,OBJ+0x814]);assert int.from_bytes(self.u.mem_read(OBJ+0x814,32),'little')==sum(1<<tag for tag in tags[id]);self.u.mem_write(OBJ+0x808,struct.pack('<iiB',id,1,kind));self.invoke(0x502830,[OBJ,OBJ+0x800,-1,-1])
  return [struct.unpack('<f',self.u.mem_read(OBJ+0x800+off,4))[0] for off in (0x90,0xa4,0xa8,0xac,0xb0)]

SKILL=OBJ+0x85000
class Skill(Attack):
 def __init__(self):
  super().__init__();self.q(SKILL+8,OBJ+0x6000);self.q(OBJ+0x6378,STOP+0xb00)
  self.u.mem_write(SKILL+0x20,b'\1\1\1');self.u.mem_write(SKILL+0x24,struct.pack('<3f',0,hero['characterAbilityCooldown'],hero['characterAbilityCooldown']))
 def hook(self,u,address,size,user):
  if address==STOP+0xb00 or address-BASE==0x48c220:
   u.reg_write(UC_X86_REG_RAX,3 if address==STOP+0xb00 else 0)
   sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  else:super().hook(u,address,size,user)
 def state(self):return list(self.u.mem_read(SKILL+0x20,2))+list(struct.unpack('<3f',self.u.mem_read(SKILL+0x24,12)))
 def tick_skill(self,dt):
  self.u.reg_write(UC_X86_REG_RDI,SKILL);self.stopAt=0x48c0a5
  self.invoke(0x48bfa0,[],{UC_X86_REG_XMM6:dt});self.stopAt=None
 def settle(self):
  for _ in range(2):self.qualify();self.update(0)

checks={k:[] for k in ('selection','mixed','timer','filters','kinds','damage','staggered','disabled','removal','cooldown','reader')};stubs=set()
def record(key,c,**row):checks[key].append(row);stubs.update(c.stubs)
def step(c,dt=0):c.qualify();c.update(dt)
def level(c):return c.invoke(0x501f00,[OBJ,LADDER[0],1])
def rate(c):
 c.invoke(0x508480,[OBJ]);return struct.unpack('<f',(c.u.reg_read(UC_X86_REG_XMM0)&0xffffffff).to_bytes(4,'little'))[0]
def start(copies=1,extra=None):
 c=Skill()
 for _ in range(copies):c.grant(ROOT)
 if extra:c.grant(extra)
 step(c);step(c);return c
for effect,copies,hero_id in itertools.product(EFFECTS,(1,2,3,6),range(11)):
 c=Selection([[effect]]*copies,hero_id);bits=c.select();selected=[i for i in range(copies) if i*6 in bits]
 assert selected==(list(range(copies)) if hero_id in (0,3) else [])
 c.invoke(0xe6e150,[OBJ+0x9200,effect]);decoded=[c.invoke(0xe6e3b0,[OBJ+0x9200,n])&0xffffffff for n in range(3)];assert decoded==[ROOT,0xffffffff,0xffffffff]
 reference=c.invoke(0xe6e3d0,[OBJ+0x9200]);assert reference==LADDER[0]
 v=start(len(selected));assert level(v)==int(bool(selected));assert len([n for n in v.nodes() if n['id']==ROOT])==int(bool(selected))
 stubs.update(v.stubs);record('selection',c,effect=effect,copies=copies,hero=hero_id,selected=selected,passives=decoded,levelReference=reference,level=level(v))
for counts in itertools.product(range(4),repeat=2):
 c=start(sum(counts));values=c.row(POS);expected=1.03 if any(counts) else 1
 assert all(math.isclose(v,expected,rel_tol=1e-6) for v in values)
 assert math.isclose(rate(c),1.5 if any(counts) else 1,rel_tol=1e-6)
 record('mixed',c,counts=counts,level=level(c),attack=values,cooldownRate=rate(c))
print('PASS selection/mixed',len(checks['selection']),len(checks['mixed']),flush=True)
for copies,fps in itertools.product((1,3),(30,60,120)):
 c=Skill()
 for _ in range(copies):c.grant(ROOT)
 changes=[];prior=None;damage_frame=round(112.5*fps)
 for frame in range(125*fps):
  if frame==damage_frame:c.damage(1)
  step(c,1/fps);current=level(c)
  if current!=prior:changes.append(dict(frame=frame,level=current));prior=current
 assert [r['level'] for r in changes]==[0]+list(range(1,11))+[0,1],(copies,fps,changes)
 for stage,event in enumerate(changes[1:11],1):assert abs(event['frame']-(stage-1)*10*fps)<=4
 assert abs(changes[-2]['frame']-damage_frame)<=3 and abs(changes[-1]['frame']-120*fps)<=4
 record('timer',c,copies=copies,fps=fps,damageFrame=damage_frame,changes=changes)
 print('PASS timer',copies,fps,flush=True)
for stage in (0,1,5,10):
 c=Skill()
 if stage:c.insert(7280300+stage)
 step(c)
 for ts,id in representatives.items():
  values=c.row(id);expected=1.03**stage if 130 in ts else 1
  assert all(math.isclose(v,expected,rel_tol=1e-6) for v in values),(stage,id,ts,values)
  record('filters',c,stage=stage,attack=id,tags=ts,values=values)
 for kind in range(13):
  values=c.row(POS,kind);expected=1.03**stage if kind!=5 else 1
  assert all(math.isclose(v,expected,rel_tol=1e-6) for v in values)
  record('kinds',c,stage=stage,kind=kind,values=values)
for stage,damage,excluded,kind,category in itertools.product((1,10),(-1,0,1,100),(0,1),(0,3,5),(0,6)):
 c=Skill();c.insert(7280300+stage);step(c)
 c.invoke(0x504d30,[OBJ,0,kind,category,excluded],{UC_X86_REG_XMM1:damage});step(c);step(c)
 assert level(c)==(0 if damage>0 else stage)
 assert rate(c)==(1 if damage>0 else 1.5)
 record('damage',c,stage=stage,damage=damage,excluded=excluded,kind=kind,category=category,afterLevel=level(c),afterCooldown=rate(c))
print('PASS filters/kinds/damage',len(checks['filters']),len(checks['kinds']),len(checks['damage']),flush=True)
for extra_frames in ([],[20,40],[599],[600]):
 c=Skill();c.grant(ROOT);changes=[];prior=None
 for frame in range(1805):
  if frame in extra_frames:c.grant(ROOT)
  step(c,1/60);current=level(c)
  if current!=prior:changes.append([frame,current]);prior=current
 assert changes==[[0,0],[1,1],[600,2],[1200,3],[1800,4]],(extra_frames,changes)
 record('staggered',c,additionalRootFrames=extra_frames,changes=changes)
for stage,mask in itertools.product((1,10),(1,2,0x40000,0x80000000)):
 c=Skill();c.insert(7280300+stage);step(c);ptr=struct.unpack('<Q',c.u.mem_read(OBJ+8,8))[0];c.u.mem_write(ptr+0x68,struct.pack('<I',mask))
 assert c.row(POS)==[1]*5 and rate(c)==1
 record('disabled',c,stage=stage,mask=mask,values=c.row(POS),cooldown=rate(c))
c=start();c.invoke(0x505280,[OBJ,0]);step(c);step(c);assert level(c)==1 and rate(c)==1.5
record('removal',c,nodes=c.nodes(),level=level(c),cooldown=rate(c))
for active,extra in itertools.product((False,True),(None,7000800,7000803)):
 c=Skill()
 if active:c.insert(LADDER[0])
 if extra:c.insert(extra)
 c.settle();c.tick_skill(0);initial=c.state();scale=x.spells[str(extra)]['characterSkillCooldownReduction'] if extra else 1
 assert math.isclose(initial[3],10*scale*(1.5 if active else 1),rel_tol=1e-6)
 c.u.mem_write(SKILL+0x20,b'\0');c.tick_skill(5);elapsed=c.state()
 if active:c.damage(1)
 else:c.insert(LADDER[0])
 c.settle();c.tick_skill(0);changed=c.state();assert changed==elapsed
 c.tick_skill(initial[3]-5);ready=c.state();assert ready[0]==1 and ready[2]==0
 assert math.isclose(ready[3],10*scale*(1 if active else 1.5),rel_tol=1e-6)
 record('cooldown',c,initiallyActive=active,otherEffect=extra,initial=initial,elapsed=elapsed,changed=changed,ready=ready)
for stage in (0,1,5,10):
 c=Skill()
 if stage:c.insert(7280300+stage)
 step(c);before=c.nodes();value=level(c);after=c.nodes();assert before==after and value==stage
 record('reader',c,stage=stage,value=value,before=before,after=after)
print('PASS remaining',{k:len(v) for k,v in checks.items()},flush=True)
out=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),paramHashes=hashes,heroParamSha256=sha(hero_raw),hero=dict(id=3,cooldown=10,charges=1),
 effects=EFFECTS,root=ROOT,ladder=LADDER,perStageRate=1.03,period=10,maxStages=10,cooldownRate=1.5,tagSets=len(representatives),checks=checks,
 native=dict(selection='4FEA30 → E6E150 → E6E3B0',reference='E6E3D0 → 501F00 (read only)',update='5057D0 → 50ACD0',grant='3C7FD0 → 3C80A0 → 3DB410 → 5077A0',damage='504D30',attack='E6D530 → 502830',cooldownRate='508480',recharge='48BFA0..48C0A5 → 42C130/508480/48C380'),
 stubs=sorted(stubs|{'Explicit current skill charges, elapsed time and pinned HeroParam base; original recharge block computes readiness and next threshold.',
 'Actor virtual+178 supplies Ironeye hero3; 48C220 completion sound/notification is a sink.',
 'Actual source tags and explicit runtime source/damage/exclusion fields; no full collision or animation scheduler.'}),
 limitations=['No full equipment rebuild, collision, DLL hooks, multiplayer, death or save reload.',
 'Container removal leaves the existing growth leaf; complete unequip scheduling is not inferred.',
 'Regular recharge block caches the current threshold; explicit resets/refills and external callers can have different lifecycle rules.',
 'Attach +40 is verified as a read-only level reference at the inspected consumers, not an initial growth grant; uninspected DLL field readers are not ruled out.',
 'Source kind5 excluded; no unsupported mapping of internal source kinds to player actions.'],gameplayVerified=False)
a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('PASS total',sum(map(len,checks.values())),flush=True)
