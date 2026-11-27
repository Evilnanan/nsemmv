"""Native on-hit stamina selection, hit dispatch, timer and resource-write probe.

Runtime impact context and delivery on the following update are explicit inputs.
The actual character resource callsite, sign conversion and clamped setter run.
Full collision, action scheduling, multiplayer and natural stamina regen do not.
"""
import argparse,itertools,json,math,struct
from pathlib import Path
from native_effect_runtime import BASE,OBJ,STOP,Chain,Inputs,sha
from unicorn.x86_const import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','output'):p.add_argument(name,type=Path)
a=p.parse_args();inputs=Inputs(a.exe,a.extracted)
raw=a.extracted.with_suffix('.AttachEffectParam.param').read_bytes();rows=Inputs.table(raw,0x44)
assert sha(raw)=='ae8128ed510a532d0fa7cb56fa9c86e4a44c9d815dd4ee01c05821d5f50a9827'
assert sha(inputs.param)=='07ec636c5565d4551efeb53e6f08bc633b2aa4f2129f13c61b0638d69b1bc176'
attack_raw=a.extracted.with_suffix('.AtkParam_Pc.param').read_bytes()
assert sha(attack_raw)=='1ec1893420053cbfb06e3efb269ade4ba9d6a617d1d3dbb370e837847be05676'
attack_rows=[attack_raw[off:off+0x1d0]
 for k in range(struct.unpack_from('<H',attack_raw,10)[0])
 if struct.unpack_from('<i',attack_raw,0x40+k*24)[0]==10000
 for off in [struct.unpack_from('<Q',attack_raw,0x48+k*24)[0]]]
assert len(attack_rows)==1 and attack_rows[0][0x1cb]&1
families=[]
for id,exclusive,category,amount in ((7100100,-1,20,2),(7100110,300,10,3)):
 attach=inputs.x['tables']['AttachEffectParam'][str(id)];r=inputs.spells[str(id)];leaf=inputs.spells[str(id+1)]
 assert attach['passiveSpEffectId_1']==id and attach['exclusivityId']==exclusive
 assert all(attach[k]==-1 for k in ('passiveSpEffectId_2','passiveSpEffectId_3','permanentSpEffectId'))
 assert (r['stateInfo'],r['spCategory'],r['effectEndurance'],r['atkOccurrenceSpEffectId'],r['triggerOnWepType'])==(2103,category,-1,id+1,0)
 assert (leaf['stateInfo'],leaf['spCategory'],leaf['changeStaminaRate'],leaf['changeStaminaPoint'],leaf['effectTargetAttacker'])==(0,20,0,-amount,1)
 assert math.isclose(leaf['effectEndurance'],.3,rel_tol=1e-6) and math.isclose(leaf['motionInterval'],.4,rel_tol=1e-6)
 assert all(r[k]==leaf[k]==-1 for k in ('cycleOccurrenceSpEffectId','replaceSpEffectId'))
 families.append(dict(effect=id,root=id,leaf=id+1,exclusive=exclusive,category=category,amount=amount,window=leaf['effectEndurance'],interval=leaf['motionInterval']))
assert {k for k,v in inputs.spells['7100110'].items() if v!=inputs.spells['7100100'][k]}=={'spCategory','atkOccurrenceSpEffectId'}
assert {k for k,v in inputs.spells['7100111'].items() if v!=inputs.spells['7100101'][k]}=={'changeStaminaPoint'}
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


