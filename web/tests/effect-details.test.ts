import { describe, expect, it } from "vitest";
import { catalog } from "../src/core/catalog";
import { effectDetail } from "../src/core/effect-details";
import source from "../../data/effect-detail-source.json";
import evidence from "../../data/effect-native-evidence.json";
import research from "../../data/effect-research.json";
import triggers from "../../data/effect-trigger-source.json";
import links from "../../data/effect-link-source.json";
import scripts from "../../data/effect-script-evidence.json";
import growth from "../../data/effect-growth-source.json";
import totem from "../../data/effect-totem-evidence.json";
import discovery from "../../data/effect-discovery-evidence.json";
import lifecycle from "../../data/effect-lifecycle-evidence.json";
import recovery from "../../data/effect-recovery-evidence.json";
import executorRecovery from "../../data/effect-executor-recovery-evidence.json";
import weaponRecovery from "../../data/effect-weapon-recovery-evidence.json";
import recluseBleed from "../../data/effect-recluse-bleed-evidence.json";
import sacrifice from "../../data/effect-revenant-sacrifice-evidence.json";
import gesture from "../../data/effect-gesture-madness-evidence.json";
import guardianSkill from "../../data/effect-guardian-skill-evidence.json";
import blade from "../../data/effect-executor-blade-evidence.json";
import prayer from "../../data/effect-undertaker-prayer-evidence.json";
import protection from "../../data/effect-guardian-protection-evidence.json";
import tenacity from "../../data/effect-executor-tenacity-evidence.json";
import duchessPoise from "../../data/effect-duchess-poise-evidence.json";
import raiderSkill from "../../data/effect-raider-skill-evidence.json";
import raiderGrowth from "../../data/effect-raider-growth-evidence.json";
import undertakerReset from "../../data/effect-undertaker-reset-evidence.json";
import treasureMap from "../../data/effect-treasure-map-evidence.json";
import passiveResource from "../../data/effect-passive-resource-evidence.json";
import damageAilment from "../../data/effect-damage-ailment-evidence.json";
import spellFamily from "../../data/effect-spell-family-evidence.json";
import periodicHp from "../../data/effect-periodic-hp-evidence.json";
import perfume from "../../data/effect-perfume-evidence.json";
import duchessUltimate from "../../data/effect-duchess-ultimate-evidence.json";
import guardianShockwave from "../../data/effect-guardian-shockwave-evidence.json";
import heroAdjustment from "../../data/effect-hero-adjustment-evidence.json";
import successiveRecovery from "../../data/effect-successive-recovery-evidence.json";
import successiveAttack from "../../data/effect-successive-attack-evidence.json";
import scholarTether from "../../data/effect-scholar-tether-evidence.json";
import scholarAilment from "../../data/effect-scholar-ailment-evidence.json";
import wylderFlame from "../../data/effect-wylder-flame-evidence.json";
import revenantEnchant from "../../data/effect-revenant-enchant-evidence.json";
import revenantFamily from "../../data/effect-revenant-family-evidence.json";
import guardianHalberd from "../../data/effect-guardian-halberd-evidence.json";
import ironeyeUltimate from "../../data/effect-ironeye-ultimate-evidence.json";
import revenantGhostflame from "../../data/effect-revenant-ghostflame-evidence.json";
import scholarFeint from "../../data/effect-scholar-feint-evidence.json";
import attackNullify from "../../data/effect-attack-nullify-evidence.json";
import rally from "../../data/effect-rally-recovery-evidence.json";
import flaskSharing from "../../data/effect-flask-sharing-evidence.json";
import ailmentGrowth from "../../data/effect-ailment-growth-evidence.json";
import frostStealth from "../../data/effect-frost-stealth-evidence.json";
import duchessStealth from "../../data/effect-duchess-stealth-evidence.json";
import undertakerContact from "../../data/effect-undertaker-contact-evidence.json";
import guardianUltimate from "../../data/effect-guardian-ultimate-evidence.json";
import wylderBleed from "../../data/effect-wylder-bleed-evidence.json";
import ironeyePoison from "../../data/effect-ironeye-poison-evidence.json";
import raiderDebuff from "../../data/effect-raider-debuff-evidence.json";
import absorption from "../../data/effect-recluse-absorption-evidence.json";
import restage from "../../data/effect-duchess-restage-evidence.json";
import ironeyeMark from "../../data/effect-ironeye-mark-evidence.json";
import recluseMark from "../../data/effect-recluse-mark-evidence.json";
import startingGoods from "../../data/effect-starting-goods-evidence.json";
import startingWeapon from "../../data/effect-starting-weapon-evidence.json";
import duration from "../../data/effect-guardian-duration-evidence.json";
import evasion from "../../data/effect-duchess-evasion-evidence.json";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";

