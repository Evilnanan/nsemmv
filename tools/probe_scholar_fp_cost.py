"""Execute Scholar self-analysis grants, tier accumulation and FP-cost timers.

The native self-grant block receives an explicit resolved analysis grade. TAE
and behavior bindings are checked separately; full target/grade resolution,
final resource deduction and gameplay are not simulated.
"""
import argparse,json,struct,itertools,math
from pathlib import Path
from native_effect_runtime import *
from native_ailment_runtime import Ailment
from native_animation_runtime import NativeTae
from effect_behavior_graph import BehaviorGraph
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','animations','behavior','script','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted);inputs=x
assert sha(x.param)=='07ec636c5565d4551efeb53e6f08bc633b2aa4f2129f13c61b0638d69b1bc176'
attachraw=a.extracted.with_suffix('.AttachEffectParam.param').read_bytes();rows=Inputs.table(attachraw,0x44)
assert sha(attachraw)=='ae8128ed510a532d0fa7cb56fa9c86e4a44c9d815dd4ee01c05821d5f50a9827'
commonraw=a.extracted.with_suffix('.PlayerCommonParam.param').read_bytes();off=struct.unpack_from('<Q',commonraw,0x48)[0];common=commonraw[off:]
assert sha(commonraw)=='2e7b384f9590e6fa3f19b2f93e3826cebf8d399246fe987382086a445f7f096c'
assert struct.unpack_from('<H',commonraw,10)[0]==1 and struct.unpack_from('<3i',common,0x270)==(708030,708040,708050)
effect,root=6500800,7500800;leaves=[7500801,7500802,7500803]
attach=x.x['tables']['AttachEffectParam'][str(effect)]
assert attach['passiveSpEffectId_1']==root and attach['permanentSpEffectId']==attach['exclusivityId']==-1
assert [k for k,v in attach.items() if k.startswith('allow') and v]==['allowScholar']
r=x.spells[str(root)];assert (r['stateInfo'],r['spCategory'])==(2127,20)
assert [r['analyzeSelfLevel'+str(i)+'_effectId'] for i in (1,2,3)]==leaves
assert struct.unpack_from('<3i',x.rows[root],0x3f0)==tuple(leaves)
rate=x.spells[str(leaves[0])]['magicConsumptionRate'];assert math.isclose(rate,.85,rel_tol=1e-6)
fields=['magicConsumptionRate','miracleConsumptionRate','shamanConsumptionRate','artsConsumptionRate','goodsConsumptionRate']
for id in [root,*leaves,708030,708040,708050,7610700,7610701,7610702,7006400]:
 assert sum(struct.unpack_from('<i',x.param,0x40+i*24)[0]==id for i in range(struct.unpack_from('<H',x.param,10)[0]))==1
for id in leaves:
 r=x.spells[str(id)];assert all(r[k]==rate for k in fields)
 assert (r['stateInfo'],r['spCategory'],r['effectEndurance'],r['isExtendSpEffectLife'],r['isContractSpEffectLife'])==(0,20,40,0,1)
 assert all(r[k]==-1 for k in ('replaceSpEffectId','cycleOccurrenceSpEffectId','atkOccurrenceSpEffectId'))
 assert all(r['invocationConditionsStateChange'+str(i)]==0 for i in (1,2,3))
anims=json.loads(a.animations.read_text());assert anims['bundles'][0]['sha256']=='806e6b218d747277ab45e14f45ca80b9ecf8c13ada22f89db2d3ef23caa62b2a'
track=next(t for b in anims['bundles'] for t in b['taes'] if t['ID']==2908)
raw=Path(str(a.animations)+'.2908.tae').read_bytes();assert sha(raw)==track['sha256']=='05df3be3ccba558f65f2632d1e08b109c6708821efd304fdb454a553235e5949'
events=[dict(animation=an['ID'],**e) for an in track['animations'] for e in an['events'] if e['Type']==1024]
assert [(e['animation'],bytes.fromhex(e['hex'])[0]) for e in events]==[(581010,0),(581020,1)]
graph=BehaviorGraph(a.behavior);bindings=[]
for name in ('PhotoShootAct','PhotoShootAct_Upper'):
 state=graph.named(name,'hkbStateMachine::StateInfo');selector=graph.reference(state,'generator');binding=graph.selector_binding(selector)
 assert binding['name']=='IsBuffMode';clips=[]
 for branch in graph.children(selector):
  children=graph.children(branch);assert len(children)==1
  clips.append(graph.string(graph.reference(children[0],'animationName')))
 assert clips==['a908_581010','a908_581020'];bindings.append(dict(state=name,binding=binding,clips=clips))
