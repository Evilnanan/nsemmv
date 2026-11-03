import { catalog, effectName } from "./catalog";

// -1 keeps future/unmapped MMV entries discoverable without guessing from their text.
export const UNCLASSIFIED = -1;
export function effectGroup(id: number) {
  return catalog.effects[id]?.group ?? UNCLASSIFIED;
}
export function filterEffects(
  choices: number[],
  query: string,
  group: number | null,
) {
  const search = query.trim().toLowerCase();
  return choices.filter(
    (id) =>
      (group === null || effectGroup(id) === group) &&
      `${id} ${effectName(id)}`.toLowerCase().includes(search),
  );
}
