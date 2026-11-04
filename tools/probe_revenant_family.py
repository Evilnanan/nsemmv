"""Trace Revenant ultimate requests into the three native family-controller slots.

Runs conditional animation dispatch, emission self-grant and controller request
selection. Scene creation/placement and existing controller state are fixtures;
this does not execute the family AI, state-machine update or multiplayer.
"""
import argparse,json,struct,itertools,math
from pathlib import Path
from native_effect_runtime import *
from native_ailment_runtime import Ailment
from native_animation_runtime import NativeTae
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','assets','animations','common','buddy','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted)
raws={name:a.extracted.with_suffix('.'+name+'.param').read_bytes() for name in ('BehaviorParam_PC','Bullet')}
behaviors=Inputs.table(raws['BehaviorParam_PC'],0x30);bullets=Inputs.table(raws['Bullet'],0x100)
weaponraw=a.assets.with_suffix('.EquipParamWeapon.param').read_bytes();weapons=Inputs.table(weaponraw,0x298)
assert json.loads(a.assets.read_text())['hashes']['regulation.bin']==x.x['hashes']['regulation.bin']
animations=json.loads(a.animations.read_text());track=next(t for b in animations['bundles'] for t in b['taes'] if t['ID']==2905)
taeraw=Path(str(a.animations)+'.2905.tae').read_bytes()
commonraw=a.common.with_suffix('.PlayerCommonParam.param').read_bytes()
assert json.loads(a.common.read_text())['hashes']['regulation.bin']==x.x['hashes']['regulation.bin']
off=struct.unpack_from('<Q',commonraw,0x48)[0];common=commonraw[off:]
buddyraw=a.buddy.read_bytes();assert sha(buddyraw)=='5d8653f1fae07f4cc7bc63c79c658c21837c8fd84e01ee0e3caeb04a3999e7c0'
buddy=Inputs.table(buddyraw,0x70)
root=7220310
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
            assert id in (600000282,600000283,600000284)
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


C=OBJ+0x60000;CONTROL=C+0x1000;MANAGER=C+0x2000;HEAD=C+0x2800
class Summon(Actor):
 def __init__(self,states,position=True,success=True):
  super().__init__();self.u.mem_map(C,0x10000);self.requests=[];self.position=position;self.success=success;self.shots=[];self.deliveries=[];self.q(OBJ+0x6350,STOP+0x700)
  self.q(OBJ+0xf160,C);self.q(C+0x10,CONTROL);self.globalq(0x3860df+7+0x38853b2,MANAGER)
  self.q(MANAGER+0x20,HEAD);self.u.mem_write(HEAD+0x19,b'\1')
  nodes=[C+0x2900+i*0x100 for i in range(3)]
  self.q(HEAD+8,nodes[1])
  for i,node in enumerate(nodes):
   self.q(node,nodes[0] if i==1 else HEAD);self.q(node+0x10,nodes[2] if i==1 else HEAD)
   self.u.mem_write(node+0x20,struct.pack('<i',270000+i*1000));self.q(node+0x28,node+0x40);self.u.mem_write(node+0x40,struct.pack('<i',27000000+i*100000))
   self.u.mem_write(CONTROL+0x18+i*0x60,bytes([states[i]]))
  self.globalq(0x38710f+7+0x3890132,C+0x3000);self.q(C+0x3010,C+0x3100)
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if pc==0xe87800:
   id=u.reg_read(UC_X86_REG_RDX)&0xffffffff;assert id in (30905102,30905103,30905104)
   u.mem_write(OBJ+0xe900,bullets[id]);ptr=u.reg_read(UC_X86_REG_RCX);u.mem_write(ptr,struct.pack('<QI',OBJ+0xe900,id));ret(ptr)
  elif pc==0x3c80a0:self.deliveries.append(u.reg_read(UC_X86_REG_RDX)&0xffffffff)  # observe original delivery
  elif pc==0x347700:self.shots.append(self.currentBullet);ret(int(self.success))
  elif pc==0x518f30:ret(OBJ+0x6000)
  elif address==STOP+0x700:ret(1)
  elif pc==0xe81650:
   ptr=u.reg_read(UC_X86_REG_RCX);u.mem_write(C+0x4000,common);self.q(ptr,C+0x4000);ret(ptr)
  elif pc==0xe71710:
   ptr=u.reg_read(UC_X86_REG_RCX);id=struct.unpack('<i',u.mem_read(ptr,4))[0];u.mem_write(C+0x5000,buddy[id]);self.q(ptr+8,C+0x5000);ret(ptr)
  elif pc==0xe954f0:ret(u.reg_read(UC_X86_REG_RCX))
  elif pc==0x3886a0:
   u.mem_write(u.reg_read(UC_X86_REG_RDX),struct.pack('<4f',0,0,0,1));u.mem_write(u.reg_read(UC_X86_REG_R8),struct.pack('<f',0));ret(int(self.position))
  elif pc==0x26909a0:ret(u.reg_read(UC_X86_REG_RAX))
  elif pc==0x385410:
   dst=u.reg_read(UC_X86_REG_RDX);u.mem_write(dst,bytes(u.mem_read(u.reg_read(UC_X86_REG_R8),16)));ret(dst)
  elif pc==0x3882e0:ret()
  elif pc==0xb31770:self.requests.append(u.reg_read(UC_X86_REG_RDX));ret()
  else:super().hook(u,address,size,user)
 def emit(self,id):
  self.currentBullet=id;slot=OBJ+0x1a000;self.u.mem_write(slot,bytes(0x600));self.u.mem_write(slot+0x329,b'\1');self.u.mem_write(slot+0x334,struct.pack('<I',id));self.u.mem_write(slot+0x494,b'\1')
  self.invoke(0x343280,[slot],{UC_X86_REG_XMM1:1/60})
 def status(self):
  return [dict(state=self.u.mem_read(CONTROL+0x18+i*0x60,1)[0],
   request=self.u.mem_read(CONTROL+0x24+i*0x60,1)[0],flags=self.u.mem_read(CONTROL+0x64+i*0x60,1)[0]) for i in range(3)]