script=a.script.read_bytes();assert sha(script)=='96339bb15f57559cd42a940d616fcc2a18a10f50845cfc22b46b356ab66c3b29'
source=script.decode('utf-8-sig').replace('\r\n','\n');begin=source.index('function ExecPhotoShoot()');script_function=source[begin:source.index('\nfunction ',begin+1)]
assert 'SetVariable("IsBuffMode", 0)' in script_function and 'SetVariable("IsBuffMode", 1)' in script_function
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
 def damage(self,value=100,excluded=0):self.invoke(0x504d30,[OBJ,0,0,0,excluded],{UC_X86_REG_XMM1:value})

class Self(Actor):
 def __init__(self,copies=0):
  super().__init__()
  self.q(OBJ+0x6190,OBJ)
  for _ in range(copies):self.insert(7500800)
  self.qualify();self.update(0)
 def hook(self,u,address,size,user):
  pc=address-BASE
  if pc==0x3d4180:return  # execute the original local-player comparison
  if pc==0x3edd6f:u.reg_write(UC_X86_REG_RIP,STOP);return
  if pc==0xe81650:
   self.stubs.add('E81650 actual PlayerCommonParam row lookup')
   ptr=u.reg_read(UC_X86_REG_RCX);u.mem_write(OBJ+0xb000,common);self.q(ptr,OBJ+0xb000);u.reg_write(UC_X86_REG_RAX,ptr)
   sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8);return
  super().hook(u,address,size,user)
 def apply(self,grade):
  self.u.reg_write(UC_X86_REG_RBP,STACK+0x9000);self.u.reg_write(UC_X86_REG_R14,grade&255)
  self.invoke(0x3edc79,[]);self.qualify();self.update(0)
 def rates(self):
  out=[]
  for rva in (0x507310,0x507410,0x5081e0,0x5061b0):
   self.invoke(rva,[OBJ]);out.append(struct.unpack('<f',(self.u.reg_read(UC_X86_REG_XMM0)&0xffffffff).to_bytes(4,'little'))[0])
  return out

class Dispatch(Self):
 def __init__(self):
  super().__init__();self.modes=[];self.q(OBJ+0xf1a8,OBJ+0xc000);self.q(OBJ+0xd018,OBJ+0x6000)
 def hook(self,u,address,size,user):
  if address-BASE==0x3ed220:
   self.modes.append(u.reg_read(UC_X86_REG_RDX)&255)
   sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8);return
  super().hook(u,address,size,user)

checks={k:[] for k in ('selection','animation','dispatch','lifetime','refresh','mixed','disabled','extension','removal')};stubs=set()
def record(key,c,**row):checks[key].append(row);stubs.update(c.stubs)
def cost(c,expected):
 values=c.rates();assert all(math.isclose(v,expected,rel_tol=2e-6) for v in values),(values,expected)
 return values
def active(c):return [n for n in c.nodes() if n['id'] in leaves]
def step(c,frames=1,fps=60):
 for _ in range(frames):c.qualify();c.update(1/fps)
for copies,hero in itertools.product((1,2,3,6),range(11)):
 c=Selection([[effect]]*copies,hero);bits=c.select();selected=[]
 for i in range(copies):
  if i*6 not in bits:continue
  c.invoke(0xe6e150,[OBJ+0x9200,effect]);selected.append(c.invoke(0xe6e3b0,[OBJ+0x9200,0])&0xffffffff)
 assert selected==([root]*copies if hero in (0,9) else [])
 d=Self(len(selected));d.apply(3);values=cost(d,rate**3 if selected else 1);stubs.update(d.stubs)
 record('selection',c,copies=copies,hero=hero,selected=selected,values=values)
print('PASS selection',len(checks['selection']),flush=True)
for e,enabled,local in itertools.product(events,(0,1),(False,True)):
 c=Dispatch();tae=NativeTae(c,raw,track['sha256']);ctx=tae.select(e['animation'],1024)
 payload=struct.unpack('<Q',c.u.mem_read(ctx+8,8))[0];assert bytes(c.u.mem_read(payload,16)).hex()==e['hex'].lower()
 c.u.mem_write(ctx+0x18,bytes([enabled]))
 if not local:c.q(OBJ+0x574e8,0)
 c.invoke(0x414820,[OBJ+0xd000,ctx]);assert c.modes==([bytes.fromhex(e['hex'])[0]] if enabled and local else []),(e['animation'],enabled,local,c.modes)
 record('animation',c,animation=e['animation'],enabled=enabled,local=local,modes=c.modes)
print('PASS animation',len(checks['animation']),flush=True)
for copies,grade in itertools.product((0,1,3,6),(-1,0,1,2,3)):
 c=Self(copies);c.apply(grade);present=sorted(n['id'] for n in active(c))
 assert present==(leaves[:max(grade,0)] if copies else [])
 values=cost(c,rate**max(grade,0) if copies else 1)
 record('dispatch',c,copies=copies,grade=grade,grants=c.grants,active=active(c),values=values)
