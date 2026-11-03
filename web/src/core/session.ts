import { SaveContainer } from "./container";
import {
  Character,
  validateTransition,
  editRelic,
  addRelic,
  removeRelic,
  setFavorite,
  savePreset,
  equipPreset,
  deletePreset,
  type Preset,
} from "./character";
import { equal, invariant } from "./binary";
import { type Roll, checkRoll } from "./rules";
export type Edit =
  | { type: "edit"; handle: number; id: number; roll: Roll }
  | { type: "add"; id: number; roll: Roll }
  | { type: "remove"; handle: number }
  | { type: "favorite"; handle: number; value: boolean }
  | {
      type: "preset";
      hero: number;
      vessel: number;
      handles: number[];
      name: string;
      index?: number;
    }
  | { type: "equip"; index: number }
  | { type: "delete-preset"; index: number };
export interface SessionView {
  filename: string;
  dirty: boolean;
  canUndo: boolean;
  canRedo: boolean;
  slot: number;
  characters: { slot: number; name: string; count: number }[];
  name: string;
  relics: {
    handle: number;
    id: number;
    roll: Roll;
    favorite: boolean;
    acquisition: number;
    owners: string;
    issues: ReturnType<typeof checkRoll>;
  }[];
  loadouts: null | {
    presets: Preset[];
    vessels: { id: number; hero: number; handles: number[] }[];
    heroes: { id: number; currentVessel: number; currentPreset: number }[];
  };
  goods: number[];
}
type Change = { slot: number; before: Uint8Array; after: Uint8Array };
export class Session {
  readonly container: SaveContainer;
  readonly occupied: number[];
  private changes = new Map<number, Uint8Array>();
  private undoStack: Change[] = [];
  private redoStack: Change[] = [];
  private saved = new Map<number, Uint8Array>();
  private constructor(
    input: Uint8Array,
    readonly filename: string,
  ) {
    this.container = SaveContainer.open(input);
    this.occupied = this.container.occupied();
    invariant(this.occupied.length, "存档没有角色");
    for (const slot of this.occupied) new Character(this.bytes(slot));
  }
  static open(input: Uint8Array, filename: string) {
    invariant(input.length <= 64 * 1024 * 1024, "文件超过 64 MiB");
    return new Session(input, filename);
  }
  bytes(slot: number) {
    invariant(
      this.occupied === undefined || this.occupied.includes(slot),
      "角色槽为空",
    );
    return this.changes.get(slot) ?? this.container.entries[slot].plain;
  }
  dirty() {
    return this.occupied.some(
      (slot) =>
        !equal(
          this.bytes(slot),
          this.saved.get(slot) ?? this.container.entries[slot].plain,
        ),
    );
  }
  view(slot: number): SessionView {
    const c = new Character(this.bytes(slot));
    return {
      filename: this.filename,
      dirty: this.dirty(),
      canUndo: !!this.undoStack.length,
      canRedo: !!this.redoStack.length,
      slot,
      name: c.name,
      characters: this.occupied.map((slot) => {
        const ch = new Character(this.bytes(slot));
        return { slot, name: ch.name, count: ch.relics.length };
      }),
      relics: c.relics.map((r) => ({
        handle: r.handle,
        id: r.id,
        roll: r.roll,
        favorite: r.favorite,
        acquisition: r.acquisition,
        owners: c.owners(r.handle),
        issues: checkRoll(r.id, r.roll),
      })),
      goods: [...c.goods],
      loadouts: c.loadouts && {
        heroes: c.loadouts.heroes.map(
          ({ id, currentPreset, currentVessel }) => ({
            id,
            currentPreset,
            currentVessel,
          }),
        ),
        vessels: c.loadouts.vessels.map(({ id, hero, handles }) => ({
          id,
          hero,
          handles,
        })),
        presets: c.loadouts.presets,
      },
    };
  }
  apply(slot: number, op: Edit) {
    const before = this.bytes(slot);
    let after: Uint8Array = before;
    let handle: number | undefined;
    switch (op.type) {
      case "edit":
        after = editRelic(before, op.handle, op.id, op.roll);
        break;
      case "add":
        ({ bytes: after, handle } = addRelic(before, op.id, op.roll));
        break;
      case "remove":
        after = removeRelic(before, op.handle);
        break;
      case "favorite":
        after = setFavorite(before, op.handle, op.value);
        break;
      case "preset":
        after = savePreset(
          before,
          op.hero,
          op.vessel,
          op.handles,
          op.name,
          op.index,
        );
        break;
      case "delete-preset":
        after = deletePreset(before, op.index);
        break;
      case "equip":
        after = equipPreset(before, op.index);
        break;
      default:
        throw new Error("未知操作");
    }
    validateTransition(
      new Character(this.container.entries[slot].plain),
      new Character(after),
    );
    if (!equal(before, after)) {
      this.changes.set(slot, after);
      this.undoStack.push({ slot, before, after });
      if (this.undoStack.length > 20) this.undoStack.shift();
      this.redoStack = [];
    }
    return handle;
  }
  undo() {
    const c = this.undoStack.pop();
    if (c) {
      this.changes.set(c.slot, c.before);
      this.redoStack.push(c);
    }
  }
  redo() {
    const c = this.redoStack.pop();
    if (c) {
      this.changes.set(c.slot, c.after);
      this.undoStack.push(c);
    }
  }
  export() {
    for (const slot of this.occupied)
      validateTransition(
        new Character(this.container.entries[slot].plain),
        new Character(this.bytes(slot)),
      );
    const result = this.container.write(this.changes);
    const reopened = SaveContainer.open(result);
    for (const slot of this.occupied) {
      const written = reopened.entries[slot].plain,
        expected = this.bytes(slot);
      invariant(
        equal(
          written.subarray(0, written.length - 28),
          expected.subarray(0, expected.length - 28),
        ),
        "导出回读不一致",
      );
    }
    this.saved = new Map(this.occupied.map((s) => [s, this.bytes(s).slice()]));
    return result;
  }
  original() {
    return this.container.original.slice();
  }
}
