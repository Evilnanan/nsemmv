import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  FolderOpen,
  Download,
  Undo2,
  Redo2,
  Plus,
  Trash2,
  Search,
  SlidersHorizontal,
  Gem,
  Layers3,
  Check,
  X,
  WandSparkles,
  Star,
  ShieldCheck,
  CircleAlert,
  ChevronRight,
  ChevronLeft,
  ArrowDownToLine,
  LoaderCircle,
  Copy,
  Sword,
  Pencil,
  Eye,
  Github,
} from "lucide-react";
import {
  catalog,
  relicDefinitions,
  effectName,
  heroNames,
  colorNames,
} from "./core/catalog";
import { EMPTY } from "./core/binary";
import {
  effectGroup,
  filterEffects,
  UNCLASSIFIED,
} from "./core/effect-filters";
import {
  autoFix,
  checkRoll,
  effectChoices,
  fixedRoll,
  toRoll,
  type Roll,
} from "./core/rules";
import { type SessionView, type Edit } from "./core/session";
import { request, download } from "./client";
import "./style.css";
type Icon = typeof Gem;
function Tool({
  icon: Icon,
  label,
  onClick,
  disabled = false,
  active = false,
  danger = false,
}: {
  icon: Icon;
  label: string;
  onClick: () => void;
  disabled?: boolean;
  active?: boolean;
  danger?: boolean;
}) {
  return (
    <button
      type="button"
      className={`tool ${active ? "active" : ""} ${danger ? "danger" : ""}`}
      title={label}
      aria-label={label}
      onClick={onClick}
      disabled={disabled}
    >
      <Icon size={19} strokeWidth={1.7} />
    </button>
  );
}
function Modal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    ref.current?.showModal();
  }, []);
  return (
    <dialog
      ref={ref}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <header>
        <h2>{title}</h2>
        <Tool icon={X} label="关闭" onClick={onClose} />
      </header>
      {children}
    </dialog>
  );
}
const blank = () => toRoll([EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY]);
type Draft = { handle?: number; id: number; roll: Roll };
function EffectPicker({
  itemId,
  curse,
  onPick,
  onClose,
}: {
  itemId: number;
  curse: boolean;
  onPick: (id: number) => void;
  onClose: () => void;
}) {
  const [q, setQ] = useState("");
  const [group, setGroup] = useState<number | null>(null);
  const [page, setPage] = useState(0);
  const choices = useMemo(() => effectChoices(itemId, curse), [itemId, curse]);
  const availableGroups = useMemo(
    () => new Set(choices.map(effectGroup)),
    [choices],
  );
  const found = filterEffects(choices, q, group);
  const numeric = /^\d+$/.test(q.trim()) ? Number(q.trim()) : null;
  const manual =
    group === null &&
    numeric !== null &&
    numeric > 0 &&
    numeric < EMPTY &&
    !choices.includes(numeric);
  const pages = Math.max(1, Math.ceil(found.length / 100));
  useEffect(() => setPage(0), [q, group, itemId, curse]);
  return (
    <Modal title={curse ? "Curse" : "Effect"} onClose={onClose}>
      <div className="effect-picker-controls">
        <div className="search">
          <Search size={17} />
          <input
            autoFocus
            aria-label="搜索词条"
            placeholder="词条 / ID"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <div className="effect-category">
          <SlidersHorizontal size={16} />
          <select
            aria-label="词条分类"
            value={group ?? ""}
            onChange={(e) =>
              setGroup(e.target.value === "" ? null : Number(e.target.value))
            }
          >
            <option value="">全部词条</option>
            {Object.values(catalog.effectCategories)
              .sort(
                (a, b) =>
                  Number(b.id === 30) - Number(a.id === 30) || a.id - b.id,
              )
              .map((category) => {
                const groups = Object.values(catalog.effectGroups).filter(
                  (g) =>
                    g.category === category.id && availableGroups.has(g.id),
                );
                return (
                  groups.length > 0 && (
                    <optgroup key={category.id} label={category.name.zh_CN}>
                      {groups.map((g) => (
                        <option value={g.id} key={g.id}>
                          {g.name.zh_CN}
                        </option>
                      ))}
                    </optgroup>
                  )
                );
              })}
            {availableGroups.has(UNCLASSIFIED) && (
              <option value={UNCLASSIFIED}>未分类</option>
            )}
          </select>
        </div>
      </div>
      <div className="picker-list">
        <button
          onClick={() => onPick(EMPTY)}
          className="picker-row"
          aria-label="清空词条"
        >
          <span>—</span>
          <span>空槽</span>
        </button>
        {manual && (
          <button className="picker-row" onClick={() => onPick(numeric!)}>
            <code>{numeric}</code>
            <span>{effectName(numeric!)}</span>
          </button>
        )}
        {found.slice(page * 100, (page + 1) * 100).map((id) => (
          <button className="picker-row" key={id} onClick={() => onPick(id)}>
            <code>{id}</code>
            <span>{effectName(id)}</span>
          </button>
        ))}
        {!found.length && !manual && <div className="empty-small">无匹配</div>}
      </div>
      <footer className="modal-footer effect-pagination">
        <span aria-label="匹配词条数">{found.length + (manual ? 1 : 0)}</span>
        {pages > 1 && (
          <>
            <div className="spacer" />
            <Tool
              icon={ChevronLeft}
              label="上一页词条"
              disabled={page === 0}
              onClick={() => setPage(page - 1)}
            />
            <span>
              {page + 1} / {pages}
            </span>
            <Tool
              icon={ChevronRight}
              label="下一页词条"
              disabled={page + 1 >= pages}
              onClick={() => setPage(page + 1)}
            />
          </>
        )}
      </footer>
    </Modal>
  );
}

