import { describe, it, expect, vi } from "vitest";
import native from "./native-mutations.json";
import { character } from "./fixtures";
import {
  Character,
  addRelic,
  savePreset,
  deletePreset,
} from "../src/core/character";
import { Binary, EMPTY, equal } from "../src/core/binary";
import { toRoll } from "../src/core/rules";
const roll = toRoll([7000000, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY]);

describe("native PC mutation evidence", () => {
  it("matches the native 72-byte initializer, with only ID and effect fields replaced", () => {
    const added = addRelic(character(), 100, roll),
      c = new Character(added.bytes),
      r = c.relics.find((r) => r.handle === added.handle)!;
    const expected = Uint8Array.from(native.relicBodyDefault),
      b = new Binary(expected);
    b.put32(0, 0x80000064);
    b.put32(8, 7000000);
    expect(
      equal(
        added.bytes.subarray(r.stateOffset + 8, r.stateOffset + 80),
        expected,
      ),
    ).toBe(true);
    expect(added.handle).toBe(0xc0800055);
    expect(c.b.u32(r.entryOffset + 4)).toBe(1);
    expect(c.b.u32(r.entryOffset + 8)).toBe(3);
    expect(c.b.u8(r.entryOffset + 12)).toBe(0);
    expect(c.b.u8(r.entryOffset + 13)).toBe(1);
  });
  it("matches native preset creation and deletion without erasing reserved bytes", () => {
    const data = character(),
      c = new Character(data),
      base = c.loadouts!.presetBase;
    data.set(native.presetCreate.input.slice(0x30), base);
    const clock = vi
      .spyOn(Date, "now")
      .mockReturnValue(Number(134380123456780000n / 10000n - 11644473600000n));
    let created: Uint8Array;
    try {
      created = savePreset(
        data,
        7,
        19000,
        [0xc0800054, 0, 0, 0, 0, 0],
        "native",
      );
    } finally {
      clock.mockRestore();
    }
    expect(
      equal(
        created!.subarray(base, base + 400),
        Uint8Array.from(native.presetCreate.output.slice(0x30)),
      ),
    ).toBe(true);
    const renamed = savePreset(
      created!,
      7,
      19000,
      [0xc0800054, 0, 0, 0, 0, 0],
      "隐士🌙",
      0,
    );
    const rc = new Character(renamed);
    expect(rc.loadouts!.presets[0].name).toBe("隐士🌙");
    expect(
      equal(
        renamed.subarray(base + 40, base + 80),
        created!.subarray(base + 40, base + 80),
      ),
    ).toBe(true);
    const deleted = deletePreset(created!, 0);
    expect(
      equal(
        deleted.subarray(base, base + 80),
        Uint8Array.from(native.presetDelete.output.slice(0x30)),
      ),
    ).toBe(true);
    expect(
      new Character(deleted).loadouts!.presets.map((p) => [p.index, p.counter]),
    ).toEqual([
      [1, 1],
      [3, 0],
    ]);
  });
  it("does not let acquisition serials or high existing indices escape the native state table", () => {
    const data = character(),
      c = new Character(data),
      b = c.b;
    b.put32(c.relics[0].stateOffset, 0xc08013ff);
    b.put32(c.relics[0].entryOffset, 0xc08013ff);
    b.put32(c.inventoryEnd + 4, 100000);
    const added = addRelic(data, 100, roll),
      after = new Character(added.bytes);
    expect(added.handle & 0xffff).toBe(85);
    expect(after.relics[1].acquisition).toBe(100000);
    expect(after.b.u32(after.inventoryEnd + 4)).toBe(100001);
  });
  it("keeps the key bank intact and refuses overflow into it", () => {
    const data = character(),
      c = new Character(data),
      b = c.b,
      key = c.banks[1];
    b.put32(key.countOffset, 1);
    b.put32(key.entriesOffset, 0xb0000001);
    b.put32(key.entriesOffset + 4, 1);
    b.put32(key.entriesOffset + 8, 90);
    const keyBytes = data.slice(key.countOffset, c.inventoryEnd);
    const added = addRelic(data, 100, roll),
      after = new Character(added.bytes);
    expect(
      equal(
        added.bytes.subarray(after.banks[1].countOffset, after.inventoryEnd),
        keyBytes,
      ),
    ).toBe(true);
    expect(after.relics[1].acquisition).toBe(91);
    for (let i = 2; i < 2688; i++) {
      b.put32(c.entriesOffset + i * 14, 0xb0000002);
      b.put32(c.entriesOffset + i * 14 + 4, 1);
    }
    expect(() => addRelic(data, 100, roll)).toThrow(/库存已满/);
  });
});
