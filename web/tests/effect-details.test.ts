import { describe, expect, it } from "vitest";
import { catalog } from "../src/core/catalog";
import { effectDetail } from "../src/core/effect-details";
import source from "../../data/effect-detail-source.json";
import evidence from "../../data/effect-native-evidence.json";
import research from "../../data/effect-research.json";
import triggers from "../../data/effect-trigger-source.json";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";

describe("MMV effect details", () => {
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
          expect([66, 67, 401]).toContain(event.type);
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
      ["绝招量表自然累积", "+5%"],
      ["攻击／效果的绝招累积", "+5%"],
    ]);
  });
  it("does not unconditionally sum starting-item branches", () => {
    const blocks = effectDetail(7121100)!.blocks;
    expect(blocks.map((b) => b.values)).toEqual([
      [["火焰壶", "×2"]],
      [["火焰壶", "×2"]],
    ]);
    expect(blocks.map((b) => b.phase)).toEqual([
      "出击时",
      "额外发放条件待确认",
    ]);
    expect(blocks[1].restrictions).toContain("需满足指定状态");
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
    expect(hit.restrictions.join()).toContain("1 秒内再次触发只延长有效期");
    expect(hit.restrictions.join()).toContain("约每 1.1 秒恢复一次");
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
