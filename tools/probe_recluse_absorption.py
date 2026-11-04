"""Trace elemental absorption events and the relic's timed elemental protection.

Pinned native event dispatch, slot collection, conditional replacement, effect
container and defense getters execute in isolation. Spatial target selection,
identity and transport use explicit fixtures; this is not gameplay.
"""
import argparse
import itertools
import json
import math
import struct
from pathlib import Path
from unicorn.x86_const import *
from native_effect_runtime import BASE, OBJ, STOP, Chain, Inputs, sha
from effect_behavior_graph import BehaviorGraph

p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','animations','behavior','output'):p.add_argument(name,type=Path)
a=p.parse_args();inputs=Inputs(a.exe,a.extracted)
tae=json.loads(a.animations.read_text());graph=BehaviorGraph(a.behavior)
assert tae['bundles'][0]['sha256']=='1410035ad79edb410fa41420ec259fcb4a1037d748c9c4a3b6ae8d1366c76d0f'
paths=[graph.state(f'ElementalAbsorption{n}Finish{suffix}') for n in ('','2','3') for suffix in ('','_Upper')]
assert [x['animation'] for x in paths]==[f'a906_{n}' for n in (560005,560005,560015,560015,560025,560025)]
events=[dict(tae=t['ID'],animation=an['ID'],**e) for b in tae['bundles'] for t in b['taes']
        for an in t['animations'] for e in an['events'] if e['Type'] in (1008,1009)]
collect=[e for e in events if e['Type']==1008];reset=[e for e in events if e['Type']==1009]
assert [(e['tae'],e['animation'],e['index']) for e in collect]==[(2906,n,1) for n in (560005,560015,560025)]
markers=(706001,706000,706002,706003);leaves=(7500601,7500602,7500603,7500604)
for e in collect:assert struct.unpack('<4i',bytes.fromhex(e['hex']))==markers
assert inputs.spells['7500600']['stateInfo']==2396
for marker,leaf,field in zip(markers,leaves,('magicDamageCutRate','fireDamageCutRate','thunderDamageCutRate','darkDamageCutRate')):
    m=inputs.spells[str(marker)];r=inputs.spells[str(leaf)]
    assert m['replaceSpEffectId']==leaf and m['stateInfo']==2263
    assert math.isclose(m['effectEndurance'],.3,rel_tol=1e-6)
    assert r['invocationConditionsStateChange1']==2396 and r['effectEndurance']==30 and r['spCategory']==20
    assert math.isclose(r[field],.8,rel_tol=1e-6)
MODULE,TARGET=OBJ+0x9000,OBJ+0xb000
class Absorption(Chain):
    def __init__(self):
        super().__init__(inputs);self.consumed=0;self.messages=[];self.present=True
        self.q(MODULE+8,OBJ+0x6000);self.q(OBJ+0x61b8,OBJ+0x8000);self.q(OBJ+0x8180,MODULE)
        self.q(OBJ+0x6190,OBJ);self.q(TARGET,OBJ+0xb800);self.q(OBJ+0xb988,STOP+0x200)
        self.u.mem_write(TARGET+0x78,struct.pack('<ii',123,456))
        self.u.mem_map(OBJ+0x40000,0x20000);self.q(OBJ+0x574e8,OBJ+0x6000)
        for rva,value in ((0x3c0f0a8,OBJ+0x40000),(0x45b4fa+0x37b874e,OBJ+0xc000),(0x45b735+0x37cec7b,OBJ+0xc200)):
            page=(BASE+rva)&~4095
            try:self.u.mem_read(page,1)
            except:self.mapped(self.u,0,page,8,0,None)
            self.q(BASE+rva,value)
        self.q(OBJ+0xc090,OBJ+0xc100)
    def hook(self,u,address,size,user):
        pc=address-BASE
        def ret(value=0):
            u.reg_write(UC_X86_REG_RAX,value);sp=u.reg_read(UC_X86_REG_RSP)
            u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
        if pc==0x757ca0:
            self.stubs.add('757CA0 explicitly selected residue wrapper; no spatial search');ret(OBJ+0xc000)
        elif pc==0x7551a0:
            self.stubs.add('7551A0 selected-residue identity fixture');ret(TARGET if self.present else 0)
        elif address==STOP+0x200:
            self.stubs.add('residue vtable +188 consume recorder');self.consumed+=1;ret()
        elif pc==0xddf8d0:
            self.stubs.add('DDF8D0 outgoing consumption message recorder')
            self.messages.append(bytes(u.mem_read(u.reg_read(UC_X86_REG_RDX),9)).hex());ret(u.reg_read(UC_X86_REG_RCX))
        elif pc in (0xee6eb0,0x183460):
            self.stubs.add(hex(pc)+' empty mixed-spell reference fixture');ret()
        elif pc==0xeefd50:
            self.stubs.add('EEFD50 empty mixed-spell lookup fixture; slot collection remains native')
            ptr=u.reg_read(UC_X86_REG_RDX);self.q(ptr,0);ret(ptr)
        else:super().hook(u,address,size,user)
    def event(self,event,element=1,active=1):
        self.u.mem_write(TARGET+0x23c,bytes([element]))
        self.q(OBJ+0xd018,OBJ+0x6000);self.q(OBJ+0xd108,OBJ+0xd200)
        self.u.mem_write(OBJ+0xd100,struct.pack('<I',event['Type']))
        self.u.mem_write(OBJ+0xd118,bytes([active]));self.u.mem_write(OBJ+0xd200,bytes.fromhex(event['hex']))
        self.invoke(0x410ca0,[OBJ+0xd000,OBJ+0xd100])
    def slots(self):return list(self.u.mem_read(MODULE+0x10,3))
    def defense(self):
        self.u.mem_write(OBJ+0x800,bytes(0x200))
        self.invoke(0x503800,[OBJ,OBJ+0x500,OBJ+0x520,OBJ+0x540,OBJ+0x800])
        return [round(v,6) for v in struct.unpack('<5f',self.u.mem_read(OBJ+0x500,20))]
    def copies(self,n):
        for _ in range(n):self.insert(7500600)
        self.qualify();self.update(0)
    def deliver(self):
        pending=self.emitted[:];self.emitted=[]
        for id in pending:self.insert(id)
        self.qualify();self.update(0)
        return pending
    def absorb(self,element):
        self.invoke(0x45c700,[MODULE]);self.event(collect[0],element);self.deliver()
        grants=[]
        for frame in range(40):
            self.qualify();self.update(1/60)
            grants.extend(self.deliver())
            if not any(n['id'] in markers for n in self.nodes()):break
        else:raise AssertionError('collection marker did not expire')
        return grants

