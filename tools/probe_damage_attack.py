"""Trace damage-triggered attack buffs through original actor grants and timers.

Equipment, allocation, identity and damage context are explicit inputs. Native
selection, self delivery, container transitions and numeric consumers execute.
This is isolated execution, not a complete game session.
"""
import argparse,itertools,json,math,struct
from pathlib import Path
from native_effect_runtime import BASE,OBJ,STOP,Inputs,Chain,sha
from native_ailment_runtime import Ailment
from unicorn.x86_const import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted);inputs=x;t=x.x['tables']
raws={name:a.extracted.with_suffix('.'+name+'.param').read_bytes() for name in ('AttachEffectParam','AtkParam_Pc')}
hashes={'AttachEffectParam':'ae8128ed510a532d0fa7cb56fa9c86e4a44c9d815dd4ee01c05821d5f50a9827','AtkParam_Pc':'1ec1893420053cbfb06e3efb269ade4ba9d6a617d1d3dbb370e837847be05676'}
assert sha(x.param)=='07ec636c5565d4551efeb53e6f08bc633b2aa4f2129f13c61b0638d69b1bc176'
for name,raw in raws.items():assert sha(raw)==hashes[name]
rows=Inputs.table(raws['AttachEffectParam'],0x44);atk=Inputs.table(raws['AtkParam_Pc'],0x1d0)
for name,table in (('AttachEffectParam',rows),('AtkParam_Pc',atk)):
 assert len(table)==struct.unpack_from('<H',raws[name],10)[0]
assert len(x.rows)==struct.unpack_from('<H',x.param,10)[0]
EFFECTS=(10001,100000,7032200,7032201,7032202)
ROOTS=(7032200,7032210,7032220)
FAMILIES=[dict(root=root,guard=root+1,leaf=root+2,rate=x.spells[str(root+2)]['physicsAttackRate']) for root in ROOTS]
BY_ROOT={f['root']:f for f in FAMILIES}
MAPPING={effect:[t['AttachEffectParam'][str(effect)]['passiveSpEffectId_'+str(n)] for n in (1,2,3)] for effect in EFFECTS}
assert MAPPING=={10001:[7032200,7032201,9762],100000:[7032200,-1,-1],7032200:[7032200,-1,-1],7032201:[7032210,-1,-1],7032202:[7032220,-1,-1]}
for effect in EFFECTS:
 r=t['AttachEffectParam'][str(effect)]
 assert r['exclusivityId']==r['permanentSpEffectId']==-1
 assert all(v==1 for k,v in r.items() if k.startswith('allow'))
for f,rate in zip(FAMILIES,(1.15,1.225,1.25)):
 r,g,l=(x.spells[str(f[k])] for k in ('root','guard','leaf'))
 assert (r['spCategory'],r['stateInfo'],r['effectEndurance'],r['motionInterval'],r['cycleOccurrenceSpEffectId'])==(10,2374,-1,1,f['guard'])
 assert (g['spCategory'],g['stateInfo'],g['effectEndurance'],g['deleteCriteriaDamage'],g['replaceSpEffectId'])==(0,0,-1,1,f['leaf'])
 assert x.rows[f['guard']][0x327]==1
 assert (l['spCategory'],l['stateInfo'],l['effectEndurance'],l['isWaitModeDelete'])==(20,0,10,1)
 assert g['invocationConditionsStateChange1']==l['invocationConditionsStateChange1']==2374
 assert l['isExtendSpEffectLife']==l['isContractSpEffectLife']==0
 assert all(l[k+'AttackRate']==f['rate'] for k in ('physics','magic','fire','thunder','dark'))
 assert math.isclose(f['rate'],rate,rel_tol=1e-6)
 assert all(l[k]==0 for k in ('magicSubCategoryChange1','magicSubCategoryChange2','magicSubCategoryChange3'))
 assert all(l[k]==1 for k in ('magParamChange','miracleParamChange','shamanParamChange'))
tags={int(id):sorted({r['subCategory'+str(n)] for n in range(1,6)}-{0}) for id,r in t['AtkParam_Pc'].items()}
for id,ts in tags.items():assert ts==sorted(set(atk[id][o] for o in (0x4e,0x4f,0x1c8,0x1c9,0x1ca))-{0})
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

class Attack(Damage):
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

checks={k:[] for k in ('selection','trigger','mixed','damageContext','filters','kinds','lifetime','refresh','continuous','staggered','disabled','removal')};stubs=set()
def record(key,c,**row):checks[key].append(row);stubs.update(c.stubs)
def step(c,dt=0):c.qualify();c.update(dt)
def start(roots):
 c=Attack()
 for root in roots:c.grant(root)
 step(c);step(c)
 return c
