"""Build compact, provenance-checked effect details. Never infer stacking from filter flags.

--extract accepts the private output of ExtractEffectDetails and writes a minimal
source snapshot. Without it, rebuild using the committed snapshot only.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--extract', type=Path)
args = parser.parse_args()
profile = json.loads((ROOT / 'data/source-profile.json').read_text())
catalog = json.loads((ROOT / 'web/src/data/catalog.json').read_text())

# Only fields with understood units enter the human-readable summary.
RATES = {
    'maxHpRate': '血量上限', 'maxMpRate': '专注值上限', 'maxStaminaRate': '精力上限',
    'physicsAttackRate': '物理攻击倍率', 'magicAttackRate': '魔力攻击倍率',
    'fireAttackRate': '火攻击倍率', 'thunderAttackRate': '雷攻击倍率', 'darkAttackRate': '圣攻击倍率',
    'slashDamageCutRate': '斩击承伤', 'blowDamageCutRate': '打击承伤', 'thrustDamageCutRate': '突刺承伤',
    'neutralDamageCutRate': '普通物理承伤', 'magicDamageCutRate': '魔力承伤',
    'fireDamageCutRate': '火承伤', 'thunderDamageCutRate': '雷承伤', 'darkDamageCutRate': '圣承伤',
    'magicConsumptionRate': '魔法 FP 消耗', 'miracleConsumptionRate': '祷告 FP 消耗',
    'shamanConsumptionRate': '特殊法术 FP 消耗', 'artsConsumptionRate': '战技 FP 消耗',
    'staminaAttackRate': '精力伤害', 'soulRate': '获得卢恩',
}
POINTS = {
    'addLifeForceStatus': '生命力', 'addWillpowerStatus': '集中力', 'addEndureStatus': '耐力',
    'addStrengthStatus': '力气', 'addDexterityStatus': '灵巧', 'addMagicStatus': '智力',
    'addFaithStatus': '信仰', 'addLuckStatus': '感应',
    'physicsAttackPower': '物理基础攻击力', 'magicAttackPower': '魔力基础攻击力',
    'fireAttackPower': '火基础攻击力', 'thunderAttackPower': '雷基础攻击力', 'darkAttackPower': '圣基础攻击力',
    'ultimateArtGauge': '绝招量表（参数单位）',
}
RESTORE = {'changeHpPoint': 'HP', 'changeMpPoint': 'FP', 'changeStaminaPoint': '精力'}
LINKS = {
    'applyIdOnKillSp': '击杀触发分支', 'applyIdOnGetSoul': '获得卢恩触发分支',
    'cycleOccurrenceSpEffectId': '周期触发分支', 'replaceSpEffectId': '替换效果分支',
    'atkOccurrenceSpEffectId': '攻击触发分支', 'accumuOverFireId': '累积触发分支',
}
ROOTS = {'passiveSpEffectId_1': '生效时', 'passiveSpEffectId_2': '生效时',
         'passiveSpEffectId_3': '生效时', 'onHitSpEffect': '命中效果'}
META = ['effectEndurance', 'motionInterval', 'spCategory', 'categoryPriority', 'stateInfo',
        'magParamChange', 'miracleParamChange', 'shamanParamChange', 'wepParamChange',
        'magicSubCategoryChange1', 'magicSubCategoryChange2', 'magicSubCategoryChange3',
        'invocationConditionsStateChange1', 'invocationConditionsStateChange2', 'invocationConditionsStateChange3',
        'wepTypeTrigger', 'wepTypeTriggerCount', 'conditionHp', 'conditionHpRate']
FIELDS = set(RATES) | set(POINTS) | set(RESTORE) | set(LINKS) | set(META)
source_path = ROOT / 'data/effect-detail-source.json'
if args.extract:
    raw = json.loads(args.extract.read_text())
    assert raw['hashes']['regulation.bin'] == profile['input_sha256']['regulation.bin']
    assert raw['regulationVersion'] == profile['regulation_version']
    attaches = raw['tables']['AttachEffectParam']
    spells = raw['tables']['SpEffectParam']
    effects = {}
    needed = set()
    for id in catalog['effects']:
        a = attaches[id]
        roots = {field: int(a[field]) for field in ROOTS if a[field] > 0}
        needed.update(roots.values())
        text_id = str(int(a['attachTextId']))
        info = raw['texts']['zh_CN']['AttachEffectInfo'].get(text_id)
        effects[id] = dict(roots=roots, **({'info': info} if info else {}))
    pending = list(needed)
    while pending:
        row = spells.get(str(pending.pop()), {})
        for field in LINKS:
            id = int(row.get(field, -1))
            if id > 0 and str(id) in spells and id not in needed:
                needed.add(id)
                pending.append(id)
    source = dict(schema=1, regulationVersion=raw['regulationVersion'], hashes=raw['hashes'], effects=effects,
                  spells={str(id): {k: round(v, 6) for k, v in spells[str(id)].items() if k in FIELDS}
                          for id in sorted(needed) if str(id) in spells})
    source_path.write_text(json.dumps(source, ensure_ascii=False, separators=(',', ':')) + '\n')
source = json.loads(source_path.read_text())
assert source['schema'] == 1
assert source['hashes']['regulation.bin'] == catalog['regulationSha256'] == profile['input_sha256']['regulation.bin']
assert source['regulationVersion'] == catalog['regulationVersion']


def num(v):
    return f'{round(v, 3):g}'


def signed(v):
    return ('+' if v > 0 else '') + num(v)


def stats(row):
    values = []
    rate_fields = set(RATES)
    for fields, label in [
        (['physicsAttackRate', 'magicAttackRate', 'fireAttackRate', 'thunderAttackRate', 'darkAttackRate'], '全属性攻击倍率'),
        (['slashDamageCutRate', 'blowDamageCutRate', 'thrustDamageCutRate', 'neutralDamageCutRate'], '物理承伤'),
    ]:
        numbers = [row.get(k, 1) for k in fields]
        if len(set(numbers)) == 1 and numbers[0] != 1:
            values.append([label, signed((numbers[0] - 1) * 100) + '%'])
            rate_fields.difference_update(fields)
    for field, label in RATES.items():
        v = row.get(field, 1)
        if field in rate_fields and v != 1:
            values.append([label, signed((v - 1) * 100) + '%'])
    for field, label in POINTS.items():
        if v := row.get(field, 0):
            values.append([label, signed(v)])
    for field, label in RESTORE.items():
        if v := row.get(field, 0):
            values.append([label + ('恢复' if v < 0 else '消耗'), num(abs(v))])
    return values


def block(id, phase, linked):
    r = source['spells'].get(str(id), {})
    values = stats(r)
    if not values:
        return None
    scope = []
    if any('AttackRate' in k and r.get(k, 1) != 1 for k in RATES):
        # This is the allowed spell channel, not a proof that every attack of that channel qualifies.
        scope = [name for key, name in [('magParamChange', '魔法'), ('miracleParamChange', '祷告'),
                                      ('shamanParamChange', '特殊法术')] if r.get(key) == 1]
    restrictions = []
    if any(r.get('magicSubCategoryChange' + str(i), 0) for i in (1, 2, 3)):
        restrictions.append('限指定法术类别')
    if any(r.get('invocationConditionsStateChange' + str(i), 0) for i in (1, 2, 3)):
        restrictions.append('需满足指定状态')
    # Timer is attached to this node, never interpreted as a cooldown or total uptime.
    return dict(source=id, phase=phase, linked=linked, values=values, scope=scope, restrictions=restrictions,
                duration=r.get('effectEndurance', 0) if r.get('effectEndurance', 0) > 0 else None,
                interval=r.get('motionInterval', 0) if r.get('motionInterval', 0) > 0 else None)

result = {}
for id, effect in source['effects'].items():
    blocks, seen = [], set()
    pending = [(v, ROOTS[k], False, 0) for k, v in effect['roots'].items()]
    while pending:
        sp, phase, linked, depth = pending.pop(0)
        if sp in seen:
            continue
        seen.add(sp)
        if b := block(sp, phase, linked):
            blocks.append(b)
        if depth < 6:
            r = source['spells'].get(str(sp), {})
            pending.extend((int(r[k]), label, True, depth + 1) for k, label in LINKS.items() if r.get(k, -1) > 0)
    notes = []
    stacking = '跨遗物叠加尚未确认'
    # User-confirmed pairing; deliberately not generalized to duplicate copies or other tiers.
    if id in ('7090000', '6090000'):
        stacking = '普通版与＋１版可叠加（使用反馈）；同版重复待确认'
    if id in ('7034200', '7034201'):
        notes.append('混合魔法的其他强化效果尚未解明。')
    result[id] = dict(info=effect.get('info'), blocks=blocks, stacking=stacking, notes=notes)
output = dict(schema=1, regulationSha256=source['hashes']['regulation.bin'], effects=result)
out = ROOT / 'web/src/data/effect-details.json'
out.write_text(json.dumps(output, ensure_ascii=False, separators=(',', ':')) + '\n')
obtainable = {str(e) for r in catalog['relics'].values() if r['obtainable'] for p in r['pools'] for e in catalog['pools'].get(str(p), [])}
print(f'{len(result)} details; {sum(bool(result[e]["blocks"]) for e in obtainable)}/{len(obtainable)} obtainable effects with decoded numeric fields; {out.stat().st_size} bytes')
