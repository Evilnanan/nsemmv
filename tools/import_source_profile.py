"""Normalize a pinned ExtractEffectDetails export into catalog inputs.

Repeated PARAM group IDs are retained. FMG base/DLC overrides are already merged
by the extractor; the generated XML pair contains the merged table and an empty
DLC overlay. The full private export and CSV/XML inputs are not committed.
"""
import argparse
import csv
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUPPORTED = {
    '3305ac374b4da1db440e2b6644bc2c3c0ae96b98df9627f1a0e7a2b06d265c06': 'Daybreak 2.1.9 Beta2-Release',
    'f7c39ad0cad7653530df4c119b96c9b09abc0d38dccf32dd649275a160bf0342': 'Daybreak 2.1.9 Beta2-Hotfix1',
}
TABLES = ('AttachEffectParam', 'AttachEffectTableParam', 'EquipParamAntique', 'AntiqueStandParam',
          'ItemLotParam_map', 'ItemLotParam_enemy', 'ItemTableParam', 'ShopLineupParam')


def rows(source, name):
    return ([dict(ID=int(i), **r) for i, r in source['tables'].get(name, {}).items()] +
            [dict(ID=r['id'], **r['fields']) for r in source.get('orderedTables', {}).get(name, [])])


def obtainable(source):
    relics = source['tables']['EquipParamAntique']
    result = {}

    def add(item, reference):
        key = str(int(item))
        if key in relics:
            result.setdefault(key, set()).add(reference)

    for name in ('ItemLotParam_map', 'ItemLotParam_enemy'):
        for row in rows(source, name):
            for slot in range(1, 9):
                suffix = f'{slot:02}'
                if (row['lotItemCategory' + suffix] == 5 and row['lotItemBasePoint' + suffix] > 0
                        and row['lotItemNum' + suffix] > 0):
                    add(row['lotItemId' + suffix], f'{name}:{row["ID"]}:{slot}')
    for row in rows(source, 'ShopLineupParam'):
        if row['equipType'] == 4 and row['setNum'] > 0 and row['sellQuantity'] != 0:
            add(row['equipId'], f'ShopLineupParam:{row["ID"]}')
    for row in rows(source, 'ItemTableParam'):
        if row['itemCategory'] == 5 and row['chanceWeight'] > 0 and row['quantity'] > 0:
            add(row['itemId'], f'ItemTableParam:{row["ID"]}')
    return {i: sorted(result[i]) for i in sorted(result, key=int)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('extracted', type=Path)
    parser.add_argument('resources', type=Path)
    parser.add_argument('--profile', type=Path, default=ROOT / 'data/source-profile.json')
    args = parser.parse_args()
    source = json.loads(args.extracted.read_text())
    digest = source['hashes']['regulation.bin']
    assert digest in SUPPORTED and source['regulationVersion'] == '10350000'
    resources = args.resources
    (resources / 'Param').mkdir(parents=True, exist_ok=True)
    for name in TABLES[:4]:
        records = sorted(rows(source, name), key=lambda r: r['ID'])
        with (resources / 'Param' / f'{name}.csv').open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(records[0]))
            writer.writeheader()
            for record in records:
                assert all(float(v).is_integer() for v in record.values()), name
                writer.writerow({k: int(v) for k, v in record.items()})
    for locale in ('zh_CN', 'en_US'):
        directory = resources / 'Text' / locale
        directory.mkdir(parents=True, exist_ok=True)
        for kind in ('AntiqueName', 'AttachEffectName', 'GoodsName', 'NpcName'):
            for suffix in ('', '_dlc01'):
                root = ET.Element('fmg'); entries = ET.SubElement(root, 'entries')
                if not suffix:
                    for id, value in source['texts'][locale][kind].items():
                        ET.SubElement(entries, 'text', id=id).text = value
                ET.ElementTree(root).write(directory / f'{kind}{suffix}.fmg.xml', encoding='utf-8', xml_declaration=True)
    hashes = {p.relative_to(resources).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(resources.rglob('*')) if p.is_file()}
    profile = dict(schema_version=1, name=SUPPORTED[digest], save_filename='NR0000.dbb',
                   regulation_version=source['regulationVersion'], input_sha256=source['hashes'],
                   obtainable_relics=obtainable(source),
                   row_counts={name: len(rows(source, name)) for name in TABLES}, resource_sha256=hashes)
    args.profile.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + '\n')
    print(f'{profile["name"]}: {profile["row_counts"]["EquipParamAntique"]} relics, '
          f'{len(profile["obtainable_relics"])} obtainable IDs')


if __name__ == '__main__':
    main()
