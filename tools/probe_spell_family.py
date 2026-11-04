"""Execute spell-family damage filters and repeated relic multipliers.

Actual Magic rows build the native category bitset. Source kind follows the
parameter forwarding observed in the projectile path; the full cast/projectile
pipeline is not simulated. Effect insertion and damage-filter/getter code run
unchanged, with the attack packet and absent auxiliary attack row explicit.
"""
import argparse
import itertools
import json
import math
import struct
from pathlib import Path
from native_effect_runtime import OBJ, Chain, Inputs, sha

p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','output'):p.add_argument(name,type=Path)
a=p.parse_args();inputs=Inputs(a.exe,a.extracted)
magic_raw=a.extracted.with_suffix('.Magic.param').read_bytes()
magic_rows=Inputs.table(magic_raw,0xac);magic=inputs.x['tables']['Magic']
roots=[*range(7043200,7043900,100),*range(7044000,7044700,100)]
families=[]
for root in roots:
    r=inputs.spells[str(root)];raw=inputs.rows[root]
    attach=inputs.x['tables']['AttachEffectParam'][str(root)]
    assert attach['passiveSpEffectId_1']==root and attach['exclusivityId']==-1
    assert r['spCategory']==10 and r['stateInfo']==71 and r['wepParamChange']==3
    assert r['effectEndurance']==-1
    assert all(r['invocationConditionsStateChange'+str(i)]==0 for i in (1,2,3))
    assert all(r[k]<=0 for k in ('replaceSpEffectId','cycleOccurrenceSpEffectId','atkOccurrenceSpEffectId'))
    assert raw[0x13a]==r['magicSubCategoryChange1'] and raw[0x13b]==raw[0x328]==0
    kind=3 if root<7044000 else 4
    assert bool(raw[0x160]&128)==(kind==3) and bool(raw[0x161]&1)==(kind==4)
    rates=[r[k+'AttackRate'] for k in ('physics','magic','fire','thunder','dark')]
    assert all(math.isclose(v,1.025,rel_tol=1e-6) for v in rates)
    families.append(dict(root=root,kind=kind,category=raw[0x13a],multiplier=rates[0]))
categories={r['category'] for r in families};spells=[]
for key,r in magic.items():
    if not categories.intersection({r['subCategory1'],r['subCategory2']}):continue
    id=int(key);raw=magic_rows[id]
    assert raw[0x62]==r['subCategory1'] and raw[0x63]==r['subCategory2']
    assert raw[0x28]==r['spEffectCategory'] and raw[0x28] in (3,4)
    spells.append(dict(id=id,kind=raw[0x28],categories=[v for v in (raw[0x62],raw[0x63]) if v],
                       name=inputs.x['texts']['zh_CN']['MagicName'].get(key)))
assert len(spells)==99

class SpellAttack(Chain):
    def prepare(self,roots,disabled=False):
        for root in roots:self.insert(root)
        self.qualify();self.update(0)
        if disabled:
            node=struct.unpack('<Q',self.u.mem_read(OBJ+8,8))[0]
            while node:
                self.u.mem_write(node+0x68,struct.pack('<I',0x800c0003))
                node=struct.unpack('<Q',self.u.mem_read(node+0x38,8))[0]
    def spell(self,spell,kind=None):
        self.u.mem_write(OBJ+0x8000,magic_rows[spell['id']]);self.q(OBJ+0x9008,OBJ+0x8000)
        self.u.mem_write(OBJ+0x808,struct.pack('<iiB',40000,1,spell['kind'] if kind is None else kind))
        # Original Magic wrapper reads +62/+63, then E6D3E0 sets category bits.
        self.invoke(0xe92180,[OBJ+0x9000,OBJ+0x814])
        tags=bytes(self.u.mem_read(OBJ+0x814,32))
        assert int.from_bytes(tags,'little')==sum(1<<c for c in set(spell['categories']))
        self.invoke(0x502830,[OBJ,OBJ+0x800,-1,-1])
        return [struct.unpack('<f',self.u.mem_read(OBJ+0x800+off,4))[0] for off in (0x90,0xa4,0xa8,0xac,0xb0)]

checks=dict(selection=[],repeat=[],kinds=[],mixed=[]);stubs=set()
def expected(family,spell,kind=None):
    return family['category'] in spell['categories'] and family['kind']==(spell['kind'] if kind is None else kind)
def verify(values,multiplier):assert all(math.isclose(v,multiplier,rel_tol=1e-6) for v in values),(values,multiplier)
def record(key,c,**row):checks[key].append(row);stubs.update(c.stubs)
for family,spell in itertools.product(families,spells):
    c=SpellAttack(inputs);c.prepare([family['root']]);values=c.spell(spell)
    applied=expected(family,spell);verify(values,family['multiplier'] if applied else 1)
    record('selection',c,root=family['root'],spell=spell['id'],applied=applied,values=values)
for family in families:
    spell=next(s for s in spells if expected(family,s))
    for copies,disabled in itertools.product(range(4),(False,True)):
        c=SpellAttack(inputs);c.prepare([family['root']]*copies,disabled);values=c.spell(spell)
        verify(values,1 if disabled else family['multiplier']**copies)
        record('repeat',c,root=family['root'],spell=spell['id'],copies=copies,disabled=disabled,values=values)
    for kind in range(13):
        c=SpellAttack(inputs);c.prepare([family['root']]);values=c.spell(spell,kind)
        verify(values,family['multiplier'] if expected(family,spell,kind) else 1)
        record('kinds',c,root=family['root'],spell=spell['id'],kind=kind,values=values)
for spell in spells:
    c=SpellAttack(inputs);c.prepare(roots);values=c.spell(spell)
    matched=[f['root'] for f in families if expected(f,spell)]
    verify(values,math.prod(f['multiplier'] for f in families if expected(f,spell)))
    record('mixed',c,spell=spell['id'],matched=matched,values=values)
output=dict(schema=1,exeSha256=sha(inputs.raw),regulationSha256=inputs.x['hashes']['regulation.bin'],paramSha256=sha(inputs.param),
            magicParamSha256=sha(magic_raw),families=families,spells=spells,checks=checks,
            native=dict(tags='E92180 → E6D3E0',packet='50F2A0',filter='511010 → EA1B00 / EA1D40',damage='502830'),
            stubs=sorted(stubs|{'attack packet has explicit source kind; full cast and projectile pipeline not executed'}),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(map(len,checks.values())),'native spell-family cases')
