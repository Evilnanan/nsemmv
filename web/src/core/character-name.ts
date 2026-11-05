import { Binary, invariant } from "./binary";
import { Character } from "./character";
import { displayGameText, storeGameText } from "./game-text";

// The PC selection summary has ten 0x290-byte records following the slot flags.
// Match the name and FACE header before writing; never replace name occurrences
// in expedition history, other characters, or other container sections.
export function summaryNameOffset(
  summary: Uint8Array,
  directory: number,
  slot: number,
  name: string,
) {
  const offset = directory + 10 + slot * 0x290;
  const b = new Binary(summary);
  b.range(offset, 0x290);
  invariant(
    [39, 0, 0, 70, 65, 67, 69].every((v, i) => summary[offset + 51 + i] === v),
    "角色选档记录无法识别",
  );
  invariant(
    displayGameText(b.text(offset, 16)) === name,
    "角色名称与选档记录不一致",
  );
  return offset;
}

export function renameCharacter(
  character: Uint8Array,
  summary: Uint8Array,
  directory: number,
  slot: number,
  input: string,
) {
  const name = input.trim();
  invariant(name.length > 0, "角色名称不能为空");
  invariant(!/[\u0000-\u001f\u007f]/.test(name), "角色名称不能包含控制字符");
  invariant(name.length <= 16, "角色名称最多 16 个 UTF-16 字符");
  const c = new Character(character);
  if (name === c.name) return { character, summary };
  const offset = summaryNameOffset(summary, directory, slot, c.name);
  const next = character.slice(),
    nextSummary = summary.slice();
  const stored = storeGameText(name);
  new Binary(next).putText(c.nameOffset, 16, stored);
  new Binary(nextSummary).putText(offset, 16, stored);
  invariant(new Character(next).name === name, "角色名称无法正确编码");
  return { character: next, summary: nextSummary };
}
