"""Execute passive resource, poise and flask stacking with real MMV rows.

Starting resource values and recovery arrivals are explicit inputs. Original
effect insertion, qualification, getters and HP packet aggregation execute;
there is no inventory equip flow, full drink animation or gameplay simulation.
"""
import argparse
import itertools
import json
import math
import struct
from pathlib import Path
from unicorn.x86_const import *
from native_effect_runtime import OBJ, Chain, Inputs, sha

p = argparse.ArgumentParser(description=__doc__)
for name in ('exe', 'extracted', 'output'): p.add_argument(name, type=Path)
a = p.parse_args(); inputs = Inputs(a.exe, a.extracted)
effects = {6610400:7610400, 6610500:7610500, 6610600:7610600,
           6611400:7611400, 6840100:6840100, **{id:id for id in range(7001000, 7001005)}}
fields = {'maxHpRate':(0x10,0x6c9150), 'maxMpRate':(0x14,0x6c91f0), 'maxStaminaRate':(0x18,0x6c9300),
          'toughnessDamageCutRate':(0x1b4,0x502270), 'changeHpEstusFlaskCorrectRate':(0x304,None)}
rows = {}
for effect, root in effects.items():
    attach = inputs.x['tables']['AttachEffectParam'][str(effect)]; row = inputs.spells[str(root)]
    assert attach['passiveSpEffectId_1'] == root and attach['exclusivityId'] == -1
    assert row['spCategory'] == 10 and row['stateInfo'] == 0 and row['effectEndurance'] == -1
    assert all(row['invocationConditionsStateChange'+str(i)] == 0 for i in (1,2,3))
    assert all(row[k] <= 0 for k in ('cycleOccurrenceSpEffectId','replaceSpEffectId','atkOccurrenceSpEffectId'))
    for field, (offset, _) in fields.items():
        assert math.isclose(struct.unpack_from('<f',inputs.rows[root],offset)[0],row[field],rel_tol=1e-6)
    rows[str(root)] = {field:row[field] for field in fields}

f32 = lambda v: struct.unpack('<f',struct.pack('<f',v))[0]
def product(ids, field):
    v = 1.
    for id in ids: v = f32(v * f32(inputs.spells[str(id)][field]))
    return v

class Passive(Chain):
    def prepare(self, ids, disabled=False):
        for id in ids: self.insert(id)
        self.qualify(); self.update(0)
        if disabled:
            node = struct.unpack('<Q',self.u.mem_read(OBJ+8,8))[0]
            while node:
                self.u.mem_write(node+0x68,struct.pack('<I',0x800c0003))
                node = struct.unpack('<Q',self.u.mem_read(node+0x38,8))[0]
    def scalar(self, rva, args):
        self.invoke(rva,args)
        return struct.unpack('<f',(self.u.reg_read(UC_X86_REG_XMM0)&0xffffffff).to_bytes(4,'little'))[0]
    def hp(self, maximum):
        # Omit the optional physical owner / HUD / harm context, retaining
        # native restoration classification, modifiers, caps and rounding.
        self.q(OBJ+0x10,0)
        self.invoke(0x506ec0,[OBJ,maximum,OBJ+0x800,OBJ+0x808,OBJ+0x820,0])
        self.q(OBJ+0x10,OBJ+0x6000)
        return list(struct.unpack('<7i',self.u.mem_read(OBJ+0x820,28)))

checks = dict(resources=[],poise=[],flask=[],flaskCap=[],ordinaryRecovery=[]); stubs=set()
resource_roots = [7610400,7610500,7610600]
for root, copies, base, disabled in itertools.product(resource_roots,range(4),(101,1000),(False,True)):
    ids=[root]*copies; c=Passive(inputs); c.prepare(ids,disabled); values={}
    for field in ('maxHpRate','maxMpRate','maxStaminaRate'):
        value=c.scalar(fields[field][1],[base,OBJ]); expected=f32(base*(1 if disabled else product(ids,field)))
        assert value == expected,(root,copies,base,disabled,field,value,expected)
        values[field]=value
    checks['resources'].append(dict(ids=ids,base=base,disabled=disabled,values=values));stubs.update(c.stubs)

