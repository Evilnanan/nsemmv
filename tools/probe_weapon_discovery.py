"""Read-only isolated execution of weapon bias selection and ItemTable drawing.

Uses actual ordered PARAM rows: ItemTable IDs identify groups, not unique rows.
OS allocation, PARAM lookup and random input are fixtures; the native filtering,
cumulative weights, weighted selection and SpEffect getter execute unchanged.
"""
import argparse
import collections
import hashlib
import json
import struct
from pathlib import Path

import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_CODE, UC_HOOK_MEM_UNMAPPED
from unicorn.x86_const import *

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('exe', type=Path)
p.add_argument('discovery', type=Path, help='ExtractEffectDetails --discovery JSON')
p.add_argument('effects', type=Path, help='ExtractEffectDetails --research JSON')
p.add_argument('output', type=Path)
a = p.parse_args()
sha = lambda data: hashlib.sha256(data).hexdigest()
exe = a.exe.read_bytes()
assert sha(exe) == '9545e8732919bb6a63904cb73223641b3c4f9a67869be5722612acca413e8b3a'
x = json.loads(a.discovery.read_text())
effects = json.loads(a.effects.read_text())
assert x['hashes']['regulation.bin'] == effects['hashes']['regulation.bin'] == '3305ac374b4da1db440e2b6644bc2c3c0ae96b98df9627f1a0e7a2b06d265c06'
pe = pefile.PE(data=exe, fast_load=True)
BASE = pe.OPTIONAL_HEADER.ImageBase
OBJ, STACK, STOP = 0x10000000, 0x20000000, 0x30000000
TABLE, VECTOR, USED = OBJ + 0x100000, OBJ + 0x10000, OBJ + 0x20000

def raw_table(path):
    raw = path.read_bytes()
    count = struct.unpack_from('<H', raw, 10)[0]
    rows = [(struct.unpack_from('<i', raw, 0x40 + i * 24)[0],
             struct.unpack_from('<Q', raw, 0x48 + i * 24)[0]) for i in range(count)]
    return raw, rows

lot_raw, lot_rows = raw_table(a.discovery.with_suffix('.ItemTableParam.param'))
hero_raw, hero_rows = raw_table(a.discovery.with_suffix('.HeroParam.param'))
sp_raw, sp_rows = raw_table(a.effects.with_suffix('.SpEffectParam.param'))
heroes = {id: hero_raw[offset:offset + 0xa8] for id, offset in hero_rows}
spells = {id: sp_raw[offset:offset + 0x400] for id, offset in sp_rows}
ordered = x['orderedTables']['ItemTableParam']
assert len(ordered) == len(lot_rows) == 35755
groups = collections.defaultdict(list)
for index, ((id, offset), decoded) in enumerate(zip(lot_rows, ordered)):
    assert id == decoded['id']
    r = decoded['fields']
    for name, pos, fmt in [('itemCategory',4,'i'), ('itemId',8,'i'), ('chanceWeight',12,'H'),
                            ('onlyForClass',15,'B'), ('eventFlagId',16,'i'), ('unknown_6',20,'i'),
                            ('unknown_7',24,'i'), ('weaponTypeDiscovery',32,'i')]:
        assert struct.unpack_from('<' + fmt, lot_raw, offset + pos)[0] == r[name]
    groups[id].append(index)
for indices in groups.values():
    assert indices == list(range(indices[0], indices[0] + len(indices)))
for id, row in heroes.items():
    assert struct.unpack_from('<i', row, 0x98)[0] == x['tables']['HeroParam'][str(id)]['defaultWeaponTypeDiscovery']
bias_roots = {int(id): int(r['weaponTypeDiscovery']) for id, r in effects['tables']['SpEffectParam'].items() if r['stateInfo'] == 2122}
stubs = set()

