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

def run(rva, ids, args, kind=0, flags=0, emitted=None, setup=None, xmm_args=None):
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
    if rva == 0x50a150:
        count = sum(x['tables']['SpEffectParam'][str(id)]['stateInfo'] == 199 for id in ids)
        u.mem_write(OBJ + 0x28, struct.pack('<Q', min(count, 15) << 20))
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
    for reg, value in (xmm_args or {}).items():
        u.reg_write(reg, int.from_bytes(struct.pack('<f', value), 'little'))
    if setup:
        setup(u)
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
        elif rva == 0x50a150 and address - BASE == 0x3c7fd0:
            calls.add('3C7FD0 effect application recorder; dispatch is native')
            assert uc.reg_read(UC_X86_REG_RCX) == OBJ + 0x500
            emitted.append(uc.reg_read(UC_X86_REG_RDX) & 0xffffffff)
            finish(0)
        elif rva == 0x48bc60 and address - BASE in (0x42c120, 0x3d4180):
            calls.add('42C120 / 3D4180 synthetic gauge owner without player HUD notification')
            finish(OBJ + 0x500 if address - BASE == 0x42c120 else 0)
        elif rva == 0x511b80 and address - BASE == 0xea17e0:
            calls.add('EA17E0 SpEffect PARAM lookup for lifetime refresh using actual row')
            id = uc.reg_read(UC_X86_REG_RDX) & 0xffffffff
            assert id in ids
            wrapper = uc.reg_read(UC_X86_REG_RCX)
            uc.mem_write(wrapper, struct.pack('<Qi', nodes[ids.index(id)] + 0x100, id))
            finish(wrapper)
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
for id in [7000000, 7000800, 7611202, 7082400, 7090000, 7090010, 7034201, 7033200, 7270100]:
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

resistance = []
resist_fields = ['changePoisonResistPoint', 'changeDiseaseResistPoint', 'changeBloodResistPoint',
                'changeCurseResistPoint', 'changeFreezeResistPoint', 'changeSleepResistPoint', 'changeMadnessResistPoint']
for ids in [[], [7003000], [7003000]*3, [7003000, 7003001], [7003000, 6850200], [6850200]*3,
            [7003100, 7003200, 7003300, 7003400, 7003500, 7003600]]:
    for flags in [0, 0x800c0003]:
        for kind, field in enumerate(resist_fields):
            value = scalar(run(0x507de0, ids, [OBJ, kind], flags=flags))
            expected = sum(x['tables']['SpEffectParam'][str(id)][field] for id in ids) if not flags else 0
            assert value == expected, (ids, field, value, expected)
            resistance.append(dict(ids=ids, flags=flags, field=field, value=value))

fp_cost = []
for ids in [[], [7610700], [7610702]*3, [7610700, 7610701, 7610702]]:
    for flags in [0, 0x800c0003]:
        for rva, field in [(0x507310, 'magicConsumptionRate'), (0x507410, 'shamanConsumptionRate'),
                           (0x5081e0, 'miracleConsumptionRate'), (0x5061b0, 'artsConsumptionRate')]:
            value = scalar(run(rva, ids, [OBJ], flags=flags))
            expected = math.prod(x['tables']['SpEffectParam'][str(id)][field] for id in ids) if not flags else 1
            assert math.isclose(value, expected, rel_tol=1e-6), (hex(rva), value, expected)
            fp_cost.append(dict(ids=ids, flags=flags, field=field, multiplier=value))

skill_uses = []
for ids in [[], [7033200], [7270100]]:
    for flags in [0, 0x800c0003]:
        value = run(0x5059b0, ids, [OBJ], flags=flags).reg_read(UC_X86_REG_RAX) & 255
        assert value == (len(ids) if not flags else 0)
        skill_uses.append(dict(ids=ids, flags=flags, value=value))

kill_matching = []
for existing in (7090000, 7090010):
    for incoming in (7090000, 7090010):
        same = bool(run(0x510b20, [existing], [OBJ + 0x1000, incoming]).reg_read(UC_X86_REG_RAX) & 255)
        match = bool(run(0x511450, [existing], [OBJ + 0x1000, 20, 0, incoming]).reg_read(UC_X86_REG_RAX) & 255)
        assert same == match == (existing == incoming)
        kill_matching.append(dict(existing=existing, incoming=incoming, reused=same))
