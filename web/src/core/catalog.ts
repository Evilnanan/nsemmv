import raw from "../data/catalog.json" with { type: "json" };
export type Locale = "zh_CN" | "en_US";
export type Names = Record<Locale, string>;
export interface Effect {
  id: number;
  name: Names;
  conflict: number;
  exclusive: number;
  sort: number;
}
export interface RelicDefinition {
  id: number;
  name: Names;
  color: number;
  deep: boolean;
  obtainable: boolean;
  salable: boolean;
  shop: boolean;
  pools: number[];
}
export interface VesselDefinition {
  id: number;
  name: Names;
  hero: number;
  goods: number;
  unlockFlag: number;
  colors: number[];
}
export interface Catalog {
  schema: number;
  profile: string;
  regulationVersion: string;
  regulationSha256: string;
  effects: Record<number, Effect>;
  relics: Record<number, RelicDefinition>;
  vessels: Record<number, VesselDefinition>;
  pools: Record<number, number[]>;
}
export const catalog = raw as Catalog;
export const relicDefinitions = Object.values(catalog.relics).filter(
  (r) => r.obtainable,
);
export const poolSets = new Map(
  Object.entries(catalog.pools).map(([k, v]) => [Number(k), new Set(v)]),
);
export const heroNames = [
  "",
  "追踪者",
  "守护者",
  "铁之眼",
  "女爵",
  "无赖",
  "复仇者",
  "隐士",
  "执行者",
  "学者",
  "送葬者",
];
export const colorNames = ["红", "蓝", "黄", "绿", "白"];
export function effectName(id: number) {
  return id === 0xffffffff || id === 0
    ? "—"
    : (catalog.effects[id]?.name.zh_CN ?? `未知词条 ${id}`);
}
