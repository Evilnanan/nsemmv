import { Binary, EMPTY, concat, invariant } from "./binary";
import { catalog, heroNames } from "./catalog";
import { type Roll, requireRoll, toRoll, values } from "./rules";
export interface ItemRecord {
  handle: number;
  id: number;
  offset: number;
  size: number;
  index: number;
  kind: number;
}
export interface Relic {
  handle: number;
  id: number;
  roll: Roll;
  stateOffset: number;
  entryOffset: number;
  favorite: boolean;
  acquisition: number;
  bank: number;
}
export interface Vessel {
  id: number;
  hero: number;
  offset: number;
  handles: number[];
}
export interface Hero {
  id: number;
  offset: number;
  currentVessel: number;
  currentPreset: number;
}
export interface Preset {
  slot: number;
  index: number;
  offset: number;
  hero: number;
  vessel: number;
  handles: number[];
  name: string;
  counter: number;
}
export interface Loadouts {
  base: number;
  presetBase: number;
  heroes: Hero[];
  vessels: Vessel[];
  presets: Preset[];
}
const STATES = 5120,
  ENTRIES = 2688,
  KEY_ENTRIES = 384,
  RELIC_KIND = 0xc0000000;
export const DEFAULT_GOODS = [
  9600, 9603, 9606, 9609, 9612, 9615, 9618, 9621, 9900, 9910,
];
export class Character {
  readonly b: Binary;
  readonly records: ItemRecord[] = [];
  readonly relics: Relic[] = [];
  readonly goods = new Set<number>(DEFAULT_GOODS);
  readonly stateEnd: number;
  readonly nameOffset: number;
  readonly entriesOffset: number;
  readonly countOffset: number;
  readonly name: string;
  readonly banks: {
    countOffset: number;
    entriesOffset: number;
    capacity: number;
    used: number;
  }[] = [];
  readonly inventoryEnd: number;
  readonly loadouts: Loadouts | null;
  constructor(readonly bytes: Uint8Array) {
    this.b = new Binary(bytes);
    const b = this.b;
    invariant(bytes.length >= 100000, "角色区段过短");
    invariant(b.u32(4) === 308, "不支持的角色存档版本（需要 308）");
    let p = 20;
    const byHandle = new Map<number, ItemRecord>();
    for (let index = 0; index < STATES; index++) {
      const handle = b.u32(p),
        kind = (handle & 0xf0000000) >>> 0,
        id = b.u32(p + 4) & 0xffffff;
      invariant(
        handle === 0 || [0x80000000, 0x90000000, RELIC_KIND].includes(kind),
        "未知物品记录类型",
      );
      const size =
        handle === 0
          ? 8
          : kind === 0x80000000
            ? 88
            : kind === 0x90000000
              ? 16
              : 80;
      b.range(p, size);
      const record = { handle, id, kind, size, index, offset: p };
      this.records.push(record);
      if (handle) {
        invariant(!byHandle.has(handle), "物品实例 handle 重复");
        byHandle.set(handle, record);
      }
      p += size;
    }
    this.stateEnd = p;
    this.nameOffset = p + 0x94;
    this.name = b.text(this.nameOffset, 16);
    this.countOffset = this.nameOffset + 0x5b8;
    this.entriesOffset = this.countOffset + 4;
    let cursor = this.countOffset;
    const used = new Set<number>();
    for (const [bank, capacity] of [ENTRIES, KEY_ENTRIES].entries()) {
      const countOffset = cursor,
        entriesOffset = cursor + 4;
      b.range(entriesOffset, capacity * 14);
      let count = 0;
      for (let i = 0; i < capacity; i++) {
        const offset = entriesOffset + i * 14,
          handle = b.u32(offset);
        if (!handle) continue;
        count++;
        const kind = (handle & 0xf0000000) >>> 0;
        if (kind === 0xb0000000 && b.u32(offset + 4) > 0)
          this.goods.add(handle & 0x0fffffff);
        if (kind !== RELIC_KIND) continue;
        const record = byHandle.get(handle);
        invariant(
          record && !used.has(handle) && b.u32(offset + 4) === 1,
          "遗物库存引用损坏",
        );
        used.add(handle);
        const v = [16, 20, 24, 56, 60, 64].map((n) => b.u32(record.offset + n));
        this.relics.push({
          handle,
          id: record.id,
          roll: toRoll(v),
          stateOffset: record.offset,
          entryOffset: offset,
          favorite: !!b.u8(offset + 12),
          acquisition: b.u32(offset + 8),
          bank,
        });
      }
      // Existing count mismatches are retained on read. An inventory mutation updates its own bank.
      this.banks.push({ countOffset, entriesOffset, capacity, used: count });
      cursor = entriesOffset + capacity * 14;
    }
    this.inventoryEnd = cursor;
    b.range(cursor, 8);
    this.loadouts = this.locateLoadouts();
  }
  get hasUnresolvedLoadouts() {
    return this.loadouts === null;
  }
  equipped(handle: number) {
    return (
      this.loadouts?.vessels.some((v) => v.handles.includes(handle)) ||
      this.loadouts?.presets.some((p) => p.handles.includes(handle)) ||
      false
    );
  }
  owners(handle: number) {
    return [
      ...new Set(
        [...(this.loadouts?.vessels ?? []), ...(this.loadouts?.presets ?? [])]
          .filter((v) => v.handles.includes(handle))
          .map((v) => heroNames[v.hero]),
      ),
    ].join(" / ");
  }
  private locateLoadouts(): Loadouts | null {
    // Structural search: capacity + ten distinct hero records + catalog-backed vessels.
    // No hard-coded bytes from unrelated sections and no writes during discovery.
    const b = this.b,
      matches: Loadouts[] = [];
    const handles = new Set(this.relics.map((r) => r.handle));
    const validHandles = (p: number) =>
      Array.from({ length: 6 }, (_, i) => b.u32(p + i * 4)).every(
        (h) => h === 0 || handles.has(h),
      );
    for (
      let p = this.inventoryEnd + 8;
      p + 1200 + 4 + 8000 <
      Math.min(this.bytes.length - 28, this.inventoryEnd + 400000);
      p++
    ) {
      if (b.u32(p) !== 100 || b.u8(p + 4) !== 1 || b.u8(p + 124) !== 2)
        continue;
      try {
        const heroes: Hero[] = [],
          vessels: Vessel[] = [],
          presets: Preset[] = [];
        let cursor = p + 4;
        const readVessel = (hero: number) => {
          const id = b.u32(cursor),
            v = catalog.vessels[id];
          invariant(
            v && (v.hero === hero || v.hero === 11) && validHandles(cursor + 4),
            "器皿结构不匹配",
          );
          vessels.push({
            id,
            hero,
            offset: cursor,
            handles: Array.from({ length: 6 }, (_, i) =>
              b.u32(cursor + 4 + i * 4),
            ),
          });
          cursor += 28;
        };
        for (let id = 1; id <= 10; id++) {
          invariant(b.u8(cursor) === id, "角色序列不匹配");
          const currentVessel = b.u32(cursor + 4);
          invariant(!!catalog.vessels[currentVessel], "未知当前器皿");
          heroes.push({
            id,
            offset: cursor,
            currentPreset: b.u8(cursor + 1),
            currentVessel,
          });
          cursor += 8;
          for (let i = 0; i < 4; i++) readVessel(id);
        }
        let count = 0;
        while (b.u32(cursor) !== 0) {
          const v = catalog.vessels[b.u32(cursor)];
          invariant(v && v.hero !== 11 && count++ < 100, "器皿列表损坏");
          readVessel(v.hero);
        }
        invariant(count >= 60, "器皿列表不完整");
        cursor += 4;
        const presetBase = cursor;
        b.range(cursor, 8000);
        for (let slot = 0; slot < 100; slot++, cursor += 80) {
          const occupied = b.u8(cursor);
          invariant(occupied === 0 || occupied === 1, "预设状态异常");
          if (!occupied) continue;
          const hero = b.u8(cursor + 1),
            vessel = b.u32(cursor + 44);
          invariant(
            hero >= 1 &&
              hero <= 10 &&
              !!catalog.vessels[vessel] &&
              validHandles(cursor + 48),
            "预设引用异常",
          );
          invariant(
            vessels.some((v) => v.hero === hero && v.id === vessel),
            "预设器皿不属于角色",
          );
          presets.push({
            slot,
            index: slot,
            offset: cursor,
            hero,
            vessel,
            handles: Array.from({ length: 6 }, (_, i) =>
              b.u32(cursor + 48 + i * 4),
            ),
            name: b.text(cursor + 4, 18),
            counter: b.u8(cursor + 3),
          });
        }
        invariant(
          heroes.every((h) => h.currentPreset === 255 || h.currentPreset < 100),
          "当前预设索引异常",
        );
        matches.push({ base: p + 4, presetBase, heroes, vessels, presets });
      } catch {
        /* Reject incomplete structural candidates without mutating the save. */
      }
    }
    invariant(matches.length <= 1, "配装位置不唯一");
    return matches[0] ?? null;
  }
}
export function signature(r: Relic) {
  return [r.id, ...values(r.roll)].join(":");
}
export function validateTransition(before: Character, after: Character) {
  const counts = new Map<string, number>(),
    shopCounts = new Map<number, number>();
  for (const r of before.relics) {
    const s = signature(r);
    counts.set(s, (counts.get(s) ?? 0) + 1);
    shopCounts.set(r.id, (shopCounts.get(r.id) ?? 0) + 1);
  }
  const current = new Map<number, number>();
  for (const r of after.relics) {
    const s = signature(r),
      remaining = counts.get(s) ?? 0;
    if (remaining > 0) counts.set(s, remaining - 1);
    else requireRoll(r.id, r.roll);
    current.set(r.id, (current.get(r.id) ?? 0) + 1);
  }
  for (const [id, count] of current)
    if (catalog.relics[id]?.shop)
      invariant(
        count <= Math.max(1, shopCounts.get(id) ?? 0),
        "不能增加商店遗物的重复副本",
      );
}
export function editRelic(
  bytes: Uint8Array,
  handle: number,
  id: number,
  roll: Roll,
) {
  const c = new Character(bytes);
  requireRoll(id, roll);
  const r = c.relics.find((x) => x.handle === handle);
  invariant(r, "遗物不存在");
  invariant(
    !catalog.relics[r.id]?.shop && !catalog.relics[id]?.shop,
    "商店遗物不能修改",
  );
  const target = catalog.relics[id],
    old = catalog.relics[r.id];
  invariant(old && old.deep === target.deep, "不能互换普通与深层遗物");
  invariant(
    old.color === target.color || (c.loadouts && !c.equipped(handle)),
    "已装备或配装未知时不能改变遗物颜色",
  );
  const out = bytes.slice(),
    b = new Binary(out);
  b.put32(r.stateOffset + 4, (0x80000000 | id) >>> 0);
  b.put32(r.stateOffset + 8, (0x80000000 | id) >>> 0);
  values(roll).forEach((v, i) =>
    b.put32(r.stateOffset + [16, 20, 24, 56, 60, 64][i], v),
  );
  validateTransition(c, new Character(out));
  return out;
}
export function setFavorite(
  bytes: Uint8Array,
  handle: number,
  favorite: boolean,
) {
  const c = new Character(bytes),
    r = c.relics.find((r) => r.handle === handle);
  invariant(r, "遗物不存在");
  const out = bytes.slice();
  out[r.entryOffset + 12] = Number(favorite);
  return out;
}
// Fixed-capacity USERDATA stream; the allocator tail is not a serialized item record.
// Preserve its discarded bytes in the undo snapshot and original-file download.
function replaceRecord(
  bytes: Uint8Array,
  record: ItemRecord,
  replacement: Uint8Array,
) {
  const end = bytes.length - 28,
    delta = replacement.length - record.size;
  invariant(record.offset + record.size < end, "记录越界");
  if (delta > 0)
    return concat(
      bytes.subarray(0, record.offset),
      replacement,
      bytes.subarray(record.offset + record.size, end - delta),
      bytes.subarray(end),
    );
  return concat(
    bytes.subarray(0, record.offset),
    replacement,
    bytes.subarray(record.offset + record.size, end),
    new Uint8Array(-delta),
    bytes.subarray(end),
  );
}
export function addRelic(
  bytes: Uint8Array,
  id: number,
  roll: Roll,
): { bytes: Uint8Array; handle: number } {
  requireRoll(id, roll);
  const c = new Character(bytes);
  invariant(c.loadouts, "配装结构未识别，不能新增遗物");
  invariant(
    !catalog.relics[id].shop || !c.relics.some((r) => r.id === id),
    "商店遗物已存在",
  );
  const referencedIndices = new Set(
    c.records.filter((r) => r.handle).map((r) => r.handle & 0xffff),
  );
  const record = c.records.find(
    (r) => !r.handle && r.index >= 84 && !referencedIndices.has(r.index),
  );
  invariant(record, "物品状态槽已满");
  let entry = -1;
  for (let i = 0; i < ENTRIES; i++)
    if (c.b.u32(c.entriesOffset + i * 14) === 0) {
      entry = i;
      break;
    }
  invariant(entry >= 0, "库存已满");
  // Native handle = kind | live bit | generation (7 bits) | state index (16 bits).
  // Never use an ever-growing inventory serial as the state index.
  let generation = 0,
    handle = (RELIC_KIND | 0x800000 | record.index) >>> 0;
  while (c.records.some((r) => r.handle === handle) && generation < 127) {
    generation++;
    handle = (RELIC_KIND | 0x800000 | (generation << 16) | record.index) >>> 0;
  }
  invariant(!c.records.some((r) => r.handle === handle), "实例 ID 已耗尽");
  const data = new Uint8Array(80),
    b = new Binary(data);
  b.put32(0, handle);
  b.put32(4, (0x80000000 | id) >>> 0);
  b.put32(8, (0x80000000 | id) >>> 0);
  for (const p of [12, 16, 20, 24, 28, 32, 48, 52, 56, 60, 64, 68])
    b.put32(p, EMPTY);
  data[39] = 255;
  values(roll).forEach((v, i) => b.put32([16, 20, 24, 56, 60, 64][i], v));
  const out = replaceRecord(bytes, record, data),
    ob = new Binary(out),
    offset = c.entriesOffset + 72 + entry * 14;
  ob.put32(c.countOffset + 72, c.banks[0].used + 1);
  ob.put32(offset, handle);
  ob.put32(offset + 4, 1);
  let latest = 0;
  for (const bank of c.banks)
    for (let i = 0; i < bank.capacity; i++) {
      const at = bank.entriesOffset + i * 14;
      if (c.b.u32(at)) latest = Math.max(latest, c.b.u32(at + 8));
    }
  const acquisition = Math.max(c.b.u32(c.inventoryEnd + 4), latest + 1);
  invariant(acquisition < EMPTY, "获取顺序 ID 已耗尽");
  ob.put32(offset + 8, acquisition);
  ob.put8(offset + 12, 0);
  ob.put8(offset + 13, 1);
  ob.put32(
    c.inventoryEnd + 72,
    Math.max(c.b.u32(c.inventoryEnd), entry + KEY_ENTRIES),
  );
  ob.put32(c.inventoryEnd + 76, acquisition + 1);
  const after = new Character(out);
  invariant(after.loadouts, "新增后配装结构异常");
  validateTransition(c, after);
  return { bytes: out, handle };
}
export function removeRelic(bytes: Uint8Array, handle: number) {
  const c = new Character(bytes),
    r = c.relics.find((r) => r.handle === handle);
  invariant(r, "遗物不存在");
  invariant(!catalog.relics[r.id]?.shop, "商店遗物不能删除");
  invariant(c.loadouts && !c.equipped(handle), "遗物被配装引用，不能删除");
  const record = c.records.find((r) => r.handle === handle)!;
  const blank = new Uint8Array(8);
  new Binary(blank).put32(4, EMPTY);
  const out = replaceRecord(bytes, record, blank),
    b = new Binary(out);
  out.fill(0, r.entryOffset - 72, r.entryOffset - 72 + 14);
  b.put32(c.banks[r.bank].countOffset - 72, c.banks[r.bank].used - 1);
  validateTransition(c, new Character(out));
  return out;
}
export function validateLoadout(
  c: Character,
  hero: number,
  vessel: number,
  handles: number[],
) {
  invariant(
    c.loadouts &&
      c.loadouts.vessels.some((v) => v.hero === hero && v.id === vessel),
    "器皿不可用",
  );
  const meta = catalog.vessels[vessel];
  invariant(c.goods.has(meta.goods), "尚未持有该器皿");
  invariant(handles.length === 6, "需要六个遗物槽");
  const seen = new Set<number>();
  handles.forEach((h, i) => {
    if (!h) return;
    const r = c.relics.find((r) => r.handle === h),
      m = r && catalog.relics[r.id];
    invariant(r && m && !seen.has(h), "遗物不存在或重复");
    seen.add(h);
    invariant(
      m.deep === i >= 3 && (meta.colors[i] === 4 || m.color === meta.colors[i]),
      "遗物类型或颜色不匹配",
    );
  });
}
// Native 0x1e17a0 / comparator 0x1df1b0: counter ascending, timestamp descending.
function normalizePresetCounters(b: Binary, presets: Preset[]) {
  [...presets]
    .sort(
      (a, c) =>
        a.counter - c.counter ||
        Number(
          b.view.getBigUint64(c.offset + 72, true) -
            b.view.getBigUint64(a.offset + 72, true),
        ),
    )
    .forEach((p, i) => b.put8(p.offset + 3, i));
}
function clearPreset(b: Binary, p: Preset) {
  // 0x1dfeb0 leaves the old name, counter and reserved bytes intact.
  b.put8(p.offset, 0);
  b.put8(p.offset + 1, 0);
  b.put32(p.offset + 44, EMPTY);
  for (let i = 0; i < 6; i++) b.put32(p.offset + 48 + i * 4, 0);
  b.view.setBigUint64(p.offset + 72, 0n, true);
}
function refreshPresetSelection(b: Binary, l: Loadouts, heroes: Hero[]) {
  // 0x1e1b10 chooses the newest matching vessel + six handles; indices stay physical.
  const active = l.presets.filter((p) => b.u8(p.offset) !== 0);
  for (const h of heroes) {
    const vessel = l.vessels.find(
      (v) => v.hero === h.id && v.id === h.currentVessel,
    );
    const found = active
      .filter(
        (p) =>
          p.vessel === h.currentVessel &&
          vessel &&
          p.handles.join() === vessel.handles.join(),
      )
      .sort((a, c) => b.u8(a.offset + 3) - b.u8(c.offset + 3))[0];
    b.put8(h.offset + 1, found?.index ?? 255);
  }
}
export function savePreset(
  bytes: Uint8Array,
  hero: number,
  vessel: number,
  handles: number[],
  name: string,
  index?: number,
) {
  const c = new Character(bytes);
  validateLoadout(c, hero, vessel, handles);
  invariant(name.trim(), "预设名称不能为空");
  const l = c.loadouts!,
    out = bytes.slice(),
    b = new Binary(out),
    existing =
      index === undefined
        ? undefined
        : l.presets.find((p) => p.index === index);
  invariant(index === undefined || existing, "预设不存在");
  const sameContents =
    existing &&
    existing.hero === hero &&
    existing.vessel === vessel &&
    existing.handles.join() === handles.join();
  if (sameContents) {
    if (existing.name === name.trim()) return out;
    b.putText(existing.offset + 4, 18, name.trim());
    b.put8(existing.offset + 40, 0);
    b.put8(existing.offset + 41, 0);
    return out;
  }
  const slot =
    existing?.slot ??
    Array.from({ length: 100 }, (_, i) => i).find(
      (i) => !l.presets.some((p) => p.slot === i),
    ) ??
    100;
  invariant(slot < 100, "预设已满");
  const p = l.presetBase + slot * 80;
  let remaining = l.presets;
  if (existing) {
    clearPreset(b, existing);
    remaining = l.presets.filter((x) => x.index !== index);
    normalizePresetCounters(b, remaining);
  } else invariant(b.u8(p) === 0, "预设槽已占用");
  if (remaining.some((p) => b.u8(p.offset + 3) === 255))
    normalizePresetCounters(b, remaining);
  for (const old of remaining) b.put8(old.offset + 3, b.u8(old.offset + 3) + 1);
  b.put8(p, 1);
  b.put8(p + 1, hero);
  b.put8(p + 3, 0);
  b.putText(p + 4, 18, name.trim());
  b.put8(p + 40, 0);
  b.put8(p + 41, 0);
  b.put32(p + 44, vessel);
  handles.forEach((h, i) => b.put32(p + 48 + i * 4, h));
  b.view.setBigUint64(
    p + 72,
    (BigInt(Date.now()) + 11644473600000n) * 10000n,
    true,
  );
  const after = new Character(out);
  invariant(
    after.loadouts?.presets.length === l.presets.length + (existing ? 0 : 1),
    "预设写入失败",
  );
  refreshPresetSelection(
    b,
    after.loadouts!,
    after.loadouts!.heroes.filter(
      (h) => h.id === hero || (existing && h.currentPreset === index),
    ),
  );
  return out;
}
export function equipPreset(bytes: Uint8Array, index: number) {
  const c = new Character(bytes),
    p = c.loadouts?.presets.find((p) => p.index === index);
  invariant(p, "预设不存在");
  validateLoadout(c, p.hero, p.vessel, p.handles);
  const h = c.loadouts!.heroes.find((h) => h.id === p.hero)!,
    v = c.loadouts!.vessels.find(
      (v) => v.hero === p.hero && v.id === p.vessel,
    )!;
  const out = bytes.slice(),
    b = new Binary(out);
  b.put8(h.offset + 1, p.index);
  b.put32(h.offset + 4, p.vessel);
  p.handles.forEach((h, i) => b.put32(v.offset + 4 + i * 4, h));
  return out;
}

export function deletePreset(bytes: Uint8Array, index: number) {
  const c = new Character(bytes),
    l = c.loadouts,
    p = l?.presets.find((p) => p.index === index);
  invariant(l && p, "预设不存在");
  const out = bytes.slice(),
    b = new Binary(out);
  clearPreset(b, p);
  const remaining = l.presets.filter((r) => r.index !== index);
  normalizePresetCounters(b, remaining);
  refreshPresetSelection(
    b,
    l,
    l.heroes.filter((h) => h.currentPreset === index),
  );
  invariant(
    new Character(out).loadouts?.presets.length === l.presets.length - 1,
    "预设删除失败",
  );
  return out;
}
