"""Build compact, provenance-checked effect details. Never infer stacking from filter flags.

--extract accepts the private output of ExtractEffectDetails and writes a minimal
source snapshot. Without it, rebuild using the committed snapshot only.
"""
import argparse
import json
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--extract', type=Path)
args = parser.parse_args()
profile = json.loads((ROOT / 'data/source-profile.json').read_text())
catalog = json.loads((ROOT / 'web/src/data/catalog.json').read_text())
trigger_path = ROOT / 'data/effect-trigger-source.json'
triggers = json.loads(trigger_path.read_text())
assert triggers['schema'] == 1 and triggers['regulationSha256'] == catalog['regulationSha256']
link_path = ROOT / 'data/effect-link-source.json'
links = json.loads(link_path.read_text())
assert links['schema'] == 1 and links['regulationSha256'] == catalog['regulationSha256']
script_path = ROOT / 'data/effect-script-evidence.json'
scripts = json.loads(script_path.read_text())
assert scripts['schema'] == 1 and scripts['regulationSha256'] == catalog['regulationSha256']
growth_path = ROOT / 'data/effect-growth-source.json'
growth = json.loads(growth_path.read_text())
assert growth['schema'] == 1 and growth['regulationSha256'] == catalog['regulationSha256']

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
    'characterSkillCooldownReduction': '技艺冷却时间',
    'ultimateArtGaugeRate': '绝招量表自然累积', 'ultimateArtGaugeChargeRate': '攻击／效果的绝招累积',
    'changeHpEstusFlaskCorrectRate': '圣杯瓶 HP 恢复量',
    'consumeStaminaRate': '精力消耗', 'toughnessDamageCutRate': '强韧度损耗',
    'saAttackPowerRate': '削韧倍率', 'regainRate': '血量回收倍率',
    'extendLifeRate': '魔法／祷告有效时间',
}
POINTS = {
    'addLifeForceStatus': '生命力', 'addWillpowerStatus': '集中力', 'addEndureStatus': '耐力',
    'addStrengthStatus': '力气', 'addDexterityStatus': '灵巧', 'addMagicStatus': '智力',
    'addFaithStatus': '信仰', 'addLuckStatus': '感应',
    'physicsAttackPower': '物理基础攻击力', 'magicAttackPower': '魔力基础攻击力',
    'fireAttackPower': '火基础攻击力', 'thunderAttackPower': '雷基础攻击力', 'darkAttackPower': '圣基础攻击力',
    'changePoisonResistPoint': '抗毒', 'changeDiseaseResistPoint': '抗腐败',
    'changeBloodResistPoint': '抗出血', 'changeCurseResistPoint': '抗骤死',
    'changeFreezeResistPoint': '抗冻伤', 'changeSleepResistPoint': '抗催眠',
    'changeMadnessResistPoint': '抗发狂', 'additionalCharacterSkillUse': '技艺使用次数',
    'staminaRecoverChangeSpeed': '精力恢复速度',
    'soul': '获得卢恩',
}
RESTORE = {'changeHpPoint': 'HP', 'changeMpPoint': 'FP', 'changeStaminaPoint': '精力'}
STATUS_BUILDUP = {'poizonAttackPower': '中毒', 'diseaseAttackPower': '猩红腐败',
                  'freezeAttackPower': '冻伤', 'bloodAttackPower': '出血',
                  'madnessAttackPower': '发狂', 'sleepAttackPower': '催眠', 'curseAttackPower': '死亡'}
LINKS = {
    'applyIdOnKillSp': '击杀触发分支', 'applyIdOnGetSoul': '获得卢恩触发分支',
    'cycleOccurrenceSpEffectId': '周期触发分支', 'replaceSpEffectId': '替换效果分支',
    'atkOccurrenceSpEffectId': '攻击触发分支', 'accumuOverFireId': '累积触发分支',
    'necromancyActivationSpEffectId': '能力触发效果',
    'analyzeAcquire_effectId': '获得样本时',
    'analyzeSelfLevel1_effectId': '技艺对自己使用 · 第 1 档',
    'analyzeSelfLevel2_effectId': '技艺对自己使用 · 第 2 档',
    'analyzeSelfLevel3_effectId': '技艺对自己使用 · 第 3 档',
}
ROOTS = {'passiveSpEffectId_1': '生效时', 'passiveSpEffectId_2': '生效时',
         'passiveSpEffectId_3': '生效时', 'onHitSpEffect': '命中效果'}
