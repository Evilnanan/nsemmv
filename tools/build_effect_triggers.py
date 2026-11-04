"""Bind reviewed action-triggered relic families to actual MMV animation events.

Full animation files stay private; commit only hashes, IDs and relevant events.
PARAM presence alone never creates an inferred trigger edge.
"""
import argparse
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('extracted', type=Path)
p.add_argument('animations', type=Path)
a = p.parse_args()
x = json.loads(a.extracted.read_text())
t = json.loads(a.animations.read_text())
assert x['hashes']['regulation.bin'] == '3305ac374b4da1db440e2b6644bc2c3c0ae96b98df9627f1a0e7a2b06d265c06'
assert t['bundles'][0]['sha256'] == '1410035ad79edb410fa41420ec259fcb4a1037d748c9c4a3b6ae8d1366c76d0f'
spells = x['tables']['SpEffectParam']
# Only reviewed simple chains enter the public summary. Complex/bullet branches
# remain in the research backlog until their own conditions have been traced.
families = {
    'bolus': ([7030200, 7030210], '使用苔药等道具时'),
    'guard-gauge': ([7030600, 7030610], '防御成功时'),
    'critical-gauge': ([7030800, 7030810], '致命一击时'),
    'critical-stamina': ([7035100, 7035110, 7035120], '致命一击后'),
    'grease': ([7030900, 7030910, 7030920], '涂抹油脂后'),
    'raider-hit': ([7031300], '技艺期间受击后'),
    'sixth-sense-gauge': ([7032400], '能力发动时'),
    'sixth-sense-attack': ([7032500], '能力发动后'),
    'ironeye-counter': ([7034700], '绝招发动后'),
    'madness-fp': ([7035500, 7035510], '发狂后'),
    'weapon-change': ([7035900], '切换武器后'),
    'guard-hp': ([7036100], '防御成功时'),
    'revenant-allies': ([7031200], '绝招发动时'),
    'critical-runes': ([7031900], '致命一击时'),
    'random-weapon': ([7035700], '切换武器后'),
    'recluse-max-hp': ([7034100], '绝招发动后'),
    'wylder-ultimate': ([7020100], '绝招发动后'),
    'wylder-skill': ([7020200], '技艺发动后'),
    'undertaker-ultimate': ([7036800], '绝招发动后'),
    'undertaker-growth': ([7037400], '发动强化技艺后'),
}
events = {}
for bundle in t['bundles']:
    for tae in bundle['taes']:
        for anim in tae['animations']:
            if anim['headerType'] != 'Standard':
                continue
            for e in anim['events']:
                if e['Type'] not in (66, 67, 302, 401):
                    continue
                raw = bytes.fromhex(e['hex'])
                id = struct.unpack_from('<i', raw)[0]
                if str(id) not in spells:
                    continue
                events.setdefault(id, []).append(dict(bundle=bundle['path'], tae=tae['ID'],
                    animation=anim['ID'], index=e['index'], type=e['Type'],
                    start=e['StartTime'], end=e['EndTime'], parameters=e['hex']))
roots = {}
for family, (ids, phase) in families.items():
    for root in ids:
        state = int(spells[str(root)]['stateInfo'])
        assert state > 0
        seeds = [id for id in events if any(spells[str(id)]['invocationConditionsStateChange' + str(i)] == state
                                          for i in (1, 2, 3))]
        assert seeds == ([root + 1, root + 3] if root == 7034100 else [root + 1]), (root, seeds)
        roots[str(root)] = dict(state=state, family=family, phase=phase, seeds=seeds,
                               events={str(id): events[id] for id in seeds})
output = dict(schema=1, regulationSha256=x['hashes']['regulation.bin'],
              assets={b['path']: b['sha256'] for b in t['bundles']}, roots=roots)
(ROOT / 'data/effect-trigger-source.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
print(f'Verified {len(roots)} marker roots against active animation events')
