"""Execute native TAE loading and Undertaker ultimate skill-charge reset.

Animation selection/activity, player identity and current skill-resource state
are explicit fixtures. File relocation, event iteration, state gates and skill
refill execute original instructions. This is not a gameplay test.
"""
import argparse
import itertools
import json
import math
import struct
from pathlib import Path
from unicorn.x86_const import *
from native_effect_runtime import BASE, OBJ, Chain, Inputs, sha
from native_animation_runtime import NativeTae
from effect_behavior_graph import BehaviorGraph

p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','npc','animations','behavior','script','output'):p.add_argument(name,type=Path)
a=p.parse_args();inputs=Inputs(a.exe,a.extracted)
npc=json.loads(a.npc.read_text());tae=json.loads(a.animations.read_text());graph=BehaviorGraph(a.behavior)
assert npc['hashes']['regulation.bin']==inputs.x['hashes']['regulation.bin'] and tae['allEvents']
assert tae['bundles'][0]['sha256']=='1410035ad79edb410fa41420ec259fcb4a1037d748c9c4a3b6ae8d1366c76d0f'
root=7500900;assert inputs.spells[str(root)]['stateInfo']==2059 and inputs.spells[str(root)]['spCategory']==20
track=next(t for t in tae['bundles'][0]['taes'] if t['ID']==2909)
raw=Path(str(a.animations)+'.2909.tae').read_bytes();assert sha(raw)==track['sha256']
hero_raw=a.npc.with_suffix('.HeroParam.param').read_bytes();hero=Inputs.table(hero_raw,0xb0)[10]
hero_row=npc['tables']['HeroParam']['10']
assert struct.unpack_from('<f',hero,0x74)[0]==hero_row['characterAbilityCooldown']==14
assert hero[0x78]==hero_row['characterAbilityUsageCount']==1
script=a.script.read_bytes();assert sha(script)=='786f8a7bc89452d9531e2299b224c8945701c422437eca9aacbeb10a57a17f4d'
source=script.decode('utf-8-sig').replace('\r\n','\n');functions=[]
for name in ('BlinkStakeStart_onUpdate','AirBlinkStakeStart_onUpdate'):
    start=source.index('function '+name+'()');f=source[start:source.index('\nfunction ',start+1)]
    assert 'env(IsBlinkStakeCollide) == TRUE' in f and 'ExecEventAllBody("W_BlinkStakeFinish")' in f
    functions.append(dict(name=name,sha256=sha(f.encode())))
state=20979;assert graph.name(state)=='BlinkStakeFinish'
blend=graph.reference(state,'generator');children=graph.blender_children(blend)
assert blend==22392 and [r['generator'] for r in children]==[32470,32471]
paths=[]
for child in graph.children(32470):
    clips=graph.children(child);assert len(clips)==1
    clip=clips[0];paths.append(dict(state=state,blend=blend,selector=32470,child=child,clip=clip,animation=graph.string(graph.reference(clip,'animationName'))))
assert [p['animation'] for p in paths]==['a909_690001','a909_690011']
events=[dict(tae=track['ID'],animation=an['ID'],**e) for an in track['animations'] for e in an['events'] if e['Type']==1020]
assert [(e['animation'],e['index']) for e in events]==[(690001,44),(690011,45)]
assert all(bytes.fromhex(e['hex'])==struct.pack('<4I',2059,0,0,0) and e['StartTime']==0 for e in events)

