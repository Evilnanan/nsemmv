"""Native effect-duration stacking, countdown, pulses and recipient ownership.

Pinned equipment/parameter selection, real grants, target qualification,
instance operations and timers run original instructions. Actor identity,
team codes and incoming effect IDs are explicit fixtures, not live co-op.
"""
import argparse,itertools,json,math,struct
from pathlib import Path
from native_effect_runtime import BASE,OBJ,STOP,Chain,Inputs,sha
from native_ailment_runtime import Ailment
from unicorn.x86_const import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','output'):p.add_argument(name,type=Path)
a=p.parse_args();inputs=x=Inputs(a.exe,a.extracted)
raw=a.extracted.with_suffix('.AttachEffectParam.param').read_bytes();rows=Inputs.table(raw,0x44)
assert sha(raw)=='ae8128ed510a532d0fa7cb56fa9c86e4a44c9d815dd4ee01c05821d5f50a9827'
assert sha(x.param)=='07ec636c5565d4551efeb53e6f08bc633b2aa4f2129f13c61b0638d69b1bc176'
magicraw=a.extracted.with_suffix('.Magic.param').read_bytes();bulletraw=a.extracted.with_suffix('.Bullet.param').read_bytes()
assert sha(magicraw)=='17742eeafe4fade863f3a7ee5f7ff483bd4897f765802fe4a1954dfa8107b63e'
assert sha(bulletraw)=='ddce4888040a061cf982a237e8f6e3ddce5f2162a238865a072f75d27b5e9d44'
magicrows=Inputs.table(magicraw,0xac);bulletrows=Inputs.table(bulletraw,0x15c)
magicids=[struct.unpack_from('<i',magicraw,0x40+i*24)[0] for i in range(struct.unpack_from('<H',magicraw,10)[0])]
bulletids=[struct.unpack_from('<i',bulletraw,0x40+i*24)[0] for i in range(struct.unpack_from('<H',bulletraw,10)[0])]
families=[]
for id,rate,category in ((330600,1.3,0),(7006400,1.5,0),(8330500,2,10),(8851300,1.45,10),(8851350,1.6,10)):
 r=x.spells[str(id)];attach=x.x['tables']['AttachEffectParam'][str(id)]
 assert attach['passiveSpEffectId_1']==id and attach['exclusivityId']==-1
 assert all(attach[k]==-1 for k in ('passiveSpEffectId_2','passiveSpEffectId_3','permanentSpEffectId'))
 assert (r['stateInfo'],r['spCategory'],r['effectEndurance'])==(193,category,-1)
 assert math.isclose(r['extendLifeRate'],rate,rel_tol=1e-6)
 assert {k for k,v in r.items() if v!=x.spells['7006400'][k]}<={'extendLifeRate','spCategory','iconId','saveCategory','spEffectTextId_1'}
 assert struct.unpack_from('<f',x.rows[id],0x310)[0]==r['extendLifeRate']
 families.append(dict(effect=id,root=id,rate=r['extendLifeRate'],category=category))
familymap={f['root']:f for f in families}
spell_sources=[]
for magic,leaf in ((4460,1446000),(6050,1605000),(6450,1645000),(6971,1697100),(6840,1685000)):
 r=x.x['tables']['Magic'][str(magic)]
 assert r['refCategory1']==2 and r['refId1']==leaf
 assert magicids.count(magic)==1 and magicrows[magic][0x1e]==2 and struct.unpack_from('<i',magicrows[magic],0x68)[0]==leaf
 spell_sources.append(dict(magic=magic,leaf=leaf,category=2,name=x.x['texts']['zh_CN']['MagicName'][str(magic)]))
