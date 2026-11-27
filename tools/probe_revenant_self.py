"""Trace family-dependent Revenant self buffs through native eligibility and consumers.

Family controller states, actor identity and inventory handles are explicit
inputs. Native selection, bridge upkeep, family-slot gating, timers, HP packets,
attack and incoming-damage consumers run unchanged. This is not live gameplay.
"""
import argparse,itertools,json,math,re,struct
from pathlib import Path
from native_effect_runtime import BASE,OBJ,STOP,Chain,Inputs,sha
from native_ailment_runtime import Ailment
from unicorn.x86_const import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','npc','texts','output'):p.add_argument(name,type=Path)
args=p.parse_args();x=Inputs(args.exe,args.extracted);inputs=x;ts=x.x['tables']
raws={name:args.extracted.with_suffix('.'+name+'.param').read_bytes() for name in ('AttachEffectParam','AtkParam_Pc')}
hashes={'AttachEffectParam':'ae8128ed510a532d0fa7cb56fa9c86e4a44c9d815dd4ee01c05821d5f50a9827','AtkParam_Pc':'1ec1893420053cbfb06e3efb269ade4ba9d6a617d1d3dbb370e837847be05676'}
for name,raw in raws.items():assert sha(raw)==hashes[name]
assert sha(x.param)=='07ec636c5565d4551efeb53e6f08bc633b2aa4f2129f13c61b0638d69b1bc176'
rows=Inputs.table(raws['AttachEffectParam'],0x44);attacks=Inputs.table(raws['AtkParam_Pc'],0x1d0)
for table,raw in ((rows,raws['AttachEffectParam']),(attacks,raws['AtkParam_Pc'])):assert len(table)==struct.unpack_from('<H',raw,10)[0]
assert ts['AttachEffectParam']['7220000']['passiveSpEffectId_1']==9200003
for id,cycle,replace,duration,period in [(9200003,9200004,-1,-1,.2),(9200004,7220000,9200005,.11,.1),(9200005,7220002,7220001,.06,.05)]:
 r=x.spells[str(id)];assert (r['cycleOccurrenceSpEffectId'],r['replaceSpEffectId'],r['spCategory'])==(cycle,replace,20)
 assert math.isclose(r['effectEndurance'],duration,abs_tol=1e-7) and math.isclose(r['motionInterval'],period,abs_tol=1e-7)
for id in (7220000,7220001,7220002):
 r=x.spells[str(id)];assert (r['stateInfo'],r['spCategory'],r['effectEndurance'])==(2107+id-7220000,20,3)
assert (x.spells['7220000']['changeHpPoint'],x.spells['7220000']['changeHpRate'],x.spells['7220000']['motionInterval'])==(-1,0,1)
assert all(math.isclose(x.spells['7220001'][k+'AttackRate'],1.1,abs_tol=1e-6) for k in ('physics','magic','fire','thunder','dark'))
assert x.spells['7220002']['neutralDamageCutRate']==1 and all(math.isclose(x.spells['7220002'][k+'DamageCutRate'],.8,abs_tol=1e-6) for k in ('magic','fire','thunder','dark'))
# Names come from current raw Buddy/Npc row names and the matching menu FMG.
npc=json.loads(args.npc.read_text());texts=json.loads(args.texts.read_text())
assert npc['hashes']['regulation.bin']==x.x['hashes']['regulation.bin']
for lang in ('engus','zhocn'):
 assert texts['hashes'][lang+'/menu']==x.x['hashes']['msg/'+lang+'/menu_dlc01.msgbnd.dcx']
npc_hashes={};raw_names={};buddy_offsets={}
for table,expected in [('NpcParam','4bfda3f7f3588fc1b3fd5508adcff8dc35537f786bb1dcbc044218eb476c20bf'),('BuddyParam','4a90b27fb0ea1df1d858d754a08e768fa7937ee6dd322705dcf008d6ad905a81')]:
 raw=args.npc.with_suffix('.'+table+'.param').read_bytes();assert sha(raw)==expected;npc_hashes[table]=sha(raw)
 entries={struct.unpack_from('<i',raw,0x40+i*24)[0]:struct.unpack_from('<QQ',raw,0x48+i*24) for i in range(struct.unpack_from('<H',raw,10)[0])}
 raw_names[table]={}
 targets=(137030000,143400000,149610000) if table=='NpcParam' else (27000000,27100000,27200000)
 for id in targets:
  off,start=entries[id];end=start;assert start
  while raw[end:end+2]!=b'\0\0':end+=2;assert end<len(raw)
  raw_names[table][id]=raw[start:end].decode('utf-16-le')
  if table=='BuddyParam':buddy_offsets[id]=struct.unpack_from('<5i',raw,off+4)