def trigger(c,damage=1,excluded=0):
 before=len(c.grants);c.damage(damage,excluded)
 for _ in range(3):step(c)
 return c.grants[before:]
def expected(roots):return math.prod(f['rate'] for f in FAMILIES if f['root'] in roots)
def verify(c,rate,kind=0):
 values=c.attack(kind)
 assert all(math.isclose(v,rate if kind!=5 else 1,rel_tol=2e-6) for v in values),(values,rate,kind,c.nodes())
 return values
def leaves(c):return [n for n in c.nodes() if n['id'] in [f['leaf'] for f in FAMILIES]]
def roots_for(effects):return [r for e in effects for r in MAPPING[e] if r>=0]
def select(effects,hero=1):
 c=Selection([[e] for e in effects],hero);bits=c.select();selected=[]
 for i,e in enumerate(effects):
  assert i*6 in bits,(effects,hero,bits)
  c.invoke(0xe6e150,[OBJ+0x9200,e])
  decoded=[c.invoke(0xe6e3b0,[OBJ+0x9200,n])&0xffffffff for n in (0,1,2)]
  assert decoded==[r&0xffffffff for r in MAPPING[e]]
  selected.extend(r for r in decoded if r!=0xffffffff)
 return c,bits,selected
for effect,copies,hero in itertools.product(EFFECTS,(1,2,3,6),range(11)):
 c,bits,selected=select([effect]*copies,hero)
 assert selected==roots_for([effect]*copies)
 v=start(selected);grants=trigger(v);values=verify(v,expected(selected));stubs.update(v.stubs)
 assert len(leaves(v))==1
 record('selection',c,effect=effect,copies=copies,hero=hero,selectionBits=bits,roots=selected,grants=grants,values=values)
print('PASS selection',len(checks['selection']),flush=True)
for effect,copies,damage,excluded in itertools.product(EFFECTS,(0,1,3,6),(-1,0,1,10000),(0,1)):
 roots=roots_for([effect]*copies);c=start(roots);grants=trigger(c,damage,excluded);fired=bool(copies and damage>0)
 assert len(leaves(c))==int(fired)
 values=verify(c,expected(roots) if fired else 1)
 record('trigger',c,effect=effect,copies=copies,damage=damage,excluded=excluded,grants=grants,values=values)
print('PASS trigger',len(checks['trigger']),flush=True)
for counts in itertools.product(range(3),repeat=len(EFFECTS)):
 effects=[e for e,n in zip(EFFECTS,counts) for _ in range(n)]
 c,bits,roots=select(effects);v=start(roots);grants=trigger(v);values=verify(v,expected(roots));stubs.update(v.stubs)
 assert sorted(n['id'] for n in leaves(v))==[f['leaf'] for f in FAMILIES if f['root'] in roots]
 record('mixed',c,counts=counts,roots=roots,grants=grants,values=values)
print('PASS mixed',len(checks['mixed']),flush=True)
for f in FAMILIES:
 c=start([f['root']]);ptr=struct.unpack('<Q',c.u.mem_read(OBJ+8,8))[0]
 while struct.unpack('<i',c.u.mem_read(ptr+8,4))[0]!=f['guard']:ptr=struct.unpack('<Q',c.u.mem_read(ptr+0x38,8))[0]
 for damage,kind,category,excluded in itertools.product((-1,0,1,10000),(0,1,2,3,254),(0,1,10,255),(0,1)):
  c.u.mem_write(ptr+0x4c,struct.pack('<f',-1));c.invoke(0x504d30,[OBJ,0,kind,category,excluded],{UC_X86_REG_XMM1:damage})
  lifetime=struct.unpack('<f',c.u.mem_read(ptr+0x4c,4))[0];assert lifetime==(0 if damage>0 else -1)
  record('damageContext',c,root=f['root'],damage=damage,kind=kind,category=category,excluded=excluded,guardLife=lifetime)
for f in FAMILIES:
 c=start([f['root']]);trigger(c)
 for attack in representatives.values():
  values=c.row(attack);assert all(math.isclose(v,f['rate'],rel_tol=1e-6) for v in values)
  record('filters',c,root=f['root'],attack=attack,values=values)
 for kind in range(13):record('kinds',c,root=f['root'],kind=kind,values=verify(c,f['rate'],kind))
print('PASS contexts/filters/kinds',len(checks['damageContext']),len(checks['filters']),len(checks['kinds']),flush=True)
for f,fps,extension in itertools.product(FAMILIES,(30,60,120),(0,3)):
 c=start([f['root']]+[7006400]*extension);trigger(c);assert leaves(c)[0]['lifetime']==10
 expired=None
 for frame in range(1,10*fps+6):
  step(c,1/fps)
  if not leaves(c):expired=frame;break
 assert expired is not None and abs(expired-10*fps)<=3,(f,fps,extension,expired)
 record('lifetime',c,root=f['root'],fps=fps,extension=extension,expiredFrame=expired,values=verify(c,1))
