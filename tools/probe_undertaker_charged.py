"""Trace Undertaker charged-spell hit protection, spell scope and refresh.

Raw PARAM, relocated TAE and original native consumers run in isolated fixtures.
The terminal spell request is recorded; collision and target delivery are not a
full game session. Compatible actor virtuals and identities are explicit inputs.
"""
import argparse,itertools,json,math,struct,re
from pathlib import Path
from native_effect_runtime import BASE,OBJ,STOP,Chain,Inputs,sha
from native_animation_runtime import NativeTae
from effect_behavior_graph import BehaviorGraph
from unicorn.x86_const import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','animations','behavior','script','output'):p.add_argument(name,type=Path)
a=p.parse_args();inputs=Inputs(a.exe,a.extracted);t=inputs.x['tables']
raws={name:a.extracted.with_suffix('.'+name+'.param').read_bytes() for name in ('AttachEffectParam','AtkParam_Pc','Magic','Bullet')}
hashes={'AttachEffectParam':'ae8128ed510a532d0fa7cb56fa9c86e4a44c9d815dd4ee01c05821d5f50a9827','AtkParam_Pc':'1ec1893420053cbfb06e3efb269ade4ba9d6a617d1d3dbb370e837847be05676','Magic':'17742eeafe4fade863f3a7ee5f7ff483bd4897f765802fe4a1954dfa8107b63e','Bullet':'ddce4888040a061cf982a237e8f6e3ddce5f2162a238865a072f75d27b5e9d44'}
assert sha(inputs.param)=='07ec636c5565d4551efeb53e6f08bc633b2aa4f2129f13c61b0638d69b1bc176'
for name,raw in raws.items():assert sha(raw)==hashes[name]
rows=Inputs.table(raws['AttachEffectParam'],0x44);atk=Inputs.table(raws['AtkParam_Pc'],0x1d0)
magicrows=Inputs.table(raws['Magic'],0xac);bulletrows=Inputs.table(raws['Bullet'],0x15c)
for name,table in (('AttachEffectParam',rows),('AtkParam_Pc',atk),('Magic',magicrows),('Bullet',bulletrows)):
 assert len(table)==struct.unpack_from('<H',raws[name],10)[0],name
EFFECTS=(7037500,7037501);root,leaf,tag=7037100,7037101,110
r=inputs.spells[str(root)];l=inputs.spells[str(leaf)]
for effect in EFFECTS:
 attach=t['AttachEffectParam'][str(effect)]
 assert [attach['passiveSpEffectId_'+str(n)] for n in (1,2,3)]==[root,-1,-1]
 assert attach['exclusivityId']==attach['permanentSpEffectId']==-1
 assert [k for k,v in attach.items() if k.startswith('allow') and v]==['allowUndertaker']
for id in (root,leaf):
 assert sum(struct.unpack_from('<i',inputs.param,0x40+n*24)[0]==id for n in range(struct.unpack_from('<H',inputs.param,10)[0]))==1
