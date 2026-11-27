"""Resolve attack bonuses conditioned on the current recipient's ailments.

Runs actual equipment selection, effect lists, target predicate, hit-callsite
block and multiplier consumer. Runtime attack packets have explicit source
inputs and native PARAM-derived tags; a raw AtkParam row is NOT a hit packet.
Full collision, ailment buildup/onset and final damage are outside this probe.
"""
import argparse,itertools,json,math,struct
from pathlib import Path
from native_effect_runtime import BASE,OBJ,STACK,STOP,Chain,Inputs,sha
from unicorn.x86_const import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted)
raw=a.extracted.with_suffix('.AttachEffectParam.param').read_bytes();rows=Inputs.table(raw,0x44)
atkraw=a.extracted.with_suffix('.AtkParam_Pc.param').read_bytes();atkrows=Inputs.table(atkraw,0x1d0)
assert sha(atkraw)=='1ec1893420053cbfb06e3efb269ade4ba9d6a617d1d3dbb370e837847be05676'
families=[]
ids=[(6260000,7260001),(6260001,7260002),(6260002,7260003),(6260300,7260301),(6260301,7260302),
     (6260400,7260401),(6260401,7260402),(6260402,7260403),(7260000,7260000),(7260300,7260300),(7260400,7260400)]
fields=('physicsAttackRate','magicAttackRate','fireAttackRate','thunderAttackRate','darkAttackRate')
base=x.spells['7260000']
for id,root in ids:
 attach=x.x['tables']['AttachEffectParam'][str(id)];r=x.spells[str(root)]
 assert attach['passiveSpEffectId_1']==root and attach['exclusivityId']==-1
 assert all(attach[k]==-1 for k in ('passiveSpEffectId_2','passiveSpEffectId_3','permanentSpEffectId'))
 assert (r['stateInfo'],r['spCategory'],r['effectEndurance'])==(2110,0,-1)
 assert r['cycleOccurrenceSpEffectId']==r['replaceSpEffectId']==-1
 assert all(r['invocationConditionsStateChange'+str(i)]==0 for i in (1,2,3))
 assert {k for k in base if r[k]!=base[k]}<=set(fields)|{'enemyStateInfoTrigger'}
 state=r['enemyStateInfoTrigger'];assert state in (2,5,260)
 rate=(1.1,1.16,1.2,1.2)[root%100]
 assert all(math.isclose(r[k],rate,rel_tol=1e-6) for k in fields)
 families.append(dict(effect=id,root=root,state=state,rate=r[fields[0]],tier=root%100))
rootmap={f['root']:f for f in families};roots=list(rootmap)
status_rows=[dict(id=id,state=state,duration=duration) for id,state,duration in ((8110000,2,40),(8110400,5,40),(107504,260,30))]
for f in status_rows:
 r=x.spells[str(f['id'])];assert r['stateInfo']==f['state'] and r['effectEndurance']==f['duration']
 assert r['cycleOccurrenceSpEffectId']==r['replaceSpEffectId']==-1
status_sets=[[f['id'] for i,f in enumerate(status_rows) if mask>>i&1] for mask in range(8)]
statusmap={f['id']:f['state'] for f in status_rows}
# Every currently extracted AtkParam tag combination has a representative.
tag_rows={}
for id,r in x.x['tables']['AtkParam_Pc'].items():
 tags=tuple(sorted({r['subCategory'+str(i)] for i in range(1,6)}-{0}))
 assert all(0<tag<256 for tag in tags)
 tag_rows.setdefault(tags,int(id))
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

