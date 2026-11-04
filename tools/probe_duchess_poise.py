"""Trace Duchess's skill poise vulnerability, emission and recipient consumer.

Pinned event dispatch, emitter timer, effect lifecycle and poise subtraction run
natively with actor, collision-arrival, base-poise and notification fixtures.
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
weapon_raw=a.assets.with_suffix('.EquipParamWeapon.param').read_bytes()
bullet_raw=a.extracted.with_suffix('.Bullet.param').read_bytes()
behaviors=Inputs.table(behavior_raw,0x30);weapons=Inputs.table(weapon_raw,0x298);bullets=Inputs.table(bullet_raw,0x100)
root,leaf=7033100,7033101
assert inputs.spells[str(root)]['stateInfo']==2091
r=inputs.spells[str(leaf)];assert r['effectEndurance']==6 and r['spCategory']==20
assert math.isclose(r['saReceiveDamageRate'],1.3,rel_tol=1e-6)
assert struct.unpack_from('<f',inputs.rows[leaf],0x25c)[0]==r['saReceiveDamageRate']
assert inputs.rows[leaf][0x160]&64==0 and inputs.rows[leaf][0x351]==0
b=inputs.x['tables']['BehaviorParam_PC']['600000149'];bullet=inputs.x['tables']['Bullet']['30903001']
attack=inputs.x['tables']['AtkParam_Pc']['600000150']
assert b['refType']==1 and b['refId']==30903001
assert bullet['spEffectId0']==leaf and bullet['atkId_Bullet']==600000150
assert bullet['hitRadius']==bullet['hitRadiusMax']==15 and bullet['numShoot']==1
assert math.isclose(bullet['life'],.2,rel_tol=1e-6)
assert all(bullet['spEffectId'+str(i)]==0 for i in range(1,5))
assert bullet['HitBulletID']==bullet['intervalCreateBulletId']==-1 and bullet['spEffectIDForShooter']==0
assert [attack[k] for k in ('selfTarget','friendlyTarget','opposeTarget','disableHitSpEffect')]==[0,0,1,0]
assert r['effectTargetOpposeTarget']==1 and r['effectTargetFriendlyTarget']==0
paths=[]
for selector,expected in ((17189,['a903_539000','a903_539005']),(17190,['a903_539100','a903_539105'])):
    assert graph.selector_binding(selector)['name']=='IsRelic_Dejavu'
    clips=[]
    for g in graph.children(selector):
        children=graph.children(g);assert len(children)==1
        clips.append(graph.string(graph.reference(children[0],'animationName')))
    assert clips==expected;paths.append(dict(selector=selector,clips=clips))
events=[dict(tae=t['ID'],animation=an['ID'],**e) for b in tae['bundles'] for t in b['taes'] if t['ID']==2903
        for an in t['animations'] for e in an['events']
        if e['Type']==2 and struct.unpack_from('<H',bytes.fromhex(e['hex']),14)[0]==2091]
assert [e['animation'] for e in events]==[539000,539005,539100,539105]
for e in events:assert struct.unpack_from('<i',bytes.fromhex(e['hex']),8)[0]==6149
MODULE=OBJ+0xc000
class Weakening(Type1Attack):
    def __init__(self):
        super().__init__(inputs,behaviors,weapons,{600000149});self.emissions=[];self.frame=0;self.poiseChanges=[]
        self.q(MODULE,OBJ+0xc200);self.q(MODULE+8,OBJ+0x6000)
        self.q(OBJ+0xc210,STOP+0x210);self.q(OBJ+0xc218,STOP+0x211)
        self.q(OBJ+0x9008,OBJ+0xc800);self.q(OBJ+0x63a0,STOP+0x200)
    def hook(self,u,address,size,user):
        pc=address-BASE
        def ret(value=0):
            u.reg_write(UC_X86_REG_RAX,value);sp=u.reg_read(UC_X86_REG_RSP)
            u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
        if pc==0x3975d0:
            self.stubs.add('3975D0 Behavior request recorder; native conditional event dispatch')
            payload=bytes(u.mem_read(u.reg_read(UC_X86_REG_R9),18))
            self.requests.append(dict(behavior=u.reg_read(UC_X86_REG_RDX),active=bool(payload[16]),instant=bool(payload[17])));ret(1)
        elif pc==0x27d0640:
            self.stubs.add('27D0640 empty animation-reference list');ret()
        elif pc==0xe87800:
            self.stubs.add('E87800 actual Bullet row lookup');id=u.reg_read(UC_X86_REG_RDX)&0xffffffff;assert id==30903001
            u.mem_write(OBJ+0xe900,bullets[id]);ptr=u.reg_read(UC_X86_REG_RCX)
            u.mem_write(ptr,struct.pack('<QI',OBJ+0xe900,id));ret(ptr)
        elif pc==0x347700:
            self.stubs.add('347700 successful projectile-emission recorder; collision arrivals are separate fixtures')
            self.emissions.append(self.frame);ret(1)
        elif address in (STOP+0x210,STOP+0x211):
            self.stubs.add('poise virtual +10 base 100; +18 recovery delay 5, explicit recipient fixtures')
            u.reg_write(UC_X86_REG_XMM0,int.from_bytes(struct.pack('<f',100 if address==STOP+0x210 else 5),'little'));ret()
        elif pc==0x48d4f0:
            self.stubs.add('48D4F0 poise-change notification sink after native subtraction')
            self.poiseChanges.append(struct.unpack('<f',u.reg_read(UC_X86_REG_XMM1).to_bytes(16,'little')[:4])[0]);ret()
        elif pc in (0x53b360,0x53b520):
            self.stubs.add(hex(pc)+' stagger reaction notification constructor/sink');ret()
        else:super().hook(u,address,size,user)
    def event(self,e,active):
        self.q(OBJ+0xd018,OBJ+0x6000);self.q(OBJ+0xd108,OBJ+0xd200);self.q(OBJ+0xd120,OBJ+0xd300)
        self.u.mem_write(OBJ+0xd100,struct.pack('<I',2));self.u.mem_write(OBJ+0xd118,bytes([active]))
        self.u.mem_write(OBJ+0xd11a,struct.pack('<H',0x27));self.u.mem_write(OBJ+0xd200,bytes.fromhex(e['hex']))
        self.invoke(0x414820,[OBJ+0xd000,OBJ+0xd100])
    def rate(self):
        self.invoke(0x508170,[OBJ,OBJ+0xd800]);return struct.unpack('<f',self.u.reg_read(UC_X86_REG_XMM0).to_bytes(16,'little')[:4])[0]
    def hit(self,amount,current=100):
        self.u.mem_write(MODULE+0x10,struct.pack('<f',current));self.u.mem_write(MODULE+0x20,b'\0');self.poiseChanges=[]
        self.invoke(0x48de50,[MODULE],{UC_X86_REG_XMM1:amount})
        return dict(remaining=struct.unpack('<f',self.u.mem_read(MODULE+0x10,4))[0],broken=bool(self.u.mem_read(MODULE+0x20,1)[0]),changed=self.poiseChanges[:])
checks=dict(dispatch=[],emission=[],consumer=[],refresh=[],lifetime=[]);stubs=set()
for e,copies,active in itertools.product(events,(0,1,2,3),(0,1)):
    c=Weakening()
    for _ in range(copies):c.insert(root)
    c.qualify();c.update(0);c.event(e,active)
    assert len(c.requests)==bool(copies and active),(e,copies,active,c.requests)
    if c.requests:assert c.requests[0]['behavior']==600000149
    checks['dispatch'].append(dict(animation=e['animation'],copies=copies,active=active,requests=c.requests));stubs.update(c.stubs)
for fps in (30,60,120):
    c=Weakening();slot=OBJ+0x4000
    c.u.mem_write(slot+0x329,b'\x01');c.u.mem_write(slot+0x334,struct.pack('<I',30903001));c.u.mem_write(slot+0x494,b'\x01')
    for frame in range(fps):c.frame=frame;c.invoke(0x343280,[slot],{UC_X86_REG_XMM1:1/fps})
    assert c.emissions==[0]
    checks['emission'].append(dict(fps=fps,emissions=c.emissions));stubs.update(c.stubs)
for copies,amount in itertools.product((0,1,2,3),(0,1,10,50,76,77,100)):
    c=Weakening()
    for _ in range(copies):c.insert(leaf)
    c.qualify();c.update(0);rate=c.rate();result=c.hit(amount)
    expected=1.3 if copies else 1
    assert math.isclose(rate,expected,rel_tol=1e-6)
    assert math.isclose(result['remaining'],100-amount*expected,abs_tol=1e-4),(copies,amount,result)
    assert result['broken']==(amount*expected>=100)
    assert len(c.nodes())==bool(copies)
    checks['consumer'].append(dict(copies=copies,input=amount,rate=rate,result=result));stubs.update(c.stubs)
for elapsed,count in itertools.product((0,1,3,5),(1,2,3)):
    c=Weakening();c.insert(leaf);c.qualify();c.update(0);c.qualify();c.update(elapsed)
    for _ in range(count):c.insert(leaf)
    c.qualify();c.update(0)
    assert len(c.nodes())==1 and c.nodes()[0]['lifetime']==6 and math.isclose(c.rate(),1.3,rel_tol=1e-6)
    checks['refresh'].append(dict(elapsed=elapsed,count=count,remaining=c.nodes()[0]['lifetime'],rate=c.rate()));stubs.update(c.stubs)
for fps in (30,60,120):
    c=Weakening();c.insert(leaf);c.qualify();c.update(0)
    for frame in range(1,8*fps):
        c.qualify();c.update(1/fps)
        if not c.nodes():break
    assert abs(frame/fps-6)<=3.01/fps and c.rate()==1
    checks['lifetime'].append(dict(fps=fps,expiryFrame=frame));stubs.update(c.stubs)
output=dict(schema=1,exeSha256=sha(inputs.raw),regulationSha256=inputs.x['hashes']['regulation.bin'],paramSha256=sha(inputs.param),
            behaviorParamSha256=sha(behavior_raw),bulletParamSha256=sha(bullet_raw),weaponParamSha256=sha(weapon_raw),
            animationBundleSha256=tae['bundles'][0]['sha256'],behaviorSha256=graph.metadata['hkxSha256'],paths=paths,events=events,
            root=root,leaf=leaf,bullet={k:bullet[k] for k in ('hitRadius','hitRadiusMax','life','numShoot','shootInterval','spEffectId0','atkId_Bullet')},
            checks=checks,native=dict(dispatch='414820/40CD80',state='508E20',behavior='668B30',emitter='343280',
                                     rate='508170/510880',filter='511350',consumer='48DE50',insert='50D060',qualify='5057D0',update='50ACD0'),
            stubs=sorted(stubs),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(map(len,checks.values())),'native Duchess poise cases')
