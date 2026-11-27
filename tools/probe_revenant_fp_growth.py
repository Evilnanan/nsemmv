"""Partial proof of Revenant FP growth and activation notification deduplication.

Executes original component, grant, growth and FP-cap routines. Does not prove
which skill/passive events reach activation, permanent-effect restoration,
actor lifecycle or gameplay. No player-facing completion claim is generated.
"""
import argparse,json,struct,math,itertools
from pathlib import Path
from native_effect_runtime import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','output'):p.add_argument(name,type=Path)
a=p.parse_args();inputs=Inputs(a.exe,a.extracted)
assert sha(inputs.param)=='07ec636c5565d4551efeb53e6f08bc633b2aa4f2129f13c61b0638d69b1bc176'
attachraw=a.extracted.with_suffix('.AttachEffectParam.param').read_bytes()
assert sha(attachraw)=='ae8128ed510a532d0fa7cb56fa9c86e4a44c9d815dd4ee01c05821d5f50a9827'
attachrows=Inputs.table(attachraw,0x44)
assert attachrows[6500500][0x27]==1 and struct.unpack_from('<i',attachrows[6500500],0x40)[0]==7500501
commonraw=a.extracted.with_suffix('.PlayerCommonParam.param').read_bytes()
assert sha(commonraw)=='2e7b384f9590e6fa3f19b2f93e3826cebf8d399246fe987382086a445f7f096c'
assert struct.unpack_from('<H',commonraw,10)[0]==1
common=commonraw[struct.unpack_from('<Q',commonraw,0x48)[0]:]
assert struct.unpack_from('<f',common,0x15c)[0]==35 and struct.unpack_from('<f',common,0x16c)[0]==100
attach=inputs.x['tables']['AttachEffectParam']['6500500']
assert (attach['passiveSpEffectId_1'],attach['permanentSpEffectId'])==(7500500,7500501)
assert [k for k,v in attach.items() if k.startswith('allow') and v]==['allowRevenant']
assert (inputs.spells['7500500']['stateInfo'],inputs.spells['7500500']['spCategory'],inputs.spells['7500500']['necromancyActivationSpEffectId'])==(2119,20,7500501)
assert struct.unpack_from('<i',inputs.rows[7500500],0x3cc)[0]==7500501
for id in range(7500501,7500531):
 r=inputs.spells[str(id)]
 assert (r['stateInfo'],r['spCategory'],r['categoryPriority'],r['saveCategory'],r['effectEndurance'])==(0,204,1,9,-1)
 assert sum(struct.unpack_from('<i',inputs.param,0x40+i*24)[0]==id for i in range(struct.unpack_from('<H',inputs.param,10)[0]))==1
root,seed=7500500,7500501
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
            self.stubs.add('actor virtuals +10 player, +590 type 0, +118/+120 false; default +150 false (Revive overrides); explicit local identity and mode')
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

class Activation(Growth):
 def hook(self,u,address,size,user):
  if address-BASE==0x27f2470:
   self.stubs.add('27F2470 existing type-0x26 component fixture; component allocation/registration not executed')
   assert u.reg_read(UC_X86_REG_RDX)==0x26
   u.reg_write(UC_X86_REG_RAX,OBJ+0xc000)
   sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8);return
  super().hook(u,address,size,user)
 def activate(self,actor,enabled=1):
  self.invoke(0x3c7f10,[actor,enabled]);self.qualify();self.update(0)
 def fp(self):
  self.invoke(0x6c91f0,[1000,OBJ]);return struct.unpack('<f',(self.u.reg_read(UC_X86_REG_XMM0)&0xffffffff).to_bytes(4,'little'))[0]