TARGET,PACKET,WRAPPER,ACTOR,OUT,EMPTY=OBJ+0x18000,OBJ+0x19000,OBJ+0x1a000,OBJ+0x1a100,OBJ+0x1b000,OBJ+0x1c000
class Values(Chain):
 def __init__(self):
  super().__init__(x)
  self.q(OBJ+0x6190,OBJ);self.q(TARGET+0x10,ACTOR);self.q(ACTOR,OBJ+0x6200)
  self.q(ACTOR+0x190,TARGET);self.q(WRAPPER+8,ACTOR);self.q(EMPTY+0x10,ACTOR)
  self.stubs.add('separate attacker and target effect containers; explicit receiver context and actor vtables')
 def hook(self,u,address,size,user):
  if address-BASE==0x43a605:u.reg_write(UC_X86_REG_RIP,STOP)
  elif address-BASE==0x26909a0:
   self.stubs.add('26909A0 security-cookie return preserves result')
   sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  else:super().hook(u,address,size,user)
 def insert_at(self,container,id):return self.invoke(0x50d060,[container,id,OBJ+0xa00,-1,0,0x3f800000,0,0,16])&0xffffffff
 def tick(self,container=TARGET,dt=0):
  self.invoke(0x5057d0,[container,0,0],{UC_X86_REG_XMM1:1})
  self.invoke(0x50acd0,[container,0,0],{UC_X86_REG_XMM1:dt})
 def setup(self,equipped,statuses):
  for root in equipped:self.insert(root)
  for id in statuses:self.insert_at(TARGET,id)
  self.tick(OBJ);self.tick()
  assert [n['id'] for n in self.nodes()]==list(dict.fromkeys(equipped))
  self.packet(10000)
 def packet(self,id,kind=0,critical=False,flag=False):
  self.u.mem_write(PACKET,bytes(0x300));self.u.mem_write(OBJ+0xa800,atkrows[id]);self.q(OBJ+0xb010,OBJ+0xa800)
  self.invoke(0xe6d530,[OBJ+0xb000,PACKET+0x124])
  tags={x.x['tables']['AtkParam_Pc'][str(id)]['subCategory'+str(i)] for i in range(1,6)}-{0}
  assert int.from_bytes(self.u.mem_read(PACKET+0x124,32),'little')==sum(1<<tag for tag in tags)
  self.u.mem_write(PACKET+0x40,struct.pack('<iii',id,1,0))
  self.u.mem_write(PACKET+0x121,bytes([2 if critical else 0,kind]))
  self.u.mem_write(PACKET+0x161,bytes([32 if flag else 0]))
  for offset in (0xf8,0x190):self.u.mem_write(PACKET+offset,struct.pack('<i',-1))
  # Compare the actual input conversion with each explicit field, rather than
  # pretending the compact 0x1D0 PARAM layout is the 0x300 runtime packet.
  flt=OBJ+0x1b100;self.invoke(0x50f230,[flt,PACKET])
  assert self.u.mem_read(flt,1)[0]==kind
  assert bytes(self.u.mem_read(flt+4,32))==bytes(self.u.mem_read(PACKET+0x124,32))
  assert self.u.mem_read(flt+0x24,2)==bytes([int(critical),int(flag)])
  assert struct.unpack('<4i',self.u.mem_read(flt+0x28,16))==(0,-1,-1,id)
  assert struct.unpack('<i',self.u.mem_read(flt+0x38,4))[0]==1
 def value(self,caller=True,base=(1,1,1,1,1),target=TARGET,attacker=True):
  self.u.mem_write(OUT+0x18,struct.pack('<5f',*base))
  if caller:
   self.q(ACTOR+0x190,target)
   for reg,v in ((UC_X86_REG_R12,OBJ+0x6000 if attacker else 0),(UC_X86_REG_R15,WRAPPER),(UC_X86_REG_R14,PACKET),(UC_X86_REG_RBP,OUT)):self.u.reg_write(reg,v)
   self.invoke(0x43a5e1,[])
  else:self.invoke(0x5025e0,[OBJ,OUT+0x18,target,PACKET])
  return list(struct.unpack('<5f',self.u.mem_read(OUT+0x18,20)))
 def disable(self,container):
  ptr=struct.unpack('<Q',self.u.mem_read(container+8,8))[0]
  while ptr:
   self.u.mem_write(ptr+0x68,struct.pack('<I',0x800c0003));ptr=struct.unpack('<Q',self.u.mem_read(ptr+0x38,8))[0]
 def target_nodes(self):
  ptr=struct.unpack('<Q',self.u.mem_read(TARGET+8,8))[0];out=[]
  while ptr:
   out.append(dict(id=struct.unpack('<i',self.u.mem_read(ptr+8,4))[0],life=struct.unpack('<f',self.u.mem_read(ptr+0x4c,4))[0],flags=struct.unpack('<I',self.u.mem_read(ptr+0x68,4))[0]))
   ptr=struct.unpack('<Q',self.u.mem_read(ptr+0x38,8))[0]
  return out

