import { useMemo, useRef, useState } from "react";
import {
  ArrowLeft,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  Search,
  X,
} from "lucide-react";
import { catalog, effectName } from "../core/catalog";
import { filterEffects, UNCLASSIFIED } from "../core/effect-filters";
import { EffectDetailContent } from "./EffectDetailContent";

// Include every named catalog entry, regardless of its current relic pool.
const entries = Object.values(catalog.effects)
  .filter((effect) => effect.id !== 0)
  .sort((a, b) => a.sort - b.sort || a.id - b.id)
  .map((effect) => effect.id);
const pageSize = 40;

export function EffectDictionary() {
  const [query, setQuery] = useState("");
  const [group, setGroup] = useState<number | null>(null);
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  const list = useRef<HTMLDivElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const results = useMemo(
    () => filterEffects(entries, query, group),
    [query, group],
  );
  const pages = Math.max(1, Math.ceil(results.length / pageSize));
  function reset() {
    setPage(0);
    setSelected(null);
    list.current?.scrollTo(0, 0);
  }
  function select(id: number) {
    setSelected(id);
    requestAnimationFrame(() =>
      heading.current?.focus({ preventScroll: true }),
    );
  }
  function back() {
    const id = selected;
    setSelected(null);
    requestAnimationFrame(() =>
      list.current
        ?.querySelector<HTMLButtonElement>(`[data-effect-id="${id}"]`)
        ?.focus({ preventScroll: true }),
    );
  }
  return (
    <main
      className={`dictionary ${selected !== null ? "dictionary-reading" : ""}`}
    >
      <header className="dictionary-heading">
        <BookOpen size={22} strokeWidth={1.5} />
        <h1>词典</h1>
        <span>{entries.length}</span>
      </header>
      <div className="dictionary-layout">
        <section className="dictionary-browser" aria-label="词条列表">
          <div className="dictionary-filters">
            <div className="search">
              <Search size={17} />
              <input
                aria-label="搜索词典词条"
                placeholder="词条 / ID"
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  reset();
                }}
              />
              {query && (
                <button
                  type="button"
                  className="tool"
                  aria-label="清空词典搜索"
                  onClick={() => {
                    setQuery("");
                    reset();
                  }}
                >
                  <X size={16} />
                </button>
              )}
            </div>
            <select
              aria-label="词典分类"
              value={group ?? ""}
              onChange={(e) => {
                setGroup(e.target.value === "" ? null : Number(e.target.value));
                reset();
              }}
            >
              <option value="">全部分类</option>
              {Object.values(catalog.effectCategories)
                .sort(
                  (a, b) =>
                    Number(b.id === 30) - Number(a.id === 30) || a.id - b.id,
                )
                .map((category) => (
                  <optgroup key={category.id} label={category.name.zh_CN}>
                    {Object.values(catalog.effectGroups)
                      .filter((g) => g.category === category.id)
                      .map((g) => (
                        <option key={g.id} value={g.id}>
                          {g.name.zh_CN}
                        </option>
                      ))}
                  </optgroup>
                ))}
              <option value={UNCLASSIFIED}>未分类</option>
            </select>
          </div>
          <div className="dictionary-list" ref={list}>
            {results.slice(page * pageSize, (page + 1) * pageSize).map((id) => (
              <button
                type="button"
                className="dictionary-row"
                key={id}
                data-effect-id={id}
                aria-pressed={selected === id}
                onClick={() => select(id)}
              >
                <span>{effectName(id)}</span>
                <code>{id}</code>
                <ChevronRight size={15} />
              </button>
            ))}
            {!results.length && (
              <div className="dictionary-empty" role="status">
                无匹配词条
              </div>
            )}
          </div>
          <footer className="dictionary-pagination">
            <span aria-live="polite">{results.length} 条</span>
            <button
              type="button"
              className="tool"
              aria-label="词典上一页"
              disabled={page === 0}
              onClick={() => {
                setPage(page - 1);
                list.current?.scrollTo(0, 0);
              }}
            >
              <ChevronLeft size={18} />
            </button>
            <code>
              {page + 1} / {pages}
            </code>
            <button
              type="button"
              className="tool"
              aria-label="词典下一页"
              disabled={page + 1 >= pages}
              onClick={() => {
                setPage(page + 1);
                list.current?.scrollTo(0, 0);
              }}
            >
              <ChevronRight size={18} />
            </button>
          </footer>
        </section>
        <section
          className="dictionary-detail"
          aria-label="词典详情"
          key={selected}
        >
          {selected !== null ? (
            <>
              <button type="button" className="dictionary-back" onClick={back}>
                <ArrowLeft size={18} />
                返回词条列表
              </button>
              <header>
                <code>{selected}</code>
                <h2 ref={heading} tabIndex={-1}>
                  {effectName(selected)}
                </h2>
              </header>
              <EffectDetailContent id={selected} />
            </>
          ) : (
            <div className="dictionary-empty">
              <BookOpen size={32} strokeWidth={1} />
              <span>选择词条</span>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
