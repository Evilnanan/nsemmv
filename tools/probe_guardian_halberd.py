"""Trace Guardian charged-halberd shockwave's native animation gate and active lifetime.

Real TAE relocation, Behavior resolution, shot-count loops and lifetime updates
execute pinned instructions. Projectile creation and scene helpers are recorders;
standalone emitter counts do not prove child spawning or overlapping damage.
"""
import argparse,json,struct,itertools,math
from pathlib import Path
from native_effect_runtime import *
from native_animation_runtime import NativeTae
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','assets','animations','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted);inputs=x
raws={name:a.extracted.with_suffix('.'+name+'.param').read_bytes() for name in ('AtkParam_Pc','BehaviorParam_PC','Bullet')}
attacks=Inputs.table(raws['AtkParam_Pc'],0x1d0);behaviors=Inputs.table(raws['BehaviorParam_PC'],0x30);bullets=Inputs.table(raws['Bullet'],0x100)
weaponraw=a.assets.with_suffix('.EquipParamWeapon.param').read_bytes();weapons=Inputs.table(weaponraw,0x298)
assert json.loads(a.assets.read_text())['hashes']['regulation.bin']==x.x['hashes']['regulation.bin']
animations=json.loads(a.animations.read_text());track=next(t for b in animations['bundles'] for t in b['taes'] if t['ID']==2271)
taeraw=Path(str(a.animations)+'.2271.tae').read_bytes()
root=7011600
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
            assert id in (600000098,600000099)
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

class Emitter(Chain):
 def __init__(self,id):super().__init__(x);self.frame=0;self.shots=[];self.id=id
 def hook(self,u,address,size,user):
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP)
   u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  pc=address-BASE
  if pc==0xe87800:
   assert u.reg_read(UC_X86_REG_RDX)&0xffffffff==self.id
   self.stubs.add('E87800 actual Guardian Bullet lookup')
   u.mem_write(OBJ+0xe900,bullets[self.id]);ptr=u.reg_read(UC_X86_REG_RCX)
   u.mem_write(ptr,struct.pack('<QI',OBJ+0xe900,self.id));ret(ptr)
  elif pc==0x3473d0:
   self.stubs.add('3473D0 individual projectile creation recorder; native count and loop execute')
   self.shots.append(self.frame);ptr=u.reg_read(UC_X86_REG_RDX);self.q(ptr,len(self.shots));ret(ptr)
  else:super().hook(u,address,size,user)

def global_pointer(c, rva, value):
    page = rva & ~4095
    c.u.mem_map(BASE+page, 4096)
    c.u.mem_write(BASE+page, inputs.pe.get_data(page, 4096).ljust(4096, b'\0'))
    c.q(BASE+rva, value)

class Lifetime(Chain):
    def hook(self, u, address, size, user):
        pc = address - BASE
        def finish(value=0):
            u.reg_write(UC_X86_REG_RAX, value)
            sp = u.reg_read(UC_X86_REG_RSP)
            u.reg_write(UC_X86_REG_RIP, struct.unpack('<Q', u.mem_read(sp, 8))[0])
            u.reg_write(UC_X86_REG_RSP, sp+8)
        if pc == 0x26909a0:
            self.stubs.add('26909A0 security cookie; preserve return register')
            finish(u.reg_read(UC_X86_REG_RAX))
        elif address in (STOP+0x200, STOP+0x208, STOP+0x210):
            self.stubs.add('synthetic active-phase virtuals do not request early termination')
            finish()
        elif pc in (0x359c80, 0x355d20, 0x355fe0, 0x350410, 0x34b750, 0x33e770,
                    0x33e570, 0x353bb0, 0x362c00, 0x3482e0, 0x3482b0, 0x34da00, 0x353df0, 0x353cb0):
            self.stubs.add(hex(pc)+' scene/physics/visual fixture; no collision simulation')
            finish()
        else:
            super().hook(u, address, size, user)


