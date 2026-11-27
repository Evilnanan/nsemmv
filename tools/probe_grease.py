"""Trace Hotfix1 grease item paths, conditional buffs, extension and overlap.

Pinned HKS/behavior references and original Type67 dispatch establish the seed
path. Native equipment selection, self-grant, timers and tagged attack getters
execute with explicit actor/inventory fixtures. Full gameplay is not executed.
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
from effect_behavior_graph import BehaviorGraph
from unicorn.x86_const import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','animations','behavior','script','definitions','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted)
raw=a.extracted.with_suffix('.AttachEffectParam.param').read_bytes();rows=Inputs.table(raw,0x44)
atkraw=a.extracted.with_suffix('.AtkParam_Pc.param').read_bytes();atkrows=Inputs.table(atkraw,0x1d0)
script=a.script.read_bytes();definitions=a.definitions.read_bytes()
assert sha(script)=='96339bb15f57559cd42a940d616fcc2a18a10f50845cfc22b46b356ab66c3b29'
text=script.decode('utf-8-sig').replace('\r\n','\n')
assert 'elseif item_type == ITEM_QUICK_WEAPON_ENCHANT then' in text
assert 'ITEM_QUICK_WEAPON_ENCHANT = 16' in definitions.decode('utf-8-sig')
graph=BehaviorGraph(a.behavior);paths=[]
for index,suffix in enumerate(('Normal','Dash','Step','AttackRight','AttackLeft')):
 for upper in ('','_Upper'):
  state='QuickItemEnchant'+suffix+upper
  path=graph.state(state);assert path['animation']==f'a000_{55200+index*10:06}'
  assert 'ExecEventHalfBlend(Event_QuickItemEnchant'+suffix+',' in text
  paths.append(path)
animations=json.loads(a.animations.read_text());rawtae={};events=[]
for bundle in animations['bundles']:
 for track in bundle['taes']:
  if track['ID']!=2000:continue
  b=a.animations.with_name(a.animations.name+'.2000.tae').read_bytes();assert sha(b)==track['sha256'];rawtae[2000]=(b,track['sha256'])
  for animation in track['animations']:
   for event in animation['events']:
    if event['Type']==67 and struct.unpack_from('<i',bytes.fromhex(event['hex']))[0] in (7030901,7030911,7030921,7030931):
     assert animation['ID'] in (50580,55200,55210,55220,55230,55240)
     events.append(dict(tae=2000,animation=animation['ID'],seed=struct.unpack_from('<i',bytes.fromhex(event['hex']))[0],**event))
assert len(events)==24
families=[]
for root,state,effects in [(7030900,2012,[13000,7030900]),(7030910,2386,[6030900]),(7030920,2387,[6030901]),(7030930,2388,[6030902])]:
 for effect in effects:
  attach=x.x['tables']['AttachEffectParam'][str(effect)];assert attach['passiveSpEffectId_1']==root and attach['exclusivityId']==-1
 r=x.spells[str(root)];leaf=x.spells[str(root+2)]
 assert r['stateInfo']==state and r['spCategory']==10 and r['effectEndurance']==-1
 assert x.spells[str(root+1)]['replaceSpEffectId']==root+2
 assert x.spells[str(root+1)]['invocationConditionsStateChange1']==leaf['invocationConditionsStateChange1']==state
 assert leaf['effectEndurance']==30 and leaf['spCategory']==20 and leaf['replaceSpEffectId']==root+3
 gate=x.spells[str(root+3)];tail=x.spells[str(root+4)]
 assert gate['invocationConditionsStateChange1']==2389 and gate['cycleOccurrenceSpEffectId']==root+4
 assert {k:(v,tail[k]) for k,v in leaf.items() if v!=tail[k]}=={'replaceSpEffectId':(root+3,-1)}
 families.append(dict(effects=effects,root=root,state=state,seed=root+1,leaf=root+2,gate=root+3,tail=root+4,duration=30,rate=leaf['physicsAttackRate'],tag=leaf['magicSubCategoryChange1']))
assert x.x['tables']['AttachEffectParam']['6030903']['passiveSpEffectId_1']==7030940
assert x.spells['7030940']['stateInfo']==2389 and x.spells['7030940']['spCategory']==10
pairs=[]
for key,r in x.spells.items():
 gate=x.spells.get(str(r['replaceSpEffectId']),{})
 if gate.get('invocationConditionsStateChange1')!=2389:continue
 leaf=x.spells.get(str(gate['cycleOccurrenceSpEffectId']),{})
 if not leaf:continue
 assert {k:(v,leaf[k]) for k,v in r.items() if v!=leaf[k]}=={'replaceSpEffectId':(r['replaceSpEffectId'],-1)}
 assert gate['replaceSpEffectId']==-1 and leaf['cycleOccurrenceSpEffectId']==-1
 pairs.append(dict(source=int(key),gate=r['replaceSpEffectId'],leaf=gate['cycleOccurrenceSpEffectId'],duration=r['effectEndurance'],extension=leaf['effectEndurance'],category=r['spCategory']))
assert len(pairs)==70
pairmap={v['source']:v for v in pairs};goods=[]
for key,r in x.x['tables']['EquipParamGoods'].items():
 refs={k:v for k,v in r.items() if 'refid' in k.lower() and v in pairmap}
 if not refs:continue
 assert r['refCategory']==2 and r['goodsUseAnim']==(50 if key=='1690' else 16) and len(refs)==6
 goods.append(dict(id=int(key),name=x.x['texts']['zh_CN']['GoodsName'][key],animationType=r['goodsUseAnim'],refs=refs))
assert len(goods)==11 and {v for g in goods for v in g['refs'].values()}==set(pairmap)-{f['leaf'] for f in families}
attacks={int(k):[r['subCategory'+str(i)] for i in range(1,6)] for k,r in x.x['tables']['AtkParam_Pc'].items()}
for id,tags in attacks.items():assert tags==[atkrows[id][o] for o in (0x4e,0x4f,0x1c8,0x1c9,0x1ca)]
representatives={}
for id,tags in attacks.items():representatives.setdefault(tuple(sorted(set(tags)-{0})),id)
melee=next(id for id,t in attacks.items() if 130 in t)
nonmelee=next(id for id,t in attacks.items() if 130 not in t)
MAN=OBJ+0x8000;OUT=OBJ+0x9000;BITS=OBJ+0x9100
class Selection(Chain):
 def __init__(self,slots,hero=1):
  super().__init__(x);self.slots=slots;self.hero=hero;self.cache={};self.q(OBJ+0x7118,STOP+0x900)
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
   u.mem_write(instance+0x18,struct.pack('<3i',*(effects+[-1]*3)[:3]));u.mem_write(ptr,bytes(24));self.q(ptr+8,instance);u.mem_write(ptr+0x10,struct.pack('<I',0x80000000|2000100));ret(ptr)
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

class Shock(Actor):
 def __init__(self):
  self.free=[];self.frame=0;self.shots=[]
  super().__init__()
 def hook(self,u,address,size,user):
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP)
   u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  pc=address-BASE
  if pc==0x3ced90:
   self.stubs.add('3CED90 synthetic animation-owner context');ret(OBJ+0xd000)
  elif pc==0x4d1b20:
   self.stubs.add('4D1B20 ordinary locally active actor');ret()
  elif pc==0x26909a0:
   self.stubs.add('26909A0 security cookie');ret(u.reg_read(UC_X86_REG_RAX))
  elif pc==0x3975d0:
   self.stubs.add('3975D0 records native emission request; full collision is not simulated')
   payload=bytes(u.mem_read(u.reg_read(UC_X86_REG_R9),8))
   self.shots.append(dict(frame=self.frame,behavior=u.reg_read(UC_X86_REG_RDX),payload=payload.hex()));ret(1)
  elif address==STOP+0x108:
   ptr=u.reg_read(UC_X86_REG_RDX)
   assert OBJ+0x20000<=ptr<OBJ+0x40000 and ptr not in self.free
   self.free.append(ptr);ret()
  elif pc==0x214e8d0 and self.free:
   assert u.reg_read(UC_X86_REG_RCX)==0x88
   ret(self.free.pop())
  else:super().hook(u,address,size,user)
 def select(self,event):
  raw,hash=rawtae[event['tae']];tae=NativeTae(self,raw,hash)
  assert tae.id==event['tae'] and tae.bank==255
  ctx=OBJ+0xd100;self.u.mem_write(ctx,bytes(0x40))
  for _ in range(1000):
   if not self.invoke(0x27d0400,[tae.animations[event['animation']],ctx]):break
   typ=struct.unpack('<I',self.u.mem_read(ctx,4))[0]
   if typ!=67:continue
   payload=struct.unpack('<Q',self.u.mem_read(ctx+8,8))[0]
   if struct.unpack('<i',self.u.mem_read(payload,4))[0]!=event['seed']:continue
   assert bytes(self.u.mem_read(payload,16))==bytes.fromhex(event['hex'])
   self.ctx=ctx;self.q(OBJ+0x8018,OBJ+0x6000);return
  raise AssertionError('missing native Type 67 event')
 def event(self):
  # Type 67 is maintained by the caller during its active animation window;
  # its own dispatch does not use ctx.active as an on/off condition.
  self.u.mem_write(self.ctx+0x18,b'\1')
  self.invoke(0x410ca0,[OBJ+0x8000,self.ctx])
 def emit(self):self.invoke(0x50aa20,[OBJ])


class Grease(Shock):
 def hook(self,u,address,size,user):
  if address-BASE==0xe6d630:
   id=u.reg_read(UC_X86_REG_R8)&0xffffffff;assert u.reg_read(UC_X86_REG_RDX)==1
   wrapper=u.reg_read(UC_X86_REG_RCX);u.mem_write(OBJ+0xa800,atkrows[id])
   u.mem_write(wrapper,struct.pack('<iii4xQ',id,0,1,OBJ+0xa800))
   sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
   self.stubs.add('E6D630 actual AtkParam_Pc row lookup')
  else:super().hook(u,address,size,user)
 def attackrow(self,id,kind=None):
  if kind is None:kind=1 if 251 in attacks[id] else 0
  self.u.mem_write(OBJ+0xa800,atkrows[id]);self.q(OBJ+0xb010,OBJ+0xa800)
  self.invoke(0xe6d530,[OBJ+0xb000,OBJ+0x814])
  tags={r for r in [x.x['tables']['AtkParam_Pc'][str(id)]['subCategory'+str(n)] for n in range(1,6)] if r}
  assert int.from_bytes(self.u.mem_read(OBJ+0x814,32),'little')==sum(1<<n for n in tags)
  self.u.mem_write(OBJ+0x808,struct.pack('<iiB',id,1,kind))
  self.invoke(0x502830,[OBJ,OBJ+0x800,-1,-1])
  return [struct.unpack('<f',self.u.mem_read(OBJ+0x800+o,4))[0] for o in(0x90,0xa4,0xa8,0xac,0xb0)]

checks={k:[] for k in ('selection','dispatch','filters','lifetime','refresh','overlap','goods','disabled')};stubs=set()
def step(c,dt=1/60,n=1):
 for _ in range(n):c.qualify();c.update(dt)
def active(c):return [r['id'] for r in c.nodes() if not r['flags']&0x800c0003]
def verify(c,f,exponent=1):
 values=c.attackrow(melee,0);rate=f['rate']**exponent
 expected=[rate]*5 if f['tag']==130 else [rate,1,1,1,1]
 assert all(math.isclose(v,w,rel_tol=2e-6) for v,w in zip(values,expected)),(values,expected)
 return values
def record(key,c,**row):
 checks[key].append(row);stubs.update(c.stubs)
def start(roots,seed=None):
 c=Grease()
 for root in roots:c.grant(root)
 if seed is not None:c.grant(seed)
 step(c,n=3);return c
# Selection remains separate from actor fixtures; every selected passive root
# is read by the actual native Attach getter before use in the list tests.
for effects in [[i] for f in families for i in f['effects']]+[[6030903],[6030902]*3,[6030903]*3,[6030902,6030903],[7030900,6030900,6030901]]:
 for hero in range(11):
  c=Selection([[e] for e in effects],hero);bits=c.select();selected=[]
  for index,effect in enumerate(effects):
   if index*6 in bits:
    c.invoke(0xe6e150,[OBJ+0x9200,effect]);selected.append(c.invoke(0xe6e3b0,[OBJ+0x9200,0])&0xffffffff)
  assert selected==[x.x['tables']['AttachEffectParam'][str(e)]['passiveSpEffectId_1'] for e in effects]
  record('selection',c,effects=effects,hero=hero,roots=selected)
print('PASS selection', len(checks['selection']), flush=True)
# All six actual animation seed sites, with marker absent/present/duplicated.
for event in events:
 f=next(f for f in families if f['seed']==event['seed'])
 for copies in (0,1,3):
  c=start([f['root']]*copies);c.select(event);c.event();step(c,n=3)
  values=verify(c,f,int(copies>0))
  assert active(c).count(f['leaf'])==int(copies>0)
  record('dispatch',c,animation=event['animation'],seed=event['seed'],copies=copies,values=values,nodes=c.nodes())
print('PASS dispatch', len(checks['dispatch']), flush=True)
# Every distinct actual attack tag set, including untagged negative controls.
f=families[-1];c=start([f['root']],f['seed'])
for tags,id in representatives.items():
 for kind in (0,1,2):
  values=c.attackrow(id,kind);expected=f['rate'] if 130 in tags else 1
  assert all(math.isclose(v,expected,rel_tol=2e-6) for v in values),(id,tags,kind,values,expected)
  record('filters',c,attack=id,tags=tags,kind=kind,values=values)
print('PASS attack filters', len(checks['filters']), flush=True)
for f in families:
 for copies,extension in itertools.product((0,1,3),(0,1,3)):
  c=start([f['root']]*copies+[7030940]*extension,f['seed']);verify(c,f,int(copies>0))
  step(c,29.9);step(c,n=20)
  assert (f['tail'] in active(c))==bool(copies and extension)
  values=verify(c,f,int(bool(copies and extension)))
  record('lifetime',c,root=f['root'],copies=copies,extension=extension,phase='after first 30s',values=values,nodes=c.nodes())
  step(c,30);step(c,n=20);verify(c,f,0)
  assert not any(i in active(c) for i in (f['leaf'],f['tail']))
  record('lifetime',c,root=f['root'],copies=copies,extension=extension,phase='expired',nodes=c.nodes())
 # Same first-phase ID refreshes without multiplying, both before extension
 # and when the previous tail is still present.
 for extension in (0,1):
  c=start([f['root']]+[7030940]*extension,f['seed']);step(c,10)
  for repeat in range(3):
   c.grant(f['seed']);step(c,n=3);values=verify(c,f)
   leaf=next(r for r in c.nodes() if r['id']==f['leaf']);assert 29.8<leaf['lifetime']<=30
   record('refresh',c,root=f['root'],extension=extension,repeat=repeat,values=values,nodes=c.nodes())
 c=start([f['root'],7030940],f['seed']);step(c,29.9);step(c,n=20);verify(c,f)
 for repeat in range(3):
  c.grant(f['seed']);step(c,n=3);values=verify(c,f,2)
  assert active(c).count(f['leaf'])==active(c).count(f['tail'])==1
  record('overlap',c,root=f['root'],repeat=repeat,values=values,nodes=c.nodes())
 step(c,30);step(c,n=20);values=verify(c,f)
 record('overlap',c,root=f['root'],phase='old tail expired; new tail active',values=values,nodes=c.nodes())
print('PASS bonus lifecycle', {k:len(checks[k]) for k in ('lifetime','refresh','overlap')}, flush=True)
# All 66 actual item effects, both hands and all three item levels. The tail
# is byte-equivalent in decoded fields except for the terminating replacement.
for pair in pairs:
 if pair['source'] in [f['leaf'] for f in families]:continue
 for copies in (0,1,3):
  c=start([7030940]*copies,pair['source'])
  step(c,pair['duration']-.1);step(c,n=20)
  assert (pair['leaf'] in active(c))==bool(copies)
  record('goods',c,source=pair['source'],copies=copies,phase='extension',nodes=c.nodes())
  if copies:
   c.grant(pair['source']);step(c,n=3)
   assert pair['source'] in active(c) and pair['leaf'] not in active(c)
   record('goods',c,source=pair['source'],copies=copies,phase='reapplied replaces tail',nodes=c.nodes())
# Disabled leaves must not contribute, even when their root marker is present.
f=families[-1];c=start([f['root']],f['seed'])
node=struct.unpack('<Q',c.u.mem_read(OBJ+8,8))[0]
while node:
 id=struct.unpack('<i',c.u.mem_read(node+8,4))[0]
 if id==f['leaf']:
  flags=struct.unpack('<I',c.u.mem_read(node+0x68,4))[0];c.u.mem_write(node+0x68,struct.pack('<I',flags|0x80000000))
 node=struct.unpack('<Q',c.u.mem_read(node+0x38,8))[0]
values=verify(c,f,0);record('disabled',c,values=values)
output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),
 attachParamSha256=sha(raw),attackParamSha256=sha(atkraw),scriptSha256=sha(script),definitionsSha256=sha(definitions),
 behaviorSha256=graph.metadata['hkxSha256'],taeSha256=rawtae[2000][1],families=families,extensionEffect=6030903,extensionRoot=7030940,
 paths=paths,events=events,pairs=pairs,goods=goods,attackRowCount=len(attacks),attackTagSetCount=len(representatives),checks=checks,
 native=dict(selection='4FEA30 → E6E150 → E6E3B0',tae='27D0F10 → 27D0400 → 410CA0',grant='3C7FD0',lifecycle='50D060 → 5057D0 → 50ACD0',attack='E6D530 → 502830'),
 stubs=sorted(stubs|{'item use decision, full behavior scheduling and actual equipment enchant application are not executed',
 'goods PARAM refs delivered to local actor as explicit fixture; no live weapon damage or multiplayer',
 'animation 50580 seed dispatch checked, but its full gameplay route is not established'}),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS', {k:len(v) for k,v in checks.items()},'tag sets',len(representatives))