def execute(rva, args, setup, random=0.5, active_flags=()):
    u = Uc(UC_ARCH_X86, UC_MODE_64)
    u.mem_map(OBJ, 0x800000); u.mem_map(STACK, 0x10000); u.mem_map(STOP, 0x1000)
    u.mem_write(OBJ + 0x9000, struct.pack('<Q', OBJ + 0x9100))
    u.mem_write(OBJ + 0x9118, struct.pack('<Q', STOP + 0x100))
    u.mem_write(OBJ + 0x9168, struct.pack('<Q', STOP + 0x108))
    u.mem_write(OBJ + 0x9180, struct.pack('<I', 32))
    sp = STACK + 0x8008
    u.mem_write(sp, struct.pack('<Q', STOP)); u.reg_write(UC_X86_REG_RSP, sp)
    for reg, value in zip([UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8, UC_X86_REG_R9], args):
        u.reg_write(reg, value & 0xffffffffffffffff)
    setup(u)
    cumulative = []
    def mapped(uc, access, address, size, value, user):
        page = address & ~4095
        assert BASE <= page < BASE + pe.OPTIONAL_HEADER.SizeOfImage, (hex(address),hex(uc.reg_read(UC_X86_REG_RIP)-BASE))
        uc.mem_map(page, 4096); uc.mem_write(page, pe.get_data(page - BASE, 4096).ljust(4096, b'\0'))
        # Synthetic flag-manager handle; flag queries are explicit test inputs.
        if page <= BASE + 0x3c115a8 < page + 4096:
            uc.mem_write(BASE + 0x3c115a8, struct.pack('<Q', OBJ + 0x9200))
        return True
    def code(uc, address, size, user):
        def finish(value=0):
            uc.reg_write(UC_X86_REG_RAX, value)
            sp = uc.reg_read(UC_X86_REG_RSP)
            uc.reg_write(UC_X86_REG_RIP, struct.unpack('<Q', uc.mem_read(sp,8))[0])
            uc.reg_write(UC_X86_REG_RSP, sp + 8)
        pc = address - BASE
        if pc == 0xe785b0:
            stubs.add('E785B0 HeroParam lookup using actual row bytes')
            id = uc.reg_read(UC_X86_REG_RDX) & 255
            uc.mem_write(OBJ + 0x8000, heroes[id])
            uc.mem_write(uc.reg_read(UC_X86_REG_RCX), struct.pack('<IIQ', id,0,OBJ+0x8000))
            finish()
        elif pc == 0xe782e0:
            stubs.add('E782E0 HeroParam wrapper cleanup'); finish()
        elif pc == 0x214f3e0:
            stubs.add('214F3E0 allocator fixture'); finish(OBJ + 0x9000)
        elif address == STOP + 0x100:
            stubs.add('allocator flags'); finish(OBJ + 0x9180)
        elif address == STOP + 0x108:
            stubs.add('allocator free'); finish()
        elif pc == 0xe79b00:
            stubs.add('E79B00 reserve empty cumulative-weight vector')
            count = uc.reg_read(UC_X86_REG_RDX)
            assert count < 1000
            uc.mem_write(uc.reg_read(UC_X86_REG_RCX)+8, struct.pack('<QQQ',VECTOR,VECTOR,VECTOR+count*8))
            finish()
        elif pc == 0x5ec580:
            stubs.add('5EC580 flag lookup context'); finish(uc.reg_read(UC_X86_REG_RCX))
        elif pc == 0x5e7260:
            stubs.add('5E7260 explicit active event flags')
            flag = struct.unpack('<i',uc.mem_read(uc.reg_read(UC_X86_REG_RDX),4))[0]
            finish(int(flag in active_flags))
        elif pc == 0x6af4f0:
            stubs.add('6AF4F0 random generator handle'); finish(OBJ + 0x9300)
        elif pc == 0xf561d0:
            stubs.add('F561D0 controlled random fraction')
            uc.reg_write(UC_X86_REG_XMM0, int.from_bytes(struct.pack('<f', random),'little')); finish()
        elif pc == 0xe798cb:
            bp = uc.reg_read(UC_X86_REG_RBP)
            start,end=struct.unpack('<QQ',uc.mem_read(bp-0x20,16))
            cumulative.extend(struct.iter_unpack('<II',uc.mem_read(start,end-start)))
    u.hook_add(UC_HOOK_MEM_UNMAPPED,mapped); u.hook_add(UC_HOOK_CODE,code)
    u.emu_start(BASE+rva,STOP,count=100000)
    assert u.reg_read(UC_X86_REG_RIP) == STOP
    return u,cumulative

def choose_bias(hero, ids, owner=True):
    def setup(u):
        u.mem_write(OBJ+0x190,struct.pack('<Q',OBJ+0x400))
        nodes=[OBJ+0x1000+i*0x600 for i in range(len(ids))]
        if nodes: u.mem_write(OBJ+0x408,struct.pack('<Q',nodes[0]))
        for i,(id,node) in enumerate(zip(ids,nodes)):
            u.mem_write(node+0x100,spells[id]);u.mem_write(node,struct.pack('<Q',node+0x100))
            if i+1<len(nodes):u.mem_write(node+0x38,struct.pack('<Q',nodes[i+1]))
    u,_=execute(0x56acf0,[OBJ+0x500,hero,OBJ if owner else 0],setup)
    result=struct.unpack('<i',u.mem_read(OBJ+0x510,4))[0]
    expected=next((bias_roots[id] for id in ids if id in bias_roots),x['tables']['HeroParam'][str(hero)]['defaultWeaponTypeDiscovery']) if owner else x['tables']['HeroParam'][str(hero)]['defaultWeaponTypeDiscovery']
    assert result==expected
    return dict(hero=hero,ids=ids,owner=owner,bias=result)

