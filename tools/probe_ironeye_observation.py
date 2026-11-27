"""Partial native proof of Ironeye observation growth and its personal consumer.

Does not establish ally delivery or cross-player growth merging. Party transport,
complete lifecycle and DLL hooks remain open; no global stacking conclusion.
"""
import argparse,json,struct,itertools,math
from pathlib import Path
from native_effect_runtime import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','curves','output'):p.add_argument(name,type=Path)
a=p.parse_args();inputs=Inputs(a.exe,a.extracted);x=inputs;root,seed=7280100,7280201
raw=a.extracted.with_suffix('.AttachEffectParam.param').read_bytes();rows=Inputs.table(raw,0x44)
curve_raw=a.curves.with_suffix('.CalcCorrectGraph.param').read_bytes();curve=Inputs.table(curve_raw,80)[140]
hashes={'AttachEffectParam':sha(raw),'CalcCorrectGraph':sha(curve_raw)}
assert hashes=={'AttachEffectParam':'ae8128ed510a532d0fa7cb56fa9c86e4a44c9d815dd4ee01c05821d5f50a9827','CalcCorrectGraph':'fda4253c4c4d8898378924b72dd817d6ac2eee8ba0e0bda6848fc1803ecbd14b'}
assert sha(inputs.param)=='07ec636c5565d4551efeb53e6f08bc633b2aa4f2129f13c61b0638d69b1bc176'
assert json.loads(a.curves.read_text())['hashes']['regulation.bin']==inputs.x['hashes']['regulation.bin']
for id in (7280100,7280101):
 ar=inputs.x['tables']['AttachEffectParam'][str(id)]
 assert [ar['passiveSpEffectId_'+str(i)] for i in (1,2,3)]==[root,-1,-1] and ar['exclusivityId']==-1
 assert ar['permanentSpEffectId']==seed and ar['isPersistentEffect']==1
 assert [k for k,v in ar.items() if k.startswith('allow') and v]==['allowIroneye']
r=inputs.spells[str(root)];assert (r['spCategory'],r['stateInfo'],r['applyIdOnGetSoul'],r['applyIdOnKillSp'])==(20,199,7280101,-1)
r=inputs.spells['7280101'];assert (r['spCategory'],r['replaceSpEffectId'])==(10,seed) and math.isclose(r['effectEndurance'],.1,abs_tol=1e-7)
assert [int(id) for id,r in inputs.spells.items() if r['spCategory']==204 and r['categoryPriority']==6]==list(range(7280201,7280300))
for level in range(1,100):
 r=inputs.spells[str(7280200+level)]
 assert (r['stateInfo'],r['spCategory'],r['categoryPriority'],r['saveCategory'],r['effectEndurance'])==(66,204,6,9,-1)
 assert math.isclose(r['itemDropRate'],level/100,abs_tol=1e-7)
 assert inputs.rows[7280200+level][0x352]&0x20
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

