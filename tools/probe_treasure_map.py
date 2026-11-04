"""Bind hidden-treasure events to map flags and execute native visibility gates.

Compiled EMEVD and MSB bindings are statically checked, not interpreted as a
game VM. Flag values, map display mode and override are explicit fixtures;
the original map predicates and pin update execute unchanged. No gameplay.
"""
import argparse
import itertools
import json
import struct
from pathlib import Path
from unicorn.x86_const import *
from native_effect_runtime import BASE, OBJ, Chain, Inputs, sha

p = argparse.ArgumentParser(description=__doc__)
for name in ('exe', 'extracted', 'map', 'events', 'output'):
    p.add_argument(name, type=Path)
a = p.parse_args(); inputs = Inputs(a.exe, a.extracted)
maps = json.loads(a.map.read_text()); events = json.loads(a.events.read_text())
assert maps['hashes']['regulation.bin'] == events['regulationSha256'] == inputs.x['hashes']['regulation.bin']
root = 7070001
assert inputs.spells[str(root)]['spCategory'] == 10 and inputs.spells[str(root)]['stateInfo'] == 0
files = {f['path']: f for f in events['files']}
common = files['event/common.emevd.dcx']; functions = files['event/common_func.emevd.dcx']
assert common['sha256'] == '91680d83cd2b7509c303c3c3bdfda98b03c3a5c42e1d985f2901a29547ee6ba6'
assert functions['sha256'] == '6417c15ce944837b96120012dcedfda6ea7a3def7d5ecdb9b534e3a8f0ba297d'
event = next(e for e in functions['events'] if e['ID'] == 90015100)
assert event['RestBehavior'] == 1
assert [(i['Bank'], i['ID'], i['hex']) for i in event['instructions']] == [
    (2000, 2, '00000000'),  # DisableNetworkSync
    (1003, 2, '0000000000000000'),  # end unless appearance flag is ON
    (2003, 66, '000000000000000001000000'),  # enable spawn flag
    (4, 5, '00000000204E0000FFFFFFFF010000000000803F'),  # await own player 20000 has effect
    (2003, 66, '000000000000000001000000'),  # enable local display flag
]
assert [(r['InstructionIndex'], r['TargetStartByte'], r['SourceStartByte'], r['ByteCount'])
        for r in event['Parameters']] == [(1, 4, 0, 4), (2, 4, 4, 4), (3, 8, 8, 4), (4, 4, 12, 4)]
initializations = []
for n, ins in enumerate(next(e for e in common['events'] if e['ID'] == 0)['instructions']):
    raw = bytes.fromhex(ins['hex'])
    if (ins['Bank'], ins['ID']) != (2000, 6) or len(raw) != 24:
        continue
    slot, function, appearance, spawn, effect, display = struct.unpack('<6i', raw)
    if function != event['ID'] or effect != root:
        continue
    assert appearance in range(8000, 8012) and spawn - display == 980
    assert spawn in range(9100, 9112)
    initializations.append(dict(index=n, slot=slot, appearance=appearance, spawn=spawn, effect=effect, display=display))
assert [r['index'] for r in initializations] == list(range(320, 356))
assert [r['slot'] for r in initializations] == list(range(36))
assert all(sum(r['appearance'] == flag for r in initializations) == 3 for flag in range(8000, 8012))

param_raw = a.map.with_suffix('.WorldMapPointParam.param').read_bytes()
raw_rows = Inputs.table(param_raw, 0x80)
points = []
for key, row in maps['tables']['WorldMapPointParam'].items():
    if row['worldMapPointIconId'] != 62 or row['eventFlagId1'] not in range(9100, 9112):
        continue
    id = int(key); raw = raw_rows[id]
    assert struct.unpack_from('<3I', raw, 4) == tuple(row[k] for k in ('eventFlagId0', 'eventFlagId1', 'eventFlagId5'))
    assert struct.unpack_from('<I', raw, 0x4c)[0] == row['eventFlagId4'] == 0
    assert struct.unpack_from('<I', raw, 0x6c)[0] == row['eventFlagId8'] == 0
    assert raw[0x56] == row['unknown_56'] and raw[0x56] in (1, 2)
    bound = row['eventFlagId0'] in range(8120, 8132)
    if bound:
        assert any(r['display'] == row['eventFlagId0'] and r['spawn'] == row['eventFlagId1'] for r in initializations)
    else:
        assert row['eventFlagId0'] in range(8720, 8732)
    points.append(dict(id=id, reveal=int(row['eventFlagId0']), spawn=int(row['eventFlagId1']),
                       opened=int(row['eventFlagId5']), displayMask=raw[0x56], boundToRelicEvent=bound))
assert len(points) == 24 and sum(p['boundToRelicEvent'] for p in points) == 12

# Bind available disappear flags to actual chest interactions. Only three of
# the twelve base points have assets in the extracted mod maps; do not infer
# missing vanilla assets or count candidates as guaranteed spawned chests.
chests = []
for point in points:
    if not point['boundToRelicEvent']:
        continue
    matches = []
    for m in events['maps']:
        for obj in m['interactions']:
            if obj['EventFlagID'] != point['opened']:
                continue
            asset = next(r for r in m['assets'] if r['Name'] == obj['ObjActPartName'])
            treasure = next(r for r in m['treasures'] if r['TreasurePartName'] == obj['ObjActPartName'])
            assert obj['ObjActParamId'] == 210 and treasure['InChest'] == 1
            matches.append(dict(map=m['path'], sha256=m['sha256'], asset=asset['EntityID'],
                                model=asset['ModelName'], objact=obj['ObjActParamId'], flag=obj['EventFlagID'], itemLot=treasure['ItemLotID']))
    chests.append(dict(point=point['id'], interactions=matches))