families=[]
for slot,buddy_id,npc_id,en,cn,text_id in [(0,27000000,137030000,'Helen','海伦',332002),(1,27100000,143400000,'Frederick','弗雷德利克',332001),(2,27200000,149610000,'Sebastian','塞巴斯蒂安',332003)]:
 assert en in raw_names['NpcParam'][npc_id] and en in raw_names['BuddyParam'][buddy_id]
 assert buddy_offsets[buddy_id][1]==npc_id and buddy_offsets[buddy_id][0]==270000+slot*1000
 for lang,name in [('engus',en),('zhocn',cn)]:
  label=texts['all'][lang]['CL_MenuText.fmg'][str(text_id)]
  assert re.sub(r'<\?keyicon@\d+\?>','',label)==name
 families.append(dict(slot=slot,buddy=buddy_id,npc=npc_id,leaf=7220000+slot,state=2107+slot,name=cn,englishName=en,menuTextId=text_id))
all_checks={}
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
   if id in rows and id not in self.cache:
    self.cache[id]=OBJ+0x10000+len(self.cache)*0x100;u.mem_write(self.cache[id],rows[id])
   self.q(ptr,self.cache.get(id,0));u.mem_write(ptr+8,struct.pack('<I',id));ret(ptr)
  else:super().hook(u,address,size,user)
 def select(self):
  self.invoke(0x4fea30,[MAN,OUT]);bits=int.from_bytes(self.u.mem_read(BITS,20),'little');return [i for i in range(144) if bits>>i&1]

class Actor(Ailment):
 def __init__(self,kind=0,maximum=500):
  # Reuse the actor setup; explicitly initialize every channel, including the
  # five channels outside the shared helper's original poison/bleed probes.
  super().__init__(x,0,maximum);self.kind=kind;self.grants=[]
  for i in range(7):
   for off in (0x9010,0x902c):self.u.mem_write(OBJ+off+i*4,struct.pack('<i',maximum))
  self.q(OBJ+0x6210,STOP+0x300);self.q(OBJ+0x6790,STOP+0x301)
  for off in (0x118,0x120,0x130,0x150):self.q(OBJ+0x6200+off,STOP+0x302)
  self.q(OBJ+0xf020,OBJ+0x9000)
  self.globalq(0x3c84d4+7+0x384b2c5,OBJ+0x18300)
  self.stubs.add('explicit player identity, actor virtual +590 type 0 and +118/+120/+130/+150 false')
  self.stubs.add('native self-grant mode 7 and local actor; network singleton present with no peer')
  self.stubs.add('3D3390 false special owner predicate; 51B920/6AF640 notification sinks; EA0CA0 absent notification mapping')
  self.stubs.add('2167950/21674E0/2167A40 monotonic notification timestamp fixture')
  self.globalq(0x3c21ec8,OBJ+0x18000);self.u.mem_write(OBJ+0x18010,struct.pack('<i',7))
  self.u.mem_map(OBJ+0x40000,0x20000);self.globalq(0x3c0f0a8,OBJ+0x40000);self.q(OBJ+0x574e8,OBJ+0x6000)
 def globalq(self,rva,value):
  try:self.u.mem_read(BASE+rva,8)
  except:self.mapped(self.u,0,BASE+rva,8,0,None)
  self.q(BASE+rva,value)
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v&0xffffffffffffffff);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if address in (STOP+0x300,STOP+0x301,STOP+0x302):ret({STOP+0x300:1,STOP+0x301:OBJ+0x18100,STOP+0x302:0}[address])
  elif pc==0x3c7fd0:self.grants.append(u.reg_read(UC_X86_REG_RDX)&0xffffffff)  # observe; execute original grant
  elif pc in(0x3d3390,0x732800,0x51b920,0x6af640):ret()
  elif pc in(0x2167950,0x21674e0,0x2167a40):
   self.q(OBJ+0x18200,100);ret(OBJ+0x18200 if pc==0x2167950 else 1 if pc==0x2167a40 else 0)
  elif pc==0xea0ca0:ret(-1)
  else:super().hook(u,address,size,user)
 def grant(self,id):self.invoke(0x3c7fd0,[OBJ+0x6000,id,1])
 def damage(self,value=100,excluded=0):self.invoke(0x504d30,[OBJ,0,0,0,excluded],{UC_X86_REG_XMM1:value})

