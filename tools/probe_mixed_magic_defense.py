"""Trace pure-holy cocktail defense from native casts to timer and damage gates.

A selected animation window and transfer of the cast's native self-grant
request into a separate native actor are explicit fixtures. Scene selection,
network delivery and final HP damage are not simulated.
"""
import argparse,itertools,json,math,struct
from pathlib import Path
from native_effect_runtime import BASE,OBJ,STOP,Chain,Inputs,sha
from native_ailment_runtime import Ailment
from native_animation_runtime import NativeTae
from effect_behavior_graph import BehaviorGraph
from unicorn.x86_const import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','animations','behavior','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted);i=x;ts=x.x['tables']
hashes={'Magic':'17742eeafe4fade863f3a7ee5f7ff483bd4897f765802fe4a1954dfa8107b63e','Bullet':'ddce4888040a061cf982a237e8f6e3ddce5f2162a238865a072f75d27b5e9d44'}
raws={name:a.extracted.with_suffix('.'+name+'.param').read_bytes() for name in hashes}
for name,raw in raws.items():assert sha(raw)==hashes[name]
assert sha(x.param)=='07ec636c5565d4551efeb53e6f08bc633b2aa4f2129f13c61b0638d69b1bc176'
rows=Inputs.table(raws['Magic'],0xac);bullets=Inputs.table(raws['Bullet'],0x15c)
core_path=Path(__file__).resolve().parent.parent/'data/effect-mixed-magic-evidence.json';core=json.loads(core_path.read_text())
assert core['regulationSha256']==x.x['hashes']['regulation.bin'] and core['effects']==[7034200,7034201] and core['root']==9200006
m=ts['Magic']['8003'];assert (m['refType'],m['refCategory2'],m['refId2'],m['spEffectCategory'])==(128,2,1800300,3)
assert struct.unpack_from('<i',rows[8003],0x6c)[0]==1800300
magic_entries={struct.unpack_from('<i',raws['Magic'],0x40+n*24)[0]:struct.unpack_from('<Q',raws['Magic'],0x50+n*24)[0] for n in range(struct.unpack_from('<H',raws['Magic'],10)[0])}
name_start=magic_entries[8003];name_end=name_start;assert name_start
while raws['Magic'][name_end:name_end+2]!=b'\0\0':name_end+=2
pure_name=raws['Magic'][name_start:name_end].decode('utf-16-le');assert pure_name=='[Magic Cocktail] Pure Holy - Divine Protection'
for id,cat,condition,multiplier in ((1800300,160,0,.9),(7034204,20,2047,.8)):
 r=x.spells[str(id)];assert (r['effectEndurance'],r['spCategory'],r['invocationConditionsStateChange1'],r['isExtendSpEffectLife'],r['isContractSpEffectLife'])==(30,cat,condition,1,1)
 assert all(math.isclose(r[k+'DamageCutRate'],multiplier,abs_tol=1e-6) for k in ('neutral','slash','blow','thrust','magic','fire','thunder','dark'))
# Name/reference binding for the player-facing overlap example.
assert x.x['texts']['zh_CN']['MagicName']['6600']=='黄金树立誓'
assert ts['Magic']['6600']['refId1']==10660000 and ts['Bullet']['10660000']['spEffectId0']==1660000
assert struct.unpack_from('<i',rows[6600],0x68)[0]==10660000
assert ts['SpEffectParam']['1660000']['spCategory']==160
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
  if pc in (0x3c8be0,0x50a630) and u.reg_read(UC_X86_REG_RDX)==7034204:
   (self.bonusAdded if pc==0x3c8be0 else self.bonusKept).append(7034204)
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

