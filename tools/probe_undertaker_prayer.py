"""Trace Undertaker prayer-buff slots through actual animation dispatch.

The native slot accessor, cast dispatch, self-grant routing, qualification and
attack/timer getters run unchanged. Selected spell/actor identity, emitter-owner
identity, terminal resource commit and next-qualification delivery are fixtures.
"""
import argparse,json,struct,math
from pathlib import Path
from native_effect_runtime import *
p=argparse.ArgumentParser(description=__doc__)
for arg in ('exe','extracted','animations','output'):p.add_argument(arg,type=Path)
a=p.parse_args();i=Inputs(a.exe,a.extracted)
raw=a.extracted.with_suffix('.Magic.param').read_bytes();rows=Inputs.table(raw,0xac)
tae=json.loads(a.animations.read_text())
assert tae['bundles'][0]['sha256']=='1410035ad79edb410fa41420ec259fcb4a1037d748c9c4a3b6ae8d1366c76d0f'
r=i.spells;assert r['7037000']['stateInfo']==r['7037001']['invocationConditionsStateChange1']==2065
assert r['7037001']['effectEndurance']==60 and r['7037001']['spCategory']==20
assert math.isclose(r['7037001']['physicsAttackRate'],1.19,rel_tol=1e-6)
assert all(r['7037001'][k]==1 for k in ['magicAttackRate','fireAttackRate','thunderAttackRate','darkAttackRate'])
events=[dict(tae=t['ID'],animation=an['ID'],**e) for b in tae['bundles'] for t in b['taes']
 for an in t['animations'] for e in an['events'] if e['Type']==64 and bytes.fromhex(e['hex'])[8]==9]
assert len(events)==74
families=[]
for id,row in i.x['tables']['Magic'].items():
 if row['refId10']!=7037001:continue
 assert row['refCategory10']==row['consumeType10']==2
 assert struct.unpack_from('<i',rows[int(id)],0x90)[0]==7037001
 relevant=[e for e in events if e['tae']==2400+row['refType']]
 families.append(dict(magic=int(id),name=i.x['texts']['zh_CN']['MagicName'].get(id),motion=int(row['refType']),
  slot=9,effect=7037001,events=relevant))
assert len(families)==33
assert [f['magic'] for f in families if not f['events']]==[2006400]
unresolved_animations=[dict(animation=an['ID'],headerType=an['headerType'],header=json.loads(an['header']),
 events=[e for e in an['events'] if e['Type']==64]) for b in tae['bundles'] for t in b['taes']
 for an in t['animations'] if t['ID']==2579 and an['ID'] in (45010,45110)]
assert len(unresolved_animations)==2
assert all(an['headerType']=='Standard' and not an['header']['ImportsHKX'] and
 len(an['events'])==1 and bytes.fromhex(an['events'][0]['hex'])[8]==0 for an in unresolved_animations)
unresolved_bullets={str(id):{k:i.x['tables']['Bullet'][str(id)][k] for k in
 ['HitBulletID','intervalCreateBulletId','spEffectIDForShooter',*[f'spEffectId{n}' for n in range(5)]]}
 for id in (210640000,210640001)}
class Prayer(Chain):
 def __init__(self,magic=6050):
  super().__init__(i);self.magic=magic;self.requests=[];self.costs=[]
  self.q(OBJ+0x6190,OBJ);self.q(OBJ+0x61b8,OBJ+0x9000)
  self.q(OBJ+0x9060,OBJ+0x9100);self.q(OBJ+0x9100,OBJ+0x9200);self.q(OBJ+0x9218,STOP+0x200)
  self.q(OBJ+0x6450,STOP+0x201);self.q(OBJ+0x6418,STOP+0x202);self.q(OBJ+0x6548,STOP+0x203)
  self.q(OBJ+0x6460,STOP+0x204)
  self.q(OBJ+0x6100,OBJ+0x6000)
  address=BASE+0x40ece6+0x3808562;self.mapped(self.u,0,address,8,0,None);self.q(address,OBJ+0xd000);self.q(OBJ+0xd010,OBJ+0xd100)
 def hook(self,u,address,size,user):
  pc=address-BASE
  def end(value=0):
   u.reg_write(UC_X86_REG_RAX,value & 0xffffffffffffffff);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if address==STOP+0x200:
   out=u.reg_read(UC_X86_REG_RDX);u.mem_write(out,struct.pack('<I',self.magic));end(out)
  elif address==STOP+0x201:end(-1)
  elif address==STOP+0x202:
   out=u.reg_read(UC_X86_REG_RDX);u.mem_write(out,struct.pack('<4f',1,1,1,1));end(out)
  elif address==STOP+0x203:end(u.reg_read(UC_X86_REG_RDX))
  elif address==STOP+0x204:end(0)
  elif pc==0xe926c0:
   out=u.reg_read(UC_X86_REG_RCX);id=u.reg_read(UC_X86_REG_RDX)&0xffffffff
   u.mem_write(OBJ+0xb000,rows[id]);u.mem_write(out,struct.pack('<IiQ',id,6,OBJ+0xb000));end(out)
  elif pc in (0x3ced90,0x4d1b20,0x3d74f0,0xb31990):end(OBJ+0xd800 if pc==0x3ced90 else 0)
  elif pc==0x4b1b90:end(OBJ+0xd900)
  elif pc==0x3c7f40:
   self.requests.append(dict(target=u.reg_read(UC_X86_REG_RCX),id=u.reg_read(UC_X86_REG_RDX)&0xffffffff));end()
  elif pc==0x384a30:
   obj=u.reg_read(UC_X86_REG_RCX);self.costs.append(list(struct.unpack('<5i',u.mem_read(obj+0xb4,20))));end()
  else:super().hook(u,address,size,user)
 def event(self,payload,active=1):
  self.q(OBJ+0x8018,OBJ+0x6000);self.q(OBJ+0x8108,OBJ+0x8200);self.q(OBJ+0x8120,OBJ+0x8300)
  self.u.mem_write(OBJ+0x8118,bytes([active]));self.u.mem_write(OBJ+0x8200,bytes.fromhex(payload))
  self.invoke(0x40eb30,[OBJ+0x8000,OBJ+0x8100])

