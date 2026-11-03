export const EMPTY = 0xffffffff;
export function invariant(ok: unknown, message: string): asserts ok {
  if (!ok) throw new Error(message);
}
export function uint(value: number, max = EMPTY) {
  invariant(
    Number.isInteger(value) && value >= 0 && value <= max,
    "数值超出范围",
  );
  return value;
}
export class Binary {
  readonly view: DataView;
  constructor(readonly bytes: Uint8Array) {
    this.view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  }
  range(offset: number, size: number) {
    invariant(
      Number.isInteger(offset) &&
        offset >= 0 &&
        size >= 0 &&
        offset + size <= this.bytes.length,
      "存档字段越界",
    );
  }
  u8(p: number) {
    this.range(p, 1);
    return this.bytes[p];
  }
  u32(p: number) {
    this.range(p, 4);
    return this.view.getUint32(p, true);
  }
  put32(p: number, value: number) {
    this.range(p, 4);
    this.view.setUint32(p, uint(value), true);
  }
  put8(p: number, value: number) {
    this.range(p, 1);
    this.bytes[p] = uint(value, 255);
  }
  text(p: number, units: number) {
    this.range(p, units * 2);
    return new TextDecoder("utf-16le", { fatal: true })
      .decode(this.bytes.subarray(p, p + units * 2))
      .split("\0")[0];
  }
  putText(p: number, units: number, value: string) {
    invariant(
      value.length <= units && !value.includes("\0"),
      `名称最多 ${units} 个 UTF-16 字符`,
    );
    this.range(p, units * 2);
    this.bytes.fill(0, p, p + units * 2);
    for (let i = 0; i < value.length; i++)
      this.view.setUint16(p + i * 2, value.charCodeAt(i), true);
  }
}
export function equal(a: Uint8Array, b: Uint8Array) {
  return a.length === b.length && a.every((x, i) => x === b[i]);
}
export function concat(...parts: Uint8Array[]) {
  const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
  let at = 0;
  for (const p of parts) {
    out.set(p, at);
    at += p.length;
  }
  return out;
}
