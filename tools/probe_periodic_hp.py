"""Execute passive HP pulse stacking, timing and separate gain/loss packets.

Uses actual MMV rows and original effect insertion, qualification, periodic
update and HP aggregation. The optional physical owner is omitted only while
collecting the numeric HP packet. No current-HP setter or gameplay is simulated.
"""
import argparse
import itertools
import json
import struct
from pathlib import Path
from native_effect_runtime import OBJ, Chain, Inputs, sha

p=argparse.ArgumentParser(description=__doc__)
for name in ('exe','extracted','output'):p.add_argument(name,type=Path)
a=p.parse_args();inputs=Inputs(a.exe,a.extracted)
roots=[7001100,6850500];rows={}
for root in roots:
    row=inputs.spells[str(root)];attach=inputs.x['tables']['AttachEffectParam'][str(root)]
    assert attach['passiveSpEffectId_1']==root and attach['exclusivityId']==-1
    assert row['spCategory']==10 and row['stateInfo']==0 and row['effectEndurance']==-1 and row['motionInterval']==1
    assert all(row['invocationConditionsStateChange'+str(i)]==0 for i in (1,2,3))
    assert all(row[k]<=0 for k in ('cycleOccurrenceSpEffectId','replaceSpEffectId','atkOccurrenceSpEffectId'))
    assert row['changeHpRate']==row['changeHpEstusFlaskRate']==row['changeHpEstusFlaskPoint']==0
    assert row['conditionHp']==row['conditionHpRate']==-1
    assert row['changeHpPoint']==(-2 if root==7001100 else 2)
    assert struct.unpack_from('<fi',inputs.rows[root],0x9c)==(row['changeHpRate'],row['changeHpPoint'])
    assert struct.unpack_from('<2f',inputs.rows[root],8)==(row['effectEndurance'],row['motionInterval'])
    rows[str(root)]={k:row[k] for k in ('changeHpPoint','motionInterval','effectEndurance','spCategory','stateInfo','bCurrHPIndependeMaxHP')}

class PeriodicHp(Chain):
    def hp(self,maximum=1000):
        self.q(OBJ+0x10,0)
        self.invoke(0x506ec0,[OBJ,maximum,OBJ+0x800,OBJ+0x808,OBJ+0x820,0])
        self.q(OBJ+0x10,OBJ+0x6000)
        return list(struct.unpack('<7i',self.u.mem_read(OBJ+0x820,28)))
    def disable(self):
        node=struct.unpack('<Q',self.u.mem_read(OBJ+8,8))[0]
        while node:
            self.u.mem_write(node+0x68,struct.pack('<I',0x800c0003))
            node=struct.unpack('<Q',self.u.mem_read(node+0x38,8))[0]

checks=dict(snapshot=[],timing=[],mixed=[],staggered=[],arrivalBaseline=[]);stubs=set()
def prepare(ids,dt=0):
    c=PeriodicHp(inputs)
    for id in ids:c.insert(id)
    c.qualify();c.update(dt)
    return c

def record(group,c,**row):checks[group].append(row);stubs.update(c.stubs)
def packet(heal,drain):return [2*heal,0,2*heal,-2*drain,0,0,0]
for root,copies,maximum,disabled in itertools.product(roots,range(4),(1,99,1000,2345),(False,True)):
    c=prepare([root]*copies)
    if disabled:c.disable()
    value=c.hp(maximum)
    assert value==(packet(copies if root==7001100 else 0,copies if root==6850500 else 0) if not disabled else [0]*7)
    record('snapshot',c,root=root,copies=copies,maximum=maximum,disabled=disabled,packet=value)

baselines={}
def timeline(c,fps,insertions=None):
    values=[]
    for frame in range(3*fps+4):
        if frame:
            for id in (insertions or {}).get(frame,[]):c.insert(id)
            c.qualify();c.update(1/fps)
        value=c.hp()
        values.append(value)
    return values
for root,copies,fps in itertools.product(roots,(1,2,3),(30,60,120)):
    c=prepare([root]*copies);values=timeline(c,fps)
    pulses=[i for i,v in enumerate(values) if any(v)]
    assert len(pulses)==4 and pulses[0]==0 and fps<=pulses[1]<=fps+2
    assert all(fps-1<=b-a<=fps+1 for a,b in zip(pulses[1:],pulses[2:]))
    expected=packet(copies if root==7001100 else 0,copies if root==6850500 else 0)
    assert all(v==(expected if i in pulses else [0]*7) for i,v in enumerate(values))
    assert len(c.nodes())==copies and all(n['id']==root and n['lifetime']==-1 for n in c.nodes())
    if copies==1:baselines[root,fps]=values
    else:assert values==[[x*copies for x in v] for v in baselines[root,fps]]
    record('timing',c,root=root,copies=copies,fps=fps,pulseFrames=pulses,packet=expected)
for heal,drain,fps in itertools.product(range(4),range(4),(30,60,120)):
    c=prepare([7001100]*heal+[6850500]*drain);values=timeline(c,fps)
    expected=[[h*heal+d*drain for h,d in zip(hp,dp)] for hp,dp in zip(baselines[7001100,fps],baselines[6850500,fps])]
    assert values==expected and len(c.nodes())==heal+drain
    record('mixed',c,heal=heal,drain=drain,fps=fps,pulses=[dict(frame=i,packet=v) for i,v in enumerate(values) if any(v)])
arrival_baselines={}
for root,fps in itertools.product(roots,(30,60,120)):
    # A mid-update arrival consumes that frame's dt on its first native update.
    c=prepare([root],1/fps);values=timeline(c,fps);arrival_baselines[root,fps]=values
    record('arrivalBaseline',c,root=root,fps=fps,pulses=[dict(frame=i,packet=v) for i,v in enumerate(values) if any(v)])
for first,second,fps in itertools.product(roots,roots,(30,60,120)):
    offset=fps//2
    c=prepare([first]);values=timeline(c,fps,{offset:[second]})
    expected=[]
    for frame in range(len(values)):
        other=arrival_baselines[second,fps][frame-offset] if frame>=offset else [0]*7
        expected.append([a+b for a,b in zip(baselines[first,fps][frame],other)])
    assert values==expected and len(c.nodes())==2, (first,fps,[(i,a,b) for i,(a,b) in enumerate(zip(values,expected)) if a!=b])
    record('staggered',c,first=first,second=second,fps=fps,offsetFrames=offset,pulses=[dict(frame=i,packet=v) for i,v in enumerate(values) if any(v)])
output=dict(schema=1,exeSha256=sha(inputs.raw),regulationSha256=inputs.x['hashes']['regulation.bin'],paramSha256=sha(inputs.param),
            rows=rows,checks=checks,native=dict(insert='50D060',qualify='5057D0',update='50ACD0 → 511B80',hp='506EC0 → 50B860 → 510100 / 510130'),
            stubs=sorted(stubs|{'optional physical owner omitted only during HP aggregation; no current HP setter, hurt event, death, overheal or multiplayer execution'}),gameplayVerified=False)
a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('PASS',sum(map(len,checks.values())),'native periodic HP cases')