def expected(equipped,statuses):
 states={statusmap[id] for id in statuses}
 return math.prod(rootmap[root]['rate'] for root in dict.fromkeys(equipped) if rootmap[root]['state'] in states)
def verify(actual,rate,base=(1,1,1,1,1)):
 assert all(math.isclose(v,b*rate,rel_tol=1e-6,abs_tol=1e-7) for v,b in zip(actual,base)),(actual,rate,base)
checks={k:[] for k in ('selection','repeat','mixed','context','tags','disabled','retarget','lifetime','caller','baseline')};stubs=set()
def record(group,c,**row):checks[group].append(row);stubs.update(c.stubs)
for f,copies,hero in itertools.product(families,(1,2,3,6),range(11)):
 c=Selection([[f['effect']]]*copies,hero);bits=c.select();selected=[]
 for index in range(copies):
  assert index*6 in bits
  id=struct.unpack('<i',c.u.mem_read(OBJ+0xa000+index*0x80+0x18,4))[0];assert id==f['effect']
  c.invoke(0xe6e150,[OBJ+0x9200,id]);selected.append(c.invoke(0xe6e3b0,[OBJ+0x9200,0])&0xffffffff)
 assert selected==[f['root']]*copies
 v=Values();v.setup(selected,[]);assert len(v.nodes())==1
 record('selection',c,effect=f['effect'],copies=copies,hero=hero,selected=selected,activeRootCount=len(v.nodes()));stubs.update(v.stubs)
print('PASS selection',len(checks['selection']),flush=True)
for f,copies,statuses in itertools.product(families,(0,1,2,3,6),status_sets):
 equipped=[f['root']]*copies;c=Values();c.setup(equipped,statuses)
 values=c.value();verify(values,expected(equipped,statuses))
 assert c.value(False)==values
 record('repeat',c,effect=f['effect'],copies=copies,statuses=statuses,values=values)
print('PASS repeat',len(checks['repeat']),flush=True)
mixed=[]
for state in (2,5,260):
 group=[f['root'] for f in families if f['state']==state]
 for n in range(2,len(group)+1):mixed.extend(map(list,itertools.combinations(group,n)))
mixed.extend([roots,list(reversed(roots)),roots*2])
for equipped,statuses in itertools.product(mixed,status_sets):
 c=Values();c.setup(equipped,statuses);values=c.value();verify(values,expected(equipped,statuses))
 record('mixed',c,roots=equipped,statuses=statuses,values=values)
print('PASS mixed',len(checks['mixed']),flush=True)
for f,critical,flag in itertools.product(families,(False,True),(False,True)):
 c=Values();c.setup([f['root']],list(statusmap))
 for kind in range(13):
  c.packet(10000,kind,critical,flag);values=c.value();verify(values,f['rate'])
  record('context',c,effect=f['effect'],kind=kind,critical=critical,flag=flag,values=values)
print('PASS context',len(checks['context']),flush=True)
c=Values();c.setup(roots,list(statusmap));rate=expected(roots,list(statusmap))
for tags,id in tag_rows.items():
 c.packet(id);values=c.value();verify(values,rate)
 record('tags',c,attack=id,tags=list(tags),values=values)
