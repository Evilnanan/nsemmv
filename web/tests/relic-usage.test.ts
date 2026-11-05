import { describe, expect, it } from "vitest";
import {
  relicUsage,
  matchesUsage,
  type UsageFilter,
} from "../src/core/relic-usage";
import { Session } from "../src/core/session";
import {
  usageFixture,
  sharedHandle,
  longPresetName,
} from "./relic-usage.fixture";

describe("relic references", () => {
  it("filters against the preset hero, including references only in presets or inactive vessels", () => {
    const { bytes, duplicate, exclusive } = usageFixture();
    const loadouts = Session.open(bytes, "usage").view(0).loadouts;
    const handles = [sharedHandle, duplicate, exclusive];
    for (const [filter, expected] of [
      ["all", handles],
      ["unshared", [duplicate, exclusive]],
      ["unused", [duplicate]],
      ["current", [sharedHandle, exclusive]],
      ["other", [sharedHandle]],
    ] as [UsageFilter, number[]][])
      expect(
        handles.filter((h) => matchesUsage(relicUsage(loadouts, h), 7, filter)),
      ).toEqual(expected);
    expect(matchesUsage(relicUsage(loadouts, exclusive), 1, "unshared")).toBe(
      false,
    );
    expect(matchesUsage(null, 7, "unused")).toBe(false);
    expect(matchesUsage(null, 7, "unshared")).toBe(false);
    expect(matchesUsage(null, 7, "all")).toBe(true);
  });
  it("distinguishes current equipment, retained vessels and every preset by instance", () => {
    const { bytes, duplicate } = usageFixture();
    const session = Session.open(bytes, "usage");
    expect(relicUsage(session.view(0).loadouts, sharedHandle)).toEqual([
      { hero: 1, vessels: [], presets: [{ index: 2, name: "共享配置" }] },
      {
        hero: 2,
        vessels: [{ id: 19000, equipped: false }],
        presets: [{ index: 3, name: "备用器皿" }],
      },
      {
        hero: 7,
        vessels: [{ id: 19000, equipped: true }],
        presets: [
          { index: 0, name: "搓招流" },
          { index: 1, name: longPresetName },
        ],
      },
    ]);
    expect(relicUsage(session.view(0).loadouts, duplicate)).toEqual([]);
    expect(relicUsage(session.view(1).loadouts, sharedHandle)).toEqual([]);
    expect(relicUsage(null, sharedHandle)).toBeNull();
  });

  it("tracks preset deletion and undo without treating a selected preset index as equipment", () => {
    const session = Session.open(usageFixture().bytes, "usage");
    session.apply(0, { type: "delete-preset", index: 0 });
    const hermit = relicUsage(session.view(0).loadouts, sharedHandle)!.find(
      (r) => r.hero === 7,
    )!;
    expect(hermit.vessels).toEqual([{ id: 19000, equipped: true }]);
    expect(hermit.presets.map((p) => p.index)).toEqual([1]);
    session.undo();
    expect(
      relicUsage(session.view(0).loadouts, sharedHandle)!.find(
        (r) => r.hero === 7,
      )!.presets,
    ).toHaveLength(2);
  });
});
