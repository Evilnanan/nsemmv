import { describe, it, expect } from "vitest";
import { catalog, relicDefinitions, poolSets } from "../src/core/catalog";
import { fixedRoll, checkRoll, effectChoices, toRoll } from "../src/core/rules";
import oracle from "./mmv-oracle.json" with { type: "json" };
describe("pinned MMV catalog", () => {
  it("matches 5310 independent Python validator outcomes across all obtainable IDs", () => {
    expect(oracle.length).toBe(5310);
    for (const c of oracle)
      expect(
        checkRoll(c.id, toRoll(c.values)).length === 0,
        `${c.id}:${c.values}`,
      ).toBe(c.valid);
  });
  it("covers every unsalable obtainable shop relic and its fixed legal roll", () => {
    expect(Object.values(catalog.relics).filter((r) => r.shop)).toHaveLength(
      206,
    );
    expect(
      [136, 12004, 12005, 12006, 12007].every(
        (id) => catalog.relics[id].salable && !catalog.relics[id].shop,
      ),
    ).toBe(true);
    expect(
      [20000, 20035, 30000, 30035].every(
        (id) => catalog.relics[id].shop && !catalog.relics[id].salable,
      ),
    ).toBe(true);
    const shops = relicDefinitions.filter((r) => r.shop);
    expect(shops.length).toBe(134);
    for (const r of shops) {
      const roll = fixedRoll(r.id);
      expect(roll, `${r.id}`).not.toBeNull();
      expect(checkRoll(r.id, roll!)).toEqual([]);
    }
  });
  it("offers every positive-weight effect from same color/type candidate pools", () => {
    for (const id of [100, 101, 2000000, 2000100, 2000200, 2000300])
      for (const curse of [false, true]) {
        const r = catalog.relics[id],
          offered = new Set(effectChoices(id, curse));
        for (const candidate of relicDefinitions.filter(
          (x) =>
            x.id === id ||
            (!x.shop && x.color === r.color && x.deep === r.deep),
        ))
          for (const pool of candidate.pools.slice(
            curse ? 3 : 0,
            curse ? 6 : 3,
          ))
            for (const effect of poolSets.get(pool) ?? [])
              expect(offered.has(effect)).toBe(true);
      }
  });
});
