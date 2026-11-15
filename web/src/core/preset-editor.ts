import { catalog, effectName } from "./catalog";
import type { SessionView } from "./session";

type Relic = SessionView["relics"][number];

export function fitsPresetSlot(relic: Relic, colors: number[], slot: number) {
  const meta = catalog.relics[relic.id];
  return (
    !!meta &&
    meta.deep === slot >= 3 &&
    (colors[slot] === 4 || colors[slot] === meta.color)
  );
}

/** Keep as many existing relics as possible, preferring their original slots.
 * Exhaustive matching matters for vessels with both wildcard and colored slots.
 */
export function fitPresetHandles(
  handles: number[],
  colors: number[],
  relics: Relic[],
) {
  const byHandle = new Map(relics.map((r) => [r.handle, r]));
  const candidates = [...new Set(handles.filter((h) => h && byHandle.has(h)))];
  let best = Array<number>(6).fill(0),
    bestScore = -1;
  function visit(
    index: number,
    selected: number[],
    used: Set<number>,
    score: number,
  ) {
    if (index === 6) {
      if (score > bestScore) {
        best = [...selected];
        bestScore = score;
      }
      return;
    }
    for (const handle of candidates) {
      if (
        used.has(handle) ||
        !fitsPresetSlot(byHandle.get(handle)!, colors, index)
      )
        continue;
      used.add(handle);
      visit(
        index + 1,
        [...selected, handle],
        used,
        score + 10 + Number(handles[index] === handle),
      );
      used.delete(handle);
    }
    visit(index + 1, [...selected, 0], used, score);
  }
  visit(0, [], new Set(), 0);
  return best;
}

export function matchesRelicSearch(relic: Relic, query: string) {
  const meta = catalog.relics[relic.id];
  const text = [
    relic.id,
    meta?.name.zh_CN,
    meta?.name.en_US,
    ...relic.roll.flatMap(({ effect, curse }) => [
      effect,
      curse,
      effectName(effect),
      effectName(curse),
    ]),
  ]
    .join(" ")
    .toLocaleLowerCase();
  return query
    .trim()
    .toLocaleLowerCase()
    .split(/\s+/)
    .every((word) => text.includes(word));
}