kill_dispatch = []
for ids in [[], [7090000], [7090010], [7090000, 7090010], [7090010, 7090000], [7000000, 7090000]]:
    for special in [0, 1]:
        for flags in [0, 0x800c0003]:
            children = []
            run(0x50a150, ids, [OBJ, OBJ + 0x500, special], flags=flags, emitted=children)
            field = 'applyIdOnKillSp' if special else 'applyIdOnGetSoul'
            expected = [int(x['tables']['SpEffectParam'][str(id)][field]) for id in ids
                        if not flags and x['tables']['SpEffectParam'][str(id)]['stateInfo'] == 199]
            assert children == expected
            u = run(0x508c70, children, [OBJ, OBJ + 0x800], flags=4)
            percent, points = struct.unpack('<2f', u.mem_read(OBJ + 0x800, 8))
            expected_percent = sum(x['tables']['SpEffectParam'][str(id)]['ultimateArtGauge'] for id in children)
            assert math.isclose(percent, expected_percent, abs_tol=1e-6) and points == 0
            kill_dispatch.append(dict(ids=ids, special=special, flags=flags, emitted=children, percent=percent))
gauge_apply = []
for percent, initial, maximum in [(5, 0, 1000), (1.65, 0, 1000), (11.5, 0, 1000), (3.8, 0, 1000), (11.5, 950, 1000)]:
    def setup(u):
        u.mem_write(OBJ + 0x814, struct.pack('<2f', initial, maximum))
    u = run(0x48bc60, [], [OBJ + 0x800], setup=setup, xmm_args={UC_X86_REG_XMM1: percent})
    value = struct.unpack('<f', u.mem_read(OBJ + 0x814, 4))[0]
    assert math.isclose(value, min(maximum, initial + maximum * percent / 100), abs_tol=1e-4)
    gauge_apply.append(dict(percent=percent, initial=initial, maximum=maximum, value=value))

# Damage amount only gates the replacement; buildup uses a fixed PARAM value.
damage_status = []
status_channels = [(6820000, 'poizonAttackPower', 0), (6820100, 'diseaseAttackPower', 1),
                   (6820200, 'freezeAttackPower', 4), (6820300, 'bloodAttackPower', 2),
                   (6820400, 'madnessAttackPower', 6), (6820500, 'sleepAttackPower', 5),
                   (6820600, 'curseAttackPower', 3)]
for root, field, channel in status_channels:
    trigger = x['tables']['SpEffectParam'][str(root)]
    bridge = int(trigger['replaceSpEffectId'])
    child = int(x['tables']['SpEffectParam'][str(bridge)]['cycleOccurrenceSpEffectId'])
    assert trigger['deleteCriteriaDamage'] == 12
    assert int(x['tables']['SpEffectParam'][str(bridge)]['replaceSpEffectId']) == root
    for damage in (0, 1, 100, 10000):
        for excluded in (0, 1):
            def setup(u):
                u.mem_write(OBJ + 0x104c, struct.pack('<f', -1))
            u = run(0x504d30, [root], [OBJ, 0, 0, 0, excluded], flags=4,
                    setup=setup, xmm_args={UC_X86_REG_XMM1: damage})
            replaced = struct.unpack('<f', u.mem_read(OBJ + 0x104c, 4))[0] == 0
            assert replaced == (damage > 0 and not excluded)
            damage_status.append(dict(root=root, damage=damage, excluded=bool(excluded), replaced=replaced))
    amount = scalar(run(0xea0d20, [child], [OBJ + 0x1000, channel]))
    assert amount == x['tables']['SpEffectParam'][str(child)][field]
    # Neutral recovery context: no incoming buildup modifiers or immunity.
    settled = scalar(run(0x42e0e0, [], [OBJ], xmm_args={UC_X86_REG_XMM1: amount,
                     UC_X86_REG_XMM2: 0, UC_X86_REG_XMM3: 1}))
    def setup_gauge(u):
        u.mem_write(OBJ + 0x800 + 0x10 + channel * 4, struct.pack('<i', 1000))
        u.mem_write(OBJ + 0x800 + 0x2c + channel * 4, struct.pack('<i', 1000))
    u = run(0x42cd70, [], [OBJ + 0x800, channel, int(settled)], setup=setup_gauge)
    remaining = struct.unpack('<i', u.mem_read(OBJ + 0x810 + channel * 4, 4))[0]
    assert remaining == 1000 - amount
    damage_status.append(dict(root=root, bridge=bridge, child=child, field=field, channel=channel,
                              amount=amount, remaining=remaining))

