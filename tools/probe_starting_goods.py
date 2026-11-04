"""Decode starting goods, Scholar extra grants and shared pouch capacity.

Uses pinned original PC instructions and MMV PARAM rows. Synthetic item handles,
PARAM lookups and memory allocators replace external managers. Inventory slot
allocation, stacking quantities, caps, removal, pouch accounting and the starting
routine itself execute native code. General pickup UI/auto-equip is bypassed;
this is not an in-game or network test and does not promise overflow recovery.
"""
import argparse,json,struct
from pathlib import Path
from native_effect_runtime import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','systems','output'):p.add_argument(name,type=Path)
a=p.parse_args()
x=Inputs(a.exe,a.extracted)
systems=json.loads(a.systems.read_text())
assert systems['hashes']['regulation.bin']==x.x['hashes']['regulation.bin']
graw=a.extracted.with_suffix('.EquipParamGoods.param').read_bytes(); goods=Inputs.table(graw,0xe0)
praw=a.systems.with_suffix('.PlayerCommonParam.param').read_bytes(); poff=struct.unpack_from('<Q',praw,0x48)[0]; prow=praw[poff:poff+0xc0]
assert (prow[14],prow[15])==(4,8)
assert (systems['tables']['PlayerCommonParam']['0']['defaultNumberOfItemSlots'],systems['tables']['PlayerCommonParam']['0']['maxNumberOfItemSlots'])==(4,8)
class StartingGoods(Chain):
    def __init__(self,hero=0):
        super().__init__(x);self.hero=hero;self.glook={};self.grants=[];self.removed=[];self.vecptr=OBJ+0x36000
        self.parent=OBJ+0xd000;self.eq=self.parent+0x1d8;self.inv=self.eq+0x1c8
        self.q(OBJ+0x6190,OBJ);self.q(OBJ+0x65a0,self.parent);self.q(self.eq+0x2f8,self.parent)
        self.q(OBJ+0x6200+0x178,STOP+0x200);self.q(OBJ+0x7118,STOP+0x201);self.q(OBJ+0x7150,STOP+0x202)
        self.u.mem_write(self.eq+8,b'\xff'*(32*4))
        for i in range(18):self.u.mem_write(self.eq+0x250+i*8,b'\xff'*8)
        self.w(self.eq+0x2e8,0xffffffff);self.q(self.eq+0x2e0,self.inv)
        self.u.mem_write(self.parent+0xc7,bytes([hero]));self.u.mem_write(OBJ+0x8000,prow)
        self.q(OBJ+0x9008,self.parent)
        self.globalq(0x3c078d0,OBJ+0x9000);self.globalq(0x3c131c8,OBJ+0x9000)
        for off,v in [(8,96),(0xc,64),(0x1c,32),(0x70,0xffffffff)]:self.w(self.inv+off,v)
        for off,v in [(0x40,OBJ+0xa000),(0x30,OBJ+0xa280),(0x48,OBJ+0xb000),(0x38,OBJ+0xb004),(0x50,OBJ+0x30000),(0x60,OBJ+0x32000)]:self.q(self.inv+off,v)
        self.u.mem_write(self.inv+0x79,b'\1');self.u.mem_write(OBJ+0x30000,b'\xff'*(0x7e1*2))
        for i in range(128):self.u.mem_write(OBJ+0x32000+i*8,struct.pack('<II',0xffffffff,(i+2)<<12))
        self.u.mem_write(self.inv+0x68,b'\0\0')
    def w(self,ptr,v):self.u.mem_write(ptr,struct.pack('<I',v&0xffffffff))
    def rd(self,ptr):return struct.unpack('<I',self.u.mem_read(ptr,4))[0]
    def globalq(self,rva,v):
        page=(BASE+rva)&~4095
        if not any(a<=page<=b for a,b,_ in self.u.mem_regions()):self.mapped(self.u,0,page,8,0,None)
        self.q(BASE+rva,v)
    def hook(self,u,address,size,user):
        pc=address-BASE
        if pc in (0xe8d840,0xe81650):self.stubs.add('E8D840 / E81650 actual MMV Goods / PlayerCommon PARAM lookup')
        if pc in (0x6a0b20,0x6a1570,0x6c1e60,0x6a0dd0,0x6c1c80):self.stubs.add('synthetic goods handles and reference ownership; native inventory allocation/counting/limits')
        if pc==0x1f4170:self.stubs.add('1F4170 general pickup auto-equip/UI side effects skipped; starting routine quick-slot assignment remains native')
        if address==STOP+0x200:self.stubs.add('actor hero enum fixture')
        if pc==0x214f3e0 or address in (STOP+0x201,STOP+0x202):self.stubs.add('isolated vector allocator and allocation-status fixture; native vector copy/iteration')
        rcx=u.reg_read(UC_X86_REG_RCX);rdx=u.reg_read(UC_X86_REG_RDX);r8=u.reg_read(UC_X86_REG_R8)
        def ret(value=0):
            u.reg_write(UC_X86_REG_RAX,value);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
        if pc==0xe8d840:
            id=rdx&0xffffffff
            if id in goods and id not in self.glook:
                assert len(self.glook)<32
                self.glook[id]=OBJ+0x34000+len(self.glook)*0xe0;u.mem_write(self.glook[id],goods[id])
            self.w(rcx,id);self.q(rcx+8,self.glook.get(id,0));ret(rcx)
        elif pc==0xe81650:self.q(rcx,OBJ+0x8000);ret(rcx)
        elif pc==0x6a0b20:self.w(rdx,self.rd(r8));ret(rdx)
        elif pc==0x6a1570:self.w(rcx+0x10,self.rd(rcx));ret()
        elif pc==0x6c1e60:self.w(rcx,self.rd(rdx));ret(rcx)
        elif pc in (0x6a0dd0,0x6c1c80,0x1f4170):ret()
        elif pc==0x214f3e0:ret(OBJ+0x7000)
        elif address==STOP+0x201:self.w(rdx,32);ret(rdx)
        elif address==STOP+0x200:ret(self.hero)
        elif address==STOP+0x202:
            assert 0<rdx<0x1000;ptr=self.vecptr;self.vecptr+=(rdx+15)&~15;assert self.vecptr<OBJ+0x39000;ret(ptr)
        elif pc==0x1f05f0:self.grants.append([self.rd(rdx)&0xfffffff,r8])
        elif pc==0x1f2b60:self.removed.append(rdx&0xffffffff)
        else:super().hook(u,address,size,user)
    def total(self,id):return sum(n for item,n in self.entries() if item==id)
    def reset_roots(self):
        while self.nodes():
            self.invoke(0x504e80,[OBJ,self.nodes()[0]['id']]);self.qualify();self.update(0)
    def entries(self):
        return [[self.rd(OBJ+0xa000+i*20+4)&0xfffffff,self.rd(OBJ+0xa000+i*20+8)] for i in range(96) if self.rd(OBJ+0xa000+i*20)]
    def capacity(self):return self.invoke(0x1f2370,[self.eq])
    def add(self,id,n=1):
        self.w(OBJ+0x8500,0x40000000|id);return self.invoke(0x1f05f0,[self.eq,OBJ+0x8500,n,1,1,0])&0xffffffff
    def start(self,roots):
        for r in roots:self.insert(r)
        self.qualify();self.update(0)
        self.invoke(0x673af0,[OBJ+0x6000])

