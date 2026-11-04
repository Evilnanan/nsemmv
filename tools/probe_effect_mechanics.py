"""Execute pinned PC effect predicates/calculators with actual MMV PARAM rows.

Inputs stay read-only. The emulator has synthetic nodes, no OS/game process.
The absent attack PARAM lookup is stubbed; no multiplier or matching predicate
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
p.add_argument('--systems', type=Path, required=True, help='Private ExtractEffectDetails --systems JSON')
a = p.parse_args()
raw = a.exe.read_bytes()
exe_hash = hashlib.sha256(raw).hexdigest()
assert exe_hash == '9545e8732919bb6a63904cb73223641b3c4f9a67869be5722612acca413e8b3a'
x = json.loads(a.extracted.read_text())
assert x['hashes']['regulation.bin'] == '3305ac374b4da1db440e2b6644bc2c3c0ae96b98df9627f1a0e7a2b06d265c06'
systems = json.loads(a.systems.read_text())
assert systems['hashes']['regulation.bin'] == x['hashes']['regulation.bin']
system_rows, system_hashes = {}, {}
for name in ('GameSystemCommonParam', 'PlayerCommonParam'):
    data = a.systems.with_suffix('.' + name + '.param').read_bytes()
    assert struct.unpack_from('<H', data, 10)[0] == 1
    assert struct.unpack_from('<i', data, 0x40)[0] == 0
    offset = struct.unpack_from('<Q', data, 0x48)[0]
    system_rows[name] = data[offset:offset + 0x400]
    system_hashes[name] = hashlib.sha256(data).hexdigest()
for name, field, offset, fmt in [('GameSystemCommonParam','unknown_30C',0x30c,'<f'),
                                ('PlayerCommonParam','fh_unknown_43b',0x25a,'<H'),
                                ('PlayerCommonParam','analyseTarget_AllyEffectId',0x1a8,'<i')]:
    assert struct.unpack_from(fmt, system_rows[name], offset)[0] == systems['tables'][name]['0'][field]
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
    lookup_addresses = {}
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
        if rva == 0x40fff0 and address - BASE == 0x3c8be0:
            calls.add('3C8BE0 TAE start-event application recorder; active flag handling is native')
            assert uc.reg_read(UC_X86_REG_RCX) == OBJ + 0x6000
            emitted.append(uc.reg_read(UC_X86_REG_RDX) & 0xffffffff)
            finish(0)
        elif rva == 0x6c8a60 and address - BASE == 0xe78730:
            calls.add('E78730 HeroStatus PARAM lookup using actual extracted rows')
            wrapper = uc.reg_read(UC_X86_REG_RCX)
            id = uc.reg_read(UC_X86_REG_RDX) & 0xffffffff
            uc.mem_write(wrapper, struct.pack('<IIQ', id, 0, hero_addresses.get(id, 0)))
            finish(wrapper)
        elif rva == 0x3ed7f1 and address - BASE in (0x3ed850, 0x3ed86a, 0x3ed914):
            # Bound the reviewed ally branch before its networking/target-list continuation.
            uc.reg_write(UC_X86_REG_RIP, STOP)
            uc.emu_stop()
        elif rva == 0x3ed7f1 and address - BASE == 0x42c120:
            calls.add('42C120 synthetic Scholar owner for reviewed ally-grant branch')
            finish(OBJ + 0x6000)
        elif rva == 0x3ed7f1 and address - BASE == 0xe81650:
            calls.add('E81650 PlayerCommon row 0 lookup, actual ally effect at +0x1a8')
            wrapper = uc.reg_read(UC_X86_REG_RCX)
            system_row = OBJ + 0x1d000
            uc.mem_write(system_row, system_rows['PlayerCommonParam'])
            uc.mem_write(wrapper, struct.pack('<QI', system_row, 0))
            finish(wrapper)
        elif rva == 0x3ed7f1 and address - BASE == 0x3c7fd0:
            calls.add('3C7FD0 Scholar ally application recorder; eligibility and effect selection are native')
            assert uc.reg_read(UC_X86_REG_RCX) == OBJ + 0x7000
            emitted.append(uc.reg_read(UC_X86_REG_RDX) & 0xffffffff)
            finish(0)
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
        elif rva in (0x5077a0, 0x511700) and address - BASE == 0xea17e0:
            calls.add('EA17E0 growth/refresh lookup using actual SpEffect PARAM rows, including missing next rows')
            id = uc.reg_read(UC_X86_REG_RDX) & 0xffffffff
            wrapper = uc.reg_read(UC_X86_REG_RCX)
            if id in rows and id not in lookup_addresses:
                lookup_addresses[id] = OBJ + 0x10000 + len(lookup_addresses) * 0x400
                assert len(lookup_addresses) < 32
                uc.mem_write(lookup_addresses[id], rows[id])
            uc.mem_write(wrapper, struct.pack('<QI', lookup_addresses.get(id, 0), id))
            finish(wrapper)
        elif rva == 0x504940 and address - BASE == 0xe76d50:
            calls.add('E76D50 GameSystemCommon row 0 lookup, actual extracted unknown_30C at +0x30c')
            wrapper = uc.reg_read(UC_X86_REG_RCX)
            system_row = OBJ + 0x1d000
            uc.mem_write(system_row, system_rows['GameSystemCommonParam'])
            uc.mem_write(wrapper, struct.pack('<QI', system_row, 0))
            finish(wrapper)
        elif rva == 0x3ea8f0 and address - BASE == 0xe81650:
            calls.add('E81650 PlayerCommon row 0 lookup, actual extracted decay field at +0x25a')
            wrapper = uc.reg_read(UC_X86_REG_RCX)
            system_row = OBJ + 0x1d000
            uc.mem_write(system_row, system_rows['PlayerCommonParam'])
            uc.mem_write(wrapper, struct.pack('<QI', system_row, 0))
            finish(wrapper)
        if address - BASE == 0xe6d630:
            calls.add('E6D630 absent attack PARAM lookup')
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
for id in [7000000, 7000800, 7611202, 7082400, 7090000, 7090010, 7034201, 7033200, 7270100, 7037400, 7150000, 7036200]:
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
for id in [7036001, 7036011, 350401, 350502, 350602, 7100101, 8600105, 8600111, 8600205, 8600211, 7036102, 7031901]:
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
    conditional = id == '7036102'
    if conditional:
        assert row['invocationConditionsStateChange1'] == 2308
    extra = {'invocationConditionsStateChange1'} if conditional else set()
    if {k for k, v in row.items() if v != baseline[k]} - allowed_differences - extra:
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
    if conditional:
        recovery_timing[id]['requiresState'] = 2308

trigger_matching = []
trigger_families = {
    'bolus': [7030202, 7030212], 'guard-gauge': [7030602, 7030612],
    'critical-gauge': [7030802, 7030812], 'grease': [7030902, 7030912, 7030922],
    'critical-stamina': [7035102, 7035112, 7035122],
    'critical-runes': [7031901],
    'wylder-ultimate': [7020101], 'undertaker-ultimate': [7036801],
    'raider-hit': [7031302], 'sixth-sense-gauge': [7032402],
    'sixth-sense-attack': [7032501], 'ironeye-counter': [7034702],
    'madness-fp': [7035502, 7035512], 'weapon-change': [7035902], 'guard-hp': [7036102],
}
for family, ids in trigger_families.items():
    for existing in ids:
        assert x['tables']['SpEffectParam'][str(existing)]['spCategory'] == 20
        for incoming in ids:
            same = bool(run(0x510b20, [existing], [OBJ + 0x1000, incoming]).reg_read(UC_X86_REG_RAX) & 255)
            match = bool(run(0x511450, [existing], [OBJ + 0x1000, 20, 0, incoming]).reg_read(UC_X86_REG_RAX) & 255)
            assert same == match == (existing == incoming)
            trigger_matching.append(dict(family=family, existing=existing, incoming=incoming, reused=same))
trigger_values = []
for family in ('guard-gauge', 'critical-gauge', 'sixth-sense-gauge'):
    ids = trigger_families[family]
    u = run(0x508c70, ids, [OBJ, OBJ + 0x800], flags=4)
    value = struct.unpack('<f', u.mem_read(OBJ + 0x800, 4))[0]
    assert math.isclose(value, sum(x['tables']['SpEffectParam'][str(id)]['ultimateArtGauge'] for id in ids), abs_tol=1e-6)
    trigger_values.append(dict(family=family, ids=ids, value=value))
ids = trigger_families['grease']
u = run(0x502830, ids, [OBJ, OBJ + 0x800, -1, -1], kind=0)
value = struct.unpack('<f', u.mem_read(OBJ + 0x890, 4))[0]
assert math.isclose(value, 1.1 * 1.17 * 1.2, rel_tol=1e-6)
trigger_values.append(dict(family='grease', ids=ids, value=value))
for flags in (0, 4, 0x800c0003):
    value = run(0x505af0, [7031901], [OBJ], flags=flags).reg_read(UC_X86_REG_RAX)
    assert value == (600 if flags == 4 else 0)
    trigger_values.append(dict(family='critical-runes', ids=[7031901], flags=flags, value=value))

extra_getters = []
for rva, field, cases in [
    (0x505aa0, 'staminaRecoverChangeSpeed', [[], [7035102], [7035112], [7035122], [7035102, 7035112, 7035122]]),
    (0x508280, 'runeDiscountValue', [[], [7230000], [7230001], [7230000, 7230001]]),
]:
    for ids in cases:
        for flags in (0, 0x800c0003):
            value = scalar(run(rva, ids, [OBJ], flags=flags))
            active = [] if flags else ids
            expected = (sum(x['tables']['SpEffectParam'][str(i)][field] for i in active)
                        if field == 'staminaRecoverChangeSpeed' else
                        math.prod(1 - x['tables']['SpEffectParam'][str(i)][field] / 100 for i in active))
            assert math.isclose(value, expected, abs_tol=1e-6), (field, ids, value)
            extra_getters.append(dict(rva=hex(rva), field=field, ids=ids, flags=flags, value=value))
shop_matching = []
for existing in (7230000, 7230001):
    for incoming in (7230000, 7230001):
        category = int(x['tables']['SpEffectParam'][str(existing)]['spCategory'])
        same = bool(run(0x510b20, [existing], [OBJ + 0x1000, incoming]).reg_read(UC_X86_REG_RAX) & 255)
        match = bool(run(0x511450, [existing], [OBJ + 0x1000, category, 0, incoming]).reg_read(UC_X86_REG_RAX) & 255)
        assert same == (existing == incoming) and not match
        shop_matching.append(dict(existing=existing, incoming=incoming, category=category, reused=same, categoryMatch=match))

def f32(v):
    return struct.unpack('<f', struct.pack('<f', v))[0]

growth_advance = []
growth_rows = {id for id in rows if x['tables']['SpEffectParam'][str(id)]['spCategory'] == 204
               and x['tables']['SpEffectParam'][str(id)]['categoryPriority'] > 0}
for existing in sorted(growth_rows):
    priority = x['tables']['SpEffectParam'][str(existing)]['categoryPriority']
    first = existing
    while first - 1 in growth_rows and x['tables']['SpEffectParam'][str(first - 1)]['categoryPriority'] == priority:
        first -= 1
    for ids in ([existing], []) if existing == first else ([existing],):
        u = run(0x5077a0, ids, [OBJ, first, OBJ + 0x800])
        changed = bool(u.reg_read(UC_X86_REG_RAX) & 255)
        target = struct.unpack('<i', u.mem_read(OBJ + 0x800, 4))[0]
        expected = (existing + 1 if existing + 1 in rows else -1) if ids else first
        assert changed == bool(ids) and target == expected, (existing, first, target, expected)
        growth_advance.append(dict(existing=ids, incoming=first, target=target, changed=changed, priority=int(priority)))

hp_conditions = []
detail_source = json.loads((Path(__file__).resolve().parents[1] / 'data/effect-detail-source.json').read_text())
for id in map(int, detail_source['spells']):
    row = x['tables']['SpEffectParam'][str(id)]
    upper, lower = row['conditionHp'], row['conditionHpRate']
    if upper <= 0 and lower <= 0:
        continue
    bound = f32(f32(upper if upper > 0 else lower) * f32(0.01))
    nominal = f32(round(upper if upper > 0 else lower, 3) / 100)
    for ratio in sorted({0., f32(bound - 0.00001), bound, nominal, f32(bound + 0.00001), 1.}):
        expected = (upper < 0 or ratio <= f32(upper * f32(.01))) and (lower < 0 or ratio >= f32(lower * f32(.01)))
        u = run(0x50fc30, [id], [OBJ + 0x1000], flags=1, xmm_args={UC_X86_REG_XMM1:ratio})
        enabled = u.mem_read(OBJ + 0x1068, 1)[0] == 4
        assert enabled == expected, (id, ratio, enabled, expected)
        if id in (6851200, 7012300, 6851000):
            u = run(0x50f740, [id], [OBJ + 0x1000, 0, OBJ, 0], flags=4,
                    setup=lambda u:u.mem_write(OBJ + 0x104c, struct.pack('<f', -1)),
                    xmm_args={UC_X86_REG_XMM1:ratio})
            assert (u.mem_read(OBJ + 0x1068, 1)[0] == 4) == expected
        hp_conditions.append(dict(id=id, upper=upper, lower=lower, ratio=ratio, enabled=enabled,
                                  boundary=bound, nominal=nominal, fullUpdate=id in (6851200, 7012300, 6851000)))

growth_values = []
for stage in range(1, 11):
    id = 7069400 + stage
    raw_value = scalar(run(0x5071b0, [id], [OBJ]))
    def setup_discovery(u):
        u.mem_write(OBJ + 0x28, struct.pack('<Q', 1 << 28))  # live state 66 bucket
    ratio = scalar(run(0x6c7f30, [id], [0, OBJ], setup=setup_discovery))
    display = run(0x6c7e40, [id], [0, OBJ], setup=setup_discovery).reg_read(UC_X86_REG_RAX)
    assert math.isclose(raw_value, .16 * stage, abs_tol=1e-6)
    assert math.isclose(ratio, 1 + .16 * stage, abs_tol=1e-6) and display == 100 + 16 * stage
    growth_values.append(dict(id=id, field='itemDropRate', raw=raw_value, neutralRatio=ratio, neutralDisplay=display))
    id = 7069300 + stage
    value = scalar(run(0x508510, [id], [OBJ]))
    assert math.isclose(value, x['tables']['SpEffectParam'][str(id)]['soulRate'], abs_tol=1e-6)
    growth_values.append(dict(id=id, field='soulRate', value=value))

location_values = []
for first in (7069001, 7069021):
    for stage in range(10):
        id = first + stage
        u = run(0x502830, [id], [OBJ, OBJ + 0x800, -1, -1], kind=3)
        rates = [struct.unpack('<f', u.mem_read(OBJ + 0x800 + off, 4))[0] for off in (0x90, 0xa4, 0xa8, 0xac, 0xb0)]
        expected = x['tables']['SpEffectParam'][str(id)]['physicsAttackRate']
        assert all(math.isclose(v, expected, abs_tol=1e-6) for v in rates)
        location_values.append(dict(id=id, rates=rates))
u = run(0x502830, [7069006, 7069030], [OBJ, OBJ + 0x800, -1, -1], kind=3)
rates = [struct.unpack('<f', u.mem_read(OBJ + 0x800 + off, 4))[0] for off in (0x90, 0xa4, 0xa8, 0xac, 0xb0)]
expected = math.prod(x['tables']['SpEffectParam'][str(id)]['physicsAttackRate'] for id in (7069006,7069030))
assert all(math.isclose(v, expected, abs_tol=1e-6) for v in rates)
location_values.append(dict(ids=[7069006,7069030], rates=rates))

guard_counter = []
system_scale = systems['tables']['GameSystemCommonParam']['0']['unknown_30C']
assert math.isclose(system_scale, .6, abs_tol=1e-6)
for tag in (0, 103):
    for hp in (0, 100, 1000, 3000):
        for base_physical in (0, .5, 1, 100):
            def setup_counter(u):
                u.mem_write(OBJ + 0x10, struct.pack('<Q', OBJ + 0x7000))
                u.mem_write(OBJ + 0x71b8, struct.pack('<Q', OBJ + 0x7400))
                u.mem_write(OBJ + 0x7400, struct.pack('<Q', OBJ + 0x7800))
                u.mem_write(OBJ + 0x7940, struct.pack('<ii', hp, 3000))
                u.mem_write(OBJ + 0x800, bytes(64))
                u.mem_write(OBJ + 0x804, (1 << tag).to_bytes(32, 'little'))
                u.mem_write(OBJ + 0x600, struct.pack('<5f', base_physical, 100, 100, 100, 100))
            u = run(0x504940, [7150000], [OBJ, OBJ + 0x600, OBJ + 0x800], setup=setup_counter)
            values = list(struct.unpack('<5f', u.mem_read(OBJ + 0x600, 20)))
            extra = hp * .05 / system_scale if tag == 103 and base_physical >= 1 else 0
            assert math.isclose(values[0], base_physical + extra, abs_tol=5e-5)
            assert values[1:] == [100]*4
            def setup_final(u):
                u.mem_write(OBJ + 0x600, struct.pack('<5f', *values))
                u.mem_write(OBJ + 0x650, struct.pack('<5f', *([1]*5)))
            one_bits = struct.unpack('<I', struct.pack('<f', 1))[0]
            scale_bits = struct.unpack('<I', struct.pack('<f', system_scale))[0]
            final = run(0x6c5fc0, [], [OBJ + 0x800, OBJ + 0x600] + [OBJ + 0x650]*6 + [one_bits]*6 + [scale_bits], setup=setup_final)
            scaled_physical = struct.unpack('<f', final.mem_read(OBJ + 0x800, 4))[0]
            assert math.isclose(scaled_physical, values[0] * system_scale, abs_tol=5e-5)
            guard_counter.append(dict(tag=tag, hp=hp, maxHp=3000, basePhysical=base_physical,
                                      values=values, systemScale=system_scale, scaledPhysical=scaled_physical))

scholar_decay = []
default_decay = systems['tables']['PlayerCommonParam']['0']['fh_unknown_43b']
assert default_decay == 80 and x['tables']['SpEffectParam']['7036200']['unk_05'] == 30
for ids in ([], [7036200], [7036200]*3):
    def setup_decay_getter(u):
        u.mem_write(OBJ + 0x28, struct.pack('<Q', 1 << 48))
    value = scalar(run(0x505bf0, ids, [OBJ], setup=setup_decay_getter))
    assert value == (30 if ids else -1)
    for dt in (0, 1/60, .5, 1, 2, 4):
        def setup_decay(u):
            u.mem_write(OBJ + 0x18, struct.pack('<f', 100))
            for rva, raw in [(0x3c0f0a8, struct.pack('<Q', OBJ + 0x3000)),
                             (0x398a858, struct.pack('<f', value))]:
                page = rva & ~4095
                u.mem_map(BASE + page, 4096)
                u.mem_write(BASE + page, pe.get_data(page, 4096))
                u.mem_write(BASE + rva, raw)
        u = run(0x3ea8f0, [], [OBJ], setup=setup_decay, xmm_args={UC_X86_REG_XMM1: dt})
        remaining = struct.unpack('<f', u.mem_read(OBJ + 0x18, 4))[0]
        assert math.isclose(remaining, max(0, 100 - dt * (value if value >= 0 else default_decay)), abs_tol=1e-5)
        scholar_decay.append(dict(ids=ids, override=value, defaultRate=default_decay, dt=dt, start=100, remaining=remaining))

scholar_ally = []
for ids in ([], [7036300], [7036300]*2):
    for eligible in (0, 1):
        emitted = []
        def setup_ally(u):
            u.mem_write(OBJ + 0x6190, struct.pack('<Q', OBJ))
            u.mem_write(OBJ + 0x28, b'\xff' * 32)
            u.reg_write(UC_X86_REG_RBP, STACK + 0x4000)
            u.reg_write(UC_X86_REG_R13, OBJ + 0x8000)
            u.reg_write(UC_X86_REG_RSI, OBJ + 0x7000)
            u.reg_write(UC_X86_REG_R15, 0)
            u.mem_write(STACK + 0x4000 - 0x4d, bytes([eligible]))
        run(0x3ed7f1, ids, [], setup=setup_ally, emitted=emitted)
        assert emitted == ([7036301] if ids and eligible else [])
        scholar_ally.append(dict(ids=ids, eligibilityByte=eligible, emitted=emitted))
ally = systems['tables']['PlayerCommonParam']['0']['analyseTarget_AllyEffectId']
assert ally == 7036301
assert run(0x510b20, [ally], [OBJ + 0x1000, ally]).reg_read(UC_X86_REG_RAX) & 255
for kind in (0, 3, 4):
    u = run(0x502830, [ally], [OBJ, OBJ + 0x800, -1, -1], kind=kind)
    rates = [struct.unpack('<f', u.mem_read(OBJ + 0x800 + off, 4))[0] for off in (0x90, 0xa4, 0xa8, 0xac, 0xb0)]
    assert all(math.isclose(v, 1.15, abs_tol=1e-6) for v in rates)
    scholar_ally.append(dict(leaf=ally, kind=kind, rates=rates, reusesSameId=True))

zone_matching = []
for existing in (1413000, 7032803):
    for incoming in (1413000, 7032803):
        node = OBJ + 0x1000
        match = bool(run(0x511450, [existing], [node, 201, 145, incoming]).reg_read(UC_X86_REG_RAX) & 255)
        assert match
        u = run(0x511700, [existing], [node, incoming, 0, 0], xmm_args={UC_X86_REG_XMM2: 1})
        pointer, actual_id = struct.unpack('<Qi', u.mem_read(node, 12))
        duration = struct.unpack('<f', u.mem_read(node + 0x4c, 4))[0]
        assert actual_id == incoming and duration == 1.5
        assert bytes(u.mem_read(pointer, len(rows[incoming]))) == rows[incoming]
        # Use the mutated live node in the actual attack getter.
        invoke(u, 0x502830, [OBJ, OBJ + 0x800, -1, -1])
        rate = struct.unpack('<f', u.mem_read(OBJ + 0x8a4, 4))[0]
        assert math.isclose(rate, x['tables']['SpEffectParam'][str(incoming)]['magicAttackRate'], abs_tol=1e-6)
        zone_matching.append(dict(existing=existing, incoming=incoming, categoryMatch=match,
                                  activeId=actual_id, duration=duration, magicRate=rate))

action_start = []
for leaf in (7020101, 7020201, 7036801):
    for active in (0, 1):
        for mode in (0, 1):
            def setup(u):
                u.mem_write(OBJ + 0x18, struct.pack('<Q', OBJ + 0x6000))
                u.mem_write(OBJ + 0x808, struct.pack('<Q', OBJ + 0x900))
                u.mem_write(OBJ + 0x818, bytes([active]))
                u.mem_write(OBJ + 0x900, struct.pack('<i', leaf))
            emitted = []
            run(0x40fff0, [], [OBJ, OBJ + 0x800, mode], setup=setup, emitted=emitted)
            assert emitted == ([leaf] if active else [])
            action_start.append(dict(leaf=leaf, active=active, mode=mode, emitted=emitted))
action_values = []
for leaf in (7020101, 7020201, 7036801):
    for kind in (0, 1, 2, 3, 4, 5):
        u = run(0x502830, [leaf], [OBJ, OBJ + 0x800, -1, -1], kind=kind)
        values = [struct.unpack('<f', u.mem_read(OBJ + 0x800 + off, 4))[0] for off in (0x90, 0xa4, 0xa8, 0xac, 0xb0)]
        expected = x['tables']['SpEffectParam'][str(leaf)]['physicsAttackRate'] if kind < 5 else 1
        assert all(math.isclose(v, expected, abs_tol=1e-6) for v in values)
        action_values.append(dict(leaf=leaf, kind=kind, rates=values))
for leaf in (7020101, 7036801):
    node = OBJ + 0x1000
    u = run(0x511700, [leaf], [node, leaf, 0, 0], xmm_args={UC_X86_REG_XMM2: 1})
    duration = struct.unpack('<f', u.mem_read(node + 0x4c, 4))[0]
    assert duration == 40
    action_values.append(dict(leaf=leaf, refreshedDuration=duration))
u = run(0x503800, [7020101], [OBJ, OBJ + 0x500, OBJ + 0x520, OBJ + 0x540, OBJ + 0x800])
values = list(struct.unpack('<5f', u.mem_read(OBJ + 0x500, 20)))
assert all(math.isclose(v, 1.2, abs_tol=1e-6) for v in values)
action_values.append(dict(leaf=7020101, damageRates=values))
# Category 10 does not reuse an existing instance. Keep the skill's complete
# repeat-cast behavior open until the grant and expiry paths are connected.
assert not run(0x510b20, [7020201], [OBJ + 0x1000, 7020201]).reg_read(UC_X86_REG_RAX) & 255

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
              timing=timing, damageStatus=damage_status, triggerMatching=trigger_matching, triggerValues=trigger_values,
              extraGetters=extra_getters, shopMatching=shop_matching, hpConditions=hp_conditions, growthAdvance=growth_advance,
              growthValues=growth_values, zoneMatching=zone_matching, locationValues=location_values,
              guardCounter=guard_counter, scholarDecay=scholar_decay, scholarAlly=scholar_ally, actionStart=action_start, actionValues=action_values)
a.output.write_text(json.dumps(dict(schema=1, exeSha256=exe_hash, regulationSha256=x['hashes']['regulation.bin'], paramSha256=hashlib.sha256(param).hexdigest(), heroParamSha256=hashlib.sha256(hero_param).hexdigest(),
    systemDefinitionHashes={k:v for k,v in systems['hashes'].items() if k.startswith('defs/')},
    systemParamSha256=system_hashes,
    systemValues={'GameSystemCommonParam/0/unknown_30C':system_scale, 'PlayerCommonParam/0/fh_unknown_43b':default_decay,
                  'PlayerCommonParam/0/analyseTarget_AllyEffectId':ally}, effectLinks={'7036300':[ally]},
    **groups, recoveryTiming=recovery_timing, stubs=sorted(calls), gameplayVerified=False), indent=2) + '\n')
print('PASS:', ', '.join(f'{k}={len(v)}' for k, v in groups.items()))
print(f'Restore-only PARAM rows matched to tested timer families: {len(recovery_timing)}')
