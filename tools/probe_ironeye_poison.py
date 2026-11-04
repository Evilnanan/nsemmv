"""Trace Ironeye skill poison, onset and the separate poisoned-target hit bonus.

Native conditional animation dispatch, accumulation, immunity, effect insertion,
HP packets and timers execute with explicit collision/actor/resistance fixtures.
No complete attack construction, spatial collision or network is simulated.
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
rows=inputs.spells
assert rows['7500200']['stateInfo']==2393
assert rows['7500201']['stateInfo']==2 and rows['7500201']['poizonAttackPower']==70
assert rows['7500201']['effectEndurance']==40 and math.isclose(rows['7500201']['motionInterval'],1.3,rel_tol=1e-6)
assert rows['7500201']['changeHpPoint']==10 and math.isclose(rows['7500201']['changeHpRate'],.1,rel_tol=1e-6)
assert rows['7500201']['cycleOccurrenceSpEffectId']==505
assert rows['7500202']['invocationConditionsStateChange1']==2
assert rows['7500202']['changeHpRate']==.25 and rows['7500202']['changeHpPoint']==250
assert rows['7500202']['spCategory']==0 and rows['7500201']['spCategory']==10004
assert rows['505']['changeHpRate']==rows['505']['changeHpPoint']==0
assert rows['9642']['disablePoison']==1
attack=inputs.x['tables']['AtkParam_Pc']['600000120']
assert inputs.x['tables']['BehaviorParam_PC']['600000120']['refType']==0
assert struct.unpack_from('<i',behaviors[600000120],12)[0]==600000120
assert struct.unpack_from('<3i',attacks[600000120],24)==(6902,7500201,7500202)
assert [attack[k] for k in ('selfTarget','friendlyTarget','opposeTarget','disableHitSpEffect')]==[0,0,1,0]
assert all(attack[k]==100 for k in ('spEffectAtkPowerCorrectRate_byDmg','spEffectAtkPowerCorrectRate_byPoint','spEffectAtkPowerCorrectRate_byRate'))
events=[dict(tae=t['ID'],animation=an['ID'],**e) for b in tae['bundles'] for t in b['taes'] if t['ID']==2902
        for an in t['animations'] if an['ID'] in (520000,520005,525000,525005)
        for e in an['events'] if e['Type']==1 and struct.unpack_from('<H',bytes.fromhex(e['hex']),14)[0]==2393]
assert len(events)==4
for e in events:
    raw=bytes.fromhex(e['hex']);assert struct.unpack_from('<i',raw,8)[0]==6120 and raw[13]==3
paths=[]
for state,blender,selector,expected in ((32495,41924,60811,['a902_525000','a902_525005']),
                                       (32496,41926,60814,['a902_520000','a902_520005'])):
    assert graph.reference(state,'generator')==blender
    children=graph.blender_children(blender);assert children[0]['generator']==selector
    binding=graph.selector_binding(selector);assert binding['name']=='HurtDaggerIndex'
    clips=[]
    for generator in graph.children(selector):
        arr=graph.children(generator);assert len(arr)==1
        clips.append(dict(generator=generator,clip=arr[0],animation=graph.string(graph.reference(arr[0],'animationName'))))
    assert [r['animation'] for r in clips]==expected
    paths.append(dict(state=state,name=graph.name(state),blender=blender,children=children,binding=binding,clips=clips))
assert graph.state('HurtDaggerAdditionalAttack')['animation']=='a902_520005'

class Poison(Chain):
    def __init__(self, maximum=500, immune=False):
        super().__init__(inputs)
        self.q(OBJ + 0x6190, OBJ)
        self.q(OBJ + 0x63a0, STOP + 0x200)  # owner virtual +1a0: no growth params
        self.q(OBJ + 0x6410, STOP + 0x201)  # owner virtual +210: no damage exclusion
        self.q(OBJ + 0x9008, OBJ + 0x6000)  # ailment controller owner
        self.q(OBJ + 0xe008, OBJ + 0x6000)  # HP data owner
        self.q(OBJ + 0x61b8, OBJ + 0xf000)
        self.q(OBJ + 0xf008, OBJ + 0xf400)
        # Queue/debug-singleton identities only. Original branch predicates run.
        for address, value in [(BASE + 0x42d85f + 7 + 0x37f4662, OBJ + 0xe800),
                               (BASE + 0x427bfa + 8 + 0x37e7736, OBJ + 0xf800)]:
            self.mapped(self.u, 0, address, 8, 0, None)
            self.q(address, value)
        for off in (0x9010, 0x902c):
            self.u.mem_write(OBJ + off, struct.pack('<i', maximum))
        if immune: self.insert(9642)
        self.qualify(); self.update(0)
        self.stubs.add('empty actor/HP/ailment objects; neutral death-protection flags and supplied starting resistance')

    def hook(self, u, address, size, user):
        pc = address - BASE
        def finish(value=0):
            u.reg_write(UC_X86_REG_RAX, value)
            sp = u.reg_read(UC_X86_REG_RSP)
            u.reg_write(UC_X86_REG_RIP, struct.unpack('<Q', u.mem_read(sp, 8))[0])
            u.reg_write(UC_X86_REG_RSP, sp + 8)
        if address in (STOP + 0x200, STOP + 0x201):
            self.stubs.add('owner virtual +1a0 no resistance-growth params; +210 no damage exclusion')
            finish()
        elif pc == 0x6ada30:
            self.stubs.add('6ADA30 ordinary resource-setter context')
            finish()
        elif pc == 0x3d4180:
            self.stubs.add('3D4180 player identity')
            finish(1)
        elif pc in (0x4e78a0, 0x4e78c0, 0xdf24d0):
            self.stubs.add(hex(pc) + ' network-message identity/transport only; no remote delivery')
            finish()
        else:
            super().hook(u, address, size, user)

    def apply_poison(self, scale=1):
        # Mirror 3DB410: insert first, then run status processing. A true return
        # removes that exact node immediately, without expiry replacement.
        index = self.insert(7500201)
        if index >= 0x80000000:return "existing"
        self.q(OBJ + 0x9800, self.lookup[7500201])
        self.u.mem_write(OBJ + 0x9900, struct.pack('<f', scale))
        self.u.mem_write(OBJ + 0x9938, struct.pack('<f', 1))
        rejected = bool(self.invoke(0x42d110, [OBJ + 0x9000, OBJ + 0x9800, OBJ + 0x9900]) & 255)
        if rejected: self.invoke(0x505280, [OBJ, index])
        return rejected

    def remaining(self):
        return struct.unpack('<i', self.u.mem_read(OBJ + 0x9010, 4))[0]

    def hp_packet(self, maximum):
        # No physical-owner invulnerability/remote state while aggregating. The
        # actual effect list and native poisonDamageRate multiplier remain live.
        self.q(OBJ + 0x10, 0)
        self.invoke(0x506ec0, [OBJ, maximum, OBJ + 0x800, OBJ + 0x808, OBJ + 0x820, 0])
        self.q(OBJ + 0x10, OBJ + 0x6000)
        return list(struct.unpack('<7i', self.u.mem_read(OBJ + 0x820, 28)))


checks=dict(dispatch=[],onset=[],damage=[],bonus=[],repeat=[],bonusTiming=[],lifetime=[]);stubs=set()
for e,copies,active in itertools.product(events,(0,1,2,3),(0,1)):
    c=Type1Attack(inputs,behaviors,weapons,{600000120})
    for _ in range(copies):c.insert(7500200)
    c.qualify();c.update(0);c.event(e,active)
    assert len(c.requests)==bool(copies)
    if c.requests:assert c.requests[0]['behavior']==600000120 and c.requests[0]['hand']==6
    checks['dispatch'].append(dict(animation=e['animation'],copies=copies,active=active,requests=c.requests));stubs.update(c.stubs)
for immune,resistance,scale in itertools.product((False,True),(1,69,70,71,140,500),(.5,1,1.5,2)):
    c=Poison(resistance,immune);rejected=c.apply_poison(scale);c.qualify();c.update(0)
    amount=int(70*scale);expected=immune or resistance>amount
    assert rejected==expected
    assert c.remaining()==(resistance if immune or not expected else resistance-amount)
    assert any(n['id']==7500201 for n in c.nodes())==(not rejected)
    checks['onset'].append(dict(immune=immune,resistance=resistance,scale=scale,baseAccumulation=amount,rejected=rejected,remaining=c.remaining()));stubs.update(c.stubs)
for maximum in (99,100,137,1000,10000,12345,100000):
    c=Poison(70);assert c.apply_poison() is False
    c.qualify();c.update(0);poison=c.hp_packet(maximum)[0]
    assert poison==-(int(maximum*.001)+10),(maximum,poison)
    c.qualify();c.update(1/60);c.insert(7500202);c.qualify();c.update(0)
    bonus=c.hp_packet(maximum)[0]
    assert bonus==-(int(maximum*.0025)+250),(maximum,bonus)
    c.qualify();c.update(1/60);assert c.hp_packet(maximum)[0]==0
    checks['damage'].append(dict(maximum=maximum,poison=poison,bonus=bonus));stubs.update(c.stubs)
for prior,count in itertools.product((0,834,3120,4002,7500201),(1,2,3)):
    c=Poison()
    if prior:c.insert(prior);c.qualify();c.update(1/60);c.qualify();c.update(1/60)
    for _ in range(count):c.insert(7500202)
    c.qualify();c.update(0);hp=c.hp_packet(10000)[0]
    assert hp==(-275 if prior else 0),(prior,count,hp,c.nodes())
    checks['bonus'].append(dict(prior=prior,count=count,damage=hp,nodes=c.nodes()));stubs.update(c.stubs)
for hits in ([0],[0,0,0],[0,1],[0,3],[0,6],[0,7],[0,8],[0,12],list(range(31))):
    c=Poison(70);c.apply_poison();c.qualify();c.update(1/60);c.qualify();c.update(1/60);damage=[]
    for frame in range(45):
        for _ in range(hits.count(frame)):c.insert(7500202)
        c.qualify();c.update(1/60);hp=c.hp_packet(10000)[0]
        if hp:damage.append(dict(frame=frame,damage=hp))
    expected=[0,8,16,24] if hits==list(range(31)) else ([0,hits[-1]] if len(hits)==2 and hits[-1]>=8 else [0])
    assert damage==[dict(frame=f,damage=-275) for f in expected]
    checks['bonusTiming'].append(dict(hits=hits,fps=60,damage=damage));stubs.update(c.stubs)
for fps in (30,120):
    c=Poison(70);c.apply_poison();c.qualify();c.update(1/fps);c.qualify();c.update(1/fps);damage=[]
    for frame in range(fps//2):
        c.insert(7500202);c.qualify();c.update(1/fps);hp=c.hp_packet(10000)[0]
        if hp:damage.append(dict(frame=frame,damage=hp))
    assert damage[0]['frame']==0 and all(r['damage']==-275 for r in damage)
    assert all(.1<=(b['frame']-a['frame'])/fps<=.1+3.01/fps for a,b in zip(damage,damage[1:]))
    checks['bonusTiming'].append(dict(hits=list(range(fps//2)),fps=fps,damage=damage));stubs.update(c.stubs)
for elapsed in (0,1,5,15,39):
    c=Poison(70);assert c.apply_poison() is False;c.qualify();c.update(0)
    c.qualify();c.update(elapsed);before=c.nodes()[0]['lifetime'];result=c.apply_poison()
    assert result=='existing' and c.nodes()[0]['lifetime']==before
    checks['repeat'].append(dict(elapsed=elapsed,result=result,remaining=before));stubs.update(c.stubs)
for fps in (30,60,120):
    c=Poison(70);c.apply_poison();c.qualify();c.update(0);ticks=[];grants=[]
    for frame in range(42*fps):
        hp=c.hp_packet(10000)[0]
        if hp:ticks.append(dict(frame=frame,damage=hp))
        if c.emitted:grants.append(dict(frame=frame,ids=c.emitted[:]))
        c.emitted.clear();c.qualify();c.update(1/fps)
        if not c.nodes():break
    assert abs((frame+1)/fps-40)<=3.01/fps
    assert len(ticks)==31 and all(t['damage']==-20 for t in ticks)
    assert all(abs((b['frame']-a['frame'])/fps-1.3)<=3.01/fps for a,b in zip(ticks,ticks[1:]))
    checks['lifetime'].append(dict(fps=fps,expiryFrame=frame+1,ticks=ticks,grants=grants));stubs.update(c.stubs)
output=dict(schema=1,exeSha256=sha(inputs.raw),regulationSha256=inputs.x['hashes']['regulation.bin'],paramSha256=sha(inputs.param),
            behaviorParamSha256=sha(behavior_raw),attackParamSha256=sha(attack_raw),weaponParamSha256=sha(weapon_raw),
            animationBundleSha256=tae['bundles'][0]['sha256'],behaviorSha256=graph.metadata['hkxSha256'],paths=paths,events=events,
            root=7500200,leaves=[7500201,7500202],checks=checks,
            native=dict(dispatch='414820',type1='40CA20',state='508E20',behavior='668B30',insert='50D060',status='42D110',
                        immunity='509790',accumulation='42CD70',remove='505280',qualify='5057D0',update='50ACD0',hp='506EC0'),
            stubs=sorted(stubs|{'hit arrivals and status correction inputs are fixtures; complete attack construction and effect-queue ordering are not simulated',
                               'cycle effect 505 has no HP change and is recorded without simulating visual delivery'}),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(map(len,checks.values())),'native Ironeye poison cases')