checks={k:[] for k in ('dispatch','controller','emission','repeat','mapping')};stubs=set()
def record(key,c,**row):checks[key].append(row);stubs.update(c.stubs)
assert x.x['tables']['AttachEffectParam']['7220210']['passiveSpEffectId_1']==root
assert x.spells[str(root)]['stateInfo']==2034 and x.spells[str(root)]['spCategory']==20
families=[]
for i in range(3):
 id=27000000+i*100000;trigger=270000+i*1000
 assert struct.unpack_from('<i',common,0xf4+4*i)[0]==id
 values=struct.unpack_from('<5i3f',buddy[id],4)
 assert values[0]==trigger
 sp=x.spells[str(trigger)];behavior=x.x['tables']['BehaviorParam_PC'][str(600000282+i)];bullet=x.x['tables']['Bullet'][str(30905102+i)]
 assert sp['stateInfo']==357 and sp['spCategory']==0 and math.isclose(sp['effectEndurance'],.05,rel_tol=1e-6)
 assert behavior['refType']==1 and behavior['refId']==30905102+i
 assert bullet['numShoot']==1 and bullet['spEffectIDForShooter']==trigger and bullet['atkId_Bullet']==-1
 families.append(dict(slot=i,buddy=id,trigger=trigger,npc=values[1],think=values[2],active=values[3],inactive=values[4]))
events=[dict(animation=an['ID'],**e) for an in track['animations'] for e in an['events']
 if e['Type']==2 and struct.unpack_from('<H',bytes.fromhex(e['hex']),14)[0]==2034]
