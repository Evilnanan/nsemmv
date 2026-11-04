import { expect, it } from "vitest";
import evidence from "../../data/name-glyph-evidence.json";
import { displayGameText, storeGameText } from "../src/core/game-text";
import { Binary, equal } from "../src/core/binary";
import { Character } from "../src/core/character";
import { Session } from "../src/core/session";
import { character, fixture } from "./fixtures";

it("matches native font selection for every UTF-16 code unit", () => {
  const mapping = evidence.mapping as Record<string, string>;
  expect(evidence.testedCodeUnits).toBe(65536);
  for (let code = 0; code < 65536; code++) {
    const hex = code.toString(16).toUpperCase().padStart(4, "0");
    expect(displayGameText(String.fromCharCode(code)).charCodeAt(0)).toBe(
      mapping[hex] ? parseInt(mapping[hex], 16) : code,
    );
  }
  const text = "<隐士> #?%＼¥ \\ ＜＞＃？％ ① Ω 🪄";
  expect(displayGameText(storeGameText(text))).toBe(text);
});

it("displays saved names without changing bytes, including after unrelated edits", () => {
  const raw = character();
  const pos = new Character(raw).nameOffset;
  new Binary(raw).putText(pos, 16, ",㉒_㉑,⑲⑳㉓㉔㉕");
  const input = fixture({ 0: raw });
  const session = Session.open(input, "NR0000.dbb");
  expect(session.view(0).characters[0].name).toBe(",>_<,#?%＼¥");
  expect(equal(session.export(), input)).toBe(true);
  session.apply(0, { type: "favorite", handle: 0xc0800054, value: true });
  const reopened = Session.open(session.export(), "reopen");
  expect(reopened.bytes(0).slice(pos, pos + 32)).toEqual(
    raw.slice(pos, pos + 32),
  );
});

it("round-trips preset symbols and retains existing mixed encodings when contents change", () => {
  const session = Session.open(fixture(), "NR0000.dbb");
  const preset = {
    type: "preset" as const,
    hero: 7,
    vessel: 19000,
    handles: [0xc0800054, 0, 0, 0, 0, 0],
    name: "<隐士>#?%＼¥🪄",
  };
  session.apply(0, preset);
  let c = new Character(session.bytes(0));
  let p = c.loadouts!.presets[0];
  expect(p.name).toBe(preset.name);
  expect(c.b.text(p.offset + 4, 18)).toBe("㉑隐士㉒⑲⑳㉓㉔㉕🪄");
  // A native save can also contain literal symbols. Viewing/editing other fields
  // must not rewrite their representation just because the display is decoded.
  const raw = session.bytes(0).slice();
  new Binary(raw).putText(p.offset + 4, 18, "<隐士㉒#⑳");
  const mixed = Session.open(fixture({ 0: raw }), "mixed");
  const before = mixed.bytes(0).slice();
  mixed.apply(0, { ...preset, name: "<隐士>#?", index: p.index });
  expect(equal(mixed.bytes(0), before)).toBe(true);
  mixed.apply(0, {
    ...preset,
    name: "<隐士>#?",
    index: p.index,
    handles: [0, 0, 0, 0, 0, 0],
  });
  c = new Character(Session.open(mixed.export(), "reopen").bytes(0));
  p = c.loadouts!.presets[0];
  expect(c.b.text(p.offset + 4, 18)).toBe("<隐士㉒#⑳");
  expect(p.name).toBe("<隐士>#?");
});
