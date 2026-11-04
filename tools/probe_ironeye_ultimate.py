"""Trace Ironeye charged ultimate selection and poison with original instructions.

HKS control flow, TAE relocation/dispatch, passive replacement and recipient
status/timer/HP consumers execute with explicit actor and input fixtures.
Child-projectile inheritance and complete collision are not simulated.
"""
import argparse
import ctypes
import ctypes.util
import itertools
import json
import math
import struct
from pathlib import Path
from native_effect_runtime import BASE, OBJ, STOP, Chain, Inputs, sha
from native_ailment_runtime import Ailment
from native_animation_runtime import NativeTae
from effect_behavior_graph import BehaviorGraph
from unicorn.x86_const import *
p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','assets','animations','script','behavior','output'):p.add_argument(name,type=Path)
a=p.parse_args();x=Inputs(a.exe,a.extracted)
assets=json.loads(a.assets.read_text());animations=json.loads(a.animations.read_text())
assert assets['hashes']['regulation.bin']==x.x['hashes']['regulation.bin']
behaviorraw=a.extracted.with_suffix('.BehaviorParam_PC.param').read_bytes();behaviors=Inputs.table(behaviorraw,0x30)
bulletraw=a.extracted.with_suffix('.Bullet.param').read_bytes();bullets=Inputs.table(bulletraw,0x100)
attackraw=a.extracted.with_suffix('.AtkParam_Pc.param').read_bytes()
weaponraw=a.assets.with_suffix('.EquipParamWeapon.param').read_bytes();weapons=Inputs.table(weaponraw,0x298)
tae=next(t for b in animations['bundles'] for t in b['taes'] if t['ID']==2902)
taeraw=Path(str(a.animations)+'.2902.tae').read_bytes();assert sha(taeraw)==tae['sha256']
raw_script=a.script.read_bytes()
assert sha(raw_script)=='786f8a7bc89452d9531e2299b224c8945701c422437eca9aacbeb10a57a17f4d'
source=raw_script.decode('utf-8-sig').replace('\r\n','\n')
start=source.index('function LongBowSnipeStart_onUpdate()');function=source[start:source.index('\nfunction ',start+1)]
graph=BehaviorGraph(a.behavior)
paths=[graph.state(name) for name in ('LongBowSnipeStart','LongBowSnipeCancelEarly')]
assert [p['animation'] for p in paths]==['a902_620000','a902_620005']
root,marker,leaf=7034600,7034601,7034602
r=x.spells[str(root)];m=x.spells[str(marker)];b=x.spells['7010601'];poison=x.spells[str(leaf)]
assert r['spCategory']==20 and r['effectEndurance']==-1 and r['cycleOccurrenceSpEffectId']==marker
assert math.isclose(r['motionInterval'],.1,rel_tol=1e-6)
assert m['spCategory']==b['spCategory']==202 and m['categoryPriority']==b['categoryPriority']==25
assert m['stateInfo']==2258 and b['stateInfo']==2025
assert poison['stateInfo']==2 and poison['spCategory']==10004 and poison['poizonAttackPower']==300
assert poison['effectEndurance']==40 and math.isclose(poison['motionInterval'],1.3,rel_tol=1e-6)
assert poison['changeHpPoint']==10 and math.isclose(poison['changeHpRate'],.1,rel_tol=1e-6)
assert poison['cycleOccurrenceSpEffectId']==505
assert x.spells['505']['changeHpPoint']==x.spells['505']['changeHpRate']==0
assert not any(s['stateInfo']==2024 for s in x.spells.values())
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

