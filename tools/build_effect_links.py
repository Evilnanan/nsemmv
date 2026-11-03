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
(ROOT / 'data/effect-link-source.json').write_text(json.dumps(dict(schema=1, regulationSha256=x['hashes']['regulation.bin'],
    hashes={k:v for k,v in x['hashes'].items() if k.startswith('defs/')}, emitters=emitters), ensure_ascii=False, indent=2) + '\n')
print(f'Verified {len(emitters)} Behavior/Bullet effect paths')