for magic,bullet,leaf in ((6430,10643000,1643000),(6431,10643100,1643100),(6600,10660000,1660000)):
 r=x.x['tables']['Magic'][str(magic)];b=x.x['tables']['Bullet'][str(bullet)]
 assert r['refCategory1']==1 and r['refId1']==bullet and b['spEffectId0']==leaf
 assert magicids.count(magic)==bulletids.count(bullet)==1
 assert magicrows[magic][0x1e]==1 and struct.unpack_from('<i',magicrows[magic],0x68)[0]==bullet
 assert struct.unpack_from('<i',bulletrows[bullet],0x6c)[0]==leaf
 spell_sources.append(dict(magic=magic,bullet=bullet,leaf=leaf,category=1,name=x.x['texts']['zh_CN']['MagicName'][str(magic)]))
leaves=[s['leaf'] for s in spell_sources]+[7036901]
for leaf in leaves:
 r=x.spells[str(leaf)];assert r['isExtendSpEffectLife']==int(leaf!=7036901)
 assert bool(x.rows[leaf][0x164]&32)==bool(r['isExtendSpEffectLife'])
 assert r['invocationConditionsStateChange1']==r['invocationConditionsStateChange2']==r['invocationConditionsStateChange3']==0
 assert r['effectEndurance']>0
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


class Pair(Actor):
 def __init__(self):
  super().__init__();self.remote=False
  self.u.mem_map(OBJ+0x60000,0x20000)
  self.u.mem_write(OBJ+0x62000,bytes(self.u.mem_read(OBJ+0x6000,0x800)))
  self.q(OBJ+0x62190,OBJ+0x63000);self.q(OBJ+0x63010,OBJ+0x62000)
  self.u.mem_write(OBJ+0x6074,b"\2");self.u.mem_write(OBJ+0x62074,b"\1")
 def hook(self,u,addr,size,user):
  if addr==BASE+0x3c80a0 and self.remote:
   u.reg_write(UC_X86_REG_R8,OBJ+0x62000)
  super().hook(u,addr,size,user)
 def addsource(self,id):
  self.invoke(0x50d060,[OBJ+0x63000,id,OBJ+0xa00,-1,0,0x3f800000,0,0,16])
  self.stepsource(0)
 def stepsource(self,dt):
  self.invoke(0x5057d0,[OBJ+0x63000,0,0],{UC_X86_REG_XMM1:1})
  self.invoke(0x50acd0,[OBJ+0x63000,0,0],{UC_X86_REG_XMM1:dt})
 def sourcelife(self,id):
  node=struct.unpack('<Q',self.u.mem_read(OBJ+0x63008,8))[0]
  found=[]
  while node:
   if struct.unpack('<i',self.u.mem_read(node+8,4))[0]==id:
    found.append(struct.unpack('<f',self.u.mem_read(node+0x4c,4))[0])
   node=struct.unpack('<Q',self.u.mem_read(node+0x38,8))[0]
  assert len(found)==1
  return found[0]

class Countdown(Chain):
 def step(self,dt):self.qualify();self.update(dt)
 def life(self,leaf):
  values=[n['lifetime'] for n in self.nodes() if n['id']==leaf]
  assert len(values)<=1
  return values[0] if values else None
 def hp(self):
  self.q(OBJ+0x10,0);self.invoke(0x506ec0,[OBJ,1000,OBJ+0x800,OBJ+0x808,OBJ+0x820,0]);self.q(OBJ+0x10,OBJ+0x6000)
  return list(struct.unpack('<7i',self.u.mem_read(OBJ+0x820,28)))
def f32(v):return struct.unpack('<f',struct.pack('<f',v))[0]
def multiplier(ids):
 result=1.;seen=set()
 for id in ids:
  f=familymap[id]
  if f['category']==0 and id in seen:continue
  seen.add(id);result=f32(result+f32(f['rate']-1))
 return result
def prepare(ids,leaf):
 c=Countdown(x)
 for id in ids+[leaf]:c.insert(id)
 c.step(0);return c
