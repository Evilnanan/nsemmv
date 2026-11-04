"""Execute successive-attack tier multipliers, duplicate roots and gradual decay.

Original accumulation, self-grants, eligibility, expiry and attack arithmetic
consume actual rows. Supplied hit-marker arrivals do not simulate combat.
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

    def counter(self):return self.invoke(0x50e570,[self.manager,0])&0xffffffff
    def add(self,amount):self.invoke(0x50e240,[self.manager,0,amount])
    def queue(self):
        slot=self.manager+0x40+0*0x20
        begin,end=struct.unpack('<QQ',self.u.mem_read(slot+8,16))
        return list(struct.unpack('<'+'i'*((end-begin)//4),self.u.mem_read(begin,end-begin)))

roots=[7037600,7037601,7037602];watchers=roots+[7037603];leaves=list(range(7037604,7037608))
thresholds=[17,30,45,60];rates=[1.05,1.065,1.09,1]
attach=x.x['tables']['AttachEffectParam']['7037600']
assert [attach['passiveSpEffectId_'+str(i)] for i in (1,2,3)]==roots and attach['exclusivityId']==-1
for i,(root,leaf) in enumerate(zip(watchers,leaves)):
 r=x.spells[str(root)];s=x.spells[str(leaf)]
 assert r['stateInfo']==s['stateInfo']==303 and r['spCategory']==20 and s['spCategory']==120
 if i<3:assert r['effectEndurance']==-1
 assert r['accumuOverVal']==thresholds[i] and r['accumuOverFireId']==leaf and r['dedupeAccumuTrigger']==0
 assert s['accumuVal']==-1 and s['effectEndurance']==(1.5 if i<3 else 0)
 assert all(math.isclose(s[k+'AttackRate'],rates[i],rel_tol=1e-6) for k in ('physics','magic','fire','thunder','dark'))
assert x.spells['7037602']['cycleOccurrenceSpEffectId']==7037603
assert math.isclose(x.spells['7037603']['effectEndurance'],.4,rel_tol=1e-6)
checks=dict(selection=[],threshold=[],multipliers=[],kinds=[],markers=[],lifecycle=[],mixed=[]);stubs=set()
def record(key,c,**row):checks[key].append(row);stubs.update(c.stubs)
def step(c,fps):c.qualify();c.update(1/fps)
def verify(values,expected):assert all(math.isclose(v,expected,rel_tol=2e-6) for v in values),(values,expected)
def start(copies,fps=60):
 c=Combo()
 for _ in range(copies):
  for root in roots:c.grant(root)
 for _ in range(fps//2):step(c,fps)
 return c
for copies,fps in itertools.product(range(4),(30,60,120)):
 c=start(copies,fps)
 for root in watchers:assert sum(n['id']==root for n in c.nodes())==int(bool(copies))
 verify(c.attack(),1)
 record('selection',c,copies=copies,fps=fps,nodes=c.nodes(),counter=c.counter())
for amount in (-100,0,16,17,29,30,44,45,59,60,100):
 c=start(1);c.add(amount)
 assert c.counter()==max(0,amount)
 for _ in range(2):
  ptr=struct.unpack('<Q',c.u.mem_read(OBJ+8,8))[0]
  while ptr:
   c.invoke(0x50dbb0,[ptr+0x10]);ptr=struct.unpack('<Q',c.u.mem_read(ptr+0x38,8))[0]
 expected=[leaf for leaf,threshold in zip(leaves,thresholds) if amount>=threshold]
 assert sorted(c.queue())==sorted(expected*2),(amount,c.queue(),expected,c.nodes())
 record('threshold',c,input=amount,counter=c.counter(),queued=c.queue())
for mask,copies in itertools.product(range(16),(1,3)):
 c=Combo()
 for i,leaf in enumerate(leaves):
  if mask&(1<<i):
   for _ in range(copies):c.grant(leaf)
 c.qualify();c.update(0);c.qualify()
 expected=math.prod(rate for i,rate in enumerate(rates) if mask&(1<<i))
 values=c.attack();verify(values,expected)
 record('multipliers',c,mask=mask,copies=copies,values=values,nodes=c.nodes())
 if copies==1 and mask in (0,1,7,15):
  for kind in range(13):
   values=c.attack(kind);verify(values,1 if kind==5 else expected)
   record('kinds',c,mask=mask,kind=kind,values=values)
for marker,present in itertools.product(range(6900,6910),(False,True)):
 c=Combo()
 if present:c.grant(7037601) # no periodic subtraction during this isolated marker check
 for _ in range(5):step(c,60)
 c.grant(marker);step(c,60);step(c,60)
 weight=x.spells[str(marker)]['accumuVal'];assert c.counter()==(weight if present else 0)
 record('markers',c,marker=marker,present=present,weight=weight,counter=c.counter())
def lifecycle(copies,fps,recoveryCopies=0):
 c=Combo()
 for _ in range(copies):
  for root in roots:c.grant(root)
 for _ in range(recoveryCopies):c.grant(7036000)
 transitions=[];previous=None;peak=1;recoveries=[]
 for frame in range(25*fps):
  if fps//6<=frame<=fps*13//6 and (frame-fps//6)%(fps//5)==0:c.grant(6909)
  step(c,fps);values=c.attack();value=values[0];peak=max(peak,value)
  active=[n['id'] for n in c.nodes() if 7037604<=n['id']<=7037606 and not(n['flags']&0x800c0003)]
  assert len(active)==len(set(active))
  verify(values,math.prod(rates[id-7037604] for id in active))
  current=tuple(sorted(active))
  if current!=previous:transitions.append(dict(frame=frame,counter=c.counter(),multiplier=value,active=active))
  previous=current
  if recoveryCopies:
   fp=c.fp(1000)
   if any(fp):
    assert fp==[50*recoveryCopies,0]
    recoveries.append(dict(frame=frame,fp=fp,attackCounter=c.counter(),recoveryCounter=c.invoke(0x50e570,[c.manager,1])&0xffffffff))
 assert math.isclose(peak,math.prod(rates),rel_tol=2e-6)
 assert not current and c.counter()==0
 assert all(n['id'] in watchers+[7036000] for n in c.nodes())
 assert any(t['active']==[7037604] for t in transitions)
 assert any(set(t['active'])=={7037604,7037605} for t in transitions)
 assert len(recoveries)==(5 if recoveryCopies else 0)
 if recoveryCopies:assert all(r['recoveryCounter']==0 and r['attackCounter']>0 for r in recoveries)
 return c,dict(copies=copies,fps=fps,recoveryCopies=recoveryCopies,peak=peak,transitions=transitions,
               recoveries=recoveries,finalCounter=c.counter(),finalNodes=c.nodes())
for copies,fps in itertools.product((1,3),(30,60,120)):
 c,row=lifecycle(copies,fps);record('lifecycle',c,**row)
for copies in (1,3):
 c,row=lifecycle(1,60,copies);record('mixed',c,**row)
for fps in (30,60,120):
 rows=[r for r in checks['lifecycle'] if r['fps']==fps]
 assert rows[0]['transitions']==rows[1]['transitions']
output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),
 effect=7037600,roots=roots,watchers=watchers,leaves=leaves,thresholds=thresholds,rates=rates,checks=checks,
 rows={str(i):{k:x.spells[str(i)][k] for k in ('stateInfo','spCategory','effectEndurance','motionInterval','cycleOccurrenceSpEffectId',
 'accumuOverFireId','accumuOverVal','accumuVal','dedupeAccumuTrigger','physicsAttackRate')} for i in watchers+leaves},
 native=dict(accumulation='50DBB0 / 50E240 / 50E570 / 50E5E0 / 50E680',update='50ACD0 / 511B80 / 511D20',
 grant='3C7FD0 → 3DB410 → 50D060',attack='502830',fp='507460'),
 stubs=sorted(stubs|{'hit-marker arrival is supplied; collision, actual attack weights, animation interruption and multiplayer are not simulated'}),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(map(len,checks.values())),'native successive attack scenarios')
