import type { SessionView } from "./session";

export type UsageFilter = "all" | "unshared" | "unused" | "current" | "other";

export function matchesUsage(
  usage: ReturnType<typeof relicUsage>,
  hero: number,
  filter: UsageFilter,
) {
  if (filter === "all") return true;
  if (!usage) return false;
  switch (filter) {
    case "unshared":
      return usage.every((row) => row.hero === hero);
    case "unused":
      return usage.length === 0;
    case "current":
      return usage.some((row) => row.hero === hero);
    case "other":
      return usage.some((row) => row.hero !== hero);
  }
}

export function relicUsage(loadouts: SessionView["loadouts"], handle: number) {
  if (!loadouts) return null;
  return loadouts.heroes.flatMap((hero) => {
    const vessels = loadouts.vessels
      .filter((v) => v.hero === hero.id && v.handles.includes(handle))
      .map((v) => ({ id: v.id, equipped: v.id === hero.currentVessel }));
    const presets = loadouts.presets
      .filter((p) => p.hero === hero.id && p.handles.includes(handle))
      .map((p) => ({ index: p.index, name: p.name }));
    return vessels.length || presets.length
      ? [{ hero: hero.id, vessels, presets }]
      : [];
  });
}