class Growth(Chain):
    def __init__(self,copies=0,mode=7):
        super().__init__(inputs);self.resolved=[];self.grants=[];self.notifications=0
        self.q(OBJ+0x6190,OBJ);self.q(OBJ+0x6210,STOP+0x200)
        self.q(OBJ+0x6790,STOP+0x201)
        for off in (0x150,0x118,0x120):self.q(OBJ+0x6200+off,STOP+0x202)
        self.q(OBJ+0x61b8,OBJ+0xd000);self.q(OBJ+0xd020,OBJ+0xd800)
        self.mapped(self.u,0,BASE+0x3c21ec8,8,0,None);self.q(BASE+0x3c21ec8,OBJ+0xf000)
        self.u.mem_write(OBJ+0xf010,struct.pack('<i',mode))
        self.u.mem_map(OBJ+0x40000,0x20000);self.mapped(self.u,0,BASE+0x3c0f0a8,8,0,None)
        self.q(BASE+0x3c0f0a8,OBJ+0x40000);self.q(OBJ+0x574e8,OBJ+0x6000)
        for _ in range(copies):self.insert(root)
        self.qualify();self.update(0)
    def arrive(self,id=seed):self.invoke(0x3c7fd0,[OBJ+0x6000,id,1])
    def hook(self,u,address,size,user):
        pc=address-BASE
        def ret(value=0):
            u.reg_write(UC_X86_REG_RAX,value&0xffffffffffffffff);sp=u.reg_read(UC_X86_REG_RSP)
            u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
        if address in (STOP+0x200,STOP+0x201,STOP+0x202):
            self.stubs.add('actor virtuals +10 player, +590 type 0, +118/+120/+150 false; explicit local identity and mode')
            ret({STOP+0x200:1,STOP+0x201:OBJ+0xf100,STOP+0x202:0}[address])
        elif pc==0x3c7fd0:
            # Observe, then execute this grant and all subsequent insertion code.
            self.grants.append(dict(id=u.reg_read(UC_X86_REG_RDX)&0xffffffff,mode=u.reg_read(UC_X86_REG_R8)&255))
        elif pc==0x3db410:self.resolved.append(u.reg_read(UC_X86_REG_RDX)&0xffffffff)
        elif pc==0x3d3390:
            self.stubs.add('3D3390 false special owner-identity predicate');ret()
        elif pc in (0x732800,0x51b920,0x6af640):
            self.stubs.add('732800 absent network peer; 51B920 and 6AF640 notification sinks, no serialization/reload')
            if pc==0x6af640:self.notifications+=1
            ret()
        elif pc in (0x2167950,0x21674e0,0x2167a40):
            self.stubs.add('2167950/21674E0/2167A40 monotonic notification timestamp fixture')
            self.q(OBJ+0xf200,100);ret(OBJ+0xf200 if pc==0x2167950 else 1 if pc==0x2167a40 else 0)
        elif pc==0xea0ca0:
            self.stubs.add('EA0CA0 absent auxiliary notification ID mapping after successful insertion');ret(-1)
        else:super().hook(u,address,size,user)

class Observation(Growth):
 def __init__(self,copies=0):
  super().__init__(0);self.rewards=[];self.u.mem_map(OBJ+0x80000,0x40000);self.q(OBJ+0x67d0,STOP+0x701)
  for _ in range(copies):self.insert(root)
  self.qualify();self.update(0)
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v&0xffffffffffffffff);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if pc==0xea17e0:
   id=u.reg_read(UC_X86_REG_RDX)&0xffffffff
   if id in inputs.rows and id not in self.lookup:
    self.lookup[id]=OBJ+0x80000+len(self.lookup)*0x400;assert len(self.lookup)<256;u.mem_write(self.lookup[id],inputs.rows[id])
   wrapper=u.reg_read(UC_X86_REG_RCX);u.mem_write(wrapper,struct.pack('<QI',self.lookup.get(id,0),id));ret(wrapper)
  elif pc in (0x4d1ae0,0x4b3b50,0x4d1b20):ret()
  elif pc==0x3ced90:ret(OBJ+0xd000)
  elif address==STOP+0x701:
   value=u.reg_read(UC_X86_REG_RDX);self.rewards.append(value);ret(value)
  else:super().hook(u,address,size,user)
 def kill(self,special=0,amount=100):self.invoke(0x668380,[OBJ+0x6000,0,OBJ+0x68000,special],{UC_X86_REG_XMM1:amount})
 def step(self,frames=9,fps=60):
  for _ in range(frames):self.qualify();self.update(1/fps)
 def scalar(self,rva):
  self.invoke(rva,[0,OBJ] if rva==0x6c7f30 else [OBJ]);return struct.unpack('<f',(self.u.reg_read(UC_X86_REG_XMM0)&0xffffffff).to_bytes(4,'little'))[0]