# All radius claims below concern the actual attack row, not the approach projectile.
checks={k:[] for k in ('dispatch','emitter','chain','lifetime','radius','attackSetup')};stubs=set()
def record(key,c,**row):checks[key].append(row);stubs.update(c.stubs)
assert x.x['tables']['AttachEffectParam'][str(root)]['passiveSpEffectId_1']==root
assert x.x['tables']['AttachEffectParam'][str(root)]['exclusivityId']==-1
assert x.spells[str(root)]['stateInfo']==2036 and x.spells[str(root)]['spCategory']==20
for behavior,bullet in ((600000098,30901145),(600000099,30901147)):
    row=x.x['tables']['BehaviorParam_PC'][str(behavior)]
    assert row['refType']==1 and row['refId']==bullet
events=[dict(animation=an['ID'],**e) for an in track['animations'] for e in an['events']
        if e['Type']==2 and struct.unpack_from('<H',bytes.fromhex(e['hex']),14)[0]==2036]
assert [(e['animation'],e['index']) for e in events]==[(30500,59),(30500,60),(30510,55),(30510,56),(32500,79),(32500,80),(32510,42),(32510,43)]
assert all(struct.unpack_from('<i',bytes.fromhex(e['hex']),8)[0] in (6098,6099) for e in events)
for copies,enabled in itertools.product((0,1,3),(0,1)):
    c=Dispatch()
    for _ in range(copies):c.insert(root)
    c.qualify();c.update(0)
    loader=NativeTae(c,taeraw,track['sha256']);assert loader.id==2271
    for event in events:
        ctx=OBJ+0xd100;c.u.mem_write(ctx,bytes(0x40));found=0
        while c.invoke(0x27d0400,[loader.animations[event['animation']],ctx]):
            if struct.unpack('<I',c.u.mem_read(ctx,4))[0]!=2:continue
            ptr=struct.unpack('<Q',c.u.mem_read(ctx+8,8))[0]
            if bytes(c.u.mem_read(ptr,32))!=bytes.fromhex(event['hex']):continue
            c.q(OBJ+0x8018,OBJ+0x6000);c.u.mem_write(ctx+0x18,bytes([enabled]))
            c.requests.clear();c.invoke(0x40cd80,[OBJ+0x8000,ctx])
            expected=bool(copies and enabled)
            assert len(c.requests)==expected,(copies,enabled,event,c.requests)
            if expected:assert c.requests[0]['behavior']==600000000+struct.unpack_from('<i',bytes.fromhex(event['hex']),8)[0]-6000 and c.requests[0]['instant']
            record('dispatch',c,copies=copies,enabled=bool(enabled),animation=event['animation'],requests=c.requests[:])
            found+=1
        assert found==1

# These are independent entry-point checks, not a complete child/scene spawn.
for id,fps in itertools.product((30901145,30901146,30901147,30901148),(30,60,120)):
    c=Emitter(id);slot=OBJ+0x4000
    c.u.mem_write(slot+0x329,b'\1');c.u.mem_write(slot+0x334,struct.pack('<I',id));c.u.mem_write(slot+0x494,b'\1')
    for frame in range(fps):c.frame=frame;c.invoke(0x343280,[slot],{UC_X86_REG_XMM1:1/fps})
    count=x.x['tables']['Bullet'][str(id)]['numShoot']
    assert c.shots==[0]*count
    record('emitter',c,bullet=id,fps=fps,shotFrames=c.shots)
for id,next_id in ((30901145,30901146),(30901146,-1),(30901147,30901148),(30901148,-1)):
    c=Emitter(id);actual=c.invoke(0x362eb0,[OBJ+0xd000,id])&0xffffffff
    assert actual==next_id&0xffffffff
    record('chain',c,bullet=id,next=next_id)