assert (r['stateInfo'],r['spCategory'],r['effectEndurance'],r['atkOccurrenceSpEffectId'],r['magicSubCategoryChange1'])==(2103,20,-1,leaf,tag)
assert all(r[k]==1 for k in ('magParamChange','miracleParamChange','shamanParamChange'))
assert all(r['magicSubCategoryChange'+str(n)]==0 for n in (2,3))
assert (l['stateInfo'],l['spCategory'],l['effectEndurance'],l['motionInterval'],l['effectTargetAttacker'],l['isExtendSpEffectLife'],l['isContractSpEffectLife'])==(0,20,10,11,1,0,0)
assert all(l[k]==-1 for k in ('cycleOccurrenceSpEffectId','replaceSpEffectId','atkOccurrenceSpEffectId'))
rate=l['neutralDamageCutRate'];assert math.isclose(rate,.65,rel_tol=1e-6)
assert all(l[k+'DamageCutRate']==rate for k in ('magic','fire','thunder','dark'))
assert l['toughnessDamageCutRate']==0 and struct.unpack_from('<f',inputs.rows[leaf],0x1b4)[0]==0
tags={int(id):sorted({row['subCategory'+str(n)] for n in range(1,6)}-{0}) for id,row in t['AtkParam_Pc'].items()}
for id,ts in tags.items():assert ts==sorted(set(atk[id][off] for off in (0x4e,0x4f,0x1c8,0x1c9,0x1ca))-{0})
positives=sorted(id for id,ts in tags.items() if tag in ts);assert len(positives)==164
representatives={}
for id,ts in tags.items():representatives.setdefault(tuple(ts),id)
assert len(representatives)==216
animations=json.loads(a.animations.read_text());assert animations['bundles'][0]['sha256']=='806e6b218d747277ab45e14f45ca80b9ecf8c13ada22f89db2d3ef23caa62b2a'
tracks={t['ID']:t for b in animations['bundles'] for t in b['taes']}
script=a.script.read_bytes();assert sha(script)=='96339bb15f57559cd42a940d616fcc2a18a10f50845cfc22b46b356ab66c3b29'
script_text=script.decode('utf-8-sig').replace('\r\n','\n')
functions={m[1]:m[0] for m in re.finditer(r'^function (\w+)\([^\n]*\).*?(?=^function |\Z)',script_text,re.M|re.S)}
assert 'IsMagicAnimExists(magic_type, 45011)' in functions['IsChargeMagic']
for hand in ('Right','Left'):
 body=functions[f'MagicLoop{hand}_Upper_onUpdate']
 assert 'IDX_AINOTE_STATETYPE_CHARGEMAGIC' in body and 'env(ActionDuration,' in body
 assert f'ExecEventHalfBlend(Event_MagicFire{hand}Cancel, blend_type)' in body
b=BehaviorGraph(a.behavior);bindings=[]
for state in ('MagicFireRight','MagicFireRightCancel','MagicFireLeft','MagicFireLeftCancel'):
 matches=[idx for idx,(typ,_,count) in enumerate(b.items) if typ and count==1 and b.types[typ&0xffffff]['Identity']=='hkbStateMachine::StateInfo' and b.name(idx)==state];assert len(matches)==1
 gen=b.reference(matches[0],'generator');path=[matches[0],gen]
 if b.item(gen)[0]['Identity']=='hkbManualSelectorGenerator':
  assert b.selector_binding(gen)['name']=='MagicRight_ShieldCategory'
  gen=b.children(gen)[0];path.append(gen)
 assert b.item(gen)[0]['Identity']=='CustomManualSelectorGenerator'
 for child in b.children(gen):
  if b.item(child)[0]['Identity']!='hkbClipGenerator':continue
  animation=b.string(b.reference(child,'animationName'))
  if any(animation==f'a{400+motion:03d}_{an:06d}' for motion in (2,17,107) for an in (45010,45011,45110,45111)):
   bindings.append(dict(state=state,path=path+[child],animation=animation))
assert len(bindings)==12,bindings
spell_bindings=[]
for magic in (4020,6010,2004500):
 m=t['Magic'][str(magic)]
 assert magicrows[magic][0x28]==m['spEffectCategory']==(3 if m['ezStateBehaviorType']==0 else 4)
 for slot in (0,1):
  bid=m['refId'+str(slot+1)];attack=t['Bullet'][str(bid)]['atkId_Bullet']
  assert m['refCategory'+str(slot+1)]==1 and struct.unpack_from('<i',magicrows[magic],0x68+slot*4)[0]==bid
  assert struct.unpack_from('<i',bulletrows[bid],0)[0]==attack
  assert (tag in tags[attack])==bool(slot)
  assert any(t['AtkParam_Pc'][str(attack)][k]>0 for k in ('atkPhys','atkMag','atkFire','atkThun','atkDark'))
  spell_bindings.append(dict(magic=magic,name=inputs.x['texts']['zh_CN']['MagicName'][str(magic)],slot=slot,bullet=bid,attack=attack,tae=2400+m['refType'],kind=magicrows[magic][0x28]))
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
        assert int.from_bytes(self.u.mem_read(ctx+0x124,32),'little')==sum(1<<tag for tag in tags[attack])
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

