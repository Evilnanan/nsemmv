"""Execute Raider skill conditional attack dispatch and recipient debuff updates.

Animation context, actor virtuals, PARAM lookup and collision arrivals are explicit
fixtures. State qualification, Behavior resolution and recipient numeric/timer
processing use pinned native instructions; this is not gameplay.
"""
import argparse
import itertools
import json
import math
import struct
from pathlib import Path
from unicorn.x86_const import *
from native_effect_runtime import BASE, OBJ, STOP, Chain, Inputs, sha
from effect_behavior_graph import BehaviorGraph
from native_attack_runtime import Type1Attack

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
paths=[graph.state('SmashAttack'+str(i)) for i in (1,2)]
assert [p['animation'] for p in paths]==['a904_541010','a904_541020']
events=[dict(tae=t['ID'],animation=an['ID'],**e) for b in tae['bundles'] for t in b['taes'] if t['ID']==2904
        for an in t['animations'] if an['ID'] in (541010,541020) for e in an['events'] if e['index']==2]
assert len(events)==2
for e,judge in zip(events,(6240,6250)):
    raw=bytes.fromhex(e['hex'])
    assert e['Type']==1 and struct.unpack_from('<i',raw,8)[0]==judge
    assert struct.unpack_from('<H',raw,14)[0]==2395 and raw[13]==3
rows={}
for id in (600000240,600000250):
    b=inputs.x['tables']['BehaviorParam_PC'][str(id)];r=inputs.x['tables']['AtkParam_Pc'][str(id)]
    assert b['refType']==0 and b['refId']==id
    assert struct.unpack_from('<i',behaviors[id],12)[0]==id
    assert r['spEffectId1']==7500401 and struct.unpack_from('<i',attacks[id],28)[0]==7500401
    assert [r[k] for k in ('selfTarget','friendlyTarget','opposeTarget','disableHitSpEffect')]==[0,0,1,0]
    rows[id]={k:r[k] for k in ('selfTarget','friendlyTarget','opposeTarget','disableHitSpEffect',*[f'spEffectId{i}' for i in range(5)])}
assert inputs.spells['7500400']['stateInfo']==2395
leaf=inputs.spells['7500401']
assert leaf['effectEndurance']==13 and leaf['spCategory']==20
assert [leaf[k] for k in ('magParamChange','miracleParamChange','shamanParamChange')]==[0,0,0]
assert inputs.rows[7500401][0x160]&128==0 and inputs.rows[7500401][0x161]&1==0 and inputs.rows[7500401][0x259]&32==0
assert all(math.isclose(leaf[k],.87,rel_tol=1e-6) for k in ('physicsAttackRate','magicAttackRate','fireAttackRate','thunderAttackRate','darkAttackRate'))
assert all(leaf['invocationConditionsStateChange'+str(i)]==0 for i in (1,2,3))


checks=dict(dispatch=[],arrival=[],refresh=[],lifetime=[]);stubs=set()
for event,copies,active in itertools.product(events,(0,1,2,3),(0,1)):
    c=Type1Attack(inputs,behaviors,weapons,rows)
    for _ in range(copies):c.insert(7500400)
    c.qualify();c.update(0);c.event(event,active)
    assert len(c.requests)==bool(copies),(event,copies,active,c.requests)
    if c.requests:
        r=c.requests[0];assert r['behavior']==(600000240 if event['animation']==541010 else 600000250)
        assert r['kind']==0 and r['slot']==1 and r['hand']==6
        assert abs(r['elapsed']-((event['EndTime']-event['StartTime']) if active else 0))<1e-6
    checks['dispatch'].append(dict(animation=event['animation'],copies=copies,active=active,requests=c.requests));stubs.update(c.stubs)
# Incoming hit requests are explicit fixtures, using the checked attack-row slot.
# The recipient intentionally has no relic root or caster state.
for count,kind in itertools.product((0,1,2,3,6),range(11)):
    c=Chain(inputs)
    for _ in range(count):c.insert(7500401)
    c.qualify();c.update(0);rates=[round(x,6) for x in c.attack(kind)]
    assert rates==[.87 if count and kind not in (3,4,5,10) else 1]*5,(count,kind,rates)
    assert len(c.nodes())==bool(count)
    checks['arrival'].append(dict(count=count,attackKind=kind,rates=rates,nodes=c.nodes()));stubs.update(c.stubs)
for elapsed,repeats in itertools.product((0,1,5,12),(1,2,3)):
    c=Chain(inputs);c.insert(7500401);c.qualify();c.update(0);c.qualify();c.update(elapsed)
    for _ in range(repeats):c.insert(7500401)
    c.qualify();c.update(0)
    assert len(c.nodes())==1 and c.nodes()[0]['lifetime']==13
    rates=[round(x,6) for x in c.attack()];assert rates==[.87]*5
    checks['refresh'].append(dict(elapsed=elapsed,repeats=repeats,nodes=c.nodes(),rates=rates));stubs.update(c.stubs)
for fps in (30,60,120):
    c=Chain(inputs);c.insert(7500401);c.qualify();c.update(0)
    for frame in range(1,15*fps):
        c.qualify();c.update(1/fps)
        if not c.nodes():break
    assert abs(frame/fps-13)<=3.01/fps and c.attack()==[1]*5
    checks['lifetime'].append(dict(fps=fps,expiryFrame=frame));stubs.update(c.stubs)
output=dict(schema=1,exeSha256=sha(inputs.raw),regulationSha256=inputs.x['hashes']['regulation.bin'],paramSha256=sha(inputs.param),
            behaviorParamSha256=sha(behavior_raw),attackParamSha256=sha(attack_raw),weaponParamSha256=sha(weapon_raw),
            animationBundleSha256=tae['bundles'][0]['sha256'],behaviorSha256=graph.metadata['hkxSha256'],paths=paths,events=events,
            root=7500400,leaf=7500401,attacks=rows,checks=checks,
            native=dict(dispatch='414820',type1='40CA20',state='508E20',behavior='668B30',insert='50D060',
                        qualify='5057D0',update='50ACD0',attack='502830'),
            stubs=sorted(stubs),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(map(len,checks.values())),'native Raider cases')