class Dispatch(Chain):
    def __init__(self):
        super().__init__(x)
        self.requests, self.emissions, self.frame = [], [], 0
        # Real Behavior resolver at +328; the other virtuals supply a synthetic
        # equipped weapon / owner identity. No state predicate is substituted.
        for off, ptr in [(0x118, STOP + 0x201), (0x190, STOP + 0x200), (0x260, STOP + 0x200),
                         (0x328, BASE + 0x668b30), (0x320, STOP + 0x201),
                         (0x250, STOP + 0x202), (0x28, STOP + 0x201), (0x178, STOP + 0x200)]:
            self.q(OBJ + 0x6200 + off, ptr)
        self.q(OBJ + 0x6190, OBJ)

    def hook(self, u, address, size, user):
        pc = address - BASE
        def finish(value=0):
            u.reg_write(UC_X86_REG_RAX, value)
            sp = u.reg_read(UC_X86_REG_RSP)
            u.reg_write(UC_X86_REG_RIP, struct.unpack('<Q', u.mem_read(sp, 8))[0])
            u.reg_write(UC_X86_REG_RSP, sp + 8)
        if address in (STOP + 0x200, STOP + 0x201, STOP + 0x202):
            self.stubs.add('synthetic player virtuals and equipped weapon 1000')
            finish({STOP + 0x200: 0, STOP + 0x201: 1, STOP + 0x202: 1000}[address])
        elif pc in (0x4d1b20, 0x3d4180, 0x3d4c10, 0xea9a60, 0xea76f0, 0x66b2d0, 0x27d0640):
            self.stubs.add(hex(pc) + ' isolated actor context / hand identity / empty animation reference list')
            finish()
        elif pc == 0x3ced90:
            self.stubs.add('3CED90 isolated actor context')
            finish(OBJ + 0xd000)
        elif pc == 0xea7fc0:
            self.stubs.add('EA7FC0 actual equipped-weapon row lookup')
            id = u.reg_read(UC_X86_REG_RDX) & 0xffffffff
            u.mem_write(OBJ + 0xb000, weapons[id])
            u.mem_write(u.reg_read(UC_X86_REG_RCX), struct.pack('<IIQ', id, 0, OBJ + 0xb000))
            finish()
        elif pc == 0xe6fcb0:
            self.stubs.add('E6FCB0 actual Behavior row lookup')
            id = u.reg_read(UC_X86_REG_RDX) & 0xffffffff
            assert id in (700000100,700000105,700000140,700000145)
            u.mem_write(OBJ + 0xb800, behaviors[id])
            self.q(u.reg_read(UC_X86_REG_RCX) + 8, OBJ + 0xb800)
            finish()
        elif pc == 0x3975d0:
            self.stubs.add('3975D0 Behavior request recorder; active/stop and conditional-state gates are native')
            payload = bytes(u.mem_read(u.reg_read(UC_X86_REG_R9), 18))
            self.requests.append(dict(behavior=u.reg_read(UC_X86_REG_RDX),
                                      active=bool(payload[16]), instant=bool(payload[17]), payload=payload.hex()))
            finish(1)
        else:
            super().hook(u, address, size, user)

lua=ctypes.CDLL(ctypes.util.find_library('lua5.4'))
lua.luaL_newstate.restype=ctypes.c_void_p
lua.luaL_openlibs.argtypes=[ctypes.c_void_p]
lua.luaL_loadstring.argtypes=[ctypes.c_void_p,ctypes.c_char_p]
lua.lua_pcallk.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_ssize_t,ctypes.c_void_p]
lua.lua_tolstring.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.POINTER(ctypes.c_size_t)]
lua.lua_tolstring.restype=ctypes.c_char_p
lua.lua_close.argtypes=[ctypes.c_void_p]
def script_case(r2,ultimate,window,interrupt,ended):
    program='''
TRUE=1; FALSE=0; g_ComboReset=0; events={}
ActionDurationAlternate=1; ActionDuration=2; GetSpEffectID=3; IsAnimEnd=4
ACTION_ARM_R2=10; ACTION_ARM_ULTRA=11
function act(...) end
function IsEnableSpecialAttack(...) return FALSE end
function SetSkillGeneratorTransitionIndex(...) end
function AttackCommonFunction(...) return %d end
function ExecEventAllBody(name) table.insert(events,name) end
function env(kind,id)
 if kind==ActionDurationAlternate and id==ACTION_ARM_R2 then return %d end
 if kind==ActionDuration and id==ACTION_ARM_ULTRA then return %d end
 if kind==GetSpEffectID and id==100285 then return %d end
 if kind==IsAnimEnd then return %d end
 return 0
end
'''%(interrupt,r2,ultimate,window,ended)
    program+=function+'\nLongBowSnipeStart_onUpdate(); return table.concat(events,",")'
    state=lua.luaL_newstate()
    try:
        lua.luaL_openlibs(state);assert lua.luaL_loadstring(state,program.encode())==0
        status=lua.lua_pcallk(state,0,1,0,0,None);result=lua.lua_tolstring(state,-1,None)
        assert status==0,result
        return result.decode()
    finally:lua.lua_close(state)