class Prayer(Chain):
 def __init__(self,magic=6050):
  super().__init__(i);self.magic=magic;self.requests=[];self.costs=[]
  self.q(OBJ+0x6190,OBJ);self.q(OBJ+0x61b8,OBJ+0x9000)
  self.q(OBJ+0x9060,OBJ+0x9100);self.q(OBJ+0x9100,OBJ+0x9200);self.q(OBJ+0x9218,STOP+0x200)
  self.q(OBJ+0x6450,STOP+0x201);self.q(OBJ+0x6418,STOP+0x202);self.q(OBJ+0x6548,STOP+0x203)
  self.q(OBJ+0x6460,STOP+0x204)
  self.q(OBJ+0x6100,OBJ+0x6000)
  address=BASE+0x40ece6+0x3808562;self.mapped(self.u,0,address,8,0,None);self.q(address,OBJ+0xd000);self.q(OBJ+0xd010,OBJ+0xd100)
 def hook(self,u,address,size,user):
  pc=address-BASE
  def end(value=0):
   u.reg_write(UC_X86_REG_RAX,value & 0xffffffffffffffff);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if address==STOP+0x200:
   out=u.reg_read(UC_X86_REG_RDX);u.mem_write(out,struct.pack('<I',self.magic));end(out)
  elif address==STOP+0x201:end(-1)
  elif address==STOP+0x202:
   out=u.reg_read(UC_X86_REG_RDX);u.mem_write(out,struct.pack('<4f',1,1,1,1));end(out)
  elif address==STOP+0x203:end(u.reg_read(UC_X86_REG_RDX))
  elif address==STOP+0x204:end(0)
  elif pc==0xe926c0:
   out=u.reg_read(UC_X86_REG_RCX);id=u.reg_read(UC_X86_REG_RDX)&0xffffffff
   u.mem_write(OBJ+0xb000,rows[id]);u.mem_write(out,struct.pack('<IiQ',id,6,OBJ+0xb000));end(out)
  elif pc in (0x3ced90,0x4d1b20,0x3d74f0,0xb31990):end(OBJ+0xd800 if pc==0x3ced90 else 0)
  elif pc==0x4b1b90:end(OBJ+0xd900)
  elif pc==0x3c7f40:
   self.requests.append(dict(target=u.reg_read(UC_X86_REG_RCX),id=u.reg_read(UC_X86_REG_RDX)&0xffffffff));end()
  elif pc==0x384a30:
   obj=u.reg_read(UC_X86_REG_RCX);self.costs.append(list(struct.unpack('<5i',u.mem_read(obj+0xb4,20))));end()
  else:super().hook(u,address,size,user)
 def event(self,payload,active=1):
  self.q(OBJ+0x8018,OBJ+0x6000);self.q(OBJ+0x8108,OBJ+0x8200);self.q(OBJ+0x8120,OBJ+0x8300)
  self.u.mem_write(OBJ+0x8118,bytes([active]));self.u.mem_write(OBJ+0x8200,bytes.fromhex(payload))
  self.invoke(0x40eb30,[OBJ+0x8000,OBJ+0x8100])

class Event(Actor):
 def __init__(self):super().__init__();self.shots=[];self.frame=0;self.bonusAdded=[];self.bonusKept=[]
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if pc in(0x3ced90,0x4d1b20):ret(OBJ+0xd800 if pc==0x3ced90 else 0)
  elif pc==0x3975d0:self.shots.append(dict(frame=self.frame,behavior=u.reg_read(UC_X86_REG_RDX)));ret(1)
  else:super().hook(u,address,size,user)
 def event(self,payload):
  self.q(OBJ+0xd018,OBJ+0x6000);self.q(OBJ+0xd108,OBJ+0xd200)
  self.u.mem_write(OBJ+0xd100,struct.pack('<I',67));self.u.mem_write(OBJ+0xd118,b'\1');self.u.mem_write(OBJ+0xd200,payload)
  self.invoke(0x410ca0,[OBJ+0xd000,OBJ+0xd100])
 def defense(self):
  self.u.mem_write(OBJ+0x800,bytes(0x200));self.invoke(0x503800,[OBJ,OBJ+0x500,OBJ+0x520,OBJ+0x540,OBJ+0x800]);return list(struct.unpack('<5f',self.u.mem_read(OBJ+0x500,20)))

anims=json.loads(a.animations.read_text());assert anims['bundles'][0]['sha256']=='806e6b218d747277ab45e14f45ca80b9ecf8c13ada22f89db2d3ef23caa62b2a'
t=next(t for b in anims['bundles'] for t in b['taes'] if t['ID']==2528)
raw=Path(str(a.animations)+'.2528.tae').read_bytes();c=Event();loader=NativeTae(c,raw,t['sha256']);ctx=OBJ+0xd100;c.u.mem_write(ctx,bytes(0x40));events={}
while c.invoke(0x27d0400,[loader.animations[45010],ctx]):
 typ=struct.unpack('<I',c.u.mem_read(ctx,4))[0]
 if typ not in (64,67):continue
 ptr=struct.unpack('<Q',c.u.mem_read(ctx+8,8))[0];payload=bytes(c.u.mem_read(ptr,16))
 if not ((typ==64 and payload[8]==1) or (typ==67 and struct.unpack_from('<i',payload)[0]==7034204)):continue
 tp=struct.unpack('<Q',c.u.mem_read(ctx+0x20,8))[0];start,end=struct.unpack('<f4xf',c.u.mem_read(tp,12));assert typ not in events
 events[typ]=dict(type=typ,payload=payload.hex(),start=start,end=end)