META = ['effectEndurance', 'motionInterval', 'spCategory', 'categoryPriority', 'stateInfo',
        'magParamChange', 'miracleParamChange', 'shamanParamChange', 'wepParamChange',
        'magicSubCategoryChange1', 'magicSubCategoryChange2', 'magicSubCategoryChange3',
        'invocationConditionsStateChange1', 'invocationConditionsStateChange2', 'invocationConditionsStateChange3',
        'wepTypeTrigger', 'wepTypeTriggerCount', 'conditionHp', 'conditionHpRate',
        'changeHpRate', 'changeMpRate', 'changeStaminaRate', 'startGoodsId', 'startingItemAmount',
        'startMagicId', 'startSwordArtsId', 'weaponTypeDiscovery', 'heroStatusModifier',
        'accumuOverVal', 'accumuVal', 'dedupeAccumuTrigger', 'behaviorId', 'ultimateArtGauge', 'deleteCriteriaDamage',
        'runeDiscountValue', 'itemDropRate']
FIELDS = set(RATES) | set(POINTS) | set(RESTORE) | set(LINKS) | set(META) | set(STATUS_BUILDUP)
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
        for root in roots.values():
            needed.update(triggers['roots'].get(str(root), {}).get('seeds', []))
            for branch in scripts['effects'].get(str(root), {}).get('branches', []):
                needed.add(branch['cooldown'])
                for hand in branch['hands']:
                    needed.update((hand['seed'], hand['leaf']))
            for ladder in growth['roots'].get(str(root), {}).get('ladders', []):
                needed.update(ladder['stages'])
                needed.add(ladder['grant'])
        text_id = str(int(a['attachTextId']))
        info = raw['texts']['zh_CN']['AttachEffectInfo'].get(text_id)
        effects[id] = dict(roots=roots, runtimeExclusive=int(a['exclusivityId']), **({'info': info} if info else {}))
    pending = list(needed)
    while pending:
        current = pending.pop()
        row = spells.get(str(current), {})
        for leaf in links['emitters'].get(str(current), {}).get('leaves', []):
            if leaf not in needed:
                needed.add(leaf)
                pending.append(leaf)
        for field in LINKS:
            id = int(row.get(field, -1))
            if id > 0 and str(id) in spells and id not in needed:
                needed.add(id)
                pending.append(id)
    source = dict(schema=1, regulationVersion=raw['regulationVersion'], hashes=raw['hashes'], effects=effects,
                  labels={k: raw['texts']['zh_CN'][k] for k in ('GoodsName', 'MagicName', 'SwordArtsName')},
                  artsTextIds={id: int(r['textId']) for id, r in raw['tables']['SwordArtsParam'].items()},
                  heroStatus=raw['tables']['HeroStatusParam'],
                  spells={str(id): {k: round(v, 6) for k, v in spells[str(id)].items() if k in FIELDS}
                          for id in sorted(needed) if str(id) in spells})
    source_path.write_text(json.dumps(source, ensure_ascii=False, separators=(',', ':')) + '\n')
source = json.loads(source_path.read_text())
assert source['schema'] == 1
assert source['hashes']['regulation.bin'] == catalog['regulationSha256'] == profile['input_sha256']['regulation.bin']
assert source['regulationVersion'] == catalog['regulationVersion']
assert set(source['effects']) == set(catalog['effects'])
evidence_path = ROOT / 'data/effect-native-evidence.json'
evidence = json.loads(evidence_path.read_text())
assert evidence['schema'] == 1
assert evidence['regulationSha256'] == source['hashes']['regulation.bin']
assert evidence['exeSha256'] == '9545e8732919bb6a63904cb73223641b3c4f9a67869be5722612acca413e8b3a'
assert all(evidence[k] for k in ('predicates', 'attributes', 'attack', 'defense', 'cooldown', 'discovery', 'gauge', 'hero',
                               'resistance', 'fpCost', 'skillUses', 'killMatching', 'killDispatch', 'gaugeApply',
                               'timing', 'recoveryTiming', 'damageStatus'))


