"""Trace Undertaker ultimate contact healing through native dispatch and HP packets.

Actual asset rows, animation references, relation filters, state qualification,
node insertion and recovery aggregation run unchanged. Collision arrivals and
actor identities are explicit fixtures, not gameplay or multiplayer validation.
"""
import argparse
import itertools
import json
import math
import struct
from pathlib import Path
from native_effect_runtime import BASE, OBJ, Chain, Inputs, sha
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
root,leaf,marker=7037300,7037301,705012
r=inputs.spells[str(leaf)]
assert inputs.spells[str(root)]['stateInfo']==2066 and inputs.spells[str(root)]['spCategory']==20
assert inputs.spells[str(marker)]['stateInfo']==r['invocationConditionsStateChange1']==624
assert r['changeHpRate']==-30 and r['changeHpPoint']==-100 and r['effectEndurance']==0
assert r['spCategory']==10 and math.isclose(r['motionInterval'],.1,rel_tol=1e-6)
assert [r[k] for k in ('effectTargetSelfTarget','effectTargetFriendlyTarget','effectTargetOpposeTarget')]==[0,1,0]
behavior=inputs.x['tables']['BehaviorParam_PC']['700000495'];attack=inputs.x['tables']['AtkParam_Pc']['700000495']
assert behavior['refType']==0 and behavior['refId']==700000495
assert attack['spEffectId1']==leaf and struct.unpack_from('<i',attacks[700000495],28)[0]==leaf
assert [attack[k] for k in ('selfTarget','friendlyTarget','opposeTarget','disableHitSpEffect')]==[0,1,0,0]
assert attack['hit0_Radius']==2 and attack['hit0_DmyPoly1']==220
paths=[]
for state in ('BlinkStakeStart','AirBlinkStakeStart'):
    matches=[i for i,(t,_,n) in enumerate(graph.items) if t and n==1 and graph.types[t&0xffffff]['Identity']=='hkbStateMachine::StateInfo' and graph.name(i)==state]
    assert len(matches)==1
    selector=graph.reference(matches[0],'generator')
    assert graph.item(selector)[0]['Identity']=='hkbManualSelectorGenerator'
    for child in graph.children(selector):
        clips=graph.children(child);assert len(clips)==1
        clip=clips[0];assert graph.item(clip)[0]['Identity']=='hkbClipGenerator'
        paths.append(dict(state=state,stateItem=matches[0],selector=selector,child=child,clip=clip,animation=graph.string(graph.reference(clip,'animationName'))))
assert [p['animation'] for p in paths]==['a909_690000','a909_690010','a909_695000','a909_695010']
events=[dict(tae=t['ID'],animation=an['ID'],**e) for b in tae['bundles'] for t in b['taes'] for an in t['animations'] for e in an['events']
        if e['Type']==1 and len(bytes.fromhex(e['hex']))>=16 and struct.unpack_from('<H',bytes.fromhex(e['hex']),14)[0]==2066]
assert [(e['tae'],e['animation'],e['index']) for e in events]==[(2909,690000,52),(2909,690010,37),(2909,695000,96),(2909,695010,46)]
assert all(struct.unpack_from('<i',bytes.fromhex(e['hex']),8)[0]==7495 for e in events)

class Recipient(Chain):
    def hp(self,maximum):
        self.q(OBJ+0x10,0)
        self.invoke(0x506ec0,[OBJ,maximum,OBJ+0x800,OBJ+0x808,OBJ+0x820,0])
        self.q(OBJ+0x10,OBJ+0x6000)
        return list(struct.unpack('<7i',self.u.mem_read(OBJ+0x820,28)))
    def target(self,id,typ,same=False):
        self.u.mem_write(OBJ+0x6074,b'\1');self.u.mem_write(OBJ+0xb074,bytes([typ]))
        self.u.mem_write(OBJ+0xc000,inputs.rows[id]);self.q(OBJ+0xb800,OBJ+0xc000)
        return bool(self.invoke(0x52cc60,[OBJ+0x6000,OBJ+0x6000 if same else OBJ+0xb000,OBJ+0xb800])&255)

