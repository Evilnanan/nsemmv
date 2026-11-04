"""Trace Recluse mark duration, repeat application and the shared recovery gate.

Behavior references and actual TAE/Behavior/Bullet rows bind the two marks to
casting. Native effect insertion/ticking, state predicates and the hit-consumer
branch run original instructions. Synthetic contexts and recovery request sinks
are explicit; this is not a complete hit or in-game/network simulation.
"""
import argparse
import itertools
import json
import math
import struct
from pathlib import Path
from unicorn.x86_const import *
from native_effect_runtime import BASE, OBJ, STACK, STOP, Chain, Inputs, sha
from effect_behavior_graph import BehaviorGraph

p = argparse.ArgumentParser(description=__doc__)
for name in ('exe', 'extracted', 'assets', 'systems', 'animations', 'behavior', 'output'):
    p.add_argument(name, type=Path)
a = p.parse_args()
inputs = Inputs(a.exe, a.extracted)
assets = json.loads(a.assets.read_text())
systems = json.loads(a.systems.read_text())
tae = json.loads(a.animations.read_text())
for source in (assets, systems):
    assert source['hashes']['regulation.bin'] == inputs.x['hashes']['regulation.bin']
assert tae['bundles'][0]['sha256'] == '1410035ad79edb410fa41420ec259fcb4a1037d748c9c4a3b6ae8d1366c76d0f'
behavior_raw = a.extracted.with_suffix('.BehaviorParam_PC.param').read_bytes()
weapon_raw = a.assets.with_suffix('.EquipParamWeapon.param').read_bytes()
player_raw = a.systems.with_suffix('.PlayerCommonParam.param').read_bytes()
behaviors = inputs.table(behavior_raw, 0x30)
weapons = inputs.table(weapon_raw, 0x298)
player_offset = struct.unpack_from('<Q', player_raw, 0x48)[0]
player_row = player_raw[player_offset:player_offset+0x140]
assert struct.unpack_from('<ffi', player_row, 0x12c) == (40, 8, 706110)
spells = inputs.spells
root, selector, ordinary = (spells[str(i)] for i in (7034300, 7034301, 7034302))
assert root['cycleOccurrenceSpEffectId'] == 7034301 and math.isclose(root['motionInterval'], .1, rel_tol=1e-6)
assert root['spCategory'] == 20
assert selector['spCategory'] == ordinary['spCategory'] == 202
assert selector['categoryPriority'] == ordinary['categoryPriority'] == 46
assert selector['stateInfo'] == 2030 and ordinary['stateInfo'] == 2031
assert selector['effectEndurance'] == 5 and ordinary['effectEndurance'] == -1
assert {k: (spells['706100'][k], v) for k, v in spells['706101'].items()
        if spells['706100'][k] != v} == {'effectEndurance': (12.5, 20)}
assert spells['706100']['stateInfo'] == spells['706101']['stateInfo'] == 608
bullet_rows = inputs.x['tables']['Bullet']
assert {k: (bullet_rows['30906000'][k], v) for k, v in bullet_rows['30906001'].items()
        if bullet_rows['30906000'][k] != v} == {'spEffectId0': (706100, 706101)}
graph = BehaviorGraph(a.behavior)
state = graph.state('BloodMagicStart')
assert state['animation'] == 'a906_660000'

