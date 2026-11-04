"""Execute reviewed Raider totem paths using pinned PC code and MMV rows.

Synthetic character identity, PARAM lookups and effect-application recording are
fixtures. Behavior selection, duration getters, timer expiration, effect matching,
kill dispatch and numeric calculators execute unchanged. No game process is run.
"""
from pathlib import Path
import argparse,json,struct,hashlib,math
import pefile
from unicorn import *
from unicorn.x86_const import *
BASE=0x140000000; OBJ=0x10000000; STACK=0x20000000; STOP=0x30000000
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('exe',type=Path)
parser.add_argument('effects',type=Path)
parser.add_argument('assets',type=Path)
parser.add_argument('animations',type=Path)
parser.add_argument('output',type=Path)
a=parser.parse_args()
sha=lambda b:hashlib.sha256(b).hexdigest()
exe=a.exe.read_bytes()
assert sha(exe)=='9545e8732919bb6a63904cb73223641b3c4f9a67869be5722612acca413e8b3a'
pe=pefile.PE(data=exe,fast_load=True)
x=json.loads(a.effects.read_text());assets=json.loads(a.assets.read_text())
assert x['hashes']['regulation.bin']==assets['hashes']['regulation.bin']=='3305ac374b4da1db440e2b6644bc2c3c0ae96b98df9627f1a0e7a2b06d265c06'
tae=json.loads(a.animations.read_text())
assert tae['bundles'][0]['sha256']=='1410035ad79edb410fa41420ec259fcb4a1037d748c9c4a3b6ae8d1366c76d0f'

def table(path,size):
 raw=Path(path).read_bytes();return {struct.unpack_from('<i',raw,0x40+i*24)[0]:raw[off:off+size] for i in range(struct.unpack_from('<H',raw,10)[0]) for off in [struct.unpack_from('<Q',raw,0x48+i*24)[0]]}