print('PASS tags',len(checks['tags']),flush=True)
for f,disabled_attacker,disabled_target,statuses in itertools.product(families,(False,True),(False,True),status_sets):
 c=Values();c.setup([f['root']]*3,statuses)
 if disabled_attacker:c.disable(OBJ)
 if disabled_target:c.disable(TARGET)
 values=c.value();verify(values,1 if disabled_attacker or disabled_target else expected([f['root']],statuses))
 record('disabled',c,effect=f['effect'],attacker=disabled_attacker,target=disabled_target,statuses=statuses,values=values)
print('PASS disabled',len(checks['disabled']),flush=True)
for f in families:
 statuses=[row['id'] for row in status_rows if row['state']==f['state']]
 c=Values();c.setup([f['root']],statuses)
 before=c.value();verify(before,f['rate'])
 after=c.value(target=EMPTY);verify(after,1)
 returned=c.value();verify(returned,f['rate'])
 # A matching status on the attacker cannot substitute for the target's state.
 for id in statuses:c.insert(id)
 c.tick(OBJ);self_only=c.value(target=EMPTY);verify(self_only,1)
 record('retarget',c,effect=f['effect'],before=before,clearTarget=after,returned=returned,attackerOnly=self_only)
for f,fps in itertools.product(status_rows,(30,60,120)):
 c=Values();c.setup(roots,[f['id']]);last=None;changes=[]
 for frame in range((f['duration']+1)*fps):
  c.tick(dt=1/fps);values=c.value()
  if values!=last:changes.append(dict(frame=frame,values=values,nodes=c.target_nodes()));last=values
 assert len(changes)==2,(f,fps,changes)
 verify(changes[0]['values'],expected(roots,[f['id']]))
 verify(changes[1]['values'],1)
 assert abs(changes[1]['frame']/fps-f['duration'])<=4.01/fps,(f,fps,changes)
 record('lifetime',c,status=f['id'],fps=fps,duration=f['duration'],changes=changes)
 print('PASS lifetime',f['id'],fps,flush=True)
for statuses,base,attacker,target_present in itertools.product(status_sets,((1,1,1,1,1),(100,0,7.5,200,123.25)),(False,True),(False,True)):
 c=Values();c.setup(roots,statuses)
 values=c.value(base=base,attacker=attacker,target=TARGET if target_present else 0)
 rate=expected(roots,statuses) if attacker and target_present else 1
 verify(values,rate,base)
 record('caller',c,statuses=statuses,base=base,attacker=attacker,target=target_present,values=values)
c=Values();c.setup(roots,list(statusmap))
for kind in range(13):
 values=c.attack(kind);verify(values,1)
 record('baseline',c,kind=kind,values=values)
output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),attachParamSha256=sha(raw),atkParamSha256=sha(atkraw),
 families=families,statusRows=status_rows,checks=checks,filterDifferences=sorted(set(fields)|{'enemyStateInfoTrigger'}),
 callsite=dict(start='43A5E1',end='43A605',sha256=sha(x.pe.get_data(0x43a5e1,0x24)),outerStart='439E80',outerEnd='43AE9F'),
 native=dict(selection='4FEA30 → E6E150 → E6E3B0',tags='E6D530',context='50F230',eligibility='511010',
 target='42C130 → 508E20',damage='43A5E1 → 5025E0',lifecycle='50D060 → 5057D0 → 50ACD0'),
 stubs=sorted(stubs|{'synthetic inventory in positive slot0; draw legality not asserted',
 'runtime hit packet explicitly supplies source kind, critical and additional flag, source IDs and native PARAM-derived tag mask; full packet construction is not run',
 'receiver context, attacker actor and input damage vector supplied at native hit-callsite basic-block boundary; surrounding collision/damage pipeline not executed',
 'target status rows inserted explicitly; actual buildup, immunity, onset and resource damage not executed',
 'no final damage mitigation or HP write, ailment cure/reapplication flows, equipment rebuilding, death/reload or multiplayer'}),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',{k:len(v) for k,v in checks.items()},flush=True)
