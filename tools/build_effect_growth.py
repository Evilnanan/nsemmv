"""Bind reviewed growth ladders to active compiled common events and PARAM rows."""
import argparse
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('extracted', type=Path)
p.add_argument('events', type=Path)
a = p.parse_args()
x = json.loads(a.extracted.read_text())
events = json.loads(a.events.read_text())
assert x['hashes']['regulation.bin'] == '3305ac374b4da1db440e2b6644bc2c3c0ae96b98df9627f1a0e7a2b06d265c06'
assert events['sha256'] == '91680d83cd2b7509c303c3c3bdfda98b03c3a5c42e1d985f2901a29547ee6ba6'
spells = x['tables']['SpEffectParam']
by_id = {e['ID']:e for e in events['events']}
roots = {}
for index, ins in enumerate(by_id[0]['instructions']):
    raw = bytes.fromhex(ins['hex'])
    if (ins['Bank'], ins['ID']) != (2000, 0) or len(raw) < 8:
        continue
    slot, event_id = struct.unpack_from('<ii', raw)
    if event_id not in (1403, 1406):
        continue
    args = list(struct.unpack('<' + 'i' * ((len(raw) - 8) // 4), raw[8:]))
    root = args[0]
    assert root in (7060101, 7060400, 7060600, 7060500, 7060300)
    event = by_id[event_id]
    bound = [bytearray.fromhex(i['hex']) for i in event['instructions']]
    for parameter in event['Parameters']:
        target, source, size = (parameter[k] for k in ('TargetStartByte', 'SourceStartByte', 'ByteCount'))
        bound[parameter['InstructionIndex']][target:target + size] = raw[8 + source:8 + source + size]
    grants = sorted({struct.unpack_from('<i', data, 4)[0]
        for i, data in zip(event['instructions'], bound) if (i['Bank'], i['ID']) == (2004, 8)} - {0})
    caps = {struct.unpack_from('<i', data, 8)[0]
        for i, data in zip(event['instructions'], bound) if (i['Bank'], i['ID']) == (2003, 127)}
    assert caps == ({7} if event_id == 1403 else {10})
    roots[str(root)] = dict(event=event_id, slot=slot, initializationIndex=index, arguments=args,
                           grants=grants, eventLimit=caps.pop())
assert len(roots) == 5
assert spells['7037401']['replaceSpEffectId'] == 7037501
roots['7037400'] = dict(grants=[7037501], eventLimit=None, animationSeed=7037401)
for root, record in roots.items():
    ladders = []
    for grant in record['grants']:
        first = grant
        while spells[str(first)]['spCategory'] != 204:
            first = int(spells[str(first)]['replaceSpEffectId'])
            assert first > 0
        priority = spells[str(first)]['categoryPriority']
        stages = []
        id = first
        while str(id) in spells:
            row = spells[str(id)]
            assert row['spCategory'] == 204 and row['categoryPriority'] == priority
            stages.append(id)
            id += 1
        assert stages
        ladders.append(dict(grant=grant, stages=stages, priority=int(priority)))
    record['ladders'] = ladders
output = dict(schema=1, regulationSha256=x['hashes']['regulation.bin'], eventSha256=events['sha256'],
              roots=roots, events={str(id):by_id[id] for id in (1403, 1406)})
(ROOT / 'data/effect-growth-source.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
unique_ladders = {ladder['stages'][0] for record in roots.values() for ladder in record['ladders']}
print(f'Verified {len(roots)} growth roots, {sum(len(r["ladders"]) for r in roots.values())} ladder references, {len(unique_ladders)} unique ladders')
