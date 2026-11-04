"""Trace Raider's animation-maintained attack bonus and vulnerability.

The pinned HKS branch, TAE dispatch, state qualification, maintenance, removal
and numeric getters execute with explicit actor/animation fixtures. This does
not simulate a complete behavior VM, collision, damage or multiplayer.
"""
import argparse
import ctypes
import ctypes.util
import itertools
import json
import math
import struct
from pathlib import Path
from unicorn.x86_const import *
from native_effect_runtime import BASE, OBJ, Chain, Inputs, sha
from effect_behavior_graph import BehaviorGraph

p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','script','animations','behavior','output'):p.add_argument(name,type=Path)
a=p.parse_args();inputs=Inputs(a.exe,a.extracted)
tae=json.loads(a.animations.read_text());graph=BehaviorGraph(a.behavior)
raw=a.script.read_bytes();assert sha(raw)=='786f8a7bc89452d9531e2299b224c8945701c422437eca9aacbeb10a57a17f4d'
assert tae['bundles'][0]['sha256']=='1410035ad79edb410fa41420ec259fcb4a1037d748c9c4a3b6ae8d1366c76d0f'
source=raw.decode('utf-8-sig').replace('\r\n','\n')
start=source.index('function SmashAttackStanceStart_onUpdate()')
function=source[start:source.index('\nfunction ',start+1)]
paths=[graph.state(n) for n in ('SmashAttackStanceStart','SmashAttack1','SmashAttack2')]
assert [p['animation'] for p in paths]==['a904_541000','a904_541010','a904_541020']
events=[dict(tae=t['ID'],animation=an['ID'],**e) for b in tae['bundles'] for t in b['taes']
        for an in t['animations'] for e in an['events'] if e['Type']==67 and
        struct.unpack_from('<i',bytes.fromhex(e['hex']))[0] in (7031601,7031602)]
assert len(events)==9 and all(e['tae']==2904 for e in events)
assert [e['animation'] for e in events if struct.unpack_from('<i',bytes.fromhex(e['hex']))[0]==7031602]==[541020]
root=7031600;leaves=[7031601,7031602];rows=inputs.spells
assert rows[str(root)]['stateInfo']==2084 and rows[str(root)]['spCategory']==20
for leaf,rate in zip(leaves,(1.5,2)):
    r=rows[str(leaf)]
    assert r['invocationConditionsStateChange1']==2084 and r['physicsAttackRate']==rate
    assert r['spCategory']==20 and math.isclose(r['effectEndurance'],.1,rel_tol=1e-6)
    assert r['isContractSpEffectLife']==r['isWaitModeDelete']==1
    assert all(r[f+'AttackRate']==1 for f in ('magic','fire','thunder','dark'))
    assert all(math.isclose(r[f+'DamageCutRate'],1.3,rel_tol=1e-6) for f in ('slash','blow','thrust','neutral','magic','fire','thunder','dark'))

