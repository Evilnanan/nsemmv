"""Execute pinned PC effect predicates/calculators with actual MMV PARAM rows.

Inputs stay read-only. The emulator has synthetic nodes, no OS/game process.
The absent weapon PARAM lookup is stubbed; no multiplier or matching predicate
is substituted. This checks effect-instance behavior, not the whole expedition.
"""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_CODE, UC_HOOK_MEM_UNMAPPED
from unicorn.x86_const import *

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('exe', type=Path)
p.add_argument('params', type=Path)
p.add_argument('extracted', type=Path)
p.add_argument('output', type=Path)
p.add_argument('--hero-params', type=Path, required=True)
a = p.parse_args()
raw = a.exe.read_bytes()
exe_hash = hashlib.sha256(raw).hexdigest()
assert exe_hash == '9545e8732919bb6a63904cb73223641b3c4f9a67869be5722612acca413e8b3a'
x = json.loads(a.extracted.read_text())
assert x['hashes']['regulation.bin'] == '3305ac374b4da1db440e2b6644bc2c3c0ae96b98df9627f1a0e7a2b06d265c06'
param = a.params.read_bytes()
count = struct.unpack_from('<H', param, 10)[0]
positions = {struct.unpack_from('<i', param, 0x40 + i * 24)[0]: struct.unpack_from('<Q', param, 0x48 + i * 24)[0] for i in range(count)}
rows = {id: param[offset:offset + 0x400] for id, offset in positions.items()}
hero_param = a.hero_params.read_bytes()
hero_count = struct.unpack_from('<H', hero_param, 10)[0]
hero_positions = {struct.unpack_from('<i', hero_param, 0x40 + i * 24)[0]: struct.unpack_from('<Q', hero_param, 0x48 + i * 24)[0] for i in range(hero_count)}
hero_rows = {id: hero_param[offset:offset + 28] for id, offset in hero_positions.items()}
hero_fields = ['statVigor', 'statMind', 'statEndurance', 'statStrength', 'statDexterity', 'statIntelligence', 'statFaith', 'statArcane']
for id, row in hero_rows.items():
    decoded = x['tables']['HeroStatusParam'][str(id)]
    assert struct.unpack_from('<h', row, 4)[0] == decoded['totalLevel']
    assert list(struct.unpack_from('<8b', row, 6)) == [decoded[f] for f in hero_fields]
assert len(rows) == len(x['tables']['SpEffectParam'])
for id, row in rows.items():
    s = x['tables']['SpEffectParam'][str(id)]
    assert struct.unpack_from('<h', row, 0x13e)[0] == s['spCategory']
    assert struct.unpack_from('<H', row, 0x156)[0] == s['stateInfo']
    assert math.isclose(struct.unpack_from('<f', row, 0x390)[0], s['characterSkillCooldownReduction'], abs_tol=1e-6)
pe = pefile.PE(data=raw, fast_load=True)
BASE = pe.OPTIONAL_HEADER.ImageBase
OBJ, STACK, STOP = 0x10000000, 0x20000000, 0x30000000
calls = set()

