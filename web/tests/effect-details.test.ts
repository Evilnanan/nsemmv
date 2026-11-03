import { describe, expect, it } from "vitest";
import { catalog } from "../src/core/catalog";
import { effectDetail } from "../src/core/effect-details";
import source from "../../data/effect-detail-source.json";
import evidence from "../../data/effect-native-evidence.json";
import research from "../../data/effect-research.json";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";

describe("MMV effect details", () => {
  it("covers the active catalog with pinned, finite, traceable parameters", () => {
    expect(source.hashes["regulation.bin"]).toBe(catalog.regulationSha256);
    const spells = source.spells as Record<string, Record<string, number>>;
    for (const id of Object.keys(catalog.effects).map(Number)) {
      const detail = effectDetail(id)!;
      expect(detail).toBeDefined();
      for (const block of detail.blocks) {
        expect(spells[String(block.source)]).toBeDefined();
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
    expect(kill.blocks.map((b) => b.phase)).toEqual([
      "击杀触发分支",
      "获得卢恩触发分支",
    ]);
    expect(kill.stacking).toContain("同版重复待确认");
    expect(effectDetail(6611202)!.stacking).toBe("可叠加；攻击倍率相乘");
    expect(effectDetail(999999998)).toBeUndefined();
  });
  it("keeps a versioned research record for every obtainable effect, without claiming gameplay verification", () => {
    const ids = new Set(
      Object.values(catalog.relics)
        .filter((r) => r.obtainable)
        .flatMap((r) => r.pools.flatMap((p) => catalog.pools[p] ?? [])),
    );
    expect(Object.keys(research.effects).map(Number).sort()).toEqual(
      [...ids].sort(),
    );
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
    expect(evidence.gameplayVerified).toBe(false);
    for (const r of Object.values(research.effects)) {
      expect(r.gameplayVerified).toBe(false);
      if (r.values === "unresolved" || r.stacking === "unresolved")
        expect(r.openQuestions.length).toBeGreaterThan(0);
    }
  });
  it("uses executed native calculations for additive stats and multiplicative rates", () => {
    expect(effectDetail(7000000)!.stacking).toBe("可叠加；能力值相加");
    expect(effectDetail(7000800)!.stacking).toBe("可叠加；冷却时间倍率相乘");
    const tripleSpell = evidence.attack.filter(
      (r) =>
        r.ids.length === 3 &&
        r.ids.every((id) => id === 7611202) &&
        [3, 4].includes(r.kind),
    );
    expect(tripleSpell).toHaveLength(2);
    for (const r of tripleSpell)
      for (const rate of r.rates) expect(rate).toBeCloseTo(1.14 ** 3, 6);
    expect(effectDetail(6632400)!.stacking).toContain("第一个武器倾向");
    expect(
      evidence.discovery.find((r) => r.ids.join() === "7632400,7633000")!
        .weaponType,
    ).not.toBe(
      evidence.discovery.find((r) => r.ids.join() === "7633000,7632400")!
        .weaponType,
    );
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
});
