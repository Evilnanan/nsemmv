"""Shared pinned inputs and isolated native effect-container execution.

Only identity, allocation and data lookups are fixtures. Numeric/state routines
execute the original instructions. This module does not start the game.
"""
import hashlib
import json
import struct
from pathlib import Path

import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_CODE, UC_HOOK_MEM_UNMAPPED
from unicorn.x86_const import *

BASE, OBJ, STACK, STOP = 0x140000000, 0x10000000, 0x20000000, 0x30000000
sha = lambda b: hashlib.sha256(b).hexdigest()


class Inputs:
    def __init__(self, exe, extracted):
        self.raw = Path(exe).read_bytes()
        assert sha(self.raw) == '9545e8732919bb6a63904cb73223641b3c4f9a67869be5722612acca413e8b3a'
        self.pe = pefile.PE(data=self.raw, fast_load=True)
        assert self.pe.OPTIONAL_HEADER.ImageBase == BASE
        self.x = json.loads(Path(extracted).read_text())
        assert self.x['hashes']['regulation.bin'] == '3305ac374b4da1db440e2b6644bc2c3c0ae96b98df9627f1a0e7a2b06d265c06'
        self.param = Path(extracted).with_suffix('.SpEffectParam.param').read_bytes()
        self.rows = self.table(self.param, 0x400)
        self.spells = self.x['tables']['SpEffectParam']

    @staticmethod
    def table(raw, size):
        return {struct.unpack_from('<i', raw, 0x40 + i * 24)[0]: raw[off:off + size]
                for i in range(struct.unpack_from('<H', raw, 10)[0])
                for off in [struct.unpack_from('<Q', raw, 0x48 + i * 24)[0]]}


class Chain:
    def __init__(self, inputs):
        self.inputs = inputs
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
        assert BASE <= page < BASE + self.inputs.pe.OPTIONAL_HEADER.SizeOfImage, (hex(address), hex(u.reg_read(UC_X86_REG_RIP) - BASE))
        u.mem_map(page, 4096)
        u.mem_write(page, self.inputs.pe.get_data(page - BASE, 4096).ljust(4096, b'\0'))
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
            if id in self.inputs.rows and id not in self.lookup:
                self.lookup[id] = OBJ + 0x10000 + len(self.lookup) * 0x400
                assert len(self.lookup) < 64
                u.mem_write(self.lookup[id], self.inputs.rows[id])
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

    def invoke(self, rva, args, xmm=None, *, instruction_limit=200000):
        sp = STACK + 0x8008
        self.q(sp, STOP)
        self.u.reg_write(UC_X86_REG_RSP, sp)
        for i, value in enumerate(args[4:]):
            self.q(sp + 0x28 + i * 8, value & 0xffffffffffffffff)
        for reg, value in zip((UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8, UC_X86_REG_R9), args):
            self.u.reg_write(reg, value & 0xffffffffffffffff)
        for reg, value in (xmm or {}).items():
            self.u.reg_write(reg, int.from_bytes(struct.pack('<f', value), 'little'))
        self.u.emu_start(BASE + rva, STOP, count=instruction_limit)
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