class Revive(Activation):
 def __init__(self,copies=1,distance=0,draw=0,accept=1,local_virtual=1):
  super().__init__(copies);self.distance=distance;self.draw=draw;self.accept=accept;self.calls=[];self.endpoint=None;self.local_virtual=local_virtual;self.draws=0;self.requests=0
  self.q(OBJ+0x6350,STOP+0x203)
  self.q(OBJ+0x6008,123);self.q(OBJ+0xd168,OBJ+0xe000)
  self.q(OBJ+0x30000,OBJ+0x32000);self.q(OBJ+0x30198,123)
  self.q(OBJ+0x30190,OBJ+0x38000)  # target has an explicit empty effect container
  self.u.mem_write(OBJ+0x301f6,b'\x04')
  self.q(OBJ+0x321a0,STOP+0x204);self.q(OBJ+0x33000,OBJ+0x34000)
  self.u.mem_write(OBJ+0x3426a,b'\1')
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(value=0):
   u.reg_write(UC_X86_REG_RAX,value&0xffffffffffffffff);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if pc in (0x393619,0x3936b8,0x3937ae):self.endpoint=hex(pc);u.reg_write(UC_X86_REG_RIP,STOP);return
  if 0x3930f0<=pc<0x3937ea and u.mem_read(address,1)==b'\xe8':
   self.calls.append(hex(pc+5+struct.unpack('<i',u.mem_read(address+1,4))[0]))
  if address==STOP+0x203:
   self.stubs.add('explicit local actor virtual +150 predicate for revival candidate tests');ret(self.local_virtual)
  elif address==STOP+0x204:
   self.stubs.add('synthetic target NPC wrapper; +26A eligibility bit explicit, not an actual NPC row');ret(OBJ+0x33000)
  elif pc==0x3d0e60:
   self.stubs.add('explicit actor positions; native squared-distance comparison against actual PlayerCommon row')
   ptr=u.reg_read(UC_X86_REG_RDX);dist=self.distance if u.reg_read(UC_X86_REG_RCX)==OBJ+0x30000 else 0
   u.mem_write(ptr,struct.pack('<4f',dist,0,0,1));ret(ptr)
  elif pc==0xe81650:
   self.stubs.add('E81650 actual pinned PlayerCommon row lookup')
   ptr=u.reg_read(UC_X86_REG_RCX);u.mem_write(OBJ+0xb000,common);self.q(ptr,OBJ+0xb000);ret(ptr)
  elif pc in (0x216b9a0,0x216ba10,0x47f740,0x4e78c0):
   self.stubs.add('216B9A0/216BA10 lock sinks; 47F740 candidate-registration sink; 4E78C0 handle-cleanup sink');ret()
  elif pc==0x282970:
   self.stubs.add('282970 synthetic target handle wrapper')
   ptr=u.reg_read(UC_X86_REG_RDX);u.mem_write(ptr,bytes(12));ret(ptr)
  elif pc==0x6af4f0:
   self.stubs.add('6AF4F0 RNG owner fixture');ret(OBJ+0x35000)
  elif pc==0xf56200:
   self.stubs.add('F56200 explicit random draw; native probability comparison, not RNG distribution');self.draws+=1
   u.reg_write(UC_X86_REG_XMM0,int.from_bytes(struct.pack('<f',self.draw),'little'));ret()
  elif pc==0x519ef0:
   self.stubs.add('519EF0 explicit acceptance of revival request; no world spawning');self.requests+=1;ret(self.accept)
  else:super().hook(u,address,size,user)
 def attempt(self):
  self.endpoint=None;self.invoke(0x3930f0,[OBJ+0x36000,OBJ+0x30000]);self.qualify();self.update(0)

checks={key:[] for key in ('growth','actorGuard','rootPresence','retention','counter','revival','revivalGuards','revivalRepeat')};stubs=set()
def record(key,c,**row):
 checks[key].append(dict(**row,fp=c.fp(),nodes=c.nodes(),grants=list(c.grants)))
 stubs.update(c.stubs)
def expected(level):return 1000*inputs.spells[str(7500500+level)]['maxMpRate'] if level else 1000
def verify(c,level):
 assert math.isclose(c.fp(),expected(level),rel_tol=1e-6),(c.fp(),level)
 leaves=[n['id'] for n in c.nodes() if seed<=n['id']<=7500530]
 assert leaves==([7500500+level] if level else []),leaves
# A direct activation is a component notification, not one declared game cast.
for copies in (0,1,3,6):
 c=Activation(copies)
 assert sum(n['id']==root for n in c.nodes())==int(bool(copies))
 for index in range(36):
  c.invoke(0x4cc320,[OBJ+0xc000,1]);c.qualify();c.update(0)
  level=min(index+1,30) if copies else 0;verify(c,level)
  record('growth',c,copies=copies,notification=index+1,level=level)
# Do not reset the actor bit to manufacture additional successful activations.
for copies in (0,1,3,6):
 c=Activation(copies)
 for index,(actor,enabled,level) in enumerate(((OBJ+0x30000,1,1),(OBJ+0x30000,1,1),(OBJ+0x31000,1,2),(OBJ+0x32000,0,2),(OBJ+0x32000,1,2))):
  c.activate(actor,enabled);verify(c,level if copies else 0)
  flag=c.u.mem_read(actor+0x1f9,1)[0];assert flag&0x80
  record('actorGuard',c,copies=copies,step=index+1,actor=hex(actor),enabled=enabled,flag=flag)
for state in ('enabled','disabled','removed'):
 c=Activation(1)
 if state=='disabled':
  node=struct.unpack('<Q',c.u.mem_read(OBJ+8,8))[0]
  c.u.mem_write(node+0x68,struct.pack('<I',0x800c0003))
 elif state=='removed':c.invoke(0x505280,[OBJ,0])
 c.activate(OBJ+0x30000);verify(c,0 if state=='removed' else 1)
 record('rootPresence',c,state=state)
# Time updates and isolated root removal are not death/save/equipment rebuild.
for copies in (1,3):
 c=Activation(copies);c.activate(OBJ+0x30000)
 for elapsed in (1,15,40,300):
  c.qualify();c.update(elapsed);verify(c,1)
  record('retention',c,copies=copies,deltaSeconds=elapsed)
 c.invoke(0x505280,[OBJ,0]);c.qualify();c.update(0);verify(c,1)
 c.activate(OBJ+0x31000);verify(c,1)
 record('retention',c,copies=copies,rootRemoved=True)
