import { cbc } from "@noble/ciphers/aes";
import { md5 } from "@noble/hashes/legacy";
import { Binary, equal, invariant } from "./binary";
const KEY = Uint8Array.from([
  0x18, 0xf6, 0x32, 0x66, 0x05, 0xbd, 0x17, 0x8a, 0x55, 0x24, 0x52, 0x3a, 0xc0,
  0xa0, 0xc6, 0x09,
]);
export interface ContainerEntry {
  index: number;
  offset: number;
  size: number;
  plain: Uint8Array;
}
export class SaveContainer {
  readonly entries: ContainerEntry[] = [];
  private constructor(readonly original: Uint8Array) {}
  static open(input: Uint8Array) {
    const bytes = input.slice(),
      b = new Binary(bytes);
    invariant(
      bytes.length >= 64 &&
        new TextDecoder().decode(bytes.subarray(0, 4)) === "BND4",
      "不是受支持的 PC 存档",
    );
    const count = b.u32(12);
    invariant(count >= 11 && count <= 64, "存档目录数量异常");
    b.range(64, count * 32);
    const container = new SaveContainer(bytes);
    const ranges: { start: number; end: number }[] = [];
    for (let index = 0; index < count; index++) {
      const p = 64 + index * 32;
      invariant(
        b.u32(p) === 64 && b.u32(p + 4) === 0xffffffff,
        "不支持的 BND4 目录布局",
      );
      const size = b.u32(p + 8),
        offset = b.u32(p + 16);
      invariant(
        size >= 48 && (size - 16) % 16 === 0 && offset >= 64 + count * 32,
        "存档区段尺寸异常",
      );
      b.range(offset, size);
      invariant(
        !ranges.some((r) => offset < r.end && offset + size > r.start),
        "存档区段重叠",
      );
      ranges.push({ start: offset, end: offset + size });
      const plain = cbc(KEY, bytes.subarray(offset, offset + 16), {
        disablePadding: true,
      }).decrypt(bytes.subarray(offset + 16, offset + size));
      const end = plain.length - 28;
      invariant(
        end >= 4 &&
          equal(md5(plain.subarray(4, end)), plain.subarray(end, end + 16)),
        `区段 ${index} 校验和错误`,
      );
      container.entries.push({ index, offset, size, plain });
    }
    return container;
  }
  write(changes: Map<number, Uint8Array>) {
    const out = this.original.slice();
    for (const [index, plain] of changes) {
      const entry = this.entries[index];
      invariant(entry && plain.length === entry.plain.length, "区段长度改变");
      if (equal(plain, entry.plain)) continue;
      const data = plain.slice(),
        end = data.length - 28;
      data.set(md5(data.subarray(4, end)), end);
      const iv = crypto.getRandomValues(new Uint8Array(16));
      out.set(iv, entry.offset);
      out.set(
        cbc(KEY, iv, { disablePadding: true }).encrypt(data),
        entry.offset + 16,
      );
    }
    return out;
  }
  occupied(): number[] {
    const bytes = this.entries[10].plain,
      marker = [39, 0, 0, 70, 65, 67, 69],
      matches: number[][] = [];
    for (let p = 61; p + marker.length <= bytes.length; p++)
      if (marker.every((v, i) => bytes[p + i] === v)) {
        const flags = [...bytes.subarray(p - 61, p - 51)];
        if (flags.every((v) => v === 0 || v === 1))
          matches.push(flags.flatMap((v, i) => (v ? [i] : [])));
      }
    invariant(matches.length === 1, "角色目录无法唯一识别");
    return matches[0];
  }
}