checks=dict(script=[],selection=[],dispatch=[],onset=[],damage=[],repeat=[],lifetime=[]);stubs=set()
def record(key,c,**row):checks[key].append(row);stubs.update(c.stubs)
def step(c,fps):c.qualify();c.update(1/fps)
for r2,ultimate,window,interrupt,ended in itertools.product((0,1),repeat=5):
    result=script_case(r2,ultimate,window,interrupt,ended)
    expected='' if interrupt else 'W_LongBowSnipeCancelEarly' if not r2 and not ultimate and window else 'W_Idle' if ended else ''
    assert result==expected
    checks['script'].append(dict(r2=r2,ultimate=ultimate,releaseWindow=window,interrupt=interrupt,ended=ended,result=result))
events=[];release=[];reset=[]
for an in tae['animations']:
    if an['ID'] not in (620000,620005):continue
    for e in an['events']:
        raw=bytes.fromhex(e['hex'])
        if e['Type']==2 and struct.unpack_from('<i',raw,8)[0] in (7100,7105,7130,7131,7140,7145):
            events.append(dict(animation=an['ID'],**e))
        if e['Type']==66 and struct.unpack_from('<i',raw)[0]==100285:release.append(dict(animation=an['ID'],**e))
        if e['Type']==67 and struct.unpack_from('<i',raw)[0]==7010601:reset.append(dict(animation=an['ID'],**e))
