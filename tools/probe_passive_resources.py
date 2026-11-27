"""Execute passive resource, poise and flask stacking with real MMV rows.

Starting resource values and recovery arrivals are explicit inputs. Original
effect insertion, qualification, getters and HP packet aggregation execute;
resource-capacity roots also pass native equipment selection; full drink
animation, current resource synchronization and gameplay are not simulated.
"""
import argparse
import itertools
import json
import math
import struct
from pathlib import Path
from unicorn.x86_const import *
from native_effect_runtime import BASE, OBJ, STOP, Chain, Inputs, sha

p = argparse.ArgumentParser(description=__doc__)
for name in ('exe', 'extracted', 'output'): p.add_argument(name, type=Path)
a = p.parse_args(); inputs = Inputs(a.exe, a.extracted)
effects = {8850051:8850050, 6610400:7610400, 6610500:7610500, 6610600:7610600,
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

attach_raw = a.extracted.with_suffix('.AttachEffectParam.param').read_bytes()
assert sha(attach_raw) == 'ae8128ed510a532d0fa7cb56fa9c86e4a44c9d815dd4ee01c05821d5f50a9827'
attach_rows = Inputs.table(attach_raw, 0x44)
assert {k for k,v in inputs.spells['8850050'].items() if v != inputs.spells['7610400'][k]} == {'maxHpRate'}
assert math.isclose(inputs.spells['8850050']['maxHpRate'], 1.12, rel_tol=1e-6)
MAN=OBJ+0x8000;OUT=OBJ+0x9000;BITS=OBJ+0x9100
class Selection(Chain):
 def __init__(self,slots,hero=1):
  super().__init__(inputs);self.slots=slots;self.hero=hero;self.cache={};self.q(OBJ+0x7118,STOP+0x900)
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
   u.mem_write(instance+0x18,struct.pack('<6i',*(effects+[-1]*6)[:6]));u.mem_write(ptr,bytes(24));self.q(ptr+8,instance);u.mem_write(ptr+0x10,struct.pack('<I',0x80000000|2000100));ret(ptr)
  elif pc==0x69e5a0:ret()
  elif pc==0xe6e430:
   ptr=u.reg_read(UC_X86_REG_RCX);id=u.reg_read(UC_X86_REG_RDX)&0xffffffff
   if id in attach_rows and id not in self.cache:
    self.cache[id]=OBJ+0x10000+len(self.cache)*0x100;u.mem_write(self.cache[id],attach_rows[id])
   self.q(ptr,self.cache.get(id,0));u.mem_write(ptr+8,struct.pack('<I',id));ret(ptr)
  else:super().hook(u,address,size,user)
 def select(self):
  self.invoke(0x4fea30,[MAN,OUT]);bits=int.from_bytes(self.u.mem_read(BITS,20),'little');return [i for i in range(144) if bits>>i&1]


checks = dict(resources=[],poise=[],flask=[],flaskCap=[],ordinaryRecovery=[],selection=[],mixedResources=[]); stubs=set()
for effect,copies,hero in itertools.product((6610400,6610500,6610600,8850051),(1,2,3,6),range(11)):
    c=Selection([[effect]]*copies,hero);bits=c.select();selected=[]
    for index in range(copies):
        assert index*6 in bits
        id=struct.unpack('<i',c.u.mem_read(OBJ+0xa000+index*0x80+0x18,4))[0];assert id==effect
        c.invoke(0xe6e150,[OBJ+0x9200,id]);selected.append(c.invoke(0xe6e3b0,[OBJ+0x9200,0])&0xffffffff)
    assert selected==[effects[effect]]*copies
    v=Passive(inputs);v.prepare(selected)
    assert [n['id'] for n in v.nodes()]==selected
    values={field:v.scalar(fields[field][1],[1000,OBJ]) for field in ('maxHpRate','maxMpRate','maxStaminaRate')}
    assert all(value==f32(1000*product(selected,field)) for field,value in values.items())
    checks['selection'].append(dict(effect=effect,copies=copies,hero=hero,selected=selected,values=values));stubs.update(c.stubs);stubs.update(v.stubs)
for ids,base,disabled in itertools.product(([7610400,8850050],[8850050,7610400],[7610400,8850050]*2,[8850050,7610400]*2),(101,1000,100000),(False,True)):
    c=Passive(inputs);c.prepare(ids,disabled)
    value=c.scalar(0x6c9150,[base,OBJ]);expected=f32(base*(1 if disabled else product(ids,'maxHpRate')))
    assert value==expected,(ids,base,disabled,value,expected)
    checks['mixedResources'].append(dict(ids=ids,base=base,disabled=disabled,value=value));stubs.update(c.stubs)
print('PASS selection and mixed resource capacity',len(checks['selection']),len(checks['mixedResources']),flush=True)

resource_roots = [7610400,7610500,7610600,8850050]
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
            attachParamSha256=sha(attach_raw),effects={str(k):v for k,v in effects.items()},rows=rows,leaves={str(id):{k:inputs.spells[str(id)][k] for k in
                ('changeHpEstusFlaskRate','changeHpEstusFlaskPoint')} for id in leaves},checks=checks,
            native=dict(selection='4FEA30 → E6E150 → E6E3B0',maxHp='6C9150 → 50C1B0 → 510310',maxMp='6C91F0 → 50C230 → 5103D0',
                        maxStamina='6C9300 → 50C2A0 → 510480',poise='502270 → 511350',flask='506EC0 → 50B860 → 510170 / 5101B0'),
            stubs=sorted(stubs|{'synthetic inventory in positive slot0 for capacity roots; draw legality and full equipment rebuild not asserted', 'base resources and recovery arrival are explicit; optional physical owner omitted for HP packet collection'}),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(map(len,checks.values())),'native passive resource cases')
