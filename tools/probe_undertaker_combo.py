"""Native Undertaker finisher hit selection, attack bonus and lifetime probe.

Uses pinned unmodified PARAM rows and native tag conversion, hit dispatch,
equipment selection, effect lifecycle and multiplier consumers. Runtime hit
metadata and result delivery are explicit fixtures, not a full game session.
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
atkraw=a.extracted.with_suffix('.AtkParam_Pc.param').read_bytes();atk=Inputs.table(atkraw,0x1d0)
assert sha(atkraw)=='1ec1893420053cbfb06e3efb269ade4ba9d6a617d1d3dbb370e837847be05676'
# Do not silently collapse duplicate IDs into last-row lookup semantics.
assert len(atk)==struct.unpack_from('<H',atkraw,10)[0]==11933
root,leaf,tag=7036900,7036901,104
r=inputs.spells[str(root)];l=inputs.spells[str(leaf)]
attach=inputs.x['tables']['AttachEffectParam'][str(root)]
assert attach['passiveSpEffectId_1']==root and attach['exclusivityId']==-1
assert all(attach[k]==-1 for k in ('passiveSpEffectId_2','passiveSpEffectId_3','permanentSpEffectId'))
assert [k for k in attach if k.startswith('allow') and attach[k]]==['allowUndertaker']
assert (r['stateInfo'],r['spCategory'],r['effectEndurance'],r['atkOccurrenceSpEffectId'],r['magicSubCategoryChange1'])==(2103,20,-1,leaf,tag)
assert {k for k in r if r[k]!=inputs.spells['7100100'][k]}=={'atkOccurrenceSpEffectId','magicSubCategoryChange1','iconId','saveCategory','spEffectTextId_1'}
fields=['physicsAttackRate','magicAttackRate','fireAttackRate','thunderAttackRate','darkAttackRate']
rate=l[fields[0]];assert math.isclose(rate,1.16,rel_tol=1e-6) and all(l[k]==rate for k in fields)
assert (l['stateInfo'],l['spCategory'],l['effectEndurance'],l['motionInterval'],l['effectTargetAttacker'],l['isExtendSpEffectLife'],l['isContractSpEffectLife'])==(0,20,20,0,1,0,1)
assert all(l[k]==-1 for k in ('cycleOccurrenceSpEffectId','replaceSpEffectId','atkOccurrenceSpEffectId'))
tags={int(id):sorted({row['subCategory'+str(i)] for i in range(1,6)}-{0}) for id,row in inputs.x['tables']['AtkParam_Pc'].items()}
positives=sorted(id for id,t in tags.items() if tag in t);assert len(positives)==493
representatives={}
for id,t in tags.items():representatives.setdefault(tuple(t),id)
assert len(representatives)==216
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
        if pc == 0xe6d630:
            attack=u.reg_read(UC_X86_REG_R8)&0xffffffff
            assert attack in atk and u.reg_read(UC_X86_REG_RDX) == 1
            self.stubs.add('E6D630 actual AtkParam_Pc lookup')
            wrapper = u.reg_read(UC_X86_REG_RCX)
            u.mem_write(OBJ + 0xb000, atk[attack])
            self.q(wrapper + 0x10, OBJ + 0xb000)
            finish(wrapper)
        elif pc == 0xea7fc0:
            raise AssertionError('unexpected weapon lookup')
        elif pc == 0xea9a60:
            self.stubs.add('EA9A60 empty auxiliary animation-reference lookup')
            finish(u.reg_read(UC_X86_REG_RCX))
        else:
            super().hook(u, address, size, user)

    def hit(self, weapon, kind=1, flags=0, attack_category=0, attack=10000):
        vector, ctx = OBJ + 0x8000, OBJ + 0x8400
        self.q(vector + 8, OBJ + 0x8200)
        self.q(vector + 0x10, OBJ + 0x8200)
        self.q(vector + 0x18, OBJ + 0x8300)
        self.u.mem_write(ctx, bytes(0x300))
        self.u.mem_write(ctx + 0x122, bytes([kind]))
        self.u.mem_write(ctx + 0x161, bytes([flags]))
        self.u.mem_write(ctx + 0x190, struct.pack('<i', weapon))
        self.u.mem_write(ctx + 0x40, struct.pack('<iii', attack, 1, attack_category))
        self.u.mem_write(ctx + 0x280, struct.pack('<i', 10))
        self.u.mem_write(OBJ+0xb000,atk[attack]);self.q(OBJ+0xb410,OBJ+0xb000)
        self.invoke(0xe6d530,[OBJ+0xb400,ctx+0x124])
        self.invoke(0x505e90, [OBJ, vector, ctx])
        end = struct.unpack('<Q', self.u.mem_read(vector + 0x10, 8))[0]
        count = (end - (OBJ + 0x8200)) // 4
        assert 0 <= count < 64
        return list(struct.unpack('<' + 'i' * count, self.u.mem_read(OBJ + 0x8200, count * 4)))

    def step(self,dt):self.qualify();self.update(dt)
    def disable(self):
        ptr=struct.unpack('<Q',self.u.mem_read(OBJ+8,8))[0]
        while ptr:
            self.u.mem_write(ptr+0x68,struct.pack('<I',0x800c0003));ptr=struct.unpack('<Q',self.u.mem_read(ptr+0x38,8))[0]

checks={k:[] for k in ('selection','attacks','context','lifetime','refresh','extension','disabled')};stubs=set()
def record(group,c,**row):checks[group].append(row);stubs.update(c.stubs)
def prepare(copies=1,extension=0):
 c=Hit(inputs)
 for _ in range(copies):c.insert(root)
 for _ in range(extension):c.insert(7006400)
 c.step(0);return c
def trigger(c,attack=90050):
 leaves=c.hit(-1,attack=attack)
 for id in leaves:c.insert(id)
 c.step(0);return leaves
def rates(c,expected):
 v=c.attack();assert all(math.isclose(x,expected,rel_tol=1e-6) for x in v),(v,expected)
 return v
for copies,hero in itertools.product((1,2,3,6),range(11)):
 c=Selection([[root]]*copies,hero);bits=c.select();selected=[]
 for i in range(copies):
  if i*6 not in bits:continue
  c.invoke(0xe6e150,[OBJ+0x9200,root]);selected.append(c.invoke(0xe6e3b0,[OBJ+0x9200,0])&0xffffffff)
 assert selected==([root]*copies if hero in (0,10) else []),(hero,selected)
 v=prepare(len(selected));leaves=trigger(v);assert leaves==([leaf] if selected else [])
 value=rates(v,rate if selected else 1)
 record('selection',c,copies=copies,hero=hero,selected=selected,leaves=leaves,rates=value);stubs.update(v.stubs)
print('PASS selection',len(checks['selection']),flush=True)
# Every tag-104 raw row, plus one representative of every current tag set.
for copies in (1,3):
 c=prepare(copies)
 for attack in sorted(set(positives)|set(representatives.values())):
  leaves=c.hit(-1,attack=attack);assert leaves==([leaf] if tag in tags[attack] else []),(attack,tags[attack],leaves)
  record('attacks',c,copies=copies,attack=attack,tags=tags[attack],leaves=leaves)
print('PASS attacks',len(checks['attacks']),flush=True)
for copies,kind,flags,category,disabled,attack in itertools.product((1,3),range(13),(0,32),(0,6),(False,True),(10000,90050)):
 c=prepare(copies)
 if disabled:c.disable()
 leaves=c.hit(-1,kind,flags,category,attack)
 assert leaves==([leaf] if attack==90050 and kind not in (3,4,10) and not disabled else []),(copies,kind,flags,category,disabled,attack,leaves)
 record('context',c,copies=copies,kind=kind,flags=flags,category=category,disabled=disabled,attack=attack,leaves=leaves)
print('PASS context',len(checks['context']),flush=True)
for copies,fps,extension in itertools.product((1,3),(30,60,120),(0,1,3)):
 c=prepare(copies,extension);trigger(c);value=rates(c,rate);expired=None
 for frame in range(1,21*fps+1):
  c.step(1/fps)
  if not any(n['id']==leaf for n in c.nodes()) and expired is None:expired=frame
 assert expired is not None and abs(expired-20*fps)<=3,(copies,fps,extension,expired)
 rates(c,1);record('lifetime',c,copies=copies,fps=fps,extension=extension,rates=value,expiredFrame=expired,expiredSeconds=expired/fps)
print('PASS lifetime',len(checks['lifetime']),flush=True)
for copies,fps in itertools.product((1,3),(30,60,120)):
 c=prepare(copies);trigger(c);events=[]
 # Refresh twice; then allow the last 20-second window to expire.
 for frame in range(31*fps+1):
  if frame in (5*fps,10*fps):
   before=c.nodes();leaves=trigger(c);after=c.nodes();assert leaves==[leaf]
   assert len([n for n in after if n['id']==leaf])==1
   assert [n['lifetime'] for n in after if n['id']==leaf]==[20]
   events.append(dict(frame=frame,before=before,after=after,rates=rates(c,rate)))
  if frame in (0,9*fps,20*fps,29*fps):rates(c,rate)
  c.step(1/fps)
 rates(c,1);assert not any(n['id']==leaf for n in c.nodes())
 record('refresh',c,copies=copies,fps=fps,events=events,final=c.nodes())
print('PASS refresh',len(checks['refresh']),flush=True)
# One-second countdown contrasts, including the adjacent duration extender.
for copies,extension in itertools.product((1,3),(0,1,2,3,6)):
 c=prepare(copies,extension);trigger(c);before=c.nodes();c.step(1)
 after=c.nodes();assert [n['lifetime'] for n in after if n['id']==leaf]==[19]
 record('extension',c,copies=copies,extension=extension,before=before,after=after,rates=rates(c,rate))
for copies in (1,3):
 c=prepare(copies);trigger(c);rates(c,rate);c.disable();value=rates(c,1)
 record('disabled',c,copies=copies,rates=value)
print('PASS extension/disabled',len(checks['extension']),len(checks['disabled']),flush=True)
output=dict(schema=1,exeSha256=sha(inputs.raw),regulationSha256=inputs.x['hashes']['regulation.bin'],paramSha256=sha(inputs.param),attachParamSha256=sha(raw),atkParamSha256=sha(atkraw),
 effect=root,root=root,leaf=leaf,tag=tag,rate=rate,duration=20,hero=10,positiveAttacks=positives,tagSets=len(representatives),checks=checks,
 native=dict(selection='4FEA30 → E6E150 → E6E3B0',tags='E6D530',hit='505E90 → 50F230 → 511010 / EA0790',lifecycle='50D060 → 5057D0 → 50ACD0 → 511B80',attack='502830'),
 stubs=sorted(stubs|{'synthetic inventory in positive slot0; draw legality not asserted; hero0 is the no-hero control and bypasses role restrictions',
 'explicit 0x300-byte runtime impact context; native E6D530 converts the actual unique AtkParam_Pc row into tags at +124',
 'actual raw AtkParam lookup at E6D630; no replaced tag or eligibility predicate',
 'hit-result IDs inserted into attacker effect list; full target delivery, collision and action scheduling not executed',
 'native float attack multipliers; final damage, current HP, network, equip rebuild and death/reload not executed',
 'all 493 tag-104 attack rows tested; their individual behavior/animation reachability is not inferred from tags'}),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS total',sum(map(len,checks.values())),flush=True)