assert sum(bool(c['interactions']) for c in chests) == 3

class MapVisibility(Chain):
    def __init__(self, point, flags):
        super().__init__(inputs)
        self.flags = set(flags); self.reads = []
        # Existing flag-manager singleton avoids the native missing-singleton diagnostic.
        global_ptr = BASE + 0xeaaa98 + 7 + 0x2d66b09
        self.mapped(self.u, 0, global_ptr, 8, 0, None); self.q(global_ptr, OBJ + 0xf000)
        self.u.mem_write(OBJ + 0x8000, raw_rows[point['id']])
        self.q(OBJ + 0x9010, OBJ + 0x8000)  # standalone PARAM wrapper
        self.q(OBJ + 0xa078, OBJ + 0x8000)  # 9048A0 enclosing point
        self.q(OBJ + 0xb028, OBJ + 0x8000)  # 90A010 pin

    def hook(self, u, address, size, user):
        if address == BASE + 0x5e7260:
            self.stubs.add('5E7260 explicit event-flag store; native map gates and pin update unchanged')
            assert u.reg_read(UC_X86_REG_RCX) == OBJ + 0xf000
            flag = struct.unpack('<I', u.mem_read(u.reg_read(UC_X86_REG_RDX), 4))[0]
            self.reads.append(flag)
            u.reg_write(UC_X86_REG_RAX, int(flag in self.flags))
            sp = u.reg_read(UC_X86_REG_RSP)
            u.reg_write(UC_X86_REG_RIP, struct.unpack('<Q', u.mem_read(sp, 8))[0])
            u.reg_write(UC_X86_REG_RSP, sp + 8)
        else:
            super().hook(u, address, size, user)

    def visible(self, mode=False, override=False):
        self.u.mem_write(OBJ + 0xc019, bytes([mode, override]))
        self.invoke(0x90a010, [OBJ + 0xb000, OBJ + 0xc000])
        return bool(self.u.mem_read(OBJ + 0xb00c, 1)[0])

checks = dict(visibility=[],override=[],copies=[],unbound=[]); stubs = set()
for point, reveal, spawn, opened in itertools.product(points, (False, True), (False, True), (False, True)):
    flags = [point[key] for key, on in [('reveal', reveal), ('spawn', spawn), ('opened', opened)] if on]
    c = MapVisibility(point, flags)
    expected = reveal and spawn and not opened
    assert bool(c.invoke(0xeaaa70, [OBJ + 0x9000]) & 255) == expected
    assert bool(c.invoke(0x9048a0, [OBJ + 0xa000]) & 255) == expected
    visible = c.visible(); assert visible == (expected and bool(point['displayMask'] & 1))
    other_mode = c.visible(mode=True); assert other_mode == (expected and bool(point['displayMask'] & 2))
    checks['visibility'].append(dict(point=point['id'], reveal=reveal, spawn=spawn, opened=opened,
                                     eligible=expected, visible=visible, otherMode=other_mode))
    stubs.update(c.stubs)
for point, opened, mode, override in itertools.product((points[0],), (False, True), (False, True), (False, True)):
    c = MapVisibility(point, [point['reveal'], point['spawn']] + ([point['opened']] if opened else []))
    visible = c.visible(mode, override)
    assert visible == (not mode and (not opened or override))
    checks['override'].append(dict(point=point['id'], opened=opened, mode=mode, override=override, visible=visible))
    stubs.update(c.stubs)
for copies in range(4):
    c = Chain(inputs)
    for _ in range(copies): c.insert(root)
    c.qualify(); c.update(0)
    nodes = c.nodes()
    # Category 10 preserves independent nodes, but EMEVD asks for presence,
    # then sets one boolean flag; it never counts or scales those nodes.
    assert len(nodes) == copies and all(r['id'] == root for r in nodes)
    checks['copies'].append(dict(copies=copies, nodes=nodes, present=bool(nodes)))
    stubs.update(c.stubs)
for point in points:
    if point['boundToRelicEvent']: continue
    c = MapVisibility(point, [point['spawn'], point['reveal'] - 600])
    visible = c.visible(); assert not visible
    checks['unbound'].append(dict(point=point['id'], flags=sorted(c.flags), visible=visible))
    stubs.update(c.stubs)

output = dict(schema=1, exeSha256=sha(inputs.raw), regulationSha256=events['regulationSha256'], paramSha256=sha(inputs.param),
              mapParamSha256=sha(param_raw), root=root, event=event, initializations=initializations, points=points, chests=chests,
              eventAssets={f['path']: f['sha256'] for f in (common, functions)}, checks=checks,
              native=dict(open='EAAA70', area='EAAC20', missing='EAA9D0', point='9048A0', pin='90A010', context='5EC560'),
              stubs=sorted(stubs), eventVmExecuted=False, gameplayVerified=False)
a.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
print('PASS', sum(map(len, checks.values())), 'native hidden-treasure cases; compiled event and chest bindings checked')
