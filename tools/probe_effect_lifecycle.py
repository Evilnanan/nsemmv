"""Execute complete reviewed effect chains in pinned PC code.

The owner identity, allocator, PARAM lookup and delivery queue are fixtures.
Insertion, eligibility, damage expiry, timer/cycle/replacement dispatch, unlinking
and numeric getters run unchanged. This is not gameplay or network validation.
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
p.add_argument('extracted', type=Path)
p.add_argument('output', type=Path)
a = p.parse_args()
raw = a.exe.read_bytes()
sha = lambda b: hashlib.sha256(b).hexdigest()
assert sha(raw) == '9545e8732919bb6a63904cb73223641b3c4f9a67869be5722612acca413e8b3a'
pe = pefile.PE(data=raw, fast_load=True)
x = json.loads(a.extracted.read_text())
assert x['hashes']['regulation.bin'] == '3305ac374b4da1db440e2b6644bc2c3c0ae96b98df9627f1a0e7a2b06d265c06'
param = a.extracted.with_suffix('.SpEffectParam.param').read_bytes()
rows = {struct.unpack_from('<i', param, 0x40 + i * 24)[0]: param[off:off + 0x400]
        for i in range(struct.unpack_from('<H', param, 10)[0])
        for off in [struct.unpack_from('<Q', param, 0x48 + i * 24)[0]]}
BASE, OBJ, STACK, STOP = pe.OPTIONAL_HEADER.ImageBase, 0x10000000, 0x20000000, 0x30000000
spells = x['tables']['SpEffectParam']


class Chain:
    def __init__(self):
        self.u = Uc(UC_ARCH_X86, UC_MODE_64)
        self.u.mem_map(OBJ, 0x40000)
        self.u.mem_map(STACK, 0x10000)
        self.u.mem_map(STOP, 0x1000)
        self.lookup = {}
        self.allocated = OBJ + 0x20000
        self.emitted = []
        self.stubs = set()
        self.q(OBJ + 0x10, OBJ + 0x6000)
        self.q(OBJ + 0x6000, OBJ + 0x6200)
        self.q(OBJ + 0x6348, STOP + 0x100)
        self.q(OBJ + 0x7000, OBJ + 0x7100)
        self.q(OBJ + 0x7168, STOP + 0x108)
        self.u.mem_write(OBJ + 0xa00, struct.pack('<4f', 1, 1, 1, 1))
        self.u.hook_add(UC_HOOK_MEM_UNMAPPED, self.mapped)
        self.u.hook_add(UC_HOOK_CODE, self.hook)

    def q(self, address, value):
        self.u.mem_write(address, struct.pack('<Q', value))

    def mapped(self, u, access, address, size, value, user):
        page = address & ~4095
        assert BASE <= page < BASE + pe.OPTIONAL_HEADER.SizeOfImage, (hex(address), hex(u.reg_read(UC_X86_REG_RIP) - BASE))
        u.mem_map(page, 4096)
        u.mem_write(page, pe.get_data(page - BASE, 4096).ljust(4096, b'\0'))
        return True

    def hook(self, u, address, size, user):
        pc = address - BASE
        def finish(value=0):
            u.reg_write(UC_X86_REG_RAX, value)
            sp = u.reg_read(UC_X86_REG_RSP)
            u.reg_write(UC_X86_REG_RIP, struct.unpack('<Q', u.mem_read(sp, 8))[0])
            u.reg_write(UC_X86_REG_RSP, sp + 8)
        if pc == 0x214e8d0:
            self.stubs.add('214E8D0 isolated 0x88-byte allocation; native constructor and insertion')
            assert u.reg_read(UC_X86_REG_RCX) == 0x88
            self.allocated += 0x90
            assert self.allocated < OBJ + 0x40000
            finish(self.allocated)
        elif pc == 0xea17e0:
            self.stubs.add('EA17E0 actual SpEffect PARAM lookup')
            id = u.reg_read(UC_X86_REG_RDX) & 0xffffffff
            if id in rows and id not in self.lookup:
                self.lookup[id] = OBJ + 0x10000 + len(self.lookup) * 0x400
                assert len(self.lookup) < 64
                u.mem_write(self.lookup[id], rows[id])
            wrapper = u.reg_read(UC_X86_REG_RCX)
            u.mem_write(wrapper, struct.pack('<QI', self.lookup.get(id, 0), id))
            finish(wrapper)
        elif pc == 0xf61390:
            self.stubs.add('F61390 isolated allocator owner')
            finish(OBJ + 0x7000)
        elif address in (STOP + 0x100, STOP + 0x108):
            self.stubs.add('owner vtable +148 false; allocator +68 free recorder')
            finish()
        elif pc == 0x3c7fd0:
            self.stubs.add('3C7FD0 grant recorder; queue delivered on next simulation frame')
            assert u.reg_read(UC_X86_REG_RCX) == OBJ + 0x6000
            self.emitted.append(u.reg_read(UC_X86_REG_RDX) & 0xffffffff)
            finish()
        elif pc == 0xe6d630:
            self.stubs.add('E6D630 absent attack PARAM lookup for untagged attack getter')
            finish(u.reg_read(UC_X86_REG_RCX))

    def invoke(self, rva, args, xmm=None):
        sp = STACK + 0x8008
        self.q(sp, STOP)
        self.u.reg_write(UC_X86_REG_RSP, sp)
        for i, value in enumerate(args[4:]):
            self.q(sp + 0x28 + i * 8, value & 0xffffffffffffffff)
        for reg, value in zip((UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8, UC_X86_REG_R9), args):
            self.u.reg_write(reg, value & 0xffffffffffffffff)
        for reg, value in (xmm or {}).items():
            self.u.reg_write(reg, int.from_bytes(struct.pack('<f', value), 'little'))
        self.u.emu_start(BASE + rva, STOP, count=200000)
        assert self.u.reg_read(UC_X86_REG_RIP) == STOP, hex(rva)
        return self.u.reg_read(UC_X86_REG_RAX)

    def insert(self, id):
        return self.invoke(0x50d060, [OBJ, id, OBJ + 0xa00, -1, 0, 0x3f800000, 0, 0, 16]) & 0xffffffff

    def qualify(self):
        self.invoke(0x5057d0, [OBJ, 0, 0], {UC_X86_REG_XMM1: 1})

    def update(self, dt):
        self.invoke(0x50acd0, [OBJ, 0, 0], {UC_X86_REG_XMM1: dt})

    def nodes(self):
        node = struct.unpack('<Q', self.u.mem_read(OBJ + 8, 8))[0]
        result = []
        while node:
            assert len(result) < 200
            id = struct.unpack('<i', self.u.mem_read(node + 8, 4))[0]
            life = struct.unpack('<f', self.u.mem_read(node + 0x4c, 4))[0]
            flags = struct.unpack('<I', self.u.mem_read(node + 0x68, 4))[0]
            result.append(dict(id=id, lifetime=round(life, 6), flags=flags))
            node = struct.unpack('<Q', self.u.mem_read(node + 0x38, 8))[0]
        return result

    def attack(self, kind=0):
        self.u.mem_write(OBJ + 0x808, struct.pack('<iiB', 40000, 1, kind))
        self.invoke(0x502830, [OBJ, OBJ + 0x800, -1, -1])
        return [struct.unpack('<f', self.u.mem_read(OBJ + 0x800 + off, 4))[0]
                for off in (0x90, 0xa4, 0xa8, 0xac, 0xb0)]

    def fp(self, maximum):
        self.invoke(0x507460, [OBJ, maximum, OBJ + 0x800])
        return list(struct.unpack('<2i', self.u.mem_read(OBJ + 0x800, 8)))


checks = {'revenant': [], 'fp': [], 'duchess': [], 'attack': []}
all_stubs = set()
for id in range(7220300, 7220307):
    row = spells[str(id)]
    assert struct.unpack_from('<f', rows[id], 0xa4)[0] == row['changeMpRate']
assert spells['7220305']['physicsAttackRate'] == spells['7220305']['magicAttackRate']
assert spells['7220305']['effectEndurance'] == 20

scenarios = [
    ('no-equipment', [60, 120, 124], 17, 1, 0),
    ('no-damage', [], 17, 1, 1),
    ('zero-damage', [60, 120, 124], 17, 0, 1),
    ('paired-hit', [60, 61], 3, 1, 1),
    ('rearm-boundary', [120, 124], 3, 1, 1),
    ('dense-hits', list(range(60, 900)), 17, 1, 1),
    ('duplicate-equipment', [120, 124], 3, 1, 3),
    ('independent-expiry', [60, 300], 23, 1, 1),
]
for name, hits, seconds, damage, copies in scenarios:
    c = Chain()
    for _ in range(copies): c.insert(7220300)
    c.qualify(); c.update(0)
    assert [n['id'] for n in c.nodes()] == ([7220300] if copies else [])
    c.insert(7220301)
    c.qualify(); c.update(0)
    grants, restores, attack_changes = [], [], []
    previous_rate = 1
    for frame in range(seconds * 60):
        incoming, c.emitted = c.emitted, []
        for id in incoming: c.insert(id)
        if incoming: grants.append(dict(frame=frame, ids=incoming))
        c.qualify()
        if frame in hits:
            c.invoke(0x504d30, [OBJ, 0, 0, 0, 0], {UC_X86_REG_XMM1: damage})
        c.update(1 / 60)
        amount, flask = c.fp(1000)
        assert flask == 0
        if amount:
            assert amount == 100
            restores.append(dict(frame=frame, amount=amount))
        rates = c.attack()
        count = sum(n['id'] == 7220305 and not n['flags'] & 0x800c0003 for n in c.nodes())
        assert all(math.isclose(v, 1.15 ** count, rel_tol=1e-6) for v in rates)
        if not math.isclose(rates[0], previous_rate, rel_tol=1e-6):
            attack_changes.append(dict(frame=frame, count=count, rate=rates[0]))
            previous_rate = rates[0]
    expected = {'no-equipment': 0, 'no-damage': 1, 'zero-damage': 1, 'paired-hit': 1, 'rearm-boundary': 2,
                'dense-hits': 8, 'duplicate-equipment': 2, 'independent-expiry': 3}[name]
    assert len(restores) == expected
    if name in ('no-damage', 'zero-damage'): assert restores[0]['frame'] > 900
    if name in ('rearm-boundary', 'duplicate-equipment'): assert restores[1]['frame'] - restores[0]['frame'] < 10
    if name == 'independent-expiry': assert [v['count'] for v in attack_changes] == [1, 2, 3, 2]
    checks['revenant'].append(dict(name=name, fps=60, hits=hits, damage=damage, equipmentCopies=copies,
        seconds=seconds, grants=grants, restores=restores, attackChanges=attack_changes, finalNodes=c.nodes()))
    all_stubs.update(c.stubs)

for special in (0, 1):
    for name, kills, seconds, copies in [
        ('no-equipment', [60], 3, 0),
        ('one-kill', [60], 3, 1), ('repeat-kill', [60, 61], 3, 1),
        ('duplicate-equipment', [60, 61], 3, 3), ('after-window', [780], 14, 1),
        ('independent-expiry', [60, 300], 33, 1),
    ]:
        c = Chain()
        for _ in range(copies): c.insert(7032700)
        c.qualify(); c.update(0)
        assert [n['id'] for n in c.nodes()] == ([7032700] if copies else [])
        c.insert(7032701)
        c.qualify(); c.update(0)
        grants, attack_changes = [], []
        previous_rate = 1
        leaf = 7032706 if special else 7032704
        for frame in range(seconds * 60):
            incoming, c.emitted = c.emitted, []
            for id in incoming: c.insert(id)
            if incoming: grants.append(dict(frame=frame, ids=incoming))
            c.qualify()
            if frame in kills: c.invoke(0x50a150, [OBJ, OBJ + 0x6000, special])
            c.update(1 / 60)
            count = sum(n['id'] == leaf and not n['flags'] & 0x800c0003 for n in c.nodes())
            rates = c.attack()
            assert all(math.isclose(v, (1.05 if special else 1.15) ** count, rel_tol=1e-6) for v in rates)
            if not math.isclose(rates[0], previous_rate, rel_tol=1e-6):
                attack_changes.append(dict(frame=frame, count=count, rate=rates[0]))
                previous_rate = rates[0]
        expected = {'no-equipment': [], 'one-kill': [1], 'repeat-kill': [1, 2], 'duplicate-equipment': [1, 2],
                    'after-window': [], 'independent-expiry': [1, 2, 1]}[name]
        assert [v['count'] for v in attack_changes] == expected
        checks['duchess'].append(dict(name=name, fps=60, kills=kills, special=special, equipmentCopies=copies,
            seconds=seconds, grants=grants, attackChanges=attack_changes, finalNodes=c.nodes()))
        all_stubs.update(c.stubs)

for leaf in (7220305, 7032704, 7032706):
    c = Chain()
    c.insert(leaf); c.qualify(); c.update(0)
    for kind in range(6):
        values = c.attack(kind)
        expected = spells[str(leaf)]['physicsAttackRate'] if kind < 5 else 1
        assert all(math.isclose(v, expected, abs_tol=1e-6) for v in values)
        checks['attack'].append(dict(leaf=leaf, kind=kind, rates=values))
    all_stubs.update(c.stubs)

for copies in (1, 2, 3):
    for maximum in (0, 1, 99, 100, 137, 1000):
        c = Chain()
        for _ in range(copies): c.insert(7220306)
        c.qualify(); c.update(0)
        value = c.fp(maximum)
        assert value == [math.trunc(maximum * copies * .1), 0]
        c.qualify(); c.update(1 / 60)
        assert c.fp(maximum) == [0, 0]
        checks['fp'].append(dict(copies=copies, maximum=maximum, first=value, nextFrame=[0, 0]))
        all_stubs.update(c.stubs)

a.output.write_text(json.dumps(dict(schema=1, exeSha256=sha(raw), regulationSha256=x['hashes']['regulation.bin'],
    paramSha256=sha(param), checks=checks, stubs=sorted(all_stubs), gameplayVerified=False), indent=2) + '\n')
print('PASS:', {k: len(v) for k, v in checks.items()})
