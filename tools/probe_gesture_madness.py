"""Trace held gesture events, madness buildup and onset resource loss.

Runs pinned native accumulation, immunity, removal, HP/FP getters and effect
container code. Actor identity, network transport, neutral death-protection flags
and absent resistance-growth assets are fixtures, not a running expedition.
"""
import argparse
import json
import math
import struct
from pathlib import Path
from native_effect_runtime import BASE, OBJ, STOP, Chain, Inputs, sha
from unicorn.x86_const import *

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('exe', type=Path)
p.add_argument('extracted', type=Path)
p.add_argument('animations', type=Path)
p.add_argument('output', type=Path)
a = p.parse_args()
inputs = Inputs(a.exe, a.extracted)
tae = json.loads(a.animations.read_text())
assert tae['bundles'][0]['sha256'] == '1410035ad79edb410fa41420ec259fcb4a1037d748c9c4a3b6ae8d1366c76d0f'
r = inputs.spells
assert r['9642']['disableMadness'] == 1
for root, state in [(7035400,2278),(7035410,2375)]:
    assert r[str(root)]['stateInfo'] == r[str(root+1)]['invocationConditionsStateChange1'] == state
    assert r[str(root+1)]['effectEndurance'] == 0 and math.isclose(r[str(root+1)]['motionInterval'],.1,abs_tol=1e-6)
    assert r[str(root+1)]['cycleOccurrenceSpEffectId'] == root+2
    leaf = r[str(root+2)]
    assert leaf['stateInfo'] == 437 and leaf['madnessAttackPower'] == 10
    assert leaf['changeHpRate'] == 10 and leaf['changeHpPoint'] == 100
    assert leaf['changeMpRate'] == 0 and leaf['changeMpPoint'] == 30
    assert leaf['effectEndurance'] == 1 and leaf['motionInterval'] == 2
    assert leaf['replaceSpEffectId'] == 1110 and leaf['cycleOccurrenceSpEffectId'] == 49060
    assert struct.unpack_from('<i', inputs.rows[root+2], 0x33c)[0] == 10
    # +3C5 bit 0 (unknown_241b_1), not unknown_239h, selects context scaling.
    assert inputs.rows[root+2][0x3c5] & 1
    assert leaf['unknown_241b_1'] == 1
assert {k:v for k,v in r['7035402'].items() if k!='invocationConditionsStateChange1'} == {k:v for k,v in r['7035412'].items() if k!='invocationConditionsStateChange1'}
events = [dict(tae=t['ID'], animation=an['ID'], **e)
          for b in tae['bundles'] for t in b['taes'] for an in t['animations']
          for e in an['events'] if e['Type'] == 67 and struct.unpack_from('<i', bytes.fromhex(e['hex']))[0] in (7035401,7035411)]
assert [(e['tae'],e['animation'],e['index']) for e in events] == [(2000,80911,9),(2000,80911,10)]
assert all(e['StartTime'] == 0 and e['EndTime'] == 6.1 for e in events)

