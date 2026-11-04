"""Execute Raider finisher dispatch and its permanent ten-step growth chain.

Collision arrival is explicit. Thereafter the original expiry grant, actor
delivery, growth selection, eligibility, insertion and numeric getters execute
without replacing the growth algorithm. Actor identity and notifications are
fixtures; no complete gameplay, collision, save reload or network is simulated.
"""
import argparse
import itertools
import json
import math
import struct
from pathlib import Path
from unicorn.x86_const import *
from native_effect_runtime import BASE, OBJ, STOP, Chain, Inputs, sha
from native_attack_runtime import Type1Attack
from effect_behavior_graph import BehaviorGraph

p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','assets','animations','behavior','output'):p.add_argument(name,type=Path)
a=p.parse_args();inputs=Inputs(a.exe,a.extracted)
assets=json.loads(a.assets.read_text());tae=json.loads(a.animations.read_text());graph=BehaviorGraph(a.behavior)
assert assets['hashes']['regulation.bin']==inputs.x['hashes']['regulation.bin']
assert tae['bundles'][0]['sha256']=='1410035ad79edb410fa41420ec259fcb4a1037d748c9c4a3b6ae8d1366c76d0f'
behavior_raw=a.extracted.with_suffix('.BehaviorParam_PC.param').read_bytes()
attack_raw=a.extracted.with_suffix('.AtkParam_Pc.param').read_bytes()
weapon_raw=a.assets.with_suffix('.EquipParamWeapon.param').read_bytes()
behaviors=Inputs.table(behavior_raw,0x30);attacks=Inputs.table(attack_raw,0x1d0);weapons=Inputs.table(weapon_raw,0x298)
root,seed=7031400,7031401;ladder=list(range(7031501,7031511));rows=inputs.spells
assert rows[str(root)]['stateInfo']==2080 and rows[str(root)]['spCategory']==20
assert rows[str(seed)]['spCategory']==10 and rows[str(seed)]['replaceSpEffectId']==ladder[0]
assert math.isclose(rows[str(seed)]['effectEndurance'],.1,rel_tol=1e-6)
assert [int(id) for id,r in rows.items() if r['spCategory']==204 and r['categoryPriority']==2]==ladder
for n,id in enumerate(ladder,1):
    r=rows[str(id)]
    assert r['effectEndurance']==-1 and r['saveCategory']==9 and r['stateInfo']==0
    assert all(math.isclose(r[field+'AttackRate'],1.03**n,rel_tol=1e-6) for field in ('physics','magic','fire','thunder','dark'))
assert ladder[-1]+1 not in inputs.rows
events=[dict(tae=t['ID'],animation=an['ID'],**e) for b in tae['bundles'] for t in b['taes']
        for an in t['animations'] for e in an['events']
        if e['Type']==1 and struct.unpack_from('<H',bytes.fromhex(e['hex']),14)[0]==2080]
assert len(events)==1 and events[0]['tae']==2904 and events[0]['animation']==541020
event=events[0];payload=bytes.fromhex(event['hex'])
assert struct.unpack_from('<i',payload,8)[0]==6251 and payload[13]==3
assert math.isclose(event['StartTime'],56/30,abs_tol=1e-6) and math.isclose(event['EndTime'],61/30,abs_tol=1e-6)
path=graph.state('SmashAttack2');assert path['animation']=='a904_541020'
b=inputs.x['tables']['BehaviorParam_PC']['600000251'];attack=inputs.x['tables']['AtkParam_Pc']['600000251']
assert b['refType']==0 and b['refId']==600000251 and struct.unpack_from('<i',behaviors[600000251],12)[0]==600000251
assert attack['spEffectId1']==seed and struct.unpack_from('<i',attacks[600000251],28)[0]==seed
assert [attack[k] for k in ('selfTarget','friendlyTarget','opposeTarget','disableHitSpEffect')]==[1,0,0,0]
assert rows[str(seed)]['effectTargetSelfTarget']==rows[str(seed)]['effectTargetSelf']==1

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
    def settle(self,fps):
        for frame in range(1,fps+1):
            self.qualify();self.update(1/fps)
            if not any(n['id']==seed for n in self.nodes()):
                self.qualify();self.update(1/fps)
                return frame
        raise AssertionError('seed failed to expire')

