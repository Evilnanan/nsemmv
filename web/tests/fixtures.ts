import { Binary, EMPTY, concat } from "../src/core/binary";
import { catalog } from "../src/core/catalog";
import { cbc } from "@noble/ciphers/aes";
import { md5 } from "@noble/hashes/legacy";
export function character() {
  const data = new Uint8Array(1048608),
    b = new Binary(data);
  b.put32(0, data.length - 16);
  b.put32(4, 308);
  for (let i = 0; i < 5120; i++) b.put32(20 + i * 8 + 4, EMPTY);
  const state = 20 + 84 * 8;
  b.put32(state, 0xc0800054);
  b.put32(state + 4, 0x80000064);
  b.put32(state + 8, 0x80000064);
  [12, 16, 20, 24, 28, 32, 48, 52, 56, 60, 64, 68].forEach((o) =>
    b.put32(state + o, EMPTY),
  );
  b.put32(state + 16, 7000000);
  const end = 20 + 5120 * 8 + 72;
  b.putText(end + 0x94, 16, "Test 隐士");
  const entry = end + 0x94 + 0x5b8 + 4;
  b.put32(entry - 4, 2);
  b.put32(entry, 0xc0800054);
  b.put32(entry + 4, 1);
  b.put32(entry + 8, 1);
  b.put32(entry + 14, (0xb0000000 | catalog.vessels[19000].goods) >>> 0);
  b.put32(entry + 18, 1);
  b.put32(entry + 22, 2);
  const inventoryEnd = entry + 2688 * 14 + 4 + 384 * 14;
  b.put32(inventoryEnd, 385);
  b.put32(inventoryEnd + 4, 3);
  let p = inventoryEnd + 8 + 100;
  b.put32(p, 100);
  p += 4;
  for (let hero = 1; hero <= 10; hero++) {
    b.put8(p, hero);
    b.put8(p + 1, 255);
    b.put32(p + 4, hero * 1000);
    p += 8;
    for (const id of [19000, 19001, 19002, 19010]) {
      b.put32(p, id);
      p += 28;
    }
  }
  for (const v of Object.values(catalog.vessels).filter((v) => v.hero !== 11)) {
    b.put32(p, v.id);
    p += 28;
  }
  b.put32(p, 0);
  for (let i = 0; i < 100; i++) b.put32(p + 4 + i * 80 + 44, EMPTY);
  data.set(new TextEncoder().encode("OPAQUE-MUST-SURVIVE"), p + 4 + 8000 + 100);
  return data;
}
export function fixture(
  chars: Record<number, Uint8Array> = { 0: character() },
  summary?: Uint8Array,
) {
  const key = Uint8Array.from([
    0x18, 0xf6, 0x32, 0x66, 0x05, 0xbd, 0x17, 0x8a, 0x55, 0x24, 0x52, 0x3a,
    0xc0, 0xa0, 0xc6, 0x09,
  ]);
  const global = summary?.slice() ?? new Uint8Array(256);
  for (const slot of Object.keys(chars)) global[32 + Number(slot)] = 1;
  global.set([39, 0, 0, 70, 65, 67, 69], 93);
  const payloads = Array.from({ length: 11 }, (_, i) =>
    i === 10 ? global : (chars[i] ?? new Uint8Array(256)),
  );
  const header = new Uint8Array(1024),
    b = new Binary(header);
  header.set(new TextEncoder().encode("BND4"));
  b.put32(12, 11);
  let offset = 1024;
  const entries = payloads.map((input, index) => {
    const raw = input.slice(),
      end = raw.length - 28;
    raw.set(md5(raw.subarray(4, end)), end);
    const iv = new Uint8Array(16).fill(index + 1),
      data = concat(iv, cbc(key, iv, { disablePadding: true }).encrypt(raw));
    const p = 64 + index * 32;
    b.put32(p, 64);
    b.put32(p + 4, EMPTY);
    b.put32(p + 8, data.length);
    b.put32(p + 16, offset);
    offset += data.length;
    return data;
  });
  return concat(
    header,
    ...entries,
    new TextEncoder().encode("UNKNOWN-CONTAINER-TAIL"),
  );
}
