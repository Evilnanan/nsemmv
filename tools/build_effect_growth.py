"""Bind reviewed growth ladders to active compiled common events and PARAM rows."""
import argparse
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('extracted', type=Path)
p.add_argument('events', type=Path)
p.add_argument('all_events', type=Path, help='Private ExtractEffectEvents output from active MMV files')
a = p.parse_args()
x = json.loads(a.extracted.read_text())
events = json.loads(a.events.read_text())
assert x['hashes']['regulation.bin'] == '3305ac374b4da1db440e2b6644bc2c3c0ae96b98df9627f1a0e7a2b06d265c06'
assert events['sha256'] == '91680d83cd2b7509c303c3c3bdfda98b03c3a5c42e1d985f2901a29547ee6ba6'
spells = x['tables']['SpEffectParam']
by_id = {e['ID']:e for e in events['events']}
roots = {}
special_sources = []
for index, ins in enumerate(by_id[0]['instructions']):
    raw = bytes.fromhex(ins['hex'])
    if (ins['Bank'], ins['ID']) != (2000, 0) or len(raw) < 8:
        continue
    slot, event_id = struct.unpack_from('<ii', raw)
    if event_id not in (1400, 1402, 1403, 1406, 1407, 1408, 1409):
        continue
    args = list(struct.unpack('<' + 'i' * ((len(raw) - 8) // 4), raw[8:]))
    root = args[0]
    assert root in (7060001, 7060101, 7060400, 7060600, 7060500, 7060300)
    event = by_id[event_id]
    bound = [bytearray.fromhex(i['hex']) for i in event['instructions']]
    for parameter in event['Parameters']:
        target, source, size = (parameter[k] for k in ('TargetStartByte', 'SourceStartByte', 'ByteCount'))
        bound[parameter['InstructionIndex']][target:target + size] = raw[8 + source:8 + source + size]
    grants = sorted({struct.unpack_from('<i', data, 4)[0]
        for i, data in zip(event['instructions'], bound) if (i['Bank'], i['ID']) == (2004, 8)} - {0})
    caps = {struct.unpack_from('<i', data, 8)[0]
        for i, data in zip(event['instructions'], bound) if (i['Bank'], i['ID']) == (2003, 127)}
    if root == 7060001:
        expected = {1400:(8145, 3, 7060000), 1402:(8155, 2, 7060000),
                    1407:(8135, 2, 7060002), 1408:(8140, 1, 7060000), 1409:(8180, 8, 7060002)}[event_id]
        counter, count, grant = expected
        assert grants == [grant]
        actual_grants = [struct.unpack_from('<ii', data) for i,data in zip(event['instructions'], bound)
                         if (i['Bank'], i['ID']) == (2004, 8)]
        assert actual_grants == [(20000, grant)] * count
        waits = [struct.unpack_from('<I', data, 12)[0] for i,data in zip(event['instructions'], bound)
                 if (i['Bank'], i['ID']) == (3, 12) and struct.unpack_from('<I', data, 4)[0] == counter]
        assert waits == (list(range(1, count + 1)) if event_id in (1400, 1402, 1409) else [1])
        assert caps == ({count} if event_id in (1400, 1402, 1409) else set())
        special_sources.append(dict(event=event_id, slot=slot, initializationIndex=index, arguments=args,
                                    counter=counter, grant=grant, grantsPerEvent=count, thresholds=waits))
        continue
    assert caps == ({7} if event_id == 1403 else {10})
    roots[str(root)] = dict(event=event_id, slot=slot, initializationIndex=index, arguments=args,
                           grants=grants, eventLimit=caps.pop())
assert len(roots) == 5
assert len(special_sources) == 5
roots['7060001'] = dict(family='special-locations', grants=[7060000, 7060002], eventLimit=None, sources=special_sources)
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
# Bind counter producers to their actual map initializations. Only loaded mod
# files are enumerated here; this is not a complete inventory of vanilla maps.
all_events = json.loads(a.all_events.read_text())
assert all_events['regulationSha256'] == x['hashes']['regulation.bin']
files = {f['path']:f for f in all_events['files']}
maps = {m['path']:m for m in all_events['maps']}
common_func = files['event/common_func.emevd.dcx']
assert common_func['sha256'] == '6417c15ce944837b96120012dcedfda6ea7a3def7d5ecdb9b534e3a8f0ba297d'
functions = {e['ID']:e for e in common_func['events']}
producer_events = (90015051, 90015304, 90045002, 90005390)
producers = []
transformations = []
for path, file in sorted(files.items()):
    for event in file['events']:
        if event['ID'] != 0:
            continue
        for index, ins in enumerate(event['instructions']):
            raw = bytes.fromhex(ins['hex'])
            if (ins['Bank'], ins['ID']) != (2000, 6):
                continue
            slot, target = struct.unpack_from('<ii', raw)
            if target not in producer_events:
                continue
            args = list(struct.unpack('<' + 'i' * ((len(raw) - 8) // 4), raw[8:]))
            if target == 90015051 and args[1] != 8180:
                continue
            body = functions[target]
            bound = [bytearray.fromhex(i['hex']) for i in body['instructions']]
            for parameter in body['Parameters']:
                offset, src, size = (parameter[k] for k in ('TargetStartByte', 'SourceStartByte', 'ByteCount'))
                bound[parameter['InstructionIndex']][offset:offset+size] = raw[8+src:8+src+size]
            increments = [list(struct.unpack('<iii', data)) for i,data in zip(body['instructions'], bound)
                          if (i['Bank'], i['ID']) == (2003, 31)]
            if target == 90015051:
                assert args[2] == 8 and args[3] in (0, 1)
                assert increments == [[8180, 4, 8]] * 2
                # SkipIfComparison's bound fourth argument selects the second increment.
                assert (body['instructions'][3]['Bank'], body['instructions'][3]['ID']) == (1000, 10)
                assert bytes(bound[3]) == bytes([1, 1, 0, 0]) + struct.pack('<ii', args[3], 1)
                units = 1 + args[3]
            else:
                assert increments == [{90015304:[8155,3,4], 90045002:[8145,4,7], 90005390:[8135,3,1]}[target]]
                units = 1
            if target == 90005390:
                # The counter watches the transformed enemy, not the original
                # scarab/corpse/etc. The paired event swaps those map entities.
                paired = [(j, bytes.fromhex(i['hex'])) for j,i in enumerate(event['instructions'])
                          if (i['Bank'],i['ID']) == (2000,6) and len(bytes.fromhex(i['hex'])) >= 8
                          and struct.unpack_from('<i', bytes.fromhex(i['hex']), 4)[0] == 90005391
                          and bytes.fromhex(i['hex'])[8:] == raw[8:]]
                assert len(paired) == 1
                map_path = path.replace('event/', 'map/mapstudio/').replace('.emevd.dcx', '.msb.dcx')
                map = maps[map_path]
                entities = [next(e for e in map['enemies'] if e['EntityID'] == id) for id in args[2:4]]
                transformations.append(dict(path=path, eventIndex=index, pairedIndex=paired[0][0],
                                            map=map_path, mapSha256=map['sha256'], original=entities[0], target=entities[1]))
            producers.append(dict(path=path, event=event['ID'], index=index, target=target, slot=slot,
                                  arguments=args, counter=increments[0][0], units=units))
assert {p['target'] for p in producers} == set(producer_events)
assert {p['units'] for p in producers if p['counter'] == 8180} == {1, 2}
output = dict(schema=1, regulationSha256=x['hashes']['regulation.bin'], eventSha256=events['sha256'],
              roots=roots, events={str(id):by_id[id] for id in (1400, 1402, 1403, 1406, 1407, 1408, 1409)},
              producerAssets={path:files[path]['sha256'] for path in sorted({p['path'] for p in producers} | {'event/common_func.emevd.dcx'})},
              producerEvents={str(id):functions[id] for id in (*producer_events, 90005391)},
              producers=producers, transformations=transformations)
(ROOT / 'data/effect-growth-source.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
unique_ladders = {ladder['stages'][0] for record in roots.values() for ladder in record['ladders']}
print(f'Verified {len(roots)} growth roots, {sum(len(r["ladders"]) for r in roots.values())} ladder references, {len(unique_ladders)} unique ladders')