spells=table(a.effects.with_suffix('.SpEffectParam.param'),0x400)
weapons=table(a.assets.with_suffix('.EquipParamWeapon.param'),0x298)
assetrows=table(a.assets.with_suffix('.AssetEnvironmentGeometryParam.param'),0x100)
behaviors=table(a.effects.with_suffix('.BehaviorParam_PC.param'),0x30)
stubs=set()
def execute(rva,args,ids=(),flags=0,setup=None,xmm=None):
 u=Uc(UC_ARCH_X86,UC_MODE_64);u.mem_map(OBJ,0x40000);u.mem_map(STACK,0x10000);u.mem_map(STOP,0x1000)
 nodes=[OBJ+0x1000+i*0x600 for i in range(len(ids))]
 if nodes:u.mem_write(OBJ+8,struct.pack('<Q',nodes[0]))
 for i,(id,n) in enumerate(zip(ids,nodes)):
  u.mem_write(n,struct.pack('<Qi',n+0x100,id));u.mem_write(n+0x100,spells[id]);u.mem_write(n+0x4c,struct.pack('<f',-1));u.mem_write(n+0x68,struct.pack('<I',flags))
  if i+1<len(nodes):u.mem_write(n+0x38,struct.pack('<Q',nodes[i+1]))
 sp=STACK+0x8008;u.mem_write(sp,struct.pack('<Q',STOP));u.reg_write(UC_X86_REG_RSP,sp)
 for i,v in enumerate(args[4:]):u.mem_write(sp+0x28+i*8,struct.pack('<Q',v))
 for reg,v in zip([UC_X86_REG_RCX,UC_X86_REG_RDX,UC_X86_REG_R8,UC_X86_REG_R9],args):u.reg_write(reg,v&0xffffffffffffffff)
 for reg,v in (xmm or {}).items():u.reg_write(reg,int.from_bytes(struct.pack('<f',v),'little'))
 emitted=[]
 if rva==0x50a150:u.mem_write(OBJ+0x28,struct.pack('<Q',sum(x['tables']['SpEffectParam'][str(i)]['stateInfo']==199 for i in ids)<<20))
 def mapped(uc,access,address,size,value,user):
  page=address&~4095;assert BASE<=page<BASE+pe.OPTIONAL_HEADER.SizeOfImage,(hex(address),hex(uc.reg_read(UC_X86_REG_RIP)-BASE))
  uc.mem_map(page,4096);uc.mem_write(page,pe.get_data(page-BASE,4096).ljust(4096,b'\0'));return True
 def hook(uc,address,size,user):
  pc=address-BASE
  def ret(value=0):
   uc.reg_write(UC_X86_REG_RAX,value);sp=uc.reg_read(UC_X86_REG_RSP);uc.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',uc.mem_read(sp,8))[0]);uc.reg_write(UC_X86_REG_RSP,sp+8)
  if address in [STOP+0x100,STOP+0x110,STOP+0x120,STOP+0x130]:
   stubs.add('synthetic player vtable and equipped weapon identity');ret({STOP+0x100:1,STOP+0x110:1000,STOP+0x120:1,STOP+0x130:0}[address])
  elif pc in [0x3d4c10,0xea9a60,0xea76f0]:
   stubs.add(hex(pc)+' player context / weapon wrapper');ret()
  elif pc==0xea7fc0:
   stubs.add('EA7FC0 actual equipped weapon PARAM lookup');id=uc.reg_read(UC_X86_REG_RDX)&0xffffffff;uc.mem_write(OBJ+0x10000,weapons[id]);uc.mem_write(uc.reg_read(UC_X86_REG_RCX),struct.pack('<IIQ',id,0,OBJ+0x10000));ret()
  elif pc==0xe6fcb0:
   stubs.add('E6FCB0 actual Behavior PARAM lookup');id=uc.reg_read(UC_X86_REG_RDX)&0xffffffff;ptr=0
   if id in behaviors:ptr=OBJ+0x11000;uc.mem_write(ptr,behaviors[id])
   uc.mem_write(uc.reg_read(UC_X86_REG_RCX)+8,struct.pack('<Q',ptr));ret()
  elif pc==0xea17e0:
   stubs.add('EA17E0 actual SpEffect PARAM lookup');id=uc.reg_read(UC_X86_REG_RDX)&0xffffffff;ptr=OBJ+0x12000;uc.mem_write(ptr,spells[id]);uc.mem_write(uc.reg_read(UC_X86_REG_RCX),struct.pack('<Qi',ptr,id));ret()
  elif pc==0x3c7fd0:
   stubs.add('3C7FD0 effect application recorder');emitted.append(uc.reg_read(UC_X86_REG_RDX)&0xffffffff);ret()
 if setup:setup(u)
 u.hook_add(UC_HOOK_MEM_UNMAPPED,mapped);u.hook_add(UC_HOOK_CODE,hook)
 u.emu_start(BASE+rva,STOP,count=200000)
 assert u.reg_read(UC_X86_REG_RIP)==STOP,hex(rva)
 return u,emitted

def scalar(u):return struct.unpack('<f',u.reg_read(UC_X86_REG_XMM0).to_bytes(16,'little')[:4])[0]
def f(u,addr):return struct.unpack('<f',u.mem_read(addr,4))[0]
def q(u,addr,v):u.mem_write(addr,struct.pack('<Q',v))
def resolver_setup(u):
 q(u,OBJ,OBJ+0x8000)
 for off,stub in [(0x320,0x100),(0x250,0x110),(0x28,0x120),(0x178,0x130)]:q(u,OBJ+0x8000+off,STOP+stub)

s=x['tables']['SpEffectParam']
for id in (7310001,7310002,7030002,7030003,7090302,7090304):
 assert struct.unpack_from('<f',spells[id],0x3ac)[0]==s[str(id)]['ultimateArtDuration']
 assert math.isclose(struct.unpack_from('<f',spells[id],0x1b4)[0],s[str(id)]['toughnessDamageCutRate'],abs_tol=1e-6)
assert struct.unpack_from('<f',assetrows[302000],0x44)[0]==assets['tables']['AssetEnvironmentGeometryParam']['302000']['lifeTime_forRuntimeCreate']==20

records={k:[] for k in ('behavior','duration','assetLifetime','timer','matching','poise','killDispatch','healing')}
for judge,expected in [(7200,700000200),(7240,700000240),(7231,700000231)]:
 u,_=execute(0x668b30,[OBJ,judge,0,0,0,0,0],setup=resolver_setup)
 actual=u.reg_read(UC_X86_REG_RAX)&0xffffffff
 assert actual==expected
 records['behavior'].append(dict(judge=judge,behavior=actual,weapon=1000))
