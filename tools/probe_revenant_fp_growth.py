"""Partial proof of Revenant FP growth and activation notification deduplication.

Executes original component, grant, growth and FP-cap routines. Does not prove
which skill/passive events reach activation, permanent-effect restoration,
actor lifecycle or gameplay. No player-facing completion claim is generated.
"""
import argparse,json,struct,math
from pathlib import Path
from native_effect_runtime import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','output'):p.add_argument(name,type=Path)
a=p.parse_args();inputs=Inputs(a.exe,a.extracted)
assert sha(inputs.param)=='07ec636c5565d4551efeb53e6f08bc633b2aa4f2129f13c61b0638d69b1bc176'
attachraw=a.extracted.with_suffix('.AttachEffectParam.param').read_bytes()
assert sha(attachraw)=='ae8128ed510a532d0fa7cb56fa9c86e4a44c9d815dd4ee01c05821d5f50a9827'
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

checks={key:[] for key in ('growth','actorGuard','rootPresence','retention')};stubs=set()
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
out=dict(schema=1,status='partial',effect=6500500,gameplayVerified=False,
 inputs=dict(exeSha256=sha(inputs.raw),regulationSha256=inputs.x['hashes']['regulation.bin'],spEffectSha256=sha(inputs.param),attachEffectSha256=sha(attachraw)),
 native=dict(actorActivation='3C7F10',componentDispatch='4B3370',componentActivation='4CC320',effectLookup='507910',grant='3C7FD0',growth='3DB410',fpCap='6C91F0'),
 checks=checks,stubs=sorted(stubs),openQuestions=[
 'Which normal-family summon and passive-enemy-revival events reach activation, including failures and repeats',
 'permanentSpEffectId initialization/restore and actual starting growth tier',
 'Actor flag reset, component destruction/recreation, full actor lifecycle',
 'Equipment selection/rebuild, death, expedition transition and save/reload',
 'Final current/integer FP writes and multiplayer source ownership',
 'Whether MMV DLL changes these dispatch/eligibility paths'])
a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(map(len,checks.values())),'partial native Revenant FP checks',{k:len(v) for k,v in checks.items()},flush=True)