checks=dict(dispatch=[],growth=[],numeric=[],repeat=[],stable=[]);stubs=set()
for copies,active in itertools.product((0,1,2,3),(0,1)):
    c=Type1Attack(inputs,behaviors,weapons,{600000251})
    for _ in range(copies):c.insert(root)
    c.qualify();c.update(0);c.event(event,active)
    assert len(c.requests)==bool(copies)
    if c.requests:assert c.requests[0]['behavior']==600000251 and c.requests[0]['slot']==2
    checks['dispatch'].append(dict(copies=copies,active=active,requests=c.requests));stubs.update(c.stubs)
for fps,copies,mode in itertools.product((30,60,120),(1,2,3),(0,7)):
    c=Growth(copies,mode);steps=[]
    for n in range(1,15):
        before=len(c.resolved);c.arrive();frame=c.settle(fps);level=min(n,10)
        nodes=[node for node in c.nodes() if node['id']!=root]
        assert len(nodes)==1 and nodes[0]['id']==ladder[level-1] and nodes[0]['lifetime']==-1
        rates=c.attack();assert all(math.isclose(v,1.03**level,rel_tol=1e-6) for v in rates)
        assert c.resolved[before:]==[seed]+([ladder[n-1]] if n<=10 else [])
        assert abs(frame/fps-.1)<=3.01/fps
        steps.append(dict(trigger=n,level=level,expiryFrame=frame,resolved=c.resolved[before:],rates=rates))
    assert c.notifications==10
    checks['growth'].append(dict(fps=fps,copies=copies,mode=mode,steps=steps,notifications=c.notifications));stubs.update(c.stubs)
for level,kind in itertools.product(range(1,11),range(11)):
    c=Growth();c.arrive(ladder[level-1]);c.qualify();c.update(0);rates=c.attack(kind)
    assert all(math.isclose(v,1 if kind==5 else 1.03**level,rel_tol=1e-6) for v in rates)
    checks['numeric'].append(dict(level=level,kind=kind,rates=rates));stubs.update(c.stubs)
for count in (1,2,3,6,12):
    c=Growth(1)
    for _ in range(count):c.arrive()
    c.settle(60);level=min(count,10)
    assert [n['id'] for n in c.nodes() if n['id']!=root]==[ladder[level-1]]
    checks['repeat'].append(dict(arrivals=count,level=level,rates=c.attack()));stubs.update(c.stubs)
for seconds in (1,60,3600):
    c=Growth();c.arrive(ladder[-1]);c.qualify();c.update(0);before=c.attack()
    c.qualify();c.update(seconds);c.qualify();c.update(1/60)
    assert c.attack()==before and c.nodes()[0]['lifetime']==-1
    checks['stable'].append(dict(seconds=seconds,rates=c.attack(),nodes=c.nodes()));stubs.update(c.stubs)
output=dict(schema=1,exeSha256=sha(inputs.raw),regulationSha256=inputs.x['hashes']['regulation.bin'],paramSha256=sha(inputs.param),
            behaviorParamSha256=sha(behavior_raw),attackParamSha256=sha(attack_raw),weaponParamSha256=sha(weapon_raw),
            animationBundleSha256=tae['bundles'][0]['sha256'],behaviorSha256=graph.metadata['hkxSha256'],path=path,event=event,
            root=root,seed=seed,ladder=ladder,attack={k:attack[k] for k in ('selfTarget','friendlyTarget','opposeTarget','spEffectId1','disableHitSpEffect')},checks=checks,
            native=dict(dispatch='414820',type1='40CA20',behavior='668B30',grant='3C7FD0',actorGrant='3C80A0',growth='5077A0',
                        arrival='3DB410',eligibility='50C6C0',insert='50D060',qualify='5057D0',update='50ACD0',attack='502830'),
            stubs=sorted(stubs|{'self-target collision arrival is explicit; no complete attack instance, actual collision geometry, interrupted animation, save reload or multiplayer'}),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(map(len,checks.values())),'native Raider growth cases')
