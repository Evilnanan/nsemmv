import { describe, expect, it } from "vitest";
import { EMPTY } from "../src/core/binary";
import {
  autoFix,
  effectAvailability,
  effectChoices,
  toRoll,
} from "../src/core/rules";
const vacant = () => toRoll([EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY]);
describe("candidate availability", () => {
  it("distinguishes duplicates, unknown IDs and the wrong effect pool", () => {
    const roll = toRoll([7000000, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY]);
    const assess = effectAvailability(100, roll, 1, false);
    expect(assess(7000001)).toMatchObject({
      state: "unavailable",
      issues: [{ code: "conflict" }],
    });
    expect(assess(999999998)).toMatchObject({
      state: "unavailable",
      issues: [{ code: "unknown" }],
    });
    expect(effectAvailability(100, roll, 0, false)(7000001).state).toBe(
      "available",
    );
    expect(
      effectAvailability(2000100, vacant(), 0, true)(7090000),
    ).toMatchObject({ state: "unavailable", issues: [{ code: "curse-pool" }] });
  });
  it("accepts a different obtainable Item ID and marks a required curse as incomplete", () => {
    const assess = effectAvailability(2000100, vacant(), 0, false);
    expect(assess(7090000)).toEqual({
      state: "available",
      issues: [],
      itemId: 2003100,
    });
    expect(assess(6611202)).toMatchObject({
      state: "incomplete",
      issues: [{ code: "missing-curse" }],
    });
  });
  it("rejects an impossible positive/curse pairing even though both effects occur in the candidate pools", () => {
    const roll = toRoll([7090000, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY]);
    expect(effectChoices(2000100, true)).toContain(6851700);
    expect(effectAvailability(2000100, roll, 0, true)(6851700)).toMatchObject({
      state: "unavailable",
      issues: [{ code: "combination" }],
    });
    const cursed = toRoll([6611202, EMPTY, EMPTY, 6851700, EMPTY, EMPTY]);
    expect(
      effectAvailability(2000100, cursed, 0, false)(7090000),
    ).toMatchObject({ state: "incomplete", issues: [{ code: "extra-curse" }] });
  });
  it("agrees with Auto Fix for every immediately usable offered effect in representative contexts", () => {
    const contexts = [
      {
        id: 100,
        roll: toRoll([7000000, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY]),
        slot: 1,
        curse: false,
      },
      { id: 2000100, roll: vacant(), slot: 0, curse: false },
      {
        id: 2000100,
        roll: toRoll([6611202, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY]),
        slot: 0,
        curse: true,
      },
    ];
    let available = 0;
    for (const c of contexts) {
      const assess = effectAvailability(c.id, c.roll, c.slot, c.curse);
      for (const id of effectChoices(c.id, c.curse)) {
        const result = assess(id),
          roll = c.roll.map((p) => ({ ...p }));
        roll[c.slot][c.curse ? "curse" : "effect"] = id;
        const fixed = autoFix(c.id, roll);
        expect(result.state === "available", `${c.id}/${id}`).toBe(
          fixed.issues.length === 0,
        );
        if (result.state === "available") available++;
      }
    }
    expect(available).toBeGreaterThan(300);
  }, 15000);
});
