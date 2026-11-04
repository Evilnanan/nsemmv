"""Execute Ironeye weakpoint selection, queued application and lifetime updates.

Pinned PC instructions run in isolation. Actor/skeleton identity, PARAM lookup,
allocation and network transport are explicit fixtures; this is not gameplay.
"""
import argparse
import itertools
import json
import struct
from pathlib import Path
from unicorn.x86_const import *
from native_effect_runtime import BASE, OBJ, STACK, STOP, Chain, Inputs, sha

p = argparse.ArgumentParser(description=__doc__)
for name in ('exe', 'extracted', 'systems', 'parts', 'output'):
    p.add_argument(name, type=Path)
a = p.parse_args()
inputs = Inputs(a.exe, a.extracted)
systems, parts = (json.loads(x.read_text()) for x in (a.systems, a.parts))
for x in (systems, parts):
    assert x['hashes']['regulation.bin'] == inputs.x['hashes']['regulation.bin']
player_raw = a.systems.with_suffix('.PlayerCommonParam.param').read_bytes()
player = Inputs.table(player_raw, 0x140)[0]
parts_raw = a.parts.with_suffix('.ScratchedPartsParam.param').read_bytes()
part_rows = Inputs.table(parts_raw, 0x14)
for id, row in parts['tables']['ScratchedPartsParam'].items():
    assert struct.unpack('<ibbHfihh', part_rows[int(id)]) == (row['characterId'], row['unknown_1'],
        row['healthPercentDamage'], row['healthPercentTrigger'], row['damageTakenRate'],
        row['animationId'], row['dummyPolyId'], row['unknown_2'])
assert struct.unpack_from('<H', player, 0xc2)[0] == 17
assert struct.unpack_from('<i', player, 0x11c)[0] == 600000110
assert inputs.spells['7280000']['stateInfo'] == 2112
assert struct.unpack_from('<H', inputs.rows[7280000], 0x3a8)[0] == 22
MODULE, VICTIM, RESOURCE, HIT = OBJ+0x8000, OBJ+0x9000, OBJ+0xb000, OBJ+0xe000