P=OBJ+0xc0000;CLONE=P+0x1000
class Profile(Observation):
 def __init__(self,copies=1,arcane=0):
  super().__init__(copies);self.u.mem_map(P,0x10000);self.q(P+0x830,CLONE);self.u.mem_write(P+0x1d4,struct.pack('<i',arcane));self.q(P+0x3008,P)
  try:self.u.mem_read(BASE+0x3c078d0,8)
  except:self.mapped(self.u,0,BASE+0x3c078d0,8,0,None)
  self.q(BASE+0x3c078d0,P+0x3000);self.q(CLONE,BASE+0x2c237e0);self.u.mem_write(P+0x2000,curve)
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if pc==0xe87b10:
   assert u.reg_read(UC_X86_REG_RDX)==140;ptr=u.reg_read(UC_X86_REG_RCX);u.mem_write(ptr,struct.pack('<I4xQ',140,P+0x2000));ret(ptr);return
  super().hook(u,address,size,user)
 def mapped(self,u,access,address,size,value,user):
  if not BASE<=address<BASE+self.inputs.pe.OPTIONAL_HEADER.SizeOfImage:print('FAULT',hex(address),hex(u.reg_read(UC_X86_REG_RIP)-BASE),flush=True)
  return super().mapped(u,access,address,size,value,user)
 def clone(self):self.invoke(0x2099c0,[P,OBJ])
 def rate(self):
  self.invoke(0x56ad70,[]);return struct.unpack('<f',(self.u.reg_read(UC_X86_REG_XMM0)&0xffffffff).to_bytes(4,'little'))[0]
 def display(self):return self.invoke(0x6c7e40,[P,CLONE])&0xffffffff
checks={k:[] for k in ('selection','aliases','growth','burst','upstream','disabled','removal','profile','timing')};stubs=set()
def record(key,c,**row):checks[key].append(row);stubs.update(c.stubs)
def values(c):return dict(nodes=c.nodes(),raw=c.scalar(0x5071b0),rate=c.scalar(0x6c7f30))
def verify(c,level):
 v=values(c);assert math.isclose(v['raw'],level/100,abs_tol=1e-7) and math.isclose(v['rate'],1+level/100,abs_tol=1e-7)
 assert [n['id'] for n in v['nodes'] if 7280201<=n['id']<7280300]==([7280200+level] if level else [])
 return v
for effect,copies,hero in itertools.product((7280100,7280101),(1,2,3),range(11)):
 c=Selection([[effect]]*copies,hero);chosen=c.select();assert [i for i in range(copies) if i*6 in chosen]==(list(range(copies)) if hero in (0,3) else [])
 c.invoke(0xe6e150,[OBJ+0x9200,effect]);passives=[c.invoke(0xe6e3b0,[OBJ+0x9200,i])&0xffffffff for i in range(3)];assert passives==[root,0xffffffff,0xffffffff]
 record('selection',c,effect=effect,copies=copies,hero=hero,chosen=chosen,passives=passives)
for counts in itertools.product((0,1,3),repeat=2):
 c=Observation(sum(counts));c.kill();c.step();v=verify(c,int(bool(sum(counts))));assert [n['id'] for n in c.nodes()].count(root)==int(bool(sum(counts)))
 record('aliases',c,counts=counts,**v)
for copies,special in itertools.product((0,1,3),(0,1)):
 c=Observation(copies)
 for kills in range(151):
  if kills:c.kill(special);c.step()
  if kills in (0,1,2,10,50,100,150):record('growth',c,copies=copies,special=special,kills=kills,**verify(c,min(kills,99) if copies else 0))
print('PASS selection/aliases/growth',flush=True)
for copies,burst,fps in itertools.product((1,3),(1,2,5,10),(30,60,120)):
 c=Observation(copies)
 for _ in range(burst):c.kill()
 c.step(fps,fps);record('burst',c,copies=copies,burst=burst,fps=fps,**verify(c,burst))
for amount,special in itertools.product((-1,0,.4,.6,1,100),(0,1)):
 c=Observation(1);c.kill(special,amount);children=c.grants.copy();assert [v['id'] for v in children]==[7280101]
 c.step();record('upstream',c,amount=amount,special=special,children=children,rewards=c.rewards,**verify(c,1))