checks=dict(slots=[],dispatch=[],lifecycle=[],attack=[]);runtime_stubs=set()
for f in families:
 c=Prayer(f['magic']);c.u.mem_write(OBJ+0xb000,rows[f['magic']]);c.u.mem_write(OBJ+0xa800,struct.pack('<IiQ',f['magic'],6,OBJ+0xb000))
 c.invoke(0xe91fd0,[OBJ+0xa800,OBJ+0xa900,9]);category,id,consume=struct.unpack('<iiB',c.u.mem_read(OBJ+0xa900,9))
 assert (category,id,consume)==(2,7037001,2)
 checks['slots'].append(dict(magic=f['magic'],category=category,effect=id,consumeType=consume,animationMatched=bool(f['events'])))
 # Match each actual hand/animation event instead of assuming a refId is fired.
 for event in f['events']:
  for copies in (0,1,3):
   for active in (0,1):
    c=Prayer(f['magic'])
    for _ in range(copies):c.insert(7037000)
    c.qualify();c.update(0);c.event(event['hex'],active)
    assert c.requests==([dict(target=OBJ+0x6000,id=7037001)] if active else [])
    for grant in c.requests:c.insert(grant['id'])
    c.qualify();c.update(0);rates=c.attack()
    assert all(math.isclose(v,(1.19 if copies and active and n==0 else 1),rel_tol=1e-6) for n,v in enumerate(rates))
    checks['dispatch'].append(dict(magic=f['magic'],animation=event['animation'],eventIndex=event['index'],
     copies=copies,active=active,grants=[g['id'] for g in c.requests],rates=rates,costRequests=c.costs))
    runtime_stubs.update(c.stubs)

base=next(f for f in families if f['magic']==6050)['events'][0]
for copies in (0,1,3):
 for casts in ([0],[0,120]):
  c=Prayer()
  for _ in range(copies):c.insert(7037000)
  c.qualify();c.update(0);changes=[];previous=None
  for tick in range(380):
   if tick in casts:
    c.event(base['hex'])
    for grant in c.requests:c.insert(grant['id'])
    c.requests.clear()
   c.qualify();c.update(.25);rates=[round(v,5) for v in c.attack()]
   if rates!=previous:changes.append(dict(tick=tick,rates=rates));previous=rates
  assert len(changes)==(2 if copies else 1)
  if copies:
   assert changes[0]['rates']==[1.19,1,1,1,1] and changes[-1]['rates']==[1]*5
   assert abs(changes[-1]['tick']*.25-(max(casts)*.25+60))<=.5
  checks['lifecycle'].append(dict(copies=copies,casts=casts,dt=.25,changes=changes))
  runtime_stubs.update(c.stubs)
for kind in range(6):
 c=Prayer();c.insert(7037000);c.qualify();c.update(0);c.insert(7037001);c.qualify();c.update(0)
 rates=c.attack(kind)
 assert all(math.isclose(v,(1.19 if kind<5 and n==0 else 1),rel_tol=1e-6) for n,v in enumerate(rates))
 checks['attack'].append(dict(kind=kind,rates=rates))
 runtime_stubs.update(c.stubs)
output=dict(schema=1,exeSha256=sha(i.raw),regulationSha256=i.x['hashes']['regulation.bin'],paramSha256=sha(i.param),
 magicParamSha256=sha(raw),animationSha256=tae['bundles'][0]['sha256'],root=7037000,leaf=7037001,families=families,
 unresolvedMotion=dict(magic=2006400,tae=2579,animations=unresolved_animations,bullets=unresolved_bullets),
 checks=checks,stubs=['E926C0 actual Magic lookup; wrapper version 6',
 'selected-spell virtual supplies requested Magic ID; no equipped-catalyst legality test',
 'actor virtuals supply no weapon row, hand identity and neutral effect context / cost modifier',
 '3CED90/4D1B20 neutral animation-owner identity', '4B1B90 available emitter-owner identity',
 '3C7F40 self-grant recorder; delivered before next qualification',
 '384A30 terminal cost-commit recorder; native cost calculation is retained',
 '3D74F0/B31990 action/HUD notifications omitted',*sorted(runtime_stubs)],gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS:',{k:len(v) for k,v in checks.items()})
