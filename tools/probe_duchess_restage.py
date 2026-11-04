"""Trace Duchess Restage's relic selector and damage multiplier.

Original HKS, native state queries, TAE dispatch, rate selection and the damage
consumer run with explicit actor, history-input, allocation and transport
fixtures. The complete hit-history recorder and game/network are not simulated.
"""
import argparse
import ctypes
import ctypes.util
import itertools
import json
import math
import struct
from pathlib import Path
from unicorn.x86_const import *
from native_effect_runtime import BASE, OBJ, STACK, STOP, Chain, Inputs, sha
from effect_behavior_graph import BehaviorGraph

p = argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','assets','systems','script','animations','behavior','output'):
    p.add_argument(name,type=Path)
a=p.parse_args()
inputs=Inputs(a.exe,a.extracted)
assets,systems,tae=(json.loads(path.read_text()) for path in (a.assets,a.systems,a.animations))
for x in (assets,systems):assert x['hashes']['regulation.bin']==inputs.x['hashes']['regulation.bin']
assert tae['bundles'][0]['sha256']=='1410035ad79edb410fa41420ec259fcb4a1037d748c9c4a3b6ae8d1366c76d0f'
raw=a.script.read_bytes()
assert sha(raw)=='786f8a7bc89452d9531e2299b224c8945701c422437eca9aacbeb10a57a17f4d'
source=raw.decode('utf-8-sig').replace('\r\n','\n')
start=source.index('function ExecDejavu()');function=source[start:source.index('\nfunction ',start+1)]
update_start=source.index('function Update()');update=source[update_start:source.index('\nfunction ',update_start+1)]
assert 'ExecChangeDejavuBlend()\n    ExecDejavu()' in update
assert 'HERO_SPEED = 4' in a.script.with_name('common_define.hks').read_text(encoding='utf-8-sig')
behavior_raw=a.extracted.with_suffix('.BehaviorParam_PC.param').read_bytes()
weapon_raw=a.assets.with_suffix('.EquipParamWeapon.param').read_bytes()
player_raw=a.systems.with_suffix('.PlayerCommonParam.param').read_bytes()
behaviors=Inputs.table(behavior_raw,0x30);weapons=Inputs.table(weapon_raw,0x298)
player=Inputs.table(player_raw,0x140)[0]
assert struct.unpack_from('<f',player,0xd0)[0]==.5
spells=inputs.spells
assert spells['7290000']['stateInfo']==2271 and spells['7290000']['spCategory']==20
assert {k:(spells['703540'][k],v) for k,v in spells['7290001'].items() if spells['703540'][k]!=v}=={'restageAttackRate':(-1,spells['7290001']['restageAttackRate'])}
assert math.isclose(spells['7290001']['restageAttackRate'],.6,rel_tol=1e-6)
assert spells['703540']['stateInfo']==spells['7290001']['stateInfo']==601
assert all(struct.unpack_from('<f',inputs.rows[id],0x3b0)[0]==spells[str(id)]['restageAttackRate'] for id in (703540,7290001))
bullets=inputs.x['tables']['Bullet']
assert {k:(bullets['30903000'][k],v) for k,v in bullets['30903005'].items() if bullets['30903000'][k]!=v}=={'spEffectId0':(703540,7290001)}
paths=[]
for id,bullet,leaf in ((600000150,30903000,703540),(600000185,30903005,7290001)):
    row=inputs.x['tables']['BehaviorParam_PC'][str(id)]
    assert row['refType']==1 and row['refId']==bullet and bullets[str(bullet)]['spEffectId0']==leaf
    paths.append(dict(behavior=id,bullet=bullet,leaf=leaf))
graph=BehaviorGraph(a.behavior)
bindings=[graph.selector_binding(i) for i in (16955,17189,17190)]
assert [b['name'] for b in bindings]==['IndexDejavuBlend','IsRelic_Dejavu','IsRelic_Dejavu']
assert graph.children(16955)==[17189,17190,17191]
animations=[]
for selector in (17189,17190):
    row=[]
    for generator in graph.children(selector):
        children=graph.children(generator);assert len(children)==1
        row.append(graph.string(graph.reference(children[0],'animationName')))
    animations.append(row)
