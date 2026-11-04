"""Trace weapon-conditioned on-hit recovery without assuming new MMV enums work.

Native hit filtering, actual weapon/attack rows, effect insertion and resource
getters execute in isolation. Impact data and queued delivery are fixtures;
DLL runtime patches and physical collisions are not loaded by this probe.
"""
import argparse
import json
import struct
from pathlib import Path
from unicorn.x86_const import *
from native_effect_runtime import BASE, OBJ, Chain, Inputs, sha

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('exe', type=Path)
p.add_argument('extracted', type=Path)
p.add_argument('assets', type=Path)
p.add_argument('output', type=Path)
a = p.parse_args()
inputs = Inputs(a.exe, a.extracted)
assets = json.loads(a.assets.read_text())
assert assets['hashes']['regulation.bin'] == inputs.x['hashes']['regulation.bin']
weapon_raw = a.assets.with_suffix('.EquipParamWeapon.param').read_bytes()
weapons = inputs.table(weapon_raw, 0x298)
weapon_ids = {}
for id, row in assets['tables']['EquipParamWeapon'].items():
    weapon_ids.setdefault(int(row['wepType']), int(id))
attack_raw = a.extracted.with_suffix('.AtkParam_Pc.param').read_bytes()
# This PARAM has duplicate IDs. Select one independently verified unique row,
# preserving the table order rather than reducing the entire table to a dict.
attack_rows = [attack_raw[off:off + 0x1d0]
    for k in range(struct.unpack_from('<H', attack_raw, 10)[0])
    if struct.unpack_from('<i', attack_raw, 0x40 + k * 24)[0] == 10000
    for off in [struct.unpack_from('<Q', attack_raw, 0x48 + k * 24)[0]]]
assert len(attack_rows) == 1 and attack_rows[0][0x1cb] & 1
families = []
for id, attach in inputs.x['tables']['AttachEffectParam'].items():
    if not 7340000 <= int(id) <= 7352800: continue
    root = int(attach['passiveSpEffectId_1'])
    row = inputs.spells[str(root)]
    leaf = int(row['atkOccurrenceSpEffectId'])
    target = inputs.spells[str(leaf)]
    kind = int(row['triggerOnWepType'])
    assert row['stateInfo'] == 2103 and row['spCategory'] == 20
    assert target['spCategory'] == 0 and target['effectTargetAttacker'] == 1
    assert target['effectEndurance'] == 1 and abs(target['motionInterval'] - 1.1) < 1e-6
    assert target['changeHpPoint'] == (-15 if int(id) < 7350000 else 0)
    assert target['changeMpPoint'] == (-2 if int(id) >= 7350000 else 0)
    assert struct.unpack_from('<H', weapons[weapon_ids[kind]], 0x1a6)[0] == kind
    families.append(dict(effect=int(id), root=root, leaf=leaf, weaponType=kind,
                         weapon=weapon_ids[kind], nativeTypeAccepted=kind <= 87))
families.sort(key=lambda r: r['effect'])
assert len(families) == 56
assert sum(not r['nativeTypeAccepted'] for r in families) == 8


class Hit(Chain):
    def hook(self, u, address, size, user):
        pc = address - BASE
        def finish(value=0):
            u.reg_write(UC_X86_REG_RAX, value)
            sp = u.reg_read(UC_X86_REG_RSP)
            u.reg_write(UC_X86_REG_RIP, struct.unpack('<Q', u.mem_read(sp, 8))[0])
            u.reg_write(UC_X86_REG_RSP, sp + 8)
        if pc == 0xe6d630:
            assert u.reg_read(UC_X86_REG_R8) == 10000 and u.reg_read(UC_X86_REG_RDX) == 1
            self.stubs.add('E6D630 unique actual AtkParam_Pc/10000 row lookup')
            wrapper = u.reg_read(UC_X86_REG_RCX)
            u.mem_write(OBJ + 0xb000, attack_rows[0])
            self.q(wrapper + 0x10, OBJ + 0xb000)
            finish(wrapper)
        elif pc == 0xea7fc0:
            id = u.reg_read(UC_X86_REG_RDX) & 0xffffffff
            self.stubs.add('EA7FC0 actual EquipParamWeapon row lookup')
            wrapper = u.reg_read(UC_X86_REG_RCX)
            u.mem_write(OBJ + 0xb800, weapons[id])
            self.q(wrapper + 8, OBJ + 0xb800)
            finish(wrapper)
        elif pc == 0xea9a60:
            self.stubs.add('EA9A60 empty auxiliary animation-reference lookup')
            finish(u.reg_read(UC_X86_REG_RCX))
        else:
            super().hook(u, address, size, user)

    def hit(self, weapon, kind=1, flags=0, attack_category=0):
        vector, ctx = OBJ + 0x8000, OBJ + 0x8400
        self.q(vector + 8, OBJ + 0x8200)
        self.q(vector + 0x10, OBJ + 0x8200)
        self.q(vector + 0x18, OBJ + 0x8300)
        self.u.mem_write(ctx, bytes(0x300))
        self.u.mem_write(ctx + 0x122, bytes([kind]))
        self.u.mem_write(ctx + 0x161, bytes([flags]))
        self.u.mem_write(ctx + 0x190, struct.pack('<i', weapon))
        self.u.mem_write(ctx + 0x40, struct.pack('<iii', 10000, 1, attack_category))
        self.u.mem_write(ctx + 0x280, struct.pack('<i', 10))
        self.invoke(0x505e90, [OBJ, vector, ctx])
        end = struct.unpack('<Q', self.u.mem_read(vector + 0x10, 8))[0]
        count = (end - (OBJ + 0x8200)) // 4
        assert 0 <= count < 64
        return list(struct.unpack('<' + 'i' * count, self.u.mem_read(OBJ + 0x8200, count * 4)))

    def hp(self):
        self.q(OBJ + 0x10, 0)
        self.invoke(0x50b860, [OBJ] + [OBJ + 0x800 + k * 0x20 for k in range(11)] + [0])
        self.q(OBJ + 0x10, OBJ + 0x6000)
        return list(struct.unpack('<2f', self.u.mem_read(OBJ + 0x880, 8)))


