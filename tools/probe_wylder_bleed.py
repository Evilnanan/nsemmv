"""Trace Wylder's confirmed pull-attack bleed path and its onset lockout.

Only the referenced 7500002 leaf contributes public values. The fire-animation
Behavior row is absent in this regulation and remains an open runtime question.
Native dispatch and recipient processing use explicit collision/actor fixtures.
"""
import argparse
import itertools
import json
import math
import struct
from pathlib import Path
from native_effect_runtime import Inputs, sha
from native_attack_runtime import Type1Attack
from native_ailment_runtime import Ailment
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
assert 600000030 not in behaviors and 600000030 not in attacks
rows=inputs.spells;leaf=rows['7500002']
assert rows['7500000']['stateInfo']==2035
assert leaf['bloodAttackPower']==55 and leaf['stateInfo']==6 and leaf['spCategory']==10003
assert leaf['changeHpRate']==12.5 and leaf['changeHpPoint']==100
assert leaf['effectEndurance']==1 and leaf['motionInterval']==2
assert leaf['isUseStatusAilmentAtkPowerCorrect']==1 and leaf['cycleOccurrenceSpEffectId']==500
assert rows['500']['changeHpRate']==rows['500']['changeHpPoint']==0
assert rows['9642']['disableBlood']==1
assert rows['7500001']['bloodAttackPower']==60
for table in ('BehaviorParam_PC','Bullet','AtkParam_Pc'):
    assert not any(v==7500001 for r in inputs.x['tables'][table].values() for v in r.values())
assert struct.unpack_from('<i',behaviors[600000035],12)[0]==600000035
assert inputs.x['tables']['BehaviorParam_PC']['600000035']['refType']==0
assert struct.unpack_from('<2i',attacks[600000035],24)==(6902,7500002)
attack=inputs.x['tables']['AtkParam_Pc']['600000035']
assert [attack[k] for k in ('selfTarget','friendlyTarget','opposeTarget','disableHitSpEffect')]==[0,0,1,0]
assert all(attack[k]==100 for k in ('spEffectAtkPowerCorrectRate_byDmg','spEffectAtkPowerCorrectRate_byPoint','spEffectAtkPowerCorrectRate_byRate'))
events=[dict(tae=t['ID'],animation=an['ID'],**e) for b in tae['bundles'] for t in b['taes'] if t['ID']==2900
        for an in t['animations'] for e in an['events']
        if e['Type']==1 and struct.unpack_from('<H',bytes.fromhex(e['hex']),14)[0]==2035]
assert [e['animation'] for e in events]==[500000,500005,505000,505005]
for e in events:
    raw=bytes.fromhex(e['hex']);assert struct.unpack_from('<i',raw,8)[0]==(6035 if e['animation']%10==5 else 6030) and raw[13]==3
paths=[graph.state(n) for n in ('FookShotPull','AirFookShotPull','FookShotFire_Walk','FookShotFire_Walk_Upper','AirFookShotFire')]
assert [p['animation'] for p in paths]==['a900_500005','a900_500005','a900_500000','a900_500000','a900_505000']
checks=dict(dispatch=[],onset=[],damage=[],repeat=[],lifetime=[]);stubs=set()
for e,copies,active in itertools.product(events,(0,1,2,3),(0,1)):
    c=Type1Attack(inputs,behaviors,weapons,{600000030,600000035})
    for _ in range(copies):c.insert(7500000)
    c.qualify();c.update(0);c.event(e,active)
    assert len(c.requests)==bool(copies)
    expected=600000035 if e['animation']%10==5 else 600000030
    if c.requests:assert c.requests[0]['behavior']==expected
    assert c.missing==([600000030]*2 if copies and expected==600000030 else [])
    checks['dispatch'].append(dict(animation=e['animation'],copies=copies,active=active,requests=c.requests,missingRows=c.missing));stubs.update(c.stubs)
for immune,resistance,scale in itertools.product((False,True),(1,54,55,56,110,500),(.5,1,1.5,2)):
    c=Ailment(inputs,2,resistance,immune);rejected=c.apply(7500002,scale);c.qualify();c.update(0)
    amount=int(55*scale);expected=immune or resistance>amount
    assert rejected==expected
    assert c.remaining()==(resistance if immune or not expected else resistance-amount)
    assert any(n['id']==7500002 for n in c.nodes())==(not rejected)
    checks['onset'].append(dict(immune=immune,resistance=resistance,scale=scale,accumulation=amount,rejected=rejected,remaining=c.remaining()));stubs.update(c.stubs)
for maximum in (99,100,137,1000,10000,12345,100000):
    c=Ailment(inputs,2,55);assert c.apply(7500002) is False;c.qualify();c.update(0)
    hp=c.hp_packet(maximum)[0];assert hp==-(int(maximum*.125)+100),(maximum,hp)
    c.qualify();c.update(1/60);assert c.hp_packet(maximum)[0]==0
    checks['damage'].append(dict(maximum=maximum,damage=hp));stubs.update(c.stubs)
for fps in (30,60,120):
    c=Ailment(inputs,2,55);c.apply(7500002);c.qualify();c.update(0);ticks=[];grants=[]
    for frame in range(3*fps):
        hp=c.hp_packet(10000)[0]
        if hp:ticks.append(dict(frame=frame,damage=hp))
        if c.emitted:grants.append(dict(frame=frame,ids=c.emitted[:]))
        c.emitted.clear();c.qualify();c.update(1/fps)
        if not c.nodes():break
    assert abs((frame+1)/fps-1)<=3.01/fps and ticks==[dict(frame=0,damage=-1350)]
    checks['lifetime'].append(dict(fps=fps,expiryFrame=frame+1,damage=ticks,grants=grants));stubs.update(c.stubs)
    c=Ailment(inputs,2,55);damage=[];applied=[]
    for frame in range(3*fps):
        result=c.apply(7500002)
        if result!='existing':applied.append(dict(frame=frame,rejected=result))
        c.qualify();c.update(1/fps);hp=c.hp_packet(10000)[0]
        if hp:damage.append(dict(frame=frame,damage=hp))
    assert len(damage)==3 and all(d['damage']==-1350 for d in damage)
    assert all(1<=(b['frame']-a['frame'])/fps<=1+3.01/fps for a,b in zip(damage,damage[1:]))
    checks['repeat'].append(dict(fps=fps,applied=applied,damage=damage));stubs.update(c.stubs)
output=dict(schema=1,exeSha256=sha(inputs.raw),regulationSha256=inputs.x['hashes']['regulation.bin'],paramSha256=sha(inputs.param),
            behaviorParamSha256=sha(behavior_raw),attackParamSha256=sha(attack_raw),weaponParamSha256=sha(weapon_raw),
            animationBundleSha256=tae['bundles'][0]['sha256'],behaviorSha256=graph.metadata['hkxSha256'],paths=paths,events=events,
            root=7500000,leaf=7500002,unresolved=dict(missingBehavior=600000030,unreferencedLeaf=7500001),checks=checks,
            native=dict(dispatch='414820',type1='40CA20',state='508E20',behavior='668B30',insert='50D060',status='42D110',
                        immunity='509790',accumulation='42CD70',remove='505280',qualify='5057D0',update='50ACD0',hp='506EC0'),
            stubs=sorted(stubs|{'attack instances/collision and status-correction inputs are fixtures; no complete gameplay or network',
                               'unresolved missing Behavior 600000030 is only recorded; no claim that its animation cannot trigger another runtime path',
                               'cycle effect 500 has no HP change and is recorded without simulating visual delivery'}),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(map(len,checks.values())),'native Wylder bleed cases')
