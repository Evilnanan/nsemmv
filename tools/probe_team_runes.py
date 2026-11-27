"""Verify shared rune relic construction, party ownership, native rebuild and rune awards.

Original native instructions execute with explicit inventory/party, allocator and
transport fixtures. This is not a live gameplay or multiplayer observation.
"""
import argparse,itertools,json,math,struct
from pathlib import Path
from native_effect_runtime import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted)
raw=a.extracted.with_suffix('.AttachEffectParam.param').read_bytes();rows=Inputs.table(raw,0x44)
anti_raw=a.extracted.with_suffix('.EquipParamAntique.param').read_bytes();anti=Inputs.table(anti_raw,0x30)
hashes={'AttachEffectParam':sha(raw),'EquipParamAntique':sha(anti_raw)}
assert hashes=={'AttachEffectParam':'ae8128ed510a532d0fa7cb56fa9c86e4a44c9d815dd4ee01c05821d5f50a9827','EquipParamAntique':'abc2930b67cfb79c71a0672654cdd9cd4adf45437791743c95a7cbd531886269'}
assert sha(x.param)=='07ec636c5565d4551efeb53e6f08bc633b2aa4f2129f13c61b0638d69b1bc176'
for table,blob in ((rows,raw),(anti,anti_raw)):
 assert len(table)==struct.unpack_from('<H',blob,10)[0]
att=x.x['tables']['AttachEffectParam']['7110000'];root=x.spells['7110000']
assert [att['passiveSpEffectId_'+str(i)] for i in (1,2,3)]==[7110000,-1,-1] and att['exclusivityId']==-1
assert all(v==1 for k,v in att.items() if k.startswith('allow'))
assert (root['spCategory'],root['stateInfo'],root['effectEndurance'])==(10,76,-1)
assert math.isclose(root['soulRate'],1.035,rel_tol=1e-7)
assert x.rows[7110000][0x352]&0x20 and all(not x.rows[id][0x352]&0x20 for id in (311100,6840000))
vtable=0x2c307f8
assert struct.unpack('<Q',x.pe.get_data(vtable+0x5d0,8))[0]==BASE+0x668300
# Use original relic-manager virtual methods, including the nonzero handle predicate.
manager_vtable=0x2c1ab28
methods={0x30:0x4ff2e0,0x38:0x4ff7c0,0x58:0x4ff6d0,0x60:0x4ff7b0,0x68:0x4ff500,0x70:0x50ebd0,0x78:0x50ebc0}
for off,rva in methods.items():assert struct.unpack('<Q',x.pe.get_data(manager_vtable+off,8))[0]==BASE+rva
by_id={id:{'category':x.spells[str(id)]['spCategory']} for id in (7110000,311100,6840000)}
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

class Rune(Chain):
 def __init__(self,roots,disabled=False,player=True,purse=True):
  super().__init__(x);self.player=player;self.writes=[]
  self.q(OBJ+0x6190,OBJ);self.q(OBJ+0x65a0,OBJ+0xc000 if purse else 0)
  self.q(OBJ+0x6000,BASE+vtable)
  for id in roots:self.insert(id)
  self.qualify();self.update(0)
  if disabled:
   node=struct.unpack('<Q',self.u.mem_read(OBJ+8,8))[0]
   while node:
    self.u.mem_write(node+0x68,struct.pack('<I',0x800c0003))
    node=struct.unpack('<Q',self.u.mem_read(node+0x38,8))[0]
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v&0xffffffffffffffff);sp=u.reg_read(UC_X86_REG_RSP)
   u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if pc==0x3d4180:
   self.stubs.add('3D4180 explicit player identity');ret(int(self.player))
  elif pc==0x2098c0:
   assert u.reg_read(UC_X86_REG_RCX)==OBJ+0xc000
   self.writes.append(struct.unpack('<i',struct.pack('<I',u.reg_read(UC_X86_REG_RDX)&0xffffffff))[0])
   self.stubs.add('2098C0 terminal rune-resource write recorder; caps and persistence not executed');ret(1)
  elif pc==0x6713f8:
   self.stubs.add('6713D6..6713F8 isolated original fixed-rune packet block boundary');u.reg_write(UC_X86_REG_RIP,STOP)
  else:super().hook(u,address,size,user)
 def rate(self):
  self.invoke(0x508510,[OBJ]);return struct.unpack('<f',(self.u.reg_read(UC_X86_REG_XMM0)&0xffffffff).to_bytes(4,'little'))[0]
 def award(self,base,scale):
  self.writes=[];self.invoke(0x668300,[OBJ+0x6000,base,scale]);return self.writes.copy()
 def fixed(self):
  self.writes=[];self.u.reg_write(UC_X86_REG_RDI,OBJ+0x6000)
  self.invoke(0x6713d6,[]);return self.writes.copy()