class Hit(Chain):
    def hook(self, u, address, size, user):
        pc = address - BASE
        def finish(value=0):
            u.reg_write(UC_X86_REG_RAX, value)
            sp = u.reg_read(UC_X86_REG_RSP)
            u.reg_write(UC_X86_REG_RIP, struct.unpack('<Q', u.mem_read(sp, 8))[0])
            u.reg_write(UC_X86_REG_RSP, sp + 8)
        if pc == 0x3daf00:
            u.reg_write(UC_X86_REG_RIP,STOP)
        elif pc == 0xe6d630:
            assert u.reg_read(UC_X86_REG_R8) == 10000 and u.reg_read(UC_X86_REG_RDX) == 1
            self.stubs.add('E6D630 unique actual AtkParam_Pc/10000 row lookup')
            wrapper = u.reg_read(UC_X86_REG_RCX)
            u.mem_write(OBJ + 0xb000, attack_rows[0])
            self.q(wrapper + 0x10, OBJ + 0xb000)
            finish(wrapper)
        elif pc == 0xea7fc0:
            raise AssertionError('unexpected weapon lookup')
        elif pc == 0xea9a60:
            self.stubs.add('EA9A60 empty auxiliary animation-reference lookup')
            finish(u.reg_read(UC_X86_REG_RCX))
        else:
            super().hook(u, address, size, user)

    def hit(self, weapon, kind=1, flags=0, attack_category=0):
        vector, ctx = OBJ + 0x8000, OBJ + 0x8400
        self.q(vector + 8, OBJ + 0x8200)
        self.q(vector + 0x10, OBJ + 0x8200)
        self.q(vector + 0x18, OBJ + 0x8300)
        self.u.mem_write(ctx, bytes(0x300))
        self.u.mem_write(ctx + 0x122, bytes([kind]))
        self.u.mem_write(ctx + 0x161, bytes([flags]))
        self.u.mem_write(ctx + 0x190, struct.pack('<i', weapon))
        self.u.mem_write(ctx + 0x40, struct.pack('<iii', 10000, 1, attack_category))
        self.u.mem_write(ctx + 0x280, struct.pack('<i', 10))
        self.invoke(0x505e90, [OBJ, vector, ctx])
        end = struct.unpack('<Q', self.u.mem_read(vector + 0x10, 8))[0]
        count = (end - (OBJ + 0x8200)) // 4
        assert 0 <= count < 64
        return list(struct.unpack('<' + 'i' * count, self.u.mem_read(OBJ + 0x8200, count * 4)))

    def step(self, dt):
        self.qualify();self.update(dt)
    def stamina(self,current=0,maximum=100):
        self.q(OBJ+0x6190,OBJ);self.q(OBJ+0x61b8,OBJ+0xf000);self.q(OBJ+0xf000,OBJ+0xe000)
        self.u.mem_write(OBJ+0xe15c,struct.pack('<ii',current,maximum))
        self.u.reg_write(UC_X86_REG_RSI,OBJ+0x6000)
        self.invoke(0x3daeb4,[])
        return struct.unpack('<i',self.u.mem_read(OBJ+0xe15c,4))[0]
    def disable(self):
        ptr=struct.unpack('<Q',self.u.mem_read(OBJ+8,8))[0]
        while ptr:
            self.u.mem_write(ptr+0x68,struct.pack('<I',0x800c0003));ptr=struct.unpack('<Q',self.u.mem_read(ptr+0x38,8))[0]


checks={k:[] for k in ('selection','filter','timing','spacing','resource')};stubs=set()
def record(group,c,**row):checks[group].append(row);stubs.update(c.stubs)
def amount(roots):return sum(2 if id==7100100 else 3 for id in set(roots))
def prepare(roots):
 c=Hit(inputs)
 for id in roots:c.insert(id)
 c.step(0);return c
slot_sets=[[f['effect']]*n for f in families for n in (1,2,3,6)]
slot_sets.extend([[7100100,7100110]*n for n in (1,3)])
slot_sets.extend([[7100110,7100100]*n for n in (1,3)])
for ids,hero in itertools.product(slot_sets,range(11)):
 c=Selection([[id] for id in ids],hero);bits=c.select();selected=[]
 for index,id in enumerate(ids):
  if index*6 not in bits:continue
  c.invoke(0xe6e150,[OBJ+0x9200,id]);selected.append(c.invoke(0xe6e3b0,[OBJ+0x9200,0])&0xffffffff)
 expected=[id for i,id in enumerate(ids) if id!=7100110 or i==ids.index(id)]
 assert selected==expected
 v=prepare(selected);leaves=v.hit(-1);assert leaves==[id+1 for id in dict.fromkeys(ids)]
 for id in leaves:v.insert(id)
 v.step(0);value=v.stamina();assert value==amount(ids)
 record('selection',c,ids=ids,hero=hero,selected=selected,leaves=leaves,restored=value);stubs.update(v.stubs)
print('PASS selection',len(checks['selection']),flush=True)
for f,copies,kind,flags,category,disabled in itertools.product(families,(1,3),range(13),(0,32),(0,6),(False,True)):
 c=prepare([f['root']]*copies)
 if disabled:c.disable()
 leaves=c.hit(-1,kind,flags,category)
 expected=[f['leaf']]*(copies if f['category']==10 else 1) if kind not in (3,4,10) and not disabled else []
 assert leaves==expected,(f,copies,kind,flags,category,disabled,leaves,expected)
 record('filter',c,effect=f['effect'],copies=copies,kind=kind,flags=flags,category=category,disabled=disabled,leaves=leaves)
print('PASS filter',len(checks['filter']),flush=True)
sets=[[7100100],[7100110],[7100100,7100110]]
def timeline(roots,fps,hits,frames):
 c=prepare(roots);pending=[];events=[];c.arrivals=[]
 for frame in range(frames):
  for id in pending:
   before=c.nodes();result=c.insert(id);c.arrivals.append(dict(frame=frame,leaf=id,before=before,result=result))
  c.step(1/fps);value=c.stamina()
  if value:
   assert value==amount(roots),(roots,frame,value)
   events.append(dict(frame=frame,restored=value))
  pending=c.hit(-1) if frame in hits else []
 assert [n['id'] for n in c.nodes()]==list(dict.fromkeys(roots)) or all(n['id'] in roots for n in c.nodes())
 return c,events
