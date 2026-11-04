"""Build compact, provenance-checked effect details. Never infer stacking from filter flags.

--extract accepts the private output of ExtractEffectDetails and writes a minimal
source snapshot. Without it, rebuild using the committed snapshot only.
"""
import argparse
import json
import hashlib
import math
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
evidence_path = ROOT / 'data/effect-native-evidence.json'
evidence = json.loads(evidence_path.read_text())
discovery_path = ROOT / 'data/effect-discovery-evidence.json'
discovery = json.loads(discovery_path.read_text())
assert discovery['schema'] == 1 and discovery['regulationSha256'] == catalog['regulationSha256']
assert discovery['exeSha256'] == evidence['exeSha256'] and not discovery['gameplayVerified']
assert discovery['rowCount'] == 35755 and discovery['groupCount'] == 3627
assert len(discovery['biasedGroups']) == 39 and len(discovery['draws']) == 1626
totem_path = ROOT / 'data/effect-totem-evidence.json'
totem = json.loads(totem_path.read_text())
assert totem['schema'] == 1 and totem['regulationSha256'] == catalog['regulationSha256']
assert totem['exeSha256'] == evidence['exeSha256'] and not totem['gameplayVerified']
assert sum(map(len, totem['checks'].values())) == 86
lifecycle_path = ROOT / 'data/effect-lifecycle-evidence.json'
lifecycle = json.loads(lifecycle_path.read_text())
assert lifecycle['schema'] == 1 and lifecycle['regulationSha256'] == catalog['regulationSha256']
assert lifecycle['exeSha256'] == evidence['exeSha256'] and not lifecycle['gameplayVerified']
assert lifecycle['paramSha256'] == evidence['paramSha256']
assert len(lifecycle['checks']['revenant']) == 8 and len(lifecycle['checks']['fp']) == 18
assert len(lifecycle['checks']['duchess']) == 12 and len(lifecycle['checks']['attack']) == 18
recovery_path = ROOT / 'data/effect-recovery-evidence.json'
recovery = json.loads(recovery_path.read_text())
assert recovery['schema'] == 1 and recovery['regulationSha256'] == catalog['regulationSha256']
assert recovery['exeSha256'] == evidence['exeSha256'] and not recovery['gameplayVerified']
assert recovery['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in recovery['checks'].items()} == dict(trigger=12, emissionAndRecovery=6, arrival=4)
executor_path = ROOT / 'data/effect-executor-recovery-evidence.json'
executor = json.loads(executor_path.read_text())
assert executor['schema'] == 1 and executor['regulationSha256'] == catalog['regulationSha256']
assert executor['exeSha256'] == evidence['exeSha256'] and not executor['gameplayVerified']
assert executor['paramSha256'] == evidence['paramSha256'] and len(executor['checks']) == 24
weapon_recovery_path = ROOT / 'data/effect-weapon-recovery-evidence.json'
weapon_recovery = json.loads(weapon_recovery_path.read_text())
assert weapon_recovery['schema'] == 1 and weapon_recovery['regulationSha256'] == catalog['regulationSha256']
assert weapon_recovery['exeSha256'] == evidence['exeSha256'] and not weapon_recovery['gameplayVerified']
assert weapon_recovery['paramSha256'] == evidence['paramSha256']
assert len(weapon_recovery['families']) == 56 and len(weapon_recovery['checks']['reapplication']) == 62
weapon_recovery_families = {str(f['effect']): f for f in weapon_recovery['families']}
recluse_bleed_path = ROOT / 'data/effect-recluse-bleed-evidence.json'
recluse_bleed = json.loads(recluse_bleed_path.read_text())
assert recluse_bleed['schema'] == 1 and recluse_bleed['regulationSha256'] == catalog['regulationSha256']
assert recluse_bleed['exeSha256'] == evidence['exeSha256'] and not recluse_bleed['gameplayVerified']
assert recluse_bleed['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in recluse_bleed['checks'].items()} == dict(onset=8, hp=7, lifecycle=7)
sacrifice_path = ROOT / 'data/effect-revenant-sacrifice-evidence.json'
sacrifice = json.loads(sacrifice_path.read_text())
assert sacrifice['schema'] == 1 and sacrifice['regulationSha256'] == catalog['regulationSha256']
assert sacrifice['exeSha256'] == evidence['exeSha256'] and not sacrifice['gameplayVerified']
assert sacrifice['paramSha256'] == evidence['paramSha256']
assert sacrifice['scriptSha256'] == scripts['scriptSha256']
assert {k: len(v) for k, v in sacrifice['checks'].items()} == dict(trigger=6, emission=6, hp=12, lifecycle=15, script=4)
gesture_path = ROOT / 'data/effect-gesture-madness-evidence.json'
gesture = json.loads(gesture_path.read_text())
assert gesture['schema'] == 1 and gesture['regulationSha256'] == catalog['regulationSha256']
assert gesture['exeSha256'] == evidence['exeSha256'] and not gesture['gameplayVerified']
assert gesture['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in gesture['checks'].items()} == dict(cadence=21, onset=16, resources=4)
guardian_skill_path = ROOT / 'data/effect-guardian-skill-evidence.json'
guardian_skill = json.loads(guardian_skill_path.read_text())
assert guardian_skill['schema'] == 1 and guardian_skill['regulationSha256'] == catalog['regulationSha256']
assert guardian_skill['exeSha256'] == evidence['exeSha256'] and not guardian_skill['gameplayVerified']
assert guardian_skill['paramSha256'] == evidence['paramSha256']
assert guardian_skill['animationSha256'] == recovery['animationSha256']
assert {k: len(v) for k, v in guardian_skill['checks'].items()} == dict(trigger=12, emissionAndRecovery=6, hp=4, arrival=6)
blade_path = ROOT / 'data/effect-executor-blade-evidence.json'
blade = json.loads(blade_path.read_text())
assert blade['schema'] == 1 and blade['regulationSha256'] == catalog['regulationSha256']
assert blade['exeSha256'] == evidence['exeSha256'] and not blade['gameplayVerified']
assert blade['paramSha256'] == evidence['paramSha256']
assert blade['animationSha256'] == recovery['animationSha256']
assert {k: len(v) for k, v in blade['checks'].items()} == dict(filter=128, lifecycle=8, penalty=6, attackRows=34)
prayer_path = ROOT / 'data/effect-undertaker-prayer-evidence.json'
prayer = json.loads(prayer_path.read_text())
assert prayer['schema'] == 1 and prayer['regulationSha256'] == catalog['regulationSha256']
assert prayer['exeSha256'] == evidence['exeSha256'] and not prayer['gameplayVerified']
assert prayer['paramSha256'] == evidence['paramSha256']
assert prayer['animationSha256'] == recovery['animationSha256']
assert {k: len(v) for k, v in prayer['checks'].items()} == dict(slots=33, dispatch=420, lifecycle=6, attack=6)
protection_path = ROOT / 'data/effect-guardian-protection-evidence.json'
protection = json.loads(protection_path.read_text())
assert protection['schema'] == 1 and protection['regulationSha256'] == catalog['regulationSha256']
assert protection['exeSha256'] == evidence['exeSha256'] and not protection['gameplayVerified']
assert protection['paramSha256'] == evidence['paramSha256']
assert protection['animationSha256'] == recovery['animationSha256']
assert {k: len(v) for k, v in protection['checks'].items()} == dict(trigger=12, emission=3, lifecycle=6)
tenacity_path = ROOT / 'data/effect-executor-tenacity-evidence.json'
tenacity = json.loads(tenacity_path.read_text())
assert tenacity['schema'] == 1 and tenacity['regulationSha256'] == catalog['regulationSha256']
assert tenacity['exeSha256'] == evidence['exeSha256'] and not tenacity['gameplayVerified']
assert tenacity['paramSha256'] == evidence['paramSha256']
assert tenacity['playerCommonSha256'] == evidence['systemParamSha256']['PlayerCommonParam']
assert {k: len(v) for k, v in tenacity['checks'].items()} == dict(trigger=99, lifecycle=13, hp=5, resistance=3)
evasion_path = ROOT / 'data/effect-duchess-evasion-evidence.json'
evasion = json.loads(evasion_path.read_text())
assert evasion['schema'] == 1 and evasion['regulationSha256'] == catalog['regulationSha256']
assert evasion['exeSha256'] == evidence['exeSha256'] and not evasion['gameplayVerified']
assert evasion['paramSha256'] == evidence['paramSha256']
assert evasion['scriptSha256'] == scripts['scriptSha256']
assert evasion['animationSha256'] == recovery['animationSha256']
assert {k: len(v) for k, v in evasion['checks'].items()} == dict(script=33, dispatch=25, lifecycle=12)
duration_path = ROOT / 'data/effect-guardian-duration-evidence.json'
duration = json.loads(duration_path.read_text())
assert duration['schema'] == 1 and duration['regulationSha256'] == catalog['regulationSha256']
assert duration['exeSha256'] == evidence['exeSha256'] and not duration['gameplayVerified']
assert duration['paramSha256'] == evidence['paramSha256']
assert duration['scriptSha256'] == scripts['scriptSha256']
assert duration['animationSha256'] == recovery['animationSha256']
assert duration['behavior']['bundleSha256'] == '0eab914717c59464b19a0cbff4c67841a92b01aef495812ed2bfa8feba7f5fd5'
assert {k: len(v) for k, v in duration['checks'].items()} == dict(script=32, dispatch=96, lifetime=12, hitHistory=6)
starting_weapon_path = ROOT / 'data/effect-starting-weapon-evidence.json'
starting_weapon = json.loads(starting_weapon_path.read_text())
assert starting_weapon['schema'] == 1 and starting_weapon['regulationSha256'] == catalog['regulationSha256']
assert starting_weapon['exeSha256'] == evidence['exeSha256'] and not starting_weapon['gameplayVerified']
assert starting_weapon['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in starting_weapon['checks'].items()} == dict(component=70, assignment=12, attack=672, status=300, binding=28)
starting_goods_path = ROOT / 'data/effect-starting-goods-evidence.json'
starting_goods = json.loads(starting_goods_path.read_text())
assert starting_goods['schema'] == 1 and starting_goods['regulationSha256'] == catalog['regulationSha256']
assert starting_goods['exeSha256'] == evidence['exeSha256'] and not starting_goods['gameplayVerified']
assert starting_goods['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in starting_goods['checks'].items()} == dict(
    selection=930, repeat=288, capacity=252, reinitialize=49, allocationFailure=1)

recluse_mark_path = ROOT / 'data/effect-recluse-mark-evidence.json'
recluse_mark = json.loads(recluse_mark_path.read_text())
assert recluse_mark['schema'] == 1 and recluse_mark['regulationSha256'] == catalog['regulationSha256']
assert recluse_mark['exeSha256'] == evidence['exeSha256'] and not recluse_mark['gameplayVerified']
assert recluse_mark['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in recluse_mark['checks'].items()} == dict(dispatch=24, lifetime=12, recovery=588, overlap=2)

ironeye_mark_path = ROOT / 'data/effect-ironeye-mark-evidence.json'
ironeye_mark = json.loads(ironeye_mark_path.read_text())
assert ironeye_mark['schema'] == 1 and ironeye_mark['regulationSha256'] == catalog['regulationSha256']
assert ironeye_mark['exeSha256'] == evidence['exeSha256'] and not ironeye_mark['gameplayVerified']
assert ironeye_mark['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in ironeye_mark['checks'].items()} == dict(selection=48, lifetime=9, refresh=16, breakage=8, rows=353)
assert (ironeye_mark['baseDuration'], ironeye_mark['extendedDuration']) == (17, 22)

restage_path = ROOT / 'data/effect-duchess-restage-evidence.json'
restage = json.loads(restage_path.read_text())
assert restage['schema'] == 1 and restage['regulationSha256'] == catalog['regulationSha256']
assert restage['exeSha256'] == evidence['exeSha256'] and not restage['gameplayVerified']
assert restage['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in restage['checks'].items()} == dict(script=104, dispatch=8, selection=12, damage=480, repeat=4)
assert restage['baseRate'] == .5 and abs(restage['relicRate'] - .6) < 1e-6

absorption_path = ROOT / 'data/effect-recluse-absorption-evidence.json'
absorption = json.loads(absorption_path.read_text())
assert absorption['schema'] == 1 and absorption['regulationSha256'] == catalog['regulationSha256']
assert absorption['exeSha256'] == evidence['exeSha256'] and not absorption['gameplayVerified']
assert absorption['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in absorption['checks'].items()} == dict(dispatch=240, reset=28, protection=16, refresh=30, lifetime=12)

raider_debuff_path = ROOT / 'data/effect-raider-debuff-evidence.json'
raider_debuff = json.loads(raider_debuff_path.read_text())
assert raider_debuff['schema'] == 1 and raider_debuff['regulationSha256'] == catalog['regulationSha256']
assert raider_debuff['exeSha256'] == evidence['exeSha256'] and not raider_debuff['gameplayVerified']
assert raider_debuff['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in raider_debuff['checks'].items()} == dict(dispatch=16, arrival=55, refresh=12, lifetime=3)

ironeye_poison_path = ROOT / 'data/effect-ironeye-poison-evidence.json'
ironeye_poison = json.loads(ironeye_poison_path.read_text())
assert ironeye_poison['schema'] == 1 and ironeye_poison['regulationSha256'] == catalog['regulationSha256']
assert ironeye_poison['exeSha256'] == evidence['exeSha256'] and not ironeye_poison['gameplayVerified']
assert ironeye_poison['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in ironeye_poison['checks'].items()} == dict(dispatch=32, onset=48, damage=7, bonus=15, repeat=5, bonusTiming=11, lifetime=3)

wylder_bleed_path = ROOT / 'data/effect-wylder-bleed-evidence.json'
wylder_bleed = json.loads(wylder_bleed_path.read_text())
assert wylder_bleed['schema'] == 1 and wylder_bleed['regulationSha256'] == catalog['regulationSha256']
assert wylder_bleed['exeSha256'] == evidence['exeSha256'] and not wylder_bleed['gameplayVerified']
assert wylder_bleed['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in wylder_bleed['checks'].items()} == dict(dispatch=32, onset=48, damage=7, repeat=3, lifetime=3)

undertaker_reset_path = ROOT / 'data/effect-undertaker-reset-evidence.json'
undertaker_reset = json.loads(undertaker_reset_path.read_text())
assert undertaker_reset['schema'] == 1 and undertaker_reset['regulationSha256'] == catalog['regulationSha256']
assert undertaker_reset['exeSha256'] == evidence['exeSha256'] and not undertaker_reset['gameplayVerified']
assert undertaker_reset['paramSha256'] == evidence['paramSha256'] and undertaker_reset['nativeEventBank'] == 255
assert {k: len(v) for k, v in undertaker_reset['checks'].items()} == dict(dispatch=32, capacity=54, repeat=6)
treasure_map_path = ROOT / 'data/effect-treasure-map-evidence.json'
treasure_map = json.loads(treasure_map_path.read_text())
assert treasure_map['schema'] == 1 and treasure_map['regulationSha256'] == catalog['regulationSha256']
assert treasure_map['exeSha256'] == evidence['exeSha256'] and not treasure_map['gameplayVerified']
assert treasure_map['paramSha256'] == evidence['paramSha256'] and not treasure_map['eventVmExecuted']
assert {k: len(v) for k, v in treasure_map['checks'].items()} == dict(visibility=192, override=8, copies=4, unbound=12)
passive_resource_path = ROOT / 'data/effect-passive-resource-evidence.json'
passive_resource = json.loads(passive_resource_path.read_text())
assert passive_resource['schema'] == 1 and passive_resource['regulationSha256'] == catalog['regulationSha256']
assert passive_resource['exeSha256'] == evidence['exeSha256'] and not passive_resource['gameplayVerified']
assert passive_resource['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in passive_resource['checks'].items()} == dict(resources=48, poise=74, flask=96, flaskCap=12, ordinaryRecovery=16)
damage_ailment_path = ROOT / 'data/effect-damage-ailment-evidence.json'
damage_ailment = json.loads(damage_ailment_path.read_text())
assert damage_ailment['schema'] == 1 and damage_ailment['regulationSha256'] == catalog['regulationSha256']
assert damage_ailment['exeSha256'] == evidence['exeSha256'] and not damage_ailment['gameplayVerified']
assert damage_ailment['paramSha256'] == evidence['paramSha256'] and damage_ailment['capacityFixture'] == 10000
assert {k: len(v) for k, v in damage_ailment['checks'].items()} == dict(trigger=224, window=63, continuous=21, mixed=1)
spell_family_path = ROOT / 'data/effect-spell-family-evidence.json'
spell_family = json.loads(spell_family_path.read_text())
assert spell_family['schema'] == 1 and spell_family['regulationSha256'] == catalog['regulationSha256']
assert spell_family['exeSha256'] == evidence['exeSha256'] and not spell_family['gameplayVerified']
assert spell_family['paramSha256'] == evidence['paramSha256'] and len(spell_family['families']) == 14
assert {k: len(v) for k, v in spell_family['checks'].items()} == dict(selection=1386, repeat=112, kinds=182, mixed=99)
periodic_hp_path = ROOT / 'data/effect-periodic-hp-evidence.json'
periodic_hp = json.loads(periodic_hp_path.read_text())
assert periodic_hp['schema'] == 1 and periodic_hp['regulationSha256'] == catalog['regulationSha256']
assert periodic_hp['exeSha256'] == evidence['exeSha256'] and not periodic_hp['gameplayVerified']
assert periodic_hp['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in periodic_hp['checks'].items()} == dict(snapshot=64, timing=18, mixed=48, staggered=12, arrivalBaseline=6)
perfume_path = ROOT / 'data/effect-perfume-evidence.json'
perfume = json.loads(perfume_path.read_text())
assert perfume['schema'] == 1 and perfume['regulationSha256'] == catalog['regulationSha256']
assert perfume['exeSha256'] == evidence['exeSha256'] and not perfume['gameplayVerified']
assert perfume['paramSha256'] == evidence['paramSha256'] and len(perfume['families']) == 2
assert {k: len(v) for k, v in perfume['checks'].items()} == dict(filters=3616, kinds=156, disabled=48, lifecycle=48)
duchess_ultimate_path = ROOT / 'data/effect-duchess-ultimate-evidence.json'
duchess_ultimate = json.loads(duchess_ultimate_path.read_text())
assert duchess_ultimate['schema'] == 1 and duchess_ultimate['regulationSha256'] == catalog['regulationSha256']
assert duchess_ultimate['exeSha256'] == evidence['exeSha256'] and not duchess_ultimate['gameplayVerified']
assert duchess_ultimate['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in duchess_ultimate['checks'].items()} == dict(selection=12, dispatch=24, threshold=11, multipliers=32, kinds=52, markers=20, lifecycle=6, duration=12)
guardian_shock_path = ROOT / 'data/effect-guardian-shockwave-evidence.json'
guardian_shock = json.loads(guardian_shock_path.read_text())
assert guardian_shock['schema'] == 1 and guardian_shock['regulationSha256'] == catalog['regulationSha256']
assert guardian_shock['exeSha256'] == evidence['exeSha256'] and not guardian_shock['gameplayVerified']
assert guardian_shock['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in guardian_shock['checks'].items()} == dict(trigger=54, repeat=6, projectile=3, target=4, damage=16)
hero_adjustment_path = ROOT / 'data/effect-hero-adjustment-evidence.json'
hero_adjustment = json.loads(hero_adjustment_path.read_text())
assert hero_adjustment['schema'] == 1 and hero_adjustment['regulationSha256'] == catalog['regulationSha256']
assert hero_adjustment['exeSha256'] == evidence['exeSha256'] and not hero_adjustment['gameplayVerified']
assert hero_adjustment['paramSha256'] == evidence['paramSha256']
assert hero_adjustment['heroStatusParamSha256'] == evidence['heroParamSha256']
assert len(hero_adjustment['families']) == 10
assert {k: len(v) for k, v in hero_adjustment['checks'].items()} == dict(single=240, combined=160, roleChange=20, disabled=20, floor=20)
successive_recovery_path = ROOT / 'data/effect-successive-recovery-evidence.json'
successive_recovery = json.loads(successive_recovery_path.read_text())
assert successive_recovery['schema'] == 1 and successive_recovery['regulationSha256'] == catalog['regulationSha256']
assert successive_recovery['exeSha256'] == evidence['exeSha256'] and not successive_recovery['gameplayVerified']
assert successive_recovery['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in successive_recovery['checks'].items()} == dict(threshold=56, mixed=32, markers=40, decay=21, repeat=36, dedupe=6)
successive_attack_path = ROOT / 'data/effect-successive-attack-evidence.json'
successive_attack = json.loads(successive_attack_path.read_text())
assert successive_attack['schema'] == 1 and successive_attack['regulationSha256'] == catalog['regulationSha256']
assert successive_attack['exeSha256'] == evidence['exeSha256'] and not successive_attack['gameplayVerified']
assert successive_attack['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in successive_attack['checks'].items()} == dict(selection=12, threshold=11, multipliers=32, kinds=52, markers=20, lifecycle=6, mixed=2)
scholar_tether_path = ROOT / 'data/effect-scholar-tether-evidence.json'
scholar_tether = json.loads(scholar_tether_path.read_text())
assert scholar_tether['schema'] == 1 and scholar_tether['regulationSha256'] == catalog['regulationSha256']
assert scholar_tether['exeSha256'] == evidence['exeSha256'] and not scholar_tether['gameplayVerified']
assert scholar_tether['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in scholar_tether['checks'].items()} == dict(dispatch=8, projectile=3, damage=36, unlink=12, late=6, repeat=6)
scholar_ailment_path = ROOT / 'data/effect-scholar-ailment-evidence.json'
scholar_ailment = json.loads(scholar_ailment_path.read_text())
assert scholar_ailment['schema'] == 1 and scholar_ailment['regulationSha256'] == catalog['regulationSha256']
assert scholar_ailment['exeSha256'] == evidence['exeSha256'] and not scholar_ailment['gameplayVerified']
assert scholar_ailment['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in scholar_ailment['checks'].items()} == dict(dispatch=12, projectile=3, targets=10, damage=54, buildup=18, unlink=12, refresh=12, late=3)
wylder_flame_path = ROOT / 'data/effect-wylder-flame-evidence.json'
wylder_flame = json.loads(wylder_flame_path.read_text())
assert wylder_flame['schema'] == 1 and wylder_flame['regulationSha256'] == catalog['regulationSha256']
assert wylder_flame['exeSha256'] == evidence['exeSha256'] and not wylder_flame['gameplayVerified']
assert wylder_flame['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in wylder_flame['checks'].items()} == dict(dispatch=30, emitter=9, chain=3, lifetime=3)
revenant_enchant_path = ROOT / 'data/effect-revenant-enchant-evidence.json'
revenant_enchant = json.loads(revenant_enchant_path.read_text())
assert revenant_enchant['schema'] == 1 and revenant_enchant['regulationSha256'] == catalog['regulationSha256']
assert revenant_enchant['exeSha256'] == evidence['exeSha256'] and not revenant_enchant['gameplayVerified']
assert revenant_enchant['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in revenant_enchant['checks'].items()} == dict(dispatch=18, emission=6, values=39, timer=12, overwrite=5, correction=4, onset=12, damage=4, frostLifetime=3)
revenant_family_path = ROOT / 'data/effect-revenant-family-evidence.json'
revenant_family = json.loads(revenant_family_path.read_text())
assert revenant_family['schema'] == 1 and revenant_family['regulationSha256'] == catalog['regulationSha256']
assert revenant_family['exeSha256'] == evidence['exeSha256'] and not revenant_family['gameplayVerified']
assert revenant_family['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in revenant_family['checks'].items()} == dict(dispatch=18, controller=26, emission=6, repeat=15, mapping=6)
guardian_halberd_path = ROOT / 'data/effect-guardian-halberd-evidence.json'
guardian_halberd = json.loads(guardian_halberd_path.read_text())
assert guardian_halberd['schema'] == 1 and guardian_halberd['regulationSha256'] == catalog['regulationSha256']
assert guardian_halberd['exeSha256'] == evidence['exeSha256'] and not guardian_halberd['gameplayVerified']
assert guardian_halberd['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in guardian_halberd['checks'].items()} == dict(dispatch=48, emitter=12, chain=4, lifetime=6, radius=20, attackSetup=4)
wylder_followup_path = ROOT / 'data/effect-wylder-followup-evidence.json'
wylder_followup = json.loads(wylder_followup_path.read_text())
assert wylder_followup['schema'] == 1 and wylder_followup['regulationSha256'] == catalog['regulationSha256']
assert wylder_followup['exeSha256'] == evidence['exeSha256'] and not wylder_followup['gameplayVerified']
assert wylder_followup['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in wylder_followup['checks'].items()} == dict(script=120, styleScript=6, attackDispatch=6, enchantDispatch=12, values=52, timer=12, overwrite=8, switchHand=2)
duchess_dagger_path = ROOT / 'data/effect-duchess-dagger-evidence.json'
duchess_dagger = json.loads(duchess_dagger_path.read_text())
assert duchess_dagger['schema'] == 1 and duchess_dagger['regulationSha256'] == catalog['regulationSha256']
assert duchess_dagger['exeSha256'] == evidence['exeSha256'] and not duchess_dagger['gameplayVerified']
assert duchess_dagger['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in duchess_dagger['checks'].items()} == dict(trigger=45, emptyPayload=3, repeat=12, damage=156, overwrite=5, radius=5, attackSetup=1)
item_sharing_path = ROOT / 'data/effect-item-sharing-evidence.json'
item_sharing = json.loads(item_sharing_path.read_text())
assert item_sharing['schema'] == 1 and item_sharing['regulationSha256'] == catalog['regulationSha256']
assert item_sharing['exeSha256'] == evidence['exeSha256'] and not item_sharing['gameplayVerified']
assert item_sharing['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in item_sharing['checks'].items()} == dict(selection=252, trigger=144, radius=126, attackSetup=42, arrival=84, cure=21, fp=6, observation=6, refresh=16)
guard_aggro_path = ROOT / 'data/effect-guard-aggro-evidence.json'
guard_aggro = json.loads(guard_aggro_path.read_text())
assert guard_aggro['schema'] == 1 and guard_aggro['regulationSha256'] == catalog['regulationSha256']
assert guard_aggro['exeSha256'] == evidence['exeSha256'] and not guard_aggro['gameplayVerified']
assert guard_aggro['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in guard_aggro['checks'].items()} == dict(script=64, graph=6, dispatch=117, qualification=12, timer=12, score=24)
guard_aggro_families = {str(id): f for f in guard_aggro['families'] for id in f['effects']}
starting_replacements_path = ROOT / 'data/effect-starting-replacements-evidence.json'
starting_replacements = json.loads(starting_replacements_path.read_text())
assert starting_replacements['schema'] == 1 and starting_replacements['regulationSha256'] == catalog['regulationSha256']
assert starting_replacements['exeSha256'] == evidence['exeSha256'] and not starting_replacements['gameplayVerified']
assert starting_replacements['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in starting_replacements['checks'].items()} == dict(compatibility=1780, baseline=32, matrix=1085, repeat=105, order=222, scope=10)
starting_replacement_families = {str(f['effect']): f for f in starting_replacements['families']}
equipped_exclusivity_path = ROOT / 'data/effect-equipped-exclusivity-evidence.json'
equipped_exclusivity = json.loads(equipped_exclusivity_path.read_text())
assert equipped_exclusivity['schema'] == 1 and equipped_exclusivity['regulationSha256'] == catalog['regulationSha256']
assert equipped_exclusivity['exeSha256'] == evidence['exeSha256'] and not equipped_exclusivity['gameplayVerified']
assert equipped_exclusivity['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in equipped_exclusivity['checks'].items()} == dict(selection=300, hero=20, mixed=7, groups=25, attributes=36, attack=1248)
equipped_exclusive_families = {str(f['effect']): f for f in equipped_exclusivity['families']}



ironeye_ultimate_path = ROOT / 'data/effect-ironeye-ultimate-evidence.json'
ironeye_ultimate = json.loads(ironeye_ultimate_path.read_text())
assert ironeye_ultimate['schema'] == 1 and ironeye_ultimate['regulationSha256'] == catalog['regulationSha256']
assert ironeye_ultimate['exeSha256'] == evidence['exeSha256'] and not ironeye_ultimate['gameplayVerified']
assert ironeye_ultimate['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in ironeye_ultimate['checks'].items()} == dict(script=32, selection=12, dispatch=12, onset=30, damage=7, repeat=5, lifetime=3)
revenant_ghostflame_path = ROOT / 'data/effect-revenant-ghostflame-evidence.json'
revenant_ghostflame = json.loads(revenant_ghostflame_path.read_text())
assert revenant_ghostflame['schema'] == 1 and revenant_ghostflame['regulationSha256'] == catalog['regulationSha256']
assert revenant_ghostflame['exeSha256'] == evidence['exeSha256'] and not revenant_ghostflame['gameplayVerified']
assert revenant_ghostflame['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in revenant_ghostflame['checks'].items()} == dict(dispatch=8, projectile=3, correction=96, onset=12, damage=21, repeat=4, lifetime=3)
scholar_feint_path = ROOT / 'data/effect-scholar-feint-evidence.json'
scholar_feint = json.loads(scholar_feint_path.read_text())
assert scholar_feint['schema'] == 1 and scholar_feint['regulationSha256'] == catalog['regulationSha256']
assert scholar_feint['exeSha256'] == evidence['exeSha256'] and not scholar_feint['gameplayVerified']
assert scholar_feint['paramSha256'] == evidence['paramSha256'] and scholar_feint['scriptSha256'] == scripts['scriptSha256']
assert {k: len(v) for k, v in scholar_feint['checks'].items()} == dict(rawEvents=27, dispatch=972, script=64)
flask_sharing_path = ROOT / 'data/effect-flask-sharing-evidence.json'
flask_sharing = json.loads(flask_sharing_path.read_text())
assert flask_sharing['schema'] == 1 and flask_sharing['regulationSha256'] == catalog['regulationSha256']
assert flask_sharing['exeSha256'] == evidence['exeSha256'] and not flask_sharing['gameplayVerified']
assert flask_sharing['paramSha256'] == evidence['paramSha256'] and flask_sharing['scriptSha256'] == scripts['scriptSha256']
assert {k: len(v) for k, v in flask_sharing['checks'].items()} == dict(branches=32, projectile=8, amounts=64, targets=44, sourceModifiers=9, timeline=24)
rally_path = ROOT / 'data/effect-rally-recovery-evidence.json'
rally = json.loads(rally_path.read_text())
assert rally['schema'] == 1 and rally['regulationSha256'] == catalog['regulationSha256']
assert rally['exeSha256'] == evidence['exeSha256'] and not rally['gameplayVerified']
assert rally['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in rally['checks'].items()} == dict(builders=135, recovery=88, pool=18, timeline=12, repeat=2, healing=4, controls=6)
attack_nullify_path = ROOT / 'data/effect-attack-nullify-evidence.json'
attack_nullify = json.loads(attack_nullify_path.read_text())
assert attack_nullify['schema'] == 1 and attack_nullify['regulationSha256'] == catalog['regulationSha256']
assert attack_nullify['exeSha256'] == evidence['exeSha256'] and not attack_nullify['gameplayVerified']
assert attack_nullify['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in attack_nullify['checks'].items()} == dict(predicate=24, rolls=200, controls=8, ailments=21, repeat=2)
ailment_growth_path = ROOT / 'data/effect-ailment-growth-evidence.json'
ailment_growth = json.loads(ailment_growth_path.read_text())
assert ailment_growth['schema'] == 1 and ailment_growth['regulationSha256'] == catalog['regulationSha256']
assert ailment_growth['exeSha256'] == evidence['exeSha256'] and not ailment_growth['gameplayVerified']
assert ailment_growth['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in ailment_growth['checks'].items()} == dict(gauges=63, activeStates=14, growth=6, numeric=50, timeline=3, clear=6)
frost_stealth_path = ROOT / 'data/effect-frost-stealth-evidence.json'
frost_stealth = json.loads(frost_stealth_path.read_text())
assert frost_stealth['schema'] == 1 and frost_stealth['regulationSha256'] == catalog['regulationSha256']
assert frost_stealth['exeSha256'] == evidence['exeSha256'] and not frost_stealth['gameplayVerified']
assert frost_stealth['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in frost_stealth['checks'].items()} == dict(onset=12, projectile=3, recipients=33, lifetime=18, repeat=16, sourceVariants=6)
duchess_stealth_path = ROOT / 'data/effect-duchess-stealth-evidence.json'
duchess_stealth = json.loads(duchess_stealth_path.read_text())
assert duchess_stealth['schema'] == 1 and duchess_stealth['regulationSha256'] == catalog['regulationSha256']
assert duchess_stealth['exeSha256'] == evidence['exeSha256'] and not duchess_stealth['gameplayVerified']
assert duchess_stealth['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in duchess_stealth['checks'].items()} == dict(rawEvents=3, dispatch=12, lifetime=9, repeat=10, damage=9)
undertaker_contact_path = ROOT / 'data/effect-undertaker-contact-evidence.json'
undertaker_contact = json.loads(undertaker_contact_path.read_text())
assert undertaker_contact['schema'] == 1 and undertaker_contact['regulationSha256'] == catalog['regulationSha256']
assert undertaker_contact['exeSha256'] == evidence['exeSha256'] and not undertaker_contact['gameplayVerified']
assert undertaker_contact['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in undertaker_contact['checks'].items()} == dict(dispatch=32, target=8, healing=24, arrival=24, lateQualification=3)
guardian_ultimate_path = ROOT / 'data/effect-guardian-ultimate-evidence.json'
guardian_ultimate = json.loads(guardian_ultimate_path.read_text())
assert guardian_ultimate['schema'] == 1 and guardian_ultimate['regulationSha256'] == catalog['regulationSha256']
assert guardian_ultimate['exeSha256'] == evidence['exeSha256'] and not guardian_ultimate['gameplayVerified']
assert guardian_ultimate['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in guardian_ultimate['checks'].items()} == dict(dispatch=32, target=12, numeric=15, damage=30, refresh=24, lifetime=6, replenishment=6)

raider_growth_path = ROOT / 'data/effect-raider-growth-evidence.json'
raider_growth = json.loads(raider_growth_path.read_text())
assert raider_growth['schema'] == 1 and raider_growth['regulationSha256'] == catalog['regulationSha256']
assert raider_growth['exeSha256'] == evidence['exeSha256'] and not raider_growth['gameplayVerified']
assert raider_growth['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in raider_growth['checks'].items()} == dict(dispatch=8, growth=18, numeric=110, repeat=5, stable=3)

raider_skill_path = ROOT / 'data/effect-raider-skill-evidence.json'
raider_skill = json.loads(raider_skill_path.read_text())
assert raider_skill['schema'] == 1 and raider_skill['regulationSha256'] == catalog['regulationSha256']
assert raider_skill['exeSha256'] == evidence['exeSha256'] and not raider_skill['gameplayVerified']
assert raider_skill['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in raider_skill['checks'].items()} == dict(script=8, dispatch=72, numeric=88, maintenance=18, transition=6, overlap=6)

duchess_poise_path = ROOT / 'data/effect-duchess-poise-evidence.json'
duchess_poise = json.loads(duchess_poise_path.read_text())
assert duchess_poise['schema'] == 1 and duchess_poise['regulationSha256'] == catalog['regulationSha256']
assert duchess_poise['exeSha256'] == evidence['exeSha256'] and not duchess_poise['gameplayVerified']
assert duchess_poise['paramSha256'] == evidence['paramSha256']
assert {k: len(v) for k, v in duchess_poise['checks'].items()} == dict(dispatch=32, emission=3, consumer=28, refresh=12, lifetime=3)

TOTEM_LEAVES = {7310000: [7310001, 7310002, 7310003, 704100],
                7030000: [7030002, 7030003],
                7090300: [7090302, 7090303, 7090304, 7090305, 7090306, 7090307]}


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
        'startMagicId', 'startSwordArtsId', 'weaponTypeDiscovery', 'heroStatusModifier', 'weakPointValue', 'restageAttackRate', 'saReceiveDamageRate',
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
            needed.update(scripts['effects'].get(str(root), {}).get('seeds', []))
            needed.update(evidence.get('effectLinks', {}).get(str(root), []))
            needed.update(TOTEM_LEAVES.get(root, []))
            if root == recovery['root']:
                needed.add(recovery['leaf'])
            if root == guardian_skill['root']:
                needed.add(guardian_skill['leaf'])
            if root == blade['root']:
                needed.update([7034401, 7034402, 7034403])
            if root == prayer['root']:
                needed.add(prayer['leaf'])
            if root == protection['root']:
                needed.add(protection['leaf'])
            if root in tenacity['roots']:
                needed.update(map(int, tenacity['rows']))
            if root == undertaker_contact['root']:
                needed.update([undertaker_contact['leaf'], undertaker_contact['marker']])
            if root == guardian_ultimate['root']:
                needed.update(guardian_ultimate['leaves'])
            if root == raider_growth['root']:
                needed.update([raider_growth['seed']] + raider_growth['ladder'])
            if root == raider_skill['root']:
                needed.update(raider_skill['leaves'])
            if root == duchess_poise['root']:
                needed.add(duchess_poise['leaf'])
            if root == duchess_ultimate['root']:
                needed.update(map(int, duchess_ultimate['rows']))
            if root == guardian_shock['root']:
                needed.update(map(int, guardian_shock['rows']))
            if root == scholar_tether['root']:
                needed.update(map(int, scholar_tether['rows']))
            if root == scholar_ailment['root']:
                needed.add(scholar_ailment['leaf'])
            if root == revenant_enchant['root']:
                needed.update((revenant_enchant['enchant'], revenant_enchant['frost']))
            if root == wylder_followup['root']:
                needed.update(map(int, wylder_followup['rows']))
            if root == duchess_dagger['root']:
                needed.update(map(int, duchess_dagger['rows']))
            if root in (7030700, 7033300):
                needed.update((root + 1, root + 2))
            if root in item_sharing['roots']:
                needed.update((7050102, 708503, 3970, 7050303))
            if root == ironeye_ultimate['root']:
                needed.update(map(int, ironeye_ultimate['rows']))
            if root == revenant_ghostflame['root']:
                needed.update(map(int, revenant_ghostflame['rows']))
            if root in (flask_sharing['root'], 8440200):
                needed.update(map(int, flask_sharing['rows']))
            if root == attack_nullify['effect']:
                needed.update(map(int, attack_nullify['rows']))
            if root in ailment_growth['roots']:
                needed.update(map(int, ailment_growth['rows']))
            if root == frost_stealth['root']:
                needed.update(map(int, frost_stealth['rows']))
            if root == duchess_stealth['root']:
                needed.update(map(int, duchess_stealth['rows']))
            if root == wylder_bleed['root']:
                needed.add(wylder_bleed['leaf'])
            if root == ironeye_poison['root']:
                needed.update(ironeye_poison['leaves'])
            if root == raider_debuff['root']:
                needed.add(raider_debuff['leaf'])
            if root == absorption['root']:
                needed.update(absorption['markers'] + absorption['leaves'])
            if root == restage['root']:
                needed.update([703540, 7290001])
            if root == recluse_mark['root']:
                needed.update(map(int, recluse_mark['rows']))
            if root in starting_weapon['roots']:
                needed.update(root + n for n in range(1, 5))
            if root == evasion['root']:
                needed.add(evasion['leaf'])
            if root == executor['root']:
                needed.update(map(int, executor['rows']))
            if root == sacrifice['root']:
                needed.update(map(int, sacrifice['rows']))
            if root in gesture['roots']:
                needed.update([root + 1, root + 2])
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
        (['ultimateArtGaugeRate', 'ultimateArtGaugeChargeRate'], '绝招量表累积（所有来源）'),
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
        if timing['repeatedApplication'] == 'ignored':
            assert any(r['leaf'] == id and r['rejectedResult'] == 0xfffffffe
                       for r in weapon_recovery['checks']['reapplication'])
            restrictions.append(f'同类恢复约 {num(duration)} 秒内只触发一次，连续命中不会延长间隔')
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
    'guardian-recovery': ('不可叠加', '同类恢复只刷新有效期', ['recovery-emitter', 'recovery-arrival']),
    'guardian-skill': ('不可叠加', '重复装备不增加单次恢复量', ['guardian-skill']),
    'executor-blade': ('不可叠加', '重复装备不增加增益或负面效果', ['executor-blade']),
    'undertaker-prayer': ('不可叠加', '再次触发刷新时长', ['undertaker-prayer']),
    'guardian-protection': ('不可叠加', '同类效果再次施加刷新时长', ['guardian-protection']),
    'executor-recovery': ('不可叠加', '重复装备不增加单次恢复量', ['executor-recovery']),
    'executor-tenacity': ('不可叠加', '重复装备不增加效果', ['executor-tenacity']),
    'undertaker-reset': ('不可叠加', '重复装备不增加恢复次数', ['undertaker-reset']),
    'treasure-map': ('不可叠加', '重复装备不增加标记', ['treasure-map']),
    'resource-capacity': ('可叠加', '上限倍率相乘', ['passive-resource']),
    'passive-poise': ('可叠加', '受到的强韧度损耗倍率相乘', ['passive-resource']),
    'flask-recovery': ('可叠加', '恢复量倍率相乘；提升与降低也相乘', ['passive-resource']),
    'damage-ailment': ('可叠加', '同种异常的累积量相加', ['damage-ailment']),
    'spell-family': ('可叠加', '攻击倍率相乘', ['spell-family']),
    'perfume': ('可叠加', '攻击倍率相乘', ['perfume']),
    'duchess-ultimate': ('不可叠加', '重复装备不增加时长或增伤', ['duchess-ultimate']),
    'guardian-shockwave': ('不可叠加', '重复装备不增加冲击波数量', ['guardian-shockwave']),
    'hero-adjustment': ('不可叠加', '同一词条只生效一次；不同词条的增减相加', ['hero-adjustment']),
    'successive-recovery': ('可叠加', '恢复量相加；累积衰减也叠加', ['successive-recovery']),
    'successive-attack': ('不可叠加', '重复装备不增加增伤或累积速度', ['successive-attack']),
    'scholar-tether': ('不可叠加', '重复装备不增加单次伤害', ['scholar-tether']),
    'scholar-ailment': ('不可叠加', '同类效果再次施加刷新时长，不叠加倍率', ['scholar-ailment']),
    'wylder-flame': ('不可叠加', '重复装备不增加火焰数量或持续时间', ['wylder-flame']),
    'revenant-enchant': ('不可叠加', '再次施加刷新附魔时长，不叠加数值', ['revenant-enchant']),
    'revenant-family': ('不可叠加', '重复装备不增加家人数量', ['revenant-family']),
    'guardian-halberd': ('不可叠加', '重复装备不增加旋风数量或范围', ['guardian-halberd']),
    'wylder-followup': ('不可叠加', '再次触发刷新附魔时长，不叠加数值', ['wylder-followup']),
    'duchess-dagger': ('不可叠加', '重复装备不增加重演比例或触发次数', ['duchess-dagger']),
    'equipped-exclusive': ('不可叠加', '相同词条只生效一次', ['equipped-exclusivity']),
    'starting-replacement': ('不可叠加', '相同词条重复无效', ['starting-replacements']),
    'guard-aggro': ('不可叠加', '同类重复装备不增加优先度；再次触发刷新时长', ['guard-aggro']),
    'item-sharing': ('不可叠加', '重复装备不增加共享范围或效果', ['item-sharing']),
    'ironeye-ultimate': ('不可叠加', '重复装备不增加累积或伤害', ['ironeye-ultimate']),
    'revenant-ghostflame': ('不可叠加', '重复装备不增加爆炸次数或冻伤累积', ['revenant-ghostflame']),
    'scholar-feint': ('不可叠加', '重复装备不延长弹反窗口', ['scholar-feint']),
    'flask-sharing': ('不可叠加', '重复装备不增加恢复量；同类持续恢复再次施加刷新时长，不叠加速度', ['flask-sharing']),
    'gradual-flask': ('不可叠加', '再次喝瓶刷新持续恢复，不叠加速度', ['flask-sharing']),
    'rally-recovery': ('不同等级可叠加', '同等级不重复；+1 与 +2 的恢复量倍率相乘，普通版无额外加成', ['rally-recovery']),
    'rally-blessing': ('可叠加', '可与遗物的恢复量倍率相乘；自身不重复', ['rally-recovery']),
    'attack-nullify': ('不可叠加', '重复装备不提高概率', ['attack-nullify']),
    'ailment-growth': ('不可叠加', '重复装备不加快增长，也不提高上限', ['ailment-growth']),
    'frost-stealth': ('不可叠加', '重复装备不延长隐身', ['frost-stealth']),
    'duchess-stealth': ('不可叠加', '重复装备不增强或延长隐匿', ['duchess-stealth']),
    'periodic-hp-recovery': ('可叠加', '恢复量相加，各自计时', ['periodic-hp']),
    'periodic-hp-loss': ('可叠加', '消耗量相加，各自计时', ['periodic-hp']),
    'undertaker-contact': ('不可叠加', '重复装备不增加单次恢复量', ['undertaker-contact']),
    'guardian-ultimate': ('不可叠加', '再次施加刷新时长', ['guardian-ultimate']),
    'raider-growth': ('不可叠加', '重复装备不加快成长，也不提高上限', ['raider-growth']),
    'raider-skill': ('不可叠加', '重复装备不增加增益或负面效果', ['raider-skill']),
    'duchess-poise': ('不可叠加', '再次施加刷新时长', ['duchess-poise']),
    'wylder-bleed': ('不可叠加', '重复装备不增加累积或伤害', ['wylder-bleed']),
    'ironeye-poison': ('不可叠加', '重复装备不增加累积或伤害', ['ironeye-poison']),
    'raider-debuff': ('不可叠加', '再次命中刷新时长', ['raider-debuff']),
    'recluse-absorption': ('不可叠加', '同属性再次收集刷新时长；不同属性可同时生效', ['recluse-absorption']),
    'duchess-restage': ('不可叠加', '重复装备不增加重演比例', ['duchess-restage']),
    'ironeye-mark': ('不可叠加', '重复装备不延长弱点持续时间', ['ironeye-mark']),
    'recluse-mark': ('不可叠加', '重复装备不延长烙印持续时间', ['recluse-mark']),
    'starting-pouch': ('可叠加', '每条 +1 格，与小型随身包合计最多 +4 格', ['starting-goods']),
    'starting-goods': ('可叠加', '数量相加，按单格上限分装', ['starting-goods']),
    'starting-weapon': ('不可叠加', '出击武器的属性／异常附加只生效一种', ['starting-weapon']),
    'guardian-duration': ('不可叠加', '重复装备不延长旋风持续时间', ['guardian-duration']),
    'duchess-evasion': ('不可叠加', '再次触发刷新时长', ['duchess-evasion']),
    'weapon-recovery': ('不可叠加', '同种词条重复无效；回血与回蓝可同时生效', ['weapon-recovery']),
    'recluse-bleed': ('不可叠加', '重复装备不增加单次触发收益', ['recluse-bleed']),
    'revenant-sacrifice': ('不可叠加', '重复装备不增加单次触发收益', ['revenant-sacrifice']),
    'gesture-madness': ('可叠加', '不同版本的累积相加；同版重复无效', ['gesture-madness']),
    'role-repeat': ('不可叠加', '重复装备不增加单次触发收益', ['effect-lifecycle']),
    'wylder-skill': ('不可叠加', '重复装备不增加单次触发收益', ['action-triggers', 'action-start', 'skill-stack']),
    'role-max-hp': ('不可叠加', '同类增益互相覆盖', ['action-triggers', 'role-lifecycle']),
    'totem': ('不可叠加', '同类图腾增益覆盖并刷新持续时间', ['totem-animation', 'totem-native']),
    'attributes': ('可叠加', '能力值相加', ['equip-injection', 'instance-matching', 'attributes']),
    'attack': ('可叠加', '攻击倍率相乘', ['equip-injection', 'instance-matching', 'attack']),
    'defense': ('可叠加', '承伤倍率相乘', ['equip-injection', 'instance-matching', 'defense']),
    'cooldown': ('可叠加', '冷却时间倍率相乘', ['equip-injection', 'instance-matching', 'cooldown']),
    'gauge': ('可叠加', '绝招量表累积倍率相乘', ['equip-injection', 'instance-matching', 'gauge']),
    'resistance': ('可叠加', '抵抗力点数相加', ['equip-injection', 'instance-matching', 'resistance']),
    'fp-cost': ('可叠加', 'FP 消耗倍率相乘', ['equip-injection', 'instance-matching', 'fpCost']),
    'weapon-count': ('不可叠加', '同种武器条件重复无效；不同武器种类分别满足条件时，可同时生效', ['instance-matching', 'weapon-count']),
    'discovery': ('不可叠加', '多个武器倾向同时存在时，采用生效列表中的第一个', ['discovery', 'discovery-selection', 'discovery-draws']),
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
    'magic-zone': ('不可叠加', '与其他魔法之境共用增益；后命中的效果覆盖前者，不自动保留较强者', ['action-script', 'bullet-links', 'zoneMatching']),
    'scholar-decay': ('不可叠加', '重复装备只生效一份', ['instance-matching', 'scholarDecay']),
    'scholar-ally': ('不可叠加', '相同增益覆盖并刷新持续时间', ['scholarAlly']),
    'guard-counter-hp': ('不可叠加', '重复装备只生效一份', ['instance-matching', 'guardCounter']),
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
    for root in effect['roots'].values():
        pending.extend((seed, '收集属性痕后', True, 0)
                       for seed in scripts['effects'].get(str(root), {}).get('seeds', []))
        pending.extend((leaf, '技艺作用于友方时', True, 0)
                       for leaf in evidence.get('effectLinks', {}).get(str(root), []))
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
        root = next(iter(effect['roots'].values()))
        measured = [r for r in discovery['selection'] if r['ids'] == [root]]
        assert len(measured) == 10 and all(r['bias'] == roots[0]['weaponTypeDiscovery'] for r in measured)
        assert name.startswith('通过潜在能力，能比较容易找到')
        blocks = [dict(source=root, phase='潜在能力奖励', linked=False,
                       values=[['武器倾向', name.removeprefix('通过潜在能力，能比较容易找到')]],
                       restrictions=['替换角色默认倾向'], scope=[], duration=None, interval=None)]
        notes.append('仅影响支持武器倾向的奖励；具体概率随奖池和候选权重变化。')
    if len(roots) == 1 and list(effect['roots'].values())[0] in (7033200, 7270100):
        rule = 'skill-uses'
    if len(roots) == 1 and list(effect['roots'].values())[0] in (7230000, 7230001):
        rule = 'shop-discount'
    if id in weapon_recovery_families:
        family = weapon_recovery_families[id]
        for b in blocks:
            if b['source'] == family['leaf']:
                b['phase'] = '对应武器命中时' if family['nativeTypeAccepted'] else '恢复参数'
        if family['nativeTypeAccepted']:
            rule = 'weapon-recovery'
        else:
            notes.append('实际触发待确认。')
    if len(external) == 1 and effect['runtimeExclusive'] == -1:
        family = external[0]['family']
        if family not in ('madness-fp', 'revenant-allies', 'random-weapon', 'undertaker-growth', 'wylder-skill', 'recluse-max-hp', 'recluse-bleed', 'revenant-damage', 'duchess-kill'):
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
    totem_roots = set(effect['roots'].values()) & TOTEM_LEAVES.keys()
    if totem_roots:
        assert len(totem_roots) == 1
        root = totem_roots.pop()
        rule = 'totem'
        if root == 7310000:
            blocks = [dict(source=root, branches=TOTEM_LEAVES[root], phase='绝招发动后', linked=True,
                values=[['图腾持续时间', '20 → 30 秒'], ['攻击增益持续时间', '30 → 45 秒']],
                restrictions=[], scope=[], duration=None, interval=None)]
        elif root == 7030000:
            assert source['spells']['7030002']['toughnessDamageCutRate'] == .1
            blocks = [dict(source=7030002, branches=[7030003], phase='获得图腾增益后', linked=True,
                values=[['强韧度损耗', '-90%']], restrictions=[], scope=[], duration=20, interval=None)]
            notes.append('搭配延长绝招时持续 30 秒。')
        else:
            assert [source['spells'][str(i)]['changeHpRate'] for i in (7090306, 7090303)] == [-20, -50]
            blocks = [dict(source=7090300, branches=TOTEM_LEAVES[root], phase='图腾增益期间打倒敌人时', linked=True,
                values=[['HP', '+20% 或 +50% 最大 HP']], restrictions=['恢复量随敌人类型变化'],
                scope=[], duration=None, interval=None)]
            notes.append('图腾增益持续 20 秒；搭配延长绝招时为 30 秒。')
    if set(effect['roots'].values()) & {7020100, 7020200, 7036800}:
        for b in blocks:
            b['scope'] = []
            if b['source'] == 7020101:
                assert all(source['spells']['7020101'][k] == 1.2 for k in
                           ('physicsAttackRate', 'maxStaminaRate', 'neutralDamageCutRate',
                            'slashDamageCutRate', 'blowDamageCutRate', 'thrustDamageCutRate',
                            'magicDamageCutRate', 'fireDamageCutRate', 'thunderDamageCutRate', 'darkDamageCutRate'))
                b['values'] = [['攻击倍率', '+20%'], ['精力上限', '+20%'], ['承伤倍率', '+20%']]
    if 7020200 in effect['roots'].values():
        assert len(evidence['skillStack']) == 9
        rule = 'wylder-skill'
        notes.append('连续发动技艺可叠加增益，倍率相乘、分别计时；两次触发合计 +21%。')
    if 7034100 in effect['roots'].values():
        assert all(source['spells'][str(sp)]['maxHpRate'] == 1.5 for sp in (7034102, 7034104))
        assert source['spells']['7034104']['deleteCriteriaDamage'] == 1
        assert source['spells']['7034103']['effectEndurance'] == 29.9
        assert all(r['active'] == r['incoming'] for r in evidence['roleLifecycle'] if 'incoming' in r)
        blocks = [dict(source=7034102, branches=[7034101, 7034103, 7034104], phase='绝招发动后', linked=True,
                       values=[['血量上限', '+50%']], restrictions=[], scope=[], duration=None, interval=None)]
        notes.append('前约 30 秒不因受损结束；之后持续至下次受到损伤。')
        rule = 'role-max-hp'
    if recluse_bleed['root'] in effect['roots'].values():
        assert source['spells']['7032902']['changeHpRate'] == 20
        assert source['spells']['7032903']['physicsAttackRate'] == 1.16
        blocks = [dict(source=7032902, branches=[7032901], phase='自身出血时', linked=True,
                       values=[['基础 HP 损失', '最大值的 20%']],
                       restrictions=['自伤可使 HP 归零'], scope=[], duration=None, interval=None),
                  dict(source=7032903, phase='自身出血后', linked=True,
                       values=[['攻击倍率', '+16%']],
                       restrictions=[], scope=[], duration=30, interval=None)]
        notes.extend(['需实际触发自身出血；免疫时也不会获得增攻。',
                      '多次发动的增益倍率相乘、分别计时；两次合计 +34.56%。'])
        rule = 'recluse-bleed'
    gesture_roots = set(effect['roots'].values()) & set(gesture['roots'])
    if gesture_roots:
        root = next(iter(gesture_roots))
        leaf = source['spells'][str(root + 2)]
        assert leaf['madnessAttackPower'] == 10 and leaf['changeHpRate'] == 10
        assert leaf['changeHpPoint'] == 100 and leaf['changeMpPoint'] == 30
        blocks = [dict(source=root + 2, branches=[root + 1], phase='盘腿坐期间', linked=True,
                       values=[['基础发狂累积', '10']], restrictions=['约每 0.1 秒累积一次'],
                       scope=[], duration=None, interval=None),
                  dict(source=root + 2, phase='实际发狂时', linked=True,
                       values=[['基础 HP 损失', '最大值的 10% + 100'], ['FP 损失', '30']],
                       restrictions=[], scope=[], duration=None, interval=None)]
        notes.append('免疫发狂时不会累积，也不会因此损失 HP／FP。')
        rule = 'gesture-madness'
    if sacrifice['root'] in effect['roots'].values():
        assert source['spells']['7010901']['changeHpRate'] == 50
        assert all(source['spells'][str(i)]['changeHpRate'] == -100 for i in (7010902, 7010906))
        assert source['spells']['7010906']['effectEndurance'] == .5
        assert sacrifice['bullet']['hitRadius'] == 30
        blocks = [dict(source=7010901, phase='绝招发动时 · 自身', linked=True,
                       values=[['HP 损失', '最大值的 50%']],
                       restrictions=[], scope=[], duration=None, interval=None),
                  dict(source=7010902, phase='绝招发动时 · 周围友方', linked=True,
                       values=[['HP 恢复', '最大值的 100%']],
                       restrictions=['半径 30 米 · 不含自身'], scope=[], duration=None, interval=None),
                  dict(source=7010906, branches=[7010905, 7010909], phase='命中倒地友方后，获救时', linked=True,
                       values=[['每次 HP 恢复', '最大值的 100%']],
                       restrictions=['持续恢复'], scope=[], duration=.5, interval=None)]
        rule = 'revenant-sacrifice'
    if executor['root'] in effect['roots'].values():
        leaf = executor['leaf']
        assert source['spells'][str(leaf)]['changeHpRate'] == -5
        assert source['spells'][str(leaf)]['changeHpPoint'] == -100
        blocks = [dict(source=leaf, branches=[int(i) for i in executor['rows'] if int(i) not in (leaf, executor['root'])],
                       phase='妖刀进入解放状态时', linked=True,
                       values=[['HP 恢复', '最大值的 5% + 100']],
                       restrictions=[], scope=[], duration=None, interval=None)]
        notes.append('每次进入解放状态恢复一次；维持解放状态不会反复恢复。')
        rule = 'executor-recovery'
    if blade['root'] in effect['roots'].values():
        assert source['spells']['7034402']['physicsAttackRate'] == 1.35
        assert source['spells']['7034402']['magicSubCategoryChange1'] == 122
        assert source['spells']['7034403']['neutralDamageCutRate'] == 1.4
        assert source['spells']['7034403']['effectEndurance'] == 5
        blocks = [dict(source=7034402, branches=[7034401], phase='妖刀状态下的技艺攻击', linked=True,
                       values=[['攻击倍率', '+35%']], restrictions=[], scope=[], duration=None, interval=None),
                  dict(source=7034403, phase='上述攻击命中造成损伤后 · 自身', linked=True,
                       values=[['承伤倍率', '+40%']], restrictions=[], scope=[], duration=5, interval=None)]
        notes.extend(['妖刀跑动重攻击的前段不适用，后段适用。',
                      '连续命中刷新负面效果的 5 秒时长；收刀不会提前解除已经触发的负面效果。'])
        rule = 'executor-blade'
    if prayer['root'] in effect['roots'].values():
        assert source['spells']['7037001']['physicsAttackRate'] == 1.19
        assert source['spells']['7037001']['effectEndurance'] == 60
        blocks = [dict(source=7037001, phase='祷告触发后', linked=True,
                       values=[['物理攻击倍率', '+19%']], restrictions=[], scope=[], duration=60, interval=None)]
        notes.extend(['恢复类祷告和武器附魔也可触发。', '远方之恢复的触发待确认。'])
        rule = 'undertaker-prayer'
    if recovery['root'] in effect['roots'].values():
        leaf = recovery['leaf']
        assert source['spells'][str(leaf)]['changeHpRate'] == -10
        assert source['spells'][str(leaf)]['changeHpPoint'] == -12
        assert source['spells'][str(leaf)]['motionInterval'] == 1
        assert recovery['bullet']['hitRadius'] == 15
        blocks = [dict(source=leaf, phase='绝招的恢复范围内', linked=True,
                       values=[['HP 恢复', '最大值的 10% + 12']],
                       restrictions=['自身及周围友方 · 半径 15 米'], scope=[], duration=None, interval=None)]
        notes.extend(['首次生效恢复一次，持续生效时约每秒恢复一次。',
                      '停止施加后，尚未到期的效果仍可能再恢复一次。'])
        rule = 'guardian-recovery'
    if guardian_skill['root'] in effect['roots'].values():
        leaf = guardian_skill['leaf']
        assert source['spells'][str(leaf)]['changeHpRate'] == -15
        assert source['spells'][str(leaf)]['changeHpPoint'] == 0
        assert guardian_skill['bullet']['hitRadius'] == 8
        blocks = [dict(source=leaf, phase='技艺发动时', linked=True,
                       values=[['HP 恢复', '最大值的 15%']],
                       restrictions=['自身及周围友方 · 半径 8 米'], scope=[], duration=None, interval=None)]
        notes.append('同类恢复同时到达只恢复一次；短时间内再次到达可能合并或延后恢复。')
        rule = 'guardian-skill'
    if protection['root'] in effect['roots'].values():
        leaf = protection['leaf']
        assert source['spells'][str(leaf)]['neutralDamageCutRate'] == .82
        assert source['spells'][str(leaf)]['effectEndurance'] == 30
        assert protection['bullet']['hitRadius'] == 8
        blocks = [dict(source=leaf, phase='获得技艺增益后', linked=True,
                       values=[['承伤倍率', '-18%']],
                       restrictions=['自身及周围友方 · 半径 8 米'], scope=[], duration=30, interval=None)]
        rule = 'guardian-protection'
    if 7500700 in effect['roots'].values():
        assert all(source['spells'][str(sp)]['changeHpRate'] == -.27 for sp in (7500701, 7500702))
        assert all(source['spells'][str(sp)]['changeHpPoint'] == -3 for sp in (7500701, 7500702))
        assert source['spells']['7500701']['effectEndurance'] + source['spells']['7500702']['effectEndurance'] == 60
        blocks = [dict(source=7500701, branches=[7500702], phase='能力发动后', linked=True,
                       values=[['HP 恢复', '最大值的 0.27% + 3']],
                       restrictions=[], scope=[], duration=60, interval=1)]
        notes.extend(['开始恢复时立即恢复一次，约 1.5 秒后的衔接也会恢复一次。',
                      '能力再次发动会追加持续恢复，恢复量相加、分别计时。'])
        rule = 'executor-tenacity'
    if 7501100 in effect['roots'].values():
        assert all(source['spells'][str(sp)]['physicsAttackRate'] == 1.05 for sp in (7501101, 7501102))
        assert all(source['spells'][str(sp)]['physicsAttackRate'] == 1.2 for sp in (707070, 707071))
        assert source['spells']['7501101']['effectEndurance'] + source['spells']['7501102']['effectEndurance'] == 20
        assert all(v['values'] == [-80] * 7 for v in tenacity['checks']['resistance'] if v['copies'])
        blocks = [dict(source=7501100, phase='装备时', linked=False,
                       values=[['异常状态抵抗力', '-80']],
                       restrictions=[], scope=[], duration=None, interval=None),
                  dict(source=7501101, branches=[7501102, 707070, 707071], phase='能力发动后', linked=True,
                       values=[['能力的攻击倍率', '+20% → +26%']],
                       restrictions=[], scope=[], duration=20, interval=None)]
        notes.append('能力再次发动会追加攻击增益，倍率相乘、分别计时。')
        rule = 'executor-tenacity'
    if any(f['root'] == int(id) for f in spell_family['families']):
        family = next(f for f in spell_family['families'] if f['root'] == int(id))
        assert list(effect['roots'].values()) == [family['root']] and effect['runtimeExclusive'] == -1
        assert source['spells'][id]['magicSubCategoryChange1'] == family['category']
        rule = 'spell-family'
    if any(f['effect'] == int(id) for f in perfume['families']):
        family = next(f for f in perfume['families'] if f['effect'] == int(id))
        assert list(effect['roots'].values()) == [family['root']] and effect['runtimeExclusive'] == -1
        assert source['spells'][str(family['root'])]['cycleOccurrenceSpEffectId'] == family['leaf']
        blocks = []
        for key, category, label in [('root', 109, '调香类道具'), ('leaf', 251, '调香瓶攻击')]:
            sp = family[key]
            assert source['spells'][str(sp)]['magicSubCategoryChange1'] == category
            b = block(sp, '生效时', False)
            b['restrictions'] = ['适用：' + label]
            b['duration'] = b['interval'] = None
            blocks.append(b)
        rule = 'perfume'
    if int(id) in duchess_ultimate['effects']:
        assert list(effect['roots'].values()) == [duchess_ultimate['root']] and effect['runtimeExclusive'] == -1
        assert source['spells']['7033010']['effectEndurance'] == 25
        assert source['spells']['703500']['effectEndurance'] == 15
        assert duchess_ultimate['thresholds'] == [17, 30, 45, 60]
        assert duchess_ultimate['rates'] == [1.09, 1.13, 1.2, 1.2]
        blocks = [dict(source=7033010, phase='绝招发动后', linked=True,
                       values=[['绝招持续时间', '15 → 25 秒']],
                       restrictions=['仅自身'], scope=[], duration=None, interval=None),
                  dict(source=7033024, branches=list(range(7033025, 7033032)), phase='绝招期间连续攻击', linked=True,
                       values=[['攻击倍率', '+9% → +23.17% → +47.80% → +77.36%']],
                       restrictions=[], scope=[], duration=None, interval=None)]
        notes.append('增伤逐档累积；停止攻击后逐渐衰退。')
        rule = 'duchess-ultimate'
    if int(id) == guardian_shock['effect']:
        assert list(effect['roots'].values()) == [guardian_shock['root']] and effect['runtimeExclusive'] == -1
        assert source['spells']['7033405']['changeHpRate'] == 0.12
        assert guardian_shock['bullet']['hitRadius'] == 2.5 and guardian_shock['bullet']['hitRadiusMax'] == 3.5
        blocks = [dict(source=guardian_shock['emitter'], branches=[guardian_shock['leaf']], phase='能力防御成功时', linked=True,
                       values=[['冲击波半径', '2.5 → 3.5 米'], ['额外 HP 伤害', '目标最大值的 0.12%']],
                       restrictions=[], scope=[], duration=None, interval=None)]
        notes.append('连续防御可再次触发。')
        rule = 'guardian-shockwave'
    if id in periodic_hp['rows']:
        row = periodic_hp['rows'][id]
        assert list(effect['roots'].values()) == [int(id)] and effect['runtimeExclusive'] == -1
        assert source['spells'][id]['changeHpPoint'] == row['changeHpPoint']
        assert source['spells'][id]['motionInterval'] == row['motionInterval']
        rule = 'periodic-hp-recovery' if row['changeHpPoint'] < 0 else 'periodic-hp-loss'
    for family in hero_adjustment['families']:
        if int(id) in family['effects']:
            index = family['effects'].index(int(id))
            root = family['roots'][index]
            assert list(effect['roots'].values()) == [root]
            assert effect['runtimeExclusive'] == family['runtimeExclusive'][index]
            assert source['spells'][str(root)]['stateInfo'] == 2123
            assert source['spells'][str(root)]['heroStatusModifier'] == family['modifiers'][index]
            assert source['spells'][str(root)]['invocationConditionsStateChange1'] == family['state']
            blocks = [block(root, '随等级调整能力值', False, {family['state']})]
            rule = 'hero-adjustment'
    if int(id) in successive_recovery['effects']:
        assert effect['runtimeExclusive'] == -1 and len(effect['roots']) == 1
        root = next(iter(effect['roots'].values()))
        index = successive_recovery['roots'].index(root)
        leaf = successive_recovery['leaves'][index]
        assert source['spells'][str(root)]['accumuOverVal'] == successive_recovery['threshold'] == 32
        assert source['spells'][str(root)]['accumuOverFireId'] == leaf
        assert source['spells'][str(leaf)]['changeMpRate'] == (-5 if index == 0 else 0)
        assert source['spells'][str(leaf)]['changeHpRate'] == (-3 if index == 1 else 0)
        blocks = [block(leaf, '连续攻击达标时', True)]
        assert blocks[0]['duration'] is None and blocks[0]['interval'] is None
        notes.extend(['累积达到 32 点时触发；每份词条每 0.8 秒减少 1 点累积。',
                      '回血与回蓝共用累积进度，可同时触发。'])
        rule = 'successive-recovery'
    if int(id) == successive_attack['effect']:
        assert list(effect['roots'].values()) == successive_attack['roots'] and effect['runtimeExclusive'] == -1
        assert successive_attack['thresholds'] == [17, 30, 45, 60]
        assert successive_attack['rates'] == [1.05, 1.065, 1.09, 1]
        assert source['spells']['7037607']['physicsAttackRate'] == 1
        blocks = [dict(source=7037604, branches=[7037605, 7037606, 7037603, 7037607], phase='连续攻击时', linked=True,
                       values=[['攻击倍率', '+5% → +11.83% → +21.89%']],
                       restrictions=[], scope=[], duration=None, interval=None)]
        notes.append('增伤逐档累积；停止攻击后逐渐衰退。')
        rule = 'successive-attack'
    if int(id) == scholar_tether['root']:
        assert list(effect['roots'].values()) == [scholar_tether['root']] and effect['runtimeExclusive'] == -1
        r = source['spells'][str(scholar_tether['leaf'])]
        assert r['changeHpPoint'] == 15 and r['changeHpRate'] == 0
        assert r['effectEndurance'] == 20 and r['motionInterval'] == 1 and r['invocationConditionsStateChange1'] == 2222
        blocks = [dict(source=scholar_tether['leaf'], phase='连结期间', linked=True,
                       values=[['HP 伤害', '15 点／次']], restrictions=['仅连结期间计时'], scope=[], duration=20, interval=1)]
        notes.extend(['未连结时暂停；连结后继续剩余时间。', '多次绝招施加的持续伤害各自计时，可叠加。'])
        rule = 'scholar-tether'
    if int(id) == ironeye_ultimate['root']:
        assert list(effect['roots'].values()) == [ironeye_ultimate['root']] and effect['runtimeExclusive'] == -1
        r = source['spells'][str(ironeye_ultimate['leaf'])]
        assert r['poizonAttackPower'] == 300 and r['changeHpPoint'] == 10 and r['changeHpRate'] == .1
        assert r['effectEndurance'] == 40 and math.isclose(r['motionInterval'], 1.3, rel_tol=1e-6)
        blocks = [dict(source=ironeye_ultimate['leaf'], phase='蓄力绝招命中时', linked=True,
                       values=[['中毒基础累积', '300']], restrictions=[], scope=[], duration=None, interval=None),
                  dict(source=ironeye_ultimate['leaf'], phase='中毒发作后', linked=True,
                       values=[['中毒伤害', '最大血量的 0.1% + 10']], restrictions=[], scope=[], duration=40, interval=1.3)]
        notes.extend(['提前放箭不附加此中毒。', '中毒期间再次命中不刷新这次中毒时长。'])
        rule = 'ironeye-ultimate'
    if int(id) == revenant_ghostflame['root']:
        assert list(effect['roots'].values()) == [revenant_ghostflame['root']] and effect['runtimeExclusive'] == -1
        r = source['spells'][str(revenant_ghostflame['leaf'])]
        assert r['freezeAttackPower'] == 50 and r['changeHpRate'] == 10 and r['changeHpPoint'] == 50
        assert r['effectEndurance'] == 30 and r['motionInterval'] == 99
        assert math.isclose(r['magicDamageCutRate'], 1.15, rel_tol=1e-6)
        blocks = [dict(source=revenant_ghostflame['leaf'], phase='爆炸命中时', linked=True,
                       values=[['爆炸半径', '4 → 10 米'], ['冻伤基础累积', '50']], restrictions=[], scope=[], duration=None, interval=None),
                  dict(source=revenant_ghostflame['leaf'], phase='冻伤发作时', linked=True,
                       values=[['冻伤伤害', '最大血量的 10% + 50']], restrictions=[], scope=[], duration=None, interval=None),
                  dict(source=revenant_ghostflame['leaf'], phase='冻伤期间', linked=True,
                       values=[['承伤倍率', '+15%']], restrictions=[], scope=[], duration=30, interval=None)]
        notes.append('再次命中不刷新这次冻伤时长。')
        rule = 'revenant-ghostflame'
    if int(id) == scholar_feint['root']:
        assert list(effect['roots'].values()) == [scholar_feint['root']] and effect['runtimeExclusive'] == -1
        blocks = [dict(source=scholar_feint['root'], phase='佯攻时', linked=False,
                       values=[['弹反窗口', '动作第 0.13～0.27 秒']], restrictions=['刺剑／重刺剑'],
                       scope=[], duration=None, interval=None)]
        rule = 'scholar-feint'
    if id in equipped_exclusive_families:
        family = equipped_exclusive_families[id]
        assert list(effect['roots'].values()) == [family['root']] and effect['runtimeExclusive'] == family['exclusive']
        assert source['spells'][str(family['root'])]['spCategory'] == 10
        if id == '7006600':
            notes.append('与战技攻击强化 +15% 同时生效时，攻击倍率合计 +21.9%。')
        if id == '7006700':
            notes.append('与近战攻击强化 +6% 同时生效时，攻击倍率合计 +21.9%。')
        rule = 'equipped-exclusive'
    if id in starting_replacement_families:
        family = starting_replacement_families[id]
        assert list(effect['roots'].values()) == [family['root']]
        field = 'startSwordArtsId' if family['kind'] == 'arts' else 'startMagicId'
        assert source['spells'][str(family['root'])][field] == family['target']
        assert len(blocks) == 1 and blocks[0]['duration'] is None
        blocks[0]['scope'] = ['出击武器'] if family['kind'] == 'arts' else ['出击手杖／圣印记']
        blocks[0]['restrictions'] = ['出击武器', '需符合战技的武器类别'] if family['kind'] == 'arts' else ['出击手杖／圣印记']
        notes.append('同一武器只保留一个出击战技。' if family['kind'] == 'arts' else '同一武器只保留一种出击魔法或祷告。')
        rule = 'starting-replacement'
    if id in guard_aggro_families:
        family = guard_aggro_families[id]
        assert list(effect['roots'].values()) == [family['root']]
        leaf = source['spells'][str(family['leaf'])]
        assert leaf['effectEndurance'] == family['duration']
        assert guard_aggro['rows'][str(family['leaf'])]['targetPriority'] == family['priority']
        blocks = [dict(source=family['leaf'], phase='防御时' if family['root'] == 7030700 else '能力发动时', linked=True,
                       values=[['受敌人攻击优先度', '+' + str(family['priority'])]], restrictions=[], scope=[],
                       duration=family['duration'], interval=None)]
        notes.append('防御与守护者能力的吸引效果可相加，优先度合计 +1050。')
        rule = 'guard-aggro'
    if int(id) in item_sharing['effects']:
        assert list(effect['roots'].values()) == item_sharing['roots']
        assert source['spells']['7050102']['changeMpRate'] == -30 and source['spells']['708503']['changeMpRate'] == -40
        assert source['spells']['3970']['itemDropRate'] == .3 and source['spells']['7050303']['itemDropRate'] == .2
        assert all(row['hitRadius'] == 15 for row in item_sharing['bullets'].values())
        blocks = [dict(source=7050300, phase='使用道具时', linked=True,
                       values=[['共享半径', '15 米']], scope=['附近我方'],
                       restrictions=['星光碎片、苔药、勇者肉块、龟颈肉、鸟爪、煮熟虾蟹'], duration=None, interval=None),
                  dict(source=7050102, branches=[708503], phase='共享星光碎片', linked=True,
                       values=[['我方专注值恢复', '最大值的 30%（学者强化后 40%）']],
                       scope=[], restrictions=[], duration=None, interval=None)]
        notes.append('普通白银鸟爪共享后也会降低自身收益：基础观察力 100 时，使用后由 130 变为 121。')
        rule = 'item-sharing'
    if int(id) in duchess_dagger['effects']:
        assert list(effect['roots'].values()) == [duchess_dagger['root']]
        assert source['spells'][str(duchess_dagger['leaf'])]['restageAttackRate'] == .4
        assert duchess_dagger['bullet']['hitRadius'] == duchess_dagger['bullet']['hitRadiusMax'] == 15
        blocks = [dict(source=duchess_dagger['leaf'], phase='短剑连击最后一击命中时', linked=True,
                       values=[['重演伤害比例', '40%'], ['作用半径', '15 米']],
                       restrictions=[], scope=[], duration=None, interval=None)]
        notes.append('强化技艺的重演伤害词条不提高此效果的重演比例。')
        rule = 'duchess-dagger'
    if int(id) in wylder_followup['effects']:
        assert list(effect['roots'].values()) == [wylder_followup['root']]
        for leaf in wylder_followup['leaves']:
            buff = source['spells'][str(leaf)]
            assert buff['fireAttackPower'] == 20 and buff['effectEndurance'] == 20
        blocks = [dict(source=wylder_followup['leaves'][0], branches=wylder_followup['leaves'][1:], phase='追加攻击时', linked=True,
                       values=[['火焰基础攻击力', '+20']], restrictions=['对应手持武器'], scope=[], duration=20, interval=None)]
        notes.append('与同一只手的同类附魔互相覆盖，保留后施加的效果。')
        rule = 'wylder-followup'
    if int(id) in guardian_halberd['effects']:
        assert list(effect['roots'].values()) == [guardian_halberd['root']]
        radius = guardian_halberd['bullets']['30901146']['hitRadius']
        assert radius == guardian_halberd['bullets']['30901146']['hitRadiusMax'] == 3
        blocks = [dict(source=guardian_halberd['root'], phase='戟蓄力攻击时', linked=True,
                       values=[['旋风半径', num(radius) + ' 米']], restrictions=[], scope=[], duration=None, interval=None)]
        rule = 'guardian-halberd'
    if int(id) in revenant_family['effects']:
        assert list(effect['roots'].values()) == [revenant_family['root']]
        assert len(revenant_family['families']) == 3
        blocks = [dict(source=revenant_family['root'], phase='发动绝招时', linked=True,
                       values=[['召唤家人', '三名']], restrictions=[], scope=[], duration=None, interval=None)]
        rule = 'revenant-family'
    if int(id) in revenant_enchant['effects']:
        assert list(effect['roots'].values()) == [revenant_enchant['root']]
        buff = source['spells'][str(revenant_enchant['enchant'])]
        frost = source['spells'][str(revenant_enchant['frost'])]
        assert buff['magicAttackPower'] == 60 and buff['effectEndurance'] == 20
        assert frost['freezeAttackPower'] == 40 and frost['effectEndurance'] == 30
        blocks = [dict(source=revenant_enchant['enchant'], phase='召唤家人时', linked=True,
                       values=[['魔力基础攻击力', '+60'], ['冻伤基础累积', '40']], restrictions=['右手武器'], scope=[], duration=20, interval=None),
                  dict(source=revenant_enchant['frost'], phase='冻伤发作时', linked=True,
                       values=[['冻伤伤害', '最大血量的 10% + 50']], restrictions=[], scope=[], duration=None, interval=None),
                  dict(source=revenant_enchant['frost'], phase='冻伤期间', linked=True,
                       values=[['承伤倍率', '+15%']], restrictions=[], scope=[], duration=30, interval=None)]
        notes.extend(['与同类右手附魔互相覆盖，保留后施加的效果。', '冻伤期间再次命中不刷新这次冻伤时长。'])
        rule = 'revenant-enchant'
    if int(id) in wylder_flame['effects']:
        assert list(effect['roots'].values()) == [wylder_flame['root']]
        lifetime = wylder_flame['bullets']['30900102']['life']
        assert lifetime == 10
        blocks = [dict(source=wylder_flame['root'], phase='绝招释放后', linked=True,
                       values=[['火焰持续时间', num(lifetime) + ' 秒']], restrictions=[], scope=[], duration=None, interval=None)]
        rule = 'wylder-flame'
    if int(id) in scholar_ailment['effects']:
        assert list(effect['roots'].values()) == [scholar_ailment['root']]
        row = scholar_ailment['rows'][str(scholar_ailment['leaf'])]
        assert row['effectEndurance'] == 20 and all(row[k] == 130 for k in ('poisonDamageRate', 'diseaseDamageRate', 'bloodDamageRate', 'freezeDamageRate', 'madnessDamageRate'))
        blocks = [dict(source=scholar_ailment['leaf'], phase='绝招效果命中时', linked=True,
                       values=[['异常造成的血量损伤', '+30%']], restrictions=['中毒／腐败／出血／冻伤／发狂'],
                       scope=[], duration=20, interval=None)]
        notes.append('不增加异常累积，也不增加催眠、发狂造成的专注值损失。')
        notes.append('断开连结不提前解除；已发作的中毒、腐败也受影响。')
        rule = 'scholar-ailment'
    if int(id) in flask_sharing['effects']:
        assert list(effect['roots'].values()) == [flask_sharing['root']] and flask_sharing['radius'] == 15
        blocks = [
            dict(source=7010220, phase='使用圣杯瓶时', linked=True,
                 values=[['自身血量恢复', '最大值的 60% → 50%']], restrictions=[], scope=['仅自身'], duration=None, interval=None),
            dict(source=7010221, phase='周围我方人物', linked=True,
                 values=[['血量恢复', '最大值的 30%'], ['治疗范围', '半径 15 米，不含自身']], restrictions=[], scope=['半径 15 米，不含自身'], duration=None, interval=None),
            dict(source=7010241, branches=[7010240,7010230,7010231], phase='搭配缓慢恢复时', linked=True,
                 values=[['自身瞬间恢复', '最大血量的 10%'], ['我方瞬间恢复', '最大血量的 5%'],
                         ['持续恢复', '约每 0.1 秒恢复最大血量的 1%'], ['持续时间', '自身 8 秒／我方 4 秒']],
                 restrictions=[], scope=[], duration=None, interval=None),
            dict(source=7010260, branches=[7010250], phase='喝瓶回蓝效果共存时', linked=True,
                 values=[['自身专注值恢复', '最大值的 30%'], ['我方专注值恢复', '最大值的 15%']],
                 restrictions=[], scope=[], duration=None, interval=None),
        ]
        notes.append('瞬间回血按接受治疗者自身的圣杯瓶恢复量加成或减益调整；持续回血不受这项修正影响。')
        rule = 'flask-sharing'
    if int(id) == 8440200:
        assert list(effect['roots'].values()) == [8440200]
        blocks = [
            dict(source=7010230, phase='使用圣杯瓶时', linked=True,
                 values=[['瞬间血量恢复', '最大值的 60% → 10%']], restrictions=[], scope=['仅自身'], duration=None, interval=None),
            dict(source=7010231, phase='随后持续恢复', linked=True,
                 values=[['血量恢复', '每次最大值的 1%']], restrictions=[], scope=['仅自身'], duration=8, interval=.1),
        ]
        notes.append('瞬间回血受圣杯瓶恢复量加成或减益影响；持续回血不受这项修正影响。')
        rule = 'gradual-flask'
    if id in rally['effects']:
        root = rally['effects'][id]
        assert list(effect['roots'].values()) == [root]
        assert math.isclose(source['spells'][str(root)]['regainRate'], rally['rows'][str(root)]['regainRate'], abs_tol=1e-6)
        values = [['可追回血量', '通常为本次损失的 100%'], ['保留时间', '通常 4 秒'], ['可追回血量消退速度', '每秒最大血量的 100%']]
        bonus = (rally['rows'][str(root)]['regainRate'] - 1) * 100
        if bonus: values.append(['攻击回血量', signed(bonus) + '%'])
        blocks = [dict(source=root, phase='受损后攻击命中', linked=False,
                       values=values, restrictions=[], scope=[], duration=None, interval=None)]
        notes.append('每次恢复量由武器与攻击动作决定，不按造成伤害的比例计算；最多恢复尚未消退的可追回血量。')
        notes.append('部分攻击不留下可追回血量，或没有保留时间；再次受损可能使先前未追回的血量提前消退。')
        rule = 'rally-blessing' if root == 8981200 else 'rally-recovery'
    if int(id) == attack_nullify['effect']:
        assert list(effect['roots'].values()) == [attack_nullify['effect']] and effect['runtimeExclusive'] == -1
        assert attack_nullify['chance'] == 20
        blocks = [dict(source=attack_nullify['effect'], phase='存在减伤降低效果时', linked=False,
                       values=[['攻击失效概率', '20%']], restrictions=[], scope=[], duration=None, interval=None)]
        notes.append('其他减伤抵消负面效果后仍可触发。')
        notes.append('成功触发仍可能累积异常。')
        rule = 'attack-nullify'
    if int(id) == ailment_growth['effect']:
        assert list(effect['roots'].values()) == ailment_growth['roots'] and effect['runtimeExclusive'] == -1
        assert ailment_growth['interval'] == 20 and ailment_growth['maximum'] == 10
        blocks = [dict(source=ailment_growth['seed'], branches=ailment_growth['ladder'][1:],
                       phase='异常累积或发作期间', linked=True,
                       values=[['攻击倍率', ' → '.join(signed((rate - 1) * 100) + '%' for rate in ailment_growth['rates'])]],
                       restrictions=[], scope=[], duration=None, interval=None)]
        notes.append('首次满足条件立即获得第一阶，其后每 20 秒提升一阶，最多 10 阶。')
        notes.append('所有异常累积和发作状态消失后，在当前 20 秒计时结束时清空增益。')
        rule = 'ailment-growth'
    if int(id) == frost_stealth['effect']:
        assert list(effect['roots'].values()) == [frost_stealth['root']] and effect['runtimeExclusive'] == 800
        assert source['spells'][str(frost_stealth['leaf'])]['effectEndurance'] == 5
        blocks = [dict(source=frost_stealth['leaf'], phase='自身或附近敌人冻伤时', linked=True,
                       values=[['隐身时间', '5 秒']], restrictions=[], scope=[], duration=None, interval=None)]
        notes.append('再次触发刷新持续时间；队友冻伤不触发。')
        rule = 'frost-stealth'
    if int(id) == duchess_stealth['effect']:
        assert list(effect['roots'].values()) == [duchess_stealth['root']] and effect['runtimeExclusive'] == -1
        assert source['spells'][str(duchess_stealth['leaf'])]['effectEndurance'] == 10
        blocks = [dict(source=duchess_stealth['leaf'], phase='背刺后', linked=True,
                       values=[['隐匿时间', '10 秒']], restrictions=[], scope=[], duration=None, interval=None)]
        notes.append('再次背刺刷新持续时间。')
        rule = 'duchess-stealth'
    if id in passive_resource['effects']:
        root = passive_resource['effects'][id]
        assert list(effect['roots'].values()) == [root] and effect['runtimeExclusive'] == -1
        row = passive_resource['rows'][str(root)]
        rule = ('resource-capacity' if any(row[k] != 1 for k in ('maxHpRate', 'maxMpRate', 'maxStaminaRate'))
                else 'passive-poise' if row['toughnessDamageCutRate'] != 1 else 'flask-recovery')
    if treasure_map['root'] in effect['roots'].values():
        blocks = [dict(source=treasure_map['root'], phase='隐藏宝藏标记', linked=False,
                       values=[['显示范围', '自己的地图']],
                       restrictions=[], scope=[], duration=None, interval=None)]
        notes.append('只标记已出现的宝藏，不增加宝藏数量。')
        rule = 'treasure-map'
    if undertaker_reset['root'] in effect['roots'].values():
        blocks = [dict(source=undertaker_reset['root'], phase='绝招收尾动作开始时', linked=False,
                       values=[['技艺使用次数', '恢复至上限']],
                       restrictions=[], scope=[], duration=None, interval=None)]
        notes.append('次数已满时不会额外储存。')
        rule = 'undertaker-reset'
    if undertaker_contact['root'] in effect['roots'].values():
        leaf = undertaker_contact['leaf']
        assert source['spells'][str(leaf)]['changeHpRate'] == -30
        assert source['spells'][str(leaf)]['changeHpPoint'] == -100
        blocks = [dict(source=leaf, phase='绝招接触友方时', linked=True,
                       values=[['HP 恢复', '目标最大值的 30% + 100']],
                       restrictions=['仅友方角色，不含自身'], scope=[], duration=None, interval=None)]
        rule = 'undertaker-contact'
    if guardian_ultimate['root'] in effect['roots'].values():
        assert source['spells']['7011401']['neutralDamageCutRate'] == .1
        assert source['spells']['7011402']['neutralDamageCutRate'] == .8
        assert all(a['radius'] == 15 for a in guardian_ultimate['assets'])
        blocks = [dict(source=7011402, phase='绝招落地／维持时', linked=True,
                       values=[['承伤倍率', '-20%']], restrictions=['自身及周围友方 · 半径 15 米'],
                       scope=[], duration=30, interval=None),
                  dict(source=7011401, phase='单次保护（受损后消耗）', linked=True,
                       values=[['承伤倍率', '-90%'], ['保护最长保留', '60 秒']],
                       restrictions=['自身及周围友方 · 半径 15 米'], scope=[], duration=None, interval=None)]
        notes.extend(['两层同时存在时合计减伤 92%。', '维持绝招时约每 0.3 秒重新施加，受损消耗的保护可再次获得。'])
        rule = 'guardian-ultimate'
    if raider_growth['root'] in effect['roots'].values():
        ladder = raider_growth['ladder']
        assert len(ladder) == 10 and source['spells'][str(ladder[0])]['physicsAttackRate'] == 1.03
        assert source['spells'][str(ladder[-1])]['physicsAttackRate'] == 1.343916
        blocks = [dict(source=ladder[0], branches=ladder[1:], phase='强化反击的最后一击时', linked=True,
                       values=[['攻击倍率', '每次 ×1.03，最多约 +34.39%'], ['成长上限', '10 次']],
                       scope=[], restrictions=[], duration=None, interval=None)]
        rule = 'raider-growth'
    if raider_skill['root'] in effect['roots'].values():
        assert source['spells']['7031601']['physicsAttackRate'] == 1.5
        assert source['spells']['7031602']['physicsAttackRate'] == 2
        assert all(source['spells'][str(sp)]['neutralDamageCutRate'] == 1.3 for sp in raider_skill['leaves'])
        blocks = [dict(source=7031601, phase='普通技艺动作期间', linked=True,
                       values=[['物理攻击倍率', '+50%'], ['承伤倍率', '+30%']],
                       scope=[], restrictions=[], duration=None, interval=None),
                  dict(source=7031602, phase='强化反击动作期间', linked=True,
                       values=[['物理攻击倍率', '+100%'], ['承伤倍率', '+30%']],
                       scope=[], restrictions=[], duration=None, interval=None)]
        rule = 'raider-skill'
    if duchess_poise['root'] in effect['roots'].values():
        poise_row = source['spells']['7033101']
        assert poise_row['saReceiveDamageRate'] == 1.3 and poise_row['effectEndurance'] == 6
        assert duchess_poise['bullet']['hitRadius'] == duchess_poise['bullet']['hitRadiusMax'] == 15
        blocks = [dict(source=7033101, phase='发动技艺时', linked=True,
                       values=[['目标承受的削韧', '+30%'], ['范围半径', '15 米']],
                       scope=[], restrictions=[], duration=6, interval=None)]
        rule = 'duchess-poise'
    if wylder_bleed['root'] in effect['roots'].values():
        bleed_row = source['spells']['7500002']
        assert bleed_row['bloodAttackPower'] == 55 and bleed_row['effectEndurance'] == 1
        assert bleed_row['changeHpRate'] == 12.5 and bleed_row['changeHpPoint'] == 100
        blocks = [dict(source=7500002, phase='技艺拉拽攻击命中时', linked=True,
                       values=[['出血基础累积', '55']], scope=[], restrictions=[], duration=None, interval=None),
                  dict(source=7500002, phase='出血发作时', linked=True,
                       values=[['出血伤害', '最大血量的 12.5% + 100']], scope=[], restrictions=[], duration=None, interval=None)]
        notes.append('该出血发作后约 1 秒内不重复触发。')
        rule = 'wylder-bleed'
    if ironeye_poison['root'] in effect['roots'].values():
        poison_row = source['spells']['7500201']
        assert poison_row['poizonAttackPower'] == 70 and poison_row['effectEndurance'] == 40
        assert poison_row['changeHpRate'] == .1 and poison_row['changeHpPoint'] == 10
        assert source['spells']['7500202']['changeHpRate'] == .25 and source['spells']['7500202']['changeHpPoint'] == 250
        blocks = [dict(source=7500201, phase='技艺命中时', linked=True,
                       values=[['中毒基础累积', '70']], scope=[], restrictions=[], duration=None, interval=None),
                  dict(source=7500201, phase='中毒发作后', linked=True,
                       values=[['中毒伤害', '最大血量的 0.1% + 10']], scope=[], restrictions=[], duration=40, interval=1.3),
                  dict(source=7500202, phase='技艺命中已中毒目标时', linked=True,
                       values=[['追加伤害', '最大血量的 0.25% + 250']], scope=[], restrictions=[], duration=None, interval=None)]
        notes.extend(['中毒期间再次命中不刷新这次中毒时长。', '追加伤害约每 0.1 秒最多触发一次。'])
        rule = 'ironeye-poison'
    if raider_debuff['root'] in effect['roots'].values():
        leaf = source['spells'][str(raider_debuff['leaf'])]
        assert leaf['effectEndurance'] == 13
        assert all(leaf[k] == .87 for k in ('physicsAttackRate', 'magicAttackRate', 'fireAttackRate', 'thunderAttackRate', 'darkAttackRate'))
        assert all(leaf[k] == 0 for k in ('magParamChange', 'miracleParamChange', 'shamanParamChange'))
        blocks = [dict(source=7500401, phase='技艺命中后', linked=True,
                       values=[['目标攻击倍率', '-13%']], scope=[], restrictions=[], duration=13, interval=None)]
        notes.append('不影响按魔法、祷告或特殊法术处理的攻击。')
        rule = 'raider-debuff'
    if absorption['root'] in effect['roots'].values():
        assert all(source['spells'][str(leaf)]['effectEndurance'] == 30 for leaf in absorption['leaves'])
        for leaf, field in zip(absorption['leaves'], ('magicDamageCutRate', 'fireDamageCutRate', 'thunderDamageCutRate', 'darkDamageCutRate')):
            assert source['spells'][str(leaf)][field] == .8
        blocks = [dict(source=7500601, branches=[7500602, 7500603, 7500604], phase='收集属性痕后', linked=True,
                       values=[['对应属性减伤', '20%']], scope=[], restrictions=[], duration=30, interval=None)]
        rule = 'recluse-absorption'
    if restage['root'] in effect['roots'].values():
        assert source['spells']['703540']['restageAttackRate'] == -1
        assert source['spells']['7290001']['restageAttackRate'] == .6
        blocks = [dict(source=7290001, branches=[703540], phase='发动技艺时', linked=True,
                       values=[['重演伤害比例', '50% → 60%']],
                       scope=[], restrictions=[], duration=None, interval=None)]
        notes.append('不提高重演的削韧。')
        rule = 'duchess-restage'
    if ironeye_mark['root'] in effect['roots'].values():
        assert source['spells']['7280000']['weakPointValue'] == ironeye_mark['extendedDuration']
        blocks = [dict(source=7280000, phase='弱点显露时', linked=False,
                       values=[['弱点最长持续时间', '17 → 22 秒']],
                       scope=[], restrictions=[], duration=None, interval=None)]
        notes.append('弱点被击破会提前消失；再次施加取原剩余时间与新时长中较长者，不累加，也不补回弱点耐久。')
        rule = 'ironeye-mark'
    if recluse_mark['root'] in effect['roots'].values():
        assert source['spells']['706100']['effectEndurance'] == 12.5
        assert source['spells']['706101']['effectEndurance'] == 20
        blocks = [dict(source=706101, branches=[706100], phase='发动绝招后', linked=True,
                       values=[['鲜血烙印持续时间', '12.5 → 20 秒']],
                       scope=[], restrictions=[], duration=None, interval=None)]
        notes.append('再次施加同版烙印会刷新时间；普通版与延长版不会叠加恢复量。')
        rule = 'recluse-mark'
    if roots and all(r.get('stateInfo') == 2102 for r in roots):
        family = list(effect['roots'].values())
        assert family in starting_goods['families']
        for root, row in zip(family, roots):
            assert all(row[k] == v for k, v in starting_goods['rows'][str(root)].items())
        item = roots[0]['startGoodsId']
        if item == 10055:
            assert family == [7121000] and roots[0]['startingItemAmount'] == 1
            blocks = [dict(source=family[0], phase='出击时', linked=False,
                           values=[['道具栏位', '+1']], scope=[], restrictions=[], duration=None, interval=None)]
            rule = 'starting-pouch'
        else:
            ordinary = sum(r['startingItemAmount'] for r in roots
                           if 2226 not in [r['invocationConditionsStateChange' + str(i)] for i in (1, 2, 3)])
            scholar = sum(r['startingItemAmount'] for r in roots)
            amount = '×' + num(ordinary)
            if scholar != ordinary:
                amount += '（学者 ×' + num(scholar) + '）'
            label = source['labels']['GoodsName'][str(item)]
            blocks = [dict(source=family[0], branches=family[1:], phase='出击时', linked=False,
                           values=[[label, amount]], scope=[], restrictions=[], duration=None, interval=None)]
            rule = 'starting-goods'
    initial_root = next((r for r in effect['roots'].values() if r in starting_weapon['roots']), None)
    if initial_root is not None:
        leaves = [initial_root + n for n in range(1, 5)]
        rows = [starting_weapon['rows'][str(n)] for n in leaves]
        if initial_root < 7120400:
            field, label = {7120000: ('magicAttackPower', '魔力攻击力'), 7120100: ('fireAttackPower', '火攻击力'),
                            7120200: ('thunderAttackPower', '雷攻击力'), 7120300: ('darkAttackPower', '圣攻击力')}[initial_root]
            assert [r['physicsAttackPower'] for r in rows] == [-30, -40, -50, -60]
            assert [r[field] for r in rows] == [33, 44, 55, 66]
            blocks = [dict(source=leaves[0], branches=leaves[1:], phase='出击武器（强化 +0／+1／+2／+3）', linked=True,
                           values=[['物理攻击力', '-30／-40／-50／-60'], [label, '+33／+44／+55／+66']],
                           restrictions=[], scope=[], duration=None, interval=None)]
        else:
            field, label, amount = {7120400: ('freezeAttackPower', '基础冻伤累积', 35),
                                    7120500: ('poizonAttackPower', '基础中毒累积', 35),
                                    7120600: ('bloodAttackPower', '基础出血累积', 25)}[initial_root]
            assert all(abs(r[k] - .85) < 1e-6 for r in rows for k in (
                'physicsAttackPowerRate', 'magicAttackPowerRate', 'fireAttackPowerRate', 'thunderAttackPowerRate', 'darkAttackPowerRate'))
            status_leaves = [initial_root + n for n in range(5, 9)]
            assert all(starting_weapon['rows'][str(n)][field] == amount for n in status_leaves)
            blocks = [dict(source=leaves[0], branches=leaves[1:], phase='对应出击武器', linked=True,
                           values=[['攻击力', '-15%']], restrictions=[], scope=[], duration=None, interval=None),
                      dict(source=status_leaves[0], branches=status_leaves[1:], phase='命中时', linked=True,
                           values=[[label, str(amount)]], restrictions=[], scope=[], duration=None, interval=None)]
        rule = 'starting-weapon'
    if 7011000 in effect['roots'].values():
        assert source['spells']['7011000']['cycleOccurrenceSpEffectId'] == duration['leaf'] == 7011001
        assert {row['bullet']: row['seconds'] for row in duration['checks']['lifetime']} == {
            30901001: 1, 30901006: 1, 30901111: 7, 30901116: 4}
        blocks = [dict(source=7011001, phase='旋风持续时间', linked=True,
                       values=[['正常释放', '1 → 7 秒'], ['提前松开按键', '1 → 4 秒']],
                       restrictions=[], scope=[], duration=None, interval=None)]
        rule = 'guardian-duration'
    if 7500300 in effect['roots'].values():
        assert source['spells']['7500301']['effectEndurance'] == evasion['duration'] == 0.4
        assert source['spells']['7500301']['stateInfo'] == evasion['state'] == 2394
        blocks = [dict(source=7500301, phase='发动技艺时', linked=True,
                       values=[['无敌时间', '0.4 秒']],
                       restrictions=[], scope=[], duration=None, interval=None)]
        rule = 'duchess-evasion'
    if 7220300 in effect['roots'].values():
        assert source['spells']['7220305']['physicsAttackRate'] == 1.15
        assert source['spells']['7220305']['effectEndurance'] == 20
        assert source['spells']['7220306']['changeMpRate'] == -10
        assert source['spells']['7220302']['effectEndurance'] == 15
        assert source['spells']['7220302']['motionInterval'] == 2
        blocks = [dict(source=7220305, branches=[7220301, 7220302, 7220303, 7220304],
                       phase='触发后', linked=True, values=[['攻击倍率', '+15%']],
                       restrictions=[], scope=[], duration=20, interval=None),
                  dict(source=7220306, phase='触发时', linked=True, values=[['FP 恢复', '最大值的 10%']],
                       restrictions=[], scope=[], duration=None, interval=None)]
        notes.extend(['绝招的触发窗口持续 15 秒，每 2 秒重新准备一次受损触发；未消耗的机会在窗口结束时结算。',
                      '多次触发的攻击倍率相乘、分别计时；两次合计 +32.25%。'])
        rule = 'role-repeat'
    if 7032700 in effect['roots'].values():
        assert [source['spells'][str(i)]['physicsAttackRate'] for i in (7032704, 7032706)] == [1.15, 1.05]
        assert source['spells']['7032702']['effectEndurance'] == 12.5
        assert all(source['spells'][str(i)]['effectEndurance'] == 30 for i in (7032704, 7032706))
        blocks = [dict(source=7032704, branches=[7032701, 7032702, 7032703, 7032705, 7032706],
                       phase='绝招期间打倒敌人后', linked=True, values=[['攻击倍率', '+5% 或 +15%']],
                       restrictions=['增幅随敌人类型变化'], scope=[], duration=30, interval=None)]
        notes.extend(['击杀触发窗口持续 12.5 秒。', '每次击杀获得独立增益，倍率相乘、分别计时。'])
        rule = 'role-repeat'
    if id == '7032800':
        edge = links['emitters']['7032802']
        assert len(evidence['zoneMatching']) == 4
        assert source['spells']['7032801']['effectEndurance'] == edge['fieldDuration'] == 30
        assert source['spells']['7032803']['effectEndurance'] == 1.5
        b = next(b for b in blocks if b['source'] == 7032803)
        b['values'].append(['魔法阵持续时间', num(edge['fieldDuration']) + ' 秒'])
        b.update(phase='魔法阵内', duration=None, interval=None, scope=[],
                 restrictions=['自身及周围友方 · 半径 ' + num(edge['radius']) + ' 米'])
        blocks = [b]
        notes.extend(['每 30 秒最多生成一次；持续收集属性痕不会刷新冷却。',
                      '离开后基础残留时间不超过 1.5 秒，受效果持续时间修正。'])
        rule = 'magic-zone'
    if id == '7036200':
        default = evidence['systemValues']['PlayerCommonParam/0/fh_unknown_43b']
        rates = {r['override'] for r in evidence['scholarDecay'] if r['ids']}
        assert rates == {30} and default == 80
        blocks = [dict(source=7036200, phase='技艺进行率回落时', linked=False,
                       values=[['进行率下降速度', signed((rates.pop() / default - 1) * 100) + '%']],
                       restrictions=[], scope=[], duration=None, interval=None)]
        rule = 'scholar-decay'
    if 7036300 in effect['roots'].values():
        assert evidence['effectLinks']['7036300'] == [7036301]
        assert any(r.get('emitted') == [7036301] for r in evidence['scholarAlly'])
        for b in blocks:
            if b['source'] == 7036301:
                b['scope'] = []
        rule = 'scholar-ally'
    if id == '7150000':
        assert len(evidence['guardCounter']) == 32
        blocks = [dict(source=7150000, phase='防御反击命中时', linked=False,
                       values=[['追加物理伤害基值', '当前 HP 的 5%']],
                       restrictions=['需本次防御反击含物理伤害'], scope=[], duration=None, interval=None)]
        rule = 'guard-counter-hp'
    grown = [growth['roots'][str(root)] for root in effect['roots'].values() if str(root) in growth['roots']]
    if grown and grown[0].get('family') == 'special-locations':
        record = grown[0]
        assert [ladder['stages'][0] for ladder in record['ladders']] == [7069001, 7069021]
        blocks = []
        for ladder, phase, restrictions in zip(record['ladders'],
                ['封印监牢／入侵者／魔法师塔', '据点目标／拟态敌人'],
                [['封印监牢最多 3 档；入侵者最多 2 档；解锁魔法师塔触发 1 档'],
                 ['据点目标通常 1 档，部分目标 2 档，最多计 8 档；拟态敌人最多计 2 档（需击败变身后的目标）', '两类来源共用成长，最多 10 档']]):
            first = ladder['stages'][0]
            rate = source['spells'][str(first)]['physicsAttackRate']
            assert all(abs(source['spells'][str(sp)]['physicsAttackRate'] - rate ** stage) < .001
                       for stage,sp in enumerate(ladder['stages'], 1))
            blocks.append(dict(source=first, branches=ladder['stages'][1:], phase=phase, linked=True,
                               values=[['每档攻击倍率', '约 ' + signed((rate - 1) * 100) + '%']],
                               restrictions=restrictions, scope=[], duration=None, interval=None))
        notes.append('两组成长可同时生效，倍率相乘。')
        rule = 'growth'
    elif grown:
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
        assert roots[0]['ultimateArtGaugeRate'] == roots[0]['ultimateArtGaugeChargeRate'] == 0.85
    if id in {str(i) for i in range(6820000, 6820700, 100)}:
        measured = next(r for r in evidence['damageStatus'] if r['root'] == int(id) and 'amount' in r)
        root, bridge, child = (measured[k] for k in ('root', 'bridge', 'child'))
        assert effect['roots'] == {'passiveSpEffectId_1': root}
        assert source['spells'][str(root)]['deleteCriteriaDamage'] == 12
        assert source['spells'][str(root)]['replaceSpEffectId'] == bridge
        assert source['spells'][str(bridge)]['replaceSpEffectId'] == root
        assert source['spells'][str(bridge)]['cycleOccurrenceSpEffectId'] == child
        assert source['spells'][str(child)][measured['field']] == measured['amount']
        family = next(f for f in damage_ailment['families'] if f['root'] == root)
        assert (family['bridge'], family['leaf'], family['field'], family['amount']) == (bridge, child, measured['field'], measured['amount'])
        blocks = [dict(source=root, branches=[bridge, child], phase='受到损伤时', linked=False,
                       values=[[STATUS_BUILDUP[measured['field']] + '累积', '+' + num(measured['amount']) + ' 点／次']],
                       scope=[], restrictions=[], duration=None, interval=None)]
        notes.append('积累量不随损伤数值变化。')
        notes.append('触发后有短暂间隔，期间受损不会重复累积。')
        rule = 'damage-ailment'
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
    questions = []
    if any(r['root'] == int(id) for r in evidence['damageStatus']):
        refs.append('damage-status')
    if any(str(root) in triggers['roots'] for root in effect['roots'].values()):
        refs.append('action-triggers')
    if any(str(root) in scripts['effects'] for root in effect['roots'].values()):
        refs.append('action-script')
        if id == '7035700':
            questions.append('与其他附魔的覆盖顺序、武器适用条件及完整动作时序')
    if any(b['source'] in edge['leaves'] for b in detail['blocks'] for edge in links['emitters'].values()):
        refs.append('bullet-links')
        questions.append('范围命中、多人来源叠加及再次发放时序')
    if missing_roots:
        questions.append('目录引用的 SpEffect 行在当前参数中不存在：' + ', '.join(map(str, missing_roots)))
    if rules[id] == 'unknown':
        questions.append('跨遗物同版／异版的覆盖、叠加与上限')
    if 2123 in states:
        refs.append('hero')
    if any(str(b['source']) in evidence['recoveryTiming'] for b in detail['blocks']):
        refs.append('recovery-timing')
    if 2102 in states:
        questions.append('完整出征／重载调度、一般拾取自动装备、道具栏位溢出后的显示／保留和网络投递')
    if 2105 in states or 2128 in states:
        questions.append('原生效果列表顺序与预设／装备加载顺序的对应、完整出击／重载队列、角色可获得武器与实际施法资格、DLL 运行时改写及多人同步' if rules[id] == 'starting-replacement' else '多个出击替换词条的优先顺序、角色限制')
    if rules[id] == 'kill':
        questions.append('敌人分类标记的具体对象、共享奖励及重载路径')
    elif rules[id] not in ('role-repeat', 'guardian-recovery', 'guardian-skill', 'guardian-protection', 'executor-blade', 'undertaker-prayer', 'executor-recovery', 'executor-tenacity', 'duchess-evasion', 'guardian-duration', 'recluse-mark', 'ironeye-mark', 'duchess-restage', 'recluse-absorption', 'raider-debuff', 'ironeye-poison', 'wylder-bleed', 'duchess-poise', 'duchess-ultimate', 'guardian-shockwave', 'successive-recovery', 'successive-attack', 'scholar-tether', 'scholar-ailment', 'wylder-flame', 'revenant-enchant', 'revenant-family', 'guardian-halberd', 'wylder-followup', 'duchess-dagger', 'item-sharing', 'guard-aggro', 'ironeye-ultimate', 'revenant-ghostflame', 'scholar-feint', 'duchess-stealth', 'frost-stealth', 'ailment-growth', 'attack-nullify', 'rally-recovery', 'rally-blessing', 'flask-sharing', 'gradual-flask', 'raider-skill', 'raider-growth', 'guardian-ultimate', 'undertaker-contact', 'undertaker-reset', 'starting-weapon', 'weapon-recovery', 'recluse-bleed', 'revenant-sacrifice', 'gesture-madness') and any(s not in (0, 71, 2100, 2102, 2105, 2122, 2123, 2128) for s in states):
        questions.append('stateInfo 分派、触发资格、次数、目标及隐藏效果链')
    if rules[id] not in ('role-repeat', 'guardian-recovery', 'guardian-skill', 'guardian-protection', 'executor-blade', 'undertaker-prayer', 'executor-recovery', 'executor-tenacity', 'duchess-evasion', 'guardian-duration', 'recluse-mark', 'ironeye-mark', 'duchess-restage', 'recluse-absorption', 'raider-debuff', 'ironeye-poison', 'wylder-bleed', 'duchess-poise', 'duchess-ultimate', 'guardian-shockwave', 'successive-recovery', 'successive-attack', 'scholar-tether', 'scholar-ailment', 'wylder-flame', 'revenant-enchant', 'revenant-family', 'guardian-halberd', 'wylder-followup', 'duchess-dagger', 'item-sharing', 'guard-aggro', 'ironeye-ultimate', 'revenant-ghostflame', 'scholar-feint', 'duchess-stealth', 'frost-stealth', 'ailment-growth', 'attack-nullify', 'rally-recovery', 'rally-blessing', 'flask-sharing', 'gradual-flask', 'raider-skill', 'raider-growth', 'guardian-ultimate', 'undertaker-contact', 'undertaker-reset', 'starting-weapon', 'weapon-recovery', 'recluse-bleed', 'revenant-sacrifice', 'gesture-madness') and any(b['linked'] for b in detail['blocks']):
        questions.append('关联分支的实际触发顺序、重复通知与刷新行为')
    if rules[id] == 'growth':
        questions.append('计数源的完整地点名单、跨日／重载恢复与同类来源相遇')
    if set(effect['roots'].values()) & {7020100, 7020200, 7036800}:
        refs.extend(['action-start', 'action-values'])
    if rules[id] == 'role-max-hp':
        questions.append('增益施加、阶段切换和移除时的当前／最大 HP 同步')
    if rules[id] == 'role-repeat':
        questions.append('完整角色／网络发放队列时序、极端实例容量与倒地／重载状态')
        if 7032700 in effect['roots'].values():
            questions.append('击杀分支的具体敌人名单与共享奖励来源；重叠绝招窗口')
    if rules[id] in ('guardian-recovery', 'guardian-skill', 'guardian-protection'):
        questions.append('实际碰撞命中、范围重新进入、完整角色队列／施法结束时序与多人网络投递')
    if rules[id] == 'executor-recovery':
        questions.append('各格挡动作的实际进入条件、完整角色队列及中断／倒地／重载交互')
    if rules[id] == 'executor-tenacity':
        questions.append('异常自然结束以外的解除入口、死亡／重载与完整角色投递时序，以及连续触发的实例容量上限')
    if rules[id] == 'undertaker-reset':
        questions.append('完整行为图的收尾进入／中断条件、强化状态与联机同步；最大次数变化及倒地／重载交互')
    if rules[id] == 'treasure-map':
        questions.append('另一组 8720～8731 显示标志的赋值路径、地图模式与显示覆盖；缺失的原版合并地图资产、完整事件调度、标志清除与多人／重载交互')
    if rules[id] == 'resource-capacity':
        questions.append('最终角色资源上限／取整、装备或移除时的当前资源同步、倒地／重载交互')
    if rules[id] == 'passive-poise':
        questions.append('完整受击上下文、角色基础强韧与恢复／失衡阈值、动作与多人交互')
    if rules[id] == 'flask-recovery':
        questions.append('完整喝瓶动作、最终当前 HP 上限与治疗修正、共享治疗及多人交互')
    if rules[id] == 'damage-ailment':
        questions.append('达到发作阈值后的同帧多份累积、已发作／免疫状态与自然退条、抵抗成长、完整受损入口和排除位来源、死亡／重载及多人交互')
    if rules[id] in ('periodic-hp-recovery', 'periodic-hp-loss'):
        questions.append('最终当前 HP 写入与治疗修正、满血／濒死时恢复和消耗的顺序、受损触发及死亡／重载／多人交互')
    if rules[id] == 'perfume':
        questions.append('完整调香瓶动作／弹体继承、战技和异常发作的独立路径、停用／重载及多人交互；攻击参数存在不代表当前局均可使用')
    if rules[id] == 'duchess-ultimate':
        questions.append('各攻击命中标记的实际投递与权重、绝招自身碰撞是否贡献累积、完整动作中断／重叠绝招、实时帧调度、死亡／重载及多人交互')
    if rules[id] == 'guardian-shockwave':
        questions.append('冲击波物理伤害的来源缩放与最终计算、真实半径插值／碰撞／同一目标去重、完整防御反应和动作中断、原生 2114 分支的额外行为、最终 HP 写入及多人／重载交互')
    if rules[id] == 'hero-adjustment':
        questions.append('默认成长曲线以外的角色覆盖、实时属性刷新与最终 HP／FP 等派生资源同步、重载及多人交互')
    if rules[id] == 'successive-recovery':
        questions.append('各攻击命中标记的实际投递与权重、最终当前 HP／FP 写入与恢复修正、满资源时处理、死亡／重载及多人交互')
    if rules[id] == 'successive-attack':
        questions.append('各攻击命中标记的实际投递与权重、完整攻击上下文和动作中断、实时调度／最终伤害、死亡／重载及多人交互')
    if rules[id] == 'scholar-tether':
        questions.append('完整碰撞和每次施放的目标去重、连结准入／距离判定、其他解除入口及多施法者网络交互、最终 HP 写入与死亡／重载清理')
    if rules[id] == 'ironeye-ultimate':
        questions.append('子弹体攻击上下文与异常继承、同目标命中去重、完整蓄力动作中断／实时调度、异常修正与抵抗成长、其他中毒覆盖、最终 HP 写入及多人／重载交互')
    if rules[id] == 'revenant-ghostflame':
        questions.append('爆炸魔力伤害的来源缩放与最终计算、完整弹体到命中数据构造／碰撞去重、实际半径插值、其他冻伤覆盖及火焰解除、自然退条与抵抗成长、最终 HP 写入及多人／重载交互')
    if rules[id] == 'scholar-feint':
        questions.append('右手／双持分支中 nil hand 的原生接口处理、完整动作选择与时间缩放、实际弹反碰撞和成功取消／失败伤害、精力扣除及多人同步')
    if rules[id] == 'scholar-ailment':
        questions.append('完整目标选取与碰撞范围、其他异常版本及伤害分流、最终 HP／FP 写入、不同施术者和多人／死亡／重载时序')
    if rules[id] == 'wylder-flame':
        questions.append('完整状态过渡与子弹体生成／落地条件、火焰实际分布和数量、伤害来源缩放、重叠命中与重复绝招、完整动作调度及多人／死亡／重载时序')
    if rules[id] == 'revenant-enchant':
        questions.append('完整召唤准入与动作中断、武器／箭矢攻击数据绑定和附魔资格、箭行为偏移 23、不同附魔类别交互、其他冻伤及火焰解除、最终资源写入与多人／死亡／重载时序')
    if rules[id] == 'revenant-family':
        questions.append('家人控制器状态 0／11 的完整生命周期与更新、已在场／死亡／召回时的实际行为、落点碰撞和资源生成、绝招动作中断及多人／重载时序')
    if rules[id] == 'guardian-halberd':
        questions.append('戟动作选择与蓄力分支、中断和时间缩放、弹体着地与完整状态过渡、武器攻击来源及动作修正、命中去重与最终 HP 伤害、多人／死亡／重载时序')
    if rules[id] == 'equipped-exclusive':
        questions.append('完整装备更新与其他角色效果汇入、属性到资源上限的曲线和限幅、特殊遗物 2070、攻击实例构造及最终伤害、卸下／重载／联机时序')
    if rules[id] == 'guard-aggro':
        questions.append('完整防御动作调度、松开防御与受击中断的刷新时序、其他选敌因素与最终目标选择、多人／死亡／重载时序')
    if rules[id] == 'item-sharing':
        questions.append('完整消耗动作与范围碰撞／队伍关系、学者熟练度增长、正在发作的异常清理、不同食物类别的覆盖与持续时间修正、最终恢复上限、多来源同帧使用与多人／死亡／重载时序')
    if rules[id] == 'duchess-dagger':
        questions.append('完整武器／动作选择、攻击载荷构造与碰撞、多目标命中的同帧触发及重演队列去重、历史记录时间筛选、最终伤害／削韧修正与多人／死亡／重载时序')
    if rules[id] == 'wylder-followup':
        questions.append('完整钩索动作调度与输入窗口／中断、实际武器攻击数据绑定与附魔资格、攻击修正及最终伤害／耗精力、实际换武器和其他类别附魔、多人／死亡／重载时序')
    if rules[id] in ('flask-sharing', 'gradual-flask'):
        questions.append('完整消耗道具与动作中断、实际范围碰撞和不同施术者投递、最终 HP／FP 上限与其他治疗修正、死亡／重载及联机时序')
    if rules[id] in ('rally-recovery', 'rally-blessing'):
        questions.append('攻击动作与武器组合的完整可达性、零保留／零回收参数的实际来源、死亡／重载与多人投递；外层攻击构造和命中调度')
    if rules[id] == 'attack-nullify':
        questions.append('完整命中入口的特殊攻击／排除标志、各种异常和命中附加效果、受击反应／资源消费、最终 HP 写入、死亡／重载与多人同步')
    if rules[id] == 'ailment-growth':
        questions.append('实际异常的自然消退和持续状态切换、根效果移除及重新装备、死亡／重载清理、其他增攻来源交互及多人同步')
    if rules[id] == 'frost-stealth':
        questions.append('不同冻伤来源及通知缺失行的实际可用性、真实弹体碰撞与范围边界、状态 600 的最终 AI／渲染消费、攻击／受击和死亡／重载清理、多人同步')
    if rules[id] == 'duchess-stealth':
        questions.append('完整致命一击选择与敌人变体、攻击动作及完整受击路径是否额外移除、隐匿外观和视觉／听觉修正在最终 AI 判定中的单位及适用范围、待机／死亡／重载和多人同步')
    if rules[id] == 'spell-family':
        questions.append('完整施法／弹体的类别继承与特殊替换路径、最终伤害／增益效果及多人交互；Magic 行存在不代表均可在当前局获取')
    if rules[id] == 'undertaker-contact':
        questions.append('完整绝招碰撞与同一目标命中去重、状态 624 在玩家与召唤物中的赋予范围、最终治疗修正／溢出及多人交互')
    if rules[id] == 'guardian-ultimate':
        questions.append('完整绝招动作／发射位置／碰撞及范围重入、同帧多次损伤的处理顺序、其他类别 201 保护的覆盖关系、最终损伤及多人／重载交互')
    if rules[id] == 'raider-growth':
        questions.append('自身判定球的完整生成／碰撞与命中去重、动作中断及事件重复调度、保存类别 9 的死亡／重载持久性、多人交互')
    if rules[id] == 'raider-skill':
        questions.append('完整动作选择／混合／中断时序；两种叶效果可并存相乘，但实际动作窗口能否交叠待确认；最终伤害与多人／重载交互')
    if rules[id] == 'duchess-poise':
        questions.append('完整发射位置／碰撞到达与动作中断、敌人基础强韧及恢复资产、实际失衡反应与多人／死亡／重载交互')
    if rules[id] == 'wylder-bleed':
        questions.append('发射阶段引用缺失的 Behavior 600000030，60 点叶效果 7500001 暂无实际引用；需核对额外运行时路径')
        questions.append('完整攻击／异常修正输入、碰撞与目标限制、自然退条与抵抗成长、最终 HP 修正及多人／死亡／重载交互')
    if rules[id] == 'ironeye-poison':
        questions.append('完整攻击构造／异常修正输入、命中发作当帧的效果队列顺序、自然退条与抵抗成长、最终 HP 修正及多人／死亡／重载交互')
    if rules[id] == 'raider-debuff':
        questions.append('完整攻击实例构造、碰撞／命中资格与最终伤害修正、特殊敌人的攻击分类及多人／死亡／重载交互')
    if rules[id] == 'recluse-absorption':
        questions.append('属性痕空间选择、完整收集动作中断、最终伤害修正与多人／死亡／重载交互')
    if rules[id] == 'duchess-restage':
        questions.append('完整历史记录／时间筛选、动作中断与实际碰撞、最终资源／削韧修正、关联目标及多人／重载交互')
    if rules[id] == 'ironeye-mark':
        questions.append('完整命中／伤害输入、骨骼部位映射、弱点击破伤害与多人投递／死亡／重载交互')
    if rules[id] == 'recluse-mark':
        questions.append('完整施法准入／中断、命中上下文与损伤输入构造、最终恢复修正／上限、多人投递与重载交互')
    if rules[id] == 'starting-weapon':
        questions.append('完整出征／重载发放队列、武器强化菜单与特殊武器别名、命中修正及异常发作／伤害结算、多人交互')
    if rules[id] == 'guardian-duration':
        questions.append('完整行为图的调度／中断、实际半径与逐段伤害／浮空差异、共享命中记录与攻击实例生命周期组合、多人／重载交互')
    if rules[id] == 'duchess-evasion':
        questions.append('完整行为图的动画调度／中断时序、特殊攻击与异常伤害入口、网络投递与重载交互')
    if rules[id] == 'executor-blade':
        questions.append('各动作判定与伤害通知的完整入口、投射物命中时状态、绝招转换／网络／重载交互')
    if rules[id] == 'undertaker-prayer':
        questions.append('远方之恢复虽有 refId10，但实际施法动画缺少槽 10 事件；运行时扩展或替代路径待查')
        questions.append('完整施法准入／中断、武器附魔资格、队列／网络／重载交互')
    if rules[id] == 'recluse-bleed':
        questions.append('出血伤害修正与保护状态组合、完整角色投递／倒地／网络／重载交互')
    if rules[id] == 'revenant-sacrifice':
        questions.append('完整命中／救援队列、低血量与绝招保护状态的结算顺序、多人来源及重载交互')
    if rules[id] == 'gesture-madness':
        questions.append('自然退条／抗性成长与来源修正、发狂反应自动中断动作、完整角色队列／网络／重载交互')
    if id in weapon_recovery_families:
        if rules[id] != 'weapon-recovery':
            refs.append('weapon-recovery')
            questions.append('未加载 DLL 的原生 EA1D40 不接受该武器类型编号；须核对 Mod 的运行时扩展或替代触发路径')
        questions.append('实际攻击／弹体的命中上下文、完整伤害入口、多人命中与投递时序')
    if 7020200 in effect['roots'].values():
        questions.append('大量连续施加时的实例容量上限、移除调度和跨网络同步')
    if rules[id] == 'totem':
        questions.append('图腾范围重复进入、多人图腾相遇、提前破坏及网络投递时序')
    if rules[id] == 'discovery':
        questions.append('所有奖励入口的实际奖池可达性、外层抽选概率及无匹配候选时的上层处理')
    if any(source['spells'].get(str(sp), {}).get(k, -1) > 0 for sp in effect['roots'].values() for k in ('conditionHp', 'conditionHpRate')):
        refs.append('hpConditions')
        questions.append('低血量状态切换与其他触发链的时序交互')
    if not detail['blocks']:
        questions.append('尚未解析到可展示数值／机制，继续查原生、事件或动作脚本')
    numeric = rules[id] not in ('undertaker-reset', 'treasure-map', 'revenant-family') and any(any(label not in ('出击时替换', '武器倾向') for label, _ in b['values']) for b in detail['blocks'])
    ledger[id] = dict(name=catalog['effects'][id]['name']['zh_CN'], obtainable=id in obtainable, roots=effect['roots'], states=states,
                      detailSources=[sp for b in detail['blocks'] for sp in [b['source'], *b.get('branches', [])]],
                      values='decoded-fields' if numeric else ('decoded-mechanism' if rules[id] in ('discovery', 'undertaker-reset', 'treasure-map', 'revenant-family') else ('named-replacement' if detail['blocks'] else 'unresolved')),
                      stacking='native-analysis' if rules[id] != 'unknown' else 'unresolved',
                      stackingCategory=detail['stacking'],
                      evidence=refs, openQuestions=questions, gameplayVerified=False)
coverage = dict(obtainable=len(obtainable), withDetails=sum(bool(result[e]['blocks']) for e in obtainable),
                withNumericFields=sum(ledger[e]['values'] == 'decoded-fields' for e in obtainable),
                withMechanicsOnly=sum(ledger[e]['values'] == 'decoded-mechanism' for e in obtainable),
                nativeStacking=sum(ledger[e]['stacking'] == 'native-analysis' for e in obtainable),
                catalog=len(ledger), catalogWithDetails=sum(bool(d['blocks']) for d in result.values()))
research = dict(schema=1, regulationSha256=source['hashes']['regulation.bin'],
                nativeEvidenceSha256=hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
                triggerEvidenceSha256=hashlib.sha256(trigger_path.read_bytes()).hexdigest(), coverage=coverage, effects=ledger)
research['linkEvidenceSha256'] = hashlib.sha256(link_path.read_bytes()).hexdigest()
research['scriptEvidenceSha256'] = hashlib.sha256(script_path.read_bytes()).hexdigest()
research['growthEvidenceSha256'] = hashlib.sha256(growth_path.read_bytes()).hexdigest()
research['totemEvidenceSha256'] = hashlib.sha256(totem_path.read_bytes()).hexdigest()
research['lifecycleEvidenceSha256'] = hashlib.sha256(lifecycle_path.read_bytes()).hexdigest()
research['recoveryEvidenceSha256'] = hashlib.sha256(recovery_path.read_bytes()).hexdigest()
research['executorRecoveryEvidenceSha256'] = hashlib.sha256(executor_path.read_bytes()).hexdigest()
research['weaponRecoveryEvidenceSha256'] = hashlib.sha256(weapon_recovery_path.read_bytes()).hexdigest()
research['recluseBleedEvidenceSha256'] = hashlib.sha256(recluse_bleed_path.read_bytes()).hexdigest()
research['revenantSacrificeEvidenceSha256'] = hashlib.sha256(sacrifice_path.read_bytes()).hexdigest()
research['gestureMadnessEvidenceSha256'] = hashlib.sha256(gesture_path.read_bytes()).hexdigest()
research['guardianSkillEvidenceSha256'] = hashlib.sha256(guardian_skill_path.read_bytes()).hexdigest()
research['executorBladeEvidenceSha256'] = hashlib.sha256(blade_path.read_bytes()).hexdigest()
research['undertakerPrayerEvidenceSha256'] = hashlib.sha256(prayer_path.read_bytes()).hexdigest()
research['guardianProtectionEvidenceSha256'] = hashlib.sha256(protection_path.read_bytes()).hexdigest()
research['executorTenacityEvidenceSha256'] = hashlib.sha256(tenacity_path.read_bytes()).hexdigest()
research['undertakerResetEvidenceSha256'] = hashlib.sha256(undertaker_reset_path.read_bytes()).hexdigest()
research['treasureMapEvidenceSha256'] = hashlib.sha256(treasure_map_path.read_bytes()).hexdigest()
research['passiveResourceEvidenceSha256'] = hashlib.sha256(passive_resource_path.read_bytes()).hexdigest()
research['damageAilmentEvidenceSha256'] = hashlib.sha256(damage_ailment_path.read_bytes()).hexdigest()
research['spellFamilyEvidenceSha256'] = hashlib.sha256(spell_family_path.read_bytes()).hexdigest()
research['periodicHpEvidenceSha256'] = hashlib.sha256(periodic_hp_path.read_bytes()).hexdigest()
research['perfumeEvidenceSha256'] = hashlib.sha256(perfume_path.read_bytes()).hexdigest()
research['duchessUltimateEvidenceSha256'] = hashlib.sha256(duchess_ultimate_path.read_bytes()).hexdigest()
research['guardianShockwaveEvidenceSha256'] = hashlib.sha256(guardian_shock_path.read_bytes()).hexdigest()
research['heroAdjustmentEvidenceSha256'] = hashlib.sha256(hero_adjustment_path.read_bytes()).hexdigest()
research['successiveRecoveryEvidenceSha256'] = hashlib.sha256(successive_recovery_path.read_bytes()).hexdigest()
research['successiveAttackEvidenceSha256'] = hashlib.sha256(successive_attack_path.read_bytes()).hexdigest()
research['scholarAilmentEvidenceSha256'] = hashlib.sha256(scholar_ailment_path.read_bytes()).hexdigest()
research['wylderFlameEvidenceSha256'] = hashlib.sha256(wylder_flame_path.read_bytes()).hexdigest()
research['revenantEnchantEvidenceSha256'] = hashlib.sha256(revenant_enchant_path.read_bytes()).hexdigest()
research['revenantFamilyEvidenceSha256'] = hashlib.sha256(revenant_family_path.read_bytes()).hexdigest()
research['guardianHalberdEvidenceSha256'] = hashlib.sha256(guardian_halberd_path.read_bytes()).hexdigest()
research['wylderFollowupEvidenceSha256'] = hashlib.sha256(wylder_followup_path.read_bytes()).hexdigest()
research['duchessDaggerEvidenceSha256'] = hashlib.sha256(duchess_dagger_path.read_bytes()).hexdigest()
research['equippedExclusivityEvidenceSha256'] = hashlib.sha256(equipped_exclusivity_path.read_bytes()).hexdigest()
research['startingReplacementsEvidenceSha256'] = hashlib.sha256(starting_replacements_path.read_bytes()).hexdigest()
research['guardAggroEvidenceSha256'] = hashlib.sha256(guard_aggro_path.read_bytes()).hexdigest()
research['itemSharingEvidenceSha256'] = hashlib.sha256(item_sharing_path.read_bytes()).hexdigest()
research['scholarTetherEvidenceSha256'] = hashlib.sha256(scholar_tether_path.read_bytes()).hexdigest()
research['ironeyeUltimateEvidenceSha256'] = hashlib.sha256(ironeye_ultimate_path.read_bytes()).hexdigest()
research['revenantGhostflameEvidenceSha256'] = hashlib.sha256(revenant_ghostflame_path.read_bytes()).hexdigest()
research['scholarFeintEvidenceSha256'] = hashlib.sha256(scholar_feint_path.read_bytes()).hexdigest()
research['flaskSharingEvidenceSha256'] = hashlib.sha256(flask_sharing_path.read_bytes()).hexdigest()
research['rallyRecoveryEvidenceSha256'] = hashlib.sha256(rally_path.read_bytes()).hexdigest()
research['attackNullifyEvidenceSha256'] = hashlib.sha256(attack_nullify_path.read_bytes()).hexdigest()
research['ailmentGrowthEvidenceSha256'] = hashlib.sha256(ailment_growth_path.read_bytes()).hexdigest()
research['frostStealthEvidenceSha256'] = hashlib.sha256(frost_stealth_path.read_bytes()).hexdigest()
research['duchessStealthEvidenceSha256'] = hashlib.sha256(duchess_stealth_path.read_bytes()).hexdigest()
research['undertakerContactEvidenceSha256'] = hashlib.sha256(undertaker_contact_path.read_bytes()).hexdigest()
research['guardianUltimateEvidenceSha256'] = hashlib.sha256(guardian_ultimate_path.read_bytes()).hexdigest()
research['raiderGrowthEvidenceSha256'] = hashlib.sha256(raider_growth_path.read_bytes()).hexdigest()
research['raiderSkillEvidenceSha256'] = hashlib.sha256(raider_skill_path.read_bytes()).hexdigest()
research['duchessPoiseEvidenceSha256'] = hashlib.sha256(duchess_poise_path.read_bytes()).hexdigest()
research['wylderBleedEvidenceSha256'] = hashlib.sha256(wylder_bleed_path.read_bytes()).hexdigest()
research['ironeyePoisonEvidenceSha256'] = hashlib.sha256(ironeye_poison_path.read_bytes()).hexdigest()
research['raiderDebuffEvidenceSha256'] = hashlib.sha256(raider_debuff_path.read_bytes()).hexdigest()
research['recluseAbsorptionEvidenceSha256'] = hashlib.sha256(absorption_path.read_bytes()).hexdigest()
research['duchessRestageEvidenceSha256'] = hashlib.sha256(restage_path.read_bytes()).hexdigest()
research['ironeyeMarkEvidenceSha256'] = hashlib.sha256(ironeye_mark_path.read_bytes()).hexdigest()
research['recluseMarkEvidenceSha256'] = hashlib.sha256(recluse_mark_path.read_bytes()).hexdigest()
research['startingGoodsEvidenceSha256'] = hashlib.sha256(starting_goods_path.read_bytes()).hexdigest()
research['startingWeaponEvidenceSha256'] = hashlib.sha256(starting_weapon_path.read_bytes()).hexdigest()
research['guardianDurationEvidenceSha256'] = hashlib.sha256(duration_path.read_bytes()).hexdigest()
research['duchessEvasionEvidenceSha256'] = hashlib.sha256(evasion_path.read_bytes()).hexdigest()
research['discoveryEvidenceSha256'] = hashlib.sha256(discovery_path.read_bytes()).hexdigest()
(ROOT / 'data/effect-research.json').write_text(json.dumps(research, ensure_ascii=False, indent=2) + '\n')
print(f'{len(result)} details; coverage={coverage}; {out.stat().st_size} browser bytes')
