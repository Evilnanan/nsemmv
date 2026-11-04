"""Trace Guardian ultimate protection, recipient scope and replenishment.

Native event dispatch, emission timers, relation filters, effect lifetime,
damage consumption and defense getters execute on pinned assets. Collision
arrivals and the duration of the source animation are explicit fixtures.
"""
import argparse
import itertools
import json
import math
import struct
from pathlib import Path
from unicorn.x86_const import *
from native_effect_runtime import BASE, OBJ, Inputs, sha
from native_attack_runtime import Type1Attack
from effect_behavior_graph import BehaviorGraph

p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','assets','script','animations','behavior','output'):p.add_argument(name,type=Path)
a=p.parse_args();inputs=Inputs(a.exe,a.extracted)
assets=json.loads(a.assets.read_text());tae=json.loads(a.animations.read_text());graph=BehaviorGraph(a.behavior)
assert assets['hashes']['regulation.bin']==inputs.x['hashes']['regulation.bin']
assert tae['bundles'][0]['sha256']=='1410035ad79edb410fa41420ec259fcb4a1037d748c9c4a3b6ae8d1366c76d0f'
script=a.script.read_bytes();assert sha(script)=='786f8a7bc89452d9531e2299b224c8945701c422437eca9aacbeb10a57a17f4d'
source=script.decode('utf-8-sig').replace('\r\n','\n')
functions=[]
for name in ('DragoonJumpLand_onUpdate','DragoonJumpLandLoop_onUpdate'):
    start=source.index('function '+name+'()');functions.append(source[start:source.index('\nfunction ',start+1)])
assert 'ExecEventAllBody("W_DragoonJumpLandLoop")' in functions[0]
assert 'env(GetUltimateChargePercent) > 0' in functions[0]
assert 'env(ActionDurationAlternate, ACTION_ARM_R2) <= 0 and env(ActionDuration, ACTION_ARM_ULTRA) <= 0 or env(GetUltimateChargePercent) <= 0' in functions[1]
behavior_raw=a.extracted.with_suffix('.BehaviorParam_PC.param').read_bytes()
bullet_raw=a.extracted.with_suffix('.Bullet.param').read_bytes()
weapon_raw=a.assets.with_suffix('.EquipParamWeapon.param').read_bytes()
behaviors=Inputs.table(behavior_raw,0x30);bullets=Inputs.table(bullet_raw,0x100);weapons=Inputs.table(weapon_raw,0x298)
root=7011400;leaves=[7011401,7011402];bullet_ids=[30901189,30901190];rows=inputs.spells
assert rows[str(root)]['stateInfo']==2082 and rows[str(root)]['spCategory']==20
assert rows['7011401']['spCategory']==201 and rows['7011401']['categoryPriority']==200
assert rows['7011401']['deleteCriteriaDamage']==1 and inputs.rows[7011401][0x327]==1
assert rows['7011402']['spCategory']==20 and rows['7011402']['deleteCriteriaDamage']==0
assert struct.unpack('<I',inputs.pe.get_data(0x504df8,4))[0]==0x504de3
paths=[graph.state(n) for n in ('DragoonJumpLand','DragoonJumpLandLoop','DragoonJumpLandEnd')]
assert [p['animation'] for p in paths]==['a901_610010','a901_610011','a901_610012']
events=[dict(tae=t['ID'],animation=an['ID'],**e) for b in tae['bundles'] for t in b['taes']
        for an in t['animations'] for e in an['events']
        if e['Type']==2 and struct.unpack_from('<H',bytes.fromhex(e['hex']),14)[0]==2082]