describe("MMV effect details", () => {
  it("uses the halberd shockwave radius rather than approach radius or attack lifetime", () => {
    const detail = effectDetail(7011600)!;
    expect(detail.blocks[0].values).toEqual([["旋风半径", "3 米"]]);
    expect(detail.blocks[0].duration).toBeNull();
    expect(detail.stacking).toBe("不可叠加");
    for (const row of guardianHalberd.checks.dispatch)
      expect(row.requests).toHaveLength(row.copies && row.enabled ? 1 : 0);
    for (const row of guardianHalberd.checks.radius)
      expect(row.radius).toBe([30901146, 30901148].includes(row.bullet) ? 3 : 0.5);
    const attack = guardianHalberd.checks.attackSetup.find(r => r.bullet === 30901146)!;
    expect(attack.requests).toEqual([{ id: 600000089, radius: 3 }]);
    expect(JSON.stringify(detail)).not.toMatch(/0\.35|40%/);
    expect(guardianHalberd.gameplayVerified).toBe(false);
    expect(research.guardianHalberdEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-guardian-halberd-evidence.json", import.meta.url)),
    ).digest("hex"));
  });
  it("resolves three independent family requests without turning trigger lifetime into summon duration", () => {
    const detail = effectDetail(7220210)!;
    expect(detail.blocks[0].values).toEqual([["召唤家人", "三名"]]);
    expect(detail.blocks[0].duration).toBeNull();
    expect(detail.stacking).toBe("不可叠加");
    expect(detail.stackingDetail).toBe("重复装备不增加家人数量");
    for (const row of revenantFamily.checks.dispatch)
      expect(row.requests).toHaveLength(row.copies && row.enabled ? 1 : 0);
    for (const row of revenantFamily.checks.emission) {
      expect(row.status.map(r => r.request)).toEqual([0, 1, 2].map(i => Number(row.success && row.slot === i)));
      expect(row.deliveries).toHaveLength(Number(row.success));
    }
    for (const row of revenantFamily.checks.repeat)
      expect(row.status.map(r => r.request)).toEqual(row.states.map(s => Number(s === 0)));
    expect(revenantFamily.gameplayVerified).toBe(false);
    expect(research.revenantFamilyEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-revenant-family-evidence.json", import.meta.url)),
    ).digest("hex"));
  });
  it("separates Revenant enchantment reapplication from replacement and frost duration", () => {
    for (const id of [7220100, 7220101]) {
      const detail = effectDetail(id)!;
      expect(detail.blocks[0].values).toEqual([["魔力基础攻击力", "+60"], ["冻伤基础累积", "40"]]);
      expect(detail.blocks[0].restrictions).toEqual(["右手武器"]);
      expect(detail.blocks[0].duration).toBe(20);
      expect(detail.blocks[1].duration).toBeNull();
      expect(detail.blocks[2].duration).toBe(30);
      expect(detail.stackingDetail).toContain("再次施加刷新附魔时长");
    }
    for (const row of revenantEnchant.checks.timer) {
      expect(Math.abs(row.expiryFrame / row.fps - (row.reapply ? 25 : 20))).toBeLessThanOrEqual(4 / row.fps);
      if (row.reapply) expect(row.remainingAfterReapply).toBe(20);
    }
    for (const row of revenantEnchant.checks.overwrite)
      expect(row.nodes.map(n => n.id)).toEqual([row.order.at(-1)]);
    for (const row of revenantEnchant.checks.correction)
      expect(row.remaining).toBe(500 - 40 * row.scale);
    expect(revenantEnchant.gameplayVerified).toBe(false);
    expect(research.revenantEnchantEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-revenant-enchant-evidence.json", import.meta.url)),
    ).digest("hex"));
  });
  it("shows flame lifetime without treating standalone emitter counts as scene hits", () => {
    const detail = effectDetail(7010500)!;
    expect(detail.stacking).toBe("不可叠加");
    expect(detail.blocks[0].values).toEqual([["火焰持续时间", "10 秒"]]);
    expect(detail.blocks[0].duration).toBeNull();
    for (const row of wylderFlame.checks.dispatch)
      expect(row.requests).toHaveLength(row.copies && row.enabled ? 1 : 0);
    for (const row of wylderFlame.checks.lifetime)
      expect(Math.abs(row.expiryFrame / row.fps - 10)).toBeLessThanOrEqual(2 / row.fps);
    expect(JSON.stringify(detail)).not.toMatch(/12|26%|每秒|每 1 秒/);
    expect(wylderFlame.gameplayVerified).toBe(false);
    expect(research.wylderFlameEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-wylder-flame-evidence.json", import.meta.url)),
    ).digest("hex"));
  });
  it("separates Scholar ailment HP damage from buildup, FP loss and link lifetime", () => {
    for (const id of [7036700, 7036701]) {
      const detail = effectDetail(id)!;
      expect(detail.stacking).toBe("不可叠加");
      expect(detail.blocks[0].values).toEqual([["异常造成的血量损伤", "+30%"]]);
      expect(detail.blocks[0].restrictions).toEqual(["中毒／腐败／出血／冻伤／发狂"]);
      expect(detail.blocks[0].duration).toBe(20);
      expect(detail.notes.join()).toContain("不增加催眠、发狂造成的专注值损失");
      expect(detail.notes.join()).toContain("断开连结不提前解除");
    }
    for (const row of scholarAilment.checks.damage) {
      const single = scholarAilment.checks.damage.find(r => r.copies === 1 && r.onset === row.onset && r.maximum === row.maximum)!;
      const plain = scholarAilment.checks.damage.find(r => r.copies === 0 && r.onset === row.onset && r.maximum === row.maximum)!;
      expect(row.fp).toEqual(plain.fp);
      if (row.copies === 3) expect(row.hp).toEqual(single.hp);
      if (row.onset === 1745) expect(row.hp[0]).toBe(0);
    }
    for (const row of scholarAilment.checks.buildup)
      expect(row.remaining).toBe(500 - row.incoming);
    for (const row of scholarAilment.checks.unlink) {
      expect(row.linked).toBe(false);
      expect(row.after).toBeCloseTo(15, 2);
    }
    for (const row of scholarAilment.checks.refresh)
      expect(Math.abs(row.expiryFrame / row.fps - (row.refresh ? 25 : 20))).toBeLessThanOrEqual(4 / row.fps);
    expect(scholarAilment.gameplayVerified).toBe(false);
    expect(research.scholarAilmentEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-scholar-ailment-evidence.json", import.meta.url)),
    ).digest("hex"));
  });
  it("separates flask sharing's self cost, ally healing and conditional restoration", () => {
    for (const id of [11001, 7010200]) {
      const detail = effectDetail(id)!;
      expect(detail.stacking).toBe("不可叠加");
      expect(detail.blocks[0].values).toEqual([["自身血量恢复", "最大值的 60% → 50%"]]);
      expect(detail.blocks[1].values).toEqual([["血量恢复", "最大值的 30%"], ["治疗范围", "半径 15 米，不含自身"]]);
      expect(detail.blocks[1].scope).toEqual(["半径 15 米，不含自身"]);
      expect(detail.blocks[2].values).toContainEqual(["持续时间", "自身 8 秒／我方 4 秒"]);
      expect(detail.blocks[3].values).toEqual([["自身专注值恢复", "最大值的 30%"], ["我方专注值恢复", "最大值的 15%"]]);
      expect(detail.blocks.every(b => b.duration === null && b.interval === null)).toBe(true);
      expect(detail.notes.join()).toContain("接受治疗者自身的圣杯瓶恢复量");
    }
    const gradual = effectDetail(8440200)!;
    expect(gradual.blocks[0].duration).toBeNull();
    expect(gradual.blocks[1].duration).toBe(8);
    expect(gradual.blocks[1].interval).toBe(.1);
    for (const row of flaskSharing.checks.branches) {
      expect(row.packets.reduce((sum, p) => sum + p.hp, 0)).toBe(row.gradual ? 100 : row.copies ? 500 : 600);
      expect(row.packets.reduce((sum, p) => sum + p.fp, 0)).toBe(row.fp ? 30 : 0);
      expect(row.allyBehaviors).toEqual(row.copies ? [
        ...(row.gradual ? [900102240, 900102241] : [900102221]), ...(row.fp ? [900102260] : []),
      ] : []);
    }
    for (const row of flaskSharing.checks.sourceModifiers)
      expect(row.hp[1]).toBe(row.recipient === 7611400 ? 330 : row.recipient === 6840100 ? 255 : 300);
    for (const row of flaskSharing.checks.targets)
      expect(row.accepted).toBe(!row.same && "sourceType" in row && [1, 2, 4].includes(row.sourceType ?? -1));
    for (const row of flaskSharing.checks.timeline.filter(r => r.copies === 3)) {
      const single = flaskSharing.checks.timeline.find(r => r.copies === 1 && r.leaf === row.leaf && r.fps === row.fps && r.refresh === row.refresh)!;
      expect(row.pulseFrames).toEqual(single.pulseFrames);
      expect(row.amount).toBe(10);
    }
    expect(flaskSharing.gameplayVerified).toBe(false);
    expect(research.flaskSharingEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-flask-sharing-evidence.json", import.meta.url)),
    ).digest("hex"));
  });
  it("separates rally recovery amounts, grade stacking and the recoverable HP window", () => {
    for (const [id, bonus] of [[7005600, null], [6005600, "+25%"], [6005601, "+35%"], [9090200, "+35%"]] as const) {
      const detail = effectDetail(id)!;
      expect(detail.stacking).toBe(id === 9090200 ? "可叠加" : "不同等级可叠加");
      expect(detail.blocks[0].values).toEqual([
        ["可追回血量", "通常为本次损失的 100%"],
        ["保留时间", "通常 4 秒"],
        ["可追回血量消退速度", "每秒最大血量的 100%"],
        ...(bonus ? [["攻击回血量", bonus]] : []),
      ]);
      expect(detail.blocks[0].duration).toBeNull();
      expect(detail.blocks[0].interval).toBeNull();
      expect(detail.notes.join()).toContain("不按造成伤害的比例计算");
      expect(detail.notes.join()).toContain("再次受损可能使先前未追回的血量提前消退");
    }
    for (const row of rally.checks.recovery) {
      expect(row.amount).toBe(Math.trunc(Math.fround(row.base * row.rate)));
      expect(row.after.hp).toBe(700 + (row.ids.length ? Math.min(300, row.amount) : 0));
      expect(row.queued.timer).toBe(row.ids.length ? 4 : 0);
    }
    const combined = rally.checks.recovery.find(r => r.ids.join() === "7005600,7005601,7005602" && r.attack === 0)!;
    const plusTwo = rally.checks.recovery.find(r => r.ids.join() === "7005602,7005602,7005602" && r.attack === 0)!;
    expect(combined.amount).toBe(59);
    expect(plusTwo.amount).toBe(47);
    for (const row of rally.checks.pool) {
      expect(row.after.hp).toBe(1000 - row.damage);
      expect(row.after.pool).toBe(row.ids.length ? row.damage * row.packet.rate : 0);
      expect(row.after.timer).toBe(row.after.pool ? 4 * row.packet.time : 0);
    }
    for (const row of rally.checks.timeline) {
      expect(Math.abs(row.decayAt - 4)).toBeLessThanOrEqual(1.01 / row.fps);
      expect(Math.abs(row.emptyAt - (4 + 300 / row.maximum))).toBeLessThanOrEqual(2.01 / row.fps);
    }
    expect(rally.checks.controls.find(r => "name" in r)?.after.hp).toBe(0);
    expect(rally.gameplayVerified).toBe(false);
    expect(research.rallyRecoveryEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-rally-recovery-evidence.json", import.meta.url)),
    ).digest("hex"));
  });
  it("distinguishes attack nullification from immunity to attached ailments", () => {
    const detail = effectDetail(7037800)!;
    expect(detail.stacking).toBe("不可叠加");
    expect(detail.stackingDetail).toBe("重复装备不提高概率");
    expect(detail.blocks[0].values).toEqual([["攻击失效概率", "20%"]]);
    expect(detail.blocks[0].duration).toBeNull();
    expect(detail.blocks[0].interval).toBeNull();
    expect(detail.notes).toEqual(["其他减伤抵消负面效果后仍可触发。", "成功触发仍可能累积异常。"]);
    for (const copies of [1, 3]) {
      const cases = attackNullify.checks.rolls.filter(r => r.copies === copies);
      expect(cases).toHaveLength(100);
      expect(cases.filter(r => r.success)).toHaveLength(20);
      for (const row of cases) {
        expect(row.draws).toBe(1);
        expect(row.hpWrites).toEqual(row.success ? [] : [-100]);
      }
    }
    for (const row of attackNullify.checks.predicate) {
      expect(row.eligible).toBe(!!row.copies && [7036602, 1501000].includes(row.debuff ?? 0));
      if (row.eligible && row.protect) expect(row.rates.every(v => v < 1)).toBe(true);
    }
    for (const row of attackNullify.checks.ailments) {
      expect(row.remaining).toBe(500 - row.amount);
      expect(row.success).toBe(row.rawSample % 100 < 20);
      expect(row.hpWrites).toEqual(row.success ? [] : [-100]);
    }
    expect(attackNullify.checks.controls.every(r => r.draws === 0)).toBe(true);
    expect(attackNullify.gameplayVerified).toBe(false);
    expect(research.attackNullifyEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-attack-nullify-evidence.json", import.meta.url)),
    ).digest("hex"));
  });
  it("shows ailment growth tiers and delayed clearing without a misleading buff duration", () => {
    const detail = effectDetail(7037700)!;
    expect(detail.stacking).toBe("不可叠加");
    expect(detail.stackingDetail).toBe("重复装备不加快增长，也不提高上限");
    expect(detail.blocks).toHaveLength(1);
    expect(detail.blocks[0].values).toEqual([["攻击倍率", "+3.5% → +7% → +11% → +15.5% → +20% → +25% → +30% → +35% → +40% → +45%"]]);
    expect(detail.blocks[0].duration).toBeNull();
    expect(detail.blocks[0].interval).toBeNull();
    expect(detail.notes).toEqual([
      "首次满足条件立即获得第一阶，其后每 20 秒提升一阶，最多 10 阶。",
      "所有异常累积和发作状态消失后，在当前 20 秒计时结束时清空增益。",
    ]);
    for (const row of ailmentGrowth.checks.gauges) {
      expect(row.count).toBe(row.copies && row.buildup ? 1 : 0);
    }
    for (const row of ailmentGrowth.checks.growth) {
      for (const step of row.steps) {
        expect(step.level).toBe(row.copies ? Math.min(step.index + 1, 10) : 0);
        expect(step.buffs).toHaveLength(step.level ? 1 : 0);
      }
    }
    for (const row of ailmentGrowth.checks.numeric) {
      for (const rate of row.rates) expect(rate).toBeCloseTo(row.kind === 5 ? 1 : ailmentGrowth.rates[row.level - 1], 5);
    }
    for (const row of ailmentGrowth.checks.timeline) {
      expect(row.transitions.map(n => n.level)).toEqual([1, 2, 0, 1]);
      for (const [i, n] of row.transitions.entries()) expect(Math.abs(n.time - [0, 20, 40, 41][i])).toBeLessThanOrEqual(3.01 / row.fps);
    }
    for (const row of ailmentGrowth.checks.clear) expect(row.after).toEqual([1, 1, 1, 1, 1]);
    expect(ailmentGrowth.gameplayVerified).toBe(false);
    expect(research.ailmentGrowthEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-ailment-growth-evidence.json", import.meta.url)),
    ).digest("hex"));
  });
  it("keeps frost concealment duration separate from the short notification markers", () => {
    const detail = effectDetail(7260700)!;
    expect(detail.stacking).toBe("不可叠加");
    expect(detail.stackingDetail).toBe("重复装备不延长隐身");
    expect(detail.blocks).toHaveLength(1);
    expect(detail.blocks[0].source).toBe(7260703);
    expect(detail.blocks[0].phase).toBe("自身或附近敌人冻伤时");
    expect(detail.blocks[0].values).toEqual([["隐身时间", "5 秒"]]);
    expect(detail.blocks[0].duration).toBeNull();
    expect(detail.blocks[0].interval).toBeNull();
    expect(detail.notes).toEqual(["再次触发刷新持续时间；队友冻伤不触发。"]);
    for (const row of frostStealth.checks.onset) {
      expect(row.shots).toHaveLength(!row.immune && row.resistance <= 50 ? 1 : 0);
    }
    for (const row of frostStealth.checks.recipients) {
      const eligible = row.same || [6, 7, 8, 9].includes(row.sourceType);
      expect(row.markerPresent).toBe(eligible);
      expect(row.hidden).toBe(!!row.copies && eligible);
      expect(row.nodes.filter(n => n.id === 7260703)).toHaveLength(row.hidden ? 1 : 0);
    }
    for (const row of frostStealth.checks.lifetime) {
      if (row.copies) {
        expect(row.first).not.toBeNull();
        expect(Math.abs((row.last! - row.first! + 1) / row.fps - 5)).toBeLessThanOrEqual(3.01 / row.fps);
      } else expect(row.first).toBeNull();
      expect(row.remaining.some(n => n.id === 7260703)).toBe(false);
    }
    for (const row of frostStealth.checks.repeat) {
      expect(row.lifetimes.every(n => n.lifetime > 4.8 && n.lifetime <= 5)).toBe(true);
      expect(Math.abs(row.transitions.at(-1)!.frame / 60 - row.starts.at(-1)! - 5)).toBeLessThan(.1);
    }
    expect(frostStealth.gameplayVerified).toBe(false);
    expect(research.frostStealthEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-frost-stealth-evidence.json", import.meta.url)),
    ).digest("hex"));
  });
  it("shows the lasting backstab concealment without exposing its maintenance timers", () => {
    const detail = effectDetail(7031800)!;
    expect(detail.stacking).toBe("不可叠加");
    expect(detail.stackingDetail).toBe("重复装备不增强或延长隐匿");
    expect(detail.blocks).toHaveLength(1);
    expect(detail.blocks[0].source).toBe(7031803);
    expect(detail.blocks[0].values).toEqual([["隐匿时间", "10 秒"]]);
    expect(detail.blocks[0].duration).toBeNull();
    expect(detail.blocks[0].interval).toBeNull();
    expect(detail.notes).toEqual(["再次背刺刷新持续时间。"]);
    for (const row of duchessStealth.checks.dispatch) {
      expect(row.states.at(-1)?.concealed).toBe(!!row.copies);
      expect(row.states.at(-1)?.transition).toBe(false);
      expect(row.nodes.filter(n => n.id === 7031803)).toHaveLength(row.copies ? 1 : 0);
    }
    for (const row of duchessStealth.checks.lifetime) {
      if (row.copies) {
        expect(row.first).not.toBeNull();
        expect(Math.abs((row.last! - row.first! + 1) / row.fps - 10)).toBeLessThanOrEqual(3.01 / row.fps);
      } else expect(row.first).toBeNull();
      expect(row.remaining.some(n => n.id === 7031803)).toBe(false);
    }
    for (const row of duchessStealth.checks.repeat) {
      expect(row.lifeAfter.every(n => n.lifetime > 9.3)).toBe(true);
      expect(Math.abs(row.transitions.at(-1)!.frame / 60 - row.starts.at(-1)! - 10)).toBeLessThan(.5);
    }
    for (const row of duchessStealth.checks.damage) {
      expect(row.after).toBeCloseTo(row.before - 1 / 60, 4);
      expect(row.rates[0]).toBeCloseTo(.01);
      expect(row.rates[1]).toBe(0);
    }
    expect(duchessStealth.gameplayVerified).toBe(false);
    expect(research.duchessStealthEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-duchess-stealth-evidence.json", import.meta.url)),
    ).digest("hex"));
  });
  it("shows the feint parry window separately from the longer cancel window", () => {
    const detail = effectDetail(7036710)!;
    expect(detail.stacking).toBe("不可叠加");
    expect(detail.stackingDetail).toBe("重复装备不延长弹反窗口");
    expect(detail.blocks[0].values).toEqual([["弹反窗口", "动作第 0.13～0.27 秒"]]);
    expect(detail.blocks[0].restrictions).toEqual(["刺剑／重刺剑"]);
    expect(detail.blocks[0].duration).toBeNull();
    expect(detail.blocks[0].interval).toBeNull();
    for (const row of scholarFeint.checks.rawEvents) {
      const attack = row.events.find(e => e.type === 1)!;
      const cancel = row.events.find(e => e.type === 0 && e.payload.startsWith("12000000"))!;
      expect(attack.end - attack.start).toBeCloseTo(4 / 30);
      expect(cancel.end).toBeGreaterThan(attack.end);
    }
    for (const row of scholarFeint.checks.dispatch) {
      if (row.type === 1) {
        expect(!!row.request).toBe(!!row.copies);
        if (row.request) {
          expect(row.request.kind).toBe(64);
          expect(row.request.behavior).toBe(row.weapon === 5000000 ? 100500591 : 100600591);
          expect(row.request.timeOffset).toBe(0);
        }
      } else expect(row.flags).toBe(row.copies ? (row.code === 18 ? 0x40 : 0x4000000000) : 0);
    }
    for (const row of scholarFeint.checks.script)
      expect(!!row.event).toBe(row.hero === 9 && [15, 16].includes(row.category) && !!row.pressed && !!row.window);
    expect(scholarFeint.gameplayVerified).toBe(false);
    expect(research.scholarFeintEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-scholar-feint-evidence.json", import.meta.url)),
    ).digest("hex"));
  });
  it("separates ghostflame frostbite onset from its lasting vulnerability and honors correction flags", () => {
    const detail = effectDetail(7011200)!;
    expect(detail.stacking).toBe("不可叠加");
    expect(detail.blocks.map(b => b.values)).toEqual([
      [["爆炸半径", "4 → 10 米"], ["冻伤基础累积", "50"]],
      [["冻伤伤害", "最大血量的 10% + 50"]], [["承伤倍率", "+15%"]],
    ]);
    expect(detail.blocks.map(b => b.duration)).toEqual([null, null, 30]);
    expect(detail.blocks.every(b => b.interval === null)).toBe(true);
    expect(detail.notes).toEqual(["再次命中不刷新这次冻伤时长。"]);
    for (const row of revenantGhostflame.checks.correction) {
      const expected = row.effect === 7500201 ? row.scale * (row.slot < 5 ? row.extra : 1) : 1;
      expect(row.appliedScale).toBe(expected);
      if (row.effect === 1501000) expect(row.amount).toBe(50);
      expect(row.remaining).toBe(1000 - row.amount);
    }
    for (const row of revenantGhostflame.checks.onset)
      expect(row.triggered).toBe(!row.immune && row.resistance <= 50);
    for (const row of revenantGhostflame.checks.damage) {
      expect(row.packet[0]).toBe(-(Math.trunc(row.maximum * .1) + 50));
      expect(row.rates.every(v => Math.abs(v - 1.15) < .00001)).toBe(true);
      expect(row.nodes.filter(n => n.id === 1501000)).toHaveLength(1);
    }
    for (const row of revenantGhostflame.checks.lifetime) {
      expect(row.hits).toHaveLength(1);
      expect(row.hits[0].frame).toBe(0);
      expect(Math.abs(row.lastActiveFrame / row.fps - 30)).toBeLessThan(.11);
      expect(row.remaining).toEqual([]);
    }
    expect(revenantGhostflame.gameplayVerified).toBe(false);
    expect(research.revenantGhostflameEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-revenant-ghostflame-evidence.json", import.meta.url)),
    ).digest("hex"));
  });
  it("keeps charged ultimate poison separate from early release and maintenance timing", () => {
    const detail = effectDetail(7034600)!;
    expect(detail.stacking).toBe("不可叠加");
    expect(detail.stackingDetail).toBe("重复装备不增加累积或伤害");
    expect(detail.blocks.map(b => b.values)).toEqual([
      [["中毒基础累积", "300"]], [["中毒伤害", "最大血量的 0.1% + 10"]],
    ]);
    expect(detail.blocks.map(b => b.duration)).toEqual([null, 40]);
    expect(detail.blocks.map(b => b.interval)).toEqual([null, 1.3]);
    expect(detail.notes).toEqual(["提前放箭不附加此中毒。", "中毒期间再次命中不刷新这次中毒时长。"]);
    for (const row of ironeyeUltimate.checks.dispatch) {
      const poison = row.requests.some(r => r.behavior === 700000140);
      expect(poison).toBe(!!row.active && row.animation === 620000 && row.state === 2258);
    }
    for (const row of ironeyeUltimate.checks.selection) {
      expect(row.states[2258]).toBe(!!row.copies);
      expect(row.states[2025]).toBe(!row.copies);
    }
    for (const row of ironeyeUltimate.checks.onset)
      expect(row.rejected).toBe(row.immune || row.resistance > row.amount);
    for (const row of ironeyeUltimate.checks.damage)
      expect(row.packet[0]).toBe(-(Math.trunc(row.maximum * .001) + 10));
    for (const row of ironeyeUltimate.checks.repeat) {
      expect(row.result).toBe("existing");
      expect(row.remaining).toBeCloseTo(40 - row.elapsed);
    }
    expect(ironeyeUltimate.gameplayVerified).toBe(false);
    expect(research.ironeyeUltimateEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-ironeye-ultimate-evidence.json", import.meta.url)),
    ).digest("hex"));
  });
  it("separates Scholar tether eligibility time from wall time and repeated ultimate applications", () => {
    const detail = effectDetail(7036400)!;
    expect(detail.stacking).toBe("不可叠加");
    expect(detail.stackingDetail).toBe("重复装备不增加单次伤害");
    expect(detail.blocks[0].values).toEqual([["HP 伤害", "15 点／次"]]);
    expect(detail.blocks[0].duration).toBe(20);
    expect(detail.blocks[0].interval).toBe(1);
    expect(detail.blocks[0].restrictions).toEqual(["仅连结期间计时"]);
    expect(detail.notes).toEqual(["未连结时暂停；连结后继续剩余时间。", "多次绝招施加的持续伤害各自计时，可叠加。"]);
    for (const row of scholarTether.checks.dispatch)
      expect(row.requests).toHaveLength(row.copies && row.active ? 1 : 0);
    for (const row of scholarTether.checks.unlink) {
      expect(row.paused).toBe(row.before);
      expect(row.after).toBeLessThan(row.before);
      expect(row.unlinkEffects).toEqual([row.reason ? 708120 : 708121]);
      expect(row.rejoinEffects).toEqual([708110]);
    }
    for (const row of scholarTether.checks.repeat) {
      expect(row.windowDamage).toBe(row.gap < 20 ? 60 : 30);
      expect(row.nodePeak).toBe(row.gap < 20 ? 2 : 1);
      expect(row.remaining).toEqual([]);
    }
    for (const row of scholarTether.checks.damage) {
      if (!row.marker) {
        expect(row.hits).toEqual([]);
        expect(row.remaining.every(n => n.lifetime === 20)).toBe(true);
      }
      for (const hit of row.hits)
        expect(hit.packet).toEqual([-15 * row.copies, 0, -15 * row.copies, 0, -15 * row.copies, 0, 0]);
    }
    expect(scholarTether.gameplayVerified).toBe(false);
    expect(research.scholarTetherEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-scholar-tether-evidence.json", import.meta.url)),
    ).digest("hex"));
  });

  it("shows cumulative successive-attack tiers without treating the decay helper as another damage tier", () => {
    const detail = effectDetail(7037600)!;
    expect(detail.stacking).toBe("不可叠加");
    expect(detail.stackingDetail).toBe("重复装备不增加增伤或累积速度");
    expect(detail.blocks).toHaveLength(1);
    expect(detail.blocks[0].values).toEqual([["攻击倍率", "+5% → +11.83% → +21.89%"]]);
    expect(detail.blocks[0].duration).toBeNull();
    expect(detail.blocks[0].interval).toBeNull();
    expect(detail.notes).toEqual(["增伤逐档累积；停止攻击后逐渐衰退。"]);
    expect(successiveAttack.rates).toEqual([1.05, 1.065, 1.09, 1]);
    for (const row of successiveAttack.checks.lifecycle) {
      expect(row.peak).toBeCloseTo(1.2188925, 5);
      expect(row.finalCounter).toBe(0);
      expect(row.transitions.at(-1)!.active).toEqual([]);
      const same = successiveAttack.checks.lifecycle.find(r => r.fps === row.fps && r.copies === 1)!;
      expect(row.transitions).toEqual(same.transitions);
    }
    for (const row of successiveAttack.checks.mixed) {
      expect(row.peak).toBeCloseTo(1.2188925, 5);
      expect(row.recoveries).toHaveLength(5);
      for (const recovery of row.recoveries) {
        expect(recovery.recoveryCounter).toBe(0);
        expect(recovery.attackCounter).toBeGreaterThan(0);
      }
    }
    expect(successiveAttack.gameplayVerified).toBe(false);
    expect(research.successiveAttackEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-successive-attack-evidence.json", import.meta.url)),
    ).digest("hex"));
  });

  it("explains shared successive-attack recovery and the extra decay from duplicate equipment", () => {
    for (const id of [10000, 7036000, 7036010]) {
      const detail = effectDetail(id)!;
      expect(detail.stacking).toBe("可叠加");
      expect(detail.stackingDetail).toBe("恢复量相加；累积衰减也叠加");
      expect(detail.blocks[0].values).toEqual([[id === 7036010 ? "HP恢复" : "FP恢复", id === 7036010 ? "最大值的 3%" : "最大值的 5%"]]);
      expect(detail.blocks[0].duration).toBeNull();
      expect(detail.blocks[0].interval).toBeNull();
      expect(detail.notes).toEqual(["累积达到 32 点时触发；每份词条每 0.8 秒减少 1 点累积。", "回血与回蓝共用累积进度，可同时触发。"]);
    }
    for (const row of successiveRecovery.checks.threshold)
      expect(row.recoveries).toHaveLength(row.copies && row.input >= 32 ? 1 : 0);
    for (const row of successiveRecovery.checks.mixed) {
      expect(row.recoveries).toHaveLength(row.copies.some(Boolean) ? 1 : 0);
      for (const r of row.recoveries) {
        expect(r.fp).toEqual([50 * row.copies[0], 0]);
        expect(r.hp).toEqual([300 * row.copies[1], 0, 300 * row.copies[1], 0, 0, 0, 0]);
        expect(r.counter).toBe(0);
      }
    }
    for (const row of successiveRecovery.checks.decay)
      expect(row.changes.map(r => r.counter)).toEqual([1, 2, 3].map(n => 20 - n * (row.copies[0] + row.copies[1])));
    for (const row of successiveRecovery.checks.repeat) {
      expect(row.recoveries).toHaveLength(Math.round(1 / row.gap));
      expect(row.recoveries[1].frame - row.recoveries[0].frame).toBeLessThan(row.fps);
    }
    expect(successiveRecovery.gameplayVerified).toBe(false);
    expect(research.successiveRecoveryEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-successive-recovery-evidence.json", import.meta.url)),
    ).digest("hex"));
  });

  it("deduplicates identical hero adjustments while combining distinct adjustments at every level", () => {
    for (const family of heroAdjustment.families) {
      for (const id of family.effects) {
        const detail = effectDetail(id)!;
        expect(detail.stacking).toBe("不可叠加");
        expect(detail.stackingDetail).toBe("同一词条只生效一次；不同词条的增减相加");
        expect(detail.blocks[0].restrictions).toEqual([]);
        expect(detail.blocks[0].phase).toBe("随等级调整能力值");
        const cases = heroAdjustment.checks.single.filter(r => r.effect === id);
        const single = cases.find(r => r.copies === 1 && r.role === "matching")!;
        const baseline = cases.find(r => r.copies === 0)!;
        for (const row of cases)
          expect(row.levels).toEqual(row.copies && row.role === "matching" ? single.levels : baseline.levels);
      }
      const cases = heroAdjustment.checks.combined.filter(r => r.hero === family.hero);
      for (const row of cases) {
        const unique = cases.find(r => r.copies[0] === Math.min(1, row.copies[0]) && r.copies[1] === Math.min(1, row.copies[1]))!;
        expect(row.levels).toEqual(unique.levels);
      }
    }
    for (const row of heroAdjustment.checks.roleChange) {
      expect(row.removed).toEqual(row.before);
      expect(row.restored).toEqual(row.active);
    }
    for (const row of heroAdjustment.checks.floor)
      expect(row.values).toEqual(row.adjustment.map(v => Math.max(0, v)));
    const combined = heroAdjustment.checks.combined.find(r => r.hero === 1 && r.copies.join() === "1,1")!;
    expect(combined.levels.find(r => r.level === 12)!.values).toEqual([41, 26, 24, 37, 30, 27, 27, 10]);
    expect(heroAdjustment.gameplayVerified).toBe(false);
    expect(research.heroAdjustmentEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-hero-adjustment-evidence.json", import.meta.url)),
    ).digest("hex"));
  });

  it("shows the Guardian shockwave HP component without turning emitter timers into cooldowns", () => {
    const detail = effectDetail(7033400)!;
    expect(detail.stacking).toBe("不可叠加");
    expect(detail.stackingDetail).toBe("重复装备不增加冲击波数量");
    expect(detail.blocks[0].values).toEqual([["冲击波半径", "2.5 → 3.5 米"], ["额外 HP 伤害", "目标最大值的 0.12%"]]);
    expect(detail.blocks[0].duration).toBeNull();
    expect(detail.blocks[0].interval).toBeNull();
    expect(detail.notes).toEqual(["连续防御可再次触发。"]);
    for (const row of guardianShockwave.checks.trigger)
      expect(row.shots).toHaveLength(row.copies ? 1 : 0);
    for (const row of guardianShockwave.checks.repeat)
      expect(row.shots).toHaveLength(row.arrivalFrames.length);
    for (const row of guardianShockwave.checks.target)
      expect(row.allowed).toBe(row.relation === "opposing");
    const singleHit = guardianShockwave.checks.damage.find(r => r.copies === 1 && r.maximum === 10000)!;
    expect(singleHit.packet).toEqual([-12, 0, -12, 0, -12, 0, 0]);
    expect(singleHit.afterExpiration).toEqual([0, 0, 0, 0, 0, 0, 0]);
    expect(guardianShockwave.gameplayVerified).toBe(false);
    expect(research.guardianShockwaveEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-guardian-shockwave-evidence.json", import.meta.url)),
    ).digest("hex"));
  });

  it("separates Duchess ultimate duration from cumulative attack tiers and their decay", () => {
    for (const id of [7033000, 7033001]) {
      const detail = effectDetail(id)!;
      expect(detail.stacking).toBe("不可叠加");
      expect(detail.stackingDetail).toBe("重复装备不增加时长或增伤");
      expect(detail.blocks[0].values).toEqual([["绝招持续时间", "15 → 25 秒"]]);
      expect(detail.blocks[0].restrictions).toEqual(["仅自身"]);
      expect(detail.blocks[1].values).toEqual([["攻击倍率", "+9% → +23.17% → +47.80% → +77.36%"]]);
      expect(detail.blocks.every(b => b.duration === null && b.interval === null)).toBe(true);
      expect(detail.notes).toEqual(["增伤逐档累积；停止攻击后逐渐衰退。"]);
    }
    for (const row of duchessUltimate.checks.threshold) {
      const expected = duchessUltimate.thresholds.flatMap((threshold, i) => row.input >= threshold ? [7033028 + i] : []);
      expect([...row.queued].sort()).toEqual([...expected, ...expected].sort());
    }
    for (const row of duchessUltimate.checks.lifecycle) {
      expect(row.peak).toBeCloseTo(1.09 * 1.13 * 1.2 * 1.2, 5);
      expect(row.transitions.at(-1)?.multiplier).toBe(1);
      expect(row.finalNodes).toEqual([]);
    }
    for (const row of duchessUltimate.checks.dispatch) {
      const fires = !!row.active && row.state === (row.judge === 7149 ? 2021 : 2022);
      expect(row.requests.length).toBe(fires ? 1 : 0);
    }
    expect(duchessUltimate.gameplayVerified).toBe(false);
    expect(research.duchessUltimateEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-duchess-ultimate-evidence.json", import.meta.url)),
    ).digest("hex"));
  });

  it("distinguishes perfume items and weapons without presenting renewal as accumulating buffs", () => {
    for (const [id, rates] of [[7043100, ["+15%", "+5%"]], [6043100, ["+30%", "+10%"]]] as const) {
      const detail = effectDetail(id)!;
      expect(detail.stacking).toBe("可叠加");
      expect(detail.blocks.map(b => b.values)).toEqual(rates.map(rate => [["攻击倍率", rate]]));
      expect(detail.blocks.map(b => b.restrictions)).toEqual([["适用：调香类道具"], ["适用：调香瓶攻击"]]);
      expect(detail.blocks.every(b => !b.duration && !b.interval && b.phase === "生效时")).toBe(true);
    }
    for (const row of perfume.checks.lifecycle) {
      expect(row.afterStop).toEqual([]);
      const first = row.frames[0].values[6150000][0];
      expect(first).toBe(1);
      expect(row.frames[1].values).toEqual(row.frames[2].values);
    }
    expect(perfume.weaponBindings.map(w => w.name)).toContain("火焰调香瓶");
    expect(perfume.sparkAromatic.name).toBe("火花香");
    expect(perfume.gameplayVerified).toBe(false);
    expect(research.perfumeEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-perfume-evidence.json", import.meta.url)),
    ).digest("hex"));
  });

  it("adds periodic HP copies while retaining independent timers and gain/loss channels", () => {
    expect(effectDetail(7001100)?.stacking).toBe("可叠加");
    expect(effectDetail(7001100)?.stackingDetail).toBe("恢复量相加，各自计时");
    expect(effectDetail(6850500)?.stackingDetail).toBe("消耗量相加，各自计时");
    for (const row of periodicHp.checks.mixed) {
      for (const pulse of row.pulses) {
        expect(pulse.packet).toEqual([2 * row.heal, 0, 2 * row.heal, row.drain ? -2 * row.drain : 0, 0, 0, 0]);
      }
    }
    const staggered = periodicHp.checks.staggered.find(r => r.first === 7001100 && r.second === 6850500 && r.fps === 60)!;
    expect(staggered.pulses[0]).toEqual({frame: 0, packet: [2, 0, 2, 0, 0, 0, 0]});
    expect(staggered.pulses[1]).toEqual({frame: 30, packet: [0, 0, 0, -2, 0, 0, 0]});
    expect(periodicHp.gameplayVerified).toBe(false);
    expect(research.periodicHpEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-periodic-hp-evidence.json", import.meta.url)),
    ).digest("hex"));
  });

  it("stacks family-specific spell multipliers while preserving native type and category filters", () => {
    for (const family of spellFamily.families) {
      const detail = effectDetail(family.root)!;
      expect(detail.stacking).toBe("可叠加");
      expect(detail.stackingDetail).toBe("攻击倍率相乘");
      expect(detail.blocks[0].values).toEqual([["攻击倍率", "+2.5%"]]);
    }
    const selected = (root: number, spell: number) => spellFamily.checks.selection.find(r => r.root === root && r.spell === spell)!;
    expect(selected(7043300, 4431).applied).toBe(true);
    expect(selected(7043300, 6907).applied).toBe(false);
    expect(selected(7043700, 4720).applied).toBe(true);
    for (const row of spellFamily.checks.repeat) {
      const expected = row.disabled ? 1 : 1.025 ** row.copies;
      expect(row.values.every(v => Math.abs(v - expected) < 1e-6)).toBe(true);
    }
    expect(spellFamily.gameplayVerified).toBe(false);
    expect(research.spellFamilyEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-spell-family-evidence.json", import.meta.url)),
    ).digest("hex"));
  });
  it("adds duplicate damage ailments and distinguishes their brief rearming window", () => {
    for (const family of damageAilment.families) {
      const detail = effectDetail(family.root)!;
      expect(detail.stacking).toBe("可叠加");
      expect(detail.stackingDetail).toBe("同种异常的累积量相加");
      expect(detail.notes).toContain("触发后有短暂间隔，期间受损不会重复累积。");
      expect(detail.blocks[0].values[0][1]).toBe(`+${family.amount} 点／次`);
      expect(detail.blocks[0].duration).toBeNull();
      for (const row of damageAilment.checks.trigger.filter(r => r.root === family.root)) {
        const fired = row.damage > 0 && !row.excluded;
        expect(row.remaining).toBe(10000 - (fired ? row.copies * family.amount : 0));
      }
      for (const row of damageAilment.checks.window.filter(r => r.root === family.root)) {
        expect(row.firstRemaining).toBe(10000 - row.copies * family.amount);
        expect(row.remaining).toBe(10000 - 2 * row.copies * family.amount);
      }
    }
    expect(damageAilment.gameplayVerified).toBe(false);
    expect(damageAilment.naturalDecayExecuted).toBe(false);
    expect(research.damageAilmentEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-damage-ailment-evidence.json", import.meta.url)),
    ).digest("hex"));
  });
  it("applies multiplicative passive resource, poise and flask stacking without conflating recovery channels", () => {
    for (const id of [6610400, 6610500, 6610600, 6611400, 6840100, 7001000, 7001001, 7001002, 7001003, 7001004])
      expect(effectDetail(id)!.stacking).toBe("可叠加");
    expect(effectDetail(6610400)!.stackingDetail).toBe("上限倍率相乘");
    expect(effectDetail(7001000)!.stackingDetail).toBe("受到的强韧度损耗倍率相乘");
    expect(effectDetail(6840100)!.stackingDetail).toContain("提升与降低也相乘");
    expect(passiveResource.checks.resources.find(r => r.ids.length === 2 && r.ids[0] === 7610400 && r.base === 1000 && !r.disabled)!.values.maxHpRate).toBe(1210);
    expect(passiveResource.checks.poise.find(r => r.ids.length === 2 && r.ids.every(id => id === 7001000) && !r.disabled)!.multiplier).toBeCloseTo(0.9025);
    expect(passiveResource.checks.flask.find(r => r.positive === 1 && r.negative === 1 && r.leaf === 501000 && r.maximum === 1000)!.packet).toEqual([0, 561, 0, 0, 0, 0, 0]);
    expect(passiveResource.checks.flaskCap.filter(r => r.leaf === 501000).every(r => r.packet[1] === r.maximum)).toBe(true);
    expect(passiveResource.checks.ordinaryRecovery.every(r => r.packet.join() === "2,0,2,0,0,0,0")).toBe(true);
    expect(passiveResource.gameplayVerified).toBe(false);
    expect(research.passiveResourceEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-passive-resource-evidence.json", import.meta.url)),
    ).digest("hex"));
  });
  it("keeps treasure markers local and does not infer fixed counts or complete map coverage", () => {
    const detail = effectDetail(7070000)!;
    expect(detail.blocks[0].values).toEqual([["显示范围", "自己的地图"]]);
    expect(detail.blocks[0].duration).toBeNull();
    expect(detail.notes).toEqual(["只标记已出现的宝藏，不增加宝藏数量。"]);
    expect(detail.stacking).toBe("不可叠加");
    expect(research.effects["7070000"].values).toBe("decoded-mechanism");
    for (const row of treasureMap.checks.visibility) {
      const point = treasureMap.points.find(p => p.id === row.point)!;
      expect(row.eligible).toBe(row.reveal && row.spawn && !row.opened);
      expect(row.visible).toBe(row.eligible && Boolean(point.displayMask & 1));
      expect(row.otherMode).toBe(row.eligible && Boolean(point.displayMask & 2));
    }
    for (const row of treasureMap.checks.copies) {
      expect(row.nodes).toHaveLength(row.copies);
      expect(row.present).toBe(row.copies > 0);
    }
    expect(treasureMap.checks.unbound.every(row => !row.visible)).toBe(true);
    expect(treasureMap.gameplayVerified).toBe(false);
    expect(treasureMap.eventVmExecuted).toBe(false);
    expect(research.treasureMapEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-treasure-map-evidence.json", import.meta.url)),
    ).digest("hex"));
  });
  it("refills Undertaker skill charges at the finishing animation without storing extra uses", () => {
    const detail = effectDetail(6500900)!;
    expect(detail.blocks[0].values).toEqual([["技艺使用次数", "恢复至上限"]]);
    expect(detail.blocks[0].phase).toBe("绝招收尾动作开始时");
    expect(detail.blocks[0].duration).toBeNull();
    expect(detail.notes).toContain("次数已满时不会额外储存。");
    expect(detail.stacking).toBe("不可叠加");
    expect(research.effects["6500900"].values).toBe("decoded-mechanism");
    for (const row of undertakerReset.checks.dispatch) {
      expect(row.bank).toBe(255);
      expect(row.refills).toBe(Number(row.copies > 0 && row.active && row.player));
    }
    for (const row of undertakerReset.checks.capacity) {
      expect(row.after.remaining).toBe(row.maximum);
      expect(row.after.elapsed).toBe(0);
      expect(row.readyAfter).toBe(true);
    }
    expect(undertakerReset.gameplayVerified).toBe(false);
    expect(research.undertakerResetEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-undertaker-reset-evidence.json", import.meta.url)),
    ).digest("hex"));
  });
  it("shows Undertaker contact as one-time ally healing without multiplying duplicate equipment", () => {
    const detail = effectDetail(7037300)!;
    expect(detail.blocks[0].values).toEqual([["HP 恢复", "目标最大值的 30% + 100"]]);
    expect(detail.blocks[0].restrictions).toEqual(["仅友方角色，不含自身"]);
    expect(detail.blocks[0].duration).toBeNull();
    expect(detail.blocks[0].interval).toBeNull();
    expect(detail.stacking).toBe("不可叠加");
    for (const row of undertakerContact.checks.dispatch)
      expect(row.requests.length).toBe(Number(row.copies > 0));
    for (const row of undertakerContact.checks.target.filter(r => r.effect === 7037301))
      expect(row.allowed).toBe(row.relation === "friendly");
    for (const row of undertakerContact.checks.healing) {
      expect(row.heals.length).toBe(Number(row.qualified));
      if (row.qualified) expect(row.heals[0].packet[0]).toBe(row.maximum * 0.3 + 100);
    }
    expect(undertakerContact.gameplayVerified).toBe(false);
    expect(research.undertakerContactEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-undertaker-contact-evidence.json", import.meta.url)),
    ).digest("hex"));
  });
  it("shows both Guardian protections for self and allies and explains the expendable layer", () => {
    for (const id of [7011400, 7011401]) {
      const detail = effectDetail(id)!;
      expect(detail.blocks.map(b => b.values)).toEqual([
        [["承伤倍率", "-20%"]], [["承伤倍率", "-90%"], ["保护最长保留", "60 秒"]],
      ]);
      expect(detail.blocks.map(b => b.duration)).toEqual([30, null]);
      expect(detail.blocks.every(b => b.restrictions.includes("自身及周围友方 · 半径 15 米"))).toBe(true);
      expect(detail.stacking).toBe("不可叠加");
      expect(detail.notes).toContain("两层同时存在时合计减伤 92%。");
    }
    for (const row of guardianUltimate.checks.target.filter(r => r.leaf !== 7033101))
      expect(row.allowed).toBe(["self", "friendly"].includes(row.relation));
    for (const row of guardianUltimate.checks.damage)
      expect(row.remaining.includes(7011401)).toBe(row.active.includes(7011401) && row.damage <= 0);
    for (const row of guardianUltimate.checks.replenishment)
      expect(row.changes.map(c => Math.round(c.rate * 100))).toEqual([8, 80, 8, 80]);
    expect(guardianUltimate.gameplayVerified).toBe(false);
    expect(research.guardianUltimateEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-guardian-ultimate-evidence.json", import.meta.url)),
    ).digest("hex"));
  });
  it("caps Raider finisher growth at ten multiplicative steps without treating duplicate equipment as growth", () => {
    for (const id of [7031400, 7031401]) {
      const detail = effectDetail(id)!;
      expect(detail.blocks[0].values).toEqual([["攻击倍率", "每次 ×1.03，最多约 +34.39%"], ["成长上限", "10 次"]]);
      expect(detail.blocks[0].phase).toBe("强化反击的最后一击时");
      expect(detail.blocks[0].duration).toBeNull();
      expect(detail.stacking).toBe("不可叠加");
      expect(detail.stackingDetail).toBe("重复装备不加快成长，也不提高上限");
    }
    for (const row of raiderGrowth.checks.growth) {
      expect(row.steps.map(s => s.level)).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 10]);
      expect(row.steps.at(-1)!.rates.every(v => Math.abs(v - 1.03 ** 10) < 0.000001)).toBe(true);
      expect(row.notifications).toBe(10);
    }
    expect(raiderGrowth.attack.selfTarget).toBe(1);
    expect(raiderGrowth.attack.opposeTarget).toBe(0);
    expect(raiderGrowth.gameplayVerified).toBe(false);
    expect(research.raiderGrowthEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-raider-growth-evidence.json", import.meta.url)),
    ).digest("hex"));
  });
  it("separates Raider's ordinary and empowered skill rates without displaying a maintenance lifetime", () => {
    for (const id of [7031500, 7031501]) {
      const detail = effectDetail(id)!;
      expect(detail.blocks.map(b => b.values)).toEqual([
        [["物理攻击倍率", "+50%"], ["承伤倍率", "+30%"]],
        [["物理攻击倍率", "+100%"], ["承伤倍率", "+30%"]],
      ]);
      expect(detail.blocks.map(b => b.duration)).toEqual([null, null]);
      expect(detail.blocks.map(b => b.interval)).toEqual([null, null]);
      expect(detail.stacking).toBe("不可叠加");
    }
    for (const row of raiderSkill.checks.numeric) {
      expect(row.rates).toEqual([row.copies && row.kind !== 5 ? (row.leaf === 7031601 ? 1.5 : 2) : 1, 1, 1, 1, 1]);
    }
    for (const row of raiderSkill.checks.maintenance) {
      expect(row.samples.at(-1)!.rate).toBe(1);
      expect(row.samples.filter(s => s.frame < row.fps * 2).every(s => s.rate > 1)).toBe(true);
    }
    expect(raiderSkill.checks.script.find(r => r.ended === 1 && r.boost === 1)!.result.event).toBe("W_SmashAttack2");
    expect(raiderSkill.checks.overlap.every(r => r.rates[0] === 3)).toBe(true);
    expect(raiderSkill.gameplayVerified).toBe(false);
    expect(research.raiderSkillEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-raider-skill-evidence.json", import.meta.url)),
    ).digest("hex"));
  });
  it("makes nearby enemies receive more poise damage for six seconds without duplicate amplification", () => {
    for (const id of [7033100, 7033101]) {
      const detail = effectDetail(id)!;
      expect(detail.blocks[0].values).toEqual([["目标承受的削韧", "+30%"], ["范围半径", "15 米"]]);
      expect(detail.blocks[0].duration).toBe(6);
      expect(detail.blocks[0].interval).toBeNull();
      expect(detail.stacking).toBe("不可叠加");
      expect(detail.stackingDetail).toBe("再次施加刷新时长");
    }
    for (const row of duchessPoise.checks.consumer) {
      expect(row.rate).toBeCloseTo(row.copies ? 1.3 : 1);
      expect(row.result.remaining).toBeCloseTo(100 - row.input * (row.copies ? 1.3 : 1), 3);
    }
    expect(duchessPoise.checks.consumer.find(r => r.copies === 0 && r.input === 77)!.result.broken).toBe(false);
    expect(duchessPoise.checks.consumer.find(r => r.copies === 1 && r.input === 77)!.result.broken).toBe(true);
    expect(duchessPoise.checks.emission.every(r => r.emissions.length === 1)).toBe(true);
    expect(duchessPoise.checks.refresh.every(r => r.remaining === 6)).toBe(true);
    expect(duchessPoise.gameplayVerified).toBe(false);
    expect(research.duchessPoiseEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-duchess-poise-evidence.json", import.meta.url)),
    ).digest("hex"));
  });
  it("shows the referenced pull-attack bleed and treats its one-second lifetime as a lockout", () => {
    const detail = effectDetail(6500000)!;
    expect(detail.blocks.map(b => b.values)).toEqual([[["出血基础累积", "55"]], [["出血伤害", "最大血量的 12.5% + 100"]]]);
    expect(detail.blocks.map(b => b.duration)).toEqual([null, null]);
    expect(detail.blocks.map(b => b.interval)).toEqual([null, null]);
    expect(detail.stacking).toBe("不可叠加");
    expect(detail.notes).toEqual(["该出血发作后约 1 秒内不重复触发。"]);
    expect(wylderBleed.checks.onset.filter(r => r.immune).every(r => r.rejected && r.remaining === r.resistance)).toBe(true);
    expect(wylderBleed.checks.damage.find(r => r.maximum === 10000)).toEqual({maximum: 10000, damage: -1350});
    expect(wylderBleed.unresolved).toEqual({missingBehavior: 600000030, unreferencedLeaf: 7500001});
    expect(detail.blocks.flatMap(b => [b.source, ...(b.branches ?? [])])).not.toContain(7500001);
    for (const row of wylderBleed.checks.lifetime)
      expect(row.damage).toEqual([{frame: 0, damage: -1350}]);
    for (const row of wylderBleed.checks.repeat) {
      expect(row.damage).toHaveLength(3);
      expect(row.damage[1].frame / row.fps).toBeGreaterThanOrEqual(1);
    }
    expect(wylderBleed.gameplayVerified).toBe(false);
    expect(research.wylderBleedEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-wylder-bleed-evidence.json", import.meta.url)),
    ).digest("hex"));
  });
  it("separates poison buildup, periodic damage and the poisoned-target bonus", () => {
    const detail = effectDetail(6500200)!;
    expect(detail.blocks.map(b => b.values)).toEqual([
      [["中毒基础累积", "70"]], [["中毒伤害", "最大血量的 0.1% + 10"]], [["追加伤害", "最大血量的 0.25% + 250"]],
    ]);
    expect(detail.blocks.map(b => b.duration)).toEqual([null, 40, null]);
    expect(detail.blocks.map(b => b.interval)).toEqual([null, 1.3, null]);
    expect(detail.stacking).toBe("不可叠加");
    expect(detail.notes).toEqual(["中毒期间再次命中不刷新这次中毒时长。", "追加伤害约每 0.1 秒最多触发一次。"]);
    expect(ironeyePoison.checks.onset.filter(r => r.immune).every(r => r.rejected && r.remaining === r.resistance)).toBe(true);
    expect(ironeyePoison.checks.damage.find(r => r.maximum === 10000)).toEqual({maximum: 10000, poison: -20, bonus: -275});
    for (const row of ironeyePoison.checks.bonus)
      expect(row.damage).toBe(row.prior ? -275 : 0);
    expect(ironeyePoison.checks.bonusTiming.filter(r => r.fps === 60 && r.hits.length === 31)[0].damage.map(r => r.frame)).toEqual([0,8,16,24]);
    for (const row of ironeyePoison.checks.repeat)
      expect(row.remaining).toBe(40 - row.elapsed);
    for (const row of ironeyePoison.checks.lifetime) {
      expect(row.ticks).toHaveLength(31);
      expect(row.ticks.every(t => t.damage === -20)).toBe(true);
    }
    expect(ironeyePoison.gameplayVerified).toBe(false);
    expect(research.ironeyePoisonEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-ironeye-poison-evidence.json", import.meta.url)),
    ).digest("hex"));
  });
  it("reduces a skill-hit target's attack rate with refresh and spell exclusions", () => {
    const detail = effectDetail(6500400)!;
    expect(detail.blocks[0].values).toEqual([["目标攻击倍率", "-13%"]]);
    expect(detail.blocks[0].duration).toBe(13);
    expect(detail.stacking).toBe("不可叠加");
    expect(detail.stackingDetail).toBe("再次命中刷新时长");
    expect(detail.notes).toEqual(["不影响按魔法、祷告或特殊法术处理的攻击。"]);
    for (const row of raiderDebuff.checks.arrival) {
      expect(row.rates).toEqual(Array(5).fill(row.count && ![3,4,5,10].includes(row.attackKind) ? 0.87 : 1));
      expect(row.nodes).toHaveLength(row.count ? 1 : 0);
    }
    for (const row of raiderDebuff.checks.refresh) {
      expect(row.rates).toEqual(Array(5).fill(0.87));
      expect(row.nodes).toHaveLength(1);
      expect(row.nodes[0].lifetime).toBe(13);
    }
    for (const row of raiderDebuff.checks.dispatch)
      expect(row.requests).toHaveLength(row.copies ? 1 : 0);
    for (const row of raiderDebuff.checks.lifetime)
      expect(Math.abs(row.expiryFrame / row.fps - 13)).toBeLessThanOrEqual(3.01 / row.fps);
    expect(raiderDebuff.gameplayVerified).toBe(false);
    expect(research.raiderDebuffEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-raider-debuff-evidence.json", import.meta.url)),
    ).digest("hex"));
  });
  it("protects the collected element with independent timers and same-element refresh", () => {
    const detail = effectDetail(6500600)!;
    expect(detail.blocks[0].values).toEqual([["对应属性减伤", "20%"]]);
    expect(detail.blocks[0].duration).toBe(30);
    expect(detail.stacking).toBe("不可叠加");
    expect(detail.stackingDetail).toBe("同属性再次收集刷新时长；不同属性可同时生效");
    for (const row of absorption.checks.protection) {
      expect(row.damageTaken).toEqual([1, ...[1, 2, 3, 4].map(e => row.copies && e === row.element ? 0.8 : 1)]);
    }
    for (const row of absorption.checks.refresh) {
      expect(row.damageTaken).toEqual([1, ...[1, 2, 3, 4].map(e => row.elements.includes(e) ? 0.8 : 1)]);
      expect(row.nodes.filter(n => absorption.leaves.includes(n.id))).toHaveLength(row.elements.length);
    }
    for (const row of absorption.checks.lifetime)
      expect(Math.abs(row.expiryFrame / row.fps - 30)).toBeLessThanOrEqual(3.01 / row.fps);
    expect(absorption.checks.dispatch.filter(r => !r.active || !r.present || !r.element || r.occupied === 3).every(r => !r.emitted.length)).toBe(true);
    expect(absorption.gameplayVerified).toBe(false);
    expect(research.recluseAbsorptionEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-recluse-absorption-evidence.json", import.meta.url)),
    ).digest("hex"));
  });
  it("raises Restage's damage share without increasing poise or multiplying duplicate relics", () => {
    const detail = effectDetail(7290000)!;
    expect(detail.blocks[0].values).toEqual([["重演伤害比例", "50% → 60%"]]);
    expect(detail.stacking).toBe("不可叠加");
    expect(detail.stackingDetail).toBe("重复装备不增加重演比例");
    expect(detail.blocks[0].duration).toBeNull();
    expect(detail.notes).toEqual(["不提高重演的削韧。"]);
    const rows = restage.checks.damage.filter((r) => r.values.length === 1 && r.values[0] === 100 && r.statusBits === 15);
    expect(rows.map((r) => r.result.hp)).toEqual([[-50], [-60]]);
    expect(rows[0].result.poise).toEqual(rows[1].result.poise);
    expect(rows[0].result.statuses).toEqual(rows[1].result.statuses);
    for (const row of restage.checks.selection)
      expect(row.rate).toBeCloseTo(row.copies ? 0.6 : 0.5);
    expect(restage.checks.repeat.map((r) => r.result.hp)).toEqual([[-50], [-60], [-60], [-50]]);
    expect(restage.bindings.map((b) => b.name)).toEqual(["IndexDejavuBlend", "IsRelic_Dejavu", "IsRelic_Dejavu"]);
    expect(restage.gameplayVerified).toBe(false);
    expect(research.duchessRestageEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-duchess-restage-evidence.json", import.meta.url)),
    ).digest("hex"));
  });
  it("uses the weakpoint lifetime and preserves longer remaining time without restoring durability", () => {
    const detail = effectDetail(7280000)!;
    expect(detail.blocks[0].values).toEqual([["弱点最长持续时间", "17 → 22 秒"]]);
    expect(detail.stacking).toBe("不可叠加");
    expect(detail.stackingDetail).toBe("重复装备不延长弱点持续时间");
    expect(detail.notes).toEqual(["弱点被击破会提前消失；再次施加取原剩余时间与新时长中较长者，不累加，也不补回弱点耐久。"]);
    expect(detail.blocks[0].duration).toBeNull();
    for (const row of ironeyeMark.checks.refresh) {
      expect(row.remaining).toBe(Math.max(row.initial - row.elapsed, row.new));
      expect(row.durability).toBe(123);
    }
    for (const row of ironeyeMark.checks.lifetime)
      expect(Math.abs(row.expiresFrame / row.fps - (row.copies ? 22 : 17))).toBeLessThanOrEqual(1.01 / row.fps);
    expect(ironeyeMark.checks.selection.filter((r) => r.kind !== 1 || r.flags || r.attack !== 600000110).every((r) => !r.queued.length)).toBe(true);
    expect(ironeyeMark.checks.breakage.filter((r) => r.damage >= 3000).every((r) => !r.queued.length && r.removedAfterZeroDurability)).toBe(true);
    expect(ironeyeMark.gameplayVerified).toBe(false);
    expect(research.ironeyeMarkEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-ironeye-mark-evidence.json", import.meta.url)),
    ).digest("hex"));
  });
  it("shows the victim mark duration and keeps overlapping marks from multiplying recovery", () => {
    for (const id of [7034300, 7034301]) {
      const detail = effectDetail(id)!;
      expect(detail.blocks[0].values).toEqual([["鲜血烙印持续时间", "12.5 → 20 秒"]]);
      expect(detail.stacking).toBe("不可叠加");
      expect(detail.stackingDetail).toBe("重复装备不延长烙印持续时间");
      expect(detail.notes).toEqual(["再次施加同版烙印会刷新时间；普通版与延长版不会叠加恢复量。"]);
      expect(detail.blocks[0].duration).toBeNull();
    }
    for (const row of recluseMark.checks.lifetime) {
      const duration = row.id === 706100 ? 12.5 : 20;
      expect(Math.abs(row.expiresFrame / row.fps - duration - (row.refresh ?? 0))).toBeLessThanOrEqual(3.01 / row.fps);
      if (row.refresh) expect(row.refreshedLifetime).toBe(duration);
    }
    for (const row of recluseMark.checks.recovery.filter((r) => r.input === 100 && r.local && r.channel >= 0))
      expect(row.requests).toEqual(row.ids.length ? [["0x426130", 40], ["0x4261c0", 8]] : []);
    expect(recluseMark.checks.recovery.filter((r) => !r.local || r.channel < 0).every((r) => !r.requests.length)).toBe(true);
    expect(recluseMark.state.animation).toBe("a906_660000");
    expect(recluseMark.gameplayVerified).toBe(false);
    expect(research.recluseMarkEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-recluse-mark-evidence.json", import.meta.url)),
    ).digest("hex"));
  });
  it("shares pouch expansion with picked pouches while keeping Dragon Heart slots independent", () => {
    for (const id of [7121000, 7121001]) {
      const detail = effectDetail(id)!;
      expect(detail.blocks[0].values).toEqual([["道具栏位", "+1"]]);
      expect(detail.stacking).toBe("可叠加");
      expect(detail.stackingDetail).toBe("每条 +1 格，与小型随身包合计最多 +4 格");
    }
    const capacity = startingGoods.checks.capacity;
    expect(capacity.find((r) => r.relic === 3 && r.pickup === 0 && r.dragon === 0)?.capacity).toBe(7);
    expect(capacity.find((r) => r.relic === 3 && r.pickup === 3 && r.dragon === 0)?.capacity).toBe(8);
    expect(capacity.find((r) => r.relic === 6 && r.pickup === 5 && r.dragon === 2)?.capacity).toBe(10);
    for (const row of startingGoods.checks.reinitialize) {
      expect(row.afterRepeat).toBe(row.new);
      expect(row.capacity).toBe(Math.min(8, 4 + row.new));
    }
    expect(startingGoods.checks.allocationFailure).toEqual([{quantity: 0, capacity: 4}]);
    expect(startingGoods.gameplayVerified).toBe(false);
    expect(research.startingGoodsEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-starting-goods-evidence.json", import.meta.url)),
    ).digest("hex"));
  });
  it("binds starting infusions to weapon instances and shows their attack penalties", () => {
    for (const id of [7120000, 7120100, 7120200, 7120300]) {
      const detail = effectDetail(id)!;
      expect(detail.blocks[0].values[0]).toEqual(["物理攻击力", "-30／-40／-50／-60"]);
      expect(detail.blocks[0].values[1][1]).toBe("+33／+44／+55／+66");
      expect(detail.stacking).toBe("不可叠加");
      expect(detail.stackingDetail).toBe("出击武器的属性／异常附加只生效一种");
    }
    for (const [id, label, amount] of [[7120400, "基础冻伤累积", "35"], [7120500, "基础中毒累积", "35"], [7120600, "基础出血累积", "25"]] as const) {
      const detail = effectDetail(id)!;
      expect(detail.blocks[0].values).toEqual([["攻击力", "-15%"]]);
      expect(detail.blocks[1].values).toEqual([[label, amount]]);
      expect(detail.blocks.every((b) => b.duration === null && b.interval === null)).toBe(true);
    }
    for (const row of startingWeapon.checks.assignment)
      expect(row.attached).toBe(row.containerOrder.at(-1) ?? -1);
    for (const row of startingWeapon.checks.component.filter((r) => "repeat" in r)) {
      expect(row.repeat).toEqual([]);
      expect(row.afterUnequip).toEqual([]);
    }
    for (const row of startingWeapon.checks.binding.filter((r) => !r.residentLevels.includes(r.weaponLevel))) {
      expect(row.points).toEqual([0, 0, 0, 0, 0]);
      expect(row.rates).toEqual([1, 1, 1, 1, 1]);
    }
    expect(startingWeapon.checks.status.filter((r) => r.attached === -1).every((r) => !r.effects.length)).toBe(true);
    expect(startingWeapon.gameplayVerified).toBe(false);
    expect(research.startingWeaponEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-starting-weapon-evidence.json", import.meta.url)),
    ).digest("hex"));
  });
  it("binds Guardian tornado lifetimes to the actual held and early-release branches", () => {
    const detail = effectDetail(7011000)!;
    expect(detail.blocks[0].values).toEqual([["正常释放", "1 → 7 秒"], ["提前松开按键", "1 → 4 秒"]]);
    expect(detail.stacking).toBe("不可叠加");
    expect(duration.states.map((r) => r.animation)).toEqual(["a901_510000", "a901_510005"]);
    for (const row of duration.checks.lifetime)
      expect(Math.abs(row.expiresFrame / row.fps - row.seconds)).toBeLessThanOrEqual(1.01 / row.fps);
    for (const row of duration.checks.dispatch) {
      const eligible = row.active && (row.judge >= 6084 ? row.copies : row.base && !row.copies);
      expect(row.requests.length).toBe(eligible ? 1 : 0);
    }
    for (const row of duration.checks.script) {
      if (row.interrupt) expect(row.result).toBe("");
      else if (!row.l2 && !row.skill && row.releaseWindow) expect(row.result).toBe("W_WindAttackCancelEarly");
      else expect(row.result).toBe(row.ended ? "W_Idle" : "");
    }
    // History expiry alone does not prove complete collision cadence.
    expect(JSON.stringify(detail)).not.toContain("0.5");
    expect(duration.gameplayVerified).toBe(false);
    expect(research.guardianDurationEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-guardian-duration-evidence.json", import.meta.url)),
    ).digest("hex"));
  });
  it("ties Duchess invulnerability to the actual skill script and conditional animation flag", () => {
    const detail = effectDetail(6500300)!;
    expect(detail.blocks[0].values).toEqual([["无敌时间", "0.4 秒"]]);
    expect(detail.stacking).toBe("不可叠加");
    expect(detail.stackingDetail).toBe("再次触发刷新时长");
    expect(evasion.checks.script).toHaveLength(33);
    expect(evasion.checks.dispatch).toHaveLength(25);
    for (const row of evasion.checks.dispatch) {
      expect(row.flags).toBe(row.leaves && !row.elapsed ? 2 : 0);
    }
    for (const row of evasion.checks.lifecycle.filter((r) => r.copies === 1)) {
      const duplicate = evasion.checks.lifecycle.find((r) => r.copies === 3 && r.fps === row.fps && r.reapplyAt === row.reapplyAt)!;
      expect(duplicate.activeFrames).toEqual(row.activeFrames);
      expect(Math.abs(row.activeFrames.length / row.fps - row.expectedDuration)).toBeLessThanOrEqual(3.01 / row.fps);
    }
    expect(evasion.gameplayVerified).toBe(false);
    expect(research.duchessEvasionEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-duchess-evasion-evidence.json", import.meta.url)),
    ).digest("hex"));
  });
  it("distinguishes repeated equipment from independent Executor ability activations", () => {
    const heal = effectDetail(6500700)!;
    expect(heal.blocks[0].values).toEqual([["HP 恢复", "最大值的 0.27% + 3"]]);
    expect(heal.blocks[0].duration).toBe(60);
    expect(heal.blocks[0].interval).toBe(1);
    expect(heal.stacking).toBe("不可叠加");
    expect(heal.notes.join()).toContain("恢复量相加、分别计时");
    const single = tenacity.checks.lifecycle.find((r) => r.recoveryCopies === 1 && r.boostCopies === 1 && r.arrivals.join() === "0" && r.fps === 10)!;
    const duplicate = tenacity.checks.lifecycle.find((r) => r.recoveryCopies === 3 && r.arrivals.join() === "0")!;
    expect(single.heals).toEqual(duplicate.heals);
    expect(single.attackChanges).toEqual(duplicate.attackChanges);
    for (const row of tenacity.checks.lifecycle.filter((r) => r.arrivals.join() === "0,50")) {
      expect(row.heals.some((h) => h.hp.join() === "-0.54,-6")).toBe(true);
      expect(row.attackChanges.some((a) => Math.abs(a.rates[0] - 1.5876) < 0.00001)).toBe(true);
    }
    for (const row of tenacity.checks.hp)
      expect(row.packet[0]).toBe(Math.trunc(row.maximum * 0.0027 + 3));
  });
  it("gates Executor ability dispatch by native hero identity and keeps the resistance penalty passive", () => {
    expect(tenacity.checks.trigger).toHaveLength(99);
    for (const row of tenacity.checks.trigger)
      expect(row.emitted).toEqual(row.hero === 8 && row.expiredIds.join() !== "100" ? [707070, 7501000] : []);
    for (const row of tenacity.checks.resistance)
      expect(row.values).toEqual(Array(7).fill(row.copies ? -80 : 0));
    for (const id of [7034800, 7034801]) {
      const detail = effectDetail(id)!;
      expect(detail.blocks[0].values).toEqual([["异常状态抵抗力", "-80"]]);
      expect(detail.blocks[0].duration).toBeNull();
      expect(detail.blocks[1].values).toEqual([["能力的攻击倍率", "+20% → +26%"]]);
      expect(detail.blocks[1].duration).toBe(20);
      expect(detail.stacking).toBe("不可叠加");
      expect(detail.notes.join()).toContain("倍率相乘、分别计时");
    }
    expect(research.executorTenacityEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-executor-tenacity-evidence.json", import.meta.url)),
    ).digest("hex"));
    expect(tenacity.gameplayVerified).toBe(false);
  });
  it("separates Guardian protection lifetime from the emitter and refreshes without multiplying", () => {
    const detail = effectDetail(6500100)!;
    expect(detail.blocks[0].values).toEqual([["承伤倍率", "-18%"]]);
    expect(detail.blocks[0].restrictions).toContain("自身及周围友方 · 半径 8 米");
    expect(detail.blocks[0].duration).toBe(30);
    expect(detail.stacking).toBe("不可叠加");
    expect(detail.stackingDetail).toBe("同类效果再次施加刷新时长");
    for (const c of protection.checks.trigger)
      expect(c.requests).toHaveLength(c.equipmentCopies && c.active ? 1 : 0);
    for (const c of protection.checks.emission) expect(c.emissions).toEqual([0]);
    for (const c of protection.checks.lifecycle) {
      expect(c.changes).toHaveLength(2);
      expect(c.changes[0].incoming).toEqual([.82, .82, .82, .82, .82]);
      expect(Math.abs(c.changes[1].tick * c.dt - (Math.max(...c.arrivals) * c.dt + 30))).toBeLessThanOrEqual(.5);
    }
    expect(research.guardianProtectionEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-guardian-protection-evidence.json", import.meta.url)),
    ).digest("hex"));
    expect(protection.gameplayVerified).toBe(false);
  });
  it("requires a prayer animation grant and keeps the unconnected distant-heal slot unresolved", () => {
    const detail = effectDetail(7037000)!;
    expect(detail.blocks[0].values).toEqual([["物理攻击倍率", "+19%"]]);
    expect(detail.blocks[0].duration).toBe(60);
    expect(detail.stacking).toBe("不可叠加");
    expect(detail.stackingDetail).toBe("再次触发刷新时长");
    expect(detail.notes.join()).toContain("恢复类祷告和武器附魔也可触发");
    expect(detail.notes.join()).toContain("远方之恢复的触发待确认");
    expect(prayer.families.filter((f) => !f.events.length).map((f) => f.magic)).toEqual([2006400]);
    for (const c of prayer.checks.dispatch) {
      expect(c.grants).toEqual(c.active ? [7037001] : []);
      expect(c.rates[0]).toBeCloseTo(c.active && c.copies ? 1.19 : 1);
      expect(c.rates.slice(1)).toEqual([1, 1, 1, 1]);
    }
    for (const c of prayer.checks.lifecycle) {
      expect(c.changes).toHaveLength(c.copies ? 2 : 1);
      if (c.copies) {
        expect(c.changes[0].rates).toEqual([1.19, 1, 1, 1, 1]);
        expect(Math.abs(c.changes[1].tick * c.dt - (Math.max(...c.casts) * c.dt + 60))).toBeLessThanOrEqual(.5);
      }
    }
    expect(research.undertakerPrayerEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-undertaker-prayer-evidence.json", import.meta.url)),
    ).digest("hex"));
    expect(prayer.gameplayVerified).toBe(false);
  });
  it("restricts Executor's bonus to tagged skill attacks and keeps the hit penalty after sheathing", () => {
    const detail = effectDetail(7034400)!;
    expect(detail.blocks.map((b) => b.values)).toEqual([
      [["攻击倍率", "+35%"]], [["承伤倍率", "+40%"]],
    ]);
    expect(detail.blocks.map((b) => b.duration)).toEqual([null, 5]);
    expect(detail.notes.join()).toContain("前段不适用，后段适用");
    expect(detail.notes.join()).toContain("收刀不会提前解除");
    expect(detail.stacking).toBe("不可叠加");
    const cases = Object.fromEntries(blade.checks.lifecycle.map((c) => [c.name, c]));
    expect(cases["no-equipment"].changes).toEqual([{ frame: 0, attack: 1, incoming: [1, 1, 1, 1, 1] }]);
    expect(cases["one-hit"].changes).toEqual(cases["duplicate-equipment"].changes);
    expect(cases["after-sheathing"].grants.at(-1)!.ids).toEqual([]);
    expect(cases["one-hit"].changes.some((c) => c.attack === 1 && c.incoming.every((v) => v === 1.4))).toBe(true);
    expect(cases["repeat-hit"].changes.at(-1)!.frame - cases["one-hit"].changes.at(-1)!.frame).toBe(60);
    for (const c of blade.checks.attackRows)
      expect(c.rate).toBeCloseTo(c.tags.includes(122) ? 1.35 : 1);
    expect(blade.checks.attackRows.filter((c) => c.rate === 1).map((c) => c.attack)).toEqual([960325]);
    for (const c of blade.checks.penalty) {
      expect(c.changes).toHaveLength(2);
      expect(c.changes[0].incoming).toEqual([1.4, 1.4, 1.4, 1.4, 1.4]);
      expect(c.changes[1].frame / c.fps).toBeCloseTo(Math.max(...c.arrivals) / c.fps + 5, 1);
    }
    expect(research.executorBladeEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-executor-blade-evidence.json", import.meta.url)),
    ).digest("hex"));
    expect(blade.gameplayVerified).toBe(false);
  });
  it("resolves both Guardian skill aliases and preserves overlapping heal arrival behavior", () => {
    const detail = effectDetail(7011100)!;
    expect(detail).toEqual(effectDetail(7011101));
    expect(detail.blocks).toHaveLength(1);
    expect(detail.blocks[0].values).toEqual([["HP 恢复", "最大值的 15%"]]);
    expect(detail.blocks[0].restrictions).toContain("自身及周围友方 · 半径 8 米");
    expect(detail.blocks[0].duration).toBeNull();
    expect(detail.blocks[0].interval).toBeNull();
    expect(detail.stacking).toBe("不可叠加");
    expect(detail.notes.join()).toContain("可能合并或延后恢复");
    for (const c of guardianSkill.checks.trigger)
      expect(c.requests).toHaveLength(c.equipmentCopies && c.active ? 1 : 0);
    for (const c of guardianSkill.checks.emissionAndRecovery) {
      expect(c.emissions).toEqual([0]);
      expect(c.heals).toEqual([{ frame: 1, hp: [-15, 0] }]);
    }
    for (const c of guardianSkill.checks.hp)
      expect(c.packet[0]).toBe(Math.trunc(c.maximum * .15));
    expect(guardianSkill.checks.arrival.map((c) => c.heals.map((h) => h.frame)))
      .toEqual([[0], [0], [0], [0, 13], [0, 12], [0, 13, 25, 37]]);
    expect(research.guardianSkillEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-guardian-skill-evidence.json", import.meta.url)),
    ).digest("hex"));
    expect(guardianSkill.gameplayVerified).toBe(false);
  });
  it("keeps held gesture buildup separate from madness onset and distinguishes the two versions", () => {
    for (const id of [7035400, 7035410]) {
      const detail = effectDetail(id)!;
      expect(detail.blocks[0].values).toEqual([["基础发狂累积", "10"]]);
      expect(detail.blocks[0].restrictions).toContain("约每 0.1 秒累积一次");
      expect(detail.blocks[1].values).toEqual([["基础 HP 损失", "最大值的 10% + 100"], ["FP 损失", "30"]]);
      expect(detail.blocks.every((b) => b.duration === null)).toBe(true);
      expect(detail.stacking).toBe("可叠加");
      expect(detail.stackingDetail).toBe("不同版本的累积相加；同版重复无效");
    }
    for (const fps of [30, 60, 120]) {
      const cases = gesture.checks.cadence.filter((c) => c.fps === fps);
      expect(cases[1].attempts).toEqual(cases[2].attempts);
      expect(cases[3].attempts).toEqual(cases[4].attempts);
      expect(cases[5].attempts).toEqual(cases[6].attempts);
      expect(cases[5].attempts).toHaveLength(cases[1].attempts.length * 2);
      for (const c of cases) {
        expect(c.resources).toEqual([]);
        expect(c.remaining).toBe(c.startingResistance - c.attempts.length * 10);
      }
    }
    for (const c of gesture.checks.onset) {
      expect(c.resources).toHaveLength(c.immune ? 0 : 1);
      if (c.immune) expect(c.remaining).toBe(c.startingResistance);
      else expect(c.resources[0]).toMatchObject({ hp: -200, fp: -30 });
    }
    for (const c of gesture.checks.resources) {
      expect(c.packet[0]).toBe(-Math.trunc(c.maximum * .1 + 100));
      expect(c.fp).toEqual([-30, 0]);
    }
    expect(research.gestureMadnessEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-gesture-madness-evidence.json", import.meta.url)),
    ).digest("hex"));
    expect(gesture.gameplayVerified).toBe(false);
  });
  it("separates Revenant's one-shot sacrifice and ally heal from continuous revival recovery", () => {
    const detail = effectDetail(7010900)!;
    expect(detail).toEqual(effectDetail(16002));
    expect(detail.blocks.map((b) => b.values)).toEqual([
      [["HP 损失", "最大值的 50%"]], [["HP 恢复", "最大值的 100%"]],
      [["每次 HP 恢复", "最大值的 100%"]],
    ]);
    expect(detail.blocks.map((b) => b.duration)).toEqual([null, null, .5]);
    expect(detail.blocks[1].restrictions).toContain("半径 30 米 · 不含自身");
    expect(detail.blocks[2].restrictions).toContain("持续恢复");
    expect(detail.stacking).toBe("不可叠加");
    for (const c of sacrifice.checks.trigger)
      expect(c.requests).toHaveLength(c.equipmentCopies && c.active ? 1 : 0);
    for (const c of sacrifice.checks.emission) {
      expect(c.attempts).toEqual([0]);
      expect(c.shooterEffects).toEqual(c.success ? [7010901] : []);
    }
    for (const c of sacrifice.checks.hp)
      expect(c.packet[0]).toBe(c.leaf === 7010901 ? (-Math.trunc(c.maximum * .5) || 0) : c.maximum);
    for (const c of sacrifice.checks.lifecycle) {
      if (c.name === "revival") {
        expect(c.restores.length).toBeGreaterThanOrEqual(c.fps / 2);
        expect(c.restores.every((r) => r.delta === 1000)).toBe(true);
        expect(c.restores.at(-1)!.frame / c.fps).toBeLessThanOrEqual(.5 + 2 / c.fps + 1e-6);
      } else {
        expect(c.restores).toHaveLength(["sacrifice", "ally"].includes(c.name) ? 1 : 0);
      }
      expect(c.remaining.map((n) => n.id)).toEqual(c.name === "duplicate-marker" ? [7010905] : []);
    }
    for (const c of sacrifice.checks.script) {
      if (c.function === "NearDeathRevival_onActivate")
        expect(c.emitted).toEqual(c.markerPresent ? [7010906] : []);
      else expect(c.emitted).toContain(7010909);
    }
    expect(research.revenantSacrificeEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-revenant-sacrifice-evidence.json", import.meta.url)),
    ).digest("hex"));
    expect(sacrifice.gameplayVerified).toBe(false);
  });
  it("requires actual self-bleed onset and separates HP loss from independently expiring attack buffs", () => {
    const detail = effectDetail(7032900)!;
    expect(detail).toEqual(effectDetail(17002));
    expect(detail.blocks.map((b) => b.values)).toEqual([
      [["基础 HP 损失", "最大值的 20%"]], [["攻击倍率", "+16%"]],
    ]);
    expect(detail.blocks.map((b) => b.duration)).toEqual([null, 30]);
    expect(detail.blocks[0].restrictions).toContain("自伤可使 HP 归零");
    expect(detail.notes.join()).toContain("免疫时也不会获得增攻");
    expect(detail.notes.join()).toContain("两次合计 +34.56%");
    expect(detail.stacking).toBe("不可叠加");
    for (const c of recluseBleed.checks.onset) {
      expect(c.rejected).toBe(c.immune || c.startingResistance > 9999);
      expect(c.attack).toBeCloseTo(c.rejected ? 1 : 1.16);
      if (c.rejected) expect(c.grants).toEqual([]);
    }
    for (const c of recluseBleed.checks.hp) {
      expect(c.packet[0]).toBe(-Math.trunc(c.maximum * .2));
      expect(c.after).toBe(Math.max(0, c.current + c.packet[0]));
    }
    const cases = recluseBleed.checks.lifecycle;
    for (const name of ["no-equipment", "immune", "below-onset"]) {
      const c = cases.find((c) => c.name === name)!;
      expect(c.damage).toEqual([]);
      expect(c.attackChanges).toEqual([]);
    }
    const repeat = cases.find((c) => c.name === "repeat")!;
    const duplicate = cases.find((c) => c.name === "duplicate-equipment")!;
    expect(duplicate.damage).toEqual(repeat.damage);
    expect(duplicate.attackChanges).toEqual(repeat.attackChanges);
    expect(repeat.attackChanges.map((r) => r.count)).toEqual([1, 2, 1, 0]);
    for (const r of repeat.attackChanges) expect(r.rate).toBeCloseTo(1.16 ** r.count);
    const later = cases.find((c) => c.name === "later-onset")!;
    expect(later.attempts.map((r) => r.rejected)).toEqual([true, false]);
    expect(later.damage).toHaveLength(1);
    expect(later.attackChanges.map((r) => r.count)).toEqual([1, 0]);
    expect(research.recluseBleedEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-recluse-bleed-evidence.json", import.meta.url)),
    ).digest("hex"));
    expect(recluseBleed.gameplayVerified).toBe(false);
  });
  it("filters weapon recovery with actual source weapons and rejects duplicate restores before expiry", () => {
    for (const f of weaponRecovery.families) {
      const detail = effectDetail(f.effect)!;
      expect(detail.stacking).toBe(f.nativeTypeAccepted ? "不可叠加" : "待确认");
      expect(detail.blocks[0].duration).toBeNull();
      expect(detail.blocks[0].interval).toBeNull();
      expect(detail.blocks[0].restrictions.join()).toContain("连续命中不会延长间隔");
      expect(detail.blocks[0].restrictions.join()).not.toContain("1.1");
      if (!f.nativeTypeAccepted) expect(detail.notes).toContain("实际触发待确认。");
      for (const r of weaponRecovery.checks.filter.filter((r) => r.effect === f.effect)) {
        expect(r.matched).toEqual(f.nativeTypeAccepted ? [f.leaf] : []);
        expect(r.mismatched).toEqual([]);
        expect(r.excludedFlag).toEqual([]);
        expect(r.excludedCategory).toEqual([]);
      }
    }
    expect(weaponRecovery.nativeOnlyTypeFailures).toEqual([
      7342500, 7342600, 7342700, 7342800, 7352500, 7352600, 7352700, 7352800,
    ]);
    expect(weaponRecovery.checks.reapplication).toHaveLength(62);
    for (const r of weaponRecovery.checks.reapplication) {
      expect(r.rejectedResult).toBe(0xfffffffe);
      expect(r.after).toEqual(r.before);
      expect(evidence.recoveryTiming[String(r.leaf) as keyof typeof evidence.recoveryTiming].repeatedApplication).toBe("ignored");
    }
    for (const r of weaponRecovery.checks.timing) {
      expect(r.restores).toHaveLength(r.continuous ? 4 : 1);
      const single = weaponRecovery.checks.timing.find((c) => c.effect === r.effect && c.hitEvery === r.hitEvery && c.copies === 1)!;
      expect(r.restores).toEqual(single.restores);
    }
    for (const r of weaponRecovery.checks.mixed) {
      expect(r.hp).toEqual([0, -15]);
      expect(r.fp).toEqual([2, 0]);
    }
    expect(research.weaponRecoveryEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-weapon-recovery-evidence.json", import.meta.url)),
    ).digest("hex"));
    expect(weaponRecovery.gameplayVerified).toBe(false);
    expect(weaponRecovery.mmvDllsExecuted).toBe(false);
  });
  it("recovers once per Executor unlock and re-arms through the actual reset chain", () => {
    const detail = effectDetail(7034500)!;
    expect(detail.blocks[0].values).toEqual([["HP 恢复", "最大值的 5% + 100"]]);
    expect(detail.blocks[0].duration).toBeNull();
    expect(detail.blocks[0].interval).toBeNull();
    expect(detail.notes.join()).toContain("维持解放状态不会反复恢复");
    expect(detail.stacking).toBe("不可叠加");
    for (const c of executorRecovery.checks.filter((c) => c.name === "threshold")) {
      const amount = executorRecovery.rows[String(c.incrementEffect) as keyof typeof executorRecovery.rows].accumuVal;
      expect(c.heals).toHaveLength(c.equipmentCopies && amount * c.count >= 50 ? 1 : 0);
      if (c.heals.length) expect(c.heals[0].hp).toEqual([-5, -100]);
    }
    for (const name of ["already-unlocked", "reset-and-repeat", "reset-warmup"]) {
      const cases = executorRecovery.checks.filter((c) => c.name === name);
      expect(cases.map((c) => c.equipmentCopies)).toEqual([1, 3]);
      expect(cases[0].heals).toEqual(cases[1].heals);
      expect(cases[0].heals).toHaveLength(name === "reset-and-repeat" ? 2 : 1);
    }
    expect(executorRecovery.events.every((e) => e.Type === 67)).toBe(true);
    expect(research.executorRecoveryEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-executor-recovery-evidence.json", import.meta.url)),
    ).digest("hex"));
    expect(executorRecovery.gameplayVerified).toBe(false);
  });
  it("distinguishes Guardian healing cadence from bullet emissions and the recipient lease", () => {
    for (const id of [12002, 12003, 7012000]) {
      const detail = effectDetail(id)!;
      expect(detail.blocks[0].values).toEqual([["HP 恢复", "最大值的 10% + 12"]]);
      expect(detail.blocks[0].restrictions).toContain("自身及周围友方 · 半径 15 米");
      expect(detail.blocks[0].duration).toBeNull();
      expect(detail.blocks[0].interval).toBeNull();
      expect(detail.notes.join()).toContain("约每秒恢复一次");
      expect(detail.notes.join()).toContain("尚未到期的效果仍可能再恢复一次");
      expect(detail.stacking).toBe("不可叠加");
    }
    for (const r of recovery.checks.trigger) {
      expect(r.requests).toHaveLength(r.equipmentCopies ? 1 : 0);
      if (r.equipmentCopies) expect(r.requests[0].active).toBe(Boolean(r.active));
    }
    for (const r of recovery.checks.emissionAndRecovery) {
      expect(r.emissions).toHaveLength(10);
      expect(r.heals).toHaveLength(4);
      expect(r.maximumRecipientNodes).toBe(1);
      expect(r.finalNodes).toEqual([]);
      expect(r.heals.at(-1)!.frame / r.fps).toBeGreaterThan(r.sourceStopsAt);
      for (const h of r.heals) expect(h.hp).toEqual([-10, -12]);
      const single = recovery.checks.emissionAndRecovery.find((c) => c.fps === r.fps && c.simultaneousSources === 1)!;
      expect(r.heals).toEqual(single.heals);
    }
    expect(recovery.checks.arrival.map((r) => r.heals.map((h) => h.frame)))
      .toEqual([[0], [0], [0, 60], [0, 61]]);
    expect(research.recoveryEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-recovery-evidence.json", import.meta.url)),
    ).digest("hex"));
    expect(recovery.gameplayVerified).toBe(false);
  });
  it("separates Revenant's fixed rearm schedule, one-shot FP and independent attack buffs", () => {
    const detail = effectDetail(7220200)!;
    expect(detail).toEqual(effectDetail(7220201));
    expect(detail.blocks.map((b) => b.values)).toEqual([
      [["攻击倍率", "+15%"]], [["FP 恢复", "最大值的 10%"]],
    ]);
    expect(detail.blocks.map((b) => b.duration)).toEqual([20, null]);
    expect(detail.blocks.every((b) => b.interval === null)).toBe(true);
    expect(detail.stacking).toBe("不可叠加");
    expect(detail.notes.join()).toContain("未消耗的机会在窗口结束时结算");
    expect(detail.notes.join()).toContain("+32.25%");
    const cases = lifecycle.checks.revenant;
    expect(cases.find((c) => c.name === "no-equipment")!.restores).toEqual([]);
    const edge = cases.find((c) => c.name === "rearm-boundary")!;
    expect(edge.restores).toHaveLength(2);
    expect(edge.restores[1].frame - edge.restores[0].frame).toBeLessThan(edge.fps / 2);
    expect(cases.find((c) => c.name === "duplicate-equipment")!.restores).toEqual(edge.restores);
    expect(cases.find((c) => c.name === "no-damage")!.restores).toHaveLength(1);
    expect(cases.find((c) => c.name === "zero-damage")!.restores).toEqual(cases.find((c) => c.name === "no-damage")!.restores);
    expect(cases.find((c) => c.name === "independent-expiry")!.attackChanges.map((c) => c.count)).toEqual([1, 2, 3, 2]);
    expect(lifecycle.checks.fp.find((c) => c.copies === 1 && c.maximum === 137)!.first).toEqual([13, 0]);
    expect(lifecycle.checks.fp.every((c) => c.nextFrame.every((v) => v === 0))).toBe(true);
    expect(research.lifecycleEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-lifecycle-evidence.json", import.meta.url)),
    ).digest("hex"));
    expect(lifecycle.gameplayVerified).toBe(false);
  });
  it("keeps Duchess's kill branches separate and preserves independent expiry", () => {
    const detail = effectDetail(7032700)!;
    expect(detail.blocks[0].values).toEqual([["攻击倍率", "+5% 或 +15%"]]);
    expect(detail.blocks[0].duration).toBe(30);
    expect(detail.notes.join()).toContain("12.5 秒");
    expect(detail.stacking).toBe("不可叠加");
    for (const special of [0, 1]) {
      const cases = lifecycle.checks.duchess.filter((c) => c.special === special);
      expect(cases.find((c) => c.name === "no-equipment")!.attackChanges).toEqual([]);
      expect(cases.find((c) => c.name === "after-window")!.attackChanges).toEqual([]);
      const repeat = cases.find((c) => c.name === "repeat-kill")!;
      expect(repeat.attackChanges.at(-1)!.rate).toBeCloseTo((special ? 1.05 : 1.15) ** 2);
      expect(cases.find((c) => c.name === "duplicate-equipment")!.attackChanges).toEqual(repeat.attackChanges);
      expect(cases.find((c) => c.name === "independent-expiry")!.attackChanges.map((c) => c.count)).toEqual([1, 2, 1]);
    }
  });
  it("preserves Recluse's two-stage HP buff instead of showing a fixed 30-second expiry", () => {
    const detail = effectDetail(7034100)!;
    expect(detail.blocks).toHaveLength(1);
    expect(detail.blocks[0].values).toEqual([["血量上限", "+50%"]]);
    expect(detail.blocks[0].duration).toBeNull();
    expect(detail.notes.join()).toBe("前约 30 秒不因受损结束；之后持续至下次受到损伤。");
    expect(detail.stacking).toBe("不可叠加");
    const damage = evidence.roleLifecycle.filter((r) => "damage" in r);
    expect(damage.filter((r) => r.id === 7034102 || r.id === 7034103).every((r) => !r.expired)).toBe(true);
    expect(damage.filter((r) => r.id === 7034104).every((r) => r.expired === (r.damage! > 0))).toBe(true);
    const transition = evidence.roleLifecycle.find((r) => "lifetime" in r && r.id === 7034103)!;
    expect(transition.expiredAt).toBeCloseTo(29.95, 2);
    const after = evidence.roleLifecycle.find((r) => "lifetime" in r && r.id === 7034104)!;
    expect(after.expiredAt).toBeNull();
    expect(triggers.roots["7034100"].seeds).toEqual([7034101, 7034103]);
  });
  it("uses start-only animation grants without truncating role buffs to the event window", () => {
    for (const id of [7033300, 7033301]) {
      const d = effectDetail(id)!;
      expect(d.blocks[0].values).toEqual([["攻击倍率", "+20%"], ["精力上限", "+20%"], ["承伤倍率", "+20%"]]);
      expect(d.blocks[0].duration).toBe(40);
      expect(d.stacking).toBe("不可叠加");
    }
    const ult = effectDetail(7036800)!;
    expect(ult.blocks[0].values).toEqual([["攻击倍率", "+18%"]]);
    expect(ult.blocks[0].duration).toBe(40);
    expect(ult.blocks[0].scope).toEqual([]);
    expect(ult.stacking).toBe("不可叠加");
    for (const id of [7033500, 7033501]) {
      const d = effectDetail(id)!;
      expect(d.blocks[0].values).toEqual([["攻击倍率", "+10%"]]);
      expect(d.blocks[0].duration).toBe(10);
      expect(d.stacking).toBe("不可叠加");
      expect(d.stackingDetail).toContain("重复装备不增加单次触发收益");
      expect(d.notes.join()).toContain("两次触发合计 +21%");
      expect(research.effects[String(id) as keyof typeof research.effects].openQuestions.join()).toContain("实例容量上限");
    }
    expect(evidence.skillStack).toHaveLength(9);
    for (const r of evidence.skillStack) {
      const leaves = r.nodes.filter((n) => n.id === 7020201);
      expect(leaves.map((n) => n.lifetime)).toEqual(r.markers ? [...Array(r.copies).fill(3), 10] : [0]);
      for (const rate of r.rates) expect(rate).toBeCloseTo(r.markers ? 1.1 ** (r.copies + 1) : 1, 6);
    }
    expect(evidence.actionStart).toHaveLength(12);
    for (const r of evidence.actionStart) expect(r.emitted).toEqual(r.active ? [r.leaf] : []);
    expect(evidence.actionValues.filter((r) => "refreshedDuration" in r).map((r) => r.refreshedDuration)).toEqual([40, 40]);
    expect(triggers.roots["7036800"].events["7036801"].every((r) => r.type === 302 && r.end < .04)).toBe(true);
  });
  it("distinguishes the totem lifetime, recipient buffs and instantaneous healing", () => {
    for (const id of [7310000, 15000]) {
      const detail = effectDetail(id)!;
      expect(detail.blocks[0].values).toEqual([
        ["图腾持续时间", "20 → 30 秒"],
        ["攻击增益持续时间", "30 → 45 秒"],
      ]);
      expect(detail.blocks[0].duration).toBeNull();
      expect(detail.stacking).toBe("不可叠加");
    }
    const poise = effectDetail(7030000)!;
    expect(poise.blocks[0].values).toEqual([["强韧度损耗", "-90%"]]);
    expect(poise.blocks[0].duration).toBe(20);
    expect(poise.notes.join()).toContain("30 秒");
    for (const id of [7090300, 15002]) {
      const detail = effectDetail(id)!;
      expect(detail.blocks[0].values).toEqual([["HP", "+20% 或 +50% 最大 HP"]]);
      expect(detail.blocks[0].duration).toBeNull();
      expect(detail.blocks[0].interval).toBeNull();
      expect(detail.blocks[0].restrictions).toContain("恢复量随敌人类型变化");
      expect(detail.stackingDetail).toContain("覆盖并刷新");
    }
    // Timer fade must not be included in the gameplay field duration.
    expect(totem.checks.timer.filter((r) => r.dt === r.life).every((r) => !r.deleted && r.remaining === .5)).toBe(true);
    expect(totem.checks.timer.filter((r) => r.dt >= r.life + .5).every((r) => r.deleted)).toBe(true);
    expect(totem.checks.matching.every((r) => r.active === r.incoming)).toBe(true);
    expect(totem.checks.killDispatch.filter((r) => !r.flags).every((r) => r.emitted.length === 1)).toBe(true);
    expect(totem.gameplayVerified).toBe(false);
    expect(research.totemEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-totem-evidence.json", import.meta.url)),
    ).digest("hex"));
  });
  it("describes weapon bias replacement without inventing a fixed percentage", () => {
    for (let id = 6630000; id <= 6633600; id += 100) {
      const detail = effectDetail(id)!;
      expect(detail.blocks).toHaveLength(1);
      expect(detail.blocks[0].source).toBe(id + 1000000);
      expect(detail.blocks[0].values).toEqual([
        ["武器倾向", catalog.effects[id].name.zh_CN.replace("通过潜在能力，能比较容易找到", "")],
      ]);
      expect(detail.blocks[0].restrictions).toContain("替换角色默认倾向");
      expect(detail.blocks[0].duration).toBeNull();
      expect(detail.notes.join()).toContain("具体概率随奖池和候选权重变化");
      expect(detail.stacking).toBe("不可叠加");
      expect(JSON.stringify(detail)).not.toContain("%");
    }
    expect(research.effects["6632300"].values).toBe("decoded-mechanism");
    expect(research.coverage.withMechanicsOnly).toBe(39);
    expect(research.coverage.withNumericFields).toBe(554);
    expect(research.discoveryEvidenceSha256).toBe(createHash("sha256").update(
      readFileSync(new URL("../../data/effect-discovery-evidence.json", import.meta.url)),
    ).digest("hex"));
    expect(discovery.regulationSha256).toBe(catalog.regulationSha256);
    expect(discovery.gameplayVerified).toBe(false);
  });
  it("preserves repeated ItemTable IDs and native first-bias selection across all heroes", () => {
    expect(discovery.rowCount).toBe(35755);
    expect(discovery.groupCount).toBe(3627);
    expect(discovery.biasedGroups).toHaveLength(39);
    const rows = discovery.rows.filter((r) => r.id === 3000200);
    expect(rows.length).toBeGreaterThan(100);
    expect(new Set(rows.map((r) => r.index)).size).toBe(rows.length);
    const firstBias = discovery.selection.filter((r) => r.ids.length === 2);
    expect(firstBias.map((r) => r.bias)).toEqual([51, 57, 51, 51]);
    for (const hero of new Set(discovery.selection.map((r) => r.hero))) {
      expect(discovery.selection.find((r) => r.hero === hero && !r.ids.length)!.bias).toBe(1000 + hero * 100);
      expect(discovery.selection.find((r) => r.hero === hero && r.ids[0] === 7632300)!.bias).toBe(51);
    }
    // A new weapon type has no candidate in some older pools. Generic pools
    // remain unchanged; the UI must not promise a universal chance or fallback.
    const missing = discovery.draws.find((r) => r.group === 3000250 && r.bias === 93)!;
    expect(missing.totalWeight).toBe(0);
    expect(missing.selectedIndex).toBeNull();
    const generic = discovery.draws.filter((r) => r.group === 2003002);
    expect(new Set(generic.map((r) => r.totalWeight))).toEqual(new Set([21000]));
    expect(new Set(generic.map((r) => r.selectedIndex)).size).toBe(1);
    const gated = discovery.draws.filter((r) => r.group === 2000);
    expect(gated.map((r) => r.totalWeight)).toEqual([0, 0, 0, 100]);
  });
  it("distinguishes the magic field from its recipient lease and follows native last-hit replacement", () => {
    const detail = effectDetail(7032800)!;
    expect(detail.blocks).toHaveLength(1);
    expect(detail.blocks[0].values).toEqual([
      ["魔力攻击倍率", "+15%"],
      ["魔法阵持续时间", "30 秒"],
    ]);
    expect(detail.blocks[0].duration).toBeNull();
    expect(detail.blocks[0].restrictions).toContain("自身及周围友方 · 半径 4.2 米");
    expect(detail.notes.join()).toContain("1.5 秒");
    expect(detail.stacking).toBe("不可叠加");
    expect(detail.stackingDetail).toContain("不自动保留较强者");
    expect(scripts.effects["7032800"].cases).toHaveLength(32);
    expect(links.emitters["7032802"].pulseInterval).toBe(.5);
    for (const r of evidence.zoneMatching) {
      expect(r.activeId).toBe(r.incoming);
      expect(r.duration).toBe(1.5);
      expect(r.magicRate).toBeCloseTo(r.incoming === 7032803 ? 1.15 : 1.2);
    }
  });
  it("binds special-location growth to two independent ladders and actual counter grants", () => {
    const detail = effectDetail(7060000)!;
    expect(detail.blocks.map((b) => b.source)).toEqual([7069001, 7069021]);
    expect(detail.blocks.map((b) => b.values)).toEqual([
      [["每档攻击倍率", "约 +5%"]],
      [["每档攻击倍率", "约 +1.5%"]],
    ]);
    expect(detail.blocks[0].restrictions.join()).toContain("最多 3 档");
    expect(detail.blocks[1].restrictions.join()).toContain("拟态敌人最多计 2 档（需击败变身后的目标）");
    expect(detail.notes).toContain("两组成长可同时生效，倍率相乘。");
    expect(growth.roots["7060001"].sources.map((r) => [r.counter, r.grantsPerEvent]))
      .toEqual([[8145,3], [8155,2], [8135,2], [8140,1], [8180,8]]);
    expect(new Set(growth.producers.filter((r) => r.counter === 8180).map((r) => r.units)))
      .toEqual(new Set([1, 2]));
    expect(growth.transformations).toHaveLength(30);
    for (const r of growth.transformations) {
      const producer = growth.producers.find((p) => p.path === r.path && p.index === r.eventIndex)!;
      expect(r.target.EntityID).toBe(producer.arguments[3]);
      expect(r.original.EntityID).toBe(producer.arguments[2]);
      expect(r.target.EntityID).not.toBe(r.original.EntityID);
    }
    const both = evidence.locationValues.find((r) => "ids" in r)!;
    const first = evidence.locationValues.find((r) => r.id === 7069006)!;
    const second = evidence.locationValues.find((r) => r.id === 7069030)!;
    expect(both.rates[0]).toBeCloseTo(first.rates[0] * second.rates[0]);
  });
  it("uses current HP only for the guard counter's physical bonus", () => {
    expect(effectDetail(7150000)!.blocks[0].values).toEqual([["追加物理伤害基值", "当前 HP 的 5%"]]);
    expect(effectDetail(7150000)!.stacking).toBe("不可叠加");
    for (const r of evidence.guardCounter) {
      const bonus = r.tag === 103 && r.basePhysical >= 1 ? r.hp * .05 : 0;
      expect(r.scaledPhysical - r.basePhysical * r.systemScale).toBeCloseTo(bonus, 4);
      expect(r.values.slice(1)).toEqual([100, 100, 100, 100]);
    }
  });
  it("derives Scholar decay from the consumer and records ally grants separately from skill thresholds", () => {
    expect(effectDetail(7036200)!.blocks[0].values).toEqual([["进行率下降速度", "-62.5%"]]);
    expect(effectDetail(7036200)!.stacking).toBe("不可叠加");
    for (const r of evidence.scholarDecay)
      expect(r.remaining).toBeCloseTo(Math.max(0, 100 - r.dt * (r.ids.length ? 30 : 80)), 4);
    for (const id of [19001, 7036300]) {
      const detail = effectDetail(id)!;
      expect(detail.blocks[0].values).toEqual([["攻击倍率", "+15%"]]);
      expect(detail.blocks[0].duration).toBe(30);
      expect(detail.stacking).toBe("不可叠加");
    }
    for (const r of evidence.scholarAlly.filter((r) => "emitted" in r))
      expect(r.emitted).toEqual(r.ids!.length && r.eligibilityByte ? [7036301] : []);
  });
  it("retains effect-specific open questions instead of clearing them or leaking them into the next record", () => {
    expect(research.effects["7035700"].openQuestions).toContain("与其他附魔的覆盖顺序、武器适用条件及完整动作时序");
    expect(research.effects["7032800"].openQuestions).toContain("范围命中、多人来源叠加及再次发放时序");
    expect(research.effects["7000000"].openQuestions).not.toContain("范围命中、多人来源叠加及再次发放时序");
  });
  it("shows damage-triggered buildup without treating ailment onset damage as per-hit damage", () => {
    const cases = [
      [6820000, "中毒", 52],
      [6820100, "猩红腐败", 44],
      [6820200, "冻伤", 44],
      [6820300, "出血", 44],
      [6820400, "发狂", 40],
      [6820500, "催眠", 40],
      [6820600, "死亡", 32],
    ] as const;
    for (const [id, label, amount] of cases) {
      const detail = effectDetail(id)!;
      expect(detail.blocks).toHaveLength(1);
      expect(detail.blocks[0].values).toEqual([
        [label + "累积", `+${amount} 点／次`],
      ]);
      expect(detail.blocks[0].duration).toBeNull();
      expect(detail.blocks[0].interval).toBeNull();
      expect(detail.blocks[0].branches).toEqual([id + 1, id + 2]);
      const measured = evidence.damageStatus.find(
        (r) => r.root === id && "amount" in r,
      )!;
      expect(measured.amount).toBe(amount);
      expect(measured.remaining).toBe(1000 - amount);
      const triggers = evidence.damageStatus.filter(
        (r) => r.root === id && "damage" in r,
      );
      expect(triggers).toHaveLength(8);
      for (const r of triggers)
        expect(r.replaced).toBe(r.damage! > 0 && !r.excluded);
    }
  });
  it("covers the active catalog with pinned, finite, traceable parameters", () => {
    expect(source.hashes["regulation.bin"]).toBe(catalog.regulationSha256);
    const spells = source.spells as Record<string, Record<string, number>>;
    for (const id of Object.keys(catalog.effects).map(Number)) {
      const detail = effectDetail(id)!;
      expect(detail).toBeDefined();
      expect(["不可叠加", "可叠加", "不同等级可叠加", "待确认"]).toContain(
        detail.stacking,
      );
      expect(JSON.stringify(detail)).not.toContain("反馈");
      for (const block of detail.blocks) {
        expect(spells[String(block.source)]).toBeDefined();
        for (const branch of block.branches ?? [])
          expect(spells[String(branch)]).toBeDefined();
        expect(
          block.values.every(
            (v) => v.length === 2 && !/NaN|Infinity/.test(v[1]),
          ),
        ).toBe(true);
      }
    }
  });
  it("uses MMV spell and weapon-condition values without confusing damage channels", () => {
    const spell = effectDetail(6611202)!;
    expect(spell.blocks[0].values).toEqual([["攻击倍率", "+14%"]]);
    expect(spell.blocks[0].scope).toEqual(["魔法", "祷告"]);
    expect(effectDetail(7082400)!.blocks[0].values).toEqual([
      ["攻击倍率", "+20%"],
    ]);
    expect(effectDetail(7000000)!.blocks[0].values).toEqual([["生命力", "+1"]]);
  });
  it("retains conditional branches and does not sum kill notifications or promise unverified stacking", () => {
    const cocktail = effectDetail(7034200)!;
    expect(cocktail.blocks.map((b) => [b.linked, b.duration])).toEqual([
      [true, 3],
      [true, 3],
    ]);
    expect(cocktail.blocks[0].values).toContainEqual(["攻击倍率", "+35%"]);
    expect(cocktail.blocks[1].values).toContainEqual(["魔法 FP 消耗", "+30%"]);
    const kill = effectDetail(7090000)!;
    expect(kill.blocks.map((b) => b.phase)).toEqual(["打倒敌人时"]);
    expect(kill.blocks[0].values).toEqual([["绝招量表", "+1.65% 或 +5%"]]);
    expect(kill.stacking).toBe("不同等级可叠加");
    expect(effectDetail(6611202)!.stacking).toBe("可叠加");
    expect(effectDetail(6611202)!.stackingDetail).toBe("攻击倍率相乘");
    expect(effectDetail(999999998)).toBeUndefined();
  });
  it("records the whole catalog separately from obtainable relics, without claiming gameplay verification", () => {
    const ids = new Set(
      Object.values(catalog.relics)
        .filter((r) => r.obtainable)
        .flatMap((r) => r.pools.flatMap((p) => catalog.pools[p] ?? [])),
    );
    expect(
      Object.entries(research.effects)
        .filter(([, r]) => r.obtainable)
        .map(([id]) => Number(id))
        .sort(),
    ).toEqual([...ids].sort());
    expect(Object.keys(research.effects).sort()).toEqual(
      Object.keys(catalog.effects).sort(),
    );
    expect(research.coverage.catalog).toBe(2241);
    expect(research.regulationSha256).toBe(catalog.regulationSha256);
    expect(evidence.regulationSha256).toBe(catalog.regulationSha256);
    expect(research.nativeEvidenceSha256).toBe(
      createHash("sha256")
        .update(
          readFileSync(
            new URL("../../data/effect-native-evidence.json", import.meta.url),
          ),
        )
        .digest("hex"),
    );
    expect(research.coverage.obtainable).toBe(637);
    expect(triggers.regulationSha256).toBe(catalog.regulationSha256);
    expect(research.triggerEvidenceSha256).toBe(
      createHash("sha256")
        .update(
          readFileSync(
            new URL("../../data/effect-trigger-source.json", import.meta.url),
          ),
        )
        .digest("hex"),
    );
    expect(evidence.gameplayVerified).toBe(false);
    for (const r of Object.values(research.effects)) {
      expect(r.gameplayVerified).toBe(false);
      if (r.values === "unresolved" || r.stacking === "unresolved")
        expect(r.openQuestions.length).toBeGreaterThan(0);
    }
  });
  it("connects action effects to pinned animations and preserves actual tier behavior", () => {
    expect(effectDetail(7030900)!.blocks[0].values).toContainEqual([
      "物理攻击倍率",
      "+10%",
    ]);
    expect(effectDetail(7030900)!.blocks[0].duration).toBe(30);
    expect(effectDetail(7030900)!.stacking).toBe("不同等级可叠加");
    expect(effectDetail(6035100)!.blocks[0].values).toContainEqual([
      "精力恢复速度",
      "+17",
    ]);
    expect(effectDetail(6035100)!.blocks[0].duration).toBe(15);
    expect(effectDetail(7034700)!.blocks[0].restrictions).toContain(
      "适用：突刺反击",
    );
    const hp = effectDetail(7036100)!.blocks[0];
    expect(hp.values).toEqual([["HP定值恢复", "15"]]);
    expect(hp.duration).toBeNull();
    expect(hp.restrictions.join()).toContain("约每 1.1 秒恢复一次");
    for (const root of Object.values(triggers.roots)) {
      for (const seed of root.seeds) {
        const events = (
          root.events as Record<string, { type: number; parameters: string }[]>
        )[seed];
        expect(events.length).toBeGreaterThan(0);
        for (const event of events) {
          expect([66, 67, 302, 401]).toContain(event.type);
          expect(Buffer.from(event.parameters, "hex").readInt32LE()).toBe(seed);
        }
      }
    }
    for (const r of evidence.triggerMatching)
      expect(r.reused).toBe(r.existing === r.incoming);
    expect(
      evidence.triggerValues.find((r) => r.family === "grease")!.value,
    ).toBeCloseTo(1.1 * 1.17 * 1.2, 6);
    expect(
      evidence.extraGetters.find(
        (r) =>
          r.field === "staminaRecoverChangeSpeed" &&
          r.ids.length === 3 &&
          r.flags === 0,
      )!.value,
    ).toBe(47);
  });
  it("shows shop price reductions without inventing a periodic purchase cooldown", () => {
    expect(effectDetail(7230000)!.blocks[0].values).toEqual([
      ["商店卢恩价格", "-10%"],
    ]);
    expect(effectDetail(7230001)!.blocks[0].values).toEqual([
      ["商店卢恩价格", "-20%"],
    ]);
    expect(effectDetail(7230000)!.blocks[0].interval).toBeNull();
    expect(effectDetail(7230001)!.stackingDetail).toContain("72%");
    expect(
      evidence.extraGetters.find(
        (r) =>
          r.field === "runeDiscountValue" &&
          r.ids.length === 2 &&
          r.flags === 0,
      )!.value,
    ).toBeCloseTo(0.72);
  });
  it("uses native HP boundaries including float rounding and full-HP lower limits", () => {
    expect(effectDetail(6851200)!.blocks[0].restrictions).toContain(
      "血量 < 84.99%",
    );
    expect(effectDetail(7012300)!.blocks[0].restrictions).toContain(
      "血量 < 40%",
    );
    expect(effectDetail(6851000)!.blocks[0].restrictions).toContain("满血时");
    for (const id of [6851200, 7012300, 6851000]) {
      const cases = evidence.hpConditions.filter((r) => r.id === id);
      expect(cases.every((r) => r.fullUpdate)).toBe(true);
      expect(cases.find((r) => r.ratio === r.boundary)!.enabled).toBe(true);
      expect(cases.some((r) => !r.enabled)).toBe(true);
    }
  });
  it("follows aura recipients and avoids presenting a refresh lease as the ability duration", () => {
    expect(links.regulationSha256).toBe(catalog.regulationSha256);
    const aura = effectDetail(7050000)!.blocks[0];
    expect(aura.values).toEqual([["精力恢复速度", "+4"]]);
    expect(aura.duration).toBeNull();
    expect(links.emitters["7050000"].includeSelf).toBe(false);
    const lowHp = effectDetail(7012200)!;
    expect(lowHp.blocks[0].values).toEqual([
      ["HP定值恢复", "1"],
      ["HP恢复", "最大值的 0.5%"],
    ]);
    expect(lowHp.blocks[0].duration).toBe(50);
    expect(lowHp.blocks[0].interval).toBe(1);
    expect(links.emitters["7012202"].includeSelf).toBe(true);
    expect(lowHp.notes.join()).toContain("不要求一直维持低血量");
    expect(effectDetail(7090100)!.blocks).toHaveLength(1);
    expect(effectDetail(7090100)!.blocks[0].values).toEqual([
      ["HP定值恢复", "20"],
    ]);
    expect(effectDetail(7031200)!.blocks[0].values).toEqual([
      ["攻击倍率", "+25%"],
    ]);
  });
  it("shows executed HKS probabilities as alternatives, not simultaneous enchantments", () => {
    const effect = scripts.effects["7035700"];
    expect(scripts.gameplayVerified).toBe(false);
    expect(effect.cases).toHaveLength(212);
    expect(effect.branches.map((b) => b.chance)).toEqual([26, 25, 25, 24]);
    const detail = effectDetail(7035700)!;
    expect(detail.blocks).toHaveLength(1);
    expect(detail.blocks[0].values).toContainEqual([
      "属性攻击力",
      "+20（随机一种）",
    ]);
    expect(detail.blocks[0].duration).toBe(10);
    expect(detail.stacking).toBe("待确认");
    expect(effectDetail(7031900)!.blocks[0].values).toEqual([
      ["获得卢恩", "+600"],
    ]);
    expect(effectDetail(7031900)!.blocks[0].duration).toBeNull();
    expect(effectDetail(7036500)!.blocks[0].values).toEqual([
      ["获得卢恩", "+1300"],
    ]);
    for (const [path, hash] of [
      ["effect-link-source.json", research.linkEvidenceSha256],
      ["effect-script-evidence.json", research.scriptEvidenceSha256],
    ])
      expect(
        createHash("sha256")
          .update(readFileSync(new URL("../../data/" + path, import.meta.url)))
          .digest("hex"),
      ).toBe(hash);
  });
  it("uses actual growth transitions and compiled event bindings instead of adding tier percentages", () => {
    expect(growth.regulationSha256).toBe(catalog.regulationSha256);
    expect(research.growthEvidenceSha256).toBe(
      createHash("sha256")
        .update(
          readFileSync(
            new URL("../../data/effect-growth-source.json", import.meta.url),
          ),
        )
        .digest("hex"),
    );
    const undertaker = effectDetail(7037400)!;
    expect(undertaker.blocks.map((b) => b.values)).toEqual([
      [["精力上限", "+4%"]],
      [["精力上限", "+48.024%"]],
    ]);
    expect(undertaker.stacking).toBe("不可叠加");
    const first = evidence.growthAdvance.find(
      (r) => r.incoming === 7037501 && r.existing.length === 0,
    )!;
    expect(first.target).toBe(7037501);
    expect(first.changed).toBe(false);
    expect(
      evidence.growthAdvance.find((r) => r.existing.join() === "7037501")!
        .target,
    ).toBe(7037502);
    expect(
      evidence.growthAdvance.find((r) => r.existing.join() === "7037510")!
        .target,
    ).toBe(-1);
    expect(effectDetail(6060500)!.blocks[1].values).toContainEqual([
      "各类异常抵抗力",
      "+300",
    ]);
    expect(effectDetail(6060400)!.blocks[0].values).toContainEqual([
      "观察力",
      "+16",
    ]);
    expect(effectDetail(6060400)!.blocks[1].values).toContainEqual([
      "观察力",
      "+112",
    ]);
    expect(growth.roots["7060101"].eventLimit).toBe(7);
    expect(growth.roots["7060300"].eventLimit).toBe(10);
    expect(
      evidence.growthValues.find((r) => r.id === 7069410)!.neutralDisplay,
    ).toBe(260);
    for (const r of Object.values(growth.roots))
      for (const ladder of r.ladders)
        expect(
          evidence.growthAdvance.some(
            (v) => v.existing[0] === ladder.stages.at(-1) && v.target === -1,
          ),
        ).toBe(true);
  });
  it("uses executed native calculations for additive stats and multiplicative rates", () => {
    expect(effectDetail(7000000)!.stackingDetail).toBe("能力值相加");
    expect(effectDetail(7000800)!.stackingDetail).toBe("冷却时间倍率相乘");
    const tripleSpell = evidence.attack.filter(
      (r) =>
        r.ids.length === 3 &&
        r.ids.every((id) => id === 7611202) &&
        [3, 4].includes(r.kind),
    );
    expect(tripleSpell).toHaveLength(2);
    for (const r of tripleSpell)
      for (const rate of r.rates) expect(rate).toBeCloseTo(1.14 ** 3, 6);
    expect(effectDetail(6632400)!.stacking).toBe("不可叠加");
    expect(effectDetail(6632400)!.stackingDetail).toContain("第一个");
    expect(
      evidence.discovery.find((r) => r.ids.join() === "7632400,7633000")!
        .weaponType,
    ).not.toBe(
      evidence.discovery.find((r) => r.ids.join() === "7633000,7632400")!
        .weaponType,
    );
  });
  it("bases tier-only stacking on native matching, dispatch and gauge settlement", () => {
    for (const id of [7090000, 6090000]) {
      expect(effectDetail(id)!.stacking).toBe("不同等级可叠加");
      expect(effectDetail(id)!.stackingDetail).toContain("同等级重复无效");
    }
    expect(evidence.killMatching).toHaveLength(4);
    for (const r of evidence.killMatching)
      expect(r.reused).toBe(r.existing === r.incoming);
    const both = evidence.killDispatch.filter(
      (r) => r.ids.join() === "7090000,7090010" && r.flags === 0,
    );
    expect(both).toHaveLength(2);
    expect(both.find((r) => r.special === 0)!.percent).toBeCloseTo(11.5);
    expect(both.find((r) => r.special === 1)!.percent).toBeCloseTo(3.8);
    expect(evidence.gaugeApply.find((r) => r.percent === 5)!.value).toBeCloseTo(
      50,
    );
  });
  it("confirms resistance, FP cost and skill-use rules with native outputs", () => {
    expect(effectDetail(7003000)!.stacking).toBe("可叠加");
    expect(effectDetail(6610702)!.stackingDetail).toBe("FP 消耗倍率相乘");
    expect(effectDetail(7033200)!.stacking).toBe("不可叠加");
    expect(
      evidence.resistance.find(
        (r) =>
          r.ids.join() === "7003000,7003001" &&
          r.field === "changePoisonResistPoint" &&
          r.flags === 0,
      )!.value,
    ).toBe(185);
    const costs = evidence.fpCost.filter(
      (r) => r.ids.join() === "7610702,7610702,7610702" && r.flags === 0,
    );
    expect(costs).toHaveLength(4);
    for (const r of costs) expect(r.multiplier).toBeCloseTo(0.84 ** 3, 6);
  });
  it("preserves resistance units, restoration units and attack categories", () => {
    expect(effectDetail(7003000)!.blocks[0].values).toEqual([["抗毒", "+75"]]);
    expect(effectDetail(6003000)!.blocks[0].values).toEqual([["抗毒", "+110"]]);
    expect(effectDetail(6850200)!.blocks[0].values).toContainEqual([
      "抗毒",
      "-80",
    ]);
    expect(effectDetail(7036000)!.blocks[0].values).toContainEqual([
      "FP恢复",
      "最大值的 5%",
    ]);
    expect(effectDetail(7036000)!.blocks[0].interval).toBeNull();
    expect(effectDetail(7040100)!.blocks[0].restrictions).toContain(
      "适用：防御反击",
    );
    expect(effectDetail(7006600)!.blocks[0].restrictions).toContain(
      "适用：近战攻击",
    );
    expect(effectDetail(7000900)!.blocks[0].values).toEqual([
      ["绝招量表累积（所有来源）", "+5%"],
    ]);
    expect(effectDetail(6840200)!.blocks[0].values).toEqual([
      ["绝招量表累积（所有来源）", "-15%"],
    ]);
    expect(effectDetail(6840200)!.notes).toEqual([]);
  });
  it("limits extra starting goods to Scholar and preserves ordinary quantities", () => {
    for (const id of [7121100, 7126000, 7126001, 7126002]) {
      const detail = effectDetail(id)!;
      expect(detail.blocks).toHaveLength(1);
      expect(detail.blocks[0].values[0][1]).toBe("×2（学者 ×4）");
      expect(detail.blocks[0].phase).toBe("出击时");
      expect(detail.blocks[0].restrictions).toEqual([]);
      expect(detail.stacking).toBe("可叠加");
    }
    for (const id of [7120900, 7122100])
      expect(effectDetail(id)!.blocks[0].values[0][1]).toBe("×1");
    expect(effectDetail(6621100)!.blocks[0].values[0][1]).toBe("×1（学者 ×2）");
    for (const row of startingGoods.checks.selection) {
      const source = startingGoods.rows[String(row.root) as keyof typeof startingGoods.rows];
      const extra = [source.invocationConditionsStateChange1, source.invocationConditionsStateChange2,
        source.invocationConditionsStateChange3].includes(2226);
      expect(row.quantity).toBe(extra && row.hero !== 9 ? 0 : source.startingItemAmount);
    }
    expect(effectDetail(7122700)!.blocks[0].values).toEqual([
      ["出击时替换", "辉剑圆阵"],
    ]);
    expect(source.artsTextIds["200"]).toBe(200);
    expect(source.labels.SwordArtsName["200"]).toBe("辉剑圆阵");
  });
  it("shows level-dependent hero adjustments, including signed native truncation", () => {
    const detail = effectDetail(6646100)!;
    expect(evidence.hero).toHaveLength(400);
    expect(detail.blocks[0].values).toContainEqual([
      "1 级",
      "集中力 -2 / 智力 +2 / 信仰 +2",
    ]);
    expect(detail.blocks[0].values).toContainEqual([
      "2 级",
      "集中力 -3 / 智力 +2 / 信仰 +2",
    ]);
    expect(detail.blocks[0].values).toContainEqual([
      "12 级起",
      "集中力 -13 / 智力 +12 / 信仰 +12",
    ]);
    for (const b of detail.blocks)
      expect(new Set(b.values.map(([label]) => label)).size).toBe(
        b.values.length,
      );
  });
  it("omits one-shot lifetimes while retaining resets, refresh limits and real regeneration durations", () => {
    const burst = effectDetail(7036000)!.blocks[0];
    expect(burst.duration).toBeNull();
    expect(burst.interval).toBeNull();
    expect(burst.restrictions).toContain("恢复时重置连续攻击累计进度");
    const once = evidence.timing.find(
      (r) => r.id === 7036001 && r.refreshAt === null,
    )!;
    expect(once.ticks).toEqual([0]);
    expect(once.accumulatorAfterFirstTick).toBe(0);
    expect(once.accumulatorAfterNewAttacks).toBe(7);
    const hit = effectDetail(7350000)!.blocks[0];
    expect(hit.duration).toBeNull();
    expect(hit.restrictions.join()).toContain("约 1 秒内只触发一次");
    expect(hit.restrictions.join()).toContain("连续命中不会延长间隔");
    // Direct 511700 timer experiments are retained, but actual reinsertion
    // never reaches that function for these category-zero leaves.
    const refreshed = evidence.timing.find(
      (r) => r.id === 8600211 && r.refreshAt === 0.2,
    )!;
    expect(refreshed.ticks).toHaveLength(2);
    expect(Math.abs(refreshed.ticks[1] - 1.1)).toBeLessThan(0.04);
    const continuous = evidence.timing.find(
      (r) => r.id === 8600211 && r.refreshEvery === 0.2,
    )!;
    expect(continuous.ticks.length).toBeGreaterThan(5);
    for (let i = 1; i < continuous.ticks.length; i++)
      expect(
        Math.abs(continuous.ticks[i] - continuous.ticks[i - 1] - 1.1),
      ).toBeLessThan(0.04);
    expect(effectDetail(7260900)!.blocks[0].duration).toBe(15);
    expect(effectDetail(7260900)!.blocks[0].interval).toBe(1.3);
    expect(effectDetail(7034200)!.blocks[0].duration).toBe(3);
  });
});