for id,fps in itertools.product((30901146,30901148),(30,60,120)):
    c=Lifetime(x);global_pointer(c,0x3c0ae30,OBJ+0xc000)
    instance,param,stages,vt=(OBJ+i for i in (0x8000,0x9000,0xa000,0xb000))
    c.u.mem_write(stages,struct.pack('<5i',1,2,3,4,4));c.q(instance+0x88,stages)
    c.u.mem_write(instance+0x90,struct.pack('<ii',1,2));c.q(instance+0x5c0,vt);c.q(instance+0x5f0,vt)
    for offset,callback in ((0x10,0x200),(0x18,0x208),(0x20,0x210)):c.q(vt+offset,STOP+callback)
    c.q(instance+0x5c8,param);c.u.mem_write(param,bullets[id]);c.u.mem_write(instance+0x580,b'\x21')
    c.u.mem_write(instance+0x600,struct.pack('<i',-1));c.invoke(0x350da0,[instance])
    expected=x.x['tables']['Bullet'][str(id)]['life']
    initial=struct.unpack('<2f',c.u.mem_read(instance+0x2d4,8))
    assert initial==(expected,expected)
    # Frozen simulation dt only; this does not imply that game menus pause.
    for _ in range(60):c.invoke(0x34f130,[instance],{UC_X86_REG_XMM1:0})
    assert struct.unpack('<2f',c.u.mem_read(instance+0x2d4,8))==initial
    for tick in range(math.ceil(expected*fps)+4):
        c.invoke(0x34f130,[instance],{UC_X86_REG_XMM1:1/fps})
        stage=struct.unpack('<i',c.u.mem_read(instance+0x90,4))[0]
        if stage>=3:break
    assert stage==3 and abs((tick+1)/fps-expected)<=2/fps,(id,fps,tick,stage)
    record('lifetime',c,bullet=id,fps=fps,initial=initial,zeroDtUpdates=60,expiryFrame=tick+1)

class AttackSetup(Chain):
 def __init__(self):super().__init__(x);self.attacks=[]
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if pc==0x34a890:
   radius=struct.unpack('<f',(u.reg_read(UC_X86_REG_XMM2)&0xffffffff).to_bytes(4,'little'))[0]
   self.attacks.append(dict(id=u.reg_read(UC_X86_REG_RDX)&0xffffffff,radius=radius));ret()
  elif pc in(0x34ad90,0x34b130,0x34dc70):ret()
  else:super().hook(u,address,size,user)
for id in (30901145,30901146,30901147,30901148):
 c=AttackSetup();param=OBJ+0x9000;c.u.mem_write(param,bullets[id]);c.q(OBJ+0x4008,param)
 row=x.x['tables']['Bullet'][str(id)];expected=.5 if id in(30901145,30901147) else 3
 assert row['hitRadius']==row['hitRadiusMax']==expected
 for fraction in(-.5,0,.5,1,2):
  c.invoke(0x363600,[OBJ+0x4008],{UC_X86_REG_XMM1:fraction})
  radius=struct.unpack('<f',(c.u.reg_read(UC_X86_REG_XMM0)&0xffffffff).to_bytes(4,'little'))[0]
  assert radius==expected
  record('radius',c,bullet=id,fraction=fraction,radius=radius)
 c.invoke(0x362c10,[OBJ+0x4000,OBJ+0x8000])
 assert c.attacks==[dict(id=row['atkId_Bullet'],radius=expected)]
 c.stubs.add('34A890 attack-instance creation recorder; 34AD90/34B130 visual sinks and 34DC70 explicit false mode predicate')
 record('attackSetup',c,bullet=id,requests=c.attacks)

fields=('life','atkId_Bullet','HitBulletID','numShoot','launchConditionType','hitRadius','hitRadiusMax',
        'dmgHitRecordLifeTime','isUseSharedHitList','isEndlessHit','intervalCreateBulletId')
output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),
    assetHashes={**{k:sha(v) for k,v in raws.items()},'weapon':sha(weaponraw),'tae':sha(taeraw)},
    effects=[root],root=root,state=2036,events=events,
    bullets={str(id):{k:x.x['tables']['Bullet'][str(id)][k] for k in fields} for id in (30901145,30901146,30901147,30901148)},
    attack={k:x.x['tables']['AtkParam_Pc']['600000089'][k] for k in ('atkPhysCorrection','atkMagCorrection','atkFireCorrection','atkThunCorrection','atkDarkCorrection','atkType','spAttribute','selfTarget','friendlyTarget','opposeTarget')},
    checks=checks,stubs=sorted(stubs|{'active phase, stage sequence and no-early-termination state virtuals supplied for lifetime checks',
        'standalone emitter entry points; complete hit-child creation, scene placement, collision, attack-instance reuse and damage calculation not executed'}),
    native=dict(animation='27D0F10 / 27D0400 → 40CD80 → 668B30',emitter='343280 → 347700 → 347250',
                childParameter='362EB0',radius='363600',attackSetup='362C10 → 34A890',lifetime='350DA0 → 34F130 → 355270'),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(map(len,checks.values())),'native Guardian halberd checks',{k:len(v) for k,v in checks.items()},flush=True)

