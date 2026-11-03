"""Compare selected PC native mutations in an isolated x64 emulator.

Only synthetic objects are passed to the native code. wcsncpy is replaced by a
bounded UTF-16 copy; deletion's normalization call is observed and suppressed
(the comparator is tested separately). No OS or game API is called.
Requires pefile, capstone, unicorn. Writes only the explicit output JSON.
"""
import argparse, hashlib, json, struct
from pathlib import Path
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_CODE, UC_HOOK_MEM_UNMAPPED
from unicorn.x86_const import UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8, UC_X86_REG_R9, UC_X86_REG_RSP, UC_X86_REG_RIP, UC_X86_REG_RAX

p=argparse.ArgumentParser(description=__doc__);p.add_argument('exe',type=Path);p.add_argument('output',type=Path);args=p.parse_args()
raw=args.exe.read_bytes();digest=hashlib.sha256(raw).hexdigest()
assert digest=='9545e8732919bb6a63904cb73223641b3c4f9a67869be5722612acca413e8b3a'
pe=pefile.PE(data=raw,fast_load=True);BASE=pe.OPTIONAL_HEADER.ImageBase
OBJ=0x10000000;STACK=0x20000000;STOP=0x30000000;NAME=OBJ+0x9000;HANDLES=OBJ+0xa000
md=Cs(CS_ARCH_X86,CS_MODE_64);md.detail=True

def run(start, data, args4, stackargs=()):
 u=Uc(UC_ARCH_X86,UC_MODE_64);u.mem_map(OBJ,0x20000);u.mem_map(STACK,0x10000);u.mem_map(STOP,0x1000)
 u.mem_write(OBJ,bytes(data));u.mem_write(NAME,'native'.encode('utf-16le')+b'\0\0');u.mem_write(HANDLES,struct.pack('<6I',0xc0800054,0,0,0,0,0))
 sp=STACK+0x8008;u.mem_write(sp,struct.pack('<Q',STOP))
 for i,v in enumerate(stackargs):u.mem_write(sp+0x28+i*8,struct.pack('<Q',v))
 for reg,v in zip([UC_X86_REG_RCX,UC_X86_REG_RDX,UC_X86_REG_R8,UC_X86_REG_R9],args4):u.reg_write(reg,v)
 u.reg_write(UC_X86_REG_RSP,sp);calls=[]
 def map_page(uc,access,address,size,value,user):
  page=address&~4095;rva=page-BASE
  if not 0<=rva<pe.OPTIONAL_HEADER.SizeOfImage:raise RuntimeError(f'Unexpected native access {address:x}')
  uc.mem_map(page,4096);uc.mem_write(page,pe.get_data(rva,4096).ljust(4096,b'\0'));return True
 def ret(uc):
  sp=uc.reg_read(UC_X86_REG_RSP);target=struct.unpack('<Q',uc.mem_read(sp,8))[0];uc.reg_write(UC_X86_REG_RSP,sp+8);uc.reg_write(UC_X86_REG_RIP,target)
 def code(uc,address,size,user):
  rva=address-BASE
  if rva==0x269cd04:
   calls.append('wcsncpy');dst=uc.reg_read(UC_X86_REG_RCX);src=uc.reg_read(UC_X86_REG_RDX);n=uc.reg_read(UC_X86_REG_R8);assert n==18
   value=bytes(uc.mem_read(src,n*2));z=next((i for i in range(0,len(value),2) if value[i:i+2]==b'\0\0'),len(value));uc.mem_write(dst,value[:z].ljust(n*2,b'\0'));uc.reg_write(UC_X86_REG_RAX,dst);ret(uc);return
  if rva==0x1e17a0:
   calls.append('normalize-counters');ret(uc);return
  ins=next(md.disasm(bytes(uc.mem_read(address,size)),address,count=1),None)
  if ins and ins.mnemonic=='call':
   target=ins.operands[0].imm-BASE if ins.operands[0].type==2 else None
   if target not in (0x269cd04,0x1e17a0):raise RuntimeError(f'Unexpected dependency at {rva:x}')
 u.hook_add(UC_HOOK_MEM_UNMAPPED,map_page);u.hook_add(UC_HOOK_CODE,code)
 u.emu_start(BASE+start,STOP,count=20000)
 assert u.reg_read(UC_X86_REG_RIP)==STOP,'Native routine did not return'
 return bytes(u.mem_read(OBJ,len(data))),calls

initial=bytearray(0x2000);struct.pack_into('<I',initial,0x1f78,100)
for i in range(100):struct.pack_into('<I',initial,0x30+i*80+44,0xffffffff)
for i,age in [(1,4),(3,1)]:
 q=0x30+i*80;initial[q]=1;initial[q+1]=7;initial[q+3]=age;struct.pack_into('<I',initial,q+44,19000);struct.pack_into('<Q',initial,q+72,134380000000000000+i)
# Keep opaque and stale fields nonzero to reveal exactly which bytes native mutates.
q=0x30;initial[q+2]=0xa4;initial[q+40:q+44]=b'ABCD'
created,create_calls=run(0x1e0010,initial,[OBJ,0,134380123456780000,19000],[HANDLES,7,NAME])
renamed,rename_calls=run(0x1dff30,created,[OBJ,0,NAME,0])
# Same-name rename is a no-op, including padding and timestamp.
assert renamed==created
removed,remove_calls=run(0x1dfeb0,created,[OBJ,0,0,0])
relic,_=run(0x6c0c10,bytes(72),[OBJ,0,0,0])
result={'executableSha256':digest,'stubs':['wcsncpy UTF-16 copy','normalization call observed, comparator analyzed separately'], 'relicBodyDefault':list(relic), 'presetCreate':{'input':list(initial[:0x30+400]),'output':list(created[:0x30+400]),'calls':create_calls},'presetDelete':{'input':list(created[:0x30+80]),'output':list(removed[:0x30+80]),'calls':remove_calls}}
args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,separators=(',',':'))+'\n');print(args.output)