# The raw +27 mode is not preserved by the current dummy-byte PARAMDEF.
# Execute both accessors and the actual counter; do not infer a grant from +40.
def counter(c):
 c.u.mem_write(OBJ+0xa800,attachrows[6500500]);c.q(OBJ+0xa900,OBJ+0xa800)
 reference=c.invoke(0xe6e3d0,[OBJ+0xa900])&0xffffffff
 mode=c.invoke(0xe6e300,[OBJ+0xa900])&255
 assert reference==seed and mode==1
 return c.invoke(0x501f00,[OBJ,reference,mode])&0xffffffff
for copies in (0,1,3,6):
 c=Activation(copies)
 for level in range(31):
  if level:c.arrive();c.qualify();c.update(0)
  # Explicit leaf grants also work without the equipped root; this tests counter semantics.
  assert counter(c)==level
  record('counter',c,copies=copies,level=level,counter=counter(c))
for scenario in ('unrelated','disabled','root-only'):
 c=Activation(1)
 if scenario=='unrelated':c.arrive(7031502);c.qualify();c.update(0)
 elif scenario=='disabled':
  c.arrive();c.qualify();c.update(0)
  node=struct.unpack('<Q',c.u.mem_read(OBJ+8,8))[0]
  while struct.unpack('<i',c.u.mem_read(node+8,4))[0]!=seed:node=struct.unpack('<Q',c.u.mem_read(node+0x38,8))[0]
  c.u.mem_write(node+0x68,struct.pack('<I',0x800c0003))
 assert counter(c)==0
 record('counter',c,scenario=scenario,counter=0)
# Full candidate routine entry to success/failure/early-exit boundary, with
# explicit scene identity, positions, RNG draw and world-acceptance result.
for copies,distance,draw,accept in itertools.product((0,1,3),(0,99.99,100,100.01),(0,34.99,35,35.0001,100),(0,1)):
 c=Revive(copies,distance,draw,accept);c.attempt()
 passed=distance<=100 and draw<=35
 endpoint='0x393619' if passed and accept else '0x3936b8' if passed else '0x3937ae'
 assert c.endpoint==endpoint
 assert c.draws==int(distance<=100) and c.requests==int(passed)
 verify(c,int(bool(copies and passed and accept)))
 record('revival',c,copies=copies,distance=distance,draw=draw,accept=accept,endpoint=c.endpoint,requests=c.requests,calls=c.calls)
for copies,guard in itertools.product((0,1,3),('local-predicate','target-flag','npc-flag','unowned','no-local-actor')):
 c=Revive(copies)
 if guard=='local-predicate':c.local_virtual=0
 elif guard=='target-flag':c.u.mem_write(OBJ+0x301f6,b'\0')
 elif guard=='npc-flag':c.u.mem_write(OBJ+0x3426a,b'\0')
 elif guard=='unowned':c.q(OBJ+0x30198,124)
 else:c.q(OBJ+0x574e8,0)
 c.attempt();verify(c,0)
 assert c.endpoint=='0x3937ae' and c.draws==c.requests==0
 record('revivalGuards',c,copies=copies,guard=guard,endpoint=c.endpoint,calls=c.calls)
for copies in (0,1,3):
 c=Revive(copies)
 for repeat in (1,2,3):
  c.attempt();verify(c,int(bool(copies)))
  assert c.endpoint=='0x393619' and len(c.grants)==1
  record('revivalRepeat',c,copies=copies,repeat=repeat,endpoint=c.endpoint)
out=dict(schema=1,status='partial',effect=6500500,gameplayVerified=False,
 inputs=dict(exeSha256=sha(inputs.raw),regulationSha256=inputs.x['hashes']['regulation.bin'],spEffectSha256=sha(inputs.param),attachEffectSha256=sha(attachraw),playerCommonSha256=sha(commonraw)),
 native=dict(revivalCandidate='3930F0',revivalProbability='507AA0',counterReference='E6E3D0',counterMode='E6E300',counter='501F00',actorActivation='3C7F10',componentDispatch='4B3370',componentActivation='4CC320',effectLookup='507910',grant='3C7FD0',growth='3DB410',fpCap='6C91F0'),
 checks=checks,stubs=sorted(stubs),openQuestions=[
 'Complete normal-family summon versus passive-enemy-revival event ownership; candidate gates now execute with explicit scene/RNG/world-acceptance fixtures',
 'Actual equipment initialization/restore and starting growth tier; raw +40 and +27 are proven counter reference/mode, not a grant in inspected consumers',
 'Actor flag reset, component destruction/recreation, full actor lifecycle',
 'Equipment selection/rebuild, death, expedition transition and save/reload',
 'Final current/integer FP writes and multiplayer source ownership',
 'Whether MMV DLL changes these dispatch/eligibility paths'])
a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(map(len,checks.values())),'partial native Revenant FP checks',{k:len(v) for k,v in checks.items()},flush=True)
