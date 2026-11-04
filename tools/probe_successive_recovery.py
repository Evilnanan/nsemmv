"""Execute successive-attack HP/FP recovery, repeated equipment and shared decay.

Native container, accumulation, queue, immediate self-grant, resource packets and
lifetime code run against pinned rows. Hit-marker arrivals and actor identities
are fixtures; final current-resource setters and combat collision are not run.
"""
import argparse
import itertools
import json
import math
import struct
from pathlib import Path
from native_effect_runtime import BASE, OBJ, STOP, Chain, Inputs, sha
from native_ailment_runtime import Ailment
from unicorn.x86_const import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted)
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

class Combo(Actor):
    def __init__(self):
        self.free=[]
        super().__init__()
        self.manager=OBJ+0xa000
        self.q(OBJ+0x18,self.manager)
        # 5014E0 constructs this manager with 50DFE0: ten counters and ten
        # vector queues. Reserve storage here; predicates and arithmetic run
        # natively. Reclaimed effect nodes are reused by the allocator fixture.
        self.q(self.manager,OBJ)
        self.q(self.manager+0x38,10);self.q(self.manager+0x188,10)
        for i in range(10):
            slot=self.manager+0x40+i*0x20;buf=OBJ+0xb000+i*0x100
            self.q(slot+8,buf);self.q(slot+0x10,buf);self.q(slot+0x18,buf+0x100)
        self.stubs.add('ten native-layout accumulation counters/queues with preallocated vector storage')

    def hook(self,u,address,size,user):
        def ret(v=0):
            u.reg_write(UC_X86_REG_RAX,v)
            sp=u.reg_read(UC_X86_REG_RSP)
            u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0])
            u.reg_write(UC_X86_REG_RSP,sp+8)
        if address==STOP+0x108:
            ptr=u.reg_read(UC_X86_REG_RDX)
            assert OBJ+0x20000<=ptr<OBJ+0x40000 and ptr not in self.free
            self.free.append(ptr);ret()
        elif address-BASE==0x214e8d0 and self.free:
            assert u.reg_read(UC_X86_REG_RCX)==0x88
            ret(self.free.pop())
        else:super().hook(u,address,size,user)

    def counter(self):return self.invoke(0x50e570,[self.manager,1])&0xffffffff
    def add(self,amount):self.invoke(0x50e240,[self.manager,1,amount])
    def queue(self):
        slot=self.manager+0x40+1*0x20
        begin,end=struct.unpack('<QQ',self.u.mem_read(slot+8,16))
        return list(struct.unpack('<'+'i'*((end-begin)//4),self.u.mem_read(begin,end-begin)))

roots=[7036000,7036010];leaves=[7036001,7036011]
effects=[int(id) for id,r in x.x['tables']['AttachEffectParam'].items() if r['passiveSpEffectId_1'] in roots]
assert sorted(effects)==[10000,7036000,7036010]
for effect in effects:assert x.x['tables']['AttachEffectParam'][str(effect)]['exclusivityId']==-1
for root,leaf in zip(roots,leaves):
 r=x.spells[str(root)];s=x.spells[str(leaf)]
 assert r['stateInfo']==s['stateInfo']==304 and r['spCategory']==s['spCategory']==10
 assert r['effectEndurance']==-1 and math.isclose(r['motionInterval'],.8,rel_tol=1e-6)
 assert r['accumuOverVal']==32 and r['accumuOverFireId']==leaf and r['accumuVal']==-1
 assert r['dedupeAccumuTrigger']==1 and r['cycleOccurrenceSpEffectId']==r['replaceSpEffectId']==-1
 assert s['accumuVal']==-999 and s['effectEndurance']==1 and s['motionInterval']==4
 assert s['changeHpRate']==(-3 if leaf==7036011 else 0) and s['changeMpRate']==(-5 if leaf==7036001 else 0)
 assert s['syncTotalHp']==1
checks=dict(threshold=[],mixed=[],markers=[],decay=[],repeat=[],dedupe=[]);stubs=set()
def record(key,c,**row):checks[key].append(row);stubs.update(c.stubs)
def start(counts,reverse=False):
 c=Combo();pairs=list(zip(roots,counts))
 for root,count in reversed(pairs) if reverse else pairs:
  for _ in range(count):c.grant(root)
 for _ in range(3):c.qualify();c.update(0)
 c.grants.clear()
 for root,count in pairs:assert sum(n['id']==root for n in c.nodes())==count
 return c
def step(c,fps=60):c.qualify();c.update(1/fps)
def packets(c):return dict(fp=c.fp(1000),hp=c.hp_packet(10000))
def expected(counts):
 fp,hp=counts[0]*50,counts[1]*300
 return dict(fp=[fp,0],hp=[hp,0,hp,0,0,0,0])
def observe(c,frames,fps=60):
 found=[]
 for frame in range(frames):
  step(c,fps);packet=packets(c)
  if any(packet['fp']) or any(packet['hp']):found.append(dict(frame=frame,counter=c.counter(),**packet))
 return found
for kind,copies,amount in itertools.product(range(2),range(4),(0,1,31,32,33,64,100)):
 counts=[copies if i==kind else 0 for i in range(2)];c=start(counts);c.add(amount)
 found=observe(c,6)
 assert len(found)==int(bool(copies) and amount>=32),(counts,amount,found)
 for r in found:assert {k:r[k] for k in ('fp','hp')}==expected(counts) and r['counter']==0
 record('threshold',c,effect=roots[kind],copies=copies,input=amount,recoveries=found,finalCounter=c.counter())
for first,second,reverse in itertools.product(range(4),range(4),(False,True)):
 counts=[first,second];c=start(counts,reverse);c.add(32);found=observe(c,6)
 assert len(found)==int(bool(first or second))
 for r in found:assert {k:r[k] for k in ('fp','hp')}==expected(counts) and r['counter']==0
 record('mixed',c,copies=counts,reverse=reverse,recoveries=found)
for marker,counts in itertools.product(range(6900,6910),([0,0],[1,0],[3,0],[1,1])):
 c=start(counts);c.grant(marker);step(c);step(c)
 weight=x.spells[str(marker)]['accumuVal'];assert weight==(marker-6899)*2
 assert c.counter()==(weight if sum(counts) else 0)
 record('markers',c,marker=marker,copies=counts,weight=weight,counter=c.counter())
for counts,fps in itertools.product(([1,0],[2,0],[3,0],[0,1],[1,1],[2,1],[0,3]),(30,60,120)):
 c=start(counts);c.add(20);previous=20;changes=[]
 for frame in range(round(2.6*fps)):
  step(c,fps);value=c.counter()
  if value!=previous:
   assert previous-value==sum(counts)
   changes.append(dict(frame=frame,counter=value));previous=value
 assert len(changes)==3 and previous==20-3*sum(counts)
 for before,after in zip(changes,changes[1:]):assert abs((after['frame']-before['frame'])/fps-.8)<=1/fps+1e-6
 record('decay',c,copies=counts,fps=fps,changes=changes)
for counts,fps,gap in itertools.product(([1,0],[3,0],[0,1],[0,3],[1,1],[3,3]),(30,60,120),(.1,.2)):
 c=start(counts);found=[];interval=round(gap*fps);end=2*fps
 for frame in range(end+round(1.5*fps)):
  if frame<end and frame%interval==0:c.grant(6909)
  step(c,fps);packet=packets(c)
  if any(packet['fp']) or any(packet['hp']):
   assert packet==expected(counts) and c.counter()==0,(counts,fps,gap,frame,packet,c.counter())
   found.append(dict(frame=frame,**packet))
 assert len(found)==round(1/gap),(counts,fps,gap,found)
 assert all((b['frame']-a['frame'])/fps<1 for a,b in zip(found,found[1:]))
 assert all(n['id'] in roots for n in c.nodes())
 record('repeat',c,copies=counts,fps=fps,marker=6909,gap=gap,recoveries=found,finalNodes=c.nodes())
for kind,copies in itertools.product(range(2),(1,2,3)):
 counts=[copies if i==kind else 0 for i in range(2)];c=start(counts)
 def compare():
  ptr=struct.unpack('<Q',c.u.mem_read(OBJ+8,8))[0]
  while ptr:
   c.invoke(0x50dbb0,[ptr+0x10]);ptr=struct.unpack('<Q',c.u.mem_read(ptr+0x38,8))[0]
 c.add(32);compare();compare();once=c.queue()
 assert once==[leaves[kind]]*copies
 c.add(68);compare();assert c.queue()==once
 c.add(-69);compare();assert c.counter()==31 and c.queue()==once
 c.add(1);compare();twice=c.queue();assert twice==once*2
 record('dedupe',c,effect=roots[kind],copies=copies,firstQueue=once,rearmedQueue=twice)
output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),
 effects=effects,roots=roots,leaves=leaves,threshold=32,checks=checks,
 rows={str(i):{k:x.spells[str(i)][k] for k in ('stateInfo','spCategory','effectEndurance','motionInterval',
 'accumuOverFireId','accumuOverVal','accumuVal','dedupeAccumuTrigger','changeHpRate','changeMpRate','syncTotalHp')}
 for i in roots+leaves},native=dict(accumulation='50DBB0 / 50E240 / 50E570 / 50E5E0 / 50E680',
 update='50ACD0 / 511B80 / 511D20',grant='3C7FD0 → 3DB410 → 50D060',resources='506EC0 / 507460'),
 stubs=sorted(stubs|{'hit markers arrive at supplied times; resource packets do not execute final current HP/FP setters or overflow',
 'attack weights are tested as supplied marker rows, not a fixed number of actual combat hits'}),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(map(len,checks.values())),'native successive recovery scenarios')
