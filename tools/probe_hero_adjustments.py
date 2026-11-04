"""Execute role-gated attribute adjustments, duplication and combined rounding.

Real container insertion/eligibility and 501CE0 / 6C8A60 arithmetic operate on
actual HeroStatus rows. Default hero base curves are supplied explicitly. The
live stat-module refresh and derived HP/FP/resource synchronization are not run.
"""
import argparse
import itertools
import json
import struct
from pathlib import Path
from native_effect_runtime import BASE,OBJ,STOP,Chain,Inputs,sha
from unicorn.x86_const import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','heroes','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted);heroes=json.loads(a.heroes.read_text())
assert heroes['hashes']['regulation.bin']==x.x['hashes']['regulation.bin']
raw=a.extracted.with_suffix('.HeroStatusParam.param').read_bytes();rows=Inputs.table(raw,28)
fields=['statVigor','statMind','statEndurance','statStrength','statDexterity','statIntelligence','statFaith','statArcane']
for id,row in rows.items():
 assert list(struct.unpack_from('<8b',row,6))==[x.x['tables']['HeroStatusParam'][str(id)][f] for f in fields]
base_evidence=json.loads((Path(__file__).resolve().parents[1]/'data/effect-native-evidence.json').read_text())
assert base_evidence['heroParamSha256']==sha(raw) and base_evidence['paramSha256']==sha(x.param)
known={(r['modifier'],r['level']):r['values'] for r in base_evidence['hero']}
families=[]
for hero in range(1,11):
 marker=7999000+(hero-1)*10;state=x.spells[str(marker)]['stateInfo']
 roots=sorted(int(k) for k,r in x.spells.items() if r['stateInfo']==2123 and r['invocationConditionsStateChange1']==state)
 assert len(roots)==2
 effects=[]
 for root in roots:
  row=x.spells[str(root)];assert row['spCategory']==20 and row['effectEndurance']==-1
  assert row['cycleOccurrenceSpEffectId']==row['replaceSpEffectId']==-1
  assert row['invocationConditionsStateChange2']==row['invocationConditionsStateChange3']==0
  assert row['heroStatusModifier'] in {k[0] for k in known}
  ids=[int(k) for k,r in x.x['tables']['AttachEffectParam'].items() if r['passiveSpEffectId_1']==root]
  assert len(ids)==1 and x.x['tables']['AttachEffectParam'][str(ids[0])]['exclusivityId']>=0
  effects.append(ids[0])
 families.append(dict(hero=hero,base=int(heroes['tables']['HeroParam'][str(hero)]['heroStatusParamId']),
                      marker=marker,state=state,roots=roots,effects=effects,
                      modifiers=[x.spells[str(root)]['heroStatusModifier'] for root in roots],
                      runtimeExclusive=[x.x['tables']['AttachEffectParam'][str(effect)]['exclusivityId'] for effect in effects]))
assert len({root for f in families for root in f['roots']})==20
class Hero(Chain):
 def __init__(self):
  super().__init__(x);self.q(OBJ+0x6390,STOP+0x400);self.u.mem_map(OBJ+0x60000,0x10000)
  self.herorows={id:OBJ+0x60000+i*0x40 for i,id in enumerate(rows)}
  for id,addr in self.herorows.items():self.u.mem_write(addr,rows[id])
  self.stubs.add('owner virtual +190 has no live stat module; original attribute aggregate invoked explicitly')
 def hook(self,u,address,size,user):
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP)
   u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  pc=address-BASE
  if address==STOP+0x400:ret()
  elif pc==0xe78730:
   self.stubs.add('E78730 actual HeroStatus PARAM lookup')
   id=u.reg_read(UC_X86_REG_RDX)&0xffffffff;wrapper=u.reg_read(UC_X86_REG_RCX)
   u.mem_write(wrapper,struct.pack('<IIQ',id,0,self.herorows.get(id,0)));ret(wrapper)
  elif pc==0xe78720:
   self.stubs.add('E78720 PARAM wrapper cleanup');ret()
  elif pc==0x26909a0:
   self.stubs.add('26909A0 security cookie');ret(u.reg_read(UC_X86_REG_RAX))
  else:super().hook(u,address,size,user)
 def curve(self,id,level):
  self.u.mem_write(OBJ+0x800,bytes(28))
  assert self.invoke(0x6c8a60,[OBJ+0x800,level,id])&255
  return list(struct.unpack('<8b',self.u.mem_read(OBJ+0x806,8)))
 def stats(self,base,level):
  if base is None:self.u.mem_write(OBJ+0x800,bytes(28))
  else:self.curve(base,level)
  self.invoke(0x501ce0,[OBJ,OBJ+0x800,level])
  return list(struct.unpack('<8b',self.u.mem_read(OBJ+0x806,8)))
