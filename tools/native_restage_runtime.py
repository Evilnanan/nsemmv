"""Pinned Restage application and history-consumption entry points.

History inputs, actor context and output sinks are explicit fixtures; no full
history recorder, collisions or multiplayer simulation.
"""
import struct
from unicorn.x86_const import *
from native_effect_runtime import BASE, OBJ, STACK, STOP, Chain

MODULE,VICTIM,HIT,RESOURCE,QUEUE=(OBJ+i for i in (0x9000,0xa000,0xb000,0xb800,0xc800))
f32=lambda x:struct.unpack('<f',struct.pack('<f',x))[0]

class Restage(Chain):
    def __init__(self, inputs, player, weapons, behaviors):
        self.inputs=inputs;self.weapons=weapons;self.behaviors=behaviors
        super().__init__(inputs)
        self.requests=[];self.heals=[];self.poise=[];self.statuses=[];self.phase=None
        for off,ptr in ((0x118,STOP+0x201),(0x190,STOP+0x200),(0x260,STOP+0x200),
                        (0x328,BASE+0x668b30),(0x320,STOP+0x201),(0x250,STOP+0x202),
                        (0x28,STOP+0x201),(0x178,STOP+0x200)):
            self.q(OBJ+0x6200+off,ptr)
        self.q(OBJ+0x6190,OBJ)
        self.q(MODULE+8,VICTIM);self.q(VICTIM+0x1b8,OBJ+0xa800)
        self.q(OBJ+0xa800,RESOURCE);self.q(OBJ+0xa898,HIT);self.q(OBJ+0xa958,MODULE)
        self.q(HIT,OBJ+0xbc00);self.q(OBJ+0xbc98,STOP+0x210);self.q(HIT+8,VICTIM)
        self.u.mem_write(RESOURCE+0x140,struct.pack('<i',100000))
        self.u.mem_write(OBJ+0xc000,player)
        self.q(QUEUE+0x20,OBJ+0xd000);self.q(QUEUE+0x28,OBJ+0xd000);self.q(QUEUE+0x30,OBJ+0xd400)
        for rva,ptr in ((0x44a3e2+0x37c93be,QUEUE),(0x430fb3+0x37de0f5,OBJ+0xf000)):
            page=(BASE+rva)&~4095
            try:self.u.mem_read(page,1)
            except:self.mapped(self.u,0,page,8,0,None)
            self.q(BASE+rva,ptr)
    def hook(self,u,address,size,user):
        pc=address-BASE
        def ret(value=0):
            u.reg_write(UC_X86_REG_RAX,value);sp=u.reg_read(UC_X86_REG_RSP)
            u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
        if (self.phase=='apply' and pc==0x3ce5e9) or (self.phase=='consume' and pc==0x449c6d):
            u.reg_write(UC_X86_REG_RIP,STOP)
        elif address in (STOP+0x200,STOP+0x201,STOP+0x202):
            self.stubs.add('synthetic animation-owner virtuals and equipped weapon 1000')
            ret({STOP+0x200:0,STOP+0x201:1,STOP+0x202:1000}[address])
        elif pc in (0x4d1b20,0x3d4180,0x3d4c10,0xea9a60,0xea76f0,0x66b2d0,0x27d0640):
            self.stubs.add(hex(pc)+' isolated animation-owner context / hand identity / empty reference list');ret()
        elif pc==0x3ced90:
            self.stubs.add('3CED90 isolated animation-owner context');ret(OBJ+0xe800)
        elif pc==0xea7fc0:
            self.stubs.add('EA7FC0 actual equipped-weapon row lookup');id=u.reg_read(UC_X86_REG_RDX)&0xffffffff
            u.mem_write(OBJ+0xe000,self.weapons[id]);u.mem_write(u.reg_read(UC_X86_REG_RCX),struct.pack('<IIQ',id,0,OBJ+0xe000));ret()
        elif pc==0xe6fcb0:
            self.stubs.add('E6FCB0 actual Behavior row lookup');id=u.reg_read(UC_X86_REG_RDX)&0xffffffff
            assert id in (600000150,600000185)
            u.mem_write(OBJ+0xe400,self.behaviors[id]);self.q(u.reg_read(UC_X86_REG_RCX)+8,OBJ+0xe400);ret()
        elif pc==0x3975d0:
            self.stubs.add('3975D0 Behavior request recorder; animation dispatch remains native')
            self.requests.append(u.reg_read(UC_X86_REG_RDX));ret(1)
        elif pc==0xe81650:
            self.stubs.add('E81650 actual PlayerCommon PARAM lookup');ptr=u.reg_read(UC_X86_REG_RCX);self.q(ptr,OBJ+0xc000);ret(ptr)
        elif pc in (0x216b9a0,0x216ba10):
            self.stubs.add('single-thread fixture mutex lock/unlock');ret()
        elif pc==0x282970:
            self.stubs.add('282970 synthetic actor entity identity');ptr=u.reg_read(UC_X86_REG_RDX);self.q(ptr,1);ret(ptr)
        elif pc==0x519ef0:
            self.stubs.add('519EF0 authoritative local recipient; no network simulation');ret(1)
        elif pc==0x426130:
            self.stubs.add('426130 HP delta recorder; final caps/modifiers are not simulated')
            self.heals.append(struct.unpack('<i',struct.pack('<I',u.reg_read(UC_X86_REG_RDX)&0xffffffff))[0]);ret()
        elif pc==0x43ced0:
            self.stubs.add('43CED0 damage notification sink after recorded HP request');ret()
        elif pc==0x48de50:
            self.stubs.add('48DE50 poise request recorder; final stagger processing not simulated')
            self.poise.append(struct.unpack('<f',u.reg_read(UC_X86_REG_XMM1).to_bytes(16,'little')[:4])[0]);ret()
        elif pc==0x3c7fd0 and self.phase=='consume':
            self.stubs.add('3C7FD0 status-effect request recorder')
            self.statuses.append(u.reg_read(UC_X86_REG_RDX));ret()
        elif address==STOP+0x210:
            self.stubs.add('synthetic absent linked actor identity; secondary replay target not simulated')
            ptr=u.reg_read(UC_X86_REG_RDX);u.mem_write(ptr,struct.pack('<i',-1));ret(ptr)
        else:super().hook(u,address,size,user)
    def boost(self,copies):
        for _ in range(copies):self.insert(7290000)
        self.qualify();self.update(0)
        return self.invoke(0x508e20,[OBJ,2271])&255
    def dispatch(self,event,active):
        self.requests.clear();self.q(OBJ+0x8018,OBJ+0x6000);self.q(OBJ+0x8108,OBJ+0x8200)
        self.u.mem_write(OBJ+0x8118,bytes([active]));self.u.mem_write(OBJ+0x811a,struct.pack('<H',0x27))
        self.q(OBJ+0x8120,OBJ+0x8300);self.u.mem_write(OBJ+0x8200,bytes.fromhex(event['hex']))
        self.invoke(0x40cd80,[OBJ+0x8000,OBJ+0x8100]);return self.requests[:]
    def apply(self,leaf):
        self.phase='apply';self.u.mem_write(OBJ+0xf400,self.inputs.rows[leaf])
        self.u.reg_write(UC_X86_REG_RBX,VICTIM)
        self.invoke(0x3ce5b3,[OBJ+0xf400]);self.phase=None
        return struct.unpack('<f',self.u.mem_read(MODULE+0x3c,4))[0]
    def consume(self,records):
        self.phase='consume';self.heals.clear();self.poise.clear();self.statuses.clear()
        ptr=OBJ+0xe000;end=ptr+20*len(records)
        for i,(damage,poise,flags) in enumerate(records):
            self.u.mem_write(ptr+i*20,struct.pack('<ifB3xii',damage,poise,flags,-1,-1))
        bp=STACK+0x6000;self.q(bp-0x80,end)
        for reg,val in ((UC_X86_REG_RDI,MODULE),(UC_X86_REG_RBX,ptr),(UC_X86_REG_R9,end),
                        (UC_X86_REG_R13,0),(UC_X86_REG_RBP,bp)):
            self.u.reg_write(reg,val)
        self.invoke(0x449aac,[],{UC_X86_REG_XMM7:0});self.phase=None
        return dict(hp=self.heals[:],poise=self.poise[:],statuses=self.statuses[:])