roots=sorted(int(i) for i,r in x.spells.items() if r['stateInfo']==2102)
assert len(roots)==93
fields=['stateInfo','spCategory','effectEndurance','startGoodsId','startingItemAmount',
        'invocationConditionsStateChange1','invocationConditionsStateChange2','invocationConditionsStateChange3']
rows={str(i):{k:x.spells[str(i)][k] for k in fields} for i in roots}
assert all({r['invocationConditionsStateChange'+str(i)] for i in (1,2,3)}<={0,2226} for r in rows.values())
families=sorted({tuple(int(r[k]) for k in ('passiveSpEffectId_1','passiveSpEffectId_2','passiveSpEffectId_3') if int(r[k]) in roots)
                 for r in x.x['tables']['AttachEffectParam'].values()}-{()})
assert all(all(rows[str(root)]['startGoodsId']==rows[str(family[0])]['startGoodsId'] for root in family) for family in families)
checks=dict(selection=[],repeat=[],capacity=[],reinitialize=[],allocationFailure=[])
stubs=set()

def record(kind,c,**case):
    checks[kind].append(case)
    stubs.update(c.stubs)

def expected_amount(family,hero):
    return sum(rows[str(r)]['startingItemAmount'] for r in family
               if hero==9 or 2226 not in [rows[str(r)]['invocationConditionsStateChange'+str(i)] for i in (1,2,3)])

