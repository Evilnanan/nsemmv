"""Normalize pinned PARAM/FMG resources for the browser; no editor runtime imports."""
import csv, hashlib, json, argparse, xml.etree.ElementTree as ET
from pathlib import Path
root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('resources', type=Path);res=parser.parse_args().resources
profile=json.loads((root/'data/source-profile.json').read_text(encoding='utf-8'))
for name,digest in profile['resource_sha256'].items():
    assert hashlib.sha256((res/name).read_bytes()).hexdigest()==digest, name

def table(name):
    with (res/'Param'/f'{name}.csv').open(encoding='utf-8-sig', newline='') as f:
        return [{k:int(v) for k,v in r.items()} for r in csv.DictReader(f)]
def text(locale,kind):
    result={}
    for suffix in ('','_dlc01'):
        for el in ET.parse(res/'Text'/locale/f'{kind}{suffix}.fmg.xml').findall('./entries/text'):
            if el.text and el.text!='%null%':result[int(el.attrib['id'])]=el.text.strip()
    return result
names={l:{k:text(l,k) for k in ('AttachEffectName','AntiqueName','GoodsName')} for l in ('zh_CN','en_US')}
def label(kind,id):return {l:names[l][kind].get(id,str(id)) for l in names}
pools={}
for r in table('AttachEffectTableParam'):
    weight=r['chanceWeight'] if r['chanceWeight_dlc']==-1 else r['chanceWeight_dlc']
    if weight>0 and r['attachEffectId']>=0:pools.setdefault(str(r['ID']),set()).add(r['attachEffectId'])
filters=json.loads((root/'data/effect-filter-source.json').read_text(encoding='utf-8'))
assert filters['schema']==1 and filters['regulationVersion']==profile['regulation_version']
assert filters['hashes']['regulation.bin']==profile['input_sha256']['regulation.bin']
def filter_label(id):return {locale:labels[str(id)] for locale,labels in filters['texts'].items()}
categories={str(r['ID']):dict(id=r['ID'],name=filter_label(r['textId'])) for r in filters['tables']['AttachEffectFilterCategoryParam'] if r['textId']>=0}
groups={str(r['ID']):dict(id=r['ID'],category=r['filterCategory'],name=filter_label(r['textId'])) for r in filters['tables']['AttachEffectFilterSubCategoryParam'] if r['textId']>=0}
assert all(str(g['category']) in categories for g in groups.values())
filter_rows={r['ID']:r for r in filters['tables']['AttachEffectFilterParam']}
def effect_group(row):
    group=filter_rows.get(row['attachFilterParamId'],{}).get('attachEffectFilterCategory')
    return group if str(group) in groups else None
effects={str(r['ID']):dict(id=r['ID'],name=label('AttachEffectName',r['attachTextId']),conflict=r['compatibilityId'],exclusive=r['exclusivityId'],sort=r['overrideEffectId'],filterId=r['attachFilterParamId'],group=effect_group(r)) for r in table('AttachEffectParam')}
relics={}
for r in table('EquipParamAntique'):
    id=r['ID'];sources=profile['obtainable_relics'].get(str(id),[])
    relics[str(id)]=dict(id=id,name=label('AntiqueName',id),color=r['relicColor'],deep=bool(r['isDeepRelic']),obtainable=bool(sources),salable=bool(r['isSalable']),shop=not bool(r['isSalable']),pools=[r[f'attachEffectTableId_{i}'] for i in (1,2,3)]+[r[f'attachEffectTableId_curse{i}'] for i in (1,2,3)])
vessels={str(r['ID']):dict(id=r['ID'],name=label('GoodsName',r['goodsId']),hero=r['heroType'],goods=r['goodsId'],unlockFlag=r['unlockFlag'],colors=[r[f'relicSlot{i}'] for i in (1,2,3)]+[r[f'deepRelicSlot{i}'] for i in (1,2,3)]) for r in table('AntiqueStandParam')}
result=dict(schema=1,profile=profile['name'],regulationVersion=profile['regulation_version'],regulationSha256=profile['input_sha256']['regulation.bin'],effects=effects,effectCategories=categories,effectGroups=groups,relics=relics,vessels=vessels,pools={k:sorted(v) for k,v in sorted(pools.items(),key=lambda x:int(x[0]))})
out=root/'web/src/data/catalog.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
print(f'{out}: {out.stat().st_size} bytes; {len(relics)} relic definitions')
