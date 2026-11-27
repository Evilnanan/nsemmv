"""Verify hand-category poise attack rates after native relic selection.

Original equipment selection, passive-root reads, insertion, qualification,
update and poise attack aggregation execute unchanged. Inventory and allocation
are explicit fixtures; no collision or target poise setter or live gameplay is simulated.
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

import math

attack_raw = a.extracted.with_suffix('.AtkParam_Pc.param').read_bytes()
attacks = Inputs.table(attack_raw, 0x1d0)
families = []
for base, rootbase, category in ((7006000, 8300100, 124), (7006100, 8310100, 125)):
    for suffix, offset, rate in ((0, 0, 1.05), (1, 0, 1.05), (2, 1, 1.15), (3, 2, 1.175)):
        effect, root = base + suffix, rootbase + offset
        attach = x.x['tables']['AttachEffectParam'][str(effect)]
        row = x.spells[str(root)]
        assert attach['passiveSpEffectId_1'] == root and attach['exclusivityId'] == -1
        assert all(attach[k] == -1 for k in ('passiveSpEffectId_2', 'passiveSpEffectId_3', 'permanentSpEffectId'))
        assert (row['spCategory'], row['stateInfo'], row['effectEndurance']) == (10, 0, -1)
        assert row['magicSubCategoryChange1'] == category
        assert row['magicSubCategoryChange2'] == row['magicSubCategoryChange3'] == 0
        assert math.isclose(row['saAttackPowerRate'], rate, rel_tol=1e-6)
        assert math.isclose(struct.unpack_from('<f', x.rows[root], 0x334)[0], rate, rel_tol=1e-6)
        assert all(row['invocationConditionsStateChange' + str(i)] == 0 for i in (1, 2, 3))
        assert all(row[k] == -1 for k in ('cycleOccurrenceSpEffectId', 'replaceSpEffectId', 'atkOccurrenceSpEffectId'))
        families.append(dict(effect=effect, root=root, category=category, rate=rate))
by_effect = {f['effect']: f for f in families}
by_root = {f['root']: f for f in families}


def tags(id):
    return sorted(set(attacks[id][o] for o in (0x4e, 0x4f, 0x1c8, 0x1c9, 0x1ca)) - {0})


representatives = (0, 90200, 100800)
assert 124 in tags(90200) and 125 not in tags(90200)
assert 125 in tags(100800) and 124 not in tags(100800)
assert not {124, 125}.intersection(tags(0))


class Poise(Chain):
    def prepare(self, roots, inactive=False):
        for root in roots:
            self.insert(root)
        self.qualify()
        self.update(0)
        if inactive:
            node = struct.unpack('<Q', self.u.mem_read(OBJ + 8, 8))[0]
            while node:
                self.u.mem_write(node + 0x68, struct.pack('<I', 0x800c0003))
                node = struct.unpack('<Q', self.u.mem_read(node + 0x38, 8))[0]

    def rate(self, attack, kind):
        self.u.mem_write(OBJ + 0xb800, attacks[attack])
        self.q(OBJ + 0xb010, OBJ + 0xb800)
        self.u.mem_write(OBJ + 0x810, bytes([kind]))
        self.invoke(0xe6d530, [OBJ + 0xb000, OBJ + 0x814])
        bits = int.from_bytes(self.u.mem_read(OBJ + 0x814, 32), 'little')
        assert bits == sum(1 << cat for cat in tags(attack))
        self.invoke(0x50f2a0, [OBJ + 0x900, OBJ + 0x800])
        self.invoke(0x507f50, [OBJ, OBJ + 0x900])
        return struct.unpack('<f', (self.u.reg_read(UC_X86_REG_XMM0) & 0xffffffff).to_bytes(4, 'little'))[0]


checks = dict(selection=[], multipliers=[], categorySweep=[])
stubs = set()
cases = [[]]
cases += [[f['effect']] * copies for f in families for copies in (1, 2, 3, 6)]
cases += [[7006000, 7006001], [7006100, 7006101],
          [7006000, 7006002, 7006003], [7006003, 7006002, 7006000],
          [7006100, 7006102, 7006103], [7006103, 7006102, 7006100],
          [7006000, 7006002, 7006003, 7006100, 7006102, 7006103]]
for effects in cases:
    selected_roots = None
    for hero in (1, 7, 10):
        c = Selection([[effect] for effect in effects], hero)
        bits = c.select()
        roots = []
        for index, effect in enumerate(effects):
            if index * 6 in bits:
                c.invoke(0xe6e150, [OBJ + 0x9200, effect])
                roots.append(c.invoke(0xe6e3b0, [OBJ + 0x9200, 0]) & 0xffffffff)
        assert roots == [by_effect[effect]['root'] for effect in effects]
        selected_roots = roots
        checks['selection'].append(dict(effects=effects, hero=hero, roots=roots))
        stubs.update(c.stubs)
    for inactive in (False, True):
        c = Poise(x)
        c.prepare(selected_roots, inactive)
        for attack, kind in itertools.product(representatives, range(13)):
            value = c.rate(attack, kind)
            matched = [] if inactive or kind in (3, 4, 10) else [root for root in selected_roots if by_root[root]['category'] in tags(attack)]
            expected = math.prod(by_root[root]['rate'] for root in matched)
            assert math.isclose(value, expected, rel_tol=1e-6), (effects, attack, kind, inactive, value, expected)
            checks['multipliers'].append(dict(effects=effects, attack=attack, kind=kind, inactive=inactive, matched=matched, multiplier=value))
        stubs.update(c.stubs)

# Verify the actual native tag reader and consumer for every tagged PC attack.
# These parameter rows are not a claim that every attack can be used in play.
category_rows = {str(category): [id for id in attacks if category in tags(id)] for category in (124, 125)}
assert set(category_rows['124']).isdisjoint(category_rows['125'])
for root, family in by_root.items():
    c = Poise(x)
    c.prepare([root, root])
    applied = 0
    for attack in sorted(set(category_rows['124'] + category_rows['125'])):
        value = c.rate(attack, 0)
        matches = family['category'] in tags(attack)
        assert math.isclose(value, family['rate'] ** 2 if matches else 1, rel_tol=1e-6)
        applied += matches
    checks['categorySweep'].append(dict(root=root, tested=len(category_rows['124']) + len(category_rows['125']), applied=applied))
    stubs.update(c.stubs)

output = dict(schema=1, exeSha256=sha(x.raw), regulationSha256=x.x['hashes']['regulation.bin'],
              paramSha256=sha(x.param), attachParamSha256=sha(raw), attackParamSha256=sha(attack_raw),
              families=families, categoryRows=category_rows, checks=checks,
              native=dict(selection='4FEA30 → E6E150 → E6E3B0', tags='E6D530 → E6D3E0', context='50F2A0', filter='511010', poise='507F50 → 510860'),
              stubs=sorted(stubs | {'inventory identity/allocation use Selection fixture from probe_equipped_exclusivity; original selector and root getters execute',
                                    'actual AtkParam rows build category tags; source kind is an explicit input',
                                    'selected roots passed into isolated effect container; no full equipment, animation/hit selection, collision, target poise/death or multiplayer execution'}),
              gameplayVerified=False)
a.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
print('PASS', {k: len(v) for k, v in checks.items()}, 'native hand-poise groups;', sum(r['tested'] for r in checks['categorySweep']), 'tagged-attack evaluations')