for roots,copies,fps,schedule in itertools.product(sets,(1,3),(30,60,120),('single','frame','tenth','fifth','half')):
 every={'frame':1,'tenth':fps//10,'fifth':fps//5,'half':fps//2}.get(schedule)
 hits=[0] if every is None else list(range(0,2*fps,every))
 c,events=timeline(roots*copies,fps,hits,3*fps)
 assert events[0]['frame']==1
 if schedule=='single':assert len(events)==1
 elif schedule=='half':assert [e['frame'] for e in events]==[h+1 for h in hits]
 else:
  assert len(events)==6,(roots,copies,fps,schedule,events)
  assert all(abs((right['frame']-left['frame'])/fps-.4)<=1.01/fps for left,right in zip(events,events[1:]))
 record('timing',c,roots=roots,copies=copies,fps=fps,schedule=schedule,hits=hits,events=events)
print('PASS timing',len(checks['timing']),flush=True)
for roots,fps,spacing in itertools.product(sets,(30,60,120),('single','frame','tenth','fifth','boundary','past','period','half')):
 gap={'frame':1,'tenth':fps//10,'fifth':fps//5,'boundary':round(.3*fps),'past':round(.3*fps)+1,'period':round(.4*fps),'half':fps//2}.get(spacing)
 hits=[0] if gap is None else [0,gap]
 c,events=timeline(roots,fps,hits,2*fps)
 assert events[0]['frame']==1 and len(events)<=2
 if spacing in ('single','frame'):assert len(events)==1,(fps,spacing,events)
 elif spacing=='half':assert [e['frame'] for e in events]==[h+1 for h in hits],(fps,spacing,events)
 elif spacing in ('past','boundary'):
  # A 0.3s node can remain until the following cleanup steps. Regrant
  # near this boundary may retain its timer or create a new instance.
  assert len(events)==2 and gap+1<=events[1]['frame']<=math.ceil(.4*fps)+2,(fps,spacing,events)
 elif spacing=='tenth':
  # The refreshed 0.3s lifetime and the 0.4s pulse meet at this
  # boundary; float rounding and cleanup can permit or omit the tail.
  if len(events)==2:assert abs(events[1]['frame']/fps-.4)<=2.01/fps
 else:
  assert len(events)==2,(fps,spacing,events)
  assert abs(events[1]['frame']/fps-.4)<=2.01/fps
 if len(events)==2:assert events[-1]['frame']<=hits[-1]+1+math.ceil(.3*fps)+2
 record('spacing',c,roots=roots,fps=fps,spacing=spacing,hits=hits,events=events,arrivals=c.arrivals)
print('PASS spacing',len(checks['spacing']),flush=True)
for roots,copies,maximum,current_kind,disabled in itertools.product(sets,(1,3),(1,10,100),('negative','zero','near','full'),(False,True)):
 current={'negative':-20,'zero':0,'near':maximum-1,'full':maximum}[current_kind]
 c=prepare(roots*copies)
 for id in c.hit(-1):c.insert(id)
 c.step(0)
 if disabled:c.disable()
 result=c.stamina(current,maximum);expected=current if disabled else min(maximum,current+amount(roots))
 assert result==expected,(roots,copies,maximum,current,disabled,result)
 record('resource',c,roots=roots,copies=copies,maximum=maximum,current=current,disabled=disabled,result=result)
print('PASS resource',len(checks['resource']),flush=True)
output=dict(schema=1,exeSha256=sha(inputs.raw),regulationSha256=inputs.x['hashes']['regulation.bin'],paramSha256=sha(inputs.param),attachParamSha256=sha(raw),atkParamSha256=sha(attack_raw),families=families,checks=checks,
 callsite=dict(start='3DAEB4',end='3DAF00',sha256=sha(inputs.pe.get_data(0x3daeb4,0x4c))),
 native=dict(selection='4FEA30 → E6E150 → E6E3B0',hit='505E90',lifecycle='50D060 → 5057D0 → 50ACD0',resource='3DAEB4 → 5085A0 → 4261D0 → 427F00'),
 stubs=sorted(stubs|{'synthetic inventory in positive slot0; draw legality not asserted',
 'explicit impact context and unique AtkParam_Pc/10000 row; full collision, packet construction and all attack tags not executed',
 'returned on-hit IDs inserted in attacker container on next simulation frame; full effect-target delivery and actor scheduling not executed',
 'explicit current/max stamina resource at native resource-callsite boundary; natural regeneration, action costs, equipment rebuild, death/reload and multiplayer not executed'}),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',{k:len(v) for k,v in checks.items()},flush=True)
