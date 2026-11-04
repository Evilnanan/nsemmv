"""Trace Revenant's sacrifice, ally restoration and revival recovery.

Animation dispatch, Behavior resolution, emitter timing, effect insertion and HP
getters execute pinned PC instructions. Character identity and successful in-range
delivery are fixtures; this does not run collision detection or multiplayer.
"""
import ctypes
import ctypes.util
import argparse
import json
import math
import struct
from pathlib import Path
from unicorn.x86_const import *
from native_effect_runtime import BASE, OBJ, STOP, Chain, Inputs, sha

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('exe', type=Path)
p.add_argument('extracted', type=Path)
p.add_argument('assets', type=Path)
p.add_argument('animations', type=Path)
p.add_argument('script', type=Path)
p.add_argument('output', type=Path)
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
bullet = inputs.x['tables']['Bullet']['30905110']
behavior = inputs.x['tables']['BehaviorParam_PC']['700000280']
attack = inputs.x['tables']['AtkParam_Pc']['790000003']
r = inputs.spells
assert behavior['refType'] == 1 and behavior['refId'] == 30905110
assert bullet['atkId_Bullet'] == 790000003 and bullet['hitRadius'] == 30
assert bullet['spEffectIDForShooter'] == 7010901
assert [bullet['spEffectId' + str(i)] for i in range(5)] == [7010902, 7010905, 0, 0, 0]
assert bullet['numShoot'] == 1 and bullet['shootInterval'] == 0 and bullet['isEndlessHit'] == 0
assert struct.unpack_from('<i', bullets[30905110], 0x60)[0] == 7010901
assert attack['selfTarget'] == 0 and attack['friendlyTarget'] == 1
assert r['7010900']['stateInfo'] == 2023 and r['7010900']['spCategory'] == 20
assert r['7010901']['changeHpRate'] == 50 and r['7010901']['motionInterval'] == 1
assert r['7010902']['changeHpRate'] == r['7010906']['changeHpRate'] == -100
assert r['7010902']['effectTargetSelfTarget'] == r['7010902']['effectTargetOpposeTarget'] == 0
assert r['7010902']['effectTargetFriendlyTarget'] == 1
assert r['7010906']['effectEndurance'] == .5 and r['7010906']['motionInterval'] == 0
assert all(r[str(i)]['categoryPriority'] == 54 and r[str(i)]['spCategory'] == 201 for i in [7010905,7010906,7010909])
events = [dict(tae=t['ID'], animation=an['ID'], **e)
          for b in tae['bundles'] for t in b['taes'] if t['ID'] == 2905
          for an in t['animations'] if an['ID'] == 650000
          for e in an['events'] if e['Type'] == 2 and struct.unpack_from('<i',bytes.fromhex(e['hex']),8)[0] == 7280]
assert len(events) == 1 and events[0]['index'] == 21
assert struct.unpack_from('<h', bytes.fromhex(events[0]['hex']),14)[0] == 2023
assert bytes.fromhex(events[0]['hex'])[13] == 0