lua=ctypes.CDLL(ctypes.util.find_library('lua5.4'))
lua.luaL_newstate.restype=ctypes.c_void_p
lua.luaL_openlibs.argtypes=[ctypes.c_void_p]
lua.luaL_loadstring.argtypes=[ctypes.c_void_p,ctypes.c_char_p]
lua.lua_pcallk.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_ssize_t,ctypes.c_void_p]
lua.lua_tolstring.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.POINTER(ctypes.c_size_t)]
lua.lua_tolstring.restype=ctypes.c_char_p
lua.lua_close.argtypes=[ctypes.c_void_p]
def branch(ended,flag,boost):
    program='''
TRUE=1;FALSE=0;IsAnimEnd=1;GetEventEzStateFlag=2;GetSpEffectID=3
SetSpecialInterpolation=4;AddSpEffect=5;POWER_DAMAGE_COUNTER=137
local inputs={%d,%d,%d};local events={};local added={};local selector=-1
function env(key,id) if key==3 then assert(id==704011) end return inputs[key] end
function act(key,id) if key==5 then table.insert(added,id) else assert(key==4) end end
function SetVariable(k,v) assert(k=='SmashAttackSelector');selector=v end
function ExecEventAllBody(e) table.insert(events,e) end
function IsEnableSpecialAttack() return FALSE end
function AttackCommonFunction() return FALSE end
'''%(ended,flag,boost)
    program+=function+'''
SmashAttackStanceStart_onUpdate()
return string.format('{"event":"%s","added":[%s],"selector":%d,"counter":%d}',
events[1] or '',table.concat(added,','),selector,POWER_DAMAGE_COUNTER)
'''
    state=lua.luaL_newstate()
    try:
        lua.luaL_openlibs(state);assert lua.luaL_loadstring(state,program.encode())==0
        status=lua.lua_pcallk(state,0,1,0,0,None);result=lua.lua_tolstring(state,-1,None)
        assert status==0,result
        return json.loads(result)
    finally:lua.lua_close(state)

class Skill(Chain):
    def __init__(self,copies):
        super().__init__(inputs);self.pending=[];self.requests=[]
        self.q(OBJ+0x6190,OBJ);self.q(OBJ+0xe018,OBJ+0x6000);self.q(OBJ+0xe108,OBJ+0xe200)
        for _ in range(copies):self.insert(root)
        self.qualify();self.update(0)
    def event(self,id,active=1):
        self.u.mem_write(OBJ+0xe100,struct.pack('<I',67));self.u.mem_write(OBJ+0xe118,bytes([active]))
        self.u.mem_write(OBJ+0xe200,struct.pack('<i',id)+bytes(12))
        self.invoke(0x410ca0,[OBJ+0xe000,OBJ+0xe100])
        for id in self.pending:self.insert(id)
        self.pending.clear()
    def defense(self):
        self.u.mem_write(OBJ+0x800,bytes(0x200))
        self.invoke(0x503800,[OBJ,OBJ+0x500,OBJ+0x520,OBJ+0x540,OBJ+0x800])
        return list(struct.unpack('<5f',self.u.mem_read(OBJ+0x500,20)))
    def hook(self,u,address,size,user):
        pc=address-BASE
        def ret(value=0):
            u.reg_write(UC_X86_REG_RAX,value);sp=u.reg_read(UC_X86_REG_RSP)
            u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
        if pc in (0x3ced90,0x4d1b20,0x3c8be0):
            self.stubs.add('3CED90/4D1B20 neutral animation owner; 3C8BE0 grant recorder with explicit delivery')
            if pc==0x3c8be0:
                id=u.reg_read(UC_X86_REG_RDX)&0xffffffff
                self.pending.append(id);self.requests.append(dict(id=id,mode=u.reg_read(UC_X86_REG_R8)&255))
            ret(OBJ+0xd000 if pc==0x3ced90 else 0)
        else:super().hook(u,address,size,user)

checks=dict(script=[],dispatch=[],numeric=[],maintenance=[],transition=[],overlap=[]);stubs=set()
for ended,flag,boost in itertools.product((0,1),repeat=3):
    result=branch(ended,flag,boost);ready=bool(ended or flag)
    assert result['event']==('W_SmashAttack'+str(2 if boost else 1) if ready else '')
    assert result['added']==([704010] if ready and boost else [])
    assert result['counter']==(0 if ready and boost else 137)
    checks['script'].append(dict(ended=ended,flag=flag,boost=boost,result=result))
for event,copies,active in itertools.product(events,(0,1,2,3),(0,1)):
    c=Skill(copies);leaf=struct.unpack_from('<i',bytes.fromhex(event['hex']))[0]
    c.event(leaf,active);c.qualify();c.update(0)
    rates=c.attack();defense=c.defense();expected=rows[str(leaf)]['physicsAttackRate'] if copies else 1
    assert rates==[expected,1,1,1,1]
    assert all(math.isclose(v,1.3 if copies else 1,rel_tol=1e-6) for v in defense)
    assert c.requests==[dict(id=leaf,mode=1)]
    checks['dispatch'].append(dict(animation=event['animation'],copies=copies,active=active,requests=c.requests,rates=rates,defense=defense));stubs.update(c.stubs)