def settle(c):
 for _ in range(3):c.qualify();c.update(0)
def start(family,counts,marker):
 c=Hero()
 if marker:c.insert(marker)
 for root,count in zip(family['roots'],counts):
  for _ in range(count):c.insert(root)
 settle(c)
 for root,count in zip(family['roots'],counts):assert sum(n['id']==root for n in c.nodes())==bool(count)
 return c
checks=dict(single=[],combined=[],roleChange=[],disabled=[],floor=[]);stubs=set()
def record(key,c,**row):checks[key].append(row);stubs.update(c.stubs)
def expected(c,family,counts,level,active=True):
 base=c.curve(family['base'],level)
 adjustments=[known[(modifier,level)] for modifier,count in zip(family['modifiers'],counts) if count and active]
 return [max(0,b+sum(v[i] for v in adjustments)) for i,b in enumerate(base)]
for family,index,copies,relation in itertools.product(families,(0,1),range(4),('absent','matching','other')):
 marker=family['marker'] if relation=='matching' else families[family['hero']%10]['marker'] if relation=='other' else None
 counts=[copies if i==index else 0 for i in range(2)];c=start(family,counts,marker);levels=[]
 for level in range(1,21):
  values=c.stats(family['base'],level)
  assert values==expected(c,family,counts,level,relation=='matching')
  levels.append(dict(level=level,values=values))
 record('single',c,hero=family['hero'],effect=family['effects'][index],copies=copies,role=relation,levels=levels)
for family,first,second in itertools.product(families,range(4),range(4)):
 c=start(family,[first,second],family['marker']);levels=[]
 for level in range(1,21):
  values=c.stats(family['base'],level)
  assert values==expected(c,family,[first,second],level)
  levels.append(dict(level=level,values=values))
 record('combined',c,hero=family['hero'],copies=[first,second],levels=levels)
for family,index in itertools.product(families,(0,1)):
 counts=[int(i==index) for i in range(2)];c=start(family,counts,None)
 before=c.stats(family['base'],12);marker=c.insert(family['marker']);settle(c)
 active=c.stats(family['base'],12)
 assert active==expected(c,family,counts,12)
 c.invoke(0x505280,[OBJ,marker]);settle(c)
 removed=c.stats(family['base'],12);assert removed==before==expected(c,family,counts,12,False)
 c.insert(family['marker']);settle(c);restored=c.stats(family['base'],12);assert restored==active
 record('roleChange',c,effect=family['effects'][index],before=before,active=active,removed=removed,restored=restored)
 # Consumer's validity gate is independent of the role-condition input.
 ptr=struct.unpack('<Q',c.u.mem_read(OBJ+8,8))[0]
 while ptr:
  if struct.unpack('<i',c.u.mem_read(ptr+8,4))[0] in family['roots']:c.u.mem_write(ptr+0x68,struct.pack('<I',0x800c0003))
  ptr=struct.unpack('<Q',c.u.mem_read(ptr+0x38,8))[0]
 values=c.stats(family['base'],12);assert values==before
 record('disabled',c,effect=family['effects'][index],values=values)
 # An explicit zero-baseline boundary, not a claim that this is a hero's base.
 c=start(family,counts,family['marker']);values=c.stats(None,12)
 delta=known[(family['modifiers'][index],12)]
 assert values==[max(0,v) for v in delta]
 record('floor',c,effect=family['effects'][index],baseline=[0]*8,adjustment=delta,values=values)
output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),
            heroStatusParamSha256=sha(raw),heroParamSha256=sha(a.heroes.with_suffix('.HeroParam.param').read_bytes()),
            families=families,checks=checks,native=dict(insert='50D060',qualify='5057D0',update='50ACD0',
            remove='505280',aggregate='501CE0',curve='6C8A60',caller='209BC0 → 501CE0; 209E20 signed attribute write'),
            stubs=sorted(stubs|{'default hero base curve and role markers supplied; live stat refresh and derived resources not simulated',
                              'zero baseline supplied only for lower-bound checks'}),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(map(len,checks.values())),'native hero adjustment scenarios')
