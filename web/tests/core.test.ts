import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fixture, character } from "./fixtures";
import { Session } from "../src/core/session";
import { SaveContainer } from "../src/core/container";
import { catalog } from "../src/core/catalog";
import {
  Character,
  addRelic,
  removeRelic,
  signature,
} from "../src/core/character";
import { Binary, EMPTY, equal } from "../src/core/binary";
import {
  autoFix,
  checkRoll,
  fixedRoll,
  toRoll,
  sortRoll,
} from "../src/core/rules";
const simple = toRoll([7000000, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY]);
describe("browser binary codec", () => {
  it("preserves each same-name shop relic's actual type and fixed effects on export", () => {
    const s = Session.open(fixture(), "test");
    const records = [
      {
        id: 2060,
        deep: false,
        effects: [7123900, 7260400, 7260700],
        curses: [],
      },
      {
        id: 19063,
        deep: true,
        effects: [6610702, 6633100, 7037501],
        curses: [6851000],
      },
    ];
    for (const { id } of records) {
      expect(catalog.relics[id].name.zh_CN).toBe("雾霾的黑夜");
      s.apply(0, { type: "add", id, roll: fixedRoll(id)! });
    }
    const reopened = Session.open(s.export(), "reopen");
    for (const { id, deep, effects, curses } of records) {
      const r = reopened.view(0).relics.find((r) => r.id === id)!;
      expect(catalog.relics[r.id].deep).toBe(deep);
      expect(catalog.relics[r.id].shop).toBe(true);
      expect(r.roll.map((p) => p.effect).sort()).toEqual(effects);
      expect(
        r.roll
          .map((p) => p.curse)
          .filter((id) => id !== EMPTY)
          .sort(),
      ).toEqual(curses);
      expect(checkRoll(r.id, r.roll)).toEqual([]);
    }
  });
  it("reads without mutating and returns an identical no-op container", () => {
    const input = fixture();
    const s = Session.open(input, "NR0000.dbb");
    expect(s.view(0).relics.length).toBe(1);
    expect(s.view(0).loadouts?.heroes.length).toBe(10);
    expect(equal(s.export(), input)).toBe(true);
  });
  it("rejects corruption, overlapping sections and unsupported revisions", () => {
    const bad = fixture();
    bad[1200] ^= 1;
    expect(() => Session.open(bad, "bad")).toThrow(/校验和/);
    const overlap = fixture();
    new Binary(overlap).put32(64 + 32 + 16, 1024);
    expect(() => Session.open(overlap, "bad")).toThrow();
    const c = character();
    new Binary(c).put32(4, 999);
    expect(() => new Character(c)).toThrow(/版本/);
  });
  it("edits transactionally, undo/redo and preserves untouched encrypted entries", () => {
    const raw = fixture({ 0: character(), 1: character() }),
      s = Session.open(raw, "NR0000.dbb");
    const baseline = SaveContainer.open(raw);
    expect(() =>
      s.apply(0, {
        type: "edit",
        handle: 0xc0800054,
        id: 100,
        roll: toRoll([6611202, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY]),
      }),
    ).toThrow();
    expect(equal(s.export(), raw)).toBe(true);
    s.apply(1, { type: "favorite", handle: 0xc0800054, value: true });
    expect(s.view(1).relics[0].favorite).toBe(true);
    s.undo();
    expect(s.view(1).relics[0].favorite).toBe(false);
    s.redo();
    const output = s.export(),
      entry = baseline.entries[0];
    expect(
      equal(
        output.subarray(entry.offset, entry.offset + entry.size),
        raw.subarray(entry.offset, entry.offset + entry.size),
      ),
    ).toBe(true);
    expect(Session.open(output, "reopen").view(1).relics[0].favorite).toBe(
      true,
    );
  });
  it("adds/removes records with offsets relocated and no dangling loadouts", () => {
    const base = character(),
      c = new Character(base),
      added = addRelic(base, 100, simple);
    const after = new Character(added.bytes);
    expect(after.relics.length).toBe(2);
    expect(after.loadouts?.heroes).toHaveLength(10);
    expect(after.name).toBe(c.name);
    expect(new TextDecoder().decode(added.bytes)).toContain(
      "OPAQUE-MUST-SURVIVE",
    );
    const removed = removeRelic(added.bytes, added.handle);
    const restored = new Character(removed);
    expect(restored.relics).toEqual(c.relics);
    expect(restored.loadouts).toEqual(c.loadouts);
    expect(restored.b.u32(restored.countOffset)).toBe(2);
    expect(restored.b.u32(restored.inventoryEnd + 4)).toBe(4);
    expect(after.b.u8(after.relics[1].entryOffset + 13)).toBe(1);
  });
  it("creates/edits/equips presets and protects referenced relics", () => {
    const s = Session.open(fixture(), "test");
    s.apply(0, {
      type: "preset",
      hero: 7,
      vessel: 19000,
      handles: [0xc0800054, 0, 0, 0, 0, 0],
      name: "搓招流隐士",
    });
    expect(s.view(0).loadouts?.presets).toHaveLength(1);
    expect(() => s.apply(0, { type: "remove", handle: 0xc0800054 })).toThrow(
      /引用/,
    );
    s.apply(0, { type: "equip", index: 0 });
    const r = Session.open(s.export(), "reopen");
    expect(
      r.view(0).loadouts?.heroes.find((h) => h.id === 7)?.currentPreset,
    ).toBe(0);
  });
  it("keeps unknown existing relics but cannot duplicate or mutate one illegally", () => {
    const c = character(),
      b = new Binary(c);
    b.put32(20 + 84 * 8 + 16, 99999999);
    const s = Session.open(fixture({ 0: c }), "test");
    s.apply(0, { type: "favorite", handle: 0xc0800054, value: true });
    expect(
      Session.open(s.export(), "reopen").view(0).relics[0].roll[0].effect,
    ).toBe(99999999);
    expect(() =>
      s.apply(0, {
        type: "add",
        id: 100,
        roll: toRoll([99999999, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY]),
      }),
    ).toThrow();
  });
});
describe("shop relic policy", () => {
  it("blocks edits, conversions and deletion at the writer, while preserving collection and equipment", () => {
    const s = Session.open(fixture(), "test");
    const roll = fixedRoll(11015)!;
    const handle = s.apply(0, { type: "add", id: 11015, roll })!;
    const baseline = s.bytes(0).slice();
    expect(() => s.apply(0, { type: "edit", handle, id: 11015, roll })).toThrow(
      /商店遗物不能修改/,
    );
    expect(() =>
      s.apply(0, {
        type: "edit",
        handle,
        id: 2000000,
        roll: toRoll([7090000, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY]),
      }),
    ).toThrow();
    expect(() =>
      s.apply(0, { type: "edit", handle: 0xc0800054, id: 11015, roll }),
    ).toThrow(/商店遗物不能修改/);
    expect(() => s.apply(0, { type: "remove", handle })).toThrow(
      /商店遗物不能删除/,
    );
    expect(equal(s.bytes(0), baseline)).toBe(true);
    s.apply(0, { type: "favorite", handle, value: true });
    expect(
      Session.open(s.export(), "reopen")
        .view(0)
        .relics.find((r) => r.handle === handle)?.favorite,
    ).toBe(true);
  });
});
describe("strict MMV rolls", () => {
  it("preserves pairs while sorting and selects an appropriate item ID", () => {
    const r = toRoll([7090000, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY]);
    const fixed = autoFix(2000100, r);
    expect(fixed.id).toBe(2003100);
    expect(fixed.issues).toEqual([]);
  });
  it("reports missing curse without silently adding one", () => {
    const r = toRoll([6611202, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY]);
    const fixed = autoFix(2000100, r);
    expect(fixed.issues.some((i) => i.code === "missing-curse")).toBe(true);
    expect(fixed.roll.every((p) => p.curse === EMPTY)).toBe(true);
  });
  it("supports MMV fixed shop rolls and prevents duplicate shop relics", () => {
    const roll = fixedRoll(11015)!;
    expect(roll).not.toBeNull();
    expect(checkRoll(11015, roll)).toEqual([]);
    const s = Session.open(fixture(), "test");
    s.apply(0, { type: "add", id: 11015, roll });
    expect(() => s.apply(0, { type: "add", id: 11015, roll })).toThrow(
      /商店遗物/,
    );
  });
});
if (process.env.NR_SAVE)
  it("local private save roundtrip (never checked in)", () => {
    const input = new Uint8Array(readFileSync(process.env.NR_SAVE!));
    const s = Session.open(input, "NR0000.dbb");
    expect(equal(s.export(), input)).toBe(true);
    for (const slot of s.occupied) {
      expect(s.view(slot).loadouts).not.toBeNull();
    }
    const slot = s.occupied.at(-1)!;
    const before = s.view(slot);
    s.apply(slot, {
      type: "favorite",
      handle: before.relics[0].handle,
      value: !before.relics[0].favorite,
    });
    const add = s.apply(slot, { type: "add", id: 100, roll: simple });
    expect(add).toBeDefined();
    const out = Session.open(s.export(), "roundtrip");
    expect(out.view(slot).relics).toHaveLength(before.relics.length + 1);
    expect(out.view(slot).loadouts?.presets).toEqual(
      s.view(slot).loadouts?.presets,
    );
  });

