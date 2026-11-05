import { Gem, Layers3, Sword } from "lucide-react";
import { catalog, heroNames } from "../core/catalog";
import { relicUsage } from "../core/relic-usage";
import type { SessionView } from "../core/session";

export function RelicUsageSummary({
  usage,
}: {
  usage: ReturnType<typeof relicUsage>;
}) {
  return (
    <span className="usage-summary" aria-label="使用角色">
      {!usage || !usage.length
        ? usage
          ? "未使用"
          : "配装未识别"
        : usage.map((row) => (
            <span className="usage-summary-hero" key={row.hero}>
              <strong>{heroNames[row.hero]}</strong>
              {row.vessels.some((v) => v.equipped) && (
                <span>
                  <Sword size={12} aria-hidden="true" />
                  装备中
                </span>
              )}
              {row.vessels.some((v) => !v.equipped) && (
                <span>
                  <Gem size={12} aria-hidden="true" />
                  器皿 {row.vessels.filter((v) => !v.equipped).length}
                </span>
              )}
              {!!row.presets.length && (
                <span>
                  <Layers3 size={12} aria-hidden="true" />
                  预设 {row.presets.length}
                </span>
              )}
            </span>
          ))}
    </span>
  );
}

export function RelicUsage({
  loadouts,
  handle,
}: {
  loadouts: SessionView["loadouts"];
  handle?: number;
}) {
  if (handle === undefined) return null;
  const usage = relicUsage(loadouts, handle);
  return (
    <section className="relic-usage" aria-label="遗物使用情况">
      <h3>使用情况</h3>
      {!usage || !usage.length ? (
        <span className="usage-empty">{usage ? "未使用" : "配装未识别"}</span>
      ) : (
        <div className="usage-list">
          {usage.map((row) => (
            <div className="usage-hero" key={row.hero}>
              <strong>{heroNames[row.hero]}</strong>
              <ul>
                {row.vessels.map((v) => {
                  const Icon = v.equipped ? Sword : Gem;
                  return (
                    <li
                      key={v.id}
                      className={v.equipped ? "usage-equipped" : ""}
                    >
                      <Icon size={14} aria-hidden="true" />
                      <small>{v.equipped ? "装备中" : "器皿"}</small>
                      <span>{catalog.vessels[v.id]?.name.zh_CN ?? v.id}</span>
                    </li>
                  );
                })}
                {row.presets.map((p) => (
                  <li key={`preset-${p.index}`}>
                    <Layers3 size={14} aria-hidden="true" />
                    <small>预设</small>
                    <span>
                      {p.name || "未命名"} <code>#{p.index + 1}</code>
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