for leaf,copies,kind in itertools.product(leaves,(0,1,2,3),range(11)):
    c=Skill(copies);c.event(leaf);c.qualify();c.update(0);rates=c.attack(kind)
    assert rates==[rows[str(leaf)]['physicsAttackRate'] if copies and kind!=5 else 1,1,1,1,1]
    checks['numeric'].append(dict(leaf=leaf,copies=copies,kind=kind,rates=rates));stubs.update(c.stubs)
for fps,leaf,copies in itertools.product((30,60,120),leaves,(1,2,3)):
    c=Skill(copies);samples=[]
    for frame in range(3*fps):
        if frame<2*fps:c.event(leaf)
        c.qualify();c.update(1/fps)
        rate=c.attack()[0]
        if frame<2*fps:assert rate==rows[str(leaf)]['physicsAttackRate']
        else:assert rate==1
        if frame in (0,fps,2*fps-1,2*fps,3*fps-1):samples.append(dict(frame=frame,rate=rate,nodes=c.nodes()))
    assert len(c.requests)==1
    checks['maintenance'].append(dict(fps=fps,leaf=leaf,copies=copies,samples=samples));stubs.update(c.stubs)
for fps,order in itertools.product((30,60,120),(leaves,list(reversed(leaves)))):
    c=Skill(1);samples=[]
    for frame in range(3*fps):
        if frame<2*fps:c.event(order[0] if frame<fps else order[1])
        c.qualify();c.update(1/fps);rate=c.attack()[0];defense=c.defense()[0]
        assert rate==(rows[str(order[0 if frame<fps else 1])]['physicsAttackRate'] if frame<2*fps else 1)
        assert math.isclose(defense,1.3 if frame<2*fps else 1,rel_tol=1e-6)
        if frame in (fps-1,fps,2*fps-1,2*fps):samples.append(dict(frame=frame,rate=rate,defense=defense))
    checks['transition'].append(dict(fps=fps,order=order,samples=samples));stubs.update(c.stubs)
# Distinct leaves can overlap in the container. This does not establish that
# the complete behavior scheduler allows overlapping animation windows.
for copies,order in itertools.product((1,2,3),(leaves,list(reversed(leaves)))):
    c=Skill(copies)
    for leaf in order:c.event(leaf)
    c.qualify();c.update(0);rates=c.attack();defense=c.defense()
    assert rates==[3,1,1,1,1] and all(math.isclose(v,1.69,rel_tol=1e-6) for v in defense)
    checks['overlap'].append(dict(copies=copies,order=order,rates=rates,defense=defense));stubs.update(c.stubs)
output=dict(schema=1,exeSha256=sha(inputs.raw),regulationSha256=inputs.x['hashes']['regulation.bin'],paramSha256=sha(inputs.param),
            scriptSha256=sha(raw),functionSha256=sha(function.encode()),animationBundleSha256=tae['bundles'][0]['sha256'],
            behaviorSha256=graph.metadata['hkxSha256'],paths=paths,events=events,root=root,leaves=leaves,checks=checks,
            native=dict(dispatch='410CA0',type67='40FF20',exists='509150',maintain='50A630',insert='50D060',
                        qualify='5057D0',update='50ACD0',attack='502830',defense='503800'),
            stubs=sorted(stubs|{'HKS animation-end/event flags and 704011 presence are explicit inputs; no complete action scheduler or damage-counter accumulation',
                               'TAE requests are delivered before the next qualification; no collision, final damage, full actor queue or multiplayer'}),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(map(len,checks.values())),'Raider skill cases (including 8 HKS branches)')
