import { CircleAlert } from "lucide-react";
import { EMPTY } from "../core/binary";
import { effectName } from "../core/catalog";
import { checkRoll, candidateConflicts } from "../core/rules";
import type { SessionView } from "../core/session";
import { EffectInspect } from "./EffectInspect";

export function PresetEffects({
  relic,
}: {
  relic: SessionView["relics"][number];
}) {
  const issues = checkRoll(relic.id, relic.roll);
  return (
    <div className="preset-effects" aria-label="遗物词条">
      {relic.roll.map((pair, index) => (
        <div className="preset-effect-pair" key={index}>
          {([false, true] as const).map((curse) => {
            const id = curse ? pair.curse : pair.effect;
            if (id === EMPTY || id === 0) return null;
            const invalid =
              issues.some((issue) => issue.slot === index + (curse ? 3 : 0)) ||
              candidateConflicts(relic.roll, index, curse, id).length > 0;
            return (
              <EffectInspect key={String(curse)} id={id}>
                <div
                  className={`preset-effect ${curse ? "curse" : ""}`}
                  aria-invalid={invalid || undefined}
                >
                  {curse && <small>Curse</small>}
                  <span>{effectName(id)}</span>
                  {invalid && (
                    <CircleAlert
                      className="preset-effect-warning"
                      size={16}
                      aria-label="词条不可用"
                    />
                  )}
                </div>
              </EffectInspect>
            );
          })}
        </div>
      ))}
    </div>
  );
}