class Attack(Actor):
 def hook(self,u,address,size,user):
  if address-BASE==0xe6d630:
   id=u.reg_read(UC_X86_REG_R8)&0xffffffff;assert u.reg_read(UC_X86_REG_RDX)==1
   wrapper=u.reg_read(UC_X86_REG_RCX);u.mem_write(OBJ+0xa800,attacks[id]);u.mem_write(wrapper,struct.pack('<iii4xQ',id,0,1,OBJ+0xa800))
   sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8);return
  super().hook(u,address,size,user)
def attack(c,weapon,attached,kind):
 out=OBJ+0x8400;c.u.mem_write(out,bytes(0x300));c.u.mem_write(out+8,struct.pack('<iiB',2,1,kind))
 c.u.mem_write(OBJ+0xa800,attacks[2]);c.q(OBJ+0xb010,OBJ+0xa800);c.invoke(0xe6d530,[OBJ+0xb000,out+0x14])
 c.u.mem_write(out+0xe8,struct.pack('<i',weapon));c.invoke(0x502830,[OBJ,out,weapon,attached])
 return dict(points=[struct.unpack('<f',c.u.mem_read(out+off,4))[0] for off in (0x48,0x5c,0x60,0x64,0x68)])

C=OBJ+0x60000;CONTROL=C+0x1000
class Family(Attack):
 def __init__(self,states):
  super().__init__();self.u.mem_map(C,0x10000);self.q(OBJ+0xf000,OBJ+0xe000);self.q(OBJ+0xf160,C);self.q(C+0x10,CONTROL)
  for i,state in enumerate(states):self.u.mem_write(CONTROL+0x18+i*0x60,bytes([state]))
 def qualify(self):self.invoke(0x5057d0,[OBJ,0,OBJ+0x6000],{UC_X86_REG_XMM1:1})
 def rates(self):
  attack(self,1000500,-1,0);return [struct.unpack('<f',self.u.mem_read(OBJ+0x8400+off,4))[0] for off in (0x90,0xa4,0xa8,0xac,0xb0)]
checks=[]
for slot,state,copies in itertools.product(range(3),(0,1,9,10,11,12,19,20,21,22),(1,3)):
 states=[0]*3;states[slot]=state;c=Family(states)
 for _ in range(copies):c.grant(9200003)
 heals=[]
 for frame in range(1,181):
  c.qualify();c.update(1/60);hp=c.hp_packet(1000)[0]
  if hp:heals.append((frame,hp))
 enabled=[n['id'] for n in c.nodes() if n['id'] in (7220000,7220001,7220002) and not n['flags']&0x800c0003]
 wanted=[7220000+slot] if state in (10,11,20,21) else []
 assert enabled==wanted,(slot,state,copies,enabled,wanted)
 rates=c.rates();expected=1.1 if slot==1 and state in (10,11,20,21) else 1
 assert all(math.isclose(v,expected,abs_tol=1e-6) for v in rates),(slot,state,rates)
 assert bool(heals)==(slot==0 and state in (10,11,20,21)),(slot,state,heals)
 checks.append(dict(slot=slot,state=state,copies=copies,enabled=enabled,heals=heals,rates=rates))

all_checks['controller']=checks
print('controller',len(checks),flush=True)

class Buffs(Family):
 def defense(self):
  self.u.mem_write(OBJ+0x800,bytes(0x200));self.invoke(0x503800,[OBJ,OBJ+0x500,OBJ+0x520,OBJ+0x540,OBJ+0x800])
  return list(struct.unpack('<5f',self.u.mem_read(OBJ+0x500,20)))
 def states(self,values):
  for i,value in enumerate(values):self.u.mem_write(CONTROL+0x18+i*0x60,bytes([value]))