assert animations==[['a903_539000','a903_539005'],['a903_539100','a903_539105']]
events={an['ID']:dict(tae=t['ID'],animation=an['ID'],**e)
        for b in tae['bundles'] for t in b['taes'] if t['ID']==2903
        for an in t['animations'] if an['ID'] in (539000,539005,539100,539105)
        for e in an['events'] if e['index']==1}
assert len(events)==4
for id,e in events.items():
    assert e['Type']==2 and e['StartTime']==0 and math.isclose(e['EndTime'],.1)
    assert struct.unpack_from('<i',bytes.fromhex(e['hex']),8)[0]==(6185 if id%100==5 else 6150)

lua = ctypes.CDLL(ctypes.util.find_library('lua5.4'))
lua.luaL_newstate.restype = ctypes.c_void_p
lua.luaL_openlibs.argtypes = [ctypes.c_void_p]
lua.luaL_loadstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
lua.lua_pcallk.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_ssize_t, ctypes.c_void_p]
lua.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_size_t)]
lua.lua_tolstring.restype = ctypes.c_char_p
lua.lua_close.argtypes = [ctypes.c_void_p]

def script_case(hero=4, blend=0, ready=1, hp=1, pressed=1, equipped=1, style=0, boost=0):
    program = '''
TRUE=1; FALSE=0; HERO_SPEED=4; HAND_LEFT_BOTH=1; HAND_RIGHT_BOTH=2
GetHeroID=1; IsCharacterSkillReady=2; GetHP=3; ActionDuration=4
GetStateChangeType=5; GetSpEffectID=6; AddSpEffect=7; ResetInputQueue=8; ACTION_ARM_SKILL=9
local inputs={%d,%d,%d,%d,%d,%d}
local vars={AddDejavuBlend=%d,IndexDejavuBlend=-1,IsRelic_Dejavu=-1}
local added={};local resets=0
c_Style=%d
function env(key,id)
  if key==5 then assert(id==2271) end
  if key==6 then assert(id==7500300) end
  return inputs[key]
end
function GetVariable(k) return vars[k] end
function SetVariable(k,v) vars[k]=v end
function act(key,id)
  if key==AddSpEffect then table.insert(added,id) else assert(key==ResetInputQueue);resets=resets+1 end
end
''' % (hero, ready, hp, pressed, boost, equipped, blend, style)
    program += function + '''
local first=ExecDejavu();local second=ExecDejavu()
return string.format('{"first":%d,"second":%d,"added":[%s],"resets":%d,"blend":%d,"style":%d,"boost":%d}',
first,second,table.concat(added,","),resets,vars.AddDejavuBlend,vars.IndexDejavuBlend,vars.IsRelic_Dejavu)
'''
    state = lua.luaL_newstate()
    try:
        lua.luaL_openlibs(state)
        assert lua.luaL_loadstring(state, program.encode()) == 0
        status = lua.lua_pcallk(state, 0, 1, 0, 0, None)
        result = lua.lua_tolstring(state, -1, None)
        assert status == 0, result
        return json.loads(result)
    finally:
        lua.lua_close(state)

MODULE,VICTIM,HIT,RESOURCE,QUEUE=(OBJ+i for i in (0x9000,0xa000,0xb000,0xb800,0xc800))
f32=lambda x:struct.unpack('<f',struct.pack('<f',x))[0]