class Reset(Chain):
    def __init__(self, player=True, maximum=None, remaining=0, elapsed=7):
        super().__init__(inputs);self.player=player;self.refills=0
        self.q(OBJ+0x6190,OBJ);self.q(OBJ+0x61b8,OBJ+0x9000);self.q(OBJ+0x9148,OBJ+0xa000);self.q(OBJ+0xa008,OBJ+0x6000)
        maximum=hero[0x78] if maximum is None else maximum
        self.u.mem_write(OBJ+0xa020,bytes([remaining,maximum,hero[0x78]]))
        self.u.mem_write(OBJ+0xa024,struct.pack('<3f',elapsed,14,14))
        # Existing debug singleton, disabled override: native availability takes
        # its normal player/count branch, not the permissive debug shortcut.
        for rva,value,size in ((0x48ba8f+8+0x37838a1,OBJ+0xf000,8),(0x48bac0+7+0x378383d,0,1)):
            try:self.u.mem_read(BASE+rva,size)
            except:self.mapped(self.u,0,BASE+rva,size,0,None)
            self.u.mem_write(BASE+rva,value.to_bytes(size,'little'))
        self.animation=NativeTae(self,raw,track['sha256'])
    def hook(self,u,address,size,user):
        if address==BASE+0x3d4180:
            self.stubs.add('3D4180 explicit player/non-player identity')
            u.reg_write(UC_X86_REG_RAX,int(self.player));sp=u.reg_read(UC_X86_REG_RSP)
            u.reg_write(UC_X86_REG_RIP,struct.unpack('<Q',u.mem_read(sp,8))[0]);u.reg_write(UC_X86_REG_RSP,sp+8)
        elif address==BASE+0x48bd40:
            self.refills+=1  # Observe; the refill routine still executes.
        else:super().hook(u,address,size,user)
    def event(self,event,active=True):
        ctx=self.animation.select(event['animation'],1020)
        ptr=struct.unpack('<Q',self.u.mem_read(ctx+8,8))[0]
        assert bytes(self.u.mem_read(ptr,16))==bytes.fromhex(event['hex'])
        assert struct.unpack('<H',self.u.mem_read(ctx+0x1a,2))[0]==255
        self.q(OBJ+0xd018,OBJ+0x6000);self.u.mem_write(ctx+0x18,bytes([active]))
        self.invoke(0x410ca0,[OBJ+0xd000,ctx])
    def resource(self):
        remaining,maximum=struct.unpack('<2B',self.u.mem_read(OBJ+0xa020,2))
        elapsed,threshold,base=struct.unpack('<3f',self.u.mem_read(OBJ+0xa024,12))
        return dict(remaining=remaining,maximum=maximum,elapsed=elapsed,threshold=threshold,base=base)
    def ready(self):return bool(self.invoke(0x48ba80,[OBJ+0xa000])&255)

checks=dict(dispatch=[],capacity=[],repeat=[]);stubs=set()
for event,copies,active,player in itertools.product(events,(0,1,2,3),(False,True),(False,True)):
    c=Reset(player=player)
    for _ in range(copies):c.insert(root)
    c.qualify();c.update(0);before=c.resource();c.event(event,active);after=c.resource()
    expected=bool(copies and active and player)
    assert c.refills==int(expected) and after['remaining']==int(expected)
    assert after['elapsed']==(0 if expected else 7) and after['maximum']==1
    if player:assert c.ready()==expected
    checks['dispatch'].append(dict(animation=event['animation'],copies=copies,active=active,player=player,bank=c.animation.bank,before=before,after=after,refills=c.refills));stubs.update(c.stubs)
for maximum,elapsed,cooldown_effect in itertools.product((1,2,3),(0,7,13),(None,7000803)):
    for remaining in range(maximum+1):
        c=Reset(maximum=maximum,remaining=remaining,elapsed=elapsed);c.insert(root)
        if cooldown_effect:c.insert(cooldown_effect)
        c.qualify();c.update(0);before=c.resource();ready_before=c.ready();c.event(events[0]);after=c.resource()
        assert after['remaining']==after['maximum']==maximum and after['elapsed']==0 and c.ready()
        assert ready_before==bool(remaining) and after['base']==14
        expected=14*(inputs.spells[str(cooldown_effect)]['characterSkillCooldownReduction'] if cooldown_effect else 1)
        assert math.isclose(after['threshold'],expected,rel_tol=1e-6)
        checks['capacity'].append(dict(maximum=maximum,remaining=remaining,elapsed=elapsed,cooldownEffect=cooldown_effect,before=before,after=after,readyBefore=ready_before,readyAfter=c.ready()));stubs.update(c.stubs)
for event,copies in itertools.product(events,(1,2,3)):
    c=Reset();
    for _ in range(copies):c.insert(root)
    c.qualify();c.update(0);states=[]
    for n in range(4):
        if n==2:c.u.mem_write(OBJ+0xa020,b'\0')  # explicit later consumption
        c.event(event);states.append(c.resource())
    assert all(s['remaining']==1 and s['maximum']==1 for s in states)
    checks['repeat'].append(dict(animation=event['animation'],copies=copies,states=states,refills=c.refills));stubs.update(c.stubs)
output=dict(schema=1,exeSha256=sha(inputs.raw),regulationSha256=inputs.x['hashes']['regulation.bin'],paramSha256=sha(inputs.param),
            heroParamSha256=sha(hero_raw),hero=dict(id=10,cooldown=14,usageCount=1),
            animationBundleSha256=tae['bundles'][0]['sha256'],taeSha256=sha(raw),nativeEventBank=255,
            behaviorSha256=graph.metadata['hkxSha256'],scriptSha256=sha(script),functions=functions,paths=paths,events=events,root=root,checks=checks,
            native=dict(relocate='27D0F10 → 27D0940',iterate='27D0400',dispatch='410CA0 → 413E6F',state='508E20',reset='48BD40',
                        cooldown='42C130 → 508480',ready='48BA80'),stubs=sorted(stubs),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(map(len,checks.values())),'native Undertaker reset cases')
