"""Trace the Duchess skill's temporary invulnerability through HKS and TAE.

Runs the original script in Lua and the original PC effect/animation dispatcher
instructions in Unicorn. Actor identity, animation scheduling and input are
fixtures; this does not simulate an actual hit or run the game.
"""
import argparse
import ctypes
import ctypes.util
import json
import math
import struct
from pathlib import Path
from unicorn.x86_const import *
from native_effect_runtime import BASE, OBJ, STOP, Chain, Inputs, sha

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('exe', type=Path)
p.add_argument('extracted', type=Path)
p.add_argument('script', type=Path)
p.add_argument('animations', type=Path)
p.add_argument('output', type=Path)
a = p.parse_args()
inputs = Inputs(a.exe, a.extracted)
raw = a.script.read_bytes()
assert sha(raw) == '786f8a7bc89452d9531e2299b224c8945701c422437eca9aacbeb10a57a17f4d'
source = raw.decode('utf-8-sig').replace('\r\n', '\n')
start = source.index('function ExecDejavu()')
function = source[start:source.index('\nfunction ', start + 1)]
update_start = source.index('function Update()')
update = source[update_start:source.index('\nfunction ', update_start + 1)]
assert 'ExecChangeDejavuBlend()\n    ExecDejavu()' in update
defines = a.script.with_name('common_define.hks').read_bytes()
assert 'HERO_SPEED = 4' in defines.decode('utf-8-sig')
root, leaf = inputs.spells['7500300'], inputs.spells['7500301']
assert leaf['stateInfo'] == 2394 and leaf['spCategory'] == root['spCategory'] == 20
assert math.isclose(leaf['effectEndurance'], .4, rel_tol=1e-6)
assert leaf['replaceSpEffectId'] == leaf['cycleOccurrenceSpEffectId'] == -1
tae = json.loads(a.animations.read_text())
assert tae['bundles'][0]['sha256'] == '1410035ad79edb410fa41420ec259fcb4a1037d748c9c4a3b6ae8d1366c76d0f'
events = [dict(tae=t['ID'], animation=an['ID'], **e)
          for b in tae['bundles'] for t in b['taes'] for an in t['animations'] for e in an['events']
          if e['Type'] == 0 and bytes.fromhex(e['hex']) == struct.pack('<ifiBBH', 8, 0, -1, 6, 0, 2394)]
assert [(e['tae'], e['animation'], e['index']) for e in events] == [
    (2903, 539000, 5), (2903, 539001, 2), (2903, 539005, 5), (2903, 539100, 5), (2903, 539105, 5)]
assert all(e['StartTime'] == 0 and e['EndTime'] == 100 for e in events)

lua = ctypes.CDLL(ctypes.util.find_library('lua5.4'))
lua.luaL_newstate.restype = ctypes.c_void_p
lua.luaL_openlibs.argtypes = [ctypes.c_void_p]
lua.luaL_loadstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
lua.lua_pcallk.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_ssize_t, ctypes.c_void_p]
lua.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_size_t)]
lua.lua_tolstring.restype = ctypes.c_char_p
lua.lua_close.argtypes = [ctypes.c_void_p]

def script_case(hero=4, blend=0, ready=1, hp=1, pressed=1, equipped=1, style=0, boost=0):
    program = '''
TRUE=1; FALSE=0; HERO_SPEED=4; HAND_LEFT_BOTH=1; HAND_RIGHT_BOTH=2
GetHeroID=1; IsCharacterSkillReady=2; GetHP=3; ActionDuration=4
GetStateChangeType=5; GetSpEffectID=6; AddSpEffect=7; ResetInputQueue=8; ACTION_ARM_SKILL=9
local inputs={%d,%d,%d,%d,%d,%d}
local vars={AddDejavuBlend=%d,IndexDejavuBlend=-1,IsRelic_Dejavu=-1}
local added={};local resets=0
c_Style=%d
function env(key,id)
  if key==5 then assert(id==2271) end
  if key==6 then assert(id==7500300) end
  return inputs[key]
end
function GetVariable(k) return vars[k] end
function SetVariable(k,v) vars[k]=v end
function act(key,id)
  if key==AddSpEffect then table.insert(added,id) else assert(key==ResetInputQueue);resets=resets+1 end
end
''' % (hero, ready, hp, pressed, boost, equipped, blend, style)
    program += function + '''
local first=ExecDejavu();local second=ExecDejavu()
return string.format('{"first":%d,"second":%d,"added":[%s],"resets":%d,"blend":%d,"style":%d,"boost":%d}',
first,second,table.concat(added,","),resets,vars.AddDejavuBlend,vars.IndexDejavuBlend,vars.IsRelic_Dejavu)
'''
    state = lua.luaL_newstate()
    try:
        lua.luaL_openlibs(state)
        assert lua.luaL_loadstring(state, program.encode()) == 0
        status = lua.lua_pcallk(state, 0, 1, 0, 0, None)
        result = lua.lua_tolstring(state, -1, None)
        assert status == 0, result
        return json.loads(result)
    finally:
        lua.lua_close(state)