def invoke(u, rva, args, xmm_args=None):
    sp = STACK + 0x8008
    u.mem_write(sp, struct.pack('<Q', STOP))
    u.reg_write(UC_X86_REG_RSP, sp)
    for reg, value in zip([UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8, UC_X86_REG_R9], args):
        u.reg_write(reg, value & 0xffffffffffffffff)
    for reg, value in (xmm_args or {}).items():
        u.reg_write(reg, int.from_bytes(struct.pack('<f', value), 'little'))
    u.emu_start(BASE + rva, STOP, count=200000)
    assert u.reg_read(UC_X86_REG_RIP) == STOP
    return u.reg_read(UC_X86_REG_RAX)

# Actual timer/refresh/accumulator routines, keeping one live synthetic node.
# Periodic restore getters consume flag 4; no lifetime or cooldown calculation is stubbed.
timing = []
for id in [7036001, 7036011, 350401, 350502, 350602, 7100101, 8600105, 8600111, 8600205, 8600211]:
    row = x['tables']['SpEffectParam'][str(id)]
    for mode in ['none', 'once', 'continuous']:
        if mode == 'continuous' and id not in (7100101, 8600211, 350602):
            continue
        refresh = mode != 'none'
        if refresh and row['spCategory'] == 10:
            continue  # Reapplication creates a separate instance, not a refresh.
        node, control = OBJ + 0x1000, OBJ + 0x900
        def setup(u):
            u.mem_write(node + 0x48, struct.pack('<3f', *([row['effectEndurance']]*3)))
            # Match the constructor's initially pending node; first update arms the tick.
            u.mem_write(node + 0x68, struct.pack('<I', 2))
            if row['stateInfo'] == 304:
                u.mem_write(OBJ + 0x28, struct.pack('<Q', 1 << 20))
                u.mem_write(control, struct.pack('<Q', OBJ))
                u.mem_write(control + 0xc, struct.pack('<i', 32))
                u.mem_write(control + 0x38, struct.pack('<Q', 10))
                u.mem_write(node + 0x10, struct.pack('<Q', control))
                for offset in (0x18, 0x1c, 0x24, 0x28):
                    u.mem_write(node + offset, struct.pack('<i', -1))
                u.mem_write(node + 0x30, struct.pack('<i', 1))
        u = run(0x511b80, [id], [node], setup=setup,
                xmm_args={UC_X86_REG_XMM1: 0, UC_X86_REG_XMM2: 1, UC_X86_REG_XMM3: 1})
        ticks = [0] if u.reg_read(UC_X86_REG_RAX) & 255 else []
        assert ticks == [0]
        reset = None
        if row['stateInfo'] == 304:
            reset = struct.unpack('<i', u.mem_read(control + 0xc, 4))[0]
            assert reset == 0
            # New attacks after recovery must not be erased throughout the 1-second lifetime.
            u.mem_write(control + 0xc, struct.pack('<i', 7))
        for frame in range(1, 361 if mode == 'continuous' else 181):
            if invoke(u, 0x5113f0, [node]) & 255:
                break
            if refresh and (frame == 12 or (mode == 'continuous' and frame % 12 == 0)):
                before = struct.unpack('<f', u.mem_read(node + 0x54, 4))[0]
                invoke(u, 0x511700, [node, id, 0, 0], {UC_X86_REG_XMM2: 1})
                assert struct.unpack('<f', u.mem_read(node + 0x54, 4))[0] == before
            if invoke(u, 0x511b80, [node], {UC_X86_REG_XMM1: 1/60, UC_X86_REG_XMM2: 1, UC_X86_REG_XMM3: 1}) & 255:
                ticks.append(round(frame/60, 6))
        if mode == 'continuous':
            assert len(ticks) >= math.floor(5 / row['motionInterval']) + 1
            assert all(abs((b-a) - row['motionInterval']) < 0.04 for a, b in zip(ticks, ticks[1:])), (id, ticks)
        elif not refresh:
            assert ticks == [0], (id, ticks)
        elif row['motionInterval'] < row['effectEndurance'] + 0.2:
            assert len(ticks) == 2 and abs(ticks[1] - row['motionInterval']) < 0.04, (id, ticks)
        else:
            assert ticks == [0], (id, ticks)
        after = struct.unpack('<i', u.mem_read(control + 0xc, 4))[0] if reset is not None else None
        if reset is not None:
            assert after == 7
        timing.append(dict(id=id, refreshAt=0.2 if refresh else None, refreshEvery=0.2 if mode == 'continuous' else None, lifetime=row['effectEndurance'],
                           interval=row['motionInterval'], ticks=ticks, accumulatorAfterFirstTick=reset,
                           accumulatorAfterNewAttacks=after))