class Gesture(Chain):
    def __init__(self, maximum=99999, immune=False, equipment=()):
        super().__init__(inputs)
        self.q(OBJ + 0x6190, OBJ)
        self.q(OBJ + 0x63a0, STOP + 0x200)  # owner virtual +1a0: no growth params
        self.q(OBJ + 0x6410, STOP + 0x201)  # owner virtual +210: no damage exclusion
        self.q(OBJ + 0x9008, OBJ + 0x6000)  # ailment controller owner
        self.q(OBJ + 0xe008, OBJ + 0x6000)  # HP data owner
        self.q(OBJ + 0x61b8, OBJ + 0xf000)
        self.q(OBJ + 0xf008, OBJ + 0xf400)
        # Queue/debug-singleton identities only. Original branch predicates run.
        for address, value in [(BASE + 0x42d85f + 7 + 0x37f4662, OBJ + 0xe800),
                               (BASE + 0x427bfa + 8 + 0x37e7736, OBJ + 0xf800)]:
            self.mapped(self.u, 0, address, 8, 0, None)
            self.q(address, value)
        for off in (0x9028, 0x9044):
            self.u.mem_write(OBJ + off, struct.pack('<i', maximum))
        for root in equipment: self.insert(root)
        if immune: self.insert(9642)
        self.qualify(); self.update(0)
        self.tae_requests = []
        self.q(OBJ + 0x8018, OBJ + 0x6000)
        self.q(OBJ + 0x8108, OBJ + 0x8200)
        self.stubs.add('empty actor/HP/ailment objects; neutral death-protection flags and supplied starting resistance')

    def hook(self, u, address, size, user):
        pc = address - BASE
        def finish(value=0):
            u.reg_write(UC_X86_REG_RAX, value)
            sp = u.reg_read(UC_X86_REG_RSP)
            u.reg_write(UC_X86_REG_RIP, struct.unpack('<Q', u.mem_read(sp, 8))[0])
            u.reg_write(UC_X86_REG_RSP, sp + 8)
        if pc in (0x3ced90, 0x4d1b20, 0x3c8be0):
            self.stubs.add('3CED90/4D1B20 neutral animation-owner context; 3C8BE0 requests delivered before next qualification')
            if pc == 0x3c8be0: self.tae_requests.append(u.reg_read(UC_X86_REG_RDX) & 0xffffffff)
            finish(OBJ + 0xd000 if pc == 0x3ced90 else 0)
        elif address in (STOP + 0x200, STOP + 0x201):
            self.stubs.add('owner virtual +1a0 no resistance-growth params; +210 no damage exclusion')
            finish()
        elif pc == 0x6ada30:
            self.stubs.add('6ADA30 ordinary resource-setter context')
            finish()
        elif pc == 0x3d4180:
            self.stubs.add('3D4180 player identity')
            finish(1)
        elif pc in (0x4e78a0, 0x4e78c0, 0xdf24d0):
            self.stubs.add(hex(pc) + ' network-message identity/transport only; no remote delivery')
            finish()
        else:
            super().hook(u, address, size, user)

    def apply_madness(self, id):
        # Mirror 3DB410: insert first, then run status processing. A true return
        # removes that exact node immediately, without expiry replacement.
        index = self.insert(id)
        if index >= 0x80000000: return dict(insertRejected=True, remaining=self.remaining())
        self.q(OBJ + 0x9800, self.lookup[id])
        self.u.mem_write(OBJ + 0x9900, struct.pack('<7f', *([1] * 7)))
        self.u.mem_write(OBJ + 0x9938, struct.pack('<f', 1))
        rejected = bool(self.invoke(0x42d110, [OBJ + 0x9000, OBJ + 0x9800, OBJ + 0x9900]) & 255)
        if rejected: self.invoke(0x505280, [OBJ, index])
        return dict(insertRejected=False, onset=not rejected, remaining=self.remaining())

    def remaining(self):
        return struct.unpack('<i', self.u.mem_read(OBJ + 0x9028, 4))[0]

    def hp_packet(self, maximum):
        # No physical-owner invulnerability/remote state while aggregating. The
        # actual effect list and native bloodDamageRate multiplier remain live.
        self.q(OBJ + 0x10, 0)
        self.invoke(0x506ec0, [OBJ, maximum, OBJ + 0x800, OBJ + 0x808, OBJ + 0x820, 0])
        self.q(OBJ + 0x10, OBJ + 0x6000)
        return list(struct.unpack('<7i', self.u.mem_read(OBJ + 0x820, 28)))

    def event(self, seed):
        self.u.mem_write(OBJ + 0x8200, struct.pack('<i', seed) + bytes(12))
        # Actual Type 67 dispatch. Existing nodes pass through 509150/50A630;
        # this is not a synthetic refresh or repeated insertion.
        self.invoke(0x40ff20, [OBJ + 0x8000, OBJ + 0x8100, 1])
        for id in self.tae_requests: self.insert(id)
        self.tae_requests.clear()

