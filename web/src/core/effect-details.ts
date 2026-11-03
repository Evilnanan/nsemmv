import raw from "../data/effect-details.json" with { type: "json" };
import { catalog } from "./catalog";

export interface EffectDetail {
  info: string | null;
  blocks: {
    source: number;
    branches?: number[];
    phase: string;
    linked: boolean;
    values: [string, string][];
    scope: string[];
    restrictions: string[];
    duration: number | null;
    interval: number | null;
  }[];
  stacking: "不可叠加" | "可叠加" | "不同等级可叠加" | "待确认";
  stackingDetail: string;
  notes: string[];
}
const details = raw.effects as unknown as Record<number, EffectDetail>;
// A mismatched dataset must never present values for the active profile.
export function effectDetail(id: number): EffectDetail | undefined {
  return raw.schema === 2 && raw.regulationSha256 === catalog.regulationSha256
    ? details[id]
    : undefined;
}