# Apply the tested timer families only to audited restore-only rows. Mixed buffs,
# conditional activation, expiry replacements and other side effects stay excluded.
snapshot = json.loads((Path(__file__).resolve().parents[1] / 'data/effect-detail-source.json').read_text())
assert snapshot['hashes']['regulation.bin'] == x['hashes']['regulation.bin']
restore_fields = {'changeHpRate', 'changeMpRate', 'changeStaminaRate', 'changeHpPoint', 'changeMpPoint', 'changeStaminaPoint'}
allowed_differences = restore_fields | {'addLifeForceStatus', 'effectEndurance', 'motionInterval', 'spCategory',
    'stateInfo', 'effectTargetAttacker', 'isWaitModeDelete', 'vfxId', 'accumuVal', 'triggerOnWepType'}
baseline = x['tables']['SpEffectParam']['7000000']
recovery_timing = {}
for id in snapshot['spells']:
    row = x['tables']['SpEffectParam'][id]
    if row['stateInfo'] not in (0, 304) or row['spCategory'] not in (0, 10, 20) or row['addLifeForceStatus'] != 0:
        continue
    if not any(row[f] < 0 for f in restore_fields) or any(row[f] > 0 for f in restore_fields):
        continue
    if {k for k, v in row.items() if v != baseline[k]} - allowed_differences:
        continue
    examples = [r for r in timing if r['refreshAt'] is None
                and math.isclose(row['effectEndurance'], r['lifetime'], abs_tol=1e-6)
                and math.isclose(row['motionInterval'], r['interval'], abs_tol=1e-6)
                and row['spCategory'] == x['tables']['SpEffectParam'][str(r['id'])]['spCategory']
                and row['stateInfo'] == x['tables']['SpEffectParam'][str(r['id'])]['stateInfo']]
    if not examples or (row['stateInfo'] == 304 and row['accumuVal'] != -999):
        continue
    recovery_timing[id] = dict(lifetime=round(row['effectEndurance'], 6), interval=round(row['motionInterval'], 6),
        repeatedApplication='independent' if row['spCategory'] == 10 else 'refresh',
        resetsAccumulator=row['stateInfo'] == 304, exemplar=examples[0]['id'])

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
groups = dict(predicates=predicate, attributes=attributes, attack=attack, defense=defense, cooldown=cooldown,
              discovery=discovery, gauge=gauge, hero=hero, resistance=resistance, fpCost=fp_cost,
              skillUses=skill_uses, killMatching=kill_matching, killDispatch=kill_dispatch, gaugeApply=gauge_apply,
              timing=timing, damageStatus=damage_status)
a.output.write_text(json.dumps(dict(schema=1, exeSha256=exe_hash, regulationSha256=x['hashes']['regulation.bin'], paramSha256=hashlib.sha256(param).hexdigest(), heroParamSha256=hashlib.sha256(hero_param).hexdigest(), **groups, recoveryTiming=recovery_timing, stubs=sorted(calls), gameplayVerified=False), indent=2) + '\n')
print('PASS:', ', '.join(f'{k}={len(v)}' for k, v in groups.items()))
print(f'Restore-only PARAM rows matched to tested timer families: {len(recovery_timing)}')