for mask in (1,2,0x40000,0x80000000):
 c=Observation(1);c.kill();c.step();node=struct.unpack('<Q',c.u.mem_read(OBJ+8,8))[0]
 while node:
  if struct.unpack('<i',c.u.mem_read(node+8,4))[0]==seed:
   flags=struct.unpack('<I',c.u.mem_read(node+0x68,4))[0];c.u.mem_write(node+0x68,struct.pack('<I',flags|mask))
  node=struct.unpack('<Q',c.u.mem_read(node+0x38,8))[0]
 assert c.scalar(0x5071b0)==0 and c.scalar(0x6c7f30)==1;record('disabled',c,mask=mask,**values(c))
for level in (0,1,10,99):
 c=Observation(1)
 for _ in range(level):c.kill();c.step()
 c.invoke(0x504e80,[OBJ,root]);c.step();c.kill();c.step();v=verify(c,level);assert root not in [n['id'] for n in v['nodes']]
 record('removal',c,level=level,**v)
print('PASS burst/upstream/disabled/removal',flush=True)
for arcane in (0,10,30,40,60,99):
 c=Profile(1,arcane);c.clone();base=c.rate();previous=0
 for tier in (0,1,2,10,99):
  for _ in range(tier-previous):c.kill();c.step()
  previous=tier;c.clone();rate=c.rate();display=c.display()
  assert math.isclose(rate,base+tier/100,abs_tol=2e-7)
  record('profile',c,arcane=arcane,tier=tier,base=base,rate=rate,display=display)
for fps in (30,60,120):
 c=Observation(1);c.kill();changes=[];last=None
 for frame in range(fps):
  c.step(1,fps);raw=c.scalar(0x5071b0)
  if raw!=last:changes.append(dict(frame=frame,raw=raw));last=raw
 assert len(changes)==2 and changes[0]['raw']==0 and math.isclose(changes[1]['raw'],.01,abs_tol=1e-7)
 assert abs(changes[1]['frame']-.1*fps)<=3;record('timing',c,fps=fps,changes=changes)
print('PASS counts',{k:len(v) for k,v in checks.items()},sum(map(len,checks.values())),flush=True)
out=dict(schema=1,status='partial',effects=[7280100,7280101],root=root,seed=seed,maxLevel=99,
 exeSha256=sha(inputs.raw),regulationSha256=inputs.x['hashes']['regulation.bin'],paramSha256=sha(inputs.param),paramHashes=hashes,
 native=dict(selection='4FEA30 → E6E150 → E6E3B0',kill='668380 → 50A150',grant='3C7FD0 → 3C80A0 → 3DB410',
 growth='5077A0',update='5057D0 → 50ACD0',raw='5071B0',ratio='6C7F30',display='6C7E40',
 profileCopy='2099C0 → 584220 → 501840',dropInput='56AD70 → 20CE40 → 584480 → 6C7F30',remove='504E80'),checks=checks,
 stubs=sorted(stubs|{'Explicit actor identity, mode 7, reward notification sinks and absent network peer; original kill, growth and consumers execute.',
 '4D1AE0/4B3B50/4D1B20 false predicates and 3CED90 animation-context identity; player reward virtual +5D0 records amounts.',
 'SpEffect lookup cache relocated to permit all 99 growth rows; actual rows returned unchanged.',
 'Empty profile copy container with actual vtable 2C237E0; full profile/container construction is not executed.',
 'Explicit arcane inputs; actual CalcCorrectGraph 140 lookup and original curve interpolation execute.'}),
 openQuestions=['Actual ally delivery/aggregation and multiple Ironeye players; the shared relic-manager path does not directly export the unshared root.',
 'Complete equipment initialization and lifecycle, late-arriving kill markers, death, expedition transitions and save/reload.',
 'Downstream loot generation/ownership, scene enemy reward attribution, and MMV DLL hooks.'],gameplayVerified=False)
a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
