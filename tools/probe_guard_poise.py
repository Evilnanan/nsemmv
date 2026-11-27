"""Trace successful-guard poise effects through actual HKS and native lifecycle.

Damage-type symbols, equipment inventory, allocation and the effect-grant queue
are explicit fixtures. Actual Lua gate, selection, replacement, timers and poise
aggregation execute; no full animation scheduling, collision or gameplay.
"""
import argparse
import ctypes
import ctypes.util
import itertools
import json
import math
import re
import struct
from pathlib import Path
from native_effect_runtime import *

p = argparse.ArgumentParser(description=__doc__)
for name in ('exe', 'extracted', 'script', 'output'):
    p.add_argument(name, type=Path)
a = p.parse_args()
x = Inputs(a.exe, a.extracted)
raw = a.extracted.with_suffix('.AttachEffectParam.param').read_bytes()
rows = Inputs.table(raw, 0x44)
# Equipment identity/allocation fixture shared with probe_equipped_exclusivity.
MAN=OBJ+0x8000;OUT=OBJ+0x9000;BITS=OBJ+0x9100
class Selection(Chain):
 def __init__(self,slots,hero=1):
  super().__init__(x);self.slots=slots;self.hero=hero;self.cache={};self.q(OBJ+0x7118,STOP+0x900)
  self.q(MAN,OBJ+0x8100);self.q(MAN+8,OBJ+0x6000)
  self.q(OBJ+0x8158,STOP+0x901);self.q(OBJ+0x8160,STOP+0x902);self.q(OBJ+0x6378,STOP+0x903)
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v&0xffffffffffffffff);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if pc==0x214f3e0:ret(OBJ+0x7000)
  elif address==STOP+0x900:
   ptr=u.reg_read(UC_X86_REG_RDX);u.mem_write(ptr,struct.pack('<I',32));ret(ptr)
  elif pc==0x2081b0:
   assert u.reg_read(UC_X86_REG_R9)==144
   ptr=u.reg_read(UC_X86_REG_RCX);self.q(ptr+8,BITS);self.q(ptr+0x10,144);self.q(ptr+0x18,160);self.q(ptr+0x20,144);u.mem_write(BITS,bytes(20));ret(ptr)
  elif pc==0x1fe1c0:ret(0)
  elif pc==0x325c40:
   self.allocated+=0x100;ret(self.allocated)
  elif address==STOP+0x901:
   index=u.reg_read(UC_X86_REG_RDX);ret(index+1 if index<len(self.slots) else 0xffffffff)
  elif address==STOP+0x902:ret(int(1<=u.reg_read(UC_X86_REG_RDX)<=len(self.slots)))
  elif address==STOP+0x903:ret(self.hero)
  elif pc==0x69e570:
   ptr=u.reg_read(UC_X86_REG_RCX);handle=struct.unpack('<I',u.mem_read(u.reg_read(UC_X86_REG_RDX),4))[0]
   effects=self.slots[handle-1];instance=OBJ+0xa000+(handle-1)*0x80
   u.mem_write(instance+0x18,struct.pack('<3i',*(effects+[-1]*3)[:3]));u.mem_write(ptr,bytes(24));self.q(ptr+8,instance);u.mem_write(ptr+0x10,struct.pack('<I',0x80000000|2000100));ret(ptr)
  elif pc==0x69e5a0:ret()
  elif pc==0xe6e430:
   ptr=u.reg_read(UC_X86_REG_RCX);id=u.reg_read(UC_X86_REG_RDX)&0xffffffff
   if id in rows and id not in self.cache:
    self.cache[id]=OBJ+0x10000+len(self.cache)*0x100;u.mem_write(self.cache[id],rows[id])
   self.q(ptr,self.cache.get(id,0));u.mem_write(ptr+8,struct.pack('<I',id));ret(ptr)
  else:super().hook(u,address,size,user)
 def select(self):
  self.invoke(0x4fea30,[MAN,OUT]);bits=int.from_bytes(self.u.mem_read(BITS,20),'little');return [i for i in range(144) if bits>>i&1]


