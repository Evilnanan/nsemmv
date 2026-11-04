"""Trace Guardian extended tornado branches, lifetime and duplicate equipment.

Uses the original Lua update, pointer-checked behavior references, TAE dispatch
and PC effect/Bullet instructions. Scene collision and complete attack-instance
lifetimes are not simulated; hit-history expiry alone is not a hit-count proof.
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
from native_effect_runtime import BASE, OBJ, STOP, Chain, Inputs, sha
from effect_behavior_graph import BehaviorGraph

p = argparse.ArgumentParser(description=__doc__)
for name in ('exe', 'extracted', 'assets', 'animations', 'script', 'behavior', 'output'):
    p.add_argument(name, type=Path)
a = p.parse_args()
inputs = Inputs(a.exe, a.extracted)
assets = json.loads(a.assets.read_text())
tae = json.loads(a.animations.read_text())
assert assets['hashes']['regulation.bin'] == inputs.x['hashes']['regulation.bin']
assert tae['bundles'][0]['sha256'] == '1410035ad79edb410fa41420ec259fcb4a1037d748c9c4a3b6ae8d1366c76d0f'
raw_tables = {name: path.read_bytes() for name, path in (
    ('Bullet', a.extracted.with_suffix('.Bullet.param')),
    ('BehaviorParam_PC', a.extracted.with_suffix('.BehaviorParam_PC.param')),
    ('EquipParamWeapon', a.assets.with_suffix('.EquipParamWeapon.param')))}
bullets = inputs.table(raw_tables['Bullet'], 0x100)
behaviors = inputs.table(raw_tables['BehaviorParam_PC'], 0x30)
weapons = inputs.table(raw_tables['EquipParamWeapon'], 0x298)
root, leaf, base = (inputs.spells[str(i)] for i in (7011000, 7011001, 7010001))
assert root['cycleOccurrenceSpEffectId'] == 7011001 and math.isclose(root['motionInterval'], .1, rel_tol=1e-6)
assert leaf['spCategory'] == base['spCategory'] == 202 and leaf['categoryPriority'] == base['categoryPriority'] == 10
assert leaf['stateInfo'] == 2037 and base['stateInfo'] == 2004
assert root['effectEndurance'] == leaf['effectEndurance'] == base['effectEndurance'] == -1

graph = BehaviorGraph(a.behavior)
graph_states = [graph.state(n) for n in ('WindAttackStart', 'WindAttackCancelEarly')]
assert [s['animation'] for s in graph_states] == ['a901_510000', 'a901_510005']
raw_script = a.script.read_bytes()
assert sha(raw_script) == '786f8a7bc89452d9531e2299b224c8945701c422437eca9aacbeb10a57a17f4d'
source = raw_script.decode('utf-8-sig').replace('\r\n', '\n')
start = source.index('function WindAttackStart_onUpdate()')
function = source[start:source.index('\nfunction ', start + 1)]

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
            assert id in (600000050, 600000052, 600000055, 600000057, 600000084, 600000085, 600000086, 600000087)
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


lua = ctypes.CDLL(ctypes.util.find_library('lua5.4'))
lua.luaL_newstate.restype = ctypes.c_void_p
lua.luaL_openlibs.argtypes = [ctypes.c_void_p]
lua.luaL_loadstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
lua.lua_pcallk.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_ssize_t, ctypes.c_void_p]
lua.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_size_t)]
lua.lua_tolstring.restype = ctypes.c_char_p
lua.lua_close.argtypes = [ctypes.c_void_p]

def script_case(l2, skill, window, interrupt, ended):
    program = '''
TRUE=1; FALSE=0; g_ComboReset=0; SetSpecialInterpolation=0
ActionDurationAlternate=1; ActionDuration=2; GetSpEffectID=3; IsAnimEnd=4
ACTION_ARM_L2=10; ACTION_ARM_SKILL=11
local inputs={%d,%d,%d,%d}; local events={}
function act(key,slot,flag) assert(key==0 and slot==0 and flag==0) end
function env(key,id)
  if key==3 then assert(id==100285) end
  return inputs[key]
end
function AttackCommonFunction(...) return %d end
function ExecEventAllBody(name) table.insert(events,name) end
''' % (l2, skill, window, ended, interrupt)
    program += function + '\nWindAttackStart_onUpdate(); return table.concat(events,",")'
    state = lua.luaL_newstate()
    try:
        lua.luaL_openlibs(state)
        assert lua.luaL_loadstring(state, program.encode()) == 0
        status = lua.lua_pcallk(state, 0, 1, 0, 0, None)
        result = lua.lua_tolstring(state, -1, None)
        assert status == 0, result
        return result.decode()
    finally:
        lua.lua_close(state)

checks = dict(script=[], dispatch=[], lifetime=[], hitHistory=[])
stubs = set()
for l2, skill, window, interrupt, ended in itertools.product((0, 1), repeat=5):
    result = script_case(l2, skill, window, interrupt, ended)
    expected = '' if interrupt else 'W_WindAttackCancelEarly' if not l2 and not skill and window else 'W_Idle' if ended else ''
    assert result == expected
    checks['script'].append(dict(l2=l2, skill=skill, releaseWindow=window, interrupt=interrupt, ended=ended, result=result))

events, release_windows = [], []
for bundle in tae['bundles']:
    for track in bundle['taes']:
        if track['ID'] != 2901: continue
        for animation in track['animations']:
            if animation['ID'] not in (510000, 510005): continue
            for event in animation['events']:
                raw = bytes.fromhex(event['hex'])
                if event['Type'] == 2 and struct.unpack_from('<i', raw, 8)[0] in (6050, 6052, 6055, 6057, 6084, 6085, 6086, 6087):
                    events.append(dict(tae=2901, animation=animation['ID'], **event))
                if event['Type'] == 66 and struct.unpack_from('<i', raw)[0] == 100285:
                    release_windows.append(dict(tae=2901, animation=animation['ID'], **event))
assert len(events) == 8
assert len(release_windows) == 1 and release_windows[0]['animation'] == 510000
assert math.isclose(release_windows[0]['StartTime'], 13/30, abs_tol=1e-6)
assert math.isclose(release_windows[0]['EndTime'], 22/30, abs_tol=1e-6)
for event in events:
    for has_base, copies, active in itertools.product((0,1), (0,1,3), (0,1)):
        c = Dispatch()
        if has_base: c.insert(7010001)
        for _ in range(copies): c.insert(7011000)
        queue = []
        for _ in range(10):
            for id in queue: c.insert(id)
            c.qualify(); c.update(1/60)
            queue = c.emitted[:]; c.emitted.clear()
        c.q(OBJ+0x8018, OBJ+0x6000); c.q(OBJ+0x8108, OBJ+0x8200)
        c.u.mem_write(OBJ+0x8118, bytes([active])); c.u.mem_write(OBJ+0x811a, struct.pack('<H', 0x27))
        c.q(OBJ+0x8120, OBJ+0x8300); c.u.mem_write(OBJ+0x8200, bytes.fromhex(event['hex']))
        c.invoke(0x40cd80, [OBJ+0x8000, OBJ+0x8100])
        judge = struct.unpack_from('<i', bytes.fromhex(event['hex']), 8)[0]
        expected = bool(active and (copies if judge >= 6084 else has_base and not copies))
        assert bool(c.requests) == expected, (judge, has_base, copies, active, c.requests, c.nodes())
        if expected: assert c.requests[0]['behavior'] == 600000000+judge-6000 and c.requests[0]['instant']
        checks['dispatch'].append(dict(animation=event['animation'], judge=judge, base=has_base,
                                       copies=copies, active=active, requests=c.requests, nodes=c.nodes()))
        stubs.update(c.stubs)

def global_pointer(c, rva, value):
    page = rva & ~4095
    c.u.mem_map(BASE+page, 4096)
    c.u.mem_write(BASE+page, inputs.pe.get_data(page, 4096).ljust(4096, b'\0'))
    c.q(BASE+rva, value)

class Lifetime(Chain):
    def hook(self, u, address, size, user):
        pc = address - BASE
        def finish(value=0):
            u.reg_write(UC_X86_REG_RAX, value)
            sp = u.reg_read(UC_X86_REG_RSP)
            u.reg_write(UC_X86_REG_RIP, struct.unpack('<Q', u.mem_read(sp, 8))[0])
            u.reg_write(UC_X86_REG_RSP, sp+8)
        if pc == 0x26909a0:
            self.stubs.add('26909A0 security cookie; preserve return register')
            finish(u.reg_read(UC_X86_REG_RAX))
        elif address in (STOP+0x200, STOP+0x208, STOP+0x210):
            self.stubs.add('synthetic active-phase virtuals do not request early termination')
            finish()
        elif pc in (0x359c80, 0x355d20, 0x355fe0, 0x350410, 0x34b750, 0x33e770,
                    0x33e570, 0x353bb0, 0x362c00, 0x3482e0, 0x3482b0, 0x34da00, 0x353df0, 0x353cb0):
            self.stubs.add(hex(pc)+' scene/physics/visual fixture; no collision simulation')
            finish()
        else:
            super().hook(u, address, size, user)

for id in (30901001, 30901006, 30901111, 30901116):
    row = inputs.x['tables']['Bullet'][str(id)]
    assert row['HitBulletID'] == -1 and row['lifeRandomRange'] == 0
    assert math.isclose(struct.unpack_from('<f', bullets[id], 0x10)[0], row['life'])
    for fps in (30,60,120):
        c = Lifetime(inputs)
        global_pointer(c, 0x3c0ae30, OBJ+0xc000)
        instance, param, stages, vt = (OBJ+i for i in (0x8000,0x9000,0xa000,0xb000))
        c.u.mem_write(stages, struct.pack('<5i',1,2,3,4,4)); c.q(instance+0x88,stages)
        c.u.mem_write(instance+0x90, struct.pack('<ii',1,2)); c.q(instance+0x5c0,vt); c.q(instance+0x5f0,vt)
        for offset, callback in ((0x10,0x200),(0x18,0x208),(0x20,0x210)): c.q(vt+offset,STOP+callback)
        c.q(instance+0x5c8,param); c.u.mem_write(param,bullets[id])
        c.u.mem_write(instance+0x580,b'\x21'); c.u.mem_write(instance+0x600,struct.pack('<i',-1))
        c.invoke(0x350da0,[instance])
        lifetime = struct.unpack('<2f',c.u.mem_read(instance+0x2d4,8))
        assert lifetime == (row['life'],row['life'])
        for tick in range(8*fps):
            c.invoke(0x34f130,[instance],{UC_X86_REG_XMM1:1/fps})
            stage = struct.unpack('<i',c.u.mem_read(instance+0x90,4))[0]
            if stage >= 3: break
        assert stage == 3 and abs((tick+1)/fps-row['life']) <= 1.01/fps
        checks['lifetime'].append(dict(bullet=id,fps=fps,seconds=row['life'],expiresFrame=tick+1,finalStage=stage))
        stubs.update(c.stubs)

# Test native shared history in isolation. Full attack-instance reuse remains a
# separate question; do not turn this into an advertised collision frequency.
for fps in (30,60,120):
    for retry in (False,True):
        c = Chain(inputs); manager, parent = OBJ+0xc000, OBJ+0xc200
        global_pointer(c,0x3c0f428,manager)
        c.q(manager+8,parent); c.u.mem_write(parent+0x18,struct.pack('<I',1))
        for n in range(4):
            record=OBJ+0xd000+n*0x20
            c.invoke(0x52eb10,[record,1]); c.q(record+0x10,record+0x20 if n<3 else 0)
        c.q(manager+0x20,OBJ+0xd000)
        life=inputs.x['tables']['Bullet']['30901111']['dmgHitRecordLifeTime']
        assert life == inputs.x['tables']['Bullet']['30901116']['dmgHitRecordLifeTime'] == .5
        assert c.invoke(0x52efd0,[manager,0],{UC_X86_REG_XMM2:life}) == parent
        first=c.invoke(0x52de70,[parent,123])
        assert c.invoke(0x52e7b0,[parent,123]) & 255 == 1
        assert c.invoke(0x52e7b0,[parent,456]) & 255 == 0
        for tick in range(fps):
            if retry and tick==fps//5: assert c.invoke(0x52de70,[parent,123]) == first
            c.invoke(0x52e7f0,[parent],{UC_X86_REG_XMM1:1/fps})
            if c.invoke(0x52e7b0,[parent,123]) & 255 == 0: break
        assert abs((tick+1)/fps-life) <= 1.01/fps
        again=c.invoke(0x52de70,[parent,123])
        assert again == first and struct.unpack('<f',c.u.mem_read(again+8,4))[0] == life
        checks['hitHistory'].append(dict(fps=fps,retryAt=.2 if retry else None,expiresFrame=tick+1,seconds=life))
        stubs.update(c.stubs)

paths=[]
for judge in (6050,6052,6055,6057,6084,6085,6086,6087):
    behavior_id=600000000+judge-6000
    behavior=inputs.x['tables']['BehaviorParam_PC'][str(behavior_id)]
    assert behavior['refType']==1
    parent=inputs.x['tables']['Bullet'][str(behavior['refId'])]
    child=inputs.x['tables']['Bullet'][str(parent['HitBulletID'])]
    paths.append(dict(judge=judge,behavior=behavior_id,parent=behavior['refId'],child=parent['HitBulletID'],
                      fields={k:child[k] for k in ('life','hitRadius','hitRadiusMax','dmgHitRecordLifeTime','atkId_Bullet',
                              'intervalCreateBulletId','intervalCreateTimeMin','intervalCreateTimeMax','isUseSharedHitList')}))
assert [(p['judge'],p['parent'],p['child']) for p in paths] == [
    (6050,30901000,30901001),(6052,30901002,30901003),
    (6055,30901005,30901006),(6057,30901007,30901008),
    (6084,30901110,30901111),(6085,30901112,30901113),
    (6086,30901115,30901116),(6087,30901117,30901118)]
assert [p['fields']['life'] for p in paths] == [1,1,1,1,7,7,4,4]
attack_comparisons=[]
for normal, extended in ((600000050,600000082),(600000055,600000083)):
    before,after=(inputs.x['tables']['AtkParam_Pc'][str(i)] for i in (normal,extended))
    differences={k:[v,after[k]] for k,v in before.items() if v!=after[k]}
    attack_comparisons.append(dict(normal=normal,extended=extended,differences=differences))
output=dict(schema=1,exeSha256=sha(inputs.raw),regulationSha256=inputs.x['hashes']['regulation.bin'],
            paramSha256=sha(inputs.param),rawTableHashes={k:sha(v) for k,v in raw_tables.items()},
            scriptSha256=sha(raw_script),functionSha256=sha(function.encode()),functionLine=source[:start].count('\n')+1,
            animationSha256=tae['bundles'][0]['sha256'],behavior={k:graph.metadata[k] for k in
                ('bundleSha256','hkxSha256','registrySha256','metadataOnly','mismatches')},states=graph_states,
            attackComparisons=attack_comparisons,root=7011000,leaf=7011001,base=7010001,events=events,releaseWindows=release_windows,paths=paths,
            native=dict(dispatch='40CD80',behaviorResolver='668B30',initializeLifetime='350DA0',
                        updateLifetime='34F130',phaseTransition='355270',historyCreate='52EFD0',
                        historyInsert='52DE70',historyQuery='52E7B0',historyUpdate='52E7F0'),
            checks=checks,stubs=sorted(stubs|{'Lua input/interrupt fixtures; real WindAttackStart_onUpdate body',
                'pooled history object with refcount 1; native entry constructors and pool lifecycle',
                'held/released animation schedule supplied; no behavior VM, collision, damage or network simulation'}),
            gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS:',{k:len(v) for k,v in checks.items()})