def run(rva, ids, args, kind=0, flags=0):
    u = Uc(UC_ARCH_X86, UC_MODE_64)
    u.mem_map(OBJ, 0x20000); u.mem_map(STACK, 0x10000); u.mem_map(STOP, 0x1000)
    nodes = [OBJ + 0x1000 + i * 0x600 for i in range(len(ids))]
    if nodes: u.mem_write(OBJ + 8, struct.pack('<Q', nodes[0]))
    for i, (id, node) in enumerate(zip(ids, nodes)):
        u.mem_write(node + 0x100, rows[id])
        u.mem_write(node, struct.pack('<Qi', node + 0x100, id))
        u.mem_write(node + 0x68, struct.pack('<I', flags))
        if i + 1 < len(nodes): u.mem_write(node + 0x38, struct.pack('<Q', nodes[i + 1]))
    context = OBJ + 0x800
    u.mem_write(context + 8, struct.pack('<iiB', 40000, 1, kind))
    hero_addresses = {}
    if rva == 0x6c8a60:
        for i, (id, row) in enumerate(hero_rows.items()):
            hero_addresses[id] = OBJ + 0x10000 + i * 0x40
            u.mem_write(hero_addresses[id], row)
    sp = STACK + 0x8008
    for i, value in enumerate(args[4:]):
        u.mem_write(sp + 0x28 + i * 8, struct.pack('<Q', value))
    u.mem_write(sp, struct.pack('<Q', STOP)); u.reg_write(UC_X86_REG_RSP, sp)
    for reg, value in zip([UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8, UC_X86_REG_R9], args):
        u.reg_write(reg, value & 0xffffffffffffffff)
    def mapped(uc, access, address, size, value, user):
        page = address & ~4095; offset = page - BASE
        if not 0 <= offset < pe.OPTIONAL_HEADER.SizeOfImage:
            raise RuntimeError(f'Unexpected dependency at {address:x}, RIP={uc.reg_read(UC_X86_REG_RIP)-BASE:x}')
        uc.mem_map(page, 4096); uc.mem_write(page, pe.get_data(offset, 4096).ljust(4096, b'\0'))
        return True
    def code(uc, address, size, user):
        def finish(value):
            uc.reg_write(UC_X86_REG_RAX, value)
            sp = uc.reg_read(UC_X86_REG_RSP)
            uc.reg_write(UC_X86_REG_RIP, struct.unpack('<Q', uc.mem_read(sp, 8))[0])
            uc.reg_write(UC_X86_REG_RSP, sp + 8)
        if rva == 0x6c8a60 and address - BASE == 0xe78730:
            calls.add('E78730 HeroStatus PARAM lookup using actual extracted rows')
            wrapper = uc.reg_read(UC_X86_REG_RCX)
            id = uc.reg_read(UC_X86_REG_RDX) & 0xffffffff
            uc.mem_write(wrapper, struct.pack('<IIQ', id, 0, hero_addresses.get(id, 0)))
            finish(wrapper)
        elif rva == 0x6c8a60 and address - BASE == 0xe78720:
            calls.add('E78720 HeroStatus PARAM wrapper cleanup')
            finish(0)
        if address - BASE == 0xe6d630:
            calls.add('E6D630 absent weapon PARAM lookup')
            uc.reg_write(UC_X86_REG_RAX, uc.reg_read(UC_X86_REG_RCX))
            sp = uc.reg_read(UC_X86_REG_RSP)
            uc.reg_write(UC_X86_REG_RIP, struct.unpack('<Q', uc.mem_read(sp, 8))[0])
            uc.reg_write(UC_X86_REG_RSP, sp + 8)
    u.hook_add(UC_HOOK_MEM_UNMAPPED, mapped); u.hook_add(UC_HOOK_CODE, code)
    u.emu_start(BASE + rva, STOP, count=200000)
    assert u.reg_read(UC_X86_REG_RIP) == STOP, hex(rva)
    return u

def scalar(u):
    return struct.unpack('<f', u.reg_read(UC_X86_REG_XMM0).to_bytes(16, 'little')[:4])[0]

predicate = []
for id in [7000000, 7000800, 7611202, 7082400, 7090000, 7090010, 7034201]:
    category = int(x['tables']['SpEffectParam'][str(id)]['spCategory'])
    u = run(0x510b20, [id], [OBJ + 0x1000, id])
    reused = bool(u.reg_read(UC_X86_REG_RAX) & 255)
    assert reused == (category != 10)
    u = run(0x510b70, [id], [OBJ + 0x1000, int(x['tables']['SpEffectParam'][str(id)]['stateInfo'])])
    assert not (u.reg_read(UC_X86_REG_RAX) & 255)
    u = run(0x510bd0, [id], [OBJ + 0x1000, category, 0])
    assert not (u.reg_read(UC_X86_REG_RAX) & 255)
    predicate.append(dict(id=id, category=category, reusesSameId=reused))
attributes = []
for ids in [[], [7000000], [7000000]*3, [7000000, 7000002, 7000100], [7000702]*2]:
    for flags in [0, 0x800c0003]:
        u = run(0x502300, ids, [OBJ, OBJ + 0x800], flags=flags)
        values = list(struct.unpack('<8i', u.mem_read(OBJ + 0x800, 32)))
        fields = ['addLifeForceStatus', 'addWillpowerStatus', 'addEndureStatus', 'addStrengthStatus',
                  'addDexterityStatus', 'addMagicStatus', 'addFaithStatus', 'addLuckStatus']
        expected = [sum(x['tables']['SpEffectParam'][str(id)][f] for id in ids) if not flags else 0 for f in fields]
        assert values == expected
        attributes.append(dict(ids=ids, flags=flags, values=values))
attack = []
for ids in [[7611202], [7611202, 7611202], [7611202]*3, [7001502, 7611202], [7082400], [7082400, 7080000]]:
    for kind in [0, 1, 2, 3, 4, 5]:
        u = run(0x502830, ids, [OBJ, OBJ + 0x800, -1, -1], kind)
        values = [struct.unpack('<f', u.mem_read(OBJ + 0x800 + off, 4))[0] for off in (0x90, 0xa4, 0xa8, 0xac, 0xb0)]
        attack.append(dict(ids=ids, kind=kind, rates=values))
# Native source-kind dispatch: 3/4 are the sorcery/incantation branches.
for r in attack:
    if r['ids'] == [7611202]*3 and r['kind'] in [3, 4]:
        assert all(math.isclose(v, 1.14**3, rel_tol=1e-6) for v in r['rates']), attack