assert set(events)=={64,67} and all(math.isclose(e['start'],17/30,abs_tol=1e-6) for e in events.values())
g=BehaviorGraph(a.behavior);bindings=[]
for name in ('MagicFireRight_CMSG','MagicFireRight_CMSG_Upper'):
 selector=g.named(name,'CustomManualSelectorGenerator')
 matches=[child for child in g.children(selector) if g.item(child)[0]['Identity']=='hkbClipGenerator' and g.string(g.reference(child,'animationName'))=='a528_045010']
 assert len(matches)==1;bindings.append(dict(selector=name,selectorItem=selector,clip=matches[0],animation='a528_045010'))
checks={k:[] for k in ('cast','timing','refresh','overlap','extension','disabled','conditions')};stubs=set()
def record(key,c,**v):checks[key].append(v);stubs.update(c.stubs)
def near(values,expected):assert all(math.isclose(v,expected,abs_tol=2e-6) for v in values),(values,expected)
def start(copies=1):
 c=Event()
 for _ in range(copies):c.grant(9200006)
 for _ in range(60):c.qualify();c.update(1/60)
 return c
def deliver(c,p,active=True):
 p.requests.clear();p.event(events[64]['payload'],int(active))
 for request in p.requests:
  assert request==dict(target=OBJ+0x6000,id=1800300);c.grant(request['id'])
 if active:c.event(bytes.fromhex(events[67]['payload']))
 return list(p.requests)
for active in (False,True):
 p=Prayer(8003);p.event(events[64]['payload'],int(active));assert p.requests==([dict(target=OBJ+0x6000,id=1800300)] if active else [])
 record('cast',p,active=active,requests=p.requests,costs=p.costs)
for copies,fps in itertools.product((0,1,3),(30,60,120)):
 c=start(copies);p=Prayer(8003);fired=set();first={};last={};samples=[]
 for frame in range(32*fps):
  time=frame/fps
  for typ,event in events.items():
   if typ in fired or not event['start']<=time<event['end']:continue
   fired.add(typ)
   if typ==64:
    p.event(event['payload']);assert p.requests==[dict(target=OBJ+0x6000,id=1800300)]
    for request in p.requests:c.grant(request['id'])
   else:c.event(bytes.fromhex(event['payload']))
  c.qualify();c.update(1/fps)
  for n in c.nodes():
   if n['id'] in (1800300,7034204) and not n['flags']&0x800c0003:first.setdefault(n['id'],frame);last[n['id']]=frame
  if frame in (0,fps,15*fps,30*fps,31*fps,32*fps-1):samples.append(dict(frame=frame,defense=c.defense(),nodes=c.nodes()))
 assert fired=={64,67};near(samples[1]['defense'],.72 if copies else .9);near(samples[-1]['defense'],1)
 assert abs((last[1800300]-first[1800300])/fps-30)<.08
 if copies:assert abs((last[7034204]-first[7034204])/fps-30)<.08
 else:assert 7034204 not in first
 deliver(c,p);c.qualify();c.update(0);near(c.defense(),.72 if copies else .9)
 after_expiry=[n for n in c.nodes() if n['id'] in (1800300,7034204)]
 assert all(n['lifetime']==30 for n in after_expiry)
 record('timing',c,copies=copies,fps=fps,first=first,last=last,samples=samples,afterExpiry=after_expiry);stubs.update(p.stubs)
 print('timing',copies,fps,flush=True)
for copies,fps in itertools.product((1,3),(30,60,120)):
 c=start(copies);p=Prayer(8003);deliver(c,p);last={};samples=[]
 for frame in range(37*fps):
  if frame==5*fps:deliver(c,p)
  c.qualify();c.update(1/fps)
  for n in c.nodes():
   if n['id'] in (1800300,7034204) and not n['flags']&0x800c0003:last[n['id']]=frame
  if frame in (fps,5*fps,10*fps,30*fps,32*fps,36*fps):samples.append(dict(frame=frame,defense=c.defense(),nodes=c.nodes()))
 for sample in samples[:-2]:
  near(sample['defense'],.72)
  for id in (1800300,7034204):assert sum(n['id']==id for n in sample['nodes'])==1
 near(samples[-2]['defense'],.9);near(samples[-1]['defense'],1)
 assert abs(last[1800300]/fps-35)<.1 and abs(last[7034204]/fps-30)<.1
 assert c.bonusAdded==[7034204] and c.bonusKept==[7034204],(c.bonusAdded,c.bonusKept)
 record('refresh',c,copies=copies,fps=fps,last=last,samples=samples,bonusAdded=c.bonusAdded,bonusKept=c.bonusKept);stubs.update(p.stubs)
 print('refresh',copies,fps,flush=True)