def num(v):
    return f'{round(v, 3):g}'


def signed(v):
    return ('+' if v > 0 else '') + num(v)


def stats(row):
    values = []
    rate_fields = set(RATES)
    for fields, label in [
        (['physicsAttackRate', 'magicAttackRate', 'fireAttackRate', 'thunderAttackRate', 'darkAttackRate'], '攻击倍率'),
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
    if v := row.get('ultimateArtGauge', 0):
        values.append(['绝招量表', signed(v) + '%'])
    if row.get('stateInfo') == 2116 and (v := row.get('runeDiscountValue', 0)):
        values.append(['商店卢恩价格', signed(-v) + '%'])
    if row.get('stateInfo') == 66 and (v := row.get('itemDropRate', 0)):
        values.append(['观察力', signed(v * 100)])
    for field, label in RESTORE.items():
        if v := row.get(field, 0):
            # Fixed and proportional restoration may coexist on the same node.
            values.append([label + '定值' + ('恢复' if v < 0 else '消耗'), num(abs(v))])
    for field, label in [('changeHpRate', 'HP'), ('changeMpRate', 'FP'), ('changeStaminaRate', '精力')]:
        if v := row.get(field, 0):
            values.append([label + ('恢复' if v < 0 else '消耗'), '最大值的 ' + num(abs(v)) + '%'])
    if row.get('stateInfo') == 2102 and row.get('startingItemAmount', 0) > 0:
        item = source.get('labels', {}).get('GoodsName', {}).get(str(int(row['startGoodsId'])))
        if item:
            values.append([item, '×' + num(row['startingItemAmount'])])
    return values


ATTRIBUTE_LABELS = ['生命力', '集中力', '耐力', '力气', '灵巧', '智力', '信仰', '感应']


def hero_values(modifier):
    cases = sorted((r for r in evidence['hero'] if r['modifier'] == modifier), key=lambda r: r['level'])
    assert [r['level'] for r in cases] == list(range(1, 21))
    last_row = modifier
    while str(last_row + 1) in source['heroStatus']:
        last_row += 1
    assert source['heroStatus'][str(last_row)]['totalLevel'] <= 20
    groups = []
    for case in cases:
        if groups and groups[-1][2] == case['values']:
            groups[-1][1] = case['level']
        else:
            groups.append([case['level'], case['level'], case['values']])
    return [[f'{start} 级起' if end == 20 else (f'{start} 级' if start == end else f'{start}～{end} 级'),
             ' / '.join(label + ' ' + signed(v) for label, v in zip(ATTRIBUTE_LABELS, values) if v)]
            for start, end, values in groups]


ATTACK_FILTERS = {
    2: '卡利亚剑魔法', 3: '辉剑魔法', 4: '挖石魔法', 5: '结晶人魔法',
    9: '荆棘魔法', 11: '重力魔法', 12: '隐形魔法', 16: '混合魔法',
    20: '狩猎神祇祷告', 21: '巨人火焰祷告', 22: '王城古龙信仰祷告',
    23: '野兽祷告', 24: '黄金律法基本主义祷告', 25: '龙飨祷告', 26: '癫火祷告',
    100: '武器蓄力攻击', 102: '跳跃攻击', 103: '防御反击', 104: '连击末段',
    108: '投掷壶', 109: '调香术', 110: '法术蓄力', 111: '战技', 112: '战技',
    119: '轻攻击首段', 120: '投掷小刀', 121: '辉石／重力石道具',
    124: '双手共持', 125: '双手各持', 130: '近战攻击',
}


def block(id, phase, linked, known_states=frozenset()):
    r = source['spells'].get(str(id), {})
    values = stats(r)
    if r.get('stateInfo') == 2123:
        values.extend(hero_values(int(r['heroStatusModifier'])))
        phase = '随等级调整能力值'
    if r.get('stateInfo') in (2105, 2128):
        table, key = ('SwordArtsName', 'startSwordArtsId') if r['stateInfo'] == 2105 else ('MagicName', 'startMagicId')
        text_id = str(int(r.get(key, -1)))
        if table == 'SwordArtsName':
            text_id = str(source['artsTextIds'].get(text_id, -1))
        name = source.get('labels', {}).get(table, {}).get(text_id)
        if name:
            values.append(['出击时替换', name])
    if not values:
        return None
    scope = []
    if any('AttackRate' in k and r.get(k, 1) != 1 for k in RATES):
        # This is the allowed spell channel, not a proof that every attack of that channel qualifies.
        scope = [name for key, name in [('magParamChange', '魔法'), ('miracleParamChange', '祷告'),
                                      ('shamanParamChange', '特殊法术')] if r.get(key) == 1]
    restrictions = []
    if r.get('stateInfo') == 197:
        restrictions.append('适用：突刺反击')
    tags = [int(r.get('magicSubCategoryChange' + str(i), 0)) for i in (1, 2, 3)]
    if any(tags):
        labels = list(dict.fromkeys(ATTACK_FILTERS.get(tag, '指定攻击类别') for tag in tags if tag))
        restrictions.append('适用：' + ' / '.join(labels))
    if r.get('stateInfo') == 2102:
        phase = '出击时' if not r.get('invocationConditionsStateChange1', 0) else '额外发放条件待确认'
    if r.get('stateInfo') == 2100:
        restrictions.append('需装备对应类别武器 ≥ ' + num(r['wepTypeTriggerCount']) + ' 把')
    if r.get('conditionHp', -1) > 0:
        cases = [v for v in evidence['hpConditions'] if v['id'] == id]
        assert cases
        at_nominal = next(v for v in cases if v['ratio'] == v['nominal'])
        restrictions.append('血量 ' + ('≤ ' if at_nominal['enabled'] else '< ') + num(r['conditionHp']) + '%')
    if r.get('conditionHpRate', -1) > 0:
        assert any(v['id'] == id for v in evidence['hpConditions'])
        restrictions.append('满血时' if r['conditionHpRate'] == 100 else '血量 ≥ ' + num(r['conditionHpRate']) + '%')
    conditions = {int(r.get('invocationConditionsStateChange' + str(i), 0)) for i in (1, 2, 3)} - {0}
    if conditions - known_states:
        restrictions.append('需满足指定状态')
    # A short-lived restore node can carry a default interval longer than its life.
    # Do not present that unused repeat interval as the trigger's cooldown.
    duration = r.get('effectEndurance', 0)
    interval = r.get('motionInterval', 0)
    if r.get('stateInfo') == 2116:
        interval = 0
    timing = evidence['recoveryTiming'].get(str(id))
    if timing and (not timing.get('requiresState') or timing['requiresState'] in known_states):
        assert timing['lifetime'] == duration and timing['interval'] == interval
        if timing['resetsAccumulator']:
            restrictions.append('恢复时重置连续攻击累计进度')
        if timing['repeatedApplication'] == 'refresh':
            restrictions.append(f'首次触发恢复一次；{num(duration)} 秒内再次触发只延长有效期，持续刷新时约每 {num(interval)} 秒恢复一次')
        # The resource change is a tick, not a buff lasting this many seconds.
        # Any consequential refresh window is described above instead.
        duration, interval = 0, 0
    if id == 7031901:
        assert any(r['id'] == id and r['refreshAt'] is None for r in evidence['timing'])
        duration = interval = 0
        restrictions.append('1 秒内再次触发只刷新有效期；连续触发时约每 1.1 秒获得一次')
    return dict(source=id, phase=phase, linked=linked, values=values, scope=scope, restrictions=restrictions,
                duration=duration if duration > 0 else None,
                interval=interval if interval > 0 and (duration < 0 or duration >= interval) else None)

STACKING_RULES = {
    'unknown': ('待确认', '', []),
    'attributes': ('可叠加', '能力值相加', ['equip-injection', 'instance-matching', 'attributes']),
    'attack': ('可叠加', '攻击倍率相乘', ['equip-injection', 'instance-matching', 'attack']),
    'defense': ('可叠加', '承伤倍率相乘', ['equip-injection', 'instance-matching', 'defense']),
    'cooldown': ('可叠加', '冷却时间倍率相乘', ['equip-injection', 'instance-matching', 'cooldown']),
    'gauge': ('可叠加', '各自累积通道的倍率相乘', ['equip-injection', 'instance-matching', 'gauge']),
    'resistance': ('可叠加', '抵抗力点数相加', ['equip-injection', 'instance-matching', 'resistance']),
    'fp-cost': ('可叠加', 'FP 消耗倍率相乘', ['equip-injection', 'instance-matching', 'fpCost']),
    'weapon-count': ('不可叠加', '同种武器条件重复无效；不同武器种类分别满足条件时，可同时生效', ['instance-matching', 'weapon-count']),
    'discovery': ('不可叠加', '多个武器倾向同时存在时，采用生效列表中的第一个', ['discovery']),
    'skill-uses': ('不可叠加', '同一技艺次数词条重复装备只生效一次', ['equip-injection', 'instance-matching', 'skillUses']),
    'kill': ('不同等级可叠加', '普通版与＋１版各生效一次，恢复量相加；同等级重复无效',
             ['equip-injection', 'instance-matching', 'killMatching', 'killDispatch', 'gaugeApply']),
    'trigger-single': ('不可叠加', '重复装备只生效一份', ['action-triggers', 'triggerMatching']),
    'trigger-tiers': ('不同等级可叠加', '不同等级各生效一份；同等级重复无效', ['action-triggers', 'triggerMatching']),
    'trigger-attack': ('不同等级可叠加', '不同等级的攻击倍率相乘；同等级重复无效', ['action-triggers', 'triggerMatching', 'triggerValues']),
    'trigger-gauge': ('不同等级可叠加', '不同等级的恢复量相加；同等级重复无效', ['action-triggers', 'triggerMatching', 'triggerValues']),
    'trigger-stamina': ('不同等级可叠加', '不同等级的恢复速度相加；同等级重复无效', ['action-triggers', 'triggerMatching', 'extraGetters']),
    'stamina-speed': ('可叠加', '精力恢复速度相加', ['instance-matching', 'extraGetters']),
    'shop-discount': ('不可叠加', '相同词条重复无效；两种折扣同时生效时价格为原价的 72%', ['extraGetters', 'shopMatching']),
    'growth': ('不可叠加', '同一词条重复装备不额外计数；成长效果按触发次数累计', ['growthAdvance', 'growth-events']),
}
result, rules = {}, {}
for id, effect in source['effects'].items():
    blocks, seen = [], set()
    pending = [(v, ROOTS[k], False, 0) for k, v in effect['roots'].items()]
    external = [triggers['roots'][str(root)] for root in effect['roots'].values() if str(root) in triggers['roots']]
    known_states = {r['state'] for r in external}
    for trigger in external:
        for seed in trigger['seeds']:
            assert source['spells'][str(seed)]['invocationConditionsStateChange1'] == trigger['state']
            pending.append((seed, trigger['phase'], True, 0))
    while pending:
        sp, phase, linked, depth = pending.pop(0)
        if sp in seen:
            continue
        seen.add(sp)
        if b := block(sp, phase, linked, known_states):
            blocks.append(b)
        if depth < 6:
            r = source['spells'].get(str(sp), {})
            pending.extend((int(r[k]), phase if external else label, True, depth + 1)
                           for k, label in LINKS.items() if r.get(k, -1) > 0)
            for leaf in links['emitters'].get(str(sp), {}).get('leaves', []):
                pending.append((leaf, phase, True, depth + 1))
    notes = []
    rule = 'unknown'
    roots = [source['spells'].get(str(v), {}) for v in effect['roots'].values()]
    simple = (len(roots) == 1 and roots[0].get('spCategory') == 10
              and roots[0].get('stateInfo') == 0 and effect.get('runtimeExclusive', -1) == -1
              and not any(roots[0].get(k, -1) > 0 for k in LINKS)
              and not any(roots[0].get('invocationConditionsStateChange' + str(i), 0) for i in (1, 2, 3)))
    if simple:
        r = roots[0]
        if any(r.get(k, 0) for k in POINTS if k.startswith('add') and k.endswith('Status')):
            rule = 'attributes'
        elif any(r.get(k, 0) for k in POINTS if k.endswith('ResistPoint')):
            rule = 'resistance'
        elif any(r.get(k, 1) != 1 for k in ('magicConsumptionRate', 'miracleConsumptionRate', 'shamanConsumptionRate', 'artsConsumptionRate')):
            rule = 'fp-cost'
        elif r.get('characterSkillCooldownReduction', 1) != 1:
            rule = 'cooldown'
        elif r.get('ultimateArtGaugeRate', 1) != 1 or r.get('ultimateArtGaugeChargeRate', 1) != 1:
            rule = 'gauge'
        elif r.get('staminaRecoverChangeSpeed', 0):
            rule = 'stamina-speed'
        elif any(r.get(k, 1) != 1 for k in RATES if k.endswith('AttackRate')):
            rule = 'attack'
        elif any(r.get(k, 1) != 1 for k in RATES if k.endswith('DamageCutRate') and k != 'toughnessDamageCutRate'):
            rule = 'defense'
    if len(roots) == 1 and roots[0].get('stateInfo') == 2100 and roots[0].get('spCategory') == 20:
        rule = 'weapon-count'
    if len(roots) == 1 and roots[0].get('stateInfo') == 2122:
        rule = 'discovery'
        name = catalog['effects'][id]['name']['zh_CN']
        notes.append(name.replace('通过潜在能力，能比较容易找到', '潜在能力武器倾向：'))
    if len(roots) == 1 and list(effect['roots'].values())[0] in (7033200, 7270100):
        rule = 'skill-uses'
    if len(roots) == 1 and list(effect['roots'].values())[0] in (7230000, 7230001):
        rule = 'shop-discount'
    if len(external) == 1 and effect['runtimeExclusive'] == -1:
        family = external[0]['family']
        if family not in ('madness-fp', 'revenant-allies', 'random-weapon', 'undertaker-growth'):
            matches = [r for r in evidence['triggerMatching'] if r['family'] == family]
            assert matches and all(r['reused'] == (r['existing'] == r['incoming']) for r in matches)
            rule = {'bolus': 'trigger-tiers', 'grease': 'trigger-attack',
                    'guard-gauge': 'trigger-gauge', 'critical-gauge': 'trigger-gauge',
                    'critical-stamina': 'trigger-stamina'}.get(family, 'trigger-single')
    if id in ('7050000', '7090100', '7012200', '7031200'):
        emitter, leaf, phase = {
            '7050000': (7050000, 7050001, '周围队友'),
            '7090100': (7090101, 7090102, '打倒敌人时'),
            '7012200': (7012202, 7012201, '血量 < 40% 时触发'),
            '7031200': (7031201, 7031202, '绝招发动时'),
        }[id]
        edge = links['emitters'][str(emitter)]
        b = next(b for b in blocks if b['source'] == leaf)
        b['phase'] = phase
        b['restrictions'].append(('自身及周围友方' if edge['includeSelf'] else '周围友方') + ' · 半径 ' + num(edge['radius']) + ' 米')
        if id == '7050000':
            # A one-second aura lease is renewed by the emitter, not a one-second ability.
            b['duration'] = b['interval'] = None
        if id == '7012200':
            notes.append('触发后的恢复持续 50 秒，不要求一直维持低血量。')
    if id == '7035700':
        branches = scripts['effects'][id]['branches']
        assert sum(b['chance'] for b in branches) == 100
        assert {b['power'] for b in branches} == {20} and {b['duration'] for b in branches} == {10}
        blocks = [dict(source=7035700, branches=[hand['leaf'] for b in branches for hand in b['hands']],
                       phase='切换武器后', linked=True,
                       values=[['属性攻击力', '+20（随机一种）'],
                               ['概率', ' / '.join(b['name'] + ' ' + num(b['chance']) + '%' for b in branches)]],
                       scope=[], restrictions=['作用于切换的那只手'], duration=10, interval=None)]
    grown = [growth['roots'][str(root)] for root in effect['roots'].values() if str(root) in growth['roots']]
    if grown:
        assert len(grown) == 1
        record = grown[0]
        cap = min([len(ladder['stages']) for ladder in record['ladders']] + ([record['eventLimit']] if record['eventLimit'] else []))
        blocks = []
        for stage in (1, cap):
            stage_ids = [ladder['stages'][stage - 1] for ladder in record['ladders']]
            values = [value for sp in stage_ids for value in stats(source['spells'][str(sp)])]
            # Keep equal defense/resistance channels concise in a multi-stat growth card.
            for labels, label in [
                (['物理承伤', '魔力承伤', '火承伤', '雷承伤', '圣承伤'], '承伤倍率'),
                (['抗毒', '抗腐败', '抗出血', '抗骤死', '抗冻伤', '抗催眠', '抗发狂'], '各类异常抵抗力'),
            ]:
                matched = [v for v in values if v[0] in labels]
                if len(matched) == len(labels) and len({v[1] for v in matched}) == 1:
                    values = [v for v in values if v[0] not in labels] + [[label, matched[0][1]]]
            assert values
            blocks.append(dict(source=stage_ids[0], branches=stage_ids[1:], phase=f'累计 {stage} 次', linked=True,
                               values=values, scope=[], restrictions=[], duration=None, interval=None))
        ladder_cap = min(len(ladder['stages']) for ladder in record['ladders'])
        notes.append(f'成长上限 {ladder_cap} 档。' + ('与其他来源的同类成长共用档位。' if len(record['ladders']) > 1 else ''))
        for ladder in record['ladders']:
            final = ladder['stages'][-1]
            assert any(r['existing'] == [final] and r['target'] == -1 for r in evidence['growthAdvance'])
        rule = 'growth'
    if id in ('7090000', '6090000'):
        root = list(effect['roots'].values())[0]
        assert roots[0]['spCategory'] == 20 and roots[0]['stateInfo'] == 199 and effect['runtimeExclusive'] == -1
        branches = [int(roots[0][k]) for k in ('applyIdOnKillSp', 'applyIdOnGetSoul')]
        values = sorted(source['spells'][str(sp)]['ultimateArtGauge'] for sp in branches)
        blocks = [dict(source=root, branches=branches, phase='打倒敌人时', linked=False,
                       values=[['绝招量表', ' 或 '.join(signed(v) + '%' for v in values)]],
                       scope=[], restrictions=['恢复量随敌人类型变化'], duration=None, interval=None)]
        rule = 'kill'
    if id in ('7034200', '7034201'):

        notes.append('混合魔法的其他强化效果尚未解明。')
    if id == '6840200':
        assert roots[0]['ultimateArtGaugeChargeRate'] == 0.85
        notes.append('影响所有来源的绝招量表累积。')
    if id in {str(i) for i in range(6820000, 6820700, 100)}:
        measured = next(r for r in evidence['damageStatus'] if r['root'] == int(id) and 'amount' in r)
        root, bridge, child = (measured[k] for k in ('root', 'bridge', 'child'))
        assert effect['roots'] == {'passiveSpEffectId_1': root}
        assert source['spells'][str(root)]['deleteCriteriaDamage'] == 12
        assert source['spells'][str(root)]['replaceSpEffectId'] == bridge
        assert source['spells'][str(bridge)]['replaceSpEffectId'] == root
        assert source['spells'][str(bridge)]['cycleOccurrenceSpEffectId'] == child
        assert source['spells'][str(child)][measured['field']] == measured['amount']
        blocks = [dict(source=root, branches=[bridge, child], phase='受到损伤时', linked=False,
                       values=[[STATUS_BUILDUP[measured['field']] + '累积', '+' + num(measured['amount']) + ' 点／次']],
                       scope=[], restrictions=[], duration=None, interval=None)]
        notes.append('积累量不随损伤数值变化。')
    stacking, stacking_detail, _ = STACKING_RULES[rule]
    rules[id] = rule
    result[id] = dict(info=effect.get('info'), blocks=blocks, stacking=stacking, stackingDetail=stacking_detail, notes=notes)
output = dict(schema=2, regulationSha256=source['hashes']['regulation.bin'], effects=result)
out = ROOT / 'web/src/data/effect-details.json'
out.write_text(json.dumps(output, ensure_ascii=False, separators=(',', ':')) + '\n')
obtainable = {str(e) for r in catalog['relics'].values() if r['obtainable'] for p in r['pools'] for e in catalog['pools'].get(str(p), [])}
ledger = {}
for id in sorted(source['effects'], key=int):
    effect, detail = source['effects'][id], result[id]
    missing_roots = [sp for sp in effect['roots'].values() if str(sp) not in source['spells']]
    states = sorted({int(source['spells'][str(sp)]['stateInfo']) for sp in effect['roots'].values() if str(sp) in source['spells']})
    refs = STACKING_RULES[rules[id]][2].copy()
    if any(r['root'] == int(id) for r in evidence['damageStatus']):
        refs.append('damage-status')
    if any(str(root) in triggers['roots'] for root in effect['roots'].values()):
        refs.append('action-triggers')
    if any(str(root) in scripts['effects'] for root in effect['roots'].values()):
        refs.append('action-script')
        questions.append('与其他附魔的覆盖顺序、武器适用条件及完整动作时序')
    if any(b['source'] in edge['leaves'] for b in detail['blocks'] for edge in links['emitters'].values()):
        refs.append('bullet-links')
        questions.append('范围命中、多人来源叠加及再次发放时序')
    questions = []
    if missing_roots:
        questions.append('目录引用的 SpEffect 行在当前参数中不存在：' + ', '.join(map(str, missing_roots)))
    if rules[id] == 'unknown':
        questions.append('跨遗物同版／异版的覆盖、叠加与上限')
    if 2123 in states:
        refs.append('hero')
    if any(str(b['source']) in evidence['recoveryTiming'] for b in detail['blocks']):
        refs.append('recovery-timing')
    if 2102 in states:
        questions.append('出击物品发放次数、容量溢出和状态 2226 的额外发放条件')
    if 2105 in states or 2128 in states:
        questions.append('多个出击替换词条的优先顺序、角色限制')
    if rules[id] == 'kill':
        questions.append('敌人分类标记的具体对象、共享奖励及重载路径')
    elif any(s not in (0, 71, 2100, 2102, 2105, 2122, 2123, 2128) for s in states):
        questions.append('stateInfo 分派、触发资格、次数、目标及隐藏效果链')
    if any(b['linked'] for b in detail['blocks']):
        questions.append('关联分支的实际触发顺序、重复通知与刷新行为')
    if rules[id] == 'growth':
        questions.append('计数源的完整地点名单、跨日／重载恢复与同类来源相遇')
    if any(source['spells'].get(str(sp), {}).get(k, -1) > 0 for sp in effect['roots'].values() for k in ('conditionHp', 'conditionHpRate')):
        refs.append('hpConditions')
        questions.append('低血量状态切换与其他触发链的时序交互')
    if not detail['blocks']:
        questions.append('尚未解析到可展示数值／机制，继续查原生、事件或动作脚本')
    numeric = any(any(label != '出击时替换' for label, _ in b['values']) for b in detail['blocks'])
    ledger[id] = dict(name=catalog['effects'][id]['name']['zh_CN'], obtainable=id in obtainable, roots=effect['roots'], states=states,
                      detailSources=[sp for b in detail['blocks'] for sp in [b['source'], *b.get('branches', [])]],
                      values='decoded-fields' if numeric else ('named-replacement' if detail['blocks'] else 'unresolved'),
                      stacking='native-analysis' if rules[id] != 'unknown' else 'unresolved',
                      stackingCategory=detail['stacking'],
                      evidence=refs, openQuestions=questions, gameplayVerified=False)
coverage = dict(obtainable=len(obtainable), withDetails=sum(bool(result[e]['blocks']) for e in obtainable),
                withNumericFields=sum(ledger[e]['values'] == 'decoded-fields' for e in obtainable),
                nativeStacking=sum(ledger[e]['stacking'] == 'native-analysis' for e in obtainable),
                catalog=len(ledger), catalogWithDetails=sum(bool(d['blocks']) for d in result.values()))
research = dict(schema=1, regulationSha256=source['hashes']['regulation.bin'],
                nativeEvidenceSha256=hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
                triggerEvidenceSha256=hashlib.sha256(trigger_path.read_bytes()).hexdigest(), coverage=coverage, effects=ledger)
research['linkEvidenceSha256'] = hashlib.sha256(link_path.read_bytes()).hexdigest()
research['scriptEvidenceSha256'] = hashlib.sha256(script_path.read_bytes()).hexdigest()
research['growthEvidenceSha256'] = hashlib.sha256(growth_path.read_bytes()).hexdigest()
(ROOT / 'data/effect-research.json').write_text(json.dumps(research, ensure_ascii=False, indent=2) + '\n')
print(f'{len(result)} details; coverage={coverage}; {out.stat().st_size} browser bytes')