class Dispatch(Chain):
    def __init__(self):
        super().__init__(inputs)
        self.requests, self.emissions, self.frame = [], [], 0
        # Real Behavior resolver at +328; the other virtuals supply a synthetic
        # equipped weapon / owner identity. No state predicate is substituted.
        for off, ptr in [(0x118, STOP + 0x201), (0x190, STOP + 0x200), (0x260, STOP + 0x200),
                         (0x328, BASE + 0x668b30), (0x320, STOP + 0x201),
                         (0x250, STOP + 0x202), (0x28, STOP + 0x201), (0x178, STOP + 0x200)]:
            self.q(OBJ + 0x6200 + off, ptr)
        self.q(OBJ + 0x6190, OBJ)

    def hook(self, u, address, size, user):
        pc = address - BASE
        def finish(value=0):
            u.reg_write(UC_X86_REG_RAX, value)
            sp = u.reg_read(UC_X86_REG_RSP)
            u.reg_write(UC_X86_REG_RIP, struct.unpack('<Q', u.mem_read(sp, 8))[0])
            u.reg_write(UC_X86_REG_RSP, sp + 8)
        if address in (STOP + 0x200, STOP + 0x201, STOP + 0x202):
            self.stubs.add('synthetic player virtuals and equipped weapon 1000')
            finish({STOP + 0x200: 0, STOP + 0x201: 1, STOP + 0x202: 1000}[address])
        elif pc in (0x4d1b20, 0x3d4180, 0x3d4c10, 0xea9a60, 0xea76f0, 0x66b2d0, 0x27d0640):
            self.stubs.add(hex(pc) + ' isolated actor context / hand identity / empty animation reference list')
            finish()
        elif pc == 0x3ced90:
            self.stubs.add('3CED90 isolated actor context')
            finish(OBJ + 0xd000)
        elif pc == 0xea7fc0:
            self.stubs.add('EA7FC0 actual equipped-weapon row lookup')
            id = u.reg_read(UC_X86_REG_RDX) & 0xffffffff
            u.mem_write(OBJ + 0xb000, weapons[id])
            u.mem_write(u.reg_read(UC_X86_REG_RCX), struct.pack('<IIQ', id, 0, OBJ + 0xb000))
            finish()
        elif pc == 0xe6fcb0:
            self.stubs.add('E6FCB0 actual Behavior row lookup')
            id = u.reg_read(UC_X86_REG_RDX) & 0xffffffff
            assert id in (700000300, 700000306)
            u.mem_write(OBJ + 0xb800, behaviors[id])
            self.q(u.reg_read(UC_X86_REG_RCX) + 8, OBJ + 0xb800)
            finish()
        elif pc == 0x3975d0:
            self.stubs.add('3975D0 Behavior request recorder; active/stop and conditional-state gates are native')
            payload = bytes(u.mem_read(u.reg_read(UC_X86_REG_R9), 18))
            self.requests.append(dict(behavior=u.reg_read(UC_X86_REG_RDX),
                                      active=bool(payload[16]), instant=bool(payload[17]), payload=payload.hex()))
            finish(1)
        else:
            super().hook(u, address, size, user)


class Mark(Chain):
    def __init__(self):
        super().__init__(inputs);self.heals=[];self.visuals=[];self.hit=False
        self.q(OBJ+0x6190,OBJ);self.q(OBJ+0x8008,OBJ+0x6000)
        self.q(OBJ+0x91b8,OBJ+0xb100);self.q(OBJ+0xb100,OBJ+0xb200)
        self.u.mem_write(OBJ+0xc000,player_row);self.u.mem_map(OBJ+0x40000,0x20000)
        self.q(OBJ+0x574e8,OBJ+0x9000)
        page=0x3c0f0a8&~4095;self.mapped(self.u,0,BASE+page,8,0,None);self.q(BASE+0x3c0f0a8,OBJ+0x40000)
    def hook(self,u,address,size,user):
        pc=address-BASE
        if pc==0xe81650:self.stubs.add('E81650 actual PlayerCommon PARAM lookup')
        if pc in (0x426130,0x4261c0):self.stubs.add('HP/FP restoration request recorders; final resource caps/modifiers not simulated')
        if pc==0x3c7fd0 and self.hit:self.stubs.add('706110 grant recorder; no full actor/network delivery')
        def ret(value=0):
            u.reg_write(UC_X86_REG_RAX,value);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
        if pc==0x43e463 and self.hit:u.reg_write(UC_X86_REG_RIP,STOP)
        elif pc==0xe81650:
            ptr=u.reg_read(UC_X86_REG_RCX);self.q(ptr,OBJ+0xc000);ret(ptr)
        elif pc in (0x426130,0x4261c0):
            self.heals.append([hex(pc),u.reg_read(UC_X86_REG_RDX)&0xffffffff]);ret()
        elif pc==0x3c7fd0 and self.hit:
            assert u.reg_read(UC_X86_REG_RCX)==OBJ+0x9000;self.visuals.append(u.reg_read(UC_X86_REG_RDX));ret()
        else:super().hook(u,address,size,user)
    def strike(self,value=100,channel=0,local=True):
        self.hit=True;self.heals.clear();self.visuals.clear();self.u.mem_write(OBJ+0xe000,bytes(0x300));self.q(OBJ+0x574e8,OBJ+0x9000 if local else 0)
        self.u.mem_write(OBJ+0xe000,struct.pack('<5f',*([int(i==channel) for i in range(5)])));self.u.mem_write(OBJ+0xe280,struct.pack('<i',value))
        for reg,val in [(UC_X86_REG_R12,OBJ+0x9000),(UC_X86_REG_R14,OBJ+0x8000),(UC_X86_REG_RSI,OBJ+0xe000),(UC_X86_REG_RBP,STACK+0x6000)]:self.u.reg_write(reg,val)
        self.invoke(0x43e33f,[],{UC_X86_REG_XMM7:0});self.hit=False;return self.heals[:]