for copies,extra,order in itertools.product((0,1,3),(1730,1768,1660000,1661000,1662000,99590),('before','after')):
 c=start(copies);p=Prayer(8003)
 if order=='before':c.grant(extra);c.qualify();c.update(0)
 deliver(c,p);c.qualify();c.update(0)
 if order=='after':c.grant(extra);c.qualify();c.update(0)
 expected=(.9 if order=='before' else x.spells[str(extra)]['neutralDamageCutRate'])*(.8 if copies else 1)
 near(c.defense(),expected);ids=[n['id'] for n in c.nodes()]
 assert (1800300 in ids)==(order=='before') and (extra in ids)==(order=='after')
 assert ids.count(7034204)==1
 record('overlap',c,copies=copies,extra=extra,order=order,defense=c.defense(),nodes=c.nodes());stubs.update(p.stubs)
for extension in ([],[7006400],[8330500],[7006400]*3,[8330500]*3,[7006400,8330500]):
 c=start();p=Prayer(8003)
 for id in extension:c.grant(id)
 c.qualify();c.update(0);deliver(c,p);c.qualify();c.update(1)
 multiplier=1+(.5 if 7006400 in extension else 0)+extension.count(8330500)
 for node in c.nodes():
  if node['id'] in (1800300,7034204):assert math.isclose(node['lifetime'],30-1/multiplier,abs_tol=1e-5)
 near(c.defense(),.72);record('extension',c,effects=extension,multiplier=multiplier,defense=c.defense(),nodes=c.nodes())
for leaf,mask in itertools.product((1800300,7034204),(1,2,0x40000,0x80000000)):
 c=start();p=Prayer(8003);deliver(c,p);c.qualify();c.update(0);ptr=struct.unpack('<Q',c.u.mem_read(OBJ+8,8))[0]
 while ptr:
  if struct.unpack('<i',c.u.mem_read(ptr+8,4))[0]==leaf:c.u.mem_write(ptr+0x68,struct.pack('<I',mask))
  ptr=struct.unpack('<Q',c.u.mem_read(ptr+0x38,8))[0]
 near(c.defense(),.8 if leaf==1800300 else .9);record('disabled',c,leaf=leaf,mask=mask,defense=c.defense())
for copies in (0,1,3):
 c=start(copies);p=Prayer(8003);deliver(c,p);c.qualify();c.update(1);before=c.nodes()
 # Remove the whole maintenance chain explicitly to isolate state 2047 loss.
 for id in (9200006,9200007,7034200,7034201):c.invoke(0x504e80,[OBJ,id])
 c.qualify();c.update(1);during=c.nodes();near(c.defense(),.9)
 c.grant(7034200);c.qualify();c.update(0);c.qualify();c.update(1);after=c.nodes();near(c.defense(),.72)
 record('conditions',c,copies=copies,before=before,during=during,after=after,defense=c.defense())
counts={k:len(v) for k,v in checks.items()};assert counts==dict(cast=2,timing=9,refresh=6,overlap=36,extension=6,disabled=8,conditions=3)
a.output.write_text(json.dumps(dict(schema=1,effects=[7034200,7034201],magic=8003,magicRowName=pure_name,root=9200006,baseline=1800300,bonus=7034204,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),paramHashes=hashes,coreEvidenceSha256=sha(core_path.read_bytes()),animationBundleSha256=anims['bundles'][0]['sha256'],taeSha256=t['sha256'],behaviorBundleSha256=g.metadata['bundleSha256'],behaviorSha256=g.metadata['hkxSha256'],events=events,bindings=bindings,checks=checks,native=dict(relocate='27D0F10',iterate='27D0400',cast='40EB30 → E91FD0 → 3C7F40',bonus='410CA0 → 40FF20 → 509150 → 3C8BE0 or 50A630',upkeep='5057D0 → 50ACD0',incoming='503800'),stubs=sorted(stubs|{'The selected animation windows and native self-grant transfer between cast and recipient runtimes are explicit fixtures; no scene cast scheduler or network transport.','Havok graph references establish clip bindings; the behavior VM, interruptions, collision, final HP damage and DLL overrides are not simulated.','Direct removal/readdition of the maintenance chain is a state-gate test, not a complete player unequip/death/reload workflow.'}),gameplayVerified=False),ensure_ascii=False,indent=2)+'\n');print('PASS',sum(counts.values()),counts)