for ids in [[],[7310000],[7310001],[7310002],[7310001,7310001],[7310002,7310001]]:
 for flags in (0,0x800c0003):
  u,_=execute(0x507ae0,[OBJ],ids,flags=flags)
  value=scalar(u);assert value==(30 if 7310001 in ids and not flags else -1)
  records['duration'].append(dict(ids=ids,flags=flags,value=value))
for override in (-1,0,30,60):
 for attached in (False,True):
  def setup(u):
   q(u,OBJ+0x48,int(attached));q(u,OBJ+8,OBJ+0x8000);u.mem_write(OBJ+0x8000,assetrows[302000]);u.mem_write(OBJ+0x168,struct.pack('<f',override))
  u,_=execute(0x6ffb60,[OBJ],setup=setup);value=scalar(u)
  assert value==((override if override>0 else 20) if attached else 0)
  records['assetLifetime'].append(dict(override=override,attached=attached,value=value))
# Constructor adds a 0.5-second visual fade; update schedules deletion only at
# the end of that fade. This is separate from the field's 20/30-second hit window.
fade=struct.unpack('<f',pe.get_data(0x32f3688,4))[0];assert fade==.5
for life in (20,30):
 u,_=execute(0x7238a0,[OBJ,OBJ+0x8000],xmm={UC_X86_REG_XMM2:life,UC_X86_REG_XMM3:fade})
 assert f(u,OBJ+0x10)==fade and f(u,OBJ+0x20)==life+fade
 for dt in (0,life,life+.25,life+.5,life+1):
  def setup(u):
   q(u,OBJ,OBJ+0x8000);u.mem_write(OBJ+0x10,struct.pack('<f',fade));u.mem_write(OBJ+0x20,struct.pack('<f',life+fade))
   u.mem_write(OBJ+0x408,struct.pack('<f',dt));q(u,OBJ+0x8060,1)
   # Already enqueued owner: preserve the actual deletion flags, omit manager allocation.
   u.mem_write(OBJ+0x8278,struct.pack('<I',0x1000));u.mem_write(OBJ+0x82fc,struct.pack('<f',1))
  u,_=execute(0x723960,[OBJ,OBJ+0x400],setup=setup)
  remaining=f(u,OBJ+0x20);opacity=f(u,OBJ+0x82fc);deleted=bool(struct.unpack('<I',u.mem_read(OBJ+0x8278,4))[0]&1)
  assert remaining==life+fade-dt and deleted==(dt>=life+fade)
  assert opacity==min(1,max(0,remaining/fade))
  records['timer'].append(dict(life=life,fade=fade,dt=dt,remaining=remaining,opacity=opacity,deleted=deleted))
for family,ids in [('duration',[7310001,7310002]),('attack',[704100,7310003]),('poise',[7030002,7030003]),('healing',[7090301,7090302,7090304])]:
 for existing in ids:
  for incoming in ids:
   r=s[str(incoming)];category=int(r['spCategory']);priority=int(r['categoryPriority'])
   u,_=execute(0x511450,[OBJ+0x1000,category,priority,incoming],[existing]);match=bool(u.reg_read(UC_X86_REG_RAX)&255);assert match
   u,_=execute(0x511700,[OBJ+0x1000,incoming,0,0],[existing],xmm={UC_X86_REG_XMM2:1})
   pointer,active=struct.unpack('<Qi',u.mem_read(OBJ+0x1000,12));duration=f(u,OBJ+0x104c)
   assert active==incoming and math.isclose(duration,r['effectEndurance'],abs_tol=1e-6)
   assert bytes(u.mem_read(pointer,0x400))==spells[incoming]
   records['matching'].append(dict(family=family,existing=existing,incoming=incoming,category=category,priority=priority,active=active,duration=duration))
for ids in [[],[7030000],[7030002],[7030003]]:
 for flags in (0,0x800c0003):
  u,_=execute(0x502270,[OBJ,0],ids,flags=flags);value=scalar(u)
  assert math.isclose(value,.1 if not flags and any(i in (7030002,7030003) for i in ids) else 1,abs_tol=1e-6)
  records['poise'].append(dict(ids=ids,flags=flags,value=value))
