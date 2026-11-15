import { describe, it, expect } from "vitest";
import { catalog, relicDefinitions } from "../src/core/catalog";
import {
  effectGroup,
  filterEffects,
  UNCLASSIFIED,
} from "../src/core/effect-filters";
import { effectChoices } from "../src/core/rules";

describe("native effect filter categories", () => {
  it("uses the native filter references, including variants and character-specific effects", () => {
    expect(Object.keys(catalog.effectCategories)).toHaveLength(4);
    expect(Object.keys(catalog.effectGroups)).toHaveLength(35);
    expect(catalog.effectGroups[30020].name.zh_CN).toBe("攻击力");
    expect(catalog.effectGroups[30010].name.zh_CN).toBe("技艺／绝招");
    expect(effectGroup(7090000)).toBe(30010);
    expect(effectGroup(7000300)).toBe(30000); // Strength belongs to attributes, not attack power.
    expect(effectGroup(7032700)).toBe(10030); // Duchess-specific, regardless of keywords.
    expect(catalog.effects[6611202].filterId).toBe(6611200);
    expect(effectGroup(6611202)).toBe(30020);
  });
  it("preserves native classifications and keeps seven unclassified Hotfix1 effects visible", () => {
    const available = new Set(
      relicDefinitions.flatMap((r) =>
        r.pools.flatMap((p) => catalog.pools[p] ?? []),
      ),
    );
    expect(available.size).toBe(657);
    const unclassified = [320906, 8220001, 8652020, 8800200, 8810000, 8831200, 8850200];
    expect(filterEffects([...available], "", UNCLASSIFIED).sort((a, b) => a - b)).toEqual(unclassified);
    for (const id of available) {
      if (unclassified.includes(id)) continue;
      const group = catalog.effectGroups[effectGroup(id)];
      expect(group, `${id}`).toBeDefined();
      expect(catalog.effectCategories[group.category]).toBeDefined();
    }
    expect(filterEffects([999999998], "", null)).toEqual([999999998]);
    expect(filterEffects([999999998], "", UNCLASSIFIED)).toEqual([999999998]);
  });
  it("intersects category and query without widening the legal candidate pools", () => {
    const choices = effectChoices(2000100, false);
    expect(filterEffects(choices, "7090000", 30010)).toEqual([7090000]);
    expect(filterEffects(choices, "7090000", 30020)).toEqual([]);
    expect(filterEffects(choices, " 6611202 ", 30020)).toEqual([6611202]);
    expect(filterEffects(choices, "绝招", 30010)).toContain(7090000);
    const grouped = [...new Set(choices.map(effectGroup))].flatMap((group) =>
      filterEffects(choices, "", group),
    );
    expect([...grouped].sort((a, b) => a - b)).toEqual(choices);
    expect(filterEffects(effectChoices(2000100, true), "", 30020)).toEqual([]);
  });
});
