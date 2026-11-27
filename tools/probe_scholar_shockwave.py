"""Trace Scholar shockwave HKS gate, native emission and incoming-damage debuff.

Actor identity, inventory, collision arrival and projectile sinks are explicit
fixtures; actual HKS gate and native grant/selection/emission/recipient routines
execute. This is not gameplay or full skill/animation scheduling.
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
from native_ailment_runtime import Ailment

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


class Actor(Ailment):
 def __init__(self,kind=0,maximum=500):
  # Reuse the actor setup; explicitly initialize every channel, including the
  # five channels outside the shared helper's original poison/bleed probes.
  super().__init__(x,0,maximum);self.kind=kind;self.grants=[]
  for i in range(7):
   for off in (0x9010,0x902c):self.u.mem_write(OBJ+off+i*4,struct.pack('<i',maximum))
  self.q(OBJ+0x6210,STOP+0x300);self.q(OBJ+0x6790,STOP+0x301)
  for off in (0x118,0x120,0x130,0x150):self.q(OBJ+0x6200+off,STOP+0x302)
  self.q(OBJ+0xf020,OBJ+0x9000)
  self.globalq(0x3c84d4+7+0x384b2c5,OBJ+0x18300)
  self.stubs.add('explicit player identity, actor virtual +590 type 0 and +118/+120/+130/+150 false')
  self.stubs.add('native self-grant mode 7 and local actor; network singleton present with no peer')
  self.stubs.add('3D3390 false special owner predicate; 51B920/6AF640 notification sinks; EA0CA0 absent notification mapping')
  self.stubs.add('2167950/21674E0/2167A40 monotonic notification timestamp fixture')
  self.globalq(0x3c21ec8,OBJ+0x18000);self.u.mem_write(OBJ+0x18010,struct.pack('<i',7))
  self.u.mem_map(OBJ+0x40000,0x20000);self.globalq(0x3c0f0a8,OBJ+0x40000);self.q(OBJ+0x574e8,OBJ+0x6000)
 def globalq(self,rva,value):
  try:self.u.mem_read(BASE+rva,8)
  except:self.mapped(self.u,0,BASE+rva,8,0,None)
  self.q(BASE+rva,value)
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v&0xffffffffffffffff);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if address in (STOP+0x300,STOP+0x301,STOP+0x302):ret({STOP+0x300:1,STOP+0x301:OBJ+0x18100,STOP+0x302:0}[address])
  elif pc==0x3c7fd0:self.grants.append(u.reg_read(UC_X86_REG_RDX)&0xffffffff)  # observe; execute original grant
  elif pc in(0x3d3390,0x732800,0x51b920,0x6af640):ret()
  elif pc in(0x2167950,0x21674e0,0x2167a40):
   self.q(OBJ+0x18200,100);ret(OBJ+0x18200 if pc==0x2167950 else 1 if pc==0x2167a40 else 0)
  elif pc==0xea0ca0:ret(-1)
  else:super().hook(u,address,size,user)
 def grant(self,id):self.invoke(0x3c7fd0,[OBJ+0x6000,id,1])
 def damage(self,value=100,excluded=0):self.invoke(0x504d30,[OBJ,0,0,0,excluded],{UC_X86_REG_XMM1:value})

class Shock(Actor):
 def __init__(self):
  self.free=[];self.frame=0;self.shots=[]
  super().__init__()
 def hook(self,u,address,size,user):
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP)
   u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  pc=address-BASE
  if pc==0x3ced90:
   self.stubs.add('3CED90 synthetic animation-owner context');ret(OBJ+0xd000)
  elif pc==0x4d1b20:
   self.stubs.add('4D1B20 ordinary locally active actor');ret()
  elif pc==0x26909a0:
   self.stubs.add('26909A0 security cookie');ret(u.reg_read(UC_X86_REG_RAX))
  elif pc==0x3975d0:
   self.stubs.add('3975D0 records native emission request; full collision is not simulated')
   payload=bytes(u.mem_read(u.reg_read(UC_X86_REG_R9),8))
   self.shots.append(dict(frame=self.frame,behavior=u.reg_read(UC_X86_REG_RDX),payload=payload.hex()));ret(1)
  elif address==STOP+0x108:
   ptr=u.reg_read(UC_X86_REG_RDX)
   assert OBJ+0x20000<=ptr<OBJ+0x40000 and ptr not in self.free
   self.free.append(ptr);ret()
  elif pc==0x214e8d0 and self.free:
   assert u.reg_read(UC_X86_REG_RCX)==0x88
   ret(self.free.pop())
  else:super().hook(u,address,size,user)
 def emit(self):self.invoke(0x50aa20,[OBJ])


raw_script = a.script.read_bytes()
assert sha(raw_script) == '96339bb15f57559cd42a940d616fcc2a18a10f50845cfc22b46b356ab66c3b29'
source = raw_script.decode('utf-8-sig').replace('\r\n', '\n')
functions = {match[1]: match[0] for match in re.finditer(r'^function (\w+)\([^\n]*\).*?(?=^function |\Z)', source, re.M | re.S)}
damage_function = functions['ExecDamage']
checks = dict(script=[], selection=[], emission=[], repeated=[], projectile=[], recipient=[], numeric=[], lifetime=[], refresh=[])
stubs = set()
for damaged, shield, relic, blocked, parry, guard_attack in itertools.product((False, True), (False, True), (False, True), ('none', '102551', 'motion', '426'), (False, True), (False, True)):
    present = ([708050] if shield else []) + ([7036600] if relic else []) + ([102551] if blocked == '102551' else [])
    program = '''
TRUE=1; FALSE=0
HasReceivedAnyDamage="damage"; GetSpEffectID="effect"; IsDamageMotionOff="motion"; Unknown426="426"; Unknown1012="later"
AddSpEffect="grant"
local added={}; local present={%s}; local values={damage=%d,motion=%d,["426"]=%d,later=TRUE}
function env(kind,id)
  if kind==GetSpEffectID then return present[id] and TRUE or FALSE end
  assert(values[kind]~=nil, tostring(kind)); return values[kind]
end
function act(kind,id) assert(kind==AddSpEffect); table.insert(added,id) end
''' % (','.join('[%d]=true' % id for id in present), int(damaged), int(blocked == 'motion'), int(blocked == '426'))
    emitted = execute_lua(program + damage_function + '\nassert(ExecDamage(%d,%d)==FALSE)\nreturn "["..table.concat(added,",").."]"' % (int(parry), int(guard_attack)))
    qualifies = damaged and shield and blocked == 'none'
    assert emitted == ([708052] + ([7036601] if relic else []) if qualifies else [])
    checks['script'].append(dict(damaged=damaged, shield=shield, relic=relic, blocked=blocked,
                                 parry=parry, guardAttack=guard_attack, emitted=emitted))

behavior_raw = a.extracted.with_suffix('.BehaviorParam_PC.param').read_bytes()
attack_raw = a.extracted.with_suffix('.AtkParam_Pc.param').read_bytes()
bullet_raw = a.extracted.with_suffix('.Bullet.param').read_bytes()
behaviors = Inputs.table(behavior_raw, 0x20)
attacks = Inputs.table(attack_raw, 0x1d0)
bullets = Inputs.table(bullet_raw, 0x100)
behavior = x.x['tables']['BehaviorParam_PC']['600000401']
bullet = x.x['tables']['Bullet']['30908001']
attack = x.x['tables']['AtkParam_Pc']['600000400']
assert behavior['refType'] == 1 and behavior['refId'] == 30908001
assert struct.unpack_from('<i', behaviors[600000401], 0xc)[0] == 30908001
assert bullet['atkId_Bullet'] == 600000400 and bullet['spEffectId0'] == 7036602
assert bullet['numShoot'] == 1 and bullet['HitBulletID'] == bullet['intervalCreateBulletId'] == -1
assert [attack[k] for k in ('selfTarget', 'friendlyTarget', 'opposeTarget', 'disableHitSpEffect')] == [0, 0, 1, 0]
for effect in (7036600, 7036601):
    attach = x.x['tables']['AttachEffectParam'][str(effect)]
    assert attach['passiveSpEffectId_1'] == 7036600 and attach['exclusivityId'] == -1
    assert attach['allowScholar'] == 1 and all(v == 0 for k, v in attach.items() if k.startswith('allow') and k != 'allowScholar')
    assert all(attach[k] == -1 for k in ('passiveSpEffectId_2', 'passiveSpEffectId_3', 'permanentSpEffectId'))
root, seed, leaf = [x.spells[str(i)] for i in (7036600, 7036601, 7036602)]
assert (root['spCategory'], root['effectEndurance']) == (20, -1)
assert (seed['spCategory'], seed['stateInfo'], seed['behaviorId']) == (20, 275, 600000401)
assert math.isclose(seed['effectEndurance'], .1, rel_tol=1e-6) and math.isclose(seed['motionInterval'], .2, rel_tol=1e-6)
assert (leaf['spCategory'], leaf['effectEndurance']) == (20, 6)
assert all(leaf[k] == 1.5 for k in ('neutralDamageCutRate', 'blowDamageCutRate', 'slashDamageCutRate', 'thrustDamageCutRate', 'magicDamageCutRate', 'fireDamageCutRate', 'thunderDamageCutRate', 'darkDamageCutRate'))


class Emitter(Chain):
 def __init__(self):super().__init__(x);self.frame=0;self.shots=[]
 def hook(self,u,address,size,user):
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP)
   u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  pc=address-BASE
  if pc==0xe87800:
   assert u.reg_read(UC_X86_REG_RDX)&0xffffffff==30908001
   self.stubs.add('E87800 actual shockwave Bullet lookup')
   u.mem_write(OBJ+0xe900,bullets[30908001]);ptr=u.reg_read(UC_X86_REG_RCX)
   u.mem_write(ptr,struct.pack('<QI',OBJ+0xe900,30908001));ret(ptr)
  elif pc==0x347700:
   self.stubs.add('347700 successful projectile recorder, without scene collision')
   self.shots.append(self.frame);ret(1)
  else:super().hook(u,address,size,user)

class Recipient(Chain):
    def target(self, typ, same=False):
        self.u.mem_write(OBJ + 0x6074, b'\1')
        self.u.mem_write(OBJ + 0xb074, bytes([typ]))
        self.u.mem_write(OBJ + 0xc000, x.rows[7036602])
        self.q(OBJ + 0xb800, OBJ + 0xc000)
        return bool(self.invoke(0x52cc60, [OBJ + 0x6000, OBJ + 0x6000 if same else OBJ + 0xb000, OBJ + 0xb800]) & 255)

    def damage_rates(self):
        self.u.mem_write(OBJ + 0x800, bytes(0x200))
        self.invoke(0x503800, [OBJ, OBJ + 0x500, OBJ + 0x520, OBJ + 0x540, OBJ + 0x800])
        return list(struct.unpack('<5f', self.u.mem_read(OBJ + 0x500, 20)))

    def step(self, dt):
        self.qualify()
        self.update(dt)

    def disable(self):
        node = struct.unpack('<Q', self.u.mem_read(OBJ + 8, 8))[0]
        while node:
            self.u.mem_write(node + 0x68, struct.pack('<I', 0x800c0003))
            node = struct.unpack('<Q', self.u.mem_read(node + 0x38, 8))[0]


for effects in ([], [7036600], [7036601], [7036600] * 3, [7036601] * 3, [7036600, 7036601], [7036601, 7036600]):
    scholar_roots = None
    for hero in range(11):
        c = Selection([[effect] for effect in effects], hero)
        bits = c.select()
        roots = []
        for index, effect in enumerate(effects):
            if index * 6 in bits:
                c.invoke(0xe6e150, [OBJ + 0x9200, effect])
                roots.append(c.invoke(0xe6e3b0, [OBJ + 0x9200, 0]) & 0xffffffff)
        # Zero is an accepted control input; do not label it as a named hero.
        assert roots == ([7036600] * len(effects) if hero in (0, 9) else []), (effects, hero, bits, roots)
        if hero == 9:
            scholar_roots = roots
        checks['selection'].append(dict(effects=effects, hero=hero, roots=roots))
        stubs.update(c.stubs)
    for damaged, shield, fps in itertools.product((False, True), (False, True), (30, 60, 120)):
        c = Shock()
        for r in scholar_roots:
            c.grant(r)
        c.qualify()
        c.update(0)
        # Feed the output of the actual script case into the original self-grant.
        script_case = next(row for row in checks['script'] if (row['damaged'], row['shield'], row['relic'], row['blocked'], row['parry'], row['guardAttack']) == (damaged, shield, bool(effects), 'none', False, False))
        for id in script_case['emitted']:
            c.grant(id)
        for frame in range(fps):
            c.frame = frame
            c.qualify()
            c.update(1 / fps)
            c.emit()
        relic_shots = [shot for shot in c.shots if shot['behavior'] == 600000401]
        assert len(relic_shots) == int(damaged and shield and bool(effects)), (effects, damaged, shield, fps, c.shots)
        assert not any(n['id'] == 7036601 for n in c.nodes())
        checks['emission'].append(dict(effects=effects, damaged=damaged, shield=shield, fps=fps, shots=c.shots))
        stubs.update(c.stubs)

for copies, fps in itertools.product((1, 3), (30, 60, 120)):
    c = Shock()
    for _ in range(copies):
        c.grant(7036600)
    arrivals = (0, fps // 2, fps)
    for frame in range(fps * 2):
        c.frame = frame
        if frame in arrivals:
            for _ in range(copies):
                c.grant(7036601)
        c.qualify()
        c.update(1 / fps)
        c.emit()
    assert len(c.shots) == 3 and all(shot['behavior'] == 600000401 for shot in c.shots)
    checks['repeated'].append(dict(copies=copies, fps=fps, arrivals=list(arrivals), shots=c.shots))
    stubs.update(c.stubs)

for fps in (30, 60, 120):
    c = Emitter()
    slot = OBJ + 0x4000
    c.u.mem_write(slot + 0x329, b'\1')
    c.u.mem_write(slot + 0x334, struct.pack('<I', 30908001))
    c.u.mem_write(slot + 0x494, b'\1')
    for frame in range(fps):
        c.frame = frame
        c.invoke(0x343280, [slot], {UC_X86_REG_XMM1: 1 / fps})
    assert c.shots == [0]
    checks['projectile'].append(dict(fps=fps, shots=c.shots))
    stubs.update(c.stubs)

for relation, typ, same in (('self', 1, True), ('friendly', 2, False), ('opposing', 6, False), ('neutral', 0, False)):
    c = Recipient(x)
    allowed = c.target(typ, same)
    # SpEffect itself allows self as well; the upstream attack has selfTarget=0.
    # Keep these separate, since collision targeting is not emulated here.
    assert allowed == (relation in ('self', 'opposing')), (relation, allowed)
    checks['recipient'].append(dict(relation=relation, effectAllows=allowed,
                                    attackTargetFlag=attack.get({'self':'selfTarget', 'friendly':'friendlyTarget', 'opposing':'opposeTarget'}.get(relation, ''))))
    stubs.update(c.stubs)

for copies in (0, 1, 2, 3, 6):
    c = Recipient(x)
    for _ in range(copies):
        c.insert(7036602)
    c.step(0)
    assert c.damage_rates() == ([1.5] * 5 if copies else [1] * 5)
    assert len(c.nodes()) == int(bool(copies))
    checks['numeric'].append(dict(copies=copies, nodes=c.nodes(), multipliers=c.damage_rates(), disabled=False))
    c.disable()
    assert c.damage_rates() == [1] * 5
    checks['numeric'].append(dict(copies=copies, multipliers=c.damage_rates(), disabled=True))
    stubs.update(c.stubs)

for fps in (30, 60, 120):
    c = Recipient(x)
    c.insert(7036602)
    c.step(0)
    last = 0
    for frame in range(1, 7 * fps + 1):
        c.step(1 / fps)
        if c.damage_rates() == [1.5] * 5:
            last = frame
        else:
            assert c.damage_rates() == [1] * 5
    assert abs(last / fps - 6) <= 3 / fps and c.nodes() == []
    checks['lifetime'].append(dict(fps=fps, lastFrame=last, finalMultipliers=c.damage_rates()))
    stubs.update(c.stubs)
    for copies in (1, 3):
        c = Recipient(x)
        c.insert(7036602)
        for _ in range(3 * fps):
            c.step(1 / fps)
        before = c.nodes()
        for _ in range(copies):
            c.insert(7036602)
        c.step(0)
        refreshed = c.nodes()
        assert len(refreshed) == 1 and refreshed[0]['lifetime'] == 6
        assert c.damage_rates() == [1.5] * 5
        for _ in range(4 * fps):
            c.step(1 / fps)
        assert c.damage_rates() == [1.5] * 5
        for _ in range(3 * fps):
            c.step(1 / fps)
        assert c.nodes() == [] and c.damage_rates() == [1] * 5
        checks['refresh'].append(dict(fps=fps, copies=copies, before=before, refreshed=refreshed, finalMultipliers=c.damage_rates()))
        stubs.update(c.stubs)

output = dict(schema=1, exeSha256=sha(x.raw), regulationSha256=x.x['hashes']['regulation.bin'],
              paramSha256=sha(x.param), attachParamSha256=sha(raw), behaviorParamSha256=sha(behavior_raw),
              bulletParamSha256=sha(bullet_raw), attackParamSha256=sha(attack_raw), scriptSha256=sha(raw_script),
              scriptFunctionSha256=sha(damage_function.encode()), effects=[7036600, 7036601], root=7036600, seed=7036601, leaf=7036602,
              duration=6, rate=1.5, behavior=dict(id=600000401, refType=1, refId=30908001),
              bullet={k:bullet[k] for k in ('atkId_Bullet', 'spEffectId0', 'hitRadius', 'hitRadiusMax', 'spreadTime', 'life', 'numShoot')},
              attack={k:attack[k] for k in ('selfTarget', 'friendlyTarget', 'opposeTarget', 'disableHitSpEffect')},
              checks=checks, native=dict(selection='4FEA30 → E6E150 → E6E3B0', grant='3C7FD0', emitter='50AA20 → 397570 → 3975D0', projectile='343280', recipient='52CC60', damage='503800'),
              stubs=sorted(stubs | {'actual ExecDamage executes in Lua5.4; environment/skill-state/damage inputs explicit, Unknown1012 terminates unrelated later branches',
                                    'inventory/allocation use Selection fixture; original self-grant and emitter run against synthetic actor',
                                    'collision arrival explicitly inserts Bullet leaf; full projectile collision/effect transport and hit deduplication not executed',
                                    'skill708050 acquisition, complete animation/skill scheduling, final damage/stagger, death/reload and multiplayer not executed'}),
              gameplayVerified=False)
a.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
print('PASS', {k:len(v) for k,v in checks.items()}, 'Scholar shockwave checks')

