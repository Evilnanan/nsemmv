import { Binary } from "../src/core/binary";
import { Character } from "../src/core/character";
import { Session } from "../src/core/session";
import { character, fixture } from "./fixtures";

export const sharedHandle = 0xc0800054;
export const longPresetName = "<搓招>备用·星光碎片与随身包包";
export function usageFixture() {
  const session = Session.open(fixture(), "usage");
  const relic = session.view(0).relics[0];
  const duplicate = session.apply(0, {
    type: "add",
    id: relic.id,
    roll: relic.roll,
  })!;
  for (const [hero, name] of [
    [7, "搓招流"],
    [7, longPresetName],
    [1, "共享配置"],
    [2, "备用器皿"],
  ] as const)
    session.apply(0, {
      type: "preset",
      hero,
      name,
      vessel: 19000,
      handles: [sharedHandle, 0, 0, 0, 0, 0],
    });
  const exclusive = session.apply(0, {
    type: "add",
    id: relic.id,
    roll: relic.roll,
  })!;
  session.apply(0, {
    type: "preset",
    hero: 7,
    name: "独用",
    vessel: 19000,
    handles: [exclusive, 0, 0, 0, 0, 0],
  });
  session.apply(0, { type: "equip", index: 0 });
  session.apply(0, { type: "equip", index: 3 });
  const bytes = session.bytes(0).slice();
  const hero = new Character(bytes).loadouts!.heroes.find((h) => h.id === 2)!;
  // Retain the other vessel's loadout after switching the active vessel.
  new Binary(bytes).put32(hero.offset + 4, 2000);
  return { bytes: fixture({ 0: bytes, 1: character() }), duplicate, exclusive };
}