assert [(e['animation'],e['index']) for e in events]==[(650000,96),(650000,97),(650000,98)]
assert [struct.unpack_from('<i',bytes.fromhex(e['hex']),8)[0] for e in events]==[6282,6283,6284]
for copies,enabled in itertools.product((0,1,3),(0,1)):
 c=Dispatch()
 for _ in range(copies):c.insert(root)
 c.qualify();c.update(0);loader=NativeTae(c,taeraw,track['sha256']);assert loader.id==2905
 ctx=OBJ+0xd100;c.u.mem_write(ctx,bytes(0x40));found=0
 while c.invoke(0x27d0400,[loader.animations[650000],ctx]):
  if struct.unpack('<I',c.u.mem_read(ctx,4))[0]!=2:continue
  ptr=struct.unpack('<Q',c.u.mem_read(ctx+8,8))[0];payload=bytes(c.u.mem_read(ptr,32))
  if payload not in [bytes.fromhex(e['hex']) for e in events]:continue
  c.q(OBJ+0x8018,OBJ+0x6000);c.u.mem_write(ctx+0x18,bytes([enabled]));c.requests.clear()
  c.invoke(0x40cd80,[OBJ+0x8000,ctx]);expected=bool(copies and enabled)
  assert len(c.requests)==expected
  if expected:assert c.requests[0]['behavior']==600000282+found and c.requests[0]['instant']
  record('dispatch',c,copies=copies,enabled=bool(enabled),event=found,requests=c.requests[:]);found+=1
 assert found==3,(copies,enabled,found,[(len(e['hex']),e['hex']) for e in events])
for state,position in itertools.product(range(13),(False,True)):
 c=Summon([state]*3,position)
 for id in (270000,271000,272000):c.grant(id)
 status=c.status()
 assert c.requests==([27000000,27100000,27200000] if position and state==0 else [])
 assert all(r==dict(state=state,request=int(position and state==0),flags=2*int(position and state==11)) for r in status)
 record('controller',c,state=state,position=position,status=status,assetRequests=c.requests)
# Isolate each ID: a single emission may only modify its own controller slot.
for i,success in itertools.product(range(3),(False,True)):
 c=Summon([0]*3,success=success);c.emit(30905102+i)
 assert c.shots==[30905102+i]
 assert c.deliveries==([270000+i*1000] if success else []),(i,success,c.deliveries,c.status())
 assert c.requests==([27000000+i*100000] if success else [])
 assert [r['request'] for r in c.status()]==[int(success and i==j) for j in range(3)]
 record('emission',c,slot=i,success=success,shots=c.shots,deliveries=c.deliveries,status=c.status(),assetRequests=c.requests)
for states in ((0,0,0),(11,11,11),(0,11,5),(4,0,11),(11,9,0)):
 c=Summon(states)
 for repeat in range(3):
  for id in (30905102,30905103,30905104):c.emit(id)
  expected=[dict(state=s,request=int(s==0),flags=2*int(s==11)) for s in states]
  assert c.status()==expected
  record('repeat',c,states=states,repeat=repeat+1,status=c.status(),assetRequests=c.requests[:])
for id in (269999,270000,270001,271000,272000,273000):
 c=Summon([0]*3);result=c.invoke(0x38ac90,[MANAGER,id])&0xffffffff
 expected=27000000+(id-270000)*100 if id in (270000,271000,272000) else 0xffffffff
 assert result==expected
 index=c.invoke(0x38a9f0,[MANAGER,result])&0xffffffff
 assert index==((id-270000)//1000 if expected!=0xffffffff else 0xffffffff)
 record('mapping',c,trigger=id,buddy=result,slot=index)
output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),
 assetHashes={**{k:sha(v) for k,v in raws.items()},'weapon':sha(weaponraw),'tae':sha(taeraw),'common':sha(commonraw),'buddy':sha(buddyraw)},
 effects=[7220210],root=root,families=families,events=events,checks=checks,
 stubs=sorted(stubs|{'E81650/E71710 actual PlayerCommon and Buddy row lookups; exact three-row effect-to-buddy tree supplied',
 'actor virtual +150 true overrides base fixture; actual local-player identity comparison executes',
 'E954F0 absent NPC row, zero collision radius; 3886A0 explicit available/unavailable owner position',
 '385410 candidate placement passthrough and 3882E0 ground-placement sink; no scene geometry',
 'B31770 asset preload recorder; controller states supplied, controller update/AI not executed',
 'E87800 actual Bullet rows; 347700 controlled emission outcome and 518F30 source identity',
 '26909A0 security-cookie return preserves RAX; full animation scheduler and multiplayer not executed'}),
 native=dict(animation='27D0F10 / 27D0400 → 40CD80 → 668B30',selfGrant='343280 → 3C7F40 → 3C80A0',
 controller='3DB410 → 460820 → 3860D0 → 38AC90 / 38A9F0 / 386D20'),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(map(len,checks.values())),'native Revenant family checks',{k:len(v) for k,v in checks.items()},flush=True)