def draw(group,hero,bias,random=0.5,active_flags=(),used=()):
    indices=groups[group]
    def setup(u):
        u.mem_write(TABLE,lot_raw)
        u.mem_write(OBJ,struct.pack('<Qiiii',TABLE,indices[0],indices[-1]+1,group,len(indices)))
        u.mem_write(OBJ+0x500,struct.pack('<QQQQ',0,USED,USED+12*len(used),USED+0x1000))
        for i,row in enumerate(used):u.mem_write(USED+i*12,struct.pack('<iii',*row))
    u,cumulative=execute(0xe79680,[OBJ,hero,bias,OBJ+0x500],setup,random,active_flags)
    expected=[];total=0
    for n,i in enumerate(indices):
        r=ordered[i]['fields']
        if r['onlyForClass'] not in (0,hero) or r['weaponTypeDiscovery'] not in (-1,bias):continue
        if r['eventFlagId'] and (0 if r['eventFlagId']==-1 else r['eventFlagId']) not in active_flags:continue
        # +0x1c is padding in the current definition; verify actual runtime bytes.
        offset=lot_rows[i][1]
        exclude=struct.unpack_from('<i',lot_raw,offset+0x1c)[0]
        if exclude and (0 if exclude==-1 else exclude) in active_flags:continue
        if r['unknown_7'] & 1 and any((v[0]==r['unknown_6'] if r['unknown_6']!=-1 else v[1:]==(r['itemCategory'],r['itemId'])) for v in used):continue
        total+=int(r['chanceWeight']);expected.append((n,total))
    assert cumulative==expected,(group,hero,bias,cumulative,expected)
    result=u.reg_read(UC_X86_REG_RAX)&0xffffffff
    if total:
        f32=lambda n:struct.unpack('<f',struct.pack('<f',n))[0]
        roll=int(f32(f32(random)*f32(total)))
        selected=next((n for n,limit in expected if roll<limit),expected[-1][0])
        assert result==selected
        selected_index=indices[selected]
    else:
        assert result==0xffffffff;selected_index=None
    return dict(group=group,hero=hero,bias=bias,random=random,activeFlags=list(active_flags),used=list(used),
                eligible=len(expected),totalWeight=total,candidates=[[indices[n],limit]for n,limit in expected],selectedIndex=selected_index)

selection=[]
roots=sorted(bias_roots)
for hero in heroes:
    selection.append(choose_bias(hero,[],False))
    selection.append(choose_bias(hero,[]))
    for root in roots:selection.append(choose_bias(hero,[root]))
for ids in ([7632300,7633000],[7633000,7632300],[7632300,7632300],[7000000,7632300]):
    selection.append(choose_bias(7,list(ids)))

# Cover every bias-bearing group in the current PARAM plus an unaffected group.
# Caller reachability is separate: PARAM presence is not proof of expedition use.
draws=[]
biased_groups=[id for id,indices in groups.items() if any(ordered[i]['fields']['weaponTypeDiscovery']!=-1 for i in indices)]
assert len(biased_groups)==39
for group in [*biased_groups,2003002]:
    for bias in sorted(set(bias_roots.values())|{1700,-1}):
        draws.append(draw(group,7,bias))
for hero in heroes:
    for bias in (x['tables']['HeroParam'][str(hero)]['defaultWeaponTypeDiscovery'],51,57):
        for random in (0,0.999999):draws.append(draw(3000200,hero,bias,random))
for hero in (8,10):
    for flags in ((),(90107,)):draws.append(draw(2000,hero,51,active_flags=flags))
for used in ((),((-1,1,8000000),)):
    draws.append(draw(4200000,7,51,used=used))

used_indices=sorted({i for d in draws for i,_ in d['candidates']}|{d['selectedIndex'] for d in draws if d['selectedIndex'] is not None})
snapshot=[dict(index=i,id=ordered[i]['id'],fields=ordered[i]['fields'])for i in used_indices]
a.output.write_text(json.dumps(dict(schema=1,exeSha256=sha(exe),regulationSha256=x['hashes']['regulation.bin'],
    paramSha256={'ItemTableParam':sha(lot_raw),'HeroParam':sha(hero_raw),'SpEffectParam':sha(sp_raw)},
    definitionHashes={k:v for k,v in x['hashes'].items() if k.startswith('defs/')},
    rowCount=len(ordered),groupCount=len(groups),biasedGroups=biased_groups,selection=selection,draws=draws,rows=snapshot,
    stubs=sorted(stubs),gameplayVerified=False),ensure_ascii=False,indent=2)+'\n')
print(f'PASS: bias selection={len(selection)}, native weighted draws={len(draws)}, ordered rows={len(ordered)}')