checks = dict(cadence=[], onset=[], resources=[])
stubs = set()
def run(roots, fps, resistance, immune=False, until_onset=False):
    c = Gesture(resistance, immune, roots)
    attempts, grants, resources = [], [], []
    stopped = None
    for frame in range(fps * 3):
        pending, c.emitted = c.emitted, []
        for id in pending:
            if id in (7035402,7035412):
                result = c.apply_madness(id)
                attempts.append(dict(frame=frame, leaf=id, **result))
                if until_onset and result.get('onset'): stopped = frame
            else:
                c.insert(id)
        if frame < fps and stopped is None:
            c.event(7035401); c.event(7035411)
        c.qualify(); c.update(1 / fps)
        hp, fp = c.hp_packet(1000)[0], c.fp(100)[0]
        if hp or fp: resources.append(dict(frame=frame, hp=hp, fp=fp))
        if c.emitted: grants.append(dict(frame=frame, ids=c.emitted.copy()))
    stubs.update(c.stubs)
    return dict(equipment=list(roots), fps=fps, startingResistance=resistance, immune=immune,
                stoppedAfterOnset=stopped, attempts=attempts, grants=grants, resources=resources, remaining=c.remaining())

configs = [(),(7035400,),(7035400,)*3,(7035410,),(7035410,)*3,(7035400,7035410),(7035400,)*3+(7035410,)*3]
for fps in (30,60,120):
    for roots in configs:
        out = run(roots,fps,99999)
        assert not out['resources']
        assert all(not a.get('insertRejected') and not a['onset'] for a in out['attempts'])
        assert out['remaining'] == 99999 - 10 * len(out['attempts'])
        assert all(a['frame'] <= fps+1 for a in out['attempts'])
        if roots: assert 8 <= len(out['attempts']) / len(set(roots)) <= 12
        else: assert not out['attempts']
        checks['cadence'].append(out)
    current = checks['cadence'][-len(configs):]
    for left,right in [(1,2),(3,4),(5,6)]:
        assert current[left]['attempts'] == current[right]['attempts']
    assert len(current[5]['attempts']) == 2 * len(current[1]['attempts'])

for root in (7035400,7035410):
    for resistance in (9,10,11,100):
        for immune in (False,True):
            out = run((root,),60,resistance,immune,True)
            successes = [a for a in out['attempts'] if a.get('onset')]
            assert len(successes) == int(not immune)
            assert len(out['resources']) == len(successes)
            if immune:
                assert out['remaining'] == resistance
                assert not any(49060 in g['ids'] or 1110 in g['ids'] for g in out['grants'])
            else:
                assert len([a for a in out['attempts'] if not a['insertRejected']]) == math.ceil(resistance / 10)
                assert out['resources'][0]['hp'] == -200 and out['resources'][0]['fp'] == -30
                assert sum(49060 in g['ids'] for g in out['grants']) == 1
                assert sum(1110 in g['ids'] for g in out['grants']) == 1
            checks['onset'].append(out)
for maximum in (1,99,137,1000):
    c = Gesture(10, False, (7035400,))
    result = c.apply_madness(7035402)
    assert result['onset']
    c.qualify(); c.update(0)
    packet, fp = c.hp_packet(maximum), c.fp(maximum)
    assert packet[0] == -math.trunc(maximum * .1 + 100) and fp == [-30,0]
    c.qualify();c.update(1/60)
    assert c.hp_packet(maximum)[0] == c.fp(maximum)[0] == 0
    checks['resources'].append(dict(maximum=maximum,packet=packet,fp=fp))
    stubs.update(c.stubs)
output = dict(schema=1,exeSha256=sha(inputs.raw),regulationSha256=inputs.x['hashes']['regulation.bin'],
    paramSha256=sha(inputs.param),animationSha256=tae['bundles'][0]['sha256'],
    roots=[7035400,7035410],events=events,checks=checks,stubs=sorted(stubs),gameplayVerified=False,
    limits=['one second of held action input; automatic interruption on onset is not simulated',
            'neutral source scaling; no passive gauge decay or dynamic resistance growth',
            'no full actor damage reaction, network or reload'])
a.output.write_text(json.dumps(output,indent=2)+'\n')
print('PASS:',{k:len(v) for k,v in checks.items()},'gesture madness checks')