checks=dict(dispatch=[],target=[],healing=[],arrival=[],lateQualification=[]);stubs=set()
for event,copies,active in itertools.product(events,(0,1,2,3),(0,1)):
    c=Type1Attack(inputs,behaviors,weapons,{700000495})
    for _ in range(copies):c.insert(root)
    c.qualify();c.update(0);c.event(event,active)
    assert len(c.requests)==bool(copies)
    if c.requests:assert c.requests[0]['behavior']==700000495
    checks['dispatch'].append(dict(animation=event['animation'],copies=copies,active=active,requests=c.requests));stubs.update(c.stubs)
for id,(relation,typ,same) in itertools.product((leaf,7033101),(('self',1,True),('friendly',2,False),('opposing',6,False),('neutral',0,False))):
    c=Recipient(inputs);allowed=c.target(id,typ,same)
    assert allowed==(relation=='friendly' if id==leaf else relation in ('self','opposing'))
    checks['target'].append(dict(effect=id,relation=relation,allowed=allowed));stubs.update(c.stubs)
for fps,qualified,maximum in itertools.product((30,60,120),(False,True),(100,1000,1500,10000)):
    c=Recipient(inputs)
    if qualified:c.insert(marker)
    c.qualify();c.update(0);c.insert(leaf);heals=[]
    for frame in range(fps):
        c.qualify();c.update(1/fps);packet=c.hp(maximum)
        if any(packet):heals.append(dict(frame=frame,packet=packet))
    assert len(heals)==int(qualified),(fps,qualified,maximum,heals)
    if heals:assert heals[0]['packet']==[maximum*30//100+100,0,maximum*30//100+100,0,0,0,0],heals
    checks['healing'].append(dict(fps=fps,qualified=qualified,maximum=maximum,heals=heals,remaining=c.nodes()));stubs.update(c.stubs)
for fps,copies,frames in itertools.product((30,60,120),(1,2,3,6),((0,),(0,15,30))):
    c=Recipient(inputs);c.insert(marker);c.qualify();c.update(0);heals=[]
    for frame in range(fps*2):
        if frame in frames:
            for _ in range(copies):c.insert(leaf)
        c.qualify();c.update(1/fps);packet=c.hp(1000)
        if any(packet):heals.append(dict(frame=frame,packet=packet))
    assert len(heals)==len(frames) and sum(h['packet'][0] for h in heals)==400*copies*len(frames),heals
    checks['arrival'].append(dict(fps=fps,copies=copies,arrivalFrames=list(frames),heals=heals));stubs.update(c.stubs)
# Missing eligibility suspends this zero-lifetime node; record this distinction
# without claiming such a collision actually arrives in the running game.
for fps in (30,60,120):
    c=Recipient(inputs);c.insert(leaf);heals=[]
    for frame in range(fps*2):
        if frame==fps:c.insert(marker)
        c.qualify();c.update(1/fps);packet=c.hp(1000)
        if any(packet):heals.append(dict(frame=frame,packet=packet))
    assert len(heals)==1 and heals[0]['frame']>=fps and heals[0]['packet'][0]==400
    checks['lateQualification'].append(dict(fps=fps,markerFrame=fps,heals=heals));stubs.update(c.stubs)
output=dict(schema=1,exeSha256=sha(inputs.raw),regulationSha256=inputs.x['hashes']['regulation.bin'],paramSha256=sha(inputs.param),
            behaviorParamSha256=sha(behavior_raw),attackParamSha256=sha(attack_raw),weaponParamSha256=sha(weapon_raw),
            animationBundleSha256=tae['bundles'][0]['sha256'],behaviorSha256=graph.metadata['hkxSha256'],paths=paths,events=events,
            root=root,leaf=leaf,marker=marker,attack={k:attack[k] for k in ('selfTarget','friendlyTarget','opposeTarget','disableHitSpEffect','hit0_Radius','hit0_DmyPoly1','spEffectId1')},checks=checks,
            native=dict(dispatch='414820',type1='40CA20',state='508E20',behavior='668B30',relation='52CC60 → 3D1B30',
                        insert='50D060',qualify='5057D0',update='50ACD0',hp='506EC0'),stubs=sorted(stubs),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(map(len,checks.values())),'native Undertaker contact cases')