assert len(events)==8 and len(release)==1 and len(reset)==1
assert reset[0]['animation']==620000 and reset[0]['StartTime']==0
assert release[0]['animation']==620000 and math.isclose(release[0]['StartTime'],55/30,abs_tol=1e-6)
for copies,fps in itertools.product(range(4),(30,60,120)):
    c=Actor()
    for _ in range(copies):c.grant(root)
    for _ in range(fps//2):step(c,fps)
    c.grant(7010601)
    for _ in range(round(fps*86/30)):step(c,fps)
    states={id:bool(c.invoke(0x508e20,[OBJ,id])&255) for id in (2025,2258)}
    assert states=={2025:not copies,2258:bool(copies)}
    assert sum(n['id']==root for n in c.nodes())==bool(copies)
    record('selection',c,copies=copies,fps=fps,states=states,nodes=c.nodes())
for animation,state,active in itertools.product((620000,620005),(0,2025,2258),(0,1)):
    c=Dispatch();loader=NativeTae(c,taeraw,tae['sha256']);assert loader.id==2902 and loader.bank==255
    if state:c.insert(marker if state==2258 else 7010601)
    c.qualify();c.update(0)
    ctx=OBJ+0xd100;c.u.mem_write(ctx,bytes(0x40));seen=[]
    for _ in range(1000):
        if not c.invoke(0x27d0400,[loader.animations[animation],ctx]):break
        if struct.unpack('<I',c.u.mem_read(ctx,4))[0]!=2:continue
        payload=struct.unpack('<Q',c.u.mem_read(ctx+8,8))[0];raw=bytes(c.u.mem_read(payload,32))
        judge=struct.unpack_from('<i',raw,8)[0]
        if judge not in (7100,7105,7130,7131,7140,7145):continue
        seen.append(judge);c.q(OBJ+0x8018,OBJ+0x6000);c.u.mem_write(ctx+0x18,bytes([active]))
        c.invoke(0x40cd80,[OBJ+0x8000,ctx])
    assert len(seen)==(6 if animation==620000 else 2)
    expected=[] if not active or animation==620000 and not state else [700000100,700000105] if animation==620005 or state==2025 else [700000140,700000145]
    assert sorted(r['behavior'] for r in c.requests)==expected,(animation,state,active,c.requests)
    record('dispatch',c,animation=animation,state=state,active=active,requests=c.requests)
bindings=[]
for behavior,bullet in ((700000140,30902210),(700000145,30902215)):
    br=x.x['tables']['BehaviorParam_PC'][str(behavior)];bu=x.x['tables']['Bullet'][str(bullet)]
    assert br['refType']==1 and br['refId']==bullet
    child=bu['HitBulletID'];ch=x.x['tables']['Bullet'][str(child)]
    attack=x.x['tables']['AtkParam_Pc'][str(bu['atkId_Bullet'])]
    if bullet==30902210:
        assert bu['spEffectId0']==leaf and struct.unpack_from('<i',bullets[bullet],0x6c)[0]==leaf
        assert all(attack[k]==100 for k in ('spEffectAtkPowerCorrectRate_byDmg','spEffectAtkPowerCorrectRate_byPoint','spEffectAtkPowerCorrectRate_byRate'))
    else:assert all(bu['spEffectId'+str(i)]==0 for i in range(5))
    assert all(ch['spEffectId'+str(i)]==0 for i in range(5))
    bindings.append(dict(behavior=behavior,bullet=bullet,child=child,bulletRow=bu,childRow=ch,attackRow=attack))
for immune,resistance,scale in itertools.product((False,True),(1,299,300,301,600),(0.5,1,2)):
    c=Ailment(x,0,resistance,immune);rejected=c.apply(leaf,scale);c.qualify();c.update(0)
    amount=int(300*scale);expected=immune or resistance>amount
    assert rejected==expected
    assert c.remaining()==(resistance if immune or not expected else resistance-amount)
    assert any(n['id']==leaf for n in c.nodes())==(not rejected)
    record('onset',c,immune=immune,resistance=resistance,scale=scale,amount=amount,rejected=rejected,remaining=c.remaining())
for maximum in (99,100,137,1000,10000,12345,100000):
    c=Ailment(x,0,300);assert c.apply(leaf) is False;c.qualify();c.update(0)
    packet=c.hp_packet(maximum);assert packet[0]==-(int(maximum*.001)+10),(maximum,packet)
    record('damage',c,maximum=maximum,packet=packet)
for elapsed in (0,1,5,15,39):
    c=Ailment(x,0,300);assert c.apply(leaf) is False;c.qualify();c.update(0)
    c.qualify();c.update(elapsed);before=c.nodes()[0]['lifetime'];result=c.apply(leaf)
    assert result=='existing' and c.nodes()[0]['lifetime']==before
    record('repeat',c,elapsed=elapsed,result=result,remaining=before)
for fps in (30,60,120):
    c=Ailment(x,0,300);assert c.apply(leaf) is False;c.qualify();c.update(0);ticks=[]
    for frame in range(42*fps):
        packet=c.hp_packet(10000)
        if packet[0]:ticks.append(dict(frame=frame,packet=packet))
        c.emitted.clear();step(c,fps)
        if not c.nodes():break
    assert abs((frame+1)/fps-40)<=3.01/fps
    assert len(ticks)==31 and all(t['packet'][0]==-20 for t in ticks)
    assert all(abs((b['frame']-a['frame'])/fps-1.3)<=3.01/fps for a,b in zip(ticks,ticks[1:]))
    record('lifetime',c,fps=fps,expiryFrame=frame+1,ticks=ticks)
output=dict(schema=1,exeSha256=sha(x.raw),regulationSha256=x.x['hashes']['regulation.bin'],paramSha256=sha(x.param),
    behaviorParamSha256=sha(behaviorraw),bulletParamSha256=sha(bulletraw),attackParamSha256=sha(attackraw),weaponParamSha256=sha(weaponraw),
    animationBundleSha256=animations['bundles'][0]['sha256'],taeSha256=sha(taeraw),behaviorSha256=graph.metadata['hkxSha256'],scriptSha256=sha(raw_script),
    root=root,marker=marker,leaf=leaf,rows={str(i):x.spells[str(i)] for i in (root,marker,leaf,7010601,505)},
    paths=paths,events=events,release=release,reset=reset,bindings=bindings,checks=checks,
    native=dict(relocate='27D0F10',iterate='27D0400',type2='40CD80',behavior='668B30',grant='3C7FD0',insert='50D060',status='42D110',
                immunity='509790',accumulation='42CD70',remove='505280',qualify='5057D0',update='50ACD0',hp='506EC0'),
    stubs=sorted(stubs|{'HKS input/environment and common interruption results are supplied; original release branch runs in Lua, not the game VM',
        'hit arrivals, poison resistance and correction scales are fixtures; collision, child-projectile inheritance and complete attack construction are not simulated',
        'cycle effect 505 has no HP change and is recorded without simulating visual delivery'}),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(map(len,checks.values())),'Ironeye charged ultimate cases')