# Check every current root against every playable hero, including non-Scholar
# negative controls for the extra branch. Inactive container flags alone do not
# determine eligibility: 673AF0 explicitly handles state 2226 and hero enum 9.
for root in roots:
    for hero in range(1,11):
        c=StartingGoods(hero);c.start([root])
        item=rows[str(root)]['startGoodsId'];expected=expected_amount([root],hero)
        assert c.total(item)==expected,(root,hero,c.entries(),expected)
        record('selection',c,root=root,hero=hero,item=item,quantity=c.total(item))

# Three matching relics fit into the four default quick slots in these isolated
# cases. This proves repeated grants, not an unlimited capacity promise.
for family in families:
    for hero in (1,9):
        for copies in (1,2,3):
            c=StartingGoods(hero);c.start(list(family)*copies)
            item=rows[str(family[0])]['startGoodsId'];expected=expected_amount(family,hero)*copies
            assert c.total(item)==expected,(family,hero,copies,c.entries(),expected)
            record('repeat',c,roots=list(family),hero=hero,copies=copies,item=item,quantity=c.total(item),stacks=c.entries())

# Native setters clamp the two pouch counters separately to four. The final
# getter combines them with base four, caps this part at eight, then adds the
# independent Dragon Heart slots (up to ten overall).
for relic in range(7):
    for pickup in range(6):
        for reverse in (False,True):
            c=StartingGoods(1)
            order=[10055]*relic+[10050]*pickup
            if reverse:order.reverse()
            for item in order:c.add(item)
            for dragon in range(3):
                if dragon:c.add(10060)
                cap=c.capacity();expected=min(10,min(8,4+min(relic,4)+min(pickup,4))+dragon)
                assert cap==expected,(relic,pickup,dragon,cap)
                record('capacity',c,relic=relic,pickup=pickup,dragon=dragon,reverse=reverse,capacity=cap)

# Reapplying initialization removes old 10055 entries and resets its counter.
# It must not accumulate the last setup's grant on top of the new setup.
for old in range(7):
    for new in range(7):
        c=StartingGoods(1);c.start([7121000]*old);c.reset_roots();c.start([7121000]*new)
        assert c.total(10055)==new and c.capacity()==min(8,4+new),(old,new,c.entries(),c.capacity())
        assert len(c.removed)==old
        c.invoke(0x673af0,[OBJ+0x6000])
        assert c.total(10055)==new and c.capacity()==min(8,4+new)
        record('reinitialize',c,old=old,new=new,afterRepeat=c.total(10055),capacity=c.capacity())

# Real key-item allocation failure must not manufacture a pouch counter change.
c=StartingGoods(1);c.w(c.inv+0x1c,0);c.start([7121000])
assert c.total(10055)==0 and c.capacity()==4
record('allocationFailure',c,quantity=0,capacity=c.capacity())

output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],
            paramSha256=sha(x.param),goodsParamSha256=sha(graw),playerCommonParamSha256=sha(praw),
            roots=roots,rows=rows,families=[list(f) for f in families],
            playerCommon=dict(defaultNumberOfItemSlots=prow[14],maxNumberOfItemSlots=prow[15]),
            native=dict(start='673AF0',grant='1F05F0 / 1F0160',existingStack='1F5470',
                        newStack='1F62A0',itemCount='1F5170',pouchNotification='1F6CA0 / 1F6E70',
                        pouchSetter='20D410',pickedPouchSetter='20D350',capacity='1F2370',
                        itemCapacity='1F5B50 / 6A3310',remove='1F2B60 / 1F6410'),
            checks=checks,stubs=sorted(stubs),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS:',{k:len(v) for k,v in checks.items()},'families',len(families))