defense = []
for ids in [[], [7002602], [7002602]*3]:
    u = run(0x503800, ids, [OBJ, OBJ + 0x500, OBJ + 0x520, OBJ + 0x540, OBJ + 0x800])
    values = list(struct.unpack('<5f', u.mem_read(OBJ + 0x500, 20)))
    expected = [1, math.prod(x['tables']['SpEffectParam'][str(id)]['magicDamageCutRate'] for id in ids), 1, 1, 1]
    assert all(math.isclose(a, b, rel_tol=1e-6) for a, b in zip(values, expected)), values
    defense.append(dict(ids=ids, rates=values))
cooldown = []
for ids in [[], [7000800], [7000802]*3, [7000800, 7000804]]:
    for flags in [0, 0x800c0003]:
        actual = scalar(run(0x508480, ids, [OBJ], flags=flags))
        expected = math.prod(x['tables']['SpEffectParam'][str(id)]['characterSkillCooldownReduction'] for id in ids) if not flags else 1
        assert math.isclose(actual, expected, rel_tol=1e-6)
        cooldown.append(dict(ids=ids, flags=flags, multiplier=actual))
discovery = []
for ids in [[], [7633000], [7632400, 7633000], [7633000, 7632400], [7000000]]:
    actual = run(0x5072d0, ids, [OBJ]).reg_read(UC_X86_REG_RAX) & 0xffffffff
    expected = next((int(x['tables']['SpEffectParam'][str(id)]['weaponTypeDiscovery']) for id in ids if x['tables']['SpEffectParam'][str(id)]['stateInfo'] == 2122), -1)
    assert actual == expected & 0xffffffff
    discovery.append(dict(ids=ids, weaponType=expected))
gauge = []
for ids in [[], [7000900], [7000900]*3, [7000900, 6840200]]:
    for flags in [0, 4, 0x800c0003]:
        for rva, field in [(0x508be0, 'ultimateArtGaugeRate'), (0x508b90, 'ultimateArtGaugeChargeRate')]:
            actual = scalar(run(rva, ids, [OBJ], flags=flags))
            active = not flags & 0x800c0003 and (rva == 0x508be0 or bool(flags & 4))
            expected = math.prod(x['tables']['SpEffectParam'][str(id)][field] for id in ids) if active else 1
            assert math.isclose(actual, expected, rel_tol=1e-6)
            gauge.append(dict(ids=ids, flags=flags, field=field, multiplier=actual))

def f32(v):
    return struct.unpack('<f', struct.pack('<f', v))[0]

hero = []
modifiers = sorted({int(row['heroStatusModifier']) for row in x['tables']['SpEffectParam'].values() if row['stateInfo'] == 2123 and row['heroStatusModifier'] >= 0})
for modifier in modifiers:
    points = []
    id = modifier
    while str(id) in x['tables']['HeroStatusParam']:
        points.append(x['tables']['HeroStatusParam'][str(id)])
        id += 1
    assert points and all(a['totalLevel'] < b['totalLevel'] for a, b in zip(points, points[1:]))
    for level in range(1, 21):
        actual = run(0x6c8a60, [], [OBJ + 0x800, level, modifier])
        assert actual.reg_read(UC_X86_REG_RAX) & 255 == 1
        values = list(struct.unpack('<8b', actual.mem_read(OBJ + 0x806, 8)))
        low = next((p for p in reversed(points) if p['totalLevel'] <= level), points[0])
        high = next((p for p in points if p['totalLevel'] >= level), points[-1])
        if low == high:
            expected = [int(low[f]) for f in hero_fields]
        else:
            expected = [math.trunc(f32(f32(f32((high[f]-low[f])/(high['totalLevel']-low['totalLevel']))*(level-low['totalLevel'])) + low[f])) for f in hero_fields]
        assert values == expected, (modifier, level, values, expected)
        hero.append(dict(modifier=modifier, level=level, values=values))
a.output.parent.mkdir(parents=True, exist_ok=True)
a.output.write_text(json.dumps(dict(schema=1, exeSha256=exe_hash, regulationSha256=x['hashes']['regulation.bin'], paramSha256=hashlib.sha256(param).hexdigest(), heroParamSha256=hashlib.sha256(hero_param).hexdigest(), predicates=predicate, attributes=attributes, attack=attack, defense=defense, cooldown=cooldown, discovery=discovery, gauge=gauge, hero=hero, stubs=sorted(calls), gameplayVerified=False), indent=2) + '\n')
print(f'PASS: {len(predicate)} matching, {len(attributes)} attributes, {len(attack)} attack, {len(defense)} defense, {len(cooldown)} cooldown, {len(discovery)} discovery, {len(gauge)} gauge, {len(hero)} hero cases')