class Cast(Chain):
 def __init__(self,magic=6050):
  super().__init__(inputs);self.magic=magic;self.requests=[];self.costs=[]
  self.q(OBJ+0x6190,OBJ);self.q(OBJ+0x61b8,OBJ+0x9000)
  self.q(OBJ+0x9060,OBJ+0xe000);self.q(OBJ+0xe000,OBJ+0xe100);self.q(OBJ+0xe118,STOP+0x200)
  self.q(OBJ+0x6450,STOP+0x201);self.q(OBJ+0x6418,STOP+0x202);self.q(OBJ+0x6548,STOP+0x203)
  self.q(OBJ+0x6460,STOP+0x204)
  self.q(OBJ+0x6100,OBJ+0x6000);self.q(OBJ+0x90e8,OBJ+0xde00);self.q(OBJ+0xde10,OBJ+0xdf00)
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
   u.mem_write(OBJ+0xb000,magicrows[id]);u.mem_write(out,struct.pack('<IiQ',id,6,OBJ+0xb000));end(out)
  elif pc in (0x3ced90,0x4d1b20,0x3d74f0,0xb31990):end(OBJ+0xd800 if pc==0x3ced90 else 0)
  elif pc in (0x4b2b60,0x484500):end(0)
  elif pc==0x383d20:
   ctx=u.reg_read(UC_X86_REG_RCX);self.requests.append(dict(type=u.mem_read(ctx+0x14,1)[0],id=struct.unpack('<i',u.mem_read(ctx+0x18,4))[0]));end(1)
  elif pc==0x4b1b90:end(OBJ+0xd900)
  elif pc==0x3c7f40:
   self.requests.append(dict(target=u.reg_read(UC_X86_REG_RCX),id=u.reg_read(UC_X86_REG_RDX)&0xffffffff));end()
  elif pc==0x384a30:
   obj=u.reg_read(UC_X86_REG_RCX);self.costs.append(list(struct.unpack('<5i',u.mem_read(obj+0xb4,20))));end()
  else:super().hook(u,address,size,user)
 def event(self,raw,track,animation,active):
  tae=NativeTae(self,raw,track['sha256']);ctx=tae.select(animation,64)
  meta=next(e for an in track['animations'] if an['ID']==animation for e in an['events'] if e['Type']==64)
  ptr=struct.unpack('<Q',self.u.mem_read(ctx+8,8))[0];payload=bytes.fromhex(meta['hex'])
  assert bytes(self.u.mem_read(ptr,len(payload)))==payload
  self.q(OBJ+0x8018,OBJ+0x6000);self.q(ctx+0x20,OBJ+0xf800)
  self.u.mem_write(ctx+0x18,bytes([active]));self.u.mem_write(OBJ+0xf800,struct.pack('<f',meta['StartTime']))
  self.invoke(0x40eb30,[OBJ+0x8000,ctx]);return meta

class Protection(Hit):
 def values(self):
  self.u.mem_write(OBJ+0x800,bytes(0x200));self.invoke(0x503800,[OBJ,OBJ+0x500,OBJ+0x520,OBJ+0x540,OBJ+0x800])
  defense=list(struct.unpack('<5f',self.u.mem_read(OBJ+0x500,20)))
  self.invoke(0x502270,[OBJ,0]);poise=struct.unpack('<f',(self.u.reg_read(UC_X86_REG_XMM0)&0xffffffff).to_bytes(4,'little'))[0]
  return dict(incoming=defense,poise=poise)
 def trigger(self,attack=40201,kind=3):
  grants=self.hit(-1,kind=kind,attack=attack)
  for id in grants:self.insert(id)
  self.step(0);return grants
checks={k:[] for k in ('selection','attacks','context','mixed','animation','lifetime','refresh','disabled','removal')};stubs=set()
def record(key,c,**row):checks[key].append(row);stubs.update(c.stubs)
def prepare(copies=1,extension=0):
 c=Protection(inputs)
 for _ in range(copies):c.insert(root)
 for _ in range(extension):c.insert(7006400)
 c.step(0);return c
def verify(c,enabled):
 values=c.values();assert all(math.isclose(v,rate if enabled else 1,rel_tol=1e-6) for v in values['incoming']),values
 assert values['poise']==(0 if enabled else 1),values
 return values