checks={k:[] for k in ('selection','countdown','mixed','lifetime','refresh','transition','healing','recipient')};stubs=set()
def record(group,c,**row):checks[group].append(row);stubs.update(c.stubs)
for f,copies,hero in itertools.product(families,(1,2,3,6),range(11)):
 id=f['effect'];c=Selection([[id]]*copies,hero);bits=c.select();selected=[]
 for i in range(copies):
  assert i*6 in bits
  c.invoke(0xe6e150,[OBJ+0x9200,id]);selected.append(c.invoke(0xe6e3b0,[OBJ+0x9200,0])&0xffffffff)
 assert selected==[id]*copies
 d=prepare(selected,1605000);d.step(1);life=d.life(1605000);expected=f32(30-f32(1/multiplier(selected)))
 assert math.isclose(life,expected,abs_tol=1e-5)
 count=sum(n['id']==id for n in d.nodes());assert count==(copies if f['category']==10 else 1)
 record('selection',c,effect=id,copies=copies,hero=hero,selected=selected,instances=count,multiplier=multiplier(selected),remaining=life);stubs.update(d.stubs)
print('PASS selection',len(checks['selection']),flush=True)
for f,copies,leaf in itertools.product(families,(1,2,3,6),leaves):
 ids=[f['root']]*copies;c=prepare(ids,leaf);before=c.life(leaf);c.step(1);after=c.life(leaf)
 scale=multiplier(ids) if leaf!=7036901 else 1
 assert math.isclose(after,f32(before-f32(1/scale)),abs_tol=1e-5)
 record('countdown',c,effect=f['effect'],copies=copies,leaf=leaf,before=before,after=after,multiplier=scale)
print('PASS countdown',len(checks['countdown']),flush=True)
sets=[[330600,7006400],[7006400,330600],[7006400,8851300,8851350],[8330500,8851300]*3,[f['root'] for f in families]]
for ids,leaf in itertools.product(sets,leaves):
 c=prepare(ids,leaf);before=c.life(leaf);c.step(1);after=c.life(leaf);scale=multiplier(ids) if leaf!=7036901 else 1
 assert math.isclose(after,f32(before-f32(1/scale)),abs_tol=1e-5)
 record('mixed',c,roots=ids,leaf=leaf,multiplier=scale,before=before,after=after)
print('PASS mixed',len(checks['mixed']),flush=True)
time_sets=[[],[7006400],[7006400]*3,[8851300]*3,[330600,7006400],[f['root'] for f in families]]
for ids,leaf,fps in itertools.product(time_sets,(1605000,7036901),(30,60,120)):
 c=prepare(ids,leaf);duration=x.spells[str(leaf)]['effectEndurance']*(multiplier(ids) if leaf!=7036901 else 1);expired=None
 for frame in range(1,math.ceil((duration+1)*fps)+1):
  c.step(1/fps)
  if c.life(leaf) is None:expired=frame;break
 assert expired is not None and abs(expired/fps-duration)<=.12+3/fps,(ids,leaf,fps,duration,expired)
 record('lifetime',c,roots=ids,leaf=leaf,fps=fps,expectedSeconds=duration,expiredFrame=expired)
print('PASS lifetime',len(checks['lifetime']),flush=True)
for ids,leaf in itertools.product(time_sets,(1605000,1685000)):
 c=prepare(ids,leaf)
 for _ in range(300):c.step(1/60)
 before=c.life(leaf);result=c.insert(leaf);c.step(0);after=c.life(leaf)
 assert after==x.spells[str(leaf)]['effectEndurance'] and after>before
 c.step(1);remaining=c.life(leaf);assert math.isclose(remaining,f32(after-f32(1/multiplier(ids))),abs_tol=1e-5)
 record('refresh',c,roots=ids,leaf=leaf,before=before,after=after,remaining=remaining,insertResult=result)
print('PASS refresh',len(checks['refresh']),flush=True)
for f in families:
 c=prepare([],1685000);c.step(1);before=c.life(1685000);index=c.insert(f['root']);c.step(1);during=c.life(1685000)
 assert math.isclose(during,f32(before-f32(1/f['rate'])),abs_tol=1e-5)
 c.invoke(0x505280,[OBJ,index]);c.step(1);after=c.life(1685000)
 assert math.isclose(after,during-1,abs_tol=1e-5) and all(n['id']!=f['root'] for n in c.nodes())
 record('transition',c,effect=f['effect'],before=before,during=during,after=after)
