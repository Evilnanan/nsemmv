import { describe, expect, it } from "vitest";
import {
  fitPresetHandles,
  fitsPresetSlot,
  matchesRelicSearch,
} from "../src/core/preset-editor";
import { Session } from "../src/core/session";
import { fixture } from "./fixtures";
import { catalog, effectName } from "../src/core/catalog";
import { fixedRoll, toRoll } from "../src/core/rules";
import { EMPTY } from "../src/core/binary";

const source = Session.open(fixture(), "test").view(0).relics[0];
const relics = [100, 109, 118, 2000000, 2000100, 2000200].map((id, index) => ({
  ...source,
  id,
  handle: index + 1,
}));

describe("preset vessel changes", () => {
  it("keeps existing slots when their colors still fit", () => {
    expect(
      fitPresetHandles([1, 2, 3, 4, 5, 6], [4, 4, 4, 4, 4, 4], relics),
    ).toEqual([1, 2, 3, 4, 5, 6]);
  });
  it("moves compatible relics rather than clearing the entire loadout", () => {
    expect(
      fitPresetHandles([1, 2, 3, 4, 5, 6], [1, 0, 2, 1, 0, 2], relics),
    ).toEqual([2, 1, 3, 5, 4, 6]);
  });
  it("reserves wildcard slots when greedy placement would discard a compatible relic", () => {
    const result = fitPresetHandles(
      [1, 2, 3, 4, 5, 6],
      [4, 0, 1, 4, 0, 1],
      relics,
    );
    expect(result).toEqual([3, 1, 2, 6, 4, 5]);
  });
  it("removes only unmatched relics and never duplicates a handle or mixes ordinary/deep slots", () => {
    const result = fitPresetHandles(
      [1, 1, 999, 4, 5, 6],
      [0, 0, 0, 1, 1, 1],
      relics,
    );
    expect(result).toEqual([1, 0, 0, 0, 5, 0]);
    result.forEach((handle, slot) => {
      if (handle)
        expect(
          fitsPresetSlot(
            relics.find((r) => r.handle === handle)!,
            [0, 0, 0, 1, 1, 1],
            slot,
          ),
        ).toBe(true);
    });
  });
});

describe("preset candidate search", () => {
  it("searches relic names, positive and Curse names/IDs, and case-insensitive multiple words", () => {
    const relic = { ...source, id: 10004, roll: fixedRoll(10004)! };
    const curse = relic.roll.find(
      (pair) => pair.curse !== EMPTY && pair.curse !== 0,
    )!.curse;
    for (const query of [
      String(curse),
      effectName(curse),
      catalog.relics[10004].name.zh_CN,
      "  10004  " + effectName(relic.roll[0].effect),
      catalog.relics[10004].name.en_US.toUpperCase(),
    ]) {
      expect(matchesRelicSearch(relic, query), query).toBe(true);
    }
    expect(matchesRelicSearch(relic, "10004 不存在的词条")).toBe(false);
    expect(
      matchesRelicSearch(
        {
          ...source,
          roll: toRoll([7000000, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY]),
        },
        "生命力",
      ),
    ).toBe(true);
  });
});