checks = dict(script=[], dispatch=[], lifecycle=[])
for hero in range(11):
    for equipped in (0, 1):
        result = script_case(hero=hero, equipped=equipped)
        assert result['added'] == ([7500301] if hero == 4 and equipped else [])
        assert result['resets'] == result['first'] == int(hero == 4) and result['second'] == 0
        checks['script'].append(dict(hero=hero, equipped=equipped, result=result))
for gate, value in [('blend', 1), ('blend', 2), ('ready', 0), ('hp', 0), ('pressed', 0)]:
    result = script_case(**{gate: value})
    assert result['added'] == [] and result['resets'] == result['first'] == result['second'] == 0
    checks['script'].append(dict(gate=gate, value=value, result=result))
for style in (0, 1, 2):
    for boost in (0, 1):
        result = script_case(style=style, boost=boost)
        assert result['style'] == int(style != 0) and result['boost'] == boost
        assert result['added'] == [7500301] and result['second'] == 0
        checks['script'].append(dict(style=style, boost=boost, result=result))

class Evasion(Chain):
    def __init__(self):
        super().__init__(inputs)
        self.q(OBJ + 0x6800, STOP + 0x100)  # Owner virtual +600: unused actor extension.
        self.q(OBJ + 0x6190, OBJ)
        self.q(OBJ + 0x61b8, OBJ + 0xd000)
        self.q(OBJ + 0xd008, OBJ + 0xd200)
        self.q(OBJ + 0x6060, OBJ + 0xd400)
        self.q(OBJ + 0xd4c8, OBJ + 0xd600)
        self.q(OBJ + 0x8018, OBJ + 0x6000)
        self.q(OBJ + 0x8108, OBJ + 0x8200)

    def flag(self, event):
        self.q(OBJ + 0xd258, 0)  # Fresh per-frame action flags, not an artificial state predicate.
        self.u.mem_write(OBJ + 0x8200, bytes.fromhex(event['hex']))
        self.u.mem_write(OBJ + 0x8118, b'\x01')
        self.invoke(0x410ca0, [OBJ + 0x8000, OBJ + 0x8100])
        return struct.unpack('<Q', self.u.mem_read(OBJ + 0xd258, 8))[0]

stubs = set()
for event in events:
    for roots, leaves, elapsed in [(0, 0, 0), (1, 0, 0), (1, 1, 0), (3, 3, 0), (1, 1, .5)]:
        c = Evasion()
        for _ in range(roots): c.insert(7500300)
        for _ in range(leaves): c.insert(7500301)
        c.qualify(); c.update(elapsed)
        if elapsed:
            # Native expiry marks then removes the node on subsequent updates.
            for _ in range(3): c.qualify(); c.update(.001)
        value = c.flag(event)
        assert value == (2 if leaves and elapsed < .4 else 0), (roots, leaves, elapsed, value, c.nodes())
        checks['dispatch'].append(dict(animation=event['animation'], roots=roots, leaves=leaves,
                                       elapsed=elapsed, flags=value, nodes=c.nodes()))
        stubs.update(c.stubs)
for fps in (30, 60, 120):
    for copies in (1, 3):
        for reapply in (False, True):
            c = Evasion()
            for _ in range(copies): c.insert(7500300); c.insert(7500301)
            c.qualify()
            frames = []
            for frame in range(fps):
                if reapply and frame == fps // 5:
                    c.insert(7500301)
                c.qualify()
                if c.flag(events[0]): frames.append(frame)
                c.update(1 / fps)
            assert frames == list(range(frames[0], frames[-1] + 1)), (fps, copies, reapply, frames)
            expected = .6 if reapply else .4
            assert abs(len(frames) / fps - expected) <= 3.01 / fps, (fps, copies, reapply, frames)
            assert [(n['id'], n['lifetime']) for n in c.nodes()] == [(7500300, -1.0)], c.nodes()
            checks['lifecycle'].append(dict(fps=fps, copies=copies, reapplyAt=.2 if reapply else None,
                                            activeFrames=frames, expectedDuration=expected))
            stubs.update(c.stubs)

output = dict(schema=1, exeSha256=sha(inputs.raw), regulationSha256=inputs.x['hashes']['regulation.bin'],
              paramSha256=sha(inputs.param), scriptSha256=sha(raw), definesSha256=sha(defines),
              functionSha256=sha(function.encode()), functionLine=source[:start].count('\n') + 1,
              updateFunctionSha256=sha(update.encode()), animationSha256=tae['bundles'][0]['sha256'],
              root=7500300, leaf=7500301, state=2394, duration=.4, events=events,
              native=dict(dispatch='410CA0', jumpTable='40D390', stateQuery='508E20',
                          branch='40D633', actionFlagsOffset='58', invincibilityMask=2),
              checks=checks, stubs=sorted(stubs | {'Lua input/variable/act fixtures; real ExecDejavu body',
                  'owner +600 returns null unused extension; per-frame action flags initially clear',
                  'active TAE event schedule supplied; no hit, damage or multiplayer simulation'}),
              gameplayVerified=False)
a.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
print('PASS:', {k: len(v) for k, v in checks.items()}, 'original script and native dispatch/lifetime checks')