for effect,copies,hero in itertools.product(EFFECTS,(1,2,3,6),range(11)):
 c=Selection([[effect]]*copies,hero);bits=c.select();allowed=hero in (0,10)
 assert all((n*6 in bits)==allowed for n in range(copies))
 roots=[]
 for n in range(copies):
  if n*6 in bits:
   c.invoke(0xe6e150,[OBJ+0x9200,effect]);roots.append(c.invoke(0xe6e3b0,[OBJ+0x9200,0])&0xffffffff)
 assert roots==([root]*copies if allowed else [])
 v=prepare(len(roots));grants=v.trigger();assert grants==([leaf] if allowed else []);value=verify(v,allowed);stubs.update(v.stubs)
 record('selection',c,effect=effect,copies=copies,hero=hero,bits=bits,roots=roots,grants=grants,values=value)
print('PASS selection',len(checks['selection']),flush=True)
for copies in (0,1,3):
 c=prepare(copies)
 for attack in sorted(set(positives)|set(representatives.values())):
  grants=c.hit(-1,attack=attack);assert grants==([leaf] if copies and tag in tags[attack] else [])
  record('attacks',c,copies=copies,attack=attack,tags=tags[attack],grants=grants)
print('PASS attacks',len(checks['attacks']),flush=True)
for copies,disabled in itertools.product((1,3),(False,True)):
 c=prepare(copies)
 if disabled:c.disable()
 for attack,kind,flags,category in itertools.product((10000,40201),range(13),(0,32),(0,6)):
  grants=c.hit(-1,kind,flags,category,attack)
  assert grants==([leaf] if attack==40201 and not disabled else []),(copies,disabled,attack,kind,flags,category,grants)
  record('context',c,copies=copies,disabled=disabled,attack=attack,kind=kind,flags=flags,category=category,grants=grants)
print('PASS context',len(checks['context']),flush=True)
for first,second in itertools.product(range(4),repeat=2):
 effects=[EFFECTS[0]]*first+[EFFECTS[1]]*second;c=Selection([[e] for e in effects],10);bits=c.select();roots=[]
 for n,e in enumerate(effects):
  assert n*6 in bits;c.invoke(0xe6e150,[OBJ+0x9200,e]);roots.append(c.invoke(0xe6e3b0,[OBJ+0x9200,0])&0xffffffff)
 assert roots==[root]*len(effects)
 v=prepare(len(roots));grants=v.trigger();assert grants==([leaf] if roots else []);values=verify(v,bool(roots));stubs.update(v.stubs)
 record('mixed',c,first=first,second=second,grants=grants,nodes=v.nodes(),values=values)
print('PASS mixed',len(checks['mixed']),flush=True)
for magic,animation,active,copies in itertools.product((4020,6010,2004500),(45010,45011,45110,45111),(0,1),(1,3)):
 slot=int(animation%10==0);binding=next(r for r in spell_bindings if r['magic']==magic and r['slot']==slot)
 track=tracks[binding['tae']];raw=Path(str(a.animations)+'.'+str(track['ID'])+'.tae').read_bytes()
 c=Cast(magic);meta=c.event(raw,track,animation,active)
 assert bytes.fromhex(meta['hex'])[8]==slot
 assert c.requests==([dict(type=1,id=binding['bullet'])] if active else []),(magic,animation,active,c.requests,binding)
 v=prepare(copies);grants=[]
 for req in c.requests:
  grants+=v.trigger(binding['attack'],binding['kind'])
 assert grants==([leaf] if active and slot else [])
 values=verify(v,bool(grants));stubs.update(v.stubs)
 record('animation',c,magic=magic,tae=track['ID'],animation=animation,event=meta['index'],slot=slot,active=active,copies=copies,requests=c.requests,attack=binding['attack'],grants=grants,values=values)
print('PASS animation',len(checks['animation']),flush=True)
for copies,fps,extension in itertools.product((1,3),(30,60,120),(0,1,3)):
 c=prepare(copies,extension);assert c.trigger()==[leaf];before=verify(c,True);expired=None
 for frame in range(1,11*fps+1):
  c.step(1/fps)
  if not any(n['id']==leaf for n in c.nodes()) and expired is None:expired=frame
 assert expired is not None and abs(expired-10*fps)<=3,(copies,fps,extension,expired)
 record('lifetime',c,copies=copies,fps=fps,extension=extension,before=before,expiredFrame=expired,values=verify(c,False))