checks = dict(dispatch=[],lifetime=[],recovery=[],overlap=[])
stubs = set()
events = [dict(tae=track['ID'],animation=animation['ID'],**event)
          for bundle in tae['bundles'] for track in bundle['taes'] if track['ID']==2906
          for animation in track['animations'] if animation['ID']==660000
          for event in animation['events'] if event['Type']==2 and
          struct.unpack_from('<i',bytes.fromhex(event['hex']),8)[0] in (7300,7306)]
assert [e['index'] for e in events] == [1,62]
assert all(math.isclose(e['StartTime'],80/30,abs_tol=1e-6) for e in events)
for event in events:
    for has_base,copies,active in itertools.product((0,1),(0,1,3),(0,1)):
        c = Dispatch()
        if has_base: c.insert(7034302)
        for _ in range(copies): c.insert(7034300)
        queue = []
        for _ in range(10):
            for id in queue: c.insert(id)
            c.qualify();c.update(1/60);queue=c.emitted[:];c.emitted.clear()
        assert sum(n['id']==7034300 for n in c.nodes())==bool(copies)
        c.q(OBJ+0x8018,OBJ+0x6000);c.q(OBJ+0x8108,OBJ+0x8200)
        c.u.mem_write(OBJ+0x8118,bytes([active]));c.u.mem_write(OBJ+0x811a,struct.pack('<H',0x27))
        c.q(OBJ+0x8120,OBJ+0x8300);c.u.mem_write(OBJ+0x8200,bytes.fromhex(event['hex']))
        c.invoke(0x40cd80,[OBJ+0x8000,OBJ+0x8100])
        judge=struct.unpack_from('<i',bytes.fromhex(event['hex']),8)[0]
        expected=bool(active and (copies if judge==7306 else has_base and not copies))
        assert bool(c.requests)==expected,(judge,has_base,copies,active,c.requests,c.nodes())
        if expected: assert c.requests[0]['behavior']==700000000+judge-7000
        checks['dispatch'].append(dict(judge=judge,base=has_base,copies=copies,active=active,requests=c.requests,nodes=c.nodes()))
        stubs.update(c.stubs)

# Duration belongs to the victim's mark, not the casting animation, the short
# Bullet lifetime, or the five-second selector refreshed by the relic.
for id in (706100,706101):
    life=spells[str(id)]['effectEndurance']
    for fps,refresh in itertools.product((30,60,120),(None,5)):
        c=Mark();c.insert(id);c.qualify();c.update(0)
        assert c.strike()==[['0x426130',40],['0x4261c0',8]]
        refreshed_life=None
        for frame in range(1,math.ceil((life+(refresh or 0)+1)*fps)):
            if refresh and frame==refresh*fps:
                for _ in range(3):c.insert(id)
                c.qualify();c.update(0)
                assert len(c.nodes())==1
                refreshed_life=c.nodes()[0]['lifetime']
                assert refreshed_life==life
            c.update(1/fps)
            if not c.nodes():break
        assert abs(frame/fps-(life+(refresh or 0)))<=3.01/fps,(id,fps,refresh,frame)
        assert c.strike()==[]
        checks['lifetime'].append(dict(id=id,fps=fps,refresh=refresh,refreshedLifetime=refreshed_life,expiresFrame=frame))
        stubs.update(c.stubs)

