import { EMPTY, invariant } from "./binary";
import { catalog, poolSets, relicDefinitions } from "./catalog";
export type Pair = { effect: number; curse: number };
export type Roll = Pair[];
export interface Issue {
  code: string;
  message: string;
  slot?: number;
}
const permutations = [
  [0, 1, 2],
  [0, 2, 1],
  [1, 0, 2],
  [1, 2, 0],
  [2, 0, 1],
  [2, 1, 0],
];
export const empty = (id: number) => id === 0 || id === EMPTY;
export function toRoll(values: number[]): Roll {
  invariant(values.length === 6, "需要三个正面和三个负面槽");
  return values
    .slice(0, 3)
    .map((effect, i) => ({ effect, curse: values[i + 3] }));
}
export function values(roll: Roll) {
  return [...roll.map((p) => p.effect), ...roll.map((p) => p.curse)];
}
export function sortRoll(roll: Roll): Roll {
  return roll
    .map((p) => ({ ...p }))
    .sort(
      (a, b) =>
        (empty(a.effect)
          ? Infinity
          : (catalog.effects[a.effect]?.sort ?? Infinity)) -
          (empty(b.effect)
            ? Infinity
            : (catalog.effects[b.effect]?.sort ?? Infinity)) ||
        (empty(a.effect) ? EMPTY : a.effect) -
          (empty(b.effect) ? EMPTY : b.effect),
    );
}
function effectsConflict(a: number, b: number) {
  if (empty(a) || empty(b)) return false;
  const first = catalog.effects[a],
    second = catalog.effects[b];
  return (
    !!first &&
    !!second &&
    (a === b ||
      (first.conflict !== -1 && first.conflict === second.conflict) ||
      (first.exclusive !== -1 && first.exclusive === second.exclusive))
  );
}
export function candidateConflicts(
  roll: Roll,
  slot: number,
  curse: boolean,
  id: number,
) {
  invariant(
    roll.length === 3 && Number.isInteger(slot) && slot >= 0 && slot < 3,
    "无效词条槽",
  );
  const replaced = slot + (curse ? 3 : 0);
  return values(roll).flatMap((other, index) =>
    index !== replaced && effectsConflict(id, other)
      ? [{ id: other, slot: index }]
      : [],
  );
}
function idsIssues(roll: Roll): Issue[] {
  if (roll.length !== 3)
    return [{ code: "length", message: "需要三个词条配对" }];
  const seen: number[] = [];
  const out: Issue[] = [];
  values(roll).forEach((id, slot) => {
    if (!Number.isInteger(id) || id < 0 || id > EMPTY) {
      out.push({ code: "id", message: "无效词条 ID", slot });
      return;
    }
    if (empty(id)) return;
    const e = catalog.effects[id];
    if (!e) {
      out.push({ code: "unknown", message: `未知词条 ${id}`, slot });
      return;
    }
    if (seen.some((other) => effectsConflict(id, other)))
      out.push({ code: "conflict", message: "词条重复或互斥", slot });
    seen.push(id);
  });
  return out;
}
function poolIssues(id: number, roll: Roll, seq: number[]): Issue[] {
  const pools = catalog.relics[id].pools,
    out: Issue[] = [];
  for (let i = 0; i < 6; i++) {
    const slot = seq[i % 3] + (i >= 3 ? 3 : 0),
      value = i < 3 ? roll[seq[i]].effect : roll[seq[i - 3]].curse,
      p = pools[i];
    if (p === -1) {
      if (!empty(value))
        out.push({
          code: i < 3 ? "extra-effect" : "extra-curse",
          message: i < 3 ? "此槽必须为空" : "此槽不允许 Curse",
          slot,
        });
    } else if (empty(value))
      out.push({
        code: i < 3 ? "missing-effect" : "missing-curse",
        message: i < 3 ? "缺少正面词条" : "缺少 Curse",
        slot,
      });
    else if (!poolSets.get(p)?.has(value))
      out.push({
        code: i < 3 ? "effect-pool" : "curse-pool",
        message: i < 3 ? "不在此遗物的抽取池内" : "Curse 不在对应抽取池内",
        slot,
      });
  }
  return out;
}
export function checkRoll(id: number, roll: Roll, checkOrder = true): Issue[] {
  if (!catalog.relics[id]?.obtainable)
    return [{ code: "item", message: "Item ID 没有有效获取来源" }];
  const ids = idsIssues(roll);
  if (ids.length) return ids;
  const choices = permutations
    .map((s) => poolIssues(id, roll, s))
    .sort((a, b) => score(a) - score(b));
  if (choices[0].length) return choices[0];
  if (checkOrder && values(roll).join() !== values(sortRoll(roll)).join())
    return [{ code: "order", message: "词条顺序需要 Auto Fix" }];
  return [];
}
function score(issues: Issue[]) {
  return issues.reduce((n, x) => n + ((x.slot ?? 0) < 3 ? 100 : 1), 0);
}
export function requireRoll(id: number, roll: Roll) {
  const issues = checkRoll(id, roll);
  invariant(!issues.length, issues.map((x) => x.message).join("；"));
}
export function candidates(id: number) {
  const current = catalog.relics[id];
  if (!current) return [];
  return relicDefinitions.filter(
    (r) =>
      r.id === id ||
      (!r.shop && r.color === current.color && r.deep === current.deep),
  );
}
export interface CandidateAvailability {
  state: "available" | "incomplete" | "unavailable";
  issues: Issue[];
  itemId?: number;
}
// Compile the possible pool assignments once per open picker, then evaluate each ID.
// Empty fields can still be filled; an already selected field must fit its paired pool.
export function effectAvailability(
  itemId: number,
  roll: Roll,
  slot: number,
  curse: boolean,
) {
  invariant(
    roll.length === 3 && Number.isInteger(slot) && slot >= 0 && slot < 3,
    "无效词条槽",
  );
  const target = slot + (curse ? 3 : 0),
    base = roll.map((p) => ({ ...p }));
  base[slot][curse ? "curse" : "effect"] = EMPTY;
  const items = candidates(itemId);
  const possible = new Set(
    items.flatMap((r) =>
      r.pools
        .slice(curse ? 3 : 0, curse ? 6 : 3)
        .flatMap((p) => [...(poolSets.get(p) ?? [])]),
    ),
  );
  const adjustable = new Set([
    "missing-effect",
    "missing-curse",
    "extra-curse",
  ]);
  const plans = items
    .flatMap((r) =>
      permutations.flatMap((seq) => {
        const pool = poolSets.get(r.pools[seq.indexOf(slot) + (curse ? 3 : 0)]);
        if (!pool?.size) return [];
        const issues = poolIssues(r.id, base, seq).filter(
          (i) => i.slot !== target,
        );
        if (issues.some((i) => !adjustable.has(i.code))) return [];
        return [{ id: r.id, pool, issues }];
      }),
    )
    .sort(
      (a, b) =>
        score(a.issues) - score(b.issues) ||
        Number(a.id !== itemId) - Number(b.id !== itemId) ||
        a.id - b.id,
    );
  return (id: number): CandidateAvailability => {
    const selected = base.map((p) => ({ ...p }));
    selected[slot][curse ? "curse" : "effect"] = id;
    const issues = idsIssues(selected);
    if (issues.length) return { state: "unavailable", issues };
    if (!items.length)
      return {
        state: "unavailable",
        issues: [{ code: "item", message: "Item ID 没有有效获取来源" }],
      };
    if (empty(id))
      return {
        state: "incomplete",
        issues: [{ code: "missing-effect", message: "待补齐词条" }],
      };
    if (!possible.has(id))
      return {
        state: "unavailable",
        issues: [
          {
            code: curse ? "curse-pool" : "effect-pool",
            message: curse
              ? "不在此类遗物的 Curse 抽取池内"
              : "不在此类遗物的正面抽取池内",
          },
        ],
      };
    const match = plans.find((p) => p.pool.has(id));
    if (!match)
      return {
        state: "unavailable",
        issues: [
          {
            code: "combination",
            message: "当前正负词条组合无法匹配同色同类型遗物的抽取池",
          },
        ],
      };
    return {
      state: match.issues.length ? "incomplete" : "available",
      issues: match.issues,
      itemId: match.id,
    };
  };
}
export function autoFix(
  id: number,
  roll: Roll,
): { id: number; roll: Roll; issues: Issue[] } {
  const sorted = sortRoll(roll),
    invalid = idsIssues(sorted);
  if (invalid.length) return { id, roll: sorted, issues: invalid };
  const matches = candidates(id).map((r) => ({
    id: r.id,
    issues: checkRoll(r.id, sorted),
  }));
  const exact = matches
    .filter((m) => !m.issues.length)
    .sort(
      (a, b) => Number(a.id !== id) - Number(b.id !== id) || a.id - b.id,
    )[0];
  if (exact) return { ...exact, roll: sorted };
  const partial = matches
    .filter((m) =>
      m.issues.every((i) => ["missing-curse", "extra-curse"].includes(i.code)),
    )
    .sort(
      (a, b) =>
        a.issues.length - b.issues.length ||
        Number(a.id !== id) - Number(b.id !== id) ||
        a.id - b.id,
    )[0];
  return {
    id: partial?.id ?? id,
    roll: sorted,
    issues: partial?.issues ?? checkRoll(id, sorted),
  };
}
export function effectChoices(id: number, curse: boolean) {
  const ids = new Set<number>();
  for (const r of candidates(id))
    for (const p of r.pools.slice(curse ? 3 : 0, curse ? 6 : 3))
      for (const e of poolSets.get(p) ?? []) ids.add(e);
  return [...ids].sort((a, b) => a - b);
}
export function fixedRoll(id: number): Roll | null {
  const r = catalog.relics[id];
  if (!r) return null;
  const v = r.pools.map((p) =>
    p === -1 ? [EMPTY] : [...(poolSets.get(p) ?? [])],
  );
  if (v.some((p) => p.length !== 1)) return null;
  const roll = sortRoll(toRoll(v.map((p) => p[0])));
  return checkRoll(id, roll).length ? null : roll;
}