class Sacrifice(Chain):
    def __init__(self):
        super().__init__(inputs)
        self.requests, self.emissions, self.frame = [], [], 0
        self.emission_success = True
        address = BASE + 0x343315 + 7 + 0x38cbd8c
        self.mapped(self.u, 0, address, 8, 0, None)
        self.q(address, OBJ + 0xf000)
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
            assert id == 700000280
            u.mem_write(OBJ + 0xb800, behaviors[id])
            self.q(u.reg_read(UC_X86_REG_RCX) + 8, OBJ + 0xb800)
            finish()
        elif pc == 0x3975d0:
            self.stubs.add('3975D0 Behavior request recorder; active/stop and conditional-state gates are native')
            payload = bytes(u.mem_read(u.reg_read(UC_X86_REG_R9), 18))
            self.requests.append(dict(behavior=u.reg_read(UC_X86_REG_RDX),
                                      active=bool(payload[16]), instant=bool(payload[17]), payload=payload.hex()))
            finish(1)
        elif pc == 0xe87800:
            self.stubs.add('E87800 actual Bullet row lookup')
            id = u.reg_read(UC_X86_REG_RDX) & 0xffffffff
            assert id == 30905110
            u.mem_write(OBJ + 0xb000, bullets[id])
            ptr = u.reg_read(UC_X86_REG_RCX)
            u.mem_write(ptr, struct.pack('<QI', OBJ + 0xb000, id))
            finish(ptr)
        elif pc == 0x347700:
            self.stubs.add('347700 controlled emission result; no projectile collision execution')
            self.emissions.append(self.frame)
            finish(int(self.emission_success))
        elif pc == 0x518f30:
            self.stubs.add('518F30 source-owner lookup fixture')
            finish(OBJ + 0x6000)
        elif pc == 0x3c7f40:
            self.stubs.add('3C7F40 shooter effect request recorder; next-frame delivery fixture')
            assert u.reg_read(UC_X86_REG_RCX) == OBJ + 0x6000
            self.emitted.append(u.reg_read(UC_X86_REG_RDX) & 0xffffffff)
            finish()
        else:
            super().hook(u, address, size, user)

    def hp_packet(self, maximum):
        # Preserve the live effects; omit unrelated physical-owner HUD/network
        # predicates. This is resource aggregation, not full damage delivery.
        self.q(OBJ + 0x10, 0)
        self.invoke(0x506ec0, [OBJ, maximum, OBJ + 0x800, OBJ + 0x808, OBJ + 0x820, 0])
        self.q(OBJ + 0x10, OBJ + 0x6000)
        return list(struct.unpack('<7i', self.u.mem_read(OBJ + 0x820, 28)))

checks = dict(trigger=[], emission=[], hp=[], lifecycle=[], script=[])
stubs = set()
for copies in (0, 1, 3):
    for active in (0, 1):
        c = Sacrifice()
        for _ in range(copies): c.insert(7010900)
        c.qualify(); c.update(0)
        c.q(OBJ + 0x8018, OBJ + 0x6000)
        c.q(OBJ + 0x8108, OBJ + 0x8200)
        c.u.mem_write(OBJ + 0x8118, bytes([active]))
        c.u.mem_write(OBJ + 0x811a, struct.pack('<H', 0x27))
        c.q(OBJ + 0x8120, OBJ + 0x8300)
        c.u.mem_write(OBJ + 0x8200, bytes.fromhex(events[0]['hex']))
        c.invoke(0x40cd80, [OBJ + 0x8000, OBJ + 0x8100])
        assert len(c.requests) == bool(copies and active)
        if c.requests:
            assert c.requests[0]['behavior'] == 700000280 and c.requests[0]['instant']
        checks['trigger'].append(dict(equipmentCopies=copies, active=active, requests=c.requests))
        stubs.update(c.stubs)

for fps in (30, 60, 120):
    for success in (False, True):
        c = Sacrifice(); c.emission_success = success
        slot = OBJ + 0x4000
        c.u.mem_write(slot + 0x329, b'\x01')
        c.u.mem_write(slot + 0x334, struct.pack('<I',30905110))
        c.u.mem_write(slot + 0x494, b'\x01')
        for frame in range(fps):
            c.frame = frame
            c.invoke(0x343280, [slot], {UC_X86_REG_XMM1: 1 / fps})
        assert c.emissions == [0]
        assert c.emitted == ([7010901] if success else [])
        checks['emission'].append(dict(fps=fps, success=success, attempts=c.emissions, shooterEffects=c.emitted))
        stubs.update(c.stubs)

for leaf in (7010901, 7010902, 7010906):
    for maximum in (1,99,137,1000):
        c = Sacrifice(); c.insert(leaf); c.qualify(); c.update(0)
        packet = c.hp_packet(maximum)
        assert packet[0] == (-math.trunc(maximum * .5) if leaf == 7010901 else maximum)
        checks['hp'].append(dict(leaf=leaf, maximum=maximum, packet=packet))
        stubs.update(c.stubs)