class Restage(Chain):
    def __init__(self):
        super().__init__(inputs)
        self.requests=[];self.heals=[];self.poise=[];self.statuses=[];self.phase=None
        for off,ptr in ((0x118,STOP+0x201),(0x190,STOP+0x200),(0x260,STOP+0x200),
                        (0x328,BASE+0x668b30),(0x320,STOP+0x201),(0x250,STOP+0x202),
                        (0x28,STOP+0x201),(0x178,STOP+0x200)):
            self.q(OBJ+0x6200+off,ptr)
        self.q(OBJ+0x6190,OBJ)
        self.q(MODULE+8,VICTIM);self.q(VICTIM+0x1b8,OBJ+0xa800)
        self.q(OBJ+0xa800,RESOURCE);self.q(OBJ+0xa898,HIT);self.q(OBJ+0xa958,MODULE)
        self.q(HIT,OBJ+0xbc00);self.q(OBJ+0xbc98,STOP+0x210);self.q(HIT+8,VICTIM)
        self.u.mem_write(RESOURCE+0x140,struct.pack('<i',100000))
        self.u.mem_write(OBJ+0xc000,player)
        self.q(QUEUE+0x20,OBJ+0xd000);self.q(QUEUE+0x28,OBJ+0xd000);self.q(QUEUE+0x30,OBJ+0xd400)
        for rva,ptr in ((0x44a3e2+0x37c93be,QUEUE),(0x430fb3+0x37de0f5,OBJ+0xf000)):
            page=(BASE+rva)&~4095
            try:self.u.mem_read(page,1)
            except:self.mapped(self.u,0,page,8,0,None)
            self.q(BASE+rva,ptr)
    def hook(self,u,address,size,user):
        pc=address-BASE
        def ret(value=0):
            u.reg_write(UC_X86_REG_RAX,value);sp=u.reg_read(UC_X86_REG_RSP)
            u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
        if (self.phase=='apply' and pc==0x3ce5e9) or (self.phase=='consume' and pc==0x449c6d):
            u.reg_write(UC_X86_REG_RIP,STOP)
        elif address in (STOP+0x200,STOP+0x201,STOP+0x202):
            self.stubs.add('synthetic animation-owner virtuals and equipped weapon 1000')
            ret({STOP+0x200:0,STOP+0x201:1,STOP+0x202:1000}[address])
        elif pc in (0x4d1b20,0x3d4180,0x3d4c10,0xea9a60,0xea76f0,0x66b2d0,0x27d0640):
            self.stubs.add(hex(pc)+' isolated animation-owner context / hand identity / empty reference list');ret()
        elif pc==0x3ced90:
            self.stubs.add('3CED90 isolated animation-owner context');ret(OBJ+0xe800)
        elif pc==0xea7fc0:
            self.stubs.add('EA7FC0 actual equipped-weapon row lookup');id=u.reg_read(UC_X86_REG_RDX)&0xffffffff
            u.mem_write(OBJ+0xe000,weapons[id]);u.mem_write(u.reg_read(UC_X86_REG_RCX),struct.pack('<IIQ',id,0,OBJ+0xe000));ret()
        elif pc==0xe6fcb0:
            self.stubs.add('E6FCB0 actual Behavior row lookup');id=u.reg_read(UC_X86_REG_RDX)&0xffffffff
            assert id in (600000150,600000185)
            u.mem_write(OBJ+0xe400,behaviors[id]);self.q(u.reg_read(UC_X86_REG_RCX)+8,OBJ+0xe400);ret()
        elif pc==0x3975d0:
            self.stubs.add('3975D0 Behavior request recorder; animation dispatch remains native')
            self.requests.append(u.reg_read(UC_X86_REG_RDX));ret(1)
        elif pc==0xe81650:
            self.stubs.add('E81650 actual PlayerCommon PARAM lookup');ptr=u.reg_read(UC_X86_REG_RCX);self.q(ptr,OBJ+0xc000);ret(ptr)
        elif pc in (0x216b9a0,0x216ba10):
            self.stubs.add('single-thread fixture mutex lock/unlock');ret()
        elif pc==0x282970:
            self.stubs.add('282970 synthetic actor entity identity');ptr=u.reg_read(UC_X86_REG_RDX);self.q(ptr,1);ret(ptr)
        elif pc==0x519ef0:
            self.stubs.add('519EF0 authoritative local recipient; no network simulation');ret(1)
        elif pc==0x426130:
            self.stubs.add('426130 HP delta recorder; final caps/modifiers are not simulated')
            self.heals.append(struct.unpack('<i',struct.pack('<I',u.reg_read(UC_X86_REG_RDX)&0xffffffff))[0]);ret()
        elif pc==0x43ced0:
            self.stubs.add('43CED0 damage notification sink after recorded HP request');ret()
        elif pc==0x48de50:
            self.stubs.add('48DE50 poise request recorder; final stagger processing not simulated')
            self.poise.append(struct.unpack('<f',u.reg_read(UC_X86_REG_XMM1).to_bytes(16,'little')[:4])[0]);ret()
        elif pc==0x3c7fd0 and self.phase=='consume':
            self.stubs.add('3C7FD0 status-effect request recorder')
            self.statuses.append(u.reg_read(UC_X86_REG_RDX));ret()
        elif address==STOP+0x210:
            self.stubs.add('synthetic absent linked actor identity; secondary replay target not simulated')
            ptr=u.reg_read(UC_X86_REG_RDX);u.mem_write(ptr,struct.pack('<i',-1));ret(ptr)
        else:super().hook(u,address,size,user)
    def boost(self,copies):
        for _ in range(copies):self.insert(7290000)
        self.qualify();self.update(0)
        return self.invoke(0x508e20,[OBJ,2271])&255
    def dispatch(self,event,active):
        self.requests.clear();self.q(OBJ+0x8018,OBJ+0x6000);self.q(OBJ+0x8108,OBJ+0x8200)
        self.u.mem_write(OBJ+0x8118,bytes([active]));self.u.mem_write(OBJ+0x811a,struct.pack('<H',0x27))
        self.q(OBJ+0x8120,OBJ+0x8300);self.u.mem_write(OBJ+0x8200,bytes.fromhex(event['hex']))
        self.invoke(0x40cd80,[OBJ+0x8000,OBJ+0x8100]);return self.requests[:]
    def apply(self,leaf):
        self.phase='apply';self.u.mem_write(OBJ+0xf400,inputs.rows[leaf])
        self.u.reg_write(UC_X86_REG_RBX,VICTIM)
        self.invoke(0x3ce5b3,[OBJ+0xf400]);self.phase=None
        return struct.unpack('<f',self.u.mem_read(MODULE+0x3c,4))[0]
    def consume(self,records):
        self.phase='consume';self.heals.clear();self.poise.clear();self.statuses.clear()
        ptr=OBJ+0xe000;end=ptr+20*len(records)
        for i,(damage,poise,flags) in enumerate(records):
            self.u.mem_write(ptr+i*20,struct.pack('<ifB3xii',damage,poise,flags,-1,-1))
        bp=STACK+0x6000;self.q(bp-0x80,end)
        for reg,val in ((UC_X86_REG_RDI,MODULE),(UC_X86_REG_RBX,ptr),(UC_X86_REG_R9,end),
                        (UC_X86_REG_R13,0),(UC_X86_REG_RBP,bp)):
            self.u.reg_write(reg,val)
        self.invoke(0x449aac,[],{UC_X86_REG_XMM7:0});self.phase=None
        return dict(hp=self.heals[:],poise=self.poise[:],statuses=self.statuses[:])