for id in (7090301,7090302,7090304):
 for special in (0,1):
  for flags in (0,0x800c0003):
   _,emitted=execute(0x50a150,[OBJ,OBJ+0x500,special],[id],flags=flags)
   field='applyIdOnKillSp' if special else 'applyIdOnGetSoul'
   assert emitted==([] if flags else [s[str(id)][field]])
   records['killDispatch'].append(dict(id=id,special=special,flags=flags,emitted=emitted))
for id in (7090303,7090305,7090306,7090307):
 for flags in (0,4,0x800c0003):
  def setup(u):u.mem_write(OBJ+0x1058,struct.pack('<4f',1,1,1,1))
  u,_=execute(0x50b860,[OBJ]+[OBJ+0x800+i*0x20 for i in range(11)]+[0],[id],flags=flags,setup=setup)
  rate,points=struct.unpack('<2f',u.mem_read(OBJ+0x880,8))
  assert rate==(s[str(id)]['changeHpRate'] if flags==4 else 0) and points==0
  records['healing'].append(dict(id=id,flags=flags,hpChangePercent=rate,hpChangePoints=points))

animation=next(a for b in tae['bundles'] for t in b['taes'] if t['ID']==2904 for a in t['animations'] if a['ID']==640000)
events=[e for e in animation['events'] if e['index'] in (26,27,28)]
assert [e['Type'] for e in events]==[2,67,2]
assert struct.unpack_from('<i',bytes.fromhex(events[1]['hex']))[0]==7310002
assert [(struct.unpack_from('<i',bytes.fromhex(e['hex']),8)[0],struct.unpack_from('<h',bytes.fromhex(e['hex']),14)[0]) for e in (events[0],events[2])]==[(7200,2256),(7240,2113)]
chains=[]
for behavior,first,leaves in [(700000200,30904000,[704100,7030002,7090302]),(700000240,30904200,[7310003,7030003,7090304])]:
 b=x['tables']['BehaviorParam_PC'][str(behavior)];assert b['refType']==1 and b['refId']==first
 chain=[]
 for id in range(first,first+5):
  row=x['tables']['Bullet'][str(id)]
  assert row['HitBulletID']==(id+1 if id<first+4 else -1)
  chain.append(dict(id=id,**{k:row[k] for k in ('HitBulletID','assetNo_Hit','life','hitRadius','dmgHitRecordLifeTime','isEndlessHit','atkId_Bullet','spEffectId0','spEffectId1','spEffectId2')}))
 assert chain[2]['assetNo_Hit']==302000
 assert [chain[-1]['spEffectId'+str(i)] for i in range(3)]==leaves
 assert chain[-1]['atkId_Bullet']==700000205 and chain[-1]['hitRadius']==12
 chains.append(dict(behavior=behavior,bullets=chain))
atk=x['tables']['AtkParam_Pc']['700000205'];assert [atk[k] for k in ('selfTarget','friendlyTarget','opposeTarget','disableHitSpEffect')]==[1,1,0,0]
used=[7310000,7310001,7310002,7310003,704100,7030000,7030002,7030003,7090300,7090301,7090302,7090303,7090304,7090305,7090306,7090307]
fields=['stateInfo','spCategory','categoryPriority','effectEndurance','motionInterval','cycleOccurrenceSpEffectId','ultimateArtDuration','physicsAttackRate','magicAttackRate','fireAttackRate','thunderAttackRate','darkAttackRate','toughnessDamageCutRate','changeHpRate','changeHpPoint','applyIdOnKillSp','applyIdOnGetSoul','invocationConditionsStateChange1','isContractSpEffectLife']
out=dict(schema=1,exeSha256=sha(exe),regulationSha256=x['hashes']['regulation.bin'],gameplayVerified=False,
 assets={b['path']:b['sha256'] for b in tae['bundles']},asset=dict(id=302000,defaultLifetime=20,fade=fade),
 animation=dict(tae=2904,id=640000,events=events),chains=chains,
 attack=dict(id=700000205,**{k:atk[k] for k in ('selfTarget','friendlyTarget','opposeTarget','disableHitSpEffect')}),
 spells={str(i):{k:s[str(i)][k] for k in fields} for i in used},checks=records,fixtures=sorted(stubs))
a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print({k:len(v) for k,v in records.items()})