function ItemPicker({
  onPick,
  onClose,
}: {
  onPick: (id: number) => void;
  onClose: () => void;
}) {
  const [q, setQ] = useState(""),
    [type, setType] = useState("normal");
  const items = relicDefinitions.filter(
    (r) =>
      (type === "shop"
        ? r.shop
        : type === "deep"
          ? r.deep && !r.shop
          : !r.deep && !r.shop) && `${r.id} ${r.name.zh_CN}`.includes(q),
  );
  return (
    <Modal title="新增遗物" onClose={onClose}>
      <div className="picker-controls">
        <div className="segments">
          {[
            ["normal", "普通"],
            ["deep", "深层"],
            ["shop", "商店遗物"],
          ].map(([id, label]) => (
            <button
              className={type === id ? "on" : ""}
              key={id}
              onClick={() => setType(id)}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="search">
          <Search size={17} />
          <input
            aria-label="搜索遗物类型"
            autoFocus
            placeholder="名称 / ID"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
      </div>
      <div className="picker-list">
        {items.slice(0, 150).map((r) => (
          <button
            className="picker-row"
            key={r.id}
            onClick={() => onPick(r.id)}
          >
            <span className={`gem color-${r.color}`}>
              <Gem size={20} />
            </span>
            <span>{r.name.zh_CN}</span>
            <code>{r.id}</code>
          </button>
        ))}
      </div>
      <footer className="modal-footer">{items.length}</footer>
    </Modal>
  );
}
function App() {
  const [view, setView] = useState<SessionView | null>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [tab, setTab] = useState<"relics" | "presets">("relics"),
    [childDirty, setChildDirty] = useState(false),
    [documentId, setDocumentId] = useState(0);
  const [selected, setSelected] = useState<number>(),
    [draft, setDraft] = useState<Draft | null>(null),
    [q, setQ] = useState(""),
    [type, setType] = useState("all"),
    [color, setColor] = useState(-1),
    [fav, setFav] = useState(false),
    [invalid, setInvalid] = useState(false),
    [page, setPage] = useState(0);
  const [picker, setPicker] = useState<{ slot: number; curse: boolean } | null>(
      null,
    ),
    [adding, setAdding] = useState(false),
    [filters, setFilters] = useState(false);
  const file = useRef<HTMLInputElement>(null);
  const current = view?.relics.find((r) => r.handle === selected);
  const draftDirty =
    !!draft &&
    (draft.handle === undefined ||
      draft.id !== current?.id ||
      JSON.stringify(draft.roll) !== JSON.stringify(current?.roll));
  const dirty = !!view?.dirty || draftDirty || childDirty;
  useEffect(() => {
    const f = (e: BeforeUnloadEvent) => {
      if (dirty) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", f);
    return () => window.removeEventListener("beforeunload", f);
  }, [dirty]);
  useEffect(() => setPage(0), [q, type, color, fav, invalid, view?.slot]);
  function discard() {
    return !(draftDirty || childDirty) || window.confirm("放弃未应用的修改？");
  }
  async function run<T>(work: () => Promise<T>): Promise<T | undefined> {
    setBusy(true);
    setError("");
    try {
      return await work();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }
  function select(handle?: number, next = view) {
    setSelected(handle);
    const r = next?.relics.find((r) => r.handle === handle);
    setDraft(
      r
        ? { handle: r.handle, id: r.id, roll: r.roll.map((p) => ({ ...p })) }
        : null,
    );
  }
  async function open(f: File) {
    if (busy) return;
    if (dirty && !window.confirm("放弃未导出的修改并打开新存档？")) return;
    await run(async () => {
      const next = await request<SessionView>("open", 0, {
        bytes: await f.arrayBuffer(),
        filename: f.name,
      });
      setView(next);
      setDocumentId((id) => id + 1);
      select(next.relics[0]?.handle, next);
      setPage(0);
      setQ("");
    });
  }
  async function apply(op: Edit) {
    if (!view) return;
    return run(async () => {
      const next = await request<SessionView & { selectedHandle?: number }>(
        "apply",
        view.slot,
        op,
      );
      setView(next);
      select(next.selectedHandle ?? selected, next);
      return next;
    });
  }
  async function exportSave() {
    if (!view || draftDirty || childDirty) return;
    await run(async () => {
      const result = await request<{
        bytes: Uint8Array;
        filename: string;
        view: SessionView;
      }>("export", view.slot);
      download(result.bytes, result.filename);
      setView(result.view);
    });
  }
  async function history(action: "undo" | "redo") {
    if (!view || !discard()) return;
    await run(async () => {
      const next = await request<SessionView>(action, view.slot);
      setView(next);
      select(selected, next);
    });
  }
  const filtered = useMemo(
    () =>
      view?.relics.filter((r) => {
        const m = catalog.relics[r.id];
        return (
          (type === "all" ||
            (type === "shop"
              ? m?.shop
              : !m?.shop && (type === "deep" ? m?.deep : !m?.deep))) &&
          (color === -1 || m?.color === color) &&
          (!fav || r.favorite) &&
          (!invalid || r.issues.length > 0) &&
          (!q ||
            `${r.id} ${m?.name.zh_CN} ${r.roll.map((p) => effectName(p.effect) + " " + effectName(p.curse)).join(" ")}`
              .toLowerCase()
              .includes(q.trim().toLowerCase()))
        );
      }) ?? [],
    [view, q, type, color, fav, invalid],
  );
  const issues = draft ? checkRoll(draft.id, draft.roll) : [];
  const meta = draft && catalog.relics[draft.id];
  function chooseEffect(id: number) {
    if (!draft || !picker) return;
    const roll = draft.roll.map((p) => ({ ...p }));
    roll[picker.slot][picker.curse ? "curse" : "effect"] = id;
    const fixed = autoFix(draft.id, roll);
    setDraft({ ...draft, id: fixed.id, roll: fixed.roll });
    setPicker(null);
  }
  return (
    <div
      className="app"
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => {
        e.preventDefault();
        if (!busy && e.dataTransfer.files[0])
          void open(e.dataTransfer.files[0]);
      }}
    >
      <input
        ref={file}
        type="file"
        accept=".dbb,.co2,.sl2,.CL_SAVE,.dat"
        hidden
        aria-label="打开存档文件"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) void open(f);
          e.target.value = "";
        }}
      />
      <aside className="rail">
        <div className="monogram">
          N<span>•</span>
        </div>
        <nav>
          <Tool
            icon={Gem}
            label="遗物"
            active={tab === "relics"}
            onClick={() => {
              if (discard()) {
                select(selected);
                setTab("relics");
              }
            }}
          />
          <Tool
            icon={Layers3}
            label="预设"
            active={tab === "presets"}
            onClick={() => {
              if (discard()) {
                select(selected);
                setTab("presets");
              }
            }}
          />
        </nav>
        <a
          className="source-link"
          href="https://github.com/Evilnanan/nsemmv"
          target="_blank"
          rel="noreferrer"
          title="GitHub"
          aria-label="GitHub"
        >
          <Github size={19} strokeWidth={1.5} />
        </a>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div className="wordmark">
            NIGHTREIGN <span>MMV</span>
          </div>
          <span className="version">DAYBREAK 2.1.9</span>
          <div className="top-actions">
            {view && (
              <>
                <span
                  className={`save-dot ${dirty ? "dirty" : ""}`}
                  title={dirty ? "未导出" : "已保存"}
                />
                <span className="filename">{view.filename}</span>
                <Tool
                  icon={Undo2}
                  label="撤销"
                  disabled={busy || !view.canUndo}
                  onClick={() => void history("undo")}
                />
                <Tool
                  icon={Redo2}
                  label="重做"
                  disabled={busy || !view.canRedo}
                  onClick={() => void history("redo")}
                />
                <span className="divider" />
              </>
            )}
            <Tool
              icon={FolderOpen}
              label="打开存档"
              disabled={busy}
              onClick={() => file.current?.click()}
            />
            {view && (
              <>
                <Tool
                  icon={ArrowDownToLine}
                  label="下载原始备份"
                  disabled={busy}
                  onClick={() =>
                    void run(async () => {
                      const r = await request<{
                        bytes: Uint8Array;
                        filename: string;
                      }>("original");
                      download(r.bytes, `backup-${r.filename}`);
                    })
                  }
                />
                <button
                  className="export"
                  title="导出存档"
                  aria-label="导出存档"
                  disabled={busy || draftDirty || childDirty}
                  onClick={() => void exportSave()}
                >
                  <Download size={18} />
                  <span>导出</span>
                </button>
              </>
            )}
          </div>
        </header>
        {error && (
          <div className="error-banner" role="alert">
            <CircleAlert size={17} />
            <span>{error}</span>
            <Tool icon={X} label="关闭错误" onClick={() => setError("")} />
          </div>
        )}
        {!view ? (
          <main className="landing">
            <div className="orbit">
              <div className="ring r1" />
              <div className="ring r2" />
              <Gem size={74} strokeWidth={0.65} />
              <i />
              <i />
              <i />
            </div>
            <span className="eyebrow">RELIC WORKSHOP</span>
            <h1>遗物工坊</h1>
            <button
              className="open-button"
              onClick={() => file.current?.click()}
              disabled={busy}
            >
              <FolderOpen size={19} />
              打开存档
            </button>
            <div className="format-list">
              .dbb <span>·</span> .co2 <span>·</span> .sl2
            </div>
            <span className="privacy">
              <ShieldCheck size={13} />
              本地处理
            </span>
          </main>
        ) : (
          <>
            <div className="characterbar">
              <select
                aria-label="角色槽"
                disabled={busy}
                value={view.slot}
                onChange={(e) => {
                  if (discard())
                    void run(async () => {
                      const next = await request<SessionView>(
                        "view",
                        Number(e.target.value),
                      );
                      setView(next);
                      select(next.relics[0]?.handle, next);
                    });
                }}
              >
                {view.characters.map((c) => (
                  <option key={c.slot} value={c.slot}>
                    {String(c.slot + 1).padStart(2, "0")} · {c.name}
                  </option>
                ))}
              </select>
              <span className="character-meta">
                <Gem size={14} />
                {view.relics.length}
              </span>
              <span className="character-meta">
                <Layers3 size={14} />
                {view.loadouts?.presets.length ?? "—"}
              </span>
            </div>
            {tab === "relics" ? (
              <main className="editor">
                <section className="inventory">
                  <div className="section-heading">
                    <h1>
                      遗物 <span>{filtered.length}</span>
                    </h1>
                    <Tool
                      icon={Plus}
                      label="新增遗物"
                      disabled={busy}
                      onClick={() => {
                        if (discard()) setAdding(true);
                      }}
                    />
                  </div>
                  <div className="list-search">
                    <div className="search">
                      <Search size={16} />
                      <input
                        aria-label="搜索库存"
                        placeholder="搜索 / ID"
                        value={q}
                        onChange={(e) => setQ(e.target.value)}
                      />
                      {q && (
                        <button aria-label="清空搜索" onClick={() => setQ("")}>
                          <X size={13} />
                        </button>
                      )}
                    </div>
                    <Tool
                      icon={SlidersHorizontal}
                      label="筛选"
                      active={filters}
                      onClick={() => setFilters(!filters)}
                    />
                  </div>
                  {filters && (
                    <div className="filters">
                      <div className="segments">
                        {[
                          ["all", "全部"],
                          ["normal", "普通"],
                          ["deep", "深层"],
                          ["shop", "商店遗物"],
                        ].map(([id, label]) => (
                          <button
                            key={id}
                            className={type === id ? "on" : ""}
                            onClick={() => setType(id)}
                          >
                            {label}
                          </button>
                        ))}
                      </div>
                      <div className="color-filters">
                        {colorNames.slice(0, 4).map((name, i) => (
                          <button
                            key={i}
                            aria-label={`${name}色`}
                            title={name}
                            className={`color-dot color-${i} ${color === i ? "on" : ""}`}
                            onClick={() => setColor(color === i ? -1 : i)}
                          />
                        ))}
                        <Tool
                          icon={Star}
                          label="收藏"
                          active={fav}
                          onClick={() => setFav(!fav)}
                        />
                        <Tool
                          icon={CircleAlert}
                          label="待检查"
                          active={invalid}
                          onClick={() => setInvalid(!invalid)}
                        />
                      </div>
                    </div>
                  )}
                  <div className="relic-list">
                    {filtered.slice(page * 60, (page + 1) * 60).map((r) => {
                      const m = catalog.relics[r.id];
                      return (
                        <button
                          key={r.handle}
                          className={`relic-card ${r.handle === selected ? "selected" : ""}`}
                          onClick={() => {
                            if (discard()) select(r.handle);
                          }}
                        >
                          <div
                            className={`relic-symbol color-${m?.color ?? 4}`}
                          >
                            <Gem size={25} strokeWidth={1.15} />
                            {m?.deep && <span />}
                          </div>
                          <div className="relic-card-content">
                            <div className="card-title">
                              <span>{m?.name.zh_CN ?? `未知遗物 ${r.id}`}</span>
                              {r.favorite && <Star size={11} />}{" "}
                              {!!r.issues.length && (
                                <CircleAlert size={12} className="amber" />
                              )}
                            </div>
                            <span className="card-effect">
                              {effectName(
                                r.roll.find((p) => p.effect !== EMPTY)
                                  ?.effect ?? EMPTY,
                              )}
                            </span>
                            <div className="card-bottom">
                              <code>{r.id}</code>
                              {r.owners && <span>{r.owners}</span>}
                            </div>
                          </div>
                          <ChevronRight size={13} className="card-arrow" />
                        </button>
                      );
                    })}
                    {!filtered.length && (
                      <div className="empty-small">无匹配</div>
                    )}
                  </div>
                  <footer className="pagination">
                    <Tool
                      icon={ChevronLeft}
                      label="上一页"
                      disabled={page === 0}
                      onClick={() => setPage(page - 1)}
                    />
                    <span>
                      {page + 1} /{" "}
                      {Math.max(1, Math.ceil(filtered.length / 60))}
                    </span>
                    <Tool
                      icon={ChevronRight}
                      label="下一页"
                      disabled={(page + 1) * 60 >= filtered.length}
                      onClick={() => setPage(page + 1)}
                    />
                  </footer>
                </section>
                <section className="detail">
                  {draft ? (
                    <>
                      <header className="detail-heading">
                        <div className={`big-gem color-${meta?.color ?? 4}`}>
                          <Gem size={45} strokeWidth={1} />
                        </div>
                        <div>
                          <span className="eyebrow">
                            {meta?.deep ? "DEEP RELIC" : "RELIC"}
                          </span>
                          <h2>{meta?.name.zh_CN ?? "未知遗物"}</h2>
                          <span className="owners">
                            {current?.owners || "—"}
                          </span>
                        </div>
                        <div className="detail-tools">
                          {draft.handle !== undefined && (
                            <>
                              <Tool
                                icon={Star}
                                label={
                                  current?.favorite ? "取消收藏" : "收藏遗物"
                                }
                                active={current?.favorite}
                                disabled={busy || draftDirty}
                                onClick={() =>
                                  void apply({
                                    type: "favorite",
                                    handle: draft.handle!,
                                    value: !current?.favorite,
                                  })
                                }
                              />
                              <Tool
                                icon={Copy}
                                label="复制遗物"
                                disabled={
                                  busy ||
                                  draftDirty ||
                                  !!issues.length ||
                                  !!meta?.shop
                                }
                                onClick={() => {
                                  setSelected(undefined);
                                  setDraft({ ...draft, handle: undefined });
                                }}
                              />
                              <Tool
                                icon={Trash2}
                                label="删除遗物"
                                danger
                                disabled={
                                  busy ||
                                  !view.loadouts ||
                                  !!current?.owners ||
                                  !!meta?.shop
                                }
                                onClick={() => {
                                  if (window.confirm("删除这件遗物？"))
                                    void apply({
                                      type: "remove",
                                      handle: draft.handle!,
                                    });
                                }}
                              />
                            </>
                          )}
                        </div>
                      </header>
                      <RelicFields
                        draft={draft}
                        setDraft={setDraft}
                        current={current}
                        busy={busy}
                        apply={apply}
                        setPicker={setPicker}
                      />
                    </>
                  ) : (
                    <div className="detail-empty">
                      <Gem size={35} strokeWidth={1} />
                    </div>
                  )}
                </section>
              </main>
            ) : (
              <Presets
                key={documentId + ":" + view.slot}
                view={view}
                busy={busy}
                apply={apply}
                onDirty={setChildDirty}
                error={error}
              />
            )}
          </>
        )}
        <footer className="statusbar">
          <span>
            <i />
            MMV
          </span>
          <span>
            {busy ? (
              <>
                <LoaderCircle size={12} className="spin" />
                处理中
              </>
            ) : (
              <>
                <ShieldCheck size={12} />
                本地
              </>
            )}
          </span>
          <code>NSE / 0.3</code>
        </footer>
      </div>
      {picker && draft && (
        <EffectPicker
          itemId={draft.id}
          curse={picker.curse}
          onPick={chooseEffect}
          onClose={() => setPicker(null)}
        />
      )}
      {adding && (
        <ItemPicker
          onClose={() => setAdding(false)}
          onPick={(id) => {
            setAdding(false);
            setSelected(undefined);
            setDraft({ id, roll: fixedRoll(id) ?? blank() });
          }}
        />
      )}
    </div>
  );
}
function RelicFields({
  draft,
  setDraft,
  current,
  busy,
  apply,
  setPicker,
  slotRule,
}: {
  draft: Draft;
  setDraft: (draft: Draft) => void;
  current?: SessionView["relics"][number];
  busy: boolean;
  apply: (op: Edit) => Promise<unknown>;
  setPicker: (picker: { slot: number; curse: boolean }) => void;
  slotRule?: { color: number; deep: boolean };
}) {
  const meta = catalog.relics[draft.id];
  const readOnly = !!catalog.relics[current?.id ?? 0]?.shop;
  const draftDirty =
    draft.handle === undefined ||
    draft.id !== current?.id ||
    JSON.stringify(draft.roll) !== JSON.stringify(current?.roll);
  const issues = checkRoll(draft.id, draft.roll);
  if (
    slotRule &&
    meta &&
    (meta.deep !== slotRule.deep ||
      (slotRule.color !== 4 && meta.color !== slotRule.color))
  )
    issues.push({ code: "preset-slot", message: "遗物类型或颜色不匹配" });
  return (
    <>
      <div className="item-line">
        <label>
          Item ID
          <input
            aria-label="Item ID"
            disabled={!!meta?.shop || readOnly}
            type="number"
            min="1"
            value={draft.id}
            onChange={(e) => setDraft({ ...draft, id: Number(e.target.value) })}
          />
        </label>
        <span className={`type-chip color-${meta?.color ?? 4}`}>
          {meta?.shop ? "商店遗物" : meta?.deep ? "深层" : "普通"} ·{" "}
          {colorNames[meta?.color ?? 4]}
        </span>
        <div className="spacer" />
        <Tool
          icon={WandSparkles}
          label="Auto Fix"
          disabled={busy || readOnly || !!meta?.shop}
          onClick={() => {
            const fixed = autoFix(draft.id, draft.roll);
            setDraft({
              ...draft,
              id: fixed.id,
              roll: fixed.roll,
            });
          }}
        />
      </div>
      <div className="effect-grid">
        <div className="effect-table-head">
          <span />
          <span>Effect</span>
          <span>Curse</span>
        </div>
        {draft.roll.map((pair, i) => (
          <div className="effect-pair" key={i}>
            <span className="pair-number">0{i + 1}</span>
            {([false, true] as const).map((curse) => {
              const id = curse ? pair.curse : pair.effect;
              return (
                <button
                  key={String(curse)}
                  className={`effect-cell ${curse ? "curse" : ""} ${issues.some((x) => x.slot === i + (curse ? 3 : 0)) ? "invalid" : ""}`}
                  onClick={() => setPicker({ slot: i, curse })}
                  disabled={busy || readOnly || !!meta?.shop}
                >
                  <span>{effectName(id)}</span>
                  <code>
                    {id === EMPTY || id === 0 ? <Plus size={14} /> : id}
                  </code>
                </button>
              );
            })}
          </div>
        ))}
      </div>
      <footer className="detail-footer">
        <div
          className={`validation ${issues.length ? "bad" : "good"}`}
          aria-live="polite"
        >
          {issues.length ? (
            <CircleAlert size={16} />
          ) : (
            <ShieldCheck size={16} />
          )}
          <span>
            {issues.length
              ? [...new Set(issues.map((i) => i.message))].join(" · ")
              : "合法"}
          </span>
        </div>
        <button
          className="apply"
          title="应用修改"
          aria-label="应用修改"
          disabled={
            busy ||
            !draftDirty ||
            !!issues.length ||
            readOnly ||
            !!(draft.handle !== undefined && meta?.shop)
          }
          onClick={() =>
            void apply(
              draft.handle === undefined
                ? {
                    type: "add",
                    id: draft.id,
                    roll: draft.roll,
                  }
                : {
                    type: "edit",
                    handle: draft.handle,
                    id: draft.id,
                    roll: draft.roll,
                  },
            )
          }
        >
          <Check size={19} />
        </button>
      </footer>
    </>
  );
}

function Presets({
  error,
  view,
  busy,
  apply,
  onDirty,
}: {
  view: SessionView;
  busy: boolean;
  apply: (op: Edit) => Promise<unknown>;
  onDirty: (value: boolean) => void;
  error: string;
}) {
  const [edit, setEdit] = useState<{
      name: string;
      hero: number;
      vessel: number;
      handles: number[];
      index?: number;
    } | null>(null),
    [slot, setSlot] = useState<number | null>(null),
    [search, setSearch] = useState("");
  const [relicEdit, setRelicEdit] = useState<{
    draft: Draft;
    slot: number;
  } | null>(null);
  const [relicPicker, setRelicPicker] = useState<{
    slot: number;
    curse: boolean;
  } | null>(null);
  const relicCurrent = view.relics.find(
    (r) => r.handle === relicEdit?.draft.handle,
  );
  const relicDirty =
    !!relicEdit &&
    (relicEdit.draft.id !== relicCurrent?.id ||
      JSON.stringify(relicEdit.draft.roll) !==
        JSON.stringify(relicCurrent?.roll));
  function closeRelic() {
    if (busy) return;
    if (!relicDirty || window.confirm("放弃未应用的修改？")) {
      setRelicEdit(null);
      setRelicPicker(null);
    }
  }
  const stored = view.loadouts?.presets.find((p) => p.index === edit?.index);
  const changed =
    !!edit &&
    (!stored ||
      edit.name !== stored.name ||
      edit.hero !== stored.hero ||
      edit.vessel !== stored.vessel ||
      edit.handles.join() !== stored.handles.join());
  useEffect(() => {
    onDirty(changed || relicDirty);
    return () => onDirty(false);
  }, [changed, relicDirty, onDirty]);
  const l = view.loadouts;
  const available = (hero: number) =>
    l?.vessels.filter(
      (v) =>
        v.hero === hero && view.goods.includes(catalog.vessels[v.id].goods),
    ) ?? [];
  if (!l) return <main className="empty-small">未识别的配装结构</main>;
  return (
    <main className="presets">
      <div className="section-heading">
        <h1>
          预设 <span>{l.presets.length}</span>
        </h1>
        <Tool
          icon={Plus}
          label="新增预设"
          disabled={busy}
          onClick={() =>
            setEdit({
              name: "",
              hero: 7,
              vessel: available(7)[0]?.id ?? 7000,
              handles: [0, 0, 0, 0, 0, 0],
            })
          }
        />
      </div>
      <div className="preset-grid">
        {l.presets.map((p) => (
          <button
            key={p.index}
            className="preset-card"
            onClick={() => setEdit({ ...p })}
          >
            <div className="preset-top">
              <span>{heroNames[p.hero]}</span>
              {l.heroes.find((h) => h.id === p.hero)?.currentPreset ===
              p.index ? (
                <Check size={15} />
              ) : (
                <ChevronRight size={15} />
              )}
            </div>
            <h2>{p.name}</h2>
            <div className="preset-gems">
              {p.handles.map((h, i) => {
                const r = view.relics.find((r) => r.handle === h);
                return (
                  <Gem
                    key={i}
                    size={23}
                    strokeWidth={1.2}
                    className={`color-${r ? (catalog.relics[r.id]?.color ?? 4) : 4} ${!h ? "vacant" : ""}`}
                  />
                );
              })}
            </div>
            <span className="preset-vessel">
              {catalog.vessels[p.vessel]?.name.zh_CN}
            </span>
          </button>
        ))}
      </div>
      {edit && !relicEdit && (
        <Modal
          title="预设"
          onClose={() => {
            if (!changed || window.confirm("放弃未保存的预设？")) {
              setEdit(null);
              setSlot(null);
            }
          }}
        >
          <div className="preset-form">
            <label>
              名称
              <input
                aria-label="预设名称"
                maxLength={18}
                value={edit.name}
                onChange={(e) => setEdit({ ...edit, name: e.target.value })}
              />
            </label>
            <div className="form-row">
              <label>
                角色
                <select
                  aria-label="夜渡者"
                  value={edit.hero}
                  onChange={(e) => {
                    const hero = Number(e.target.value);
                    setEdit({
                      ...edit,
                      hero,
                      vessel: available(hero)[0]?.id ?? hero * 1000,
                      handles: [0, 0, 0, 0, 0, 0],
                    });
                  }}
                >
                  {heroNames.slice(1).map((name, i) => (
                    <option value={i + 1} key={i}>
                      {name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                器皿
                <select
                  aria-label="器皿"
                  value={edit.vessel}
                  onChange={(e) =>
                    setEdit({
                      ...edit,
                      vessel: Number(e.target.value),
                      handles: [0, 0, 0, 0, 0, 0],
                    })
                  }
                >
                  {available(edit.hero).map((v) => (
                    <option key={v.id} value={v.id}>
                      {catalog.vessels[v.id].name.zh_CN}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className="preset-slots">
              {edit.handles.map((h, i) => {
                const r = view.relics.find((r) => r.handle === h),
                  m = r && catalog.relics[r.id];
                return (
                  <div className="preset-slot-cell" key={i}>
                    <button
                      aria-label={`预设遗物 ${i + 1}`}
                      className={`preset-slot ${slot === i ? "on" : ""}`}
                      onClick={() => {
                        setSlot(i);
                        setSearch("");
                      }}
                    >
                      <Gem
                        size={22}
                        className={`color-${catalog.vessels[edit.vessel].colors[i]}`}
                      />
                      <span>{m?.name.zh_CN ?? "—"}</span>
                      <small>{i < 3 ? "普通" : "深层"}</small>
                    </button>
                    {r && (
                      <Tool
                        icon={m?.shop ? Eye : Pencil}
                        label={`${m?.shop ? "查看" : "编辑"}预设遗物 ${i + 1}`}
                        disabled={busy}
                        onClick={() =>
                          setRelicEdit({
                            slot: i,
                            draft: {
                              handle: r.handle,
                              id: r.id,
                              roll: r.roll.map((p) => ({ ...p })),
                            },
                          })
                        }
                      />
                    )}
                  </div>
                );
              })}
            </div>
            {slot !== null && (
              <div className="slot-picker">
                <div className="search">
                  <Search size={15} />
                  <input
                    aria-label="搜索预设遗物"
                    placeholder="词条 / ID"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                  />
                  <Tool
                    icon={X}
                    label="关闭遗物选择"
                    onClick={() => setSlot(null)}
                  />
                </div>
                <div className="slot-options">
                  <button
                    className="picker-row"
                    onClick={() => {
                      const handles = [...edit.handles];
                      handles[slot] = 0;
                      setEdit({ ...edit, handles });
                      setSlot(null);
                    }}
                  >
                    —
                  </button>
                  {view.relics
                    .filter((r) => {
                      const m = catalog.relics[r.id],
                        color = catalog.vessels[edit.vessel].colors[slot];
                      return (
                        m &&
                        m.deep === slot >= 3 &&
                        (color === 4 || color === m.color) &&
                        (!edit.handles.includes(r.handle) ||
                          edit.handles[slot] === r.handle) &&
                        `${r.id} ${r.roll.map((p) => effectName(p.effect)).join(" ")}`.includes(
                          search,
                        )
                      );
                    })
                    .slice(0, 80)
                    .map((r) => (
                      <button
                        className="picker-row"
                        key={r.handle}
                        onClick={() => {
                          const handles = [...edit.handles];
                          handles[slot] = r.handle;
                          setEdit({ ...edit, handles });
                          setSlot(null);
                        }}
                      >
                        <code>{r.id}</code>
                        <span>
                          {r.roll
                            .filter((p) => p.effect !== EMPTY)
                            .map((p) => effectName(p.effect))
                            .join(" / ")}
                        </span>
                      </button>
                    ))}
                </div>
              </div>
            )}
            {error && (
              <div className="validation bad" role="alert">
                <CircleAlert size={16} />
                {error}
              </div>
            )}
            <div className="modal-actions">
              {edit.index !== undefined && (
                <Tool
                  icon={Trash2}
                  label="删除预设"
                  danger
                  disabled={busy}
                  onClick={async () => {
                    if (
                      window.confirm("删除这个预设？") &&
                      (await apply({
                        type: "delete-preset",
                        index: edit.index!,
                      }))
                    )
                      setEdit(null);
                  }}
                />
              )}
              {edit.index !== undefined && (
                <Tool
                  icon={Sword}
                  label="装备预设"
                  disabled={busy || changed}
                  onClick={async () => {
                    if (await apply({ type: "equip", index: edit.index! }))
                      setEdit(null);
                  }}
                />
              )}
              <div className="spacer" />
              <button
                className="apply"
                aria-label="保存预设"
                title="保存预设"
                disabled={
                  busy || !edit.name.trim() || !edit.handles.some(Boolean)
                }
                onClick={async () => {
                  const result = await apply({ type: "preset", ...edit });
                  if (result) setEdit(null);
                }}
              >
                <Check size={19} />
              </button>
            </div>
          </div>
        </Modal>
      )}
      {edit && relicEdit && (
        <Modal title="遗物" onClose={closeRelic}>
          <div className="preset-relic-editor">
            <h3>
              {catalog.relics[relicEdit.draft.id]?.name.zh_CN ?? "未知遗物"}
            </h3>
            <RelicFields
              draft={relicEdit.draft}
              setDraft={(draft) => setRelicEdit({ ...relicEdit, draft })}
              current={relicCurrent}
              busy={busy}
              setPicker={setRelicPicker}
              slotRule={{
                color: catalog.vessels[edit.vessel].colors[relicEdit.slot],
                deep: relicEdit.slot >= 3,
              }}
              apply={async (op) => {
                const result = await apply(op);
                if (result) {
                  setRelicEdit(null);
                  setRelicPicker(null);
                }
                return result;
              }}
            />
            {error && (
              <div className="validation bad" role="alert">
                <CircleAlert size={16} />
                {error}
              </div>
            )}
          </div>
        </Modal>
      )}
      {relicEdit && relicPicker && (
        <EffectPicker
          itemId={relicEdit.draft.id}
          curse={relicPicker.curse}
          onClose={() => setRelicPicker(null)}
          onPick={(id) => {
            const roll = relicEdit.draft.roll.map((p) => ({ ...p }));
            roll[relicPicker.slot][relicPicker.curse ? "curse" : "effect"] = id;
            const fixed = autoFix(relicEdit.draft.id, roll);
            setRelicEdit({
              ...relicEdit,
              draft: { ...relicEdit.draft, id: fixed.id, roll: fixed.roll },
            });
            setRelicPicker(null);
          }}
        />
      )}
    </main>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