checks=dict(script=[],dispatch=[],selection=[],damage=[],repeat=[]);stubs=set()
for hero,style,copies in itertools.product(range(11),(0,1,2),(0,1,3)):
    c=Restage();boost=c.boost(copies);r=script_case(hero=hero,style=style,boost=boost,equipped=0)
    assert r['first']==r['resets']==int(hero==4) and r['second']==0
    assert r['boost']==(boost if hero==4 else -1)
    assert len(c.nodes())==bool(copies)
    checks['script'].append(dict(hero=hero,style=style,copies=copies,result=r));stubs.update(c.stubs)
for gate,value in (('blend',1),('blend',2),('ready',0),('hp',0),('pressed',0)):
    r=script_case(**{gate:value},boost=1,equipped=0)
    assert r['first']==r['second']==r['resets']==0 and r['boost']==-1
    checks['script'].append(dict(gate=gate,value=value,result=r))
for event,active in itertools.product(events.values(),(0,1)):
    c=Restage();requests=c.dispatch(event,active)
    expected=600000185 if event['animation']%100==5 else 600000150
    assert requests==([expected] if active else [])
    checks['dispatch'].append(dict(animation=event['animation'],active=active,requests=requests));stubs.update(c.stubs)
for style,copies in itertools.product((0,1,2),(0,1,2,3)):
    c=Restage();r=script_case(style=style,boost=c.boost(copies),equipped=0)
    animation=int(animations[r['style']][r['boost']].split('_')[1])
    request=c.dispatch(events[animation],1)[0];leaf=next(p['leaf'] for p in paths if p['behavior']==request)
    rate=c.apply(leaf);assert math.isclose(rate,.6 if copies else .5,rel_tol=1e-6)
    begin,end=struct.unpack('<QQ',c.u.mem_read(QUEUE+0x20,16));assert end-begin==8
    checks['selection'].append(dict(style=style,copies=copies,animation=animation,leaf=leaf,rate=rate,queued=1));stubs.update(c.stubs)
