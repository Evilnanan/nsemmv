"""Pinned poison/bleed recipient processing with explicit resistance inputs.

Insertion, native immunity and accumulation, rejection removal, eligibility,
HP packets and timers execute original instructions. Hit delivery, resistance
inputs and missing growth assets are fixtures, not a running game.
"""
import struct
from unicorn.x86_const import *
from native_effect_runtime import BASE, OBJ, STOP, Chain

class Ailment(Chain):
    def __init__(self, inputs, kind, maximum=500, immune=False):
        super().__init__(inputs)
        assert kind in (0, 2)
        self.kind = kind
        self.q(OBJ + 0x6190, OBJ)
        self.q(OBJ + 0x63a0, STOP + 0x200)  # owner virtual +1a0: no growth params
        self.q(OBJ + 0x6410, STOP + 0x201)  # owner virtual +210: no damage exclusion
        self.q(OBJ + 0x9008, OBJ + 0x6000)  # ailment controller owner
        self.q(OBJ + 0xe008, OBJ + 0x6000)  # HP data owner
        self.q(OBJ + 0x61b8, OBJ + 0xf000)
        self.q(OBJ + 0xf008, OBJ + 0xf400)
        # Queue/debug-singleton identities only. Original branch predicates run.
        for address, value in [(BASE + 0x42d85f + 7 + 0x37f4662, OBJ + 0xe800),
                               (BASE + 0x427bfa + 8 + 0x37e7736, OBJ + 0xf800)]:
            self.mapped(self.u, 0, address, 8, 0, None)
            self.q(address, value)
        for off in (0x9010 + kind * 4, 0x902c + kind * 4):
            self.u.mem_write(OBJ + off, struct.pack('<i', maximum))
        if immune: self.insert(9642)
        self.qualify(); self.update(0)
        self.stubs.add('empty actor/HP/ailment objects; neutral death-protection flags and supplied starting resistance')

    def hook(self, u, address, size, user):
        pc = address - BASE
        def finish(value=0):
            u.reg_write(UC_X86_REG_RAX, value)
            sp = u.reg_read(UC_X86_REG_RSP)
            u.reg_write(UC_X86_REG_RIP, struct.unpack('<Q', u.mem_read(sp, 8))[0])
            u.reg_write(UC_X86_REG_RSP, sp + 8)
        if address in (STOP + 0x200, STOP + 0x201):
            self.stubs.add('owner virtual +1a0 no resistance-growth params; +210 no damage exclusion')
            finish()
        elif pc == 0x6ada30:
            self.stubs.add('6ADA30 ordinary resource-setter context')
            finish()
        elif pc == 0x3d4180:
            self.stubs.add('3D4180 player identity')
            finish(1)
        elif pc in (0x4e78a0, 0x4e78c0, 0xdf24d0):
            self.stubs.add(hex(pc) + ' network-message identity/transport only; no remote delivery')
            finish()
        else:
            super().hook(u, address, size, user)

    def apply(self, effect, scale=1):
        # Mirror 3DB410: insert first, then run status processing. A true return
        # removes that exact node immediately, without expiry replacement.
        index = self.insert(effect)
        if index >= 0x80000000:return "existing"
        self.q(OBJ + 0x9800, self.lookup[effect])
        self.u.mem_write(OBJ + 0x9900 + self.kind * 4, struct.pack('<f', scale))
        self.u.mem_write(OBJ + 0x9938, struct.pack('<f', 1))
        rejected = bool(self.invoke(0x42d110, [OBJ + 0x9000, OBJ + 0x9800, OBJ + 0x9900]) & 255)
        if rejected: self.invoke(0x505280, [OBJ, index])
        return rejected

    def remaining(self):
        return struct.unpack('<i', self.u.mem_read(OBJ + 0x9010 + self.kind * 4, 4))[0]

    def hp_packet(self, maximum):
        # No physical-owner invulnerability/remote state while aggregating. The
        # actual effect list and native ailment damage multipliers remain live.
        self.q(OBJ + 0x10, 0)
        self.invoke(0x506ec0, [OBJ, maximum, OBJ + 0x800, OBJ + 0x808, OBJ + 0x820, 0])
        self.q(OBJ + 0x10, OBJ + 0x6000)
        return list(struct.unpack('<7i', self.u.mem_read(OBJ + 0x820, 28)))