class Weakpoint(Chain):
    def __init__(self, part=100000):
        super().__init__(inputs)
        self.part = part; self.branch = False; self.messages = []; self.freed = []
        self.q(OBJ+0x6190, OBJ)
        self.q(MODULE+8, VICTIM); self.q(OBJ+0x8808, VICTIM)
        self.q(VICTIM+0x1b8, OBJ+0xa000); self.q(OBJ+0xa000, RESOURCE)
        self.q(OBJ+0xa198, MODULE)
        self.u.mem_write(RESOURCE+0x140, struct.pack('<ii', 10000, 10000))
        self.u.mem_write(VICTIM+0x1b0, struct.pack('<i', parts['tables']['ScratchedPartsParam'][str(part)]['characterId']))
        self.u.mem_write(OBJ+0xc000, player)
        self.u.mem_write(OBJ+0xc800, part_rows[part])
        self.q(MODULE+0x20, OBJ+0xd000); self.q(MODULE+0x28, OBJ+0xd000); self.q(MODULE+0x30, OBJ+0xd400)
        self.u.mem_map(OBJ+0x40000, 0x20000); self.q(OBJ+0x574e8, OBJ+0x6000)
        for rva, value in ((0x3c0f0a8, OBJ+0x40000),(0x488974+0x3799554, OBJ+0xf100),
                           (0x488b52+0x378bf1e, 0)):
            page=(BASE+rva)&~4095
            try:self.u.mem_read(page,1)
            except:self.mapped(self.u,0,page,8,0,None)
            self.q(BASE+rva,value)
    def hook(self,u,address,size,user):
        pc=address-BASE
        def ret(value=0):
            u.reg_write(UC_X86_REG_RAX,value); sp=u.reg_read(UC_X86_REG_RSP)
            u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
        if self.branch and pc in (0x43dc17,0x43dc9a):u.reg_write(UC_X86_REG_RIP,STOP)
        elif pc==0xe81650:
            self.stubs.add('E81650 actual PlayerCommon PARAM lookup');ptr=u.reg_read(UC_X86_REG_RCX);self.q(ptr,OBJ+0xc000);ret(ptr)
        elif pc==0xe835a0:
            self.stubs.add('E835A0 actual ScratchedParts row lookup with explicit actor/part fixture')
            assert u.reg_read(UC_X86_REG_RDX)&0xffffffff==parts['tables']['ScratchedPartsParam'][str(self.part)]['characterId']
            assert u.reg_read(UC_X86_REG_R8)&255==0
            ptr=u.reg_read(UC_X86_REG_RCX);self.q(ptr,OBJ+0xc800);ret(ptr)
        elif pc==0x39bf80:
            self.stubs.add('39BF80 synthetic skeleton maps hit body to part 0');ret(0)
        elif pc==0x282970:
            self.stubs.add('282970 synthetic actor entity identity');ptr=u.reg_read(UC_X86_REG_RDX);self.q(ptr,1);ret(ptr)
        elif pc==0x519ef0:
            self.stubs.add('519EF0 authoritative local recipient; network ownership not simulated');ret(1)
        elif pc==0xdf24d0:
            self.stubs.add('DF24D0 outgoing network-message recorder; no network delivery')
            assert u.reg_read(UC_X86_REG_RDX)==0x7d
            self.messages.append(bytes(u.mem_read(u.reg_read(UC_X86_REG_R8),24)).hex());ret()
        elif pc==0x214e8d0 and u.reg_read(UC_X86_REG_RCX)==0x30:
            self.stubs.add('214E8D0 isolated weakpoint-node allocator; native constructor')
            self.allocated+=0x90;ret(self.allocated)
        elif address==STOP+0x108:
            self.freed.append(u.reg_read(UC_X86_REG_RDX));super().hook(u,address,size,user)
        elif pc==0x2695450 and u.reg_read(UC_X86_REG_R8)==0:
            self.stubs.add('2695450 zero-length vector erase memmove');ret(u.reg_read(UC_X86_REG_RCX))
        else:super().hook(u,address,size,user)
    def marks(self):
        ptr=struct.unpack('<Q',self.u.mem_read(MODULE+0x10,8))[0]; result=[]
        while ptr:
            raw=bytes(self.u.mem_read(ptr,0x30))
            result.append(dict(ptr=ptr,part=raw[0],durability=struct.unpack_from('<i',raw,4)[0],
                               maximum=struct.unpack_from('<i',raw,8)[0],remaining=struct.unpack_from('<f',raw,12)[0]))
            ptr=struct.unpack_from('<Q',raw,0x28)[0]
            assert len(result)<10
        return result
    def hit(self,attack=600000110,kind=1,flags=0,damage=1):
        self.u.mem_write(HIT,bytes(0x300));self.u.mem_write(HIT+0x40,struct.pack('<ii',attack,kind))
        self.u.mem_write(HIT+0x280,struct.pack('<i',damage));self.u.mem_write(HIT+0x2c1,bytes([flags]))
        for reg,val in ((UC_X86_REG_R12,OBJ+0x6000),(UC_X86_REG_R14,OBJ+0x8800),
                        (UC_X86_REG_RSI,HIT),(UC_X86_REG_RBP,STACK+0x6000)):
            self.u.reg_write(reg,val)
        self.branch=True;self.invoke(0x43dac8,[]);self.branch=False
        begin,end=struct.unpack('<QQ',self.u.mem_read(MODULE+0x20,16))
        queued=[struct.unpack('<BxH',self.u.mem_read(ptr,4)) for ptr in range(begin,end,4)]
        self.invoke(0x487be0,[MODULE]);assert struct.unpack('<Q',self.u.mem_read(MODULE+0x28,8))[0]==begin
        return queued
    def tick(self,dt):
        self.u.mem_write(OBJ+0xd808,struct.pack('<f',dt));self.invoke(0x488ad0,[MODULE,OBJ+0xd800])
    def copies(self,n):
        for _ in range(n):self.insert(7280000)
        self.qualify();self.update(0)

