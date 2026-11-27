"""Verify guard stamina multipliers through native selection and cost calculation.

Inventory, actor identity, parameter lookups and the independent stat correction
are explicit fixtures. Native insertion, qualification, aggregation and the
complete guard cost calculator execute unchanged; no live gameplay is run.
"""
import argparse
import itertools
import json
import math
import struct
from pathlib import Path
from native_effect_runtime import *

p = argparse.ArgumentParser(description=__doc__)
for name in ('exe', 'extracted', 'assets', 'output'):
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


assets = json.loads(a.assets.read_text())
assert assets['hashes']['regulation.bin'] == x.x['hashes']['regulation.bin']
weapon_raw = a.assets.with_suffix('.EquipParamWeapon.param').read_bytes()
weapons = Inputs.table(weapon_raw, 0x2a8)
behavior_raw = a.extracted.with_suffix('.BehaviorParam_PC.param').read_bytes()
behaviors = Inputs.table(behavior_raw, 0x20)
attack_raw = a.extracted.with_suffix('.AtkParam_Pc.param').read_bytes()
attacks = Inputs.table(attack_raw, 0x1d0)
families = []
for effect, rate, category in ((341000, .8, 0), (8220000, .9, 10), (8220001, .85, 10), (8220002, .8, 10)):
    attach = x.x['tables']['AttachEffectParam'][str(effect)]
    row = x.spells[str(effect)]
    assert attach['passiveSpEffectId_1'] == effect and attach['exclusivityId'] == -1
    assert all(attach[k] == -1 for k in ('passiveSpEffectId_2', 'passiveSpEffectId_3', 'permanentSpEffectId'))
    assert (row['spCategory'], row['stateInfo'], row['wepParamChange'], row['effectEndurance']) == (category, 158, 0, -1)
    assert math.isclose(row['guardStaminaMult'], rate, rel_tol=1e-6)
    assert math.isclose(struct.unpack_from('<f', x.rows[effect], 0x388)[0], rate, rel_tol=1e-6)
    assert all(row['invocationConditionsStateChange' + str(i)] == 0 for i in (1, 2, 3))
    assert all(row[k] == -1 for k in ('cycleOccurrenceSpEffectId', 'replaceSpEffectId', 'atkOccurrenceSpEffectId'))
    families.append(dict(effect=effect, root=effect, rate=rate, category=category))
by_effect = {f['effect']: f for f in families}


class Guard(Chain):
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

    def number(self):
        return struct.unpack('<f', (self.u.reg_read(UC_X86_REG_XMM0) & 0xffffffff).to_bytes(4, 'little'))[0]

    def rate(self, selector=None):
        self.invoke(0x506dc0 if selector is None else 0x506ce0, [OBJ, selector or 0])
        return self.number()

    def hook(self, u, address, size, user):
        pc = address - BASE
        def ret(value=0):
            u.reg_write(UC_X86_REG_RAX, value)
            sp = u.reg_read(UC_X86_REG_RSP)
            u.reg_write(UC_X86_REG_RIP, struct.unpack('<Q', u.mem_read(sp, 8))[0])
            u.reg_write(UC_X86_REG_RSP, sp + 8)
        ptr = u.reg_read(UC_X86_REG_RCX)
        if pc == 0xe6fcb0:
            self.stubs.add('E6FCB0 actual BehaviorParam_PC lookup')
            id = u.reg_read(UC_X86_REG_RDX)
            u.mem_write(OBJ + 0xc000, behaviors[id])
            self.q(ptr + 8, OBJ + 0xc000)
            ret(ptr)
        elif pc == 0xea7fc0:
            self.stubs.add('EA7FC0 actual EquipParamWeapon lookup; no reinforcement')
            id = u.reg_read(UC_X86_REG_RDX)
            u.mem_write(OBJ + 0xc100, weapons[id])
            self.q(ptr + 8, OBJ + 0xc100)
            ret(ptr)
        elif pc == 0xea9a60:
            self.stubs.add('EA9A60 absent reinforcement fixture')
            self.q(ptr + 8, 0)
            ret(ptr)
        elif pc == 0xe6d630:
            self.stubs.add('E6D630 actual AtkParam_Pc lookup from original E6FC70')
            id = u.reg_read(UC_X86_REG_R8) & 0xffffffff
            if id in attacks:
                u.mem_write(OBJ + 0xc400, attacks[id])
                self.q(ptr + 0x10, OBJ + 0xc400)
            ret(ptr)
        elif pc == 0x6cc570:
            self.stubs.add('6CC570 independent guard stat correction set to zero')
            u.reg_write(UC_X86_REG_XMM0, 0)
            ret()
        elif pc == 0x6d0080:
            self.stubs.add('6D0080 guarding eligibility explicit fixture')
            ret(int(self.guarding))
        elif pc == 0x3ced90:
            self.stubs.add('3CED90 actor identity fixture')
            ret(OBJ + 0xd800)
        elif pc in (0x4d1b20, 0x3d4180):
            self.stubs.add('4D1B20/3D4180 actor early-exit and debug flags false')
            ret()
        elif address == STOP + 0x200:
            ret(100)  # slot outside optional weapon-skill branch
        elif address == STOP + 0x208:
            ret(self.weapon)
        elif address == STOP + 0x210:
            ret(OBJ + 0xd800)
        else:
            super().hook(u, address, size, user)

    def cost(self, weapon, behavior, incoming, guarding=True):
        self.weapon, self.guarding = weapon, guarding
        actor, vtable, stance = OBJ + 0xd000, OBJ + 0xe000, OBJ + 0xe800
        self.q(actor, vtable)
        self.q(vtable + 0x268, STOP + 0x200)
        self.q(vtable + 0x250, STOP + 0x208)
        self.q(vtable + 0x190, STOP + 0x210)
        self.q(actor + 0x190, OBJ)
        self.q(actor + 0x670, stance)
        self.u.mem_write(stance, struct.pack('<I', 0))
        self.invoke(0x6687f0, [actor, 0, behavior], {UC_X86_REG_XMM1: incoming})
        return self.number()


