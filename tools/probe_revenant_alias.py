"""Bridge the Hotfix1 Revenant relic alias to the pinned family-controller proof.

Original equipment selection, passive-root reading, insertion and state lookup
execute. Inventory and allocation are explicit fixtures; the controller proof
is referenced by content hash, not reinterpreted from matching display names.
"""
import argparse
import json
import struct
from pathlib import Path
from native_effect_runtime import *

p = argparse.ArgumentParser(description=__doc__)
for name in ('exe', 'extracted', 'family_evidence', 'output'):
    p.add_argument(name, type=Path)
a = p.parse_args()
x = Inputs(a.exe, a.extracted)
raw = a.extracted.with_suffix('.AttachEffectParam.param').read_bytes()
rows = Inputs.table(raw, 0x44)
# Equipment identity/allocation fixture shared with probe_equipped_exclusivity.
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
   u.mem_write(instance+0x18,struct.pack('<3i',*(effects+[-1]*3)[:3]));u.mem_write(ptr,bytes(24));self.q(ptr+8,instance);u.mem_write(ptr+0x10,struct.pack('<I',0x80000000|2000100));ret(ptr)
  elif pc==0x69e5a0:ret()
  elif pc==0xe6e430:
   ptr=u.reg_read(UC_X86_REG_RCX);id=u.reg_read(UC_X86_REG_RDX)&0xffffffff
   if id in rows and id not in self.cache:
    self.cache[id]=OBJ+0x10000+len(self.cache)*0x100;u.mem_write(self.cache[id],rows[id])
   self.q(ptr,self.cache.get(id,0));u.mem_write(ptr+8,struct.pack('<I',id));ret(ptr)
  else:super().hook(u,address,size,user)
 def select(self):
  self.invoke(0x4fea30,[MAN,OUT]);bits=int.from_bytes(self.u.mem_read(BITS,20),'little');return [i for i in range(144) if bits>>i&1]


proof_bytes = a.family_evidence.read_bytes()
proof = json.loads(proof_bytes)
assert proof['exeSha256'] == sha(x.raw)
assert proof['regulationSha256'] == x.x['hashes']['regulation.bin']
assert proof['paramSha256'] == sha(x.param) and not proof['gameplayVerified']
assert proof['root'] == 7220310 and proof['effects'] == [7220210]
assert {k:len(v) for k,v in proof['checks'].items()} == dict(dispatch=18, controller=26, emission=6, repeat=15, mapping=6)
attaches = x.x['tables']['AttachEffectParam']
base, alias = attaches['7220210'], attaches['7220211']
differences = {k:[v,alias[k]] for k,v in base.items() if v != alias[k]}
assert differences == {'compatibilityId':[900,-1]}
root = proof['root']
assert base['passiveSpEffectId_1'] == alias['passiveSpEffectId_1'] == root
assert base['exclusivityId'] == alias['exclusivityId'] == -1
assert (x.spells[str(root)]['spCategory'], x.spells[str(root)]['stateInfo'], x.spells[str(root)]['effectEndurance']) == (20,2034,-1)
cases = [[],[7220210],[7220211],[7220210,7220211],[7220211,7220210],[7220211]*3]
checks=[];stubs=set()
for effects in cases:
    for hero in range(11):
        c=Selection([[effect] for effect in effects],hero)
        bits=c.select();roots=[]
        for index,effect in enumerate(effects):
            if index*6 in bits:
                c.invoke(0xe6e150,[OBJ+0x9200,effect])
                roots.append(c.invoke(0xe6e3b0,[OBJ+0x9200,0])&0xffffffff)
        assert roots == ([root]*len(effects) if hero in (0,6) else [])
        stubs.update(c.stubs)
        chain=Chain(x)
        for selected in roots:chain.insert(selected)
        chain.qualify();chain.update(0)
        active=bool(chain.invoke(0x508e20,[OBJ,2034])&255)
        assert len(chain.nodes()) == int(bool(roots)) and active == bool(roots)
        checks.append(dict(effects=effects,hero=hero,roots=roots,nodes=chain.nodes(),stateActive=active))
        stubs.update(chain.stubs)
output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),
            attachParamSha256=sha(raw),familyEvidenceSha256=sha(proof_bytes),effects=[7220210,7220211],root=root,state=2034,
            parameterDifferences=differences,checks=checks,
            native=dict(selection='4FEA30 → E6E150 → E6E3B0',lifecycle='50D060 → 5057D0 → 50ACD0',state='508E20'),
            stubs=sorted(stubs|{'inventory and allocation use Selection fixture; hero0 accepted control is not assigned a character name',
                               'selected roots enter isolated effect container; full equipment lifecycle not executed',
                               'family controller/animation evidence reused by exact content hash; no gameplay, AI or multiplayer execution'}),
            gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',len(checks),'native alias selection/root/state checks')
