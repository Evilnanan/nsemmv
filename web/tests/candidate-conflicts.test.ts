import { describe, expect, it } from "vitest";
import { EMPTY } from "../src/core/binary";
import { catalog } from "../src/core/catalog";
import { candidateConflicts, checkRoll, toRoll } from "../src/core/rules";

describe("candidate conflict preview", () => {
  it("replaces the selected slot instead of treating its old effect as another effect", () => {
    const roll = toRoll([7000000, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY]);
    const before = structuredClone(roll);
    expect(candidateConflicts(roll, 0, false, 7000000)).toEqual([]);
    expect(candidateConflicts(roll, 0, false, 7000001)).toEqual([]);
    expect(candidateConflicts(roll, 1, false, 7000000)).toEqual([
      { id: 7000000, slot: 0 },
    ]);
    expect(candidateConflicts(roll, 1, false, 7000001)).toEqual([
      { id: 7000000, slot: 0 },
    ]);
    expect(roll).toEqual(before);
  });
  it("uses the native exclusivity groups, not only identical IDs or compatibility groups", () => {
    expect(catalog.effects[6630000].exclusive).toBe(202);
    const original = catalog.effects[6630100];
    // Pinned rows share both groups. Isolate the exclusion rule from compatibility.
    catalog.effects[6630100] = { ...original, conflict: -1 };
    try {
      const roll = toRoll([6630000, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY]);
      expect(candidateConflicts(roll, 1, false, 6630100)).toEqual([
        { id: 6630000, slot: 0 },
      ]);
      expect(
        checkRoll(100, toRoll([6630000, 6630100, EMPTY, EMPTY, EMPTY, EMPTY])),
      ).toEqual([{ code: "conflict", message: "词条重复或互斥", slot: 1 }]);
    } finally {
      catalog.effects[6630100] = original;
    }
  });
  it("checks all six fields and excludes only the field being replaced", () => {
    const roll = toRoll([7000000, EMPTY, EMPTY, 6851700, EMPTY, EMPTY]);
    expect(candidateConflicts(roll, 0, true, 6851700)).toEqual([]);
    expect(candidateConflicts(roll, 1, true, 6851700)).toEqual([
      { id: 6851700, slot: 3 },
    ]);
    expect(candidateConflicts(roll, 0, true, 7000000)).toEqual([
      { id: 7000000, slot: 0 },
    ]);
    expect(candidateConflicts(roll, 0, false, 6851700)).toEqual([
      { id: 6851700, slot: 3 },
    ]);
  });
  it("does not label unrelated existing conflicts, empty fields or missing curses as a candidate conflict", () => {
    const invalid = toRoll([7000000, 7000001, EMPTY, EMPTY, EMPTY, EMPTY]);
    expect(candidateConflicts(invalid, 2, false, 7000100)).toEqual([]);
    expect(candidateConflicts(invalid, 2, false, EMPTY)).toEqual([]);
    expect(candidateConflicts(invalid, 2, false, 0)).toEqual([]);
    expect(
      candidateConflicts(
        toRoll([EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY]),
        0,
        false,
        6611202,
      ),
    ).toEqual([]);
  });
});
