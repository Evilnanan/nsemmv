"""Pinned native Type 1 animation event dispatch with explicit attack-request sinks.

The caller supplies actual Behavior and equipped-weapon PARAM bytes. Actor
identity and hit construction remain fixtures; state gates and resolution run
original instructions. This helper does not simulate collision or gameplay.
"""
import struct
from unicorn.x86_const import *
from native_effect_runtime import BASE, OBJ, STOP, Chain

class Type1Attack(Chain):
    def __init__(self, inputs, behaviors, weapons, allowed):
        super().__init__(inputs);self.requests=[]
        self.behaviors=behaviors;self.weapons=weapons;self.allowed=allowed
        for off,ptr in ((0x118,STOP+0x201),(0x190,STOP+0x200),(0x260,STOP+0x200),
                        (0x328,BASE+0x668b30),(0x320,STOP+0x201),(0x250,STOP+0x202),
                        (0x28,STOP+0x201),(0x178,STOP+0x200)):
            self.q(OBJ+0x6200+off,ptr)
        self.q(OBJ+0x6190,OBJ);self.q(OBJ+0x61b8,OBJ+0x9000);self.q(OBJ+0x9098,OBJ+0x9800)
    def hook(self,u,address,size,user):
        pc=address-BASE
        def ret(value=0):
            u.reg_write(UC_X86_REG_RAX,value);sp=u.reg_read(UC_X86_REG_RSP)
            u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
        if address in (STOP+0x200,STOP+0x201,STOP+0x202):
            self.stubs.add('synthetic animation-owner virtuals and equipped weapon 1000')
            ret({STOP+0x200:0,STOP+0x201:1,STOP+0x202:1000}[address])
        elif pc in (0x4d1b20,0x3d4180,0x3d4c10,0xea9a60,0xea76f0,0x66b2d0):
            self.stubs.add(hex(pc)+' isolated actor context / hand identity');ret()
        elif pc==0x3ced90:
            self.stubs.add('3CED90 isolated animation-owner context');ret(OBJ+0xe800)
        elif pc==0xea7fc0:
            self.stubs.add('EA7FC0 actual equipped-weapon row lookup');id=u.reg_read(UC_X86_REG_RDX)&0xffffffff
            u.mem_write(OBJ+0xe000,self.weapons[id]);u.mem_write(u.reg_read(UC_X86_REG_RCX),struct.pack('<IIQ',id,0,OBJ+0xe000));ret()
        elif pc==0xe6fcb0:
            self.stubs.add('E6FCB0 actual Behavior row lookup');id=u.reg_read(UC_X86_REG_RDX)&0xffffffff
            assert id in self.allowed
            u.mem_write(OBJ+0xe400,self.behaviors[id]);self.q(u.reg_read(UC_X86_REG_RCX)+8,OBJ+0xe400);ret()
        elif pc==0x4341d0:
            self.stubs.add('4341D0 attack-instance request recorder; collision and attack construction are not simulated')
            sp=u.reg_read(UC_X86_REG_RSP)
            self.requests.append(dict(behavior=u.reg_read(UC_X86_REG_R8),kind=u.reg_read(UC_X86_REG_R9),
                                      slot=struct.unpack('<i',u.mem_read(sp+0x28,4))[0],
                                      hand=struct.unpack('<i',u.mem_read(sp+0x30,4))[0],
                                      elapsed=struct.unpack('<f',u.mem_read(sp+0x50,4))[0]))
            ptr=u.reg_read(UC_X86_REG_RDX);u.mem_write(ptr,bytes(16));ret(ptr)
        elif pc==0x415ea0:
            self.stubs.add('415EA0 attack animation-reference sink after request');ret()
        else:super().hook(u,address,size,user)
    def event(self,event,active):
        self.q(OBJ+0xd018,OBJ+0x6000);self.q(OBJ+0xd108,OBJ+0xd200);self.q(OBJ+0xd120,OBJ+0xd300)
        self.u.mem_write(OBJ+0xd100,struct.pack('<I',1));self.u.mem_write(OBJ+0xd118,bytes([active]))
        self.u.mem_write(OBJ+0xd110,struct.pack('<f',event['StartTime']));self.u.mem_write(OBJ+0xd300,struct.pack('<f',event['EndTime']))
        self.u.mem_write(OBJ+0xd200,bytes.fromhex(event['hex']));self.invoke(0x414820,[OBJ+0xd000,OBJ+0xd100])