describe("preset slot and metadata integrity", () => {
  it("retains physical indices across deleted holes and reuses a hole without moving later records", () => {
    const s = Session.open(fixture(), "test"),
      handle = 0xc0800054;
    const second = s.apply(0, { type: "add", id: 100, roll: simple })!;
    s.apply(0, {
      type: "preset",
      hero: 7,
      vessel: 19000,
      handles: [handle, 0, 0, 0, 0, 0],
      name: "one",
    });
    s.apply(0, {
      type: "preset",
      hero: 7,
      vessel: 19000,
      handles: [second, 0, 0, 0, 0, 0],
      name: "two",
    });
    s.apply(0, { type: "equip", index: 1 });
    s.apply(0, { type: "delete-preset", index: 0 });
    let c = new Character(s.bytes(0));
    expect(c.loadouts?.presets[0].index).toBe(1);
    expect(c.loadouts?.heroes[6].currentPreset).toBe(1);
    const p = c.loadouts!.presets[0];
    const timestamp = c.b.view.getBigUint64(p.offset + 72, true);
    expect(
      timestamp > 130000000000000000n && timestamp < 150000000000000000n,
    ).toBe(true);
    s.apply(0, {
      type: "preset",
      hero: 7,
      vessel: 19000,
      handles: [handle, 0, 0, 0, 0, 0],
      name: "reused",
    });
    c = new Character(s.bytes(0));
    expect(c.loadouts?.presets.map((p) => p.index)).toEqual([0, 1]);
    expect(c.loadouts?.presets[1].name).toBe("two");
    expect(c.loadouts?.heroes[6].currentPreset).toBe(1);
    expect(c.b.view.getBigUint64(p.offset + 72, true)).toBe(timestamp);
    s.apply(0, {
      type: "preset",
      index: 1,
      hero: 7,
      vessel: 19000,
      handles: [second, 0, 0, 0, 0, 0],
      name: "renamed",
    });
    expect(s.view(0).loadouts?.heroes[6].currentPreset).toBe(1);
  });
  it("retains a pre-existing stale selected index and refuses an unowned vessel", () => {
    const b = character(),
      c = new Character(b);
    b[c.loadouts!.heroes[0].offset + 1] = 99;
    expect(new Character(b).loadouts?.heroes[0].currentPreset).toBe(99);
    const s = Session.open(fixture({ 0: b }), "test");
    expect(() =>
      s.apply(0, {
        type: "preset",
        hero: 7,
        vessel: 19001,
        handles: [0xc0800054, 0, 0, 0, 0, 0],
        name: "locked",
      }),
    ).toThrow(/持有/);
  });
});
