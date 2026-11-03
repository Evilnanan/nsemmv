import {
  useEffect,
  useId,
  useLayoutEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { Info, X } from "lucide-react";
import { effectName } from "../core/catalog";
import { effectDetail } from "../core/effect-details";

const dismissEvent = "dismiss-effect-details";

/** The popover top layer keeps this above nested native dialogs and clipped lists. */
export function EffectInspect({
  id,
  children,
  className = "",
}: {
  id: number;
  children: ReactNode;
  className?: string;
}) {
  const uid = useId();
  const host = useRef<HTMLDivElement>(null);
  const card = useRef<HTMLDivElement>(null);
  const info = useRef<HTMLButtonElement>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const pinned = useRef(false);
  const [open, setOpen] = useState(false);
  const hasEffect = id !== 0 && id !== 0xffffffff;
  const detail = effectDetail(id);
  const clearTimer = () => {
    clearTimeout(timer.current);
  };
  const close = () => {
    clearTimer();
    pinned.current = false;
    setOpen(false);
  };
  const show = () => {
    clearTimer();
    if (!hasEffect) return;
    document.dispatchEvent(new Event(dismissEvent));
    setOpen(true);
  };
  const scheduleClose = () => {
    clearTimer();
    if (!pinned.current) timer.current = setTimeout(close, 180);
  };
  useEffect(() => {
    document.addEventListener(dismissEvent, close);
    return () => {
      clearTimer();
      document.removeEventListener(dismissEvent, close);
    };
  }, []);
  useEffect(() => {
    close();
  }, [id]);
  useLayoutEffect(() => {
    if (!open || !card.current || !host.current) return;
    const popup = card.current;
    popup.showPopover();
    const place = () => {
      if (!host.current) return;
      const viewport = window.visualViewport;
      const width = viewport?.width ?? document.documentElement.clientWidth;
      const height = viewport?.height ?? window.innerHeight;
      const x = viewport?.offsetLeft ?? 0;
      const y = viewport?.offsetTop ?? 0;
      popup.style.maxHeight = `${Math.min(560, height - 16)}px`;
      popup.style.maxWidth = `${width - 16}px`;
      const anchor = host.current.getBoundingClientRect();
      const rect = popup.getBoundingClientRect();
      const left = Math.max(
        x + 8,
        Math.min(anchor.right - rect.width, x + width - rect.width - 8),
      );
      const below = y + height - anchor.bottom - 8;
      const top =
        below >= rect.height || below >= anchor.top - y
          ? Math.max(
              y + 8,
              Math.min(anchor.bottom + 6, y + height - rect.height - 8),
            )
          : Math.max(y + 8, anchor.top - rect.height - 6);
      popup.style.left = `${left}px`;
      popup.style.top = `${top}px`;
    };
    place();
    const outside = (e: PointerEvent) => {
      if (!host.current?.contains(e.target as Node)) close();
    };
    const escape = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      e.preventDefault();
      e.stopImmediatePropagation();
      if (popup.contains(document.activeElement)) info.current?.focus();
      close();
    };
    const scroll = (e: Event) => {
      if (!popup.contains(e.target as Node)) close();
    };
    document.addEventListener("pointerdown", outside, true);
    document.addEventListener("keydown", escape, true);
    document.addEventListener("scroll", scroll, true);
    window.addEventListener("resize", place);
    window.visualViewport?.addEventListener("resize", place);
    return () => {
      popup.hidePopover();
      document.removeEventListener("pointerdown", outside, true);
      document.removeEventListener("keydown", escape, true);
      document.removeEventListener("scroll", scroll, true);
      window.removeEventListener("resize", place);
      window.visualViewport?.removeEventListener("resize", place);
    };
  }, [open]);
  return (
    <div
      ref={host}
      className={`effect-inspect ${className}`}
      onPointerEnter={(e) => {
        if (e.pointerType === "mouse" && !open) {
          clearTimer();
          timer.current = setTimeout(show, 320);
        } else clearTimer();
      }}
      onPointerLeave={scheduleClose}
      onBlur={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget)) scheduleClose();
      }}
    >
      <div className="effect-inspect-target" onClick={close}>
        {children}
      </div>
      {hasEffect && (
        <button
          type="button"
          ref={info}
          className="effect-info"
          aria-label={`词条详情：${effectName(id)}`}
          aria-expanded={open}
          aria-controls={open ? uid : undefined}
          onFocus={(e) => {
            if (e.currentTarget.matches(":focus-visible")) show();
          }}
          onClick={() => {
            if (open && pinned.current) close();
            else {
              show();
              pinned.current = true;
            }
          }}
        >
          <Info size={16} aria-hidden="true" />
        </button>
      )}
      {open && (
        <div
          ref={card}
          id={uid}
          popover="manual"
          role="dialog"
          aria-label="词条详情"
          className="effect-popover"
          onPointerEnter={clearTimer}
          onPointerLeave={scheduleClose}
        >
          <div className="effect-popover-heading">
            <strong>{effectName(id)}</strong>
            <button
              type="button"
              className="tool"
              aria-label="关闭词条详情"
              onClick={() => {
                info.current?.focus();
                close();
              }}
            >
              <X size={17} />
            </button>
          </div>
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
              {!!b.scope.length && (
                <p className="effect-detail-muted">
                  法术适用：{b.scope.join(" / ")}
                </p>
              )}
              {!!b.restrictions.length && (
                <p className="effect-detail-muted">
                  {b.restrictions.join(" · ")}
                </p>
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
          {!!detail?.blocks.some((b) => b.linked) && (
            <p className="effect-detail-muted">部分触发条件尚未确认</p>
          )}
          <dl className="effect-detail-rules">
            <div>
              <dt>叠加</dt>
              <dd>{detail?.stacking ?? "尚未确认"}</dd>
            </div>
          </dl>
          {detail?.notes.map((note) => (
            <p key={note} className="effect-detail-muted">
              {note}
            </p>
          ))}
          <small className="effect-detail-source">MMV 2.1.9 · 参数值</small>
        </div>
      )}
    </div>
  );
}