assert [(e['tae'],e['animation'],e['index']) for e in events]==[(2901,610010,43),(2901,610010,44),(2901,610011,23),(2901,610011,24)]
for e in events:assert bytes.fromhex(e['hex'])[13]==1 and e['StartTime']==0 and e['EndTime']==100
assets_used=[]
for behavior,id,leaf,rate,duration in zip((700000809,700000810),bullet_ids,leaves,(.1,.8),(60,30)):
    b=inputs.x['tables']['BehaviorParam_PC'][str(behavior)]
    bullet=inputs.x['tables']['Bullet'][str(id)];attack=inputs.x['tables']['AtkParam_Pc'][str(bullet['atkId_Bullet'])]
    assert b['refType']==1 and b['refId']==id and bullet['spEffectId0']==leaf
    assert bullet['hitRadius']==bullet['hitRadiusMax']==15 and bullet['numShoot']==1
    assert math.isclose(bullet['shootInterval'],.3,rel_tol=1e-6) and math.isclose(bullet['life'],.3,rel_tol=1e-6)
    assert bullet['HitBulletID']==bullet['intervalCreateBulletId']==-1 and bullet['spEffectIDForShooter']==0
    assert [attack[k] for k in ('selfTarget','friendlyTarget','opposeTarget','disableHitSpEffect')]==[1,1,0,0]
    r=rows[str(leaf)];assert r['effectEndurance']==duration
    assert all(math.isclose(r[f+'DamageCutRate'],rate,rel_tol=1e-6) for f in ('neutral','slash','blow','thrust','magic','fire','thunder','dark'))
    assert [r[k] for k in ('effectTargetSelfTarget','effectTargetFriendlyTarget','effectTargetOpposeTarget')]==[1,1,0]
    assets_used.append(dict(behavior=behavior,bullet=id,leaf=leaf,radius=15,interval=bullet['shootInterval'],duration=duration,
                            attack={k:attack[k] for k in ('selfTarget','friendlyTarget','opposeTarget','disableHitSpEffect')}))

class Protection(Type1Attack):
    def __init__(self):
        super().__init__(inputs,behaviors,weapons,{700000809,700000810});self.emissions=[];self.frame=0;self.bullet=0
    def hook(self,u,address,size,user):
        pc=address-BASE
        def ret(value=0):
            u.reg_write(UC_X86_REG_RAX,value);sp=u.reg_read(UC_X86_REG_RSP)
            u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
        if pc==0x3975d0:
            self.stubs.add('3975D0 Behavior request recorder after native state/active-mode processing')
            payload=bytes(u.mem_read(u.reg_read(UC_X86_REG_R9),18))
            self.requests.append(dict(behavior=u.reg_read(UC_X86_REG_RDX),active=bool(payload[16]),instant=bool(payload[17])));ret(1)
        elif pc==0x27d0640:self.stubs.add('27D0640 empty animation-reference fixture');ret()
        elif pc==0xe87800:
            self.stubs.add('E87800 actual Bullet lookup');id=u.reg_read(UC_X86_REG_RDX)&0xffffffff;assert id in bullet_ids
            u.mem_write(OBJ+0xe900,bullets[id]);ptr=u.reg_read(UC_X86_REG_RCX)
            u.mem_write(ptr,struct.pack('<QI',OBJ+0xe900,id));ret(ptr)
        elif pc==0x347700:
            self.stubs.add('347700 successful emission recorder; recipient collision arrivals delivered explicitly next frame')
            self.emissions.append(dict(frame=self.frame,bullet=self.bullet));ret(1)
        else:super().hook(u,address,size,user)
    def event(self,e,active):
        self.q(OBJ+0xd018,OBJ+0x6000);self.q(OBJ+0xd108,OBJ+0xd200);self.q(OBJ+0xd120,OBJ+0xd300)
        self.u.mem_write(OBJ+0xd100,struct.pack('<I',2));self.u.mem_write(OBJ+0xd118,bytes([active]))
        self.u.mem_write(OBJ+0xd11a,struct.pack('<H',0x27));self.u.mem_write(OBJ+0xd200,bytes.fromhex(e['hex']))
        self.invoke(0x414820,[OBJ+0xd000,OBJ+0xd100])
    def defense(self):
        self.u.mem_write(OBJ+0x800,bytes(0x200))
        self.invoke(0x503800,[OBJ,OBJ+0x500,OBJ+0x520,OBJ+0x540,OBJ+0x800])
        return list(struct.unpack('<5f',self.u.mem_read(OBJ+0x500,20)))
    def hurt(self,damage,excluded=0):self.invoke(0x504d30,[OBJ,0,0,0,excluded],{UC_X86_REG_XMM1:damage})
    def recipient(self,leaf,target_type,same=False):
        self.u.mem_write(OBJ+0x6074,b'\1');self.u.mem_write(OBJ+0xb074,bytes([target_type]))
        self.u.mem_write(OBJ+0xc000,inputs.rows[leaf]);self.q(OBJ+0xb800,OBJ+0xc000)
        return bool(self.invoke(0x52cc60,[OBJ+0x6000,OBJ+0x6000 if same else OBJ+0xb000,OBJ+0xb800])&255)