print('PASS lifetime',len(checks['lifetime']),flush=True)
for f,copies in itertools.product(FAMILIES,(1,3)):
 c=start([f['root']]*copies);trigger(c);refresh=[]
 for frame in range(1,18*60+6):
  step(c,1/60)
  if frame in (4*60,8*60):
   granted=trigger(c);assert granted.count(f['leaf'])==1 and len(leaves(c))==1 and leaves(c)[0]['lifetime']==10
   refresh.append(dict(frame=frame,grants=granted,life=leaves(c)[0]['lifetime']))
  if not leaves(c):break
 assert abs(frame-18*60)<=3
 record('refresh',c,root=f['root'],copies=copies,refresh=refresh,expiredFrame=frame,values=verify(c,1))
print('PASS refresh',len(checks['refresh']),flush=True)
for f,fps in itertools.product(FAMILIES,(30,60,120)):
 by_copies={}
 for copies in (1,3):
  c=start([f['root']]*copies);events=[]
  for frame in range(fps*3):
   c.qualify();c.damage();before=len(c.grants);c.update(1/fps)
   grants=c.grants[before:]
   if grants.count(f['leaf']):events.append(frame)
   assert len(leaves(c))<=1
  by_copies[copies]=events
  assert 2<=len(events)<fps
  record('continuous',c,root=f['root'],fps=fps,copies=copies,leafFrames=events,values=verify(c,f['rate']))
 assert by_copies[1]==by_copies[3],by_copies
for f in FAMILIES:
 c=start([f['root']]);events=[]
 for frame in range(180):
  if frame in (20,40):c.grant(f['root'])
  c.qualify()
  if frame>=60:c.damage()
  before=len(c.grants);c.update(1/60)
  if f['leaf'] in c.grants[before:]:events.append(frame)
  assert len(leaves(c))<=1
 assert len(events)>5,events
 record('staggered',c,root=f['root'],fps=60,addedFrames=[20,40],leafFrames=events,values=verify(c,f['rate']))
print('PASS continuous/staggered',len(checks['continuous']),len(checks['staggered']),flush=True)
for f in FAMILIES:
 c=start([f['root']]);trigger(c);ptr=struct.unpack('<Q',c.u.mem_read(OBJ+8,8))[0]
 while struct.unpack('<i',c.u.mem_read(ptr+8,4))[0]!=f['leaf']:ptr=struct.unpack('<Q',c.u.mem_read(ptr+0x38,8))[0]
 c.u.mem_write(ptr+0x68,struct.pack('<I',0x40000));record('disabled',c,root=f['root'],values=verify(c,1))
 for other in (False,True):
  roots=[f['root']]+([next(r for r in ROOTS if r!=f['root'])] if other else [])
  c=start(roots);trigger(c);c.invoke(0x505280,[OBJ,0]);step(c);step(c)
  assert (f['leaf'] in [n['id'] for n in c.nodes()])==other
  record('removal',c,root=f['root'],otherLevelPresent=other,nodes=c.nodes(),values=verify(c,expected(roots) if other else 1))
print('PASS disabled/removal',len(checks['disabled']),len(checks['removal']),flush=True)
out=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),paramHashes=hashes,
 effects=EFFECTS,rootsByEffect=MAPPING,families=FAMILIES,duration=10,rearmPeriod=1,tagSets=len(representatives),
 checks=checks,native=dict(selection='4FEA30 → E6E150 → E6E3B0',damage='504D30',update='5057D0 → 50ACD0',grant='3C7FD0 → 3C80A0 → 3DB410',insert='50A4C0 → 50D060',attack='E6D530 → 502830',remove='505280'),
 stubs=sorted(stubs|{'E6D630 actual AtkParam_Pc lookup','explicit inventory, actor identity and damage/source/exclusion inputs'}),
 limitations=['No full collision, source damage construction, final HP write, DLL hooks, equipment rebuild, death, reload or multiplayer.',
 'Source kind 5 is excluded by the attack getter; its complete gameplay meaning is not established here.',
 'Staggered root insertion changes periodic rearm opportunities without increasing same-level magnitude; full equipment scheduling remains untraced.',
 'State 2374 is shared across grades: another grade retains an existing leaf after its own root is removed; this is container removal, not complete unequip.',
 'Extra row 9762 in effect 10001 is included in native delivery and numeric comparisons, not claimed to have no possible external consumer.'],gameplayVerified=False)
a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('PASS total',sum(map(len,checks.values())),flush=True)
