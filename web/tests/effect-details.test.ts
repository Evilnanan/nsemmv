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
import discovery from "../../data/effect-discovery-evidence.json";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";

describe("MMV effect details", () => {
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
    expect(research.coverage.withMechanicsOnly).toBe(36);
    expect(research.coverage.withNumericFields).toBe(480);
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
