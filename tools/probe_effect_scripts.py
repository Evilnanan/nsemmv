"""Execute reviewed active HKS function branches in Lua with explicit engine stubs.

This verifies script control flow, not the game VM, hit delivery or network play.
"""
import argparse
import ctypes
import ctypes.util
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('script', type=Path)
p.add_argument('extracted', type=Path)
p.add_argument('output', type=Path)
a = p.parse_args()
raw = a.script.read_bytes()
assert hashlib.sha256(raw).hexdigest() == '786f8a7bc89452d9531e2299b224c8945701c422437eca9aacbeb10a57a17f4d'
source = raw.decode('utf-8-sig').replace('\r\n', '\n')
start = source.index('function WeaponChangeCommonFunction(')
end = source.index('\nfunction ', start + 1)
function = source[start:end]
hand_start = source.index('function ExecWeaponChange(')
hand_end = source.index('\nfunction ', hand_start + 1)
hand_function = source[hand_start:hand_end]
assert 'RELIC_WEAPONCHANGE_ENCHANT = 0\n        kind = GetWeaponChangeType(HAND_RIGHT)' in hand_function
assert 'RELIC_WEAPONCHANGE_ENCHANT = 1\n        kind = GetWeaponChangeType(HAND_LEFT)' in hand_function
x = json.loads(a.extracted.read_text())
assert x['hashes']['regulation.bin'] == '3305ac374b4da1db440e2b6644bc2c3c0ae96b98df9627f1a0e7a2b06d265c06'
spells = x['tables']['SpEffectParam']
lua = ctypes.CDLL(ctypes.util.find_library('lua5.4'))
lua.luaL_newstate.restype = ctypes.c_void_p
lua.luaL_openlibs.argtypes = [ctypes.c_void_p]
lua.luaL_loadstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
lua.lua_pcallk.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_ssize_t, ctypes.c_void_p]
lua.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_size_t)]
lua.lua_tolstring.restype = ctypes.c_char_p
lua.lua_close.argtypes = [ctypes.c_void_p]

def execute(hand, roll, missing=None, blocking=None):
    present = {7035700, 7035701} - ({missing} if missing else set())
    if blocking:
        present.add(blocking)
    program = '''
TRUE=1; FALSE=0; GetSpEffectID=1; AddSpEffect=2
function SetAIActionState() end
function ExecPassiveAction() return TRUE end
local present={%s}
local added={}
function env(_, id) return present[id] and TRUE or FALSE end
function act(_, id) table.insert(added, id) end
math.random=function(lo, hi) assert(lo==1 and hi==100); return %d end
RELIC_WEAPONCHANGE_ENCHANT=%d
''' % (','.join('[%d]=true' % id for id in sorted(present)), roll, hand)
    program += function + '\nWeaponChangeCommonFunction(0)\nreturn "["..table.concat(added,",").."]"'
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

cases = []
counts = {}
for hand in (0, 1):
    for roll in range(1, 101):
        emitted = execute(hand, roll)
        assert len(emitted) == 2
        cooldown, seed = emitted
        assert cooldown in range(7035718, 7035722)
        counts[cooldown] = counts.get(cooldown, 0) + 1
        assert spells[str(cooldown)]['effectEndurance'] < .101
        cases.append(dict(hand=hand, roll=roll, emitted=emitted))
    for missing in (7035700, 7035701):
        emitted = execute(hand, 75, missing=missing)
        assert emitted == []
        cases.append(dict(hand=hand, missing=missing, emitted=emitted))
    for blocking in range(7035718, 7035722):
        emitted = execute(hand, 75, blocking=blocking)
        assert emitted == []
        cases.append(dict(hand=hand, blocking=blocking, emitted=emitted))
branches = []
for cooldown, field, name in [(7035718, 'magicAttackPower', '魔力'), (7035719, 'fireAttackPower', '火'),
                              (7035720, 'thunderAttackPower', '雷'), (7035721, 'darkAttackPower', '圣')]:
    hands = []
    for hand in (0, 1):
        seeds = {r['emitted'][1] for r in cases if r['hand'] == hand and r['emitted'] and r['emitted'][0] == cooldown}
        assert len(seeds) == 1
        seed = seeds.pop()
        leaf = int(spells[str(seed)]['cycleOccurrenceSpEffectId'])
        row = spells[str(leaf)]
        assert row[field] == 20 and row['effectEndurance'] == 10
        assert row['spCategory'] == (162 if hand == 0 else 163)
        hands.append(dict(hand=hand, seed=seed, leaf=leaf, category=int(row['spCategory'])))
    branches.append(dict(cooldown=cooldown, chance=counts[cooldown] / 2, field=field, name=name, power=20,
                         duration=10, hands=hands))
assert [b['chance'] for b in branches] == [26, 25, 25, 24]
a.output.write_text(json.dumps(dict(schema=1, regulationSha256=x['hashes']['regulation.bin'],
    script='action/script/c0000.hks', scriptSha256=hashlib.sha256(raw).hexdigest(),
    functionSha256=hashlib.sha256(function.encode()).hexdigest(), functionLine=source[:start].count('\n') + 1,
    handSelectionFunctionSha256=hashlib.sha256(hand_function.encode()).hexdigest(),
    effects={'7035700':dict(branches=branches, cases=cases)},
    stubs=['env: supplied held effects', 'act: records emitted effects', 'math.random: enumerates 1..100',
           'SetAIActionState: no-op', 'ExecPassiveAction: exits after the inspected branch'], gameplayVerified=False),
    ensure_ascii=False, indent=2) + '\n')
print(f'PASS: {len(cases)} actual HKS branch cases; {len(branches)} PARAM chains')