checks=dict(selection=[],lifetime=[],refresh=[],breakage=[],rows=[]);stubs=set()
for copies,attack,kind,flags in itertools.product((0,1,2,3),(600000110,600000109,-1),(0,1),(0,8)):
    c=Weakpoint();c.copies(copies);q=c.hit(attack,kind,flags)
    valid=attack==600000110 and kind==1 and flags==0
    expected=22 if copies else 17
    assert q==([(0,expected)] if valid else []),(copies,attack,kind,flags,q)
    assert len(c.nodes())==bool(copies)
    assert [r['remaining'] for r in c.marks()]==([expected] if valid else [])
    checks['selection'].append(dict(copies=copies,attack=attack,kind=kind,flags=flags,queued=q,marks=c.marks()))
    stubs.update(c.stubs)
for copies,fps in itertools.product((0,1,3),(30,60,120)):
    c=Weakpoint();c.copies(copies);c.hit();life=22 if copies else 17
    c.tick(0);assert c.marks()[0]['remaining']==life
    for frame in range(1,(life+1)*fps):
        c.tick(1/fps)
        if not c.marks():break
    assert abs(frame/fps-life)<=1.01/fps,(copies,fps,frame)
    assert len(c.freed)==1
    checks['lifetime'].append(dict(copies=copies,fps=fps,expiresFrame=frame));stubs.update(c.stubs)
for initial,new,elapsed in itertools.product((17,22),(17,22),(0,3,10,16)):
    c=Weakpoint();c.invoke(0x4886a0,[MODULE,0,initial]);c.tick(elapsed)
    old=c.marks()[0];c.u.mem_write(old['ptr']+4,struct.pack('<i',123))
    c.invoke(0x4886a0,[MODULE,0,new]);result=c.marks()
    assert len(result)==1 and result[0]['remaining']==max(initial-elapsed,new) and result[0]['durability']==123
    checks['refresh'].append(dict(initial=initial,new=new,elapsed=elapsed,remaining=result[0]['remaining'],durability=result[0]['durability']))
    stubs.update(c.stubs)
# Hit-time gate refuses a new mark when that hit would already exhaust existing durability.
for copies,damage in itertools.product((0,1),(0,2999,3000,3001)):
    c=Weakpoint();c.copies(copies);c.hit();c.tick(3);before=c.marks()[0];q=c.hit(damage=damage)
    assert bool(q)==(damage<3000)
    if damage>=3000:assert c.marks()[0]['remaining']==before['remaining']
    c.u.mem_write(before['ptr']+4,bytes(4));c.tick(0);assert not c.marks()
    checks['breakage'].append(dict(copies=copies,damage=damage,queued=q,removedAfterZeroDurability=True));stubs.update(c.stubs)
for id,row in parts['tables']['ScratchedPartsParam'].items():
    if row['unknown_1']!=0 or row['healthPercentTrigger']<=0:continue
    c=Weakpoint(int(id));c.invoke(0x4886a0,[MODULE,0,22]);marks=c.marks()
    expected=int(10000*(part_rows[int(id)][6]/100))
    assert marks[0]['durability']==expected and marks[0]['remaining']==22
    c.tick(22.125);assert not c.marks()
    checks['rows'].append(dict(id=int(id),durability=expected,removedAfter=22.125));stubs.update(c.stubs)
output=dict(schema=1,exeSha256=sha(inputs.raw),regulationSha256=inputs.x['hashes']['regulation.bin'],
            paramSha256=sha(inputs.param),playerCommonParamSha256=sha(player_raw),scratchedPartsParamSha256=sha(parts_raw),
            root=7280000,baseDuration=17,extendedDuration=22,checks=checks,
            native=dict(hitBranch='43DAC8..43DC17',attackGate='488590',localPlayer='3D4180',duration='507B30',
                        queue='488840',applyQueue='487BE0',apply='4886A0',tick='488AD0',wouldBreak='4883C0'),
            stubs=sorted(stubs|{'isolated hit-consumer subrange; no full attack/damage construction, animation, death, reload or network simulation',
                               'visual-manager singleton absent; duration and removal execute native instructions'}),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS:',{k:len(v) for k,v in checks.items()})