lua = ctypes.CDLL(ctypes.util.find_library('lua5.4'))
lua.luaL_newstate.restype = ctypes.c_void_p
lua.luaL_openlibs.argtypes = [ctypes.c_void_p]
lua.luaL_loadstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
lua.lua_pcallk.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_ssize_t, ctypes.c_void_p]
lua.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_size_t)]
lua.lua_tolstring.restype = ctypes.c_char_p
lua.lua_close.argtypes = [ctypes.c_void_p]

def execute_lua(program):
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


raw_script = a.script.read_bytes()
assert sha(raw_script) == '96339bb15f57559cd42a940d616fcc2a18a10f50845cfc22b46b356ab66c3b29'
source = raw_script.decode('utf-8-sig').replace('\r\n', '\n')
functions = {match[1]: match[0] for match in re.finditer(r'^function (\w+)\([^\n]*\).*?(?=^function |\Z)', source, re.M | re.S)}
guard_function = functions['ExecGuardBuff']
callers = {name: sha(body.encode()) for name, body in functions.items() if 'ExecGuardBuff()' in body and name != 'ExecGuardBuff'}
assert len(callers) == 21
damage_types = sorted(set(re.findall(r'\bDAMAGE_TYPE_\w+', source)))
script_checks = []
for damage_type in damage_types:
    program = '''
FALSE=0; GetReceivedDamageType="received"; AddSpEffect="grant"
DAMAGE_TYPE_GUARD="DAMAGE_TYPE_GUARD"
local added={}
function env(kind) assert(kind==GetReceivedDamageType); return %s end
function act(kind,id) assert(kind==AddSpEffect); table.insert(added,id) end
''' % json.dumps(damage_type)
    emitted = execute_lua(program + guard_function + '\nassert(ExecGuardBuff()==FALSE)\nreturn "["..table.concat(added,",").."]"')
    expected = [7030601, 7036101, 8650001, 8650101, 8652001, 8652011, 8652021, 8652101, 8652111, 8652121] if damage_type == 'DAMAGE_TYPE_GUARD' else []
    assert emitted == expected
    script_checks.append(dict(damageType=damage_type, emitted=emitted))
guard_grants = next(r['emitted'] for r in script_checks if r['damageType'] == 'DAMAGE_TYPE_GUARD')
families = []
for root, state, rate in ((8652000, 2077, .88), (8652010, 2243, .82), (8652020, 2244, .76)):
    attach = x.x['tables']['AttachEffectParam'][str(root)]
    assert attach['passiveSpEffectId_1'] == root and attach['exclusivityId'] == -1
    assert all(attach[k] == -1 for k in ('passiveSpEffectId_2', 'passiveSpEffectId_3', 'permanentSpEffectId'))
    base, seed, leaf = [x.spells[str(root + offset)] for offset in range(3)]
    assert (base['stateInfo'], base['spCategory'], base['effectEndurance']) == (state, 10, -1)
    assert seed['spCategory'] == 10 and math.isclose(seed['effectEndurance'], .1, rel_tol=1e-6)
    assert seed['replaceSpEffectId'] == root + 2
    assert (leaf['spCategory'], leaf['stateInfo'], leaf['effectEndurance']) == (20, 0, 10)
    assert math.isclose(leaf['toughnessDamageCutRate'], rate, rel_tol=1e-6)
    assert math.isclose(struct.unpack_from('<f', x.rows[root + 2], 0x1b4)[0], rate, rel_tol=1e-6)
    assert all(r['invocationConditionsStateChange1'] == state for r in (seed, leaf))
    assert all(r['invocationConditionsStateChange' + str(i)] == 0 for r in (base, seed, leaf) for i in (2, 3))
    assert all(r['cycleOccurrenceSpEffectId'] == r['atkOccurrenceSpEffectId'] == -1 for r in (base, seed, leaf))
    families.append(dict(effect=root, root=root, state=state, seed=root + 1, leaf=root + 2, rate=rate, duration=10))
