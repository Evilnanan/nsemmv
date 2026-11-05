import { describe, it, expect } from "vitest";
import { Binary, equal } from "../src/core/binary";
import { SaveContainer } from "../src/core/container";
import { Session } from "../src/core/session";
import { Character } from "../src/core/character";
import { displayGameText } from "../src/core/game-text";
import { nameFixture } from "./character-name.fixture";
import { fixture } from "./fixtures";

describe("character rename", () => {
  it("updates only the selected name and its selection summary, with atomic undo and redo", () => {
    const input = nameFixture(),
      s = Session.open(input, "names");
    const before = SaveContainer.open(input);
    const offset = new Character(s.bytes(1)).nameOffset;
    const name = "<搓招>#?%＼¥🪄";
    s.apply(1, { type: "rename", name });
    expect(s.view(1).name).toBe(name);
    expect(s.view(0).name).toBe("OvO");
    expect(s.dirty()).toBe(true);
    const result = SaveContainer.open(s.export());
    expect(s.dirty()).toBe(false);
    expect(
      displayGameText(
        new Binary(result.entries[10].plain).text(42 + 0x290, 16),
      ),
    ).toBe(name);
    for (const e of result.entries) {
      const original = before.entries[e.index].plain;
      const p = e.index === 1 ? offset : e.index === 10 ? 42 + 0x290 : -100;
      const masked = e.plain.slice(0, e.plain.length - 28);
      if (p >= 0) masked.set(original.subarray(p, p + 32), p);
      expect(equal(masked, original.subarray(0, original.length - 28))).toBe(true);
    }
    s.undo();
    expect(s.dirty()).toBe(true);
    expect(s.view(1).name).toBe(",>_<,");
    expect(equal(s.export(), input)).toBe(true);
    s.redo();
    expect(s.view(1).name).toBe(name);
    expect(
      displayGameText(
        new Binary(SaveContainer.open(s.export()).entries[10].plain).text(
          42 + 0x290,
          16,
        ),
      ),
    ).toBe(name);
  });

  it("preserves an unchanged spelling, allows full-length Unicode, and rejects invalid writes atomically", () => {
    const s = Session.open(nameFixture(), "names");
    s.apply(1, { type: "rename", name: ",>_<," });
    expect(s.view(1).canUndo).toBe(false);
    for (const name of ["隐".repeat(16), "🪄".repeat(8), "<".repeat(16)]) {
      s.apply(1, { type: "rename", name });
      expect(Session.open(s.export(), "reopen").view(1).name).toBe(name);
    }
    const before = s.bytes(1).slice();
    for (const name of ["", "  ", "隐".repeat(17), "a\0b", "a\nb", "\ud800"])
      expect(() => s.apply(1, { type: "rename", name })).toThrow();
    expect(s.bytes(1)).toEqual(before);
    const unsupported = Session.open(fixture(), "unknown summary");
    expect(() =>
      unsupported.apply(0, { type: "rename", name: "改名" }),
    ).toThrow();
    expect(unsupported.dirty()).toBe(false);
    expect(unsupported.view(0).canUndo).toBe(false);
  });
});
