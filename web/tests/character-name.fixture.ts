import { Binary } from "../src/core/binary";
import { Character } from "../src/core/character";
import { character, fixture } from "./fixtures";

export function nameFixture(names = ["OvO", ",㉒_㉑,"]) {
  const chars = { 0: character(), 1: character() };
  const summary = new Uint8Array(6656),
    b = new Binary(summary);
  for (const [slot, raw] of Object.entries(chars)) {
    const offset = new Character(raw).nameOffset;
    new Binary(raw).putText(offset, 16, names[Number(slot)]);
    const target = 42 + Number(slot) * 0x290;
    summary.set(raw.subarray(offset, offset + 32), target);
    summary.set([39, 0, 0, 70, 65, 67, 69], target + 51);
    if (Number(slot)) b.put32(target - 6, 0x104);
  }
  return fixture(chars, summary);
}