poise_rate=struct.unpack_from('<f',player,0xd4)[0]
for leaf,values,flags in itertools.product((703540,7290001),
        ([],[0],[1],[2],[3],[4],[5],[9],[10],[99],[100],[999],[1,1,1],[3,7,11],[100,200,300]),range(16)):
    c=Restage();rate=c.apply(leaf)
    records=[(v,0 if v==0 else 12.5,flags) for v in values]
    r=c.consume(records);damage=0;poise=0.
    for v,p,f in records:damage=int(f32(f32(f32(v)*rate)+f32(damage)));poise=f32(poise+f32(f32(p)*poise_rate))
    eligible=damage>0 or poise>0
    assert r['hp']==([-damage] if damage>0 else []),(leaf,values,flags,r,damage)
    assert r['poise']==([poise] if eligible else [])
    assert r['statuses']==([703600+i for i in range(4) if flags&(1<<i)] if eligible else [])
    checks['damage'].append(dict(leaf=leaf,values=values,statusBits=flags,result=r));stubs.update(c.stubs)
for sequence in ((703540,703540,703540),(7290001,7290001,7290001),(703540,7290001),(7290001,703540)):
    c=Restage();rates=[c.apply(leaf) for leaf in sequence]
    assert all(math.isclose(rate,.6 if leaf==7290001 else .5,rel_tol=1e-6) for leaf,rate in zip(sequence,rates))
    r=c.consume([(100,10,0)]);assert r['hp']==([-60] if sequence[-1]==7290001 else [-50])
    checks['repeat'].append(dict(sequence=sequence,rates=rates,result=r));stubs.update(c.stubs)
output=dict(schema=1,exeSha256=sha(inputs.raw),regulationSha256=inputs.x['hashes']['regulation.bin'],
            paramSha256=sha(inputs.param),behaviorParamSha256=sha(behavior_raw),weaponParamSha256=sha(weapon_raw),
            playerCommonParamSha256=sha(player_raw),scriptSha256=sha(raw),functionSha256=sha(function.encode()),
            animationSha256=tae['bundles'][0]['sha256'],behavior={k:graph.metadata[k] for k in ('bundleSha256','hkxSha256','registrySha256','metadataOnly','mismatches')},
            root=7290000,baseRate=.5,relicRate=spells['7290001']['restageAttackRate'],poiseRate=poise_rate,
            bindings=bindings,animations=animations,events=list(events.values()),paths=paths,checks=checks,
            native=dict(state='508E20',dispatch='40CD80',resolve='668B30',arrival='3CE5B3..3CE5E9',
                        rate='44A340',queue='733490',consume='449AAC..449C6D',damage='430F50'),
            stubs=sorted(stubs|{'original HKS environment/input calls are fixtures; state-2271 result comes from native query',
                               'synthetic replay-history records; full recorder, time filtering and scheduling not simulated',
                               'no full hit, resource/stagger modifiers, linked actor, multiplayer or game execution'}),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS:',{k:len(v) for k,v in checks.items()})