print('PASS lifetime',len(checks['lifetime']),flush=True)
for copies,fps in itertools.product((1,3),(30,60,120)):
 c=prepare(copies);assert c.trigger()==[leaf];events=[]
 for frame in range(19*fps+1):
  if frame in (4*fps,8*fps):
   before=c.nodes();grants=c.trigger();assert grants==[leaf]
   assert [n['lifetime'] for n in c.nodes() if n['id']==leaf]==[10]
   events.append(dict(frame=frame,before=before,after=c.nodes(),values=verify(c,True)))
  if frame in (0,7*fps,10*fps,17*fps):verify(c,True)
  c.step(1/fps)
 record('refresh',c,copies=copies,fps=fps,events=events,final=c.nodes(),values=verify(c,False))
for copies in (1,3):
 c=prepare(copies);c.trigger();c.disable();record('disabled',c,copies=copies,values=verify(c,False))
 c=prepare(copies);c.trigger();c.invoke(0x505280,[OBJ,0]);c.step(0)
 assert [n['id'] for n in c.nodes()]==[leaf] and c.trigger()==[]
 before=verify(c,True)
 for _ in range(11*60):c.step(1/60)
 record('removal',c,copies=copies,before=before,values=verify(c,False),nodes=c.nodes())
print('PASS refresh/disabled/removal',len(checks['refresh']),len(checks['disabled']),len(checks['removal']),flush=True)
out=dict(schema=1,exeSha256=sha(inputs.raw),regulationSha256=inputs.x['hashes']['regulation.bin'],paramSha256=sha(inputs.param),paramHashes=hashes,
 animationSha256=animations['bundles'][0]['sha256'],taeHashes={str(k):tracks[k]['sha256'] for k in {r['tae'] for r in spell_bindings}},
 behaviorSha256=b.metadata['bundleSha256'],scriptSha256=sha(script),effects=list(EFFECTS),root=root,leaf=leaf,tag=tag,rate=rate,duration=10,
 positiveAttacks=positives,tagSets=len(representatives),spellBindings=spell_bindings,behaviorBindings=bindings,
 scriptFunctions={name:sha(functions[name].encode()) for name in ('IsChargeMagic','MagicLoopRight_Upper_onUpdate','MagicLoopLeft_Upper_onUpdate')},checks=checks,
 native=dict(selection='4FEA30 → E6E150 → E6E3B0',animation='27D0F10 → 27D0400 → 40EB30 → 3953C0 → 384800 → E91FD0',hit='E6D530 → 505E90 → 50F230',defense='503800',poise='502270',lifecycle='50D060 → 5057D0 → 50ACD0'),
 stubs=sorted(stubs|{'explicit local actor/inventory and hit metadata; emitted hit results inserted into attacker container',
 'E926C0 actual Magic row; actor selected-spell virtual, hand/cost context and no weapon row',
 '4B1B90 available emitter; 4B2B60 no secondary actor; 484500 neutral notification mode',
 '383D20 terminal cast-request recorder after native category/reference selection, not actual bullet spawning',
 '3CED90/4D1B20 ordinary owner predicate; 3D74F0/B31990 notifications omitted',
 'TAE event activity and selected animation are explicit inputs; static pointer-checked graph/HKS binding, not a full behavior VM'}),
 limitations=['All tagged PC rows are tested as hit inputs, not assumed reachable actions.',
 'Sorcery and incantation examples use native cast selection and genuine charged/uncharged animation events; actual projectile collision and full HKS scheduling are not executed.',
 'The effect reduces poise damage to zero; this does not establish immunity to grabs or every forced reaction.',
 'Additional ailment damage-cut fields need separate consumer validation; no claim about ailment buildup.',
 'No full equipment rebuild, DLL hooks, death/reload, final HP writes or multiplayer session.'],gameplayVerified=False)
a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('PASS total',sum(map(len,checks.values())),flush=True)