checks=dict(dispatch=[],target=[],numeric=[],damage=[],refresh=[],lifetime=[],replenishment=[]);stubs=set()
for event,copies,active in itertools.product(events,(0,1,2,3),(0,1)):
    c=Protection()
    for _ in range(copies):c.insert(root)
    c.qualify();c.update(0);c.event(event,active)
    assert len(c.requests)==bool(copies)
    if c.requests:
        judge=struct.unpack_from('<i',bytes.fromhex(event['hex']),8)[0]
        assert c.requests[0]==dict(behavior=700000000+judge-7000,active=bool(active),instant=False)
    checks['dispatch'].append(dict(animation=event['animation'],event=event['index'],copies=copies,active=active,requests=c.requests));stubs.update(c.stubs)
for leaf,(relation,typ,same) in itertools.product(leaves+[7033101],(('self',1,True),('friendly',2,False),('opposing',6,False),('neutral',0,False))):
    c=Protection();allowed=c.recipient(leaf,typ,same)
    assert allowed==(relation in ('self','friendly') if leaf in leaves else relation in ('self','opposing')),(leaf,relation,typ,same,allowed)
    checks['target'].append(dict(leaf=leaf,relation=relation,sourceType=1,targetType=typ,same=same,allowed=allowed));stubs.update(c.stubs)
for active,copies in itertools.product(([7011401],[7011402],leaves),(0,1,2,3,6)):
    c=Protection()
    for _ in range(copies):
        for leaf in active:c.insert(leaf)
    c.qualify();c.update(0);rates=c.defense();expected=math.prod(.1 if id==7011401 else .8 for id in active) if copies else 1
    assert all(math.isclose(v,expected,rel_tol=1e-6) for v in rates)
    assert len(c.nodes())==(len(active) if copies else 0)
    checks['numeric'].append(dict(active=active,copies=copies,rates=rates));stubs.update(c.stubs)
for active,damage,excluded in itertools.product(([7011401],[7011402],leaves),(-1,0,.01,1,100),(0,1)):
    c=Protection()
    for leaf in active:c.insert(leaf)
    c.qualify();c.update(0);before=c.defense();c.hurt(damage,excluded);immediate=c.defense()
    assert immediate==before
    for _ in range(3):c.qualify();c.update(1/60)
    remaining=[n['id'] for n in c.nodes()]
    assert remaining==[id for id in active if id!=7011401 or damage<=0]
    expected=math.prod(.1 if id==7011401 else .8 for id in remaining)
    assert all(math.isclose(v,expected,rel_tol=1e-6) for v in c.defense())
    checks['damage'].append(dict(active=active,damage=damage,excluded=excluded,before=before,immediate=immediate,remaining=remaining,after=c.defense()));stubs.update(c.stubs)