checks = dict(selection=[], multipliers=[], costs=[])
stubs = set()
cases = [[]] + [[f['effect']] * copies for f in families for copies in (1, 2, 3, 6)]
cases += [[8220000, 8220001, 8220002], [8220002, 8220001, 8220000],
          [341000, 341000, 8220000, 8220001, 8220002],
          [8220002, 8220001, 8220000, 341000, 341000]]
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
    for inactive in (False, True):
        c = Guard(x)
        c.prepare(roots, inactive)
        active = [e for e in effects if e != 341000] + ([341000] if 341000 in effects else [])
        assert sorted(n['id'] for n in c.nodes()) == sorted(active)
        expected_rate = 1 if inactive else math.prod(by_effect[e]['rate'] for e in active)
        for selector in (None, 0, 1, 2, 3):
            actual = c.rate(selector)
            expected = 1 if selector == 3 else expected_rate
            assert math.isclose(actual, expected, rel_tol=1e-6), (effects, selector, actual, expected)
            checks['multipliers'].append(dict(effects=effects, inactive=inactive, selector=selector, nodes=c.nodes(), multiplier=actual))
        for weapon, behavior, incoming, guarding in itertools.product((1000, 24050000, 31050000, 11000), (10, 11, 530), (0, 100, 257.5), (False, True)):
            guard = assets['tables']['EquipParamWeapon'][str(weapon)]['staminaGuardDef']
            b = x.x['tables']['BehaviorParam_PC'][str(behavior)]
            cut = x.x['tables']['AtkParam_Pc'].get(str(b['refId']), {}).get('guardStaminaCutRate', 0) if b['refType'] == 0 else 0
            assert struct.unpack_from('<h', weapons[weapon], 0xd8)[0] == guard
            assert struct.unpack_from('<i', behaviors[behavior], 0x14)[0] == b['stamina']
            if b['refType'] == 0 and b['refId'] in attacks:
                assert struct.unpack_from('<h', attacks[b['refId']], 0x64)[0] == cut
            reduction = max(0, min(100, (guard + 1) * (1 + cut / 100))) if guarding else 0
            expected = incoming * (1 - reduction / 100) * expected_rate + b['stamina']
            actual = c.cost(weapon, behavior, incoming, guarding)
            assert math.isclose(actual, expected, rel_tol=2e-6, abs_tol=1e-5), (effects, weapon, behavior, incoming, guarding, actual, expected)
            checks['costs'].append(dict(effects=effects, inactive=inactive, weapon=weapon, behavior=behavior,
                                       incoming=incoming, guarding=guarding, reduction=reduction,
                                       fixed=b['stamina'], multiplier=expected_rate, result=actual))
        stubs.update(c.stubs)

output = dict(schema=1, exeSha256=sha(x.raw), regulationSha256=x.x['hashes']['regulation.bin'],
              paramSha256=sha(x.param), attachParamSha256=sha(raw), weaponParamSha256=sha(weapon_raw),
              behaviorParamSha256=sha(behavior_raw), attackParamSha256=sha(attack_raw),
              families=families, checks=checks,
              native=dict(selection='4FEA30 → E6E150 → E6E3B0', aggregate='506CE0 / 506DC0',
                          cost='6687F0 → 506DC0 → 6C5B10', attack='E6FC70'),
              stubs=sorted(stubs | {'inventory identity/allocation use Selection fixture from probe_equipped_exclusivity',
                                    'selected roots passed into isolated effect container; no full equipment, collision, stamina setter, guard break or multiplayer execution',
                                    'actor slot and stance fixture skip two-hand and weapon-skill modifiers; guard stat correction zero; no reinforcement'}),
              gameplayVerified=False)
a.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
print('PASS', {k: len(v) for k, v in checks.items()}, 'native guard stamina checks')

