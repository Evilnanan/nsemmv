"""Verify Hotfix1 periodic FP roots after native relic selection.

Original equipment selection, passive-root reads, insertion, qualification,
periodic update and FP aggregation execute unchanged. Inventory and allocation
are explicit fixtures; no current-FP setter or live gameplay is simulated.
"""
import argparse
import itertools
import json
import struct
from pathlib import Path
from native_effect_runtime import *

p = argparse.ArgumentParser(description=__doc__)
for name in ('exe', 'extracted', 'output'):
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

families = []
for effect, root, interval in ((7006502, 7006500, 2.5), (7006501, 7006505, 2), (7006500, 7006506, 1)):
    attach = x.x['tables']['AttachEffectParam'][str(effect)]
    row = x.spells[str(root)]
    assert attach['passiveSpEffectId_1'] == root and attach['exclusivityId'] == -1
    assert all(attach[k] == -1 for k in ('passiveSpEffectId_2', 'passiveSpEffectId_3', 'permanentSpEffectId'))
    assert (row['spCategory'], row['stateInfo'], row['effectEndurance'], row['motionInterval']) == (10, 0, -1, interval)
    assert row['changeMpPoint'] == -1 and row['changeMpRate'] == 0
    assert row['conditionHp'] == row['conditionHpRate'] == -1
    assert all(row['invocationConditionsStateChange' + str(i)] == 0 for i in (1, 2, 3))
    assert all(row[k] == -1 for k in ('cycleOccurrenceSpEffectId', 'replaceSpEffectId', 'atkOccurrenceSpEffectId'))
    assert struct.unpack_from('<2f', x.rows[root], 8) == (-1, interval)
    families.append(dict(effect=effect, root=root, interval=interval, amount=1))

checks = dict(selection=[], snapshot=[], timing=[], mixed=[], arrivalBaseline=[], staggered=[])
stubs = set()
effects = [f['effect'] for f in families]
roots = [f['root'] for f in families]


def record(group, c, **data):
    stubs.update(c.stubs)
    checks[group].append(data)


def prepare(ids, dt=0):
    c = Chain(x)
    for root in ids:
        c.insert(root)
    c.qualify()
    c.update(dt)
    return c


def disable(c):
    node = struct.unpack('<Q', c.u.mem_read(OBJ + 8, 8))[0]
    while node:
        c.u.mem_write(node + 0x68, struct.pack('<I', 0x800c0003))
        node = struct.unpack('<Q', c.u.mem_read(node + 0x38, 8))[0]


# Execute native selection/root access before testing the periodic containers.
for ids, hero in itertools.product(
    [[], *[[effect] * copies for effect in effects for copies in (1, 2, 3, 6)],
     effects, list(reversed(effects)), effects * 2], (1, 7, 10)
):
    c = Selection([[effect] for effect in ids], hero)
    bits = c.select()
    accepted = []
    for index, effect in enumerate(ids):
        if index * 6 in bits:
            c.invoke(0xe6e150, [OBJ + 0x9200, effect])
            accepted.append(c.invoke(0xe6e3b0, [OBJ + 0x9200, 0]) & 0xffffffff)
    expected = [next(f['root'] for f in families if f['effect'] == effect) for effect in ids]
    assert accepted == expected
    v = prepare(accepted)
    value = v.fp(1000)
    assert value == [len(ids), 0]
    stubs.update(v.stubs)
    record('selection', c, effects=ids, hero=hero, roots=accepted, fpPacket=value)

for root, copies, maximum, inactive in itertools.product(roots, (0, 1, 2, 3, 6), (1, 99, 1000, 2345), (False, True)):
    c = prepare([root] * copies)
    if inactive:
        disable(c)
    value = c.fp(maximum)
    assert value == ([0, 0] if inactive else [copies, 0])
    record('snapshot', c, root=root, copies=copies, maximum=maximum, inactive=inactive, fpPacket=value)


def timeline(c, fps, insertions=None):
    values = []
    for frame in range(8 * fps + 4):
        if frame:
            for root in (insertions or {}).get(frame, []):
                c.insert(root)
            c.qualify()
            c.update(1 / fps)
        value = c.fp(1000)
        assert value[1] == 0
        values.append(value[0])
    return values


def pulses(values):
    return [dict(frame=i, fp=value) for i, value in enumerate(values) if value]


baseline = {}
for family, copies, fps in itertools.product(families, (1, 2, 3), (30, 60, 120)):
    root, interval = family['root'], family['interval']
    c = prepare([root] * copies)
    values = timeline(c, fps)
    frames = [i for i, value in enumerate(values) if value]
    assert frames[0] == 0 and len(frames) >= 4
    assert interval * fps <= frames[1] <= interval * fps + 2
    assert all(interval * fps - 1 <= b - a <= interval * fps + 2 for a, b in zip(frames[1:], frames[2:]))
    assert all(value in (0, copies) for value in values)
    if copies == 1:
        baseline[root, fps] = values
    else:
        assert values == [value * copies for value in baseline[root, fps]]
    assert len(c.nodes()) == copies and all(n['lifetime'] == -1 for n in c.nodes())
    record('timing', c, root=root, copies=copies, fps=fps, pulses=pulses(values))

for counts, fps in itertools.product(((1, 1, 0), (1, 0, 1), (0, 1, 1), (1, 1, 1), (2, 2, 2)), (30, 60, 120)):
    c = prepare([root for root, count in zip(roots, counts) for _ in range(count)])
    values = timeline(c, fps)
    expected = [sum(baseline[root, fps][i] * count for root, count in zip(roots, counts)) for i in range(len(values))]
    assert values == expected
    record('mixed', c, roots=roots, copies=counts, fps=fps, pulses=pulses(values))

arrival = {}
for root, fps in itertools.product(roots, (30, 60, 120)):
    c = prepare([root], 1 / fps)
    values = timeline(c, fps)
    arrival[root, fps] = values
    record('arrivalBaseline', c, root=root, fps=fps, pulses=pulses(values))
for first, second, fps in itertools.product(roots, roots, (30, 60, 120)):
    offset = fps // 2
    c = prepare([first])
    values = timeline(c, fps, {offset: [second]})
    expected = [baseline[first, fps][i] + (arrival[second, fps][i - offset] if i >= offset else 0) for i in range(len(values))]
    assert values == expected
    record('staggered', c, first=first, second=second, fps=fps, offsetFrames=offset, pulses=pulses(values))

output = dict(schema=1, exeSha256=sha(x.raw), regulationSha256=x.x['hashes']['regulation.bin'],
              paramSha256=sha(x.param), attachParamSha256=sha(raw), families=families, checks=checks,
              native=dict(selection='4FEA30 → E6E150 → E6E3B0', insert='50D060', qualify='5057D0', update='50ACD0 → 511B80', fp='507460'),
              stubs=sorted(stubs | {'equipment inventory and allocation use Selection fixture from probe_equipped_exclusivity; native selector and passive-root access retained',
                                    'selected roots passed into separate effect container; not a full equipment manager or actor rebuild',
                                    'no current FP setter, cap/overflow, casting costs, death/reload or multiplayer execution'}), gameplayVerified=False)
a.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
print('PASS', sum(map(len, checks.values())), 'native periodic FP cases', {k: len(v) for k, v in checks.items()})