for leaf,elapsed,copies in itertools.product(leaves,(0,1,15,29),(1,2,3)):
    c=Protection();c.insert(leaf);c.qualify();c.update(0);c.qualify();c.update(elapsed)
    for _ in range(copies):c.insert(leaf)
    c.qualify();c.update(0)
    assert len(c.nodes())==1 and c.nodes()[0]['lifetime']==rows[str(leaf)]['effectEndurance']
    checks['refresh'].append(dict(leaf=leaf,elapsed=elapsed,copies=copies,lifetime=c.nodes()[0]['lifetime']));stubs.update(c.stubs)
for fps,leaf in itertools.product((30,60,120),leaves):
    c=Protection();c.insert(leaf);c.qualify();c.update(0);duration=rows[str(leaf)]['effectEndurance']
    for frame in range(1,int((duration+1)*fps)):
        c.qualify();c.update(1/fps)
        if not c.nodes():break
    assert abs(frame/fps-duration)<=3.01/fps and c.defense()==[1]*5
    checks['lifetime'].append(dict(fps=fps,leaf=leaf,expiryFrame=frame));stubs.update(c.stubs)
for fps,arrival_copies in itertools.product((30,60,120),(1,3)):
    c=Protection();pending=[];changes=[];previous=1
    for index,id in enumerate(bullet_ids):
        slot=OBJ+0x4000+index*0x1000
        c.u.mem_write(slot+0x329,b'\1');c.u.mem_write(slot+0x334,struct.pack('<I',id));c.u.mem_write(slot+0x494,b'\0')
    for frame in range(4*fps):
        for id in pending:
            for _ in range(arrival_copies):c.insert(id)
        pending=[];c.qualify()
        if frame in (fps,round(2.9*fps)):c.hurt(1)
        c.update(1/fps);rate=c.defense()[0]
        if not math.isclose(rate,previous,rel_tol=1e-6):changes.append(dict(frame=frame,rate=rate));previous=rate
        if frame<3*fps:
            for index,id in enumerate(bullet_ids):
                before=len(c.emissions);c.frame=frame;c.bullet=id
                c.invoke(0x343280,[OBJ+0x4000+index*0x1000],{UC_X86_REG_XMM1:1/fps})
                if len(c.emissions)>before:pending.append(leaves[index])
    for id in bullet_ids:
        emitted=[e['frame'] for e in c.emissions if e['bullet']==id]
        assert len(emitted)==10
        assert all(abs((b-a)/fps-.3)<=1/fps+1e-6 for a,b in zip(emitted,emitted[1:]))
    assert [round(x['rate'],2) for x in changes]==[.08,.8,.08,.8]
    assert [n['id'] for n in c.nodes()]==[7011402]
    checks['replenishment'].append(dict(fps=fps,arrivalCopies=arrival_copies,sourceStopsAt=3,hits=[fps,round(2.9*fps)],emissions=c.emissions,changes=changes));stubs.update(c.stubs)
output=dict(schema=1,exeSha256=sha(inputs.raw),regulationSha256=inputs.x['hashes']['regulation.bin'],paramSha256=sha(inputs.param),
            behaviorParamSha256=sha(behavior_raw),bulletParamSha256=sha(bullet_raw),weaponParamSha256=sha(weapon_raw),scriptSha256=sha(script),
            scriptFunctionsSha256=[sha(f.encode()) for f in functions],animationBundleSha256=tae['bundles'][0]['sha256'],
            behaviorSha256=graph.metadata['hkxSha256'],paths=paths,events=events,assets=assets_used,root=root,leaves=leaves,checks=checks,
            native=dict(dispatch='414820',type2='40CD80',behavior='668B30',emitter='343280',target='52CC60',relation='3D1B30',
                        insert='50D060',qualify='5057D0',update='50ACD0',hurt='504D30',defense='503800'),
            stubs=sorted(stubs|{'actual static relation matrix; explicit actor team-type/identity inputs',
                               'source animation stops at a fixture time; no full HKS/behavior scheduler or collision geometry',
                               'incoming positive/zero damage is explicit; no full final-damage, network or save-reload simulation'}),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(map(len,checks.values())),'native Guardian ultimate cases')
