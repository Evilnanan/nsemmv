import { effectName } from "../core/catalog";
import { effectDetail } from "../core/effect-details";

export function EffectDetailContent({ id }: { id: number }) {
  const detail = effectDetail(id);
  return (
    <div className="effect-detail-content">
      {detail?.info && detail.info !== effectName(id) && (
        <p className="effect-mechanism">{detail.info}</p>
      )}
      {!detail?.blocks.length && (
        <p className="effect-detail-muted">具体数值尚未解明</p>
      )}
      {detail?.blocks.map((b) => (
        <section className="effect-detail-block" key={b.source}>
          <div className="effect-detail-phase">{b.phase}</div>
          <dl>
            {b.values.map(([label, value]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
          {!!b.restrictions.length && (
            <p className="effect-detail-muted">{b.restrictions.join(" · ")}</p>
          )}
          {(b.duration !== null || b.interval !== null) && (
            <p className="effect-detail-muted">
              {[
                b.duration !== null && `此效果持续 ${b.duration} 秒`,
                b.interval !== null && `触发周期 ${b.interval} 秒`,
              ]
                .filter(Boolean)
                .join(" · ")}
            </p>
          )}
        </section>
      ))}
      <dl className="effect-detail-rules">
        <div>
          <dt>叠加</dt>
          <dd>{detail?.stacking ?? "待确认"}</dd>
        </div>
      </dl>
      {detail?.stackingDetail && (
        <p className="effect-detail-muted">{detail.stackingDetail}</p>
      )}
      {detail?.notes.map((note) => (
        <p key={note} className="effect-detail-muted">
          {note}
        </p>
      ))}
      <small className="effect-detail-source">MMV 2.1.9 · 参数值</small>
    </div>
  );
}