for fps in (30,60,120):
    for name, ids in [('sacrifice',[7010901]),('ally',[7010902]),
                      ('revival',[7010905,7010906]),('clear-on-down',[7010905,7010909]),
                      ('duplicate-marker',[7010905,7010905])]:
        c = Sacrifice()
        for id in ids: c.insert(id)
        restores = []
        for frame in range(fps):
            c.qualify(); c.update(0 if frame == 0 else 1 / fps)
            packet = c.hp_packet(1000)
            if packet[0]: restores.append(dict(frame=frame, delta=packet[0]))
        if name in ('sacrifice','ally'):
            assert restores == [dict(frame=0, delta=-500 if name == 'sacrifice' else 1000)]
        elif name == 'revival':
            assert len(restores) >= fps / 2 and all(h['delta'] == 1000 for h in restores)
            # Expiration/removal crosses up to two update boundaries.
            assert .5 <= restores[-1]['frame'] / fps <= .5 + 2 / fps + 1e-6, (fps, restores)
        else:
            assert not restores
        assert [n['id'] for n in c.nodes()] == ([7010905] if name == 'duplicate-marker' else [])
        checks['lifecycle'].append(dict(name=name,fps=fps,restores=restores,remaining=c.nodes()))
        stubs.update(c.stubs)

script_raw = a.script.read_bytes()
assert sha(script_raw) == '786f8a7bc89452d9531e2299b224c8945701c422437eca9aacbeb10a57a17f4d'
script = script_raw.decode('utf-8-sig').replace('\r\n','\n')
lua = ctypes.CDLL(ctypes.util.find_library('lua5.4'))
lua.luaL_newstate.restype = ctypes.c_void_p
lua.luaL_openlibs.argtypes = [ctypes.c_void_p]
lua.luaL_loadstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
lua.lua_pcallk.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_ssize_t, ctypes.c_void_p]
lua.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_size_t)]
lua.lua_tolstring.restype = ctypes.c_char_p
lua.lua_close.argtypes = [ctypes.c_void_p]
functions = {}
for name in ('NearDeathStart_onActivate', 'NearDeathRevival_onActivate'):
    start = script.index('function ' + name + '(')
    body = script[start:script.index('\nfunction ', start + 1)]
    functions[name] = dict(sha256=sha(body.encode()), line=script[:start].count('\n') + 1)
    for present in (False,True):
        program = """
TRUE=1; FALSE=0; GetSpEffectID=1; AddSpEffect=2
local added={}
function ResetRightArmAdd() end
function SetVariable() end
function ActivateRightArmAdd() end
function env(kind,id) assert(kind==GetSpEffectID and id==7010905); return %s end
function act(kind,id) assert(kind==AddSpEffect); table.insert(added,id) end
""" % ('TRUE' if present else 'FALSE')
        program += body + '\n' + name + '()\nreturn "["..table.concat(added,",").."]"'
        state = lua.luaL_newstate()
        try:
            lua.luaL_openlibs(state)
            assert lua.luaL_loadstring(state, program.encode()) == 0
            status = lua.lua_pcallk(state,0,1,0,0,None)
            value = lua.lua_tolstring(state,-1,None)
            assert status == 0, value
            emitted = json.loads(value)
        finally:
            lua.lua_close(state)
        expected = [705021,7010909,42206,30101] if name == 'NearDeathStart_onActivate' else ([7010906] if present else [])
        assert emitted == expected
        checks['script'].append(dict(function=name,markerPresent=present,emitted=emitted))
stubs.add('Lua: supplied 7010905 presence; act records effects; animation resets and variables are no-ops')
rows = {str(i): {k:r[str(i)][k] for k in ['stateInfo','spCategory','categoryPriority','effectEndurance','motionInterval','changeHpRate','changeHpPoint','effectTargetSelfTarget','effectTargetFriendlyTarget','effectTargetOpposeTarget','effectTargetPcDeceased']}
        for i in [7010900,7010901,7010902,7010905,7010906,7010909]}
output = dict(schema=1, exeSha256=sha(inputs.raw), regulationSha256=inputs.x['hashes']['regulation.bin'],
    paramSha256=sha(inputs.param), animationSha256=tae['bundles'][0]['sha256'], scriptSha256=sha(script_raw),
    root=7010900, rows=rows, events=events, functions=functions,
    bullet={k:bullet[k] for k in ['hitRadius','atkId_Bullet','spEffectId0','spEffectId1','spEffectIDForShooter','shootInterval','numShoot']},
    behavior=behavior, targetFlags={k:attack[k] for k in ['selfTarget','friendlyTarget','opposeTarget']},
    checks=checks, stubs=sorted(stubs), gameplayVerified=False)
a.output.write_text(json.dumps(output, indent=2) + '\n')
print('PASS:', {k:len(v) for k,v in checks.items()}, 'Revenant sacrifice checks')