# The hit consumer is a boolean state-608 gate, not a loop over marks. Keep
# normal+extended coexisting nodes as a counterexample to 'only one node'.
variants=[[],[706100],[706101],[706100]*3,[706101]*3,[706100,706101],[706101,706100]]
for ids in variants:
    c=Mark()
    for id in ids:c.insert(id)
    c.qualify();c.update(0)
    for channel,local,value in itertools.product((-1,0,1,2,3,4),(False,True),(0,1,3,12,13,100,999)):
        actual=c.strike(value,channel,local)
        expected=[int(value*.4),int(value*.08)]
        eligible=bool(ids) and channel>=0 and local and any(expected)
        assert actual==([['0x426130',expected[0]],['0x4261c0',expected[1]]] if eligible else [])
        assert c.visuals==([706110] if eligible else [])
        checks['recovery'].append(dict(ids=ids,channel=channel,local=local,input=value,requests=actual,grants=c.visuals[:]))
    stubs.update(c.stubs)
for first,second in ((706100,706101),(706101,706100)):
    c=Mark();c.insert(first);c.qualify();c.update(0);changes=[];previous=None
    for frame in range(251):
        if frame==30:c.insert(second);c.qualify()
        c.update(.1)
        current=[n['id'] for n in c.nodes()]
        if current!=previous:
            requests=c.strike()
            assert requests==([['0x426130',40],['0x4261c0',8]] if current else [])
            changes.append(dict(frame=frame,ids=current,requests=requests));previous=current
    assert not c.nodes() and any(len(change['ids'])==2 for change in changes)
    checks['overlap'].append(dict(first=first,second=second,secondAt=3,dt=.1,changes=changes))
    stubs.update(c.stubs)

fields=['spCategory','categoryPriority','stateInfo','effectEndurance','cycleOccurrenceSpEffectId','motionInterval']
rows={str(id):{k:spells[str(id)][k] for k in fields} for id in (7034300,7034301,7034302,706100,706101)}
paths=[]
for id,bullet,mark in ((700000300,30906000,706100),(700000306,30906001,706101)):
    behavior=inputs.x['tables']['BehaviorParam_PC'][str(id)]
    assert behavior['refType']==1 and behavior['refId']==bullet and bullet_rows[str(bullet)]['spEffectId0']==mark
    paths.append(dict(behavior=id,bullet=bullet,mark=mark))
output=dict(schema=1,exeSha256=sha(inputs.raw),regulationSha256=inputs.x['hashes']['regulation.bin'],
            paramSha256=sha(inputs.param),behaviorParamSha256=sha(behavior_raw),weaponParamSha256=sha(weapon_raw),
            playerCommonParamSha256=sha(player_raw),animationSha256=tae['bundles'][0]['sha256'],
            behavior={k:graph.metadata[k] for k in ('bundleSha256','hkxSha256','registrySha256','metadataOnly','mismatches')},state=state,root=7034300,rows=rows,paths=paths,events=events,
            native=dict(dispatch='40CD80',resolveBehavior='668B30',insert='50D060',tick='50ACD0',
                        recoveryBranch='43E33F..43E463',positiveChannels='52F780',localPlayer='3D4180',state='508E20'),
            checks=checks,stubs=sorted(stubs|{'synthetic hit context; +280 input and HP/FP requests do not simulate full damage construction or final recovery',
                                           'native hit-consumer subrange stops before unrelated hit side effects; no full hit/net/animation simulation'}),
            gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS:',{k:len(v) for k,v in checks.items()})
