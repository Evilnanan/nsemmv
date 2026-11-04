"""Execute Duchess self-ultimate selection, combo thresholds and timed tiers.

Native instructions perform animation relocation, conditional dispatch, effect
insertion, accumulation, renewal and attack multiplication. Actor/allocator and
PARAM lookup fixtures do not simulate collision or complete gameplay.
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
from unicorn.x86_const import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','assets','tae','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted)
assets=json.loads(a.assets.read_text());assert assets['hashes']['regulation.bin']==x.x['hashes']['regulation.bin']
wepraw=a.assets.with_suffix('.EquipParamWeapon.param').read_bytes();weapons=Inputs.table(wepraw,0x298)
behaviorraw=a.extracted.with_suffix('.BehaviorParam_PC.param').read_bytes();behaviors=Inputs.table(behaviorraw,0x30)
taeraw=a.tae.read_bytes();taesha='e0d4bc441fa9c14a699ab865e58313f24e81f0f4d51dab995bba3844fa3e0ce5'
assert sha(taeraw)==taesha
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

class Dispatch(Chain):
    def __init__(self):
        super().__init__(x)
        self.requests, self.emissions, self.frame = [], [], 0
        # Real Behavior resolver at +328; the other virtuals supply a synthetic
        # equipped weapon / owner identity. No state predicate is substituted.
        for off, ptr in [(0x118, STOP + 0x201), (0x190, STOP + 0x200), (0x260, STOP + 0x200),
                         (0x328, BASE + 0x668b30), (0x320, STOP + 0x201),
                         (0x250, STOP + 0x202), (0x28, STOP + 0x201), (0x178, STOP + 0x200)]:
            self.q(OBJ + 0x6200 + off, ptr)
        self.q(OBJ + 0x6190, OBJ)

    def hook(self, u, address, size, user):
        pc = address - BASE
        def finish(value=0):
            u.reg_write(UC_X86_REG_RAX, value)
            sp = u.reg_read(UC_X86_REG_RSP)
            u.reg_write(UC_X86_REG_RIP, struct.unpack('<Q', u.mem_read(sp, 8))[0])
            u.reg_write(UC_X86_REG_RSP, sp + 8)
        if address in (STOP + 0x200, STOP + 0x201, STOP + 0x202):
            self.stubs.add('synthetic player virtuals and equipped weapon 1000')
            finish({STOP + 0x200: 0, STOP + 0x201: 1, STOP + 0x202: 1000}[address])
        elif pc in (0x4d1b20, 0x3d4180, 0x3d4c10, 0xea9a60, 0xea76f0, 0x66b2d0, 0x27d0640):
            self.stubs.add(hex(pc) + ' isolated actor context / hand identity / empty animation reference list')
            finish()
        elif pc == 0x3ced90:
            self.stubs.add('3CED90 isolated actor context')
            finish(OBJ + 0xd000)
        elif pc == 0xea7fc0:
            self.stubs.add('EA7FC0 actual equipped-weapon row lookup')
            id = u.reg_read(UC_X86_REG_RDX) & 0xffffffff
            u.mem_write(OBJ + 0xb000, weapons[id])
            u.mem_write(u.reg_read(UC_X86_REG_RCX), struct.pack('<IIQ', id, 0, OBJ + 0xb000))
            finish()
        elif pc == 0xe6fcb0:
            self.stubs.add('E6FCB0 actual Behavior row lookup')
            id = u.reg_read(UC_X86_REG_RDX) & 0xffffffff
            assert id in (700000149, 700000150)
            u.mem_write(OBJ + 0xb800, behaviors[id])
            self.q(u.reg_read(UC_X86_REG_RCX) + 8, OBJ + 0xb800)
            finish()
        elif pc == 0x3975d0:
            self.stubs.add('3975D0 Behavior request recorder; active/stop and conditional-state gates are native')
            payload = bytes(u.mem_read(u.reg_read(UC_X86_REG_R9), 18))
            self.requests.append(dict(behavior=u.reg_read(UC_X86_REG_RDX),
                                      active=bool(payload[16]), instant=bool(payload[17]), payload=payload.hex()))
            finish(1)
        else:
            super().hook(u, address, size, user)


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

    def counter(self):return self.invoke(0x50e570,[self.manager,5])&0xffffffff
    def add(self,amount):self.invoke(0x50e240,[self.manager,5,amount])
    def queue(self):
        slot=self.manager+0x40+5*0x20
        begin,end=struct.unpack('<QQ',self.u.mem_read(slot+8,16))
        return list(struct.unpack('<'+'i'*((end-begin)//4),self.u.mem_read(begin,end-begin)))


checks=dict(selection=[],dispatch=[],threshold=[],multipliers=[],kinds=[],markers=[],lifecycle=[],duration=[])
stubs=set()
def record(key,c,**row):checks[key].append(row);stubs.update(c.stubs)
def step(c,fps):c.qualify();c.update(1/fps)
def verify(values,expected):assert all(math.isclose(v,expected,rel_tol=2e-6) for v in values),(values,expected)
def ptrs(c):
    ptr=struct.unpack('<Q',c.u.mem_read(OBJ+8,8))[0]
    while ptr:
        yield ptr
        ptr=struct.unpack('<Q',c.u.mem_read(ptr+0x38,8))[0]

effects=[7033000,7033001]
for effect in effects:
    attach=x.x['tables']['AttachEffectParam'][str(effect)]
    assert attach['passiveSpEffectId_1']==7033000 and attach['exclusivityId']==-1
root=x.spells['7033000']
assert root['spCategory']==20 and root['cycleOccurrenceSpEffectId']==7033001
assert math.isclose(root['motionInterval'],.1,rel_tol=1e-6)
assert x.spells['7033001']['stateInfo']==2021 and x.spells['7033002']['stateInfo']==2022
assert x.spells['7033001']['spCategory']==x.spells['7033002']['spCategory']==202
assert x.spells['7033001']['categoryPriority']==x.spells['7033002']['categoryPriority']==47

# Passive replacement occurs before the animation's 1.3667-second emission.
for copies,fps in itertools.product(range(4),(30,60,120)):
    c=Combo()
    for _ in range(copies):c.grant(7033000)
    for _ in range(fps//2):step(c,fps)
    c.grant(7033002)
    for _ in range(round(fps*1.3666667)):step(c,fps)
    states={id:bool(c.invoke(0x508e20,[OBJ,id])&255) for id in (2021,2022)}
    assert states=={2021:bool(copies),2022:not copies}
    assert sum(n['id']==7033000 for n in c.nodes())==bool(copies)
    record('selection',c,copies=copies,fps=fps,states=states,nodes=c.nodes())

# Relocate the actual animation, then iterate to each conditional behavior.
for animation,judge,state,active in itertools.product((630000,635000),(7149,7150),(0,2021,2022),(0,1)):
    c=Dispatch();tae=NativeTae(c,taeraw,taesha)
    assert tae.id==2903 and tae.bank==255
    if state:c.insert(7033001 if state==2021 else 7033002)
    c.qualify();c.update(0)
    ctx=OBJ+0xd100;c.u.mem_write(ctx,bytes(0x40));found=False
    for _ in range(1000):
        if not c.invoke(0x27d0400,[tae.animations[animation],ctx]):break
        typ=struct.unpack('<I',c.u.mem_read(ctx,4))[0]
        if typ!=2:continue
        payload=struct.unpack('<Q',c.u.mem_read(ctx+8,8))[0]
        raw=bytes(c.u.mem_read(payload,32))
        if struct.unpack_from('<i',raw,8)[0]!=judge:continue
        assert struct.unpack_from('<H',raw,14)[0]==(2021 if judge==7149 else 2022)
        assert struct.unpack('<H',c.u.mem_read(ctx+0x1a,2))[0]==255
        c.q(OBJ+0x8018,OBJ+0x6000);c.u.mem_write(ctx+0x18,bytes([active]))
        c.invoke(0x40cd80,[OBJ+0x8000,ctx]);found=True;break
    assert found
    expected=active and state==(2021 if judge==7149 else 2022)
    assert bool(c.requests)==bool(expected),(animation,judge,state,active,c.requests)
    if expected:assert c.requests[0]['behavior']==700000000+judge-7000
    record('dispatch',c,animation=animation,judge=judge,state=state,active=active,requests=c.requests)

bindings=[]
for behavior,bullet,effect,friendly,duration in ((700000149,30903011,7033010,0,25),(700000150,30903010,703500,1,15)):
    br=x.x['tables']['BehaviorParam_PC'][str(behavior)]
    bu=x.x['tables']['Bullet'][str(bullet)];atk=x.x['tables']['AtkParam_Pc'][str(bu['atkId_Bullet'])]
    assert br['refType']==1 and br['refId']==bullet and bu['spEffectId0']==effect
    assert atk['selfTarget']==1 and atk['friendlyTarget']==friendly and atk['opposeTarget']==0
    assert x.spells[str(effect)]['effectEndurance']==duration and x.spells[str(effect)]['stateInfo']==600
    if not friendly:assert bu['spEffectId2']==7033020
    bindings.append(dict(behavior=behavior,bullet=bullet,attack=bu['atkId_Bullet'],effect=effect,
                         selfTarget=1,friendlyTarget=friendly,opposeTarget=0,duration=duration))
    for copies,fps in itertools.product((1,3),(30,60,120)):
        c=Combo()
        for _ in range(copies):c.grant(effect)
        frames=0
        while c.nodes() and frames<(duration+1)*fps:step(c,fps);frames+=1
        assert not c.nodes() and abs(frames/fps-duration)<=3/fps+1e-6, (effect,copies,fps,frames,c.nodes())
        record('duration',c,effect=effect,copies=copies,fps=fps,expiryFrame=frames)

thresholds=[17,30,45,60];rates=[1.09,1.13,1.2,1.2]
for i in range(4):
    seed=x.spells[str(7033020+i)];watch=x.spells[str(7033024+i)];buff=x.spells[str(7033028+i)]
    assert seed['replaceSpEffectId']==7033024+i and seed['effectEndurance']==0
    assert seed['cycleOccurrenceSpEffectId']==(7033021+i if i<3 else -1)
    assert watch['stateInfo']==308 and watch['spCategory']==20 and watch['effectEndurance']==25
    assert watch['accumuOverVal']==thresholds[i] and watch['accumuOverFireId']==7033028+i
    assert watch['dedupeAccumuTrigger']==0
    assert buff['stateInfo']==308 and buff['accumuVal']==-1
    assert all(math.isclose(buff[k+'AttackRate'],rates[i],rel_tol=1e-6) for k in ('physics','magic','fire','thunder','dark'))
    assert buff['effectEndurance']==(1.5 if i<3 else 0)
    assert buff['spCategory']==(120 if i<3 else 20)

# Exercise the actual inclusive comparisons and native queue, including
# repeated evaluation and negative/clamped input. No timer changes here.
for amount in (-100,0,16,17,29,30,44,45,59,60,100):
    c=Combo()
    for id in range(7033024,7033028):c.grant(id)
    c.qualify();c.update(0);c.qualify();c.add(amount)
    assert c.counter()==max(0,amount), (amount,c.counter(),c.nodes(),c.invoke(0x508e20,[OBJ,308]))
    for _ in range(2):
        for ptr in ptrs(c):c.invoke(0x50dbb0,[ptr+0x10])
    expected=[7033028+i for i,t in enumerate(thresholds) if amount>=t]
    assert sorted(c.queue())==sorted(expected*2)
    record('threshold',c,input=amount,counter=c.counter(),queued=c.queue())

# Different tiers coexist and multiply. The first three leaves deduplicate;
# manually issuing multiple zero-life fourth leaves can multiply for one
# update. Equipment stacking is checked at the root and complete seed chain.
for mask,copies in itertools.product(range(16),(1,3)):
    c=Combo();expected=1
    for i,rate in enumerate(rates):
        if mask&(1<<i):
            for _ in range(copies):c.grant(7033028+i)
            expected*=rate**(copies if i==3 else 1)
    c.qualify();c.update(0);c.qualify()
    values=c.attack();verify(values,expected)
    assert len(c.nodes())==mask.bit_count()+((copies-1) if mask&8 else 0)
    record('multipliers',c,mask=mask,copies=copies,values=values,nodes=c.nodes())
    if copies==1 and mask in (0,1,7,15):
        for kind in range(13):
            values=c.attack(kind);verify(values,1 if kind==5 else expected)
            record('kinds',c,mask=mask,kind=kind,values=values)

# Actual hit-marker rows differ in contribution. Grant delivery is an input;
# this does not prove which combat collisions deliver each row.
for marker,present in itertools.product(range(6900,6910),(False,True)):
    c=Combo()
    if present:c.grant(7033025) # state 308 watcher with no periodic subtraction
    for _ in range(5):step(c,60)
    row=x.spells[str(marker)];assert row['stateInfo']==314 and row['accumuVal']==(marker-6899)*2
    c.grant(marker);step(c,60);step(c,60)
    assert c.counter()==(row['accumuVal'] if present else 0)
    record('markers',c,marker=marker,watcher=present,counter=c.counter(),weight=row['accumuVal'])

# Real immediate grant, zero-life seed/replacement chain and repeated markers.
# Stop the markers after 2.2 s, then observe native decay and final expiration.
for copies,fps in itertools.product((1,3),(30,60,120)):
    c=Combo()
    for _ in range(copies):c.grant(7033020)
    transitions=[];previous=None;peak=1;stopped=None
    for frame in range(27*fps):
        if fps//6<=frame<=fps*13//6 and (frame-fps//6)%(fps//5)==0:c.grant(6909)
        step(c,fps)
        values=c.attack();value=values[0];verify(values,value)
        peak=max(peak,value)
        active=[n['id'] for n in c.nodes() if 7033028<=n['id']<=7033031 and not(n['flags']&0x800c0003)]
        assert len(active)==len(set(active))
        verify(values,math.prod(rates[id-7033028] for id in active))
        current=round(value,6)
        if current!=previous:transitions.append(dict(frame=frame,counter=c.counter(),multiplier=current,active=active))
        if frame==3*fps:stopped=c.counter()
        previous=current;c.grants.clear()
    assert math.isclose(peak,math.prod(rates),rel_tol=2e-6)
    assert not c.nodes() and current==1 and stopped>0
    record('lifecycle',c,copies=copies,fps=fps,peak=peak,transitions=transitions,finalNodes=c.nodes())

output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),
            taeSha256=taesha,behaviorParamSha256=sha(behaviorraw),weaponParamSha256=sha(wepraw),
            effects=effects,root=7033000,bindings=bindings,thresholds=thresholds,rates=rates,
            rows={str(i):{k:x.spells[str(i)][k] for k in ('stateInfo','spCategory','effectEndurance','motionInterval',
                  'cycleOccurrenceSpEffectId','replaceSpEffectId','accumuOverVal','accumuOverFireId','accumuVal','dedupeAccumuTrigger','physicsAttackRate')}
                  for i in [7033000,7033001,7033002,7033010,703500,*range(7033020,7033032)]},
            checks=checks,native=dict(animation='27D0F10 / 27D0400 → 40CD80 → 668B30',
                  accumulation='50DA20 / 50DB20 / 50DBB0 → 50E240 / 50E570 / 50E5E0 / 50E680',
                  update='50ACD0 → 511B80 / 511D20',attack='502830',grant='3C7FD0 → 3DB410 → 50D060'),
            stubs=sorted(stubs|{'hit-marker arrival is supplied; full collision, animation scheduling and multiplayer not executed'}),
            gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(map(len,checks.values())),'native Duchess ultimate cases')

