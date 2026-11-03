"""Extract reviewed cross-table effect links without copying full game tables."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('extracted', type=Path)
a = p.parse_args()
x = json.loads(a.extracted.read_text())
assert x['hashes']['regulation.bin'] == '3305ac374b4da1db440e2b6644bc2c3c0ae96b98df9627f1a0e7a2b06d265c06'
tables = x['tables']
emitters = {}
for emitter, expected_leaf in [(7050000, 7050001), (7090101, 7090102), (7090103, 7090102),
                               (7012202, 7012201), (7031201, 7031202)]:
    row = tables['SpEffectParam'][str(emitter)]
    assert row['stateInfo'] == 275
    behavior_id = int(row['behaviorId'])
    behavior = tables['BehaviorParam_PC'][str(behavior_id)]
    assert behavior['refType'] == 1
    bullet_id = int(behavior['refId'])
    bullet = tables['Bullet'][str(bullet_id)]
    assert bullet['HitBulletID'] == bullet['intervalCreateBulletId'] == -1
    assert bullet['numShoot'] == 1 and bullet['initVellocity'] == 0 and bullet['isEndlessHit'] == 0
    leaves = [int(bullet['spEffectId' + str(i)]) for i in range(5) if bullet['spEffectId' + str(i)] > 0]
    assert leaves == [expected_leaf]
    atk_id = int(bullet['atkId_Bullet'])
    attack = tables['AtkParam_Pc'][str(atk_id)]
    assert attack['disableHitSpEffect'] == 0 and attack['friendlyTarget'] == 1 and attack['opposeTarget'] == 0
    assert attack['selfTarget'] == (emitter == 7012202)
    emitters[str(emitter)] = dict(behaviorId=behavior_id, bulletId=bullet_id, attackId=atk_id,
        leaves=leaves, radius=bullet['hitRadius'], includeSelf=bool(attack['selfTarget']),
        behavior={k:behavior[k] for k in ('refType', 'refId')},
        bullet={k:bullet[k] for k in ('hitRadius', 'hitRadiusMax', 'life', 'atkId_Bullet', 'spEffectId0',
                                     'HitBulletID', 'intervalCreateBulletId', 'numShoot', 'initVellocity')},
        attack={k:attack[k] for k in ('friendlyTarget', 'opposeTarget', 'selfTarget', 'disableHitSpEffect')})
# Terra Magica is placed through two hit transitions and then emits a recurring
# friendly buff pulse. The field's collision radius is not its buff radius.
behavior = tables['BehaviorParam_PC']['869050000']
assert tables['SpEffectParam']['7032802']['behaviorId'] == 869050000
assert behavior['refType'] == 1 and behavior['refId'] == 12413000
zone_bullets = {str(id): tables['Bullet'][str(id)] for id in range(12413000, 12413004)}
assert [zone_bullets[str(id)]['HitBulletID'] for id in range(12413000, 12413004)] == [12413001, 12413002, -1, -1]
assert [zone_bullets[str(id)]['intervalCreateBulletId'] for id in range(12413000, 12413004)] == [-1, 12413003, 12413003, -1]
assert all(r['numShoot'] == 1 and r['initVellocity'] == 0 for r in zone_bullets.values())
field, pulse = zone_bullets['12413002'], zone_bullets['12413003']
assert field['life'] == 30 and field['intervalCreateTimeMin'] == field['intervalCreateTimeMax'] == .5
assert pulse['spEffectId0'] == 7032803 and pulse['isEndlessHit'] == 0
assert all(pulse['spEffectId' + str(i)] == 0 for i in range(1, 5))
attack = tables['AtkParam_Pc'][str(int(pulse['atkId_Bullet']))]
assert attack['friendlyTarget'] == attack['selfTarget'] == 1
assert attack['opposeTarget'] == attack['disableHitSpEffect'] == 0
emitters['7032802'] = dict(behaviorId=869050000, bulletId=12413000, attackId=int(pulse['atkId_Bullet']),
    leaves=[7032803], radius=pulse['hitRadius'], includeSelf=True, fieldDuration=field['life'], pulseInterval=.5,
    behavior={k:behavior[k] for k in ('refType', 'refId')},
    bullets={id:{k:r[k] for k in ('HitBulletID', 'intervalCreateBulletId', 'intervalCreateTimeMin',
             'intervalCreateTimeMax', 'life', 'hitRadius', 'hitRadiusMax', 'atkId_Bullet', 'spEffectId0',
             'numShoot', 'initVellocity', 'isEndlessHit')} for id,r in zone_bullets.items()},
    attack={k:attack[k] for k in ('friendlyTarget', 'opposeTarget', 'selfTarget', 'disableHitSpEffect')})
(ROOT / 'data/effect-link-source.json').write_text(json.dumps(dict(schema=1, regulationSha256=x['hashes']['regulation.bin'],
    hashes={k:v for k,v in x['hashes'].items() if k.startswith('defs/')}, emitters=emitters), ensure_ascii=False, indent=2) + '\n')
print(f'Verified {len(emitters)} Behavior/Bullet effect paths')