print('PASS transition',len(checks['transition']),flush=True)
for leaf,copies,fps in itertools.product((1643000,1685000),(0,1,3),(30,60,120)):
 ids=[7006400]*copies;c=prepare(ids,leaf);events=[];duration=x.spells[str(leaf)]['effectEndurance']*multiplier(ids);amount=-x.spells[str(leaf)]['changeHpPoint'];expired=None
 for frame in range(math.ceil((duration+1)*fps)+1):
  packet=c.hp()
  if any(packet):
   assert packet==[amount,0,amount,0,0,0,0],packet
   events.append(frame)
  if c.life(leaf) is None:expired=frame;break
  c.step(1/fps)
 assert expired is not None and abs(expired/fps-duration)<=.12+3/fps
 assert abs(len(events)-duration)<=2,(leaf,copies,fps,len(events),duration)
 assert all(abs((b-a)/fps-1)<=2/fps for a,b in zip(events,events[1:]))
 record('healing',c,leaf=leaf,copies=copies,fps=fps,amount=amount,pulseFrames=events,totalPacketHealing=amount*len(events),expiredFrame=expired)
print('PASS healing',len(checks['healing']),flush=True)
for source_copies,recipient_copies,leaf in itertools.product((0,1,3),(0,1,3),(1660000,1643001)):
 c=Pair()
 for _ in range(source_copies):c.addsource(7006400)
 c.addsource(1660000)
 assert c.sourcelife(1660000)==80
 for _ in range(recipient_copies):c.grant(7006400)
 c.remote=True;c.grant(leaf);c.qualify();c.update(0)
 before=[n['lifetime'] for n in c.nodes() if n['id']==leaf]
 assert before==[x.spells[str(leaf)]['effectEndurance']],(source_copies,recipient_copies,leaf,c.nodes())
 c.qualify();c.update(1);after=[n['lifetime'] for n in c.nodes() if n['id']==leaf]
 assert len(after)==1 and math.isclose(after[0],f32(before[0]-f32(1/(1.5 if recipient_copies else 1))),abs_tol=1e-5)
 c.stepsource(1);source_after=c.sourcelife(1660000)
 assert math.isclose(source_after,f32(80-f32(1/(1.5 if source_copies else 1))),abs_tol=1e-5)
 record('recipient',c,sourceCopies=source_copies,recipientCopies=recipient_copies,leaf=leaf,before=before[0],after=after[0],sourceBefore=80,sourceAfter=source_after)
print('PASS recipient',len(checks['recipient']),flush=True)
output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),attachParamSha256=sha(raw),magicParamSha256=sha(magicraw),bulletParamSha256=sha(bulletraw),families=families,spellSources=spell_sources,checks=checks,
 native=dict(selection='4FEA30 → E6E150 → E6E3B0',grant='3C7FD0 → 3C80A0 → 3DB410 → 50A4C0 → 50D060',target='50C6C0 → 52CC60',lifecycle='5057D0 → 50ACD0 → 511B80',remove='505280',healing='506EC0'),
 stubs=sorted(stubs|{'synthetic positive-slot inventory; draw availability not inferred for catalog-only rows',
 'source and recipient identity/team codes 1/2 are explicit; original targeting predicates execute',
 '3C7FD0 caller supplies its ordinary context; at 3C80A0 entry R8 is set to a separate source actor for recipient cases',
 'separate source effect list populated by native insertion, qualification and update; source and recipient do not share effect nodes',
 'pinned Magic/Bullet references identify example payloads; complete casting, projectile creation/collision and network transport not executed',
 'HP recovery packets run original consumer; final current-HP write, caps and recipient healing modifiers outside scope',
 '30/60/120 Hz isolated timelines; removal targets one native instance index, not a full equipment rebuild'}),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS total',sum(map(len,checks.values())),flush=True)