checks=[]
for mask,copies,fps in itertools.product(range(8),(1,3),(30,60,120)):
 c=Buffs([10 if mask>>i&1 else 0 for i in range(3)])
 for _ in range(copies):c.grant(9200003)
 heals=[]
 for frame in range(1,fps//2+1):
  c.qualify();c.update(1/fps);v=c.hp_packet(1000)[0]
  if v:heals.append((frame,v))
 enabled=sorted(n['id'] for n in c.nodes() if 7220000<=n['id']<=7220002 and not n['flags']&0x800c0003)
 assert enabled==[7220000+i for i in range(3) if mask>>i&1]
 attack_rates=c.rates();defense=c.defense();expectAttack=1.1 if mask&2 else 1
 assert all(math.isclose(v,expectAttack,abs_tol=1e-6) for v in attack_rates)
 expected=[1]+[.8 if mask&4 else 1]*4
 assert all(math.isclose(v,e,abs_tol=1e-6) for v,e in zip(defense,expected)),(mask,defense)
 assert sum(v for _,v in heals)==(1 if mask&1 else 0)
 checks.append(dict(mask=mask,copies=copies,fps=fps,enabled=enabled,attack=attack_rates,defense=defense,heals=heals))

all_checks['combinations']=checks

checks=[]
for scenario,copies,fps in itertools.product(('withdraw-return','rotate','remove-root'),(1,3),(30,60,120)):
 c=Buffs([10,10,10]);heals=[];samples=[]
 for _ in range(copies):c.grant(9200003)
 for frame in range(1,8*fps+1):
  time=(frame-1)/fps
  if scenario=='withdraw-return':states=[10]*3 if time<2 else [0]*3 if time<4 else [20]*3
  elif scenario=='rotate':states=[10 if i==min(int(time//2),2) else 0 for i in range(3)]
  else:states=[10]*3
  if scenario=='remove-root' and frame==2*fps+1:c.invoke(0x504e80,[OBJ,9200003])
  c.states(states);c.qualify();c.update(1/fps);hp=c.hp_packet(1000)[0]
  if hp:heals.append((frame,hp))
  if frame in (fps,2*fps,2*fps+1,3*fps,4*fps,4*fps+1,5*fps,6*fps,8*fps):
   samples.append(dict(frame=frame,states=states,nodes=c.nodes(),attack=c.rates(),defense=c.defense()))
 checks.append(dict(scenario=scenario,copies=copies,fps=fps,heals=heals,samples=samples))

for r in checks:
 fps=r['fps'];scenario=r['scenario']
 for sample in r['samples']:
  enabled=[n['id'] for n in sample['nodes'] if 7220000<=n['id']<=7220002 and not n['flags']&0x800c0003]
  if scenario=='remove-root':
   if sample['frame']>=6*fps:assert not enabled
   if sample['frame']<=4*fps:assert sorted(enabled)==[7220000,7220001,7220002]
  else:assert sorted(enabled)==[7220000+i for i,v in enumerate(sample['states']) if v in (10,11,20,21)]
  assert all(math.isclose(v,1.1 if 7220001 in enabled else 1,abs_tol=1e-6) for v in sample['attack'])
  assert all(math.isclose(v,.8 if i and 7220002 in enabled else 1,abs_tol=1e-6) for i,v in enumerate(sample['defense']))
 assert all(v==1 for _,v in r['heals'])
 if scenario=='withdraw-return':
  assert not any(2*fps<frame<=4*fps for frame,_ in r['heals'])
  active_frames=[frame-(2*fps if frame>4*fps else 0) for frame,_ in r['heals']]
  assert all(abs((b-a)-fps)<=1 for a,b in zip(active_frames,active_frames[1:])),r
 if scenario=='rotate':assert all(frame<=2*fps for frame,_ in r['heals'])
for scenario,fps in itertools.product(('withdraw-return','rotate','remove-root'),(30,60,120)):
 pair=[r for r in checks if r['scenario']==scenario and r['fps']==fps];assert len(pair)==2 and pair[0]['heals']==pair[1]['heals']
all_checks['timing']=checks
print('timing',len(checks),flush=True)

checks={k:[] for k in ('selection','hpAmounts','mixed','disabled','extension')}
for hero,copies in itertools.product(range(11),(0,1,3)):
 c=Selection([[7220000]]*copies,hero);chosen=c.select();roots=[9200003 for i in range(copies) if i*6 in chosen]
 assert len(roots)==(copies if hero in (0,6) else 0),(hero,copies,chosen)
 checks['selection'].append(dict(hero=hero,copies=copies,chosen=chosen,roots=roots))
for maximum,copies in itertools.product((1,100,1000,2345),(1,3)):
 c=Buffs([10,0,0])
 for _ in range(copies):c.grant(9200003)
 packets=[]
 for frame in range(1,121):
  c.qualify();c.update(1/60);hp=c.hp_packet(maximum)[0]
  if hp:packets.append((frame,hp))
 assert packets and all(hp==1 for _,hp in packets)
 checks['hpAmounts'].append(dict(maximum=maximum,copies=copies,packets=packets))
for copies,extra in itertools.product((0,1,3),(0,1,3)):
 c=Buffs([10,10,10]);counts={}
 for _ in range(copies):c.grant(9200003)
 for _ in range(extra):c.grant(7001100)
 for frame in range(1,121):
  c.qualify();c.update(1/60);hp=c.hp_packet(1000)[0]
  if hp:counts[frame]=hp
 assert sum(counts.values())==2*(bool(copies)+2*extra),(copies,extra,counts)
 checks['mixed'].append(dict(copies=copies,extra=extra,packets=counts,total=sum(counts.values())))
for leaf,mask in itertools.product((7220000,7220001,7220002),(1,2,0x40000,0x80000000)):
 c=Buffs([10,10,10]);c.grant(leaf);c.qualify();c.update(0);ptr=struct.unpack('<Q',c.u.mem_read(OBJ+8,8))[0]
 assert struct.unpack('<i',c.u.mem_read(ptr+8,4))[0]==leaf
 flags=struct.unpack('<I',c.u.mem_read(ptr+0x68,4))[0];c.u.mem_write(ptr+0x68,struct.pack('<I',flags|mask))
 hp=c.hp_packet(1000)[0];rates=c.rates();defense=c.defense();assert hp==0 and rates==defense==[1.]*5
 checks['disabled'].append(dict(leaf=leaf,mask=mask,hp=hp,rates=rates,defense=defense))
for extension in (None,7006400,8330500):
 c=Buffs([10]*3)
 if extension:c.grant(extension)
 for leaf in (7220000,7220001,7220002):c.grant(leaf)
 c.qualify();c.update(1)
 nodes=[n for n in c.nodes() if 7220000<=n['id']<=7220002];assert all(n['lifetime']==2 for n in nodes),nodes
 checks['extension'].append(dict(extension=extension,nodes=nodes))

all_checks.update(checks)

class AttackRows(Buffs):
 def row(self,id,kind=0):
  out=OBJ+0x8400;self.u.mem_write(out,bytes(0x300));self.u.mem_write(out+8,struct.pack('<iiB',id,1,kind))
  self.u.mem_write(OBJ+0xa800,attacks[id]);self.q(OBJ+0xb010,OBJ+0xa800);self.invoke(0xe6d530,[OBJ+0xb000,out+0x14])
  self.invoke(0x502830,[OBJ,out,-1,-1]);return [struct.unpack('<f',self.u.mem_read(out+off,4))[0] for off in (0x90,0xa4,0xa8,0xac,0xb0)]
representatives={}
for id,r in ts['AtkParam_Pc'].items():representatives.setdefault(tuple(sorted({r['subCategory'+str(i)] for i in range(1,6)}-{0})),int(id))
checks={k:[] for k in ('tags','kinds')}
for copies in (0,1,3):
 c=AttackRows([0,10,0])
 for _ in range(copies):c.grant(9200003)
 for _ in range(30):c.qualify();c.update(1/60)
 for tags,id in representatives.items():
  rates=c.row(id);assert all(math.isclose(v,1.1 if copies else 1,abs_tol=1e-6) for v in rates),(id,rates)
  checks['tags'].append(dict(copies=copies,id=id,tags=tags,rates=rates))
 for kind in range(13):
  rates=c.row(2,kind);checks['kinds'].append(dict(copies=copies,kind=kind,rates=rates))

for r in checks['kinds']:assert all(math.isclose(v,1.1 if r['copies'] and r['kind']!=5 else 1,abs_tol=1e-6) for v in r['rates'])
all_checks.update(checks)
counts={k:len(v) for k,v in all_checks.items()}
assert counts==dict(controller=60,combinations=48,timing=18,selection=33,hpAmounts=8,mixed=9,disabled=12,extension=3,tags=648,kinds=39)
args.output.write_text(json.dumps(dict(schema=1,effect=7220000,root=9200003,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),paramHashes=hashes,npcHashes=npc_hashes,textHashes=texts['hashes'],families=families,acceptedStates=[10,11,20,21],checks=all_checks,
 native=dict(selection='4FEA30 → E6E150 → E6E3B0',eligibility='5057D0 → 50F740 → EA1AA0 → 460AC0 → 3864C0',grant='3C7FD0 → 3C80A0 → 3DB410',upkeep='50D060 → 5057D0 → 50ACD0',hp='506EC0',attack='E6D530 → 502830',incoming='503800'),
 stubs=sorted(c.stubs|{'Inventory slots, handles, hero IDs and actual AttachEffect/AtkParam data lookup are fixtures; native selection and consumers execute.',
 'Actor passed to qualifier has real three-slot controller layout with supplied states. Native family-index mapping and accepted-state predicate execute; scene spawning, AI state transitions and multiplayer are not simulated.',
 'Explicit full HP ratio, neutral stamina data and current-weapon context. Resource packets are read before final HP clamping/writing.',
 'Controller state changes and direct root removal are explicit test inputs, not complete inventory rebuild, death or reload workflows.'}),gameplayVerified=False),ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(counts.values()),counts)