checks=dict(dispatch=[],reset=[],protection=[],refresh=[],lifetime=[]);stubs=set()
for event,element,occupied,active,present in itertools.product(collect,range(5),range(4),(0,1),(False,True)):
    c=Absorption();c.present=present;c.u.mem_write(MODULE+0x10,bytes([1]*occupied+[0]*(3-occupied)))
    before=c.slots();c.event(event,element,active)
    valid=element>0 and occupied<3 and active and present
    expected=before[:]
    if valid:expected[occupied]=element
    assert c.slots()==expected and c.emitted==([markers[element-1]] if valid else []),(event,element,occupied,active,present,c.slots(),c.emitted)
    assert c.consumed==int(bool(valid)) and len(c.messages)==int(bool(valid))
    checks['dispatch'].append(dict(animation=event['animation'],element=element,occupied=occupied,active=active,present=present,slots=c.slots(),emitted=c.emitted))
    stubs.update(c.stubs)
for event,active in itertools.product(reset,(0,1)):
    c=Absorption();c.u.mem_write(MODULE+0x10,bytes([1,3,4]));c.event(event,active=active)
    assert c.slots()==([0,0,0] if active else [1,3,4]) and not c.emitted
    checks['reset'].append(dict(tae=event['tae'],animation=event['animation'],active=active,slots=c.slots()));stubs.update(c.stubs)
# Pending grants are delivered on explicit subsequent frames. Keep collection
# marker expiry separate from the conditional replacement's 30 second timer.
for copies,element in itertools.product((0,1,2,3),range(1,5)):
    c=Absorption();c.copies(copies);pending=c.absorb(element)
    expected=[1]*5
    if copies:expected[element]=.8
    assert c.defense()==expected,(copies,element,pending,c.nodes(),c.defense())
    checks['protection'].append(dict(copies=copies,element=element,grants=pending,nodes=c.nodes(),damageTaken=c.defense()));stubs.update(c.stubs)
for copies,mask in itertools.product((1,3),range(1,16)):
    c=Absorption();c.copies(copies);elements=[e for e in range(1,5) if mask&(1<<(e-1))]
    for element in elements:c.absorb(element)
    expected=[1]+[.8 if e in elements else 1 for e in range(1,5)]
    assert c.defense()==expected
    c.qualify();c.update(5)
    for element in elements:
        c.absorb(element)
        nodes=[n for n in c.nodes() if n['id']==leaves[element-1]]
        assert len(nodes)==1 and nodes[0]['lifetime']==30
        assert c.defense()==expected
    checks['refresh'].append(dict(copies=copies,elements=elements,nodes=c.nodes(),damageTaken=c.defense()));stubs.update(c.stubs)
for element,fps in itertools.product(range(1,5),(30,60,120)):
    c=Absorption();c.copies(1);c.absorb(element)
    for frame in range(1,32*fps):
        c.qualify();c.update(1/fps)
        if not any(n['id']==leaves[element-1] for n in c.nodes()):break
    assert abs(frame/fps-30)<=3.01/fps,(element,fps,frame)
    assert c.defense()==[1]*5
    checks['lifetime'].append(dict(element=element,fps=fps,expiryFrame=frame));stubs.update(c.stubs)
output=dict(schema=1,exeSha256=sha(inputs.raw),regulationSha256=inputs.x['hashes']['regulation.bin'],paramSha256=sha(inputs.param),
            animationBundleSha256=tae['bundles'][0]['sha256'],behaviorSha256=graph.metadata['hkxSha256'],paths=paths,events=events,
            root=7500600,markers=markers,leaves=leaves,checks=checks,
            stubs=sorted(stubs),gameplayVerified=False)
output['native']=dict(dispatch='410CA0',collect='45B480',localPlayer='3D4180',reset='45C700',
                      insert='50D060',qualify='5057D0',update='50ACD0',defense='503800')
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(map(len,checks.values())),'native absorption cases')