by_root = {f['root']: f for f in families}


class Poise(Chain):
    def __init__(self, inputs):
        super().__init__(inputs)
        self.delivered = []

    def prepare(self, roots):
        for root in roots:
            self.insert(root)
        self.tick(0)

    def tick(self, dt):
        queued = self.emitted[:]
        self.emitted.clear()
        for leaf in queued:
            self.insert(leaf)
        self.delivered.extend(queued)
        self.qualify()
        self.update(dt)

    def rate(self):
        self.invoke(0x502270, [OBJ, 0])
        return struct.unpack('<f', (self.u.reg_read(UC_X86_REG_XMM0) & 0xffffffff).to_bytes(4, 'little'))[0]

    def trigger(self, count=1):
        for _ in range(count):
            for seed in guard_grants:
                self.insert(seed)

    def leaves(self):
        return [n for n in self.nodes() if n['id'] in [f['leaf'] for f in families] and not n['flags'] & 0x800c0003]

    def disable(self):
        node = struct.unpack('<Q', self.u.mem_read(OBJ + 8, 8))[0]
        while node:
            self.u.mem_write(node + 0x68, struct.pack('<I', 0x800c0003))
            node = struct.unpack('<Q', self.u.mem_read(node + 0x38, 8))[0]


checks = dict(script=script_checks, selection=[], trigger=[], lifetime=[], refresh=[], disabled=[], mixed=[])
stubs = set()
cases = [[]] + [[f['effect']] * copies for f in families for copies in (1, 2, 3, 6)]
cases += list(map(list, itertools.permutations(by_root)))
for effects in cases:
    for hero in (1, 7, 10):
        c = Selection([[effect] for effect in effects], hero)
        bits = c.select()
        roots = []
        for index, effect in enumerate(effects):
            if index * 6 in bits:
                c.invoke(0xe6e150, [OBJ + 0x9200, effect])
                roots.append(c.invoke(0xe6e3b0, [OBJ + 0x9200, 0]) & 0xffffffff)
        assert roots == effects
        checks['selection'].append(dict(effects=effects, hero=hero, roots=roots))
        stubs.update(c.stubs)
    for repeats, fps in itertools.product((0, 1, 3), (30, 60, 120)):
        c = Poise(x)
        c.prepare(roots)
        assert c.rate() == 1 and c.leaves() == []
        c.trigger(repeats)
        for _ in range(fps // 5):
            c.tick(1 / fps)
        expected_leaves = sorted({by_root[root]['leaf'] for root in roots}) if repeats else []
        assert sorted(n['id'] for n in c.leaves()) == expected_leaves, (effects, repeats, fps, c.nodes(), expected_leaves)
        expected_rate = math.prod(by_root[root]['rate'] for root in set(roots)) if repeats else 1
        assert math.isclose(c.rate(), expected_rate, rel_tol=1e-6)
        checks['trigger'].append(dict(effects=effects, repeats=repeats, fps=fps, delivered=c.delivered, leaves=c.leaves(), multiplier=c.rate()))
        c.disable()
        assert c.rate() == 1
        checks['disabled'].append(dict(effects=effects, repeats=repeats, fps=fps, multiplier=c.rate()))
        stubs.update(c.stubs)

for root, fps in itertools.product(by_root, (30, 60, 120)):
    c = Poise(x)
    c.prepare([root])
    c.trigger()
    first = last = None
    for frame in range(1, 11 * fps + 1):
        c.tick(1 / fps)
        if c.leaves():
            if first is None:
                first = frame
            last = frame
            assert math.isclose(c.rate(), by_root[root]['rate'], rel_tol=1e-6)
        else:
            assert c.rate() == 1
    # Timer expiry, replacement request, next-tick delivery and activation each
    # advance on the fixture's update boundary; this is not a gameplay latency.
    assert first is not None and .1 <= first / fps <= .1 + 5 / fps, (root, fps, first)
    assert abs((last - first + 1) / fps - 10) <= 3 / fps
    checks['lifetime'].append(dict(root=root, fps=fps, firstFrame=first, lastFrame=last, finalMultiplier=c.rate()))
    stubs.update(c.stubs)

# Repeated guard after five seconds refreshes the one leaf, including duplicate
# seed notifications. Mixed-level timers remain independent.
for roots in ([8652020], [8652020] * 3, list(by_root), list(reversed(by_root))):
    c = Poise(x)
    c.prepare(roots)
    c.trigger()
    for _ in range(12):
        c.tick(1 / 60)
    before = c.leaves()
    for _ in range(5):
        c.tick(1)
    aged = c.leaves()
    c.trigger(3)
    for _ in range(12):
        c.tick(1 / 60)
    refreshed = c.leaves()
    assert sorted(n['id'] for n in refreshed) == sorted(n['id'] for n in before)
    assert all(n['lifetime'] > 9.8 for n in refreshed)
    assert all(n['lifetime'] < 5 for n in aged)
    expected = math.prod(by_root[r]['rate'] for r in set(roots))
    assert math.isclose(c.rate(), expected, rel_tol=1e-6)
    for _ in range(6):
        c.tick(1)
    still_active = c.leaves()
    assert len(still_active) == len(refreshed)
    # Leave two coarse fixture updates for expiry cleanup; fine-grained 30/60/
    # 120 Hz duration is checked separately above.
    for _ in range(6):
        c.tick(1)
    assert c.leaves() == [] and c.rate() == 1
    checks['refresh'].append(dict(roots=roots, before=before, aged=aged, refreshed=refreshed,
                                  afterOriginalExpiry=still_active, multiplier=expected, finalMultiplier=c.rate()))
    stubs.update(c.stubs)

for first, second in itertools.permutations(by_root, 2):
    c = Poise(x)
    c.prepare([first])
    c.trigger()
    for _ in range(12):
        c.tick(1 / 60)
    for _ in range(5):
        c.tick(1)
    # A second root arriving cannot make the old, already expired seed qualify.
    c.insert(second)
    c.tick(0)
    assert [n['id'] for n in c.leaves()] == [first + 2]
    # Only the new level's seed arrives in this explicit timer-isolation fixture.
    c.insert(second + 1)
    for _ in range(12):
        c.tick(1 / 60)
    assert math.isclose(c.rate(), by_root[first]['rate'] * by_root[second]['rate'], rel_tol=1e-6)
    both = c.leaves()
    for _ in range(7):
        c.tick(1)
    assert [n['id'] for n in c.leaves()] == [second + 2]
    assert math.isclose(c.rate(), by_root[second]['rate'], rel_tol=1e-6)
    checks['mixed'].append(dict(first=first, second=second, both=both, remaining=c.leaves(), multiplier=c.rate()))
    stubs.update(c.stubs)

output = dict(schema=1, exeSha256=sha(x.raw), regulationSha256=x.x['hashes']['regulation.bin'],
              paramSha256=sha(x.param), attachParamSha256=sha(raw), scriptSha256=sha(raw_script),
              guardFunctionSha256=sha(guard_function.encode()), callers=callers, families=families, checks=checks,
              native=dict(selection='4FEA30 → E6E150 → E6E3B0', lifecycle='50D060 → 5057D0 → 50ACD0', poise='502270'),
              stubs=sorted(stubs | {'actual HKS executes in Lua5.4; damage type API symbols represented by distinct strings; not an engine enum mapping',
                                    'inventory identity/allocation use Selection fixture from probe_equipped_exclusivity',
                                    'HKS requests enter isolated effect container; native replacement grants recorded by 3C7FD0 fixture arrive on next tick; full actor queue and animation scheduling not executed',
                                    'no actual collision, incoming poise damage, stagger reaction, death/reload or multiplayer execution',
                                    'mixed timer test explicitly grants only the second seed to isolate independent lifetime'}),
              gameplayVerified=False)
a.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
print('PASS', {k: len(v) for k, v in checks.items()}, 'guard poise checks; HKS callers', len(callers))