print('PASS dispatch',len(checks['dispatch']),flush=True)
for copies,grade,fps in itertools.product((1,3),(1,2,3),(30,60,120)):
 c=Self(copies);c.apply(grade);expired=None
 for frame in range(1,41*fps+1):
  step(c,fps=fps)
  if not active(c) and expired is None:expired=frame
 assert expired is not None and abs(expired-40*fps)<=3,(copies,grade,fps,expired)
 values=cost(c,1);record('lifetime',c,copies=copies,grade=grade,fps=fps,expiredFrame=expired,values=values)
print('PASS lifetime',len(checks['lifetime']),flush=True)
for copies,first,second in itertools.product((1,3),(1,2,3),(1,2,3)):
 c=Self(copies);c.apply(first);step(c,5*60);before=active(c);c.grants.clear();c.apply(second);after=active(c)
 assert sorted(n['id'] for n in after)==leaves[:max(first,second)]
 for n in after:assert math.isclose(n['lifetime'],40 if n['id'] in leaves[:second] else 35,abs_tol=.002)
 values=cost(c,rate**max(first,second))
 step(c,35*60+3);at40=active(c);cost(c,rate**second)
 assert sorted(n['id'] for n in at40)==leaves[:second]
 step(c,5*60);assert not active(c);cost(c,1)
 record('refresh',c,copies=copies,first=first,second=second,before=before,after=after,values=values,afterOldExpiry=at40)
print('PASS refresh',len(checks['refresh']),flush=True)
for grade,other,count in itertools.product((1,2,3),(7610700,7610701,7610702),(1,3)):
 c=Self(1)
 for _ in range(count):c.insert(other)
 c.qualify();c.update(0);c.apply(grade)
 values=cost(c,rate**grade*x.spells[str(other)]['magicConsumptionRate']**count)
 record('mixed',c,grade=grade,other=other,count=count,values=values)
print('PASS mixed',len(checks['mixed']),flush=True)
for copies,grade in itertools.product((1,3),(1,2,3)):
 c=Self(copies);ptr=struct.unpack('<Q',c.u.mem_read(OBJ+8,8))[0];c.u.mem_write(ptr+0x68,struct.pack('<I',0x800c0003))
 # No requalification before the native dispatch block; disabled root cannot emit leaves.
 c.apply(grade);assert not active(c);values=cost(c,1);record('disabled',c,copies=copies,grade=grade,target='root',values=values)
 c=Self(copies);c.apply(grade);ptr=struct.unpack('<Q',c.u.mem_read(OBJ+8,8))[0]
 while ptr:
  if struct.unpack('<i',c.u.mem_read(ptr+8,4))[0] in leaves:c.u.mem_write(ptr+0x68,struct.pack('<I',0x800c0003))
  ptr=struct.unpack('<Q',c.u.mem_read(ptr+0x38,8))[0]
 values=cost(c,1);record('disabled',c,copies=copies,grade=grade,target='leaves',values=values)
for extension,grade in itertools.product((0,1,3),(1,2,3)):
 c=Self(1)
 for _ in range(extension):c.insert(7006400)
 c.qualify();c.update(0);c.apply(grade);step(c,60)
 assert all(math.isclose(n['lifetime'],39,abs_tol=.002) for n in active(c))
 record('extension',c,extension=extension,grade=grade,active=active(c))
for grade in (1,2,3):
 c=Self(1);c.apply(grade);c.invoke(0x505280,[OBJ,0]);step(c,60)
 assert not any(n['id']==root for n in c.nodes())
 before=active(c);c.apply(3);after=active(c);assert before==after
 record('removal',c,grade=grade,active=after,values=cost(c,rate**grade))
print('PASS controls',len(checks['disabled']),len(checks['extension']),len(checks['removal']),flush=True)
out=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),attachParamSha256=sha(attachraw),playerCommonSha256=sha(commonraw),
 taeSha256=sha(raw),behaviorSha256=graph.metadata['bundleSha256'],scriptSha256=sha(script),effect=effect,root=root,leaves=leaves,rate=rate,duration=40,
 events=events,behaviorBindings=bindings,scriptFunction=script_function,checks=checks,
 native=dict(selection='4FEA30 → E6E150 → E6E3B0',animation='27D0F10 → 27D0400 → 414820 → 3ED220 (mode recorder)',
 selfGrantBlock=['3EDC79','3EDD6F'],tiers='505D00',grant='3C7FD0 → 3C80A0 → 3DB410 → 50A4C0 → 50D060',
 costs=['507310','507410','5081E0','5061B0'],lifecycle='5057D0 → 50ACD0 → 511B80'),
 stubs=sorted(stubs),limitations=['Resolved analysis grade is explicit; full 3ED220 target scan/grade resolution and behavior/HKS scheduler not executed.',
 'TAE mode arrival is recorded separately from self-grant block execution.', 'The four spell/skill FP multiplier consumers execute; final integer FP deduction, goods cost consumer and DLL changes are not simulated.',
 'No actual equipment rebuild, death/reload or network gameplay; removing a root tests only the native effect container.'],gameplayVerified=False)
a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print('PASS total',sum(map(len,checks.values())),flush=True)