checks = dict(filter=[], timing=[], mixed=[], reapplication=[])
stubs = set()
for family in families:
    for copies in (1, 3):
        c = Hit(inputs)
        for _ in range(copies): c.insert(family['root'])
        c.qualify(); c.update(0)
        match = c.hit(family['weapon'])
        wrong = c.hit(weapon_ids[3 if family['weaponType'] == 1 else 1])
        assert match == ([family['leaf']] if family['nativeTypeAccepted'] else [])
        assert wrong == []
        kinds = {str(kind): c.hit(family['weapon'], kind=kind) for kind in (0, 1, 2, 3, 4, 11, 12)}
        assert all(v == (match if int(k) in (1, 2, 11, 12) else []) for k, v in kinds.items())
        flagged = c.hit(family['weapon'], flags=32)
        category = c.hit(family['weapon'], attack_category=6)
        assert flagged == category == []
        checks['filter'].append(dict(effect=family['effect'], copies=copies, matched=match,
                                    mismatched=wrong, kinds=kinds, excludedFlag=flagged, excludedCategory=category))
        stubs.update(c.stubs)

# Every leaf is compared against one audited timing family, including any hidden
# fields. Only identifiers, resources and the weapon filter may differ.
base = inputs.spells[str(families[0]['leaf'])]
for f in families:
    leaf = inputs.spells[str(f['leaf'])]
    assert {k for k,v in leaf.items() if v != base[k]} <= {'changeHpPoint', 'changeMpPoint', 'triggerOnWepType'}

for effect in (7340000, 7342400, 7350000, 7352400):
    family = next(f for f in families if f['effect'] == effect)
    for copies in (1, 3):
        for hit_every in (None, 12, 1):
            continuous = hit_every is not None
            c = Hit(inputs)
            for _ in range(copies): c.insert(family['root'])
            c.qualify(); c.update(0)
            restores, pending = [], []
            for frame in range(360):
                for id in pending: c.insert(id)
                c.qualify(); c.update(1 / 60)
                hp, fp = c.hp(), c.fp(100)
                if any(hp + fp): restores.append(dict(frame=frame, hp=hp, fp=fp))
                pending = c.hit(family['weapon']) if frame == 0 or (continuous and frame <= 240 and frame % hit_every == 0) else []
            assert len(restores) == (4 if continuous else 1), (effect, copies, continuous, restores)
            assert all(r['hp'] == [0, -15 if effect < 7350000 else 0] and
                       r['fp'] == [2 if effect >= 7350000 else 0, 0] for r in restores)
            assert not any(n['id'] == family['leaf'] for n in c.nodes())
            checks['timing'].append(dict(effect=effect, copies=copies, continuous=continuous, hitEvery=hit_every, fps=60, restores=restores))
            stubs.update(c.stubs)

for copies in (1, 3):
    c = Hit(inputs)
    for _ in range(copies):
        for id in (8600110, 8600210): c.insert(id)
    c.qualify(); c.update(0)
    leaves = c.hit(weapon_ids[1])
    assert leaves == [8600111, 8600211]
    for id in leaves: c.insert(id)
    c.qualify(); c.update(1 / 60)
    hp, fp = c.hp(), c.fp(100)
    assert hp == [0, -15] and fp == [2, 0]
    checks['mixed'].append(dict(copies=copies, leaves=leaves, hp=hp, fp=fp))
    stubs.update(c.stubs)

# Audit all category-zero recovery leaves from the earlier timer study through
# real insertion. Calling 511700 directly does not establish reapplication.
old = json.loads((Path(__file__).resolve().parents[1] / 'data/effect-native-evidence.json').read_text())
for id in old['recoveryTiming']:
    row = inputs.spells[id]
    if row['spCategory'] != 0: continue
    c = Hit(inputs)
    c.insert(int(id)); c.qualify(); c.update(0)
    c.qualify(); c.update(.2)
    before = c.nodes()
    result = c.insert(int(id))
    after = c.nodes()
    assert result == 0xfffffffe and before == after and len(after) == 1
    c.qualify(); c.update(2)
    for _ in range(3):
        c.qualify(); c.update(1 / 60)
    assert c.nodes() == [], (id, c.nodes())
    c.insert(int(id)); c.qualify(); c.update(0)
    hp, fp = c.hp(), c.fp(100)
    assert hp == [row['changeHpRate'], row['changeHpPoint']]
    assert fp == [-row['changeMpPoint'], 0]
    checks['reapplication'].append(dict(leaf=int(id), rejectedResult=result, before=before, after=after,
                                        afterExpiryHp=hp, afterExpiryFp=fp))
    stubs.update(c.stubs)
assert len(checks['reapplication']) == 62

output = dict(schema=1, exeSha256=sha(inputs.raw), regulationSha256=inputs.x['hashes']['regulation.bin'],
    paramSha256=sha(inputs.param), weaponParamSha256=sha(weapon_raw), attackParamSha256=sha(attack_raw),
    families=families, checks=checks, stubs=sorted(stubs),
    nativeOnlyTypeFailures=[f['effect'] for f in families if not f['nativeTypeAccepted']],
    gameplayVerified=False, mmvDllsExecuted=False)
a.output.write_text(json.dumps(output, indent=2) + '\n')
print('PASS:', {k: len(v) for k,v in checks.items()}, 'weapon recovery checks')
