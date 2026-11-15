"""Generate deterministic rule fixtures directly from pinned CSV inputs (no web imports)."""
import argparse
import csv
import hashlib
import itertools
import json
import random
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
EMPTY = 0xffffffff

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('resources',type=Path);a=p.parse_args()
    profile=json.loads((ROOT/'data/source-profile.json').read_text())
    for name,h in profile['resource_sha256'].items():
        assert hashlib.sha256((a.resources/name).read_bytes()).hexdigest()==h,name
    def table(name):
        with (a.resources/'Param'/f'{name}.csv').open(newline='') as f:
            return [{k:int(v) for k,v in row.items()} for row in csv.DictReader(f)]
    effects={r['ID']:r for r in table('AttachEffectParam')};items={r['ID']:r for r in table('EquipParamAntique')}
    pools={-1:{EMPTY}}
    for row in table('AttachEffectTableParam'):
        weight=row['chanceWeight_dlc'] if row['chanceWeight_dlc']!=-1 else row['chanceWeight']
        if weight>0 and row['attachEffectId']>=0:pools.setdefault(row['ID'],set()).add(row['attachEffectId'])
    def conflict(a,b):
        return a==b or any(effects[a][k]!=-1 and effects[a][k]==effects[b][k] for k in ('compatibilityId','exclusivityId'))
    def order(v):
        return sorted(zip(v[:3],v[3:]),key=lambda p:(effects[p[0]]['overrideEffectId'],p[0]) if p[0]!=EMPTY else (float('inf'),EMPTY))
    def sorted_values(v):
        pairs=order(v);return [p[0] for p in pairs]+[p[1] for p in pairs]
    def ids(item):return [item[f'attachEffectTableId_{i}'] for i in (1,2,3)]+[item[f'attachEffectTableId_curse{i}'] for i in (1,2,3)]
    def valid(id,v):
        v=[EMPTY if x==0 else x for x in v];present=[x for x in v if x!=EMPTY]
        if any(x not in effects for x in present) or any(conflict(x,y) for x,y in itertools.combinations(present,2)):return False
        if v!=sorted_values(v):return False
        return any(all(v[permutation[j%3]+(3 if j>=3 else 0)] in pools.get(pool,set()) for j,pool in enumerate(ids(items[id]))) for permutation in itertools.permutations(range(3)))
    rng=random.Random(2191)
    def sample(id):
        candidates=[sorted(pools.get(pool,set())) for pool in ids(items[id])]
        for row in candidates:rng.shuffle(row)
        selected=[]
        def visit(index):
            if index==6:return sorted_values(selected)
            for value in candidates[index]:
                if value!=EMPTY and any(other!=EMPTY and conflict(value,other) for other in selected):continue
                selected.append(value);result=visit(index+1)
                if result is not None:return result
                selected.pop()
            return None
        return visit(0)
    result=[]
    for id in sorted(map(int,profile['obtainable_relics'])):
        first=sample(id);assert first is not None, f'No legal roll for {id}'
        second=sample(id);missing=first.copy();missing[0]=EMPTY
        unknown=first.copy();unknown[0]=99999999
        reversed_pairs=[*first[:3][::-1],*first[3:][::-1]]
        cases=[first,[0 if v==EMPTY else v for v in first],second,missing,unknown,reversed_pairs]
        for values in cases:result.append(dict(id=id,values=values,valid=valid(id,values)))
        assert result[-6]['valid'] and result[-4]['valid']
    (ROOT/'web/tests/mmv-oracle.json').write_text(json.dumps(result,separators=(',',':'))+'\n')
    print(f'{len(result)} independent outcomes covering {len(profile["obtainable_relics"])} IDs')

if __name__=='__main__':main()