poise_roots=list(range(7001000,7001005))
sets=[[]]+[[id]*n for id in poise_roots for n in (1,2,3)]+[list(ids) for ids in itertools.permutations(poise_roots,2)]+[poise_roots]
for ids, disabled in itertools.product(sets,(False,True)):
    c=Passive(inputs); c.prepare(ids,disabled)
    value=c.scalar(0x502270,[OBJ,0]); expected=1 if disabled else product(ids,'toughnessDamageCutRate')
    assert value == expected,(ids,disabled,value,expected)
    checks['poise'].append(dict(ids=ids,disabled=disabled,multiplier=value));stubs.update(c.stubs)

# Actual percentage and fixed restoration rows; arrivals are explicit, not a
# claim that every row can be selected by this player's flask animation.
leaves=[501000,501075,501087]
for leaf in leaves:
    row=inputs.spells[str(leaf)]
    assert row['changeHpEstusFlaskRate'] <= 0 and row['changeHpEstusFlaskPoint'] <= 0
    assert row['changeHpRate'] == row['changeHpPoint'] == 0
    assert struct.unpack_from('<2i',inputs.rows[leaf],0x2f4) == (row['changeHpEstusFlaskRate'],row['changeHpEstusFlaskPoint'])

def recovery_case(positive,negative,leaf,maximum,kind):
    ids=[7611400]*positive+[6840100]*negative; c=Passive(inputs);c.prepare(ids+[leaf])
    packet=c.hp(maximum); mult=product(ids,'changeHpEstusFlaskCorrectRate');row=inputs.spells[str(leaf)]
    rate=max(-100.,f32(row['changeHpEstusFlaskRate']*mult))
    point=max(-9999.,f32(row['changeHpEstusFlaskPoint']*mult))
    expected=math.trunc(f32(-f32(f32(maximum*rate)*f32(.01))-point))
    assert packet==[0,expected,0,0,0,0,0],(positive,negative,leaf,maximum,packet,expected)
    checks[kind].append(dict(positive=positive,negative=negative,leaf=leaf,maximum=maximum,multiplier=mult,packet=packet))
    stubs.update(c.stubs)
for positive,negative,leaf,maximum in itertools.product(range(4),range(4),leaves,(101,1000)):
    recovery_case(positive,negative,leaf,maximum,'flask')
for positive,leaf,maximum in itertools.product((6,10),leaves,(101,1000)):
    recovery_case(positive,0,leaf,maximum,'flaskCap')
for positive,negative in itertools.product(range(4),range(4)):
    c=Passive(inputs);c.prepare([7611400]*positive+[6840100]*negative+[7001100])
    packet=c.hp(1000);assert packet==[2,0,2,0,0,0,0],packet
    checks['ordinaryRecovery'].append(dict(positive=positive,negative=negative,packet=packet));stubs.update(c.stubs)

output=dict(schema=1,exeSha256=sha(inputs.raw),regulationSha256=inputs.x['hashes']['regulation.bin'],paramSha256=sha(inputs.param),
            effects={str(k):v for k,v in effects.items()},rows=rows,leaves={str(id):{k:inputs.spells[str(id)][k] for k in
                ('changeHpEstusFlaskRate','changeHpEstusFlaskPoint')} for id in leaves},checks=checks,
            native=dict(maxHp='6C9150 → 50C1B0 → 510310',maxMp='6C91F0 → 50C230 → 5103D0',
                        maxStamina='6C9300 → 50C2A0 → 510480',poise='502270 → 511350',flask='506EC0 → 50B860 → 510170 / 5101B0'),
            stubs=sorted(stubs|{'base resources and recovery arrival are explicit; optional physical owner omitted for HP packet collection'}),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(map(len,checks.values())),'native passive resource cases')