def f32(v):return struct.unpack('<f',struct.pack('<f',v))[0]
def actual_roots(roots):
 out=[]
 for id in roots:
  if by_id.get(id,{}).get('category')==0 and id in out:continue
  out.append(id)
 return out
def expected(roots):
 v=1.
 for id in actual_roots(roots):v=f32(v*x.spells[str(id)]['soulRate'])
 return v

class Export(Selection):
 def __init__(self,slots,remote):super().__init__(slots);self.remote=remote
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if pc==0x69e570:
   ptr=u.reg_read(UC_X86_REG_RCX);instance=OBJ+0xa000
   u.mem_write(instance+0x18,struct.pack('<6i',*(self.slots[0]+[-1]*6)[:6]));u.mem_write(ptr,bytes(24));self.q(ptr+8,instance);u.mem_write(ptr+0x10,struct.pack('<I',0x80000000|2000100));u.mem_write(instance+0x58,bytes([self.remote]));ret(ptr);return
  if pc==0xe6e430:
   ptr=u.reg_read(UC_X86_REG_RCX);id=u.reg_read(UC_X86_REG_RDX)&0xffffffff
   if id in rows and id not in self.cache:
    self.cache[id]=OBJ+0x18000+len(self.cache)*0x100;u.mem_write(self.cache[id],rows[id])
   self.q(ptr,self.cache.get(id,0));u.mem_write(ptr+8,struct.pack('<I',id));ret(ptr);return
  if pc==0x1dd930:
   v=u.reg_read(UC_X86_REG_RCX);item=bytes(u.mem_read(u.reg_read(UC_X86_REG_R8),4));p=OBJ+0xb000
   self.q(v+8,p);self.q(v+0x10,p+4);self.q(v+0x18,p+0x100);u.mem_write(p,item)
   u.reg_write(UC_X86_REG_RAX,0);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8);return
  super().hook(u,address,size,user)
 def export(self,index=0):
  self.invoke(0x4ff520,[MAN,OUT,0x40000001,index]);start,end=struct.unpack('<QQ',self.u.mem_read(OUT+8,16));return list(struct.unpack('<'+'i'*((end-start)//4),self.u.mem_read(start,end-start))) if start else []
INV=OBJ+0x40000;PAY=OBJ+0x65000
class Construct(Export):
 def __init__(self):
  super().__init__([[7110000]],0);self.u.mem_map(INV,0x40000);self.instances=[];self.created=[];self.ring=0
  for rva,v in [(0x3c131c8,INV),(0x3c2d9c0,OBJ+0x7000),(0x3c078d0,OBJ+0x68000)]:
   self.mapped(self.u,0,BASE+rva,8,0,None) if not any(lo<=BASE+rva<=hi for lo,hi,_ in self.u.mem_regions()) else None
   self.q(BASE+rva,v)
  self.q(OBJ+0x68008,OBJ+0x68100);self.u.mem_write(OBJ+0x68108,struct.pack('<I',42))
  for i in range(24):
   self.u.mem_write(INV+0x14008+i*4,struct.pack('<I',i+1));self.u.mem_write(INV+0xa008+(i+1)*8,struct.pack('<II',0x800000+i+1,0))
  self.u.mem_write(INV+0x19008,struct.pack('<II',0,24))
 def hook(self,u,address,size,user):
  pc=address-BASE;rcx=u.reg_read(UC_X86_REG_RCX);rdx=u.reg_read(UC_X86_REG_RDX)
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if pc==0x214e8d0 and rcx==0xf8:
   v=OBJ+0x70000+len(self.instances)*0x100;self.instances.append(v);ret(v);return
  if pc==0xe6c4d0:
   if rdx in anti:u.mem_write(OBJ+0x69000,anti[rdx])
   u.mem_write(rcx,struct.pack('<IIQ',rdx&0xffffffff,0,OBJ+0x69000 if rdx in anti else 0));ret(rcx);return
  if pc==0xf8b630:ret(0);return
  if pc in (0x6c1e60,0x6c1cf0):u.mem_write(rcx,bytes(u.mem_read(rdx,4)));ret(rcx);return
  if pc==0x6c1c80:ret();return
  if pc==0x69e570:
   h=struct.unpack('<I',u.mem_read(rdx,4))[0];i=h&0x7fffff;v=struct.unpack('<Q',u.mem_read(INV+8+i*8,8))[0];u.mem_write(rcx,struct.pack('<I4xQI',h,v,struct.unpack('<I',u.mem_read(v+0xc,4))[0]));ret(rcx);return
  if pc==0x6a1570:
   h=struct.unpack('<I',u.mem_read(rcx,4))[0];i=h&0x7fffff;v=struct.unpack('<Q',u.mem_read(INV+8+i*8,8))[0];self.q(rcx+8,v);u.mem_write(rcx+0x10,bytes(u.mem_read(v+0xc,4)));ret();return
  if pc==0x26909a0:ret(u.reg_read(UC_X86_REG_RAX));return
  if pc==0x69fed0:self.created.append(dict(flag=u.reg_read(UC_X86_REG_R9)&255,payload=bytes(u.mem_read(u.reg_read(UC_X86_REG_R8),72)).hex()))
  super().hook(u,address,size,user)

class Connected(Construct):
 def __init__(self):
  super().__init__();self.vectors={};self.tree=OBJ+0x66000;self.sentinel=self.tree+0x100;self.q(self.tree+8,self.sentinel)
  self.u.mem_write(self.sentinel+0x19,b'\1');self.u.mem_write(OBJ+0x68108,struct.pack('<I',1))
  self.party_nodes=[self.tree+0x200+i*0x300 for i in range(3)]
  self.q(self.sentinel+8,self.party_nodes[1])
  for i,node in enumerate(self.party_nodes):
   for off in (0,8,0x10):self.q(node+off,self.sentinel)
   self.u.mem_write(node+0x20,struct.pack('<I',i+1))
  self.q(self.party_nodes[1],self.party_nodes[0]);self.q(self.party_nodes[1]+0x10,self.party_nodes[2])
  self.q(MAN+0x10,OBJ);self.q(OBJ+0x6190,OBJ);self.u.mem_write(MAN+0x20,struct.pack('<I',24));self.q(MAN+0x48,BITS)
  self.q(MAN+0x30,self.tree);self.u.mem_write(MAN+0x38,b'\1');self.q(OBJ+0x8158,BASE+0x4ff6d0);self.q(OBJ+0x8168,STOP+0x904)
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if address==STOP+0x904:ret();return
  if address==STOP+0x902:
   h=u.reg_read(UC_X86_REG_RDX);ret(int((h&0xff800000)==0xc0800000 and 1<=h&0x7fffff<=len(self.instances)));return
  if pc==0x1dd930:
   v=u.reg_read(UC_X86_REG_RCX);item=bytes(u.mem_read(u.reg_read(UC_X86_REG_R8),4))
   if v not in self.vectors:self.vectors[v]=OBJ+0xd000+len(self.vectors)*0x400
   p=self.vectors[v];self.q(v+8,p);self.q(v+0x10,p+4);self.q(v+0x18,p+0x400);u.mem_write(p,item);ret();return
  super().hook(u,address,size,user)
 def setup(self,counts,mixed=True):
  for i,count in enumerate(counts):
   key=OBJ+0x64f00;self.u.mem_write(key,struct.pack('<I',i+1))
   for j in range(6):
    self.invoke(0x6c0c10,[PAY+j*72])
    if j<count:
     self.u.mem_write(PAY+j*72,struct.pack('<II3i',0x80000000|2000100,1,7110000,311100 if mixed else -1,-1));self.u.mem_write(PAY+j*72+0x30,struct.pack('<3i',6840000 if mixed else -1,-1,-1))
   self.invoke(0x1dd0e0,[self.tree,key,PAY])
 def collect(self):
  chosen=self.select();out=OBJ+0xc000;self.q(out,OBJ+0x7000);self.invoke(0x4feeb0,[MAN,out]);start,end=struct.unpack('<QQ',self.u.mem_read(out+8,16));v=list(struct.unpack('<'+'i'*((end-start)//4),self.u.mem_read(start,end-start))) if start else []
  return dict(chosen=chosen,roots=v)
class Rebuild(Connected):
 def __init__(self):
  super().__init__();self.grants=[];self.refs=[];self.writes=[];self.q(OBJ+0x65a0,OBJ+0xb800);self.q(MAN+0x18,OBJ+0xa000)
  for off,rva in ((0x60,0x4ff7b0),(0x68,0x4ff500),(0x30,0x4ff2e0),(0x38,0x4ff7c0),(0x70,0x50ebd0),(0x78,0x50ebc0)):
   self.q(OBJ+0x8100+off,BASE+rva)
  self.stubs.update({'Temporary relic inventory/free ring and balanced three-owner tree are explicit inputs; original instance construction and owner comparison execute.',
   '6C1E60/6C1CF0 handle copies, 6C1C80/69FA70/69FAF0 reference lifetime sinks; native manager handle replacement executes.',
   '69E570/6A1570 resolve actual allocated instance handles; E6C4D0/E6E430 return pinned parameter rows.',
   '1DD930 vector allocation and 2081B0 bit-vector allocation are fixtures; native list selection/copy/removal execute.',
   'Explicit local player, grant mode 7 and no peer; notification transport/timestamp sinks are fixtures.',
   'Recipient virtual +238 is false; old party handles remain allocated while supplied equipped handle lists change.',
   '2098C0 records final rune write requests; purse caps and persistence do not execute.'})
  self.q(OBJ+0x6438,STOP+0x302)
  self.q(OBJ+0x6210,STOP+0x300);self.q(OBJ+0x6790,STOP+0x301)
  for off in (0x118,0x120,0x130,0x150):self.q(OBJ+0x6200+off,STOP+0x302)
  self.q(OBJ+0x61b8,OBJ+0xf000);self.q(OBJ+0xf008,OBJ+0xf400)
  self.globalq(0x3c84d4+7+0x384b2c5,OBJ+0x5c000)
  self.globalq(0x3c21ec8,OBJ+0x5c100);self.u.mem_write(OBJ+0x5c110,struct.pack('<i',7))
  self.globalq(0x3c0f0a8,OBJ+0x80000);self.u.mem_map(OBJ+0x80000,0x20000);self.q(OBJ+0x974e8,OBJ+0x6000)
 def globalq(self,rva,value):
  try:self.u.mem_read(BASE+rva,8)
  except:self.mapped(self.u,0,BASE+rva,8,0,None)
  self.q(BASE+rva,value)
 def hook(self,u,address,size,user):
  pc=address-BASE
  def ret(v=0):
   u.reg_write(UC_X86_REG_RAX,v&0xffffffffffffffff);sp=u.reg_read(UC_X86_REG_RSP);u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
  if address in (STOP+0x300,STOP+0x301,STOP+0x302):ret({STOP+0x300:1,STOP+0x301:OBJ+0x5c200,STOP+0x302:0}[address]);return
  if pc==0x2081b0:
   ptr=u.reg_read(UC_X86_REG_RCX);assert u.reg_read(UC_X86_REG_R9)==144
   target=OBJ+0x9500;self.q(ptr+8,target);self.q(ptr+0x10,144);self.q(ptr+0x18,160);self.q(ptr+0x20,144);u.mem_write(target,bytes(20));ret(ptr);return
  if pc==0x2098c0:
   assert u.reg_read(UC_X86_REG_RCX)==OBJ+0xb800
   self.writes.append(u.reg_read(UC_X86_REG_RDX)&0xffffffff);ret(1);return
  if pc==0x3c8a40:self.grants.append(u.reg_read(UC_X86_REG_RDX)&0xffffffff)
  if pc in (0x69fa70,0x69faf0):self.refs.append(pc);ret();return
  if pc in (0x3d3390,0x732800,0x51b920,0x6af640,0x4e78a0,0x4e78c0,0xdf24d0):ret();return
  if pc==0x3d4180:ret(1);return
  if pc==0xea0ca0:ret(-1);return
  if pc in (0x2167950,0x21674e0,0x2167a40):
   self.q(OBJ+0x5c300,100);ret(OBJ+0x5c300 if pc==0x2167950 else 1 if pc==0x2167a40 else 0);return
  super().hook(u,address,size,user)
 def rebuild(self):
  self.grants=[];self.invoke(0x4ff1b0,[MAN],instruction_limit=2000000);self.qualify();self.update(0)
  chosen=[i for i in range(144) if int.from_bytes(self.u.mem_read(BITS,20),'little')>>i&1]
  return dict(chosen=chosen,grants=self.grants,nodes=self.nodes())
 def rate(self):
  self.invoke(0x508510,[OBJ]);return struct.unpack('<f',(self.u.reg_read(UC_X86_REG_XMM0)&0xffffffff).to_bytes(4,'little'))[0]
 def award(self,base,scale):
  self.writes=[];self.invoke(0x668300,[OBJ+0x6000,base,scale]);return self.writes.copy()
 def counts(self,counts):
  for node,handles,count in zip(self.party_nodes,self.saved,counts):
   self.u.mem_write(node+0x1e0,struct.pack('<6I',*(handles[:count]+[0]*(6-count))))
 def save_handles(self):self.saved=[list(struct.unpack('<6I',self.u.mem_read(node+0x1e0,24))) for node in self.party_nodes]

checks={k:[] for k in ('local','shared','rebuild','disabled','fixed')};stubs=set()
def record(key,c,**row):checks[key].append(row);stubs.update(c.stubs)
for copies,extra,count in itertools.product(range(7),(None,311100,6840000),(0,1,3)):
 if extra is None and count:continue
 roots=[7110000]*copies+([extra]*count if extra else []);c=Rune(roots);rate=c.rate()
 assert rate==expected(roots) and [n['id'] for n in c.nodes()]==actual_roots(roots)
 record('local',c,copies=copies,extra=extra,count=count,rate=rate,nodes=c.nodes())
print('PASS local',len(checks['local']),flush=True)
for recipient,mixed in itertools.product((1,2,3),(False,True)):
 c=Rebuild();c.u.mem_write(OBJ+0x68108,struct.pack('<I',recipient));c.setup((6,6,6),mixed);c.save_handles()
 flags=[c.u.mem_read(v+0x58,1)[0] for v in c.instances]
 assert flags==[int(owner!=recipient) for owner in (1,2,3) for _ in range(6)]
 assert all(c.u.mem_read(v+0xf0,1)[0]==1 and struct.unpack('<i',c.u.mem_read(v+0xa8,4))[0]==7110000 for v in c.instances)
 record('shared',c,recipient=recipient,mixed=mixed,flags=flags,createdFlags=[v['flag'] for v in c.created],handles=c.saved)
 for counts in ((1,0,0),(1,0,0),(0,1,0),(1,1,1),(1,1,1),(3,0,0),(0,3,3),(6,6,6),(6,6,6),(0,0,0),(0,0,0),(1,1,1)):
  c.counts(counts);r=c.rebuild();rate=c.rate();ids=[n['id'] for n in c.nodes()];own=counts[recipient-1] if mixed else 0
  assert ids.count(7110000)==sum(counts) and ids.count(311100)==int(own>0) and ids.count(6840000)==own,(counts,ids)
  assert rate==expected(ids)
  assert r['grants'].count(7110000)==sum(counts) and r['grants'].count(311100)==own and r['grants'].count(6840000)==own
  awards=[]
  for base,scale in itertools.product((1,100,101,999,10000),(0,1)):
   result=c.award(base,scale);assert result==[int(f32(f32(base)*rate)) if scale else base]
   awards.append(dict(base=base,scale=scale,values=result))
  record('rebuild',c,recipient=recipient,mixed=mixed,counts=counts,rate=rate,awards=awards,**r)
 print('PASS party construction/rebuild',recipient,mixed,flush=True)
for mask in (1,2,0x40000,0x80000000):
 c=Rune([7110000]*3);assert c.rate()>1
 node=struct.unpack('<Q',c.u.mem_read(OBJ+8,8))[0]
 while node:
  flags=struct.unpack('<I',c.u.mem_read(node+0x68,4))[0];c.u.mem_write(node+0x68,struct.pack('<I',flags|mask));node=struct.unpack('<Q',c.u.mem_read(node+0x38,8))[0]
 assert c.rate()==1;record('disabled',c,mask=mask,rate=c.rate())
for copies,packets in itertools.product((0,1,3,6),([7031901],[7036501],[7031901,7036501])):
 c=Rune([7110000]*copies+([7031900] if 7031901 in packets else []))
 for packet in packets:c.insert(packet)
 c.qualify();c.update(0);result=c.fixed();assert result==[sum(x.spells[str(id)]['soul'] for id in packets)]
 record('fixed',c,copies=copies,packets=packets,values=result)
print('PASS counts',{k:len(v) for k,v in checks.items()},sum(map(len,checks.values())),flush=True)
out=dict(schema=1,effect=7110000,root=7110000,multiplier=root['soulRate'],exeSha256=sha(x.raw),
 regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),paramHashes=hashes,checks=checks,
 native=dict(owner='1DD0E0 → 1DD590',construct='69FED0 → 69E680 / 6A1720 → 69E640 / 69E990 → 69E9C0',
 shared='69E630 + instance[58] → 4FF520 / SpEffect[352]&20',lookup='4FF6D0 → 1DCDA0',selection='4FF960 → 4FEA30',
 rebuild='4FF1B0 → 50EAC0 → 4FF7C0 / 50EC60 → 4FF2E0',remove='504E80',grant='50EBC0 → 50EBD0 → 3C8A40 → 3C80A0 → 3DB410',
 insert='50D060',qualify='5057D0',update='50ACD0',rate='508510',award='668300 → 2098C0',fixed='6713D6..6713F8'),
 stubs=sorted(stubs),limitations=['Party data and subsequent handle lists are explicit input, not live multiplayer transport or save/equipment editing.',
 'Only the shared party-manager mode is executed. Full manager creation, coexisting local-only manager scheduling, death, session changes, reload and DLL hooks are not simulated.',
 'Rune award scaling flag is supplied; complete scene reward sources, terminal purse caps and persistence are not executed.',
 'Six input relics per owner are native equipment fixtures, not claims about relic draw legality or a tested maximum for all possible effect arrangements.'],gameplayVerified=False)
a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
