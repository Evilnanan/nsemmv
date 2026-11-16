import { useEffect, useMemo, useRef, useState } from "react";
import {
  Check,
  ChevronLeft,
  ChevronRight,
  Gem,
  Search,
  Star,
  Store,
  X,
} from "lucide-react";
import { catalog, colorNames } from "../core/catalog";
import { fitsPresetSlot, matchesRelicSearch } from "../core/preset-editor";
import {
  matchesUsage,
  type UsageFilter,
  type relicUsage,
} from "../core/relic-usage";
import type { SessionView } from "../core/session";
import { PresetEffects } from "./PresetEffects";
import { RelicUsageSummary } from "./RelicUsage";

const PAGE_SIZE = 18;
const shopFilterLabels = {
  all: "全部遗物",
  shop: "仅商店遗物",
  "non-shop": "排除商店遗物",
};
export function PresetRelicPicker({
  view,
  hero,
  colors,
  handles,
  slot,
  usages,
  onPick,
  onClose,
}: {
  view: SessionView;
  hero: number;
  colors: number[];
  handles: number[];
  slot: number;
  usages: Map<number, ReturnType<typeof relicUsage>>;
  onPick: (handle: number) => void;
  onClose: () => void;
}) {
  const [search, setSearch] = useState("");
  const [usageFilter, setUsageFilter] = useState<UsageFilter>("all");
  const [shopFilter, setShopFilter] = useState<"all" | "shop" | "non-shop">(
    "all",
  );
  const [favorites, setFavorites] = useState(false);
  const nextShopFilter =
    shopFilter === "all" ? "shop" : shopFilter === "shop" ? "non-shop" : "all";
  const [page, setPage] = useState(0);
  const input = useRef<HTMLInputElement>(null);
  const back = useRef<HTMLButtonElement>(null);
  const list = useRef<HTMLDivElement>(null);
  const matches = useMemo(
    () =>
      view.relics.filter(
        (r) =>
          fitsPresetSlot(r, colors, slot) &&
          (!handles.includes(r.handle) || handles[slot] === r.handle) &&
          (!favorites || r.favorite) &&
          (shopFilter === "all" ||
            !!catalog.relics[r.id]?.shop === (shopFilter === "shop")) &&
          matchesUsage(usages.get(r.handle) ?? null, hero, usageFilter) &&
          matchesRelicSearch(r, search),
      ),
    [
      view.relics,
      colors,
      slot,
      handles,
      favorites,
      shopFilter,
      usages,
      hero,
      usageFilter,
      search,
    ],
  );
  const pages = Math.max(1, Math.ceil(matches.length / PAGE_SIZE));
  const currentPage = Math.min(page, pages - 1);
  useEffect(() => {
    setPage(0);
  }, [slot, search, usageFilter, shopFilter, favorites]);
  useEffect(() => {
    list.current?.scrollTo(0, 0);
  }, [currentPage, slot, search, usageFilter, shopFilter, favorites]);
  useEffect(() => {
    (window.matchMedia("(max-width: 1000px)").matches
      ? back.current
      : input.current
    )?.focus({ preventScroll: true });
  }, []);
  return (
    <aside className="slot-picker" aria-label="选择预设遗物">
      <div className="slot-picker-heading">
        <button
          ref={back}
          type="button"
          className="tool"
          aria-label="关闭遗物选择"
          title="返回预设"
          onClick={onClose}
        >
          <ChevronLeft size={20} />
        </button>
        <Gem size={19} className={`color-${colors[slot]}`} />
        <h3>
          {slot < 3 ? "普通" : "深层"} {(slot % 3) + 1}
        </h3>
        <span>
          {colors[slot] === 4 ? "任意颜色" : colorNames[colors[slot]]}
        </span>
      </div>
      <div className="slot-picker-filters">
        <div className="search">
          <Search size={15} />
          <input
            ref={input}
            aria-label="搜索预设遗物"
            placeholder="名称 / 词条 / ID"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {search && (
            <button
              type="button"
              className="tool"
              aria-label="清除遗物搜索"
              onClick={() => {
                setSearch("");
                input.current?.focus();
              }}
            >
              <X size={16} />
            </button>
          )}
        </div>
        <div className="slot-filter-row">
          <select
            className="usage-filter"
            aria-label="筛选遗物使用情况"
            value={usageFilter}
            onChange={(e) => setUsageFilter(e.target.value as UsageFilter)}
          >
            <option value="all">全部使用情况</option>
            <option value="unshared">未被其他角色使用</option>
            <option value="unused">未使用</option>
            <option value="current">当前角色使用</option>
            <option value="other">其他角色使用</option>
          </select>
          <button
            type="button"
            className={`tool shop-filter ${shopFilter !== "all" ? "active" : ""} ${shopFilter === "non-shop" ? "excluded" : ""}`}
            aria-label={`商店遗物筛选：${shopFilterLabels[shopFilter]}`}
            title={`${shopFilterLabels[shopFilter]} · 点击切换为${shopFilterLabels[nextShopFilter]}`}
            aria-pressed={shopFilter !== "all"}
            onClick={() => setShopFilter(nextShopFilter)}
          >
            <Store size={18} />
            {shopFilter !== "all" && (
              <span className="shop-filter-badge" aria-hidden="true">
                {shopFilter === "shop" ? <Check size={11} /> : <X size={11} />}
              </span>
            )}
          </button>
          <button
            type="button"
            className={`tool ${favorites ? "active" : ""}`}
            aria-label="仅显示收藏遗物"
            title="仅显示收藏遗物"
            aria-pressed={favorites}
            onClick={() => setFavorites(!favorites)}
          >
            <Star size={18} fill={favorites ? "currentColor" : "none"} />
          </button>
        </div>
      </div>
      <div className="slot-options" ref={list}>
        {!matches.length && (
          <div className="slot-no-results">
            <Search size={24} />
            <span>无匹配</span>
            <button
              type="button"
              onClick={() => {
                setSearch("");
                setFavorites(false);
                setUsageFilter("all");
                setShopFilter("all");
                input.current?.focus({ preventScroll: true });
              }}
            >
              重置筛选
            </button>
          </div>
        )}
        {matches
          .slice(currentPage * PAGE_SIZE, (currentPage + 1) * PAGE_SIZE)
          .map((r) => {
            const meta = catalog.relics[r.id],
              selected = handles[slot] === r.handle;
            return (
              <article
                className={`relic-candidate ${selected ? "selected" : ""}`}
                key={r.handle}
              >
                <button
                  type="button"
                  className="picker-row relic-option"
                  aria-label={`选择遗物 ${r.id} · ${r.handle}`}
                  aria-pressed={selected}
                  onClick={() => onPick(r.handle)}
                >
                  <span className="relic-option-content">
                    <span className="relic-option-title">
                      <Gem size={16} className={`color-${meta.color}`} />
                      <strong>{meta.name.zh_CN}</strong>
                      {selected ? (
                        <Check size={16} />
                      ) : (
                        <ChevronRight size={16} />
                      )}
                    </span>
                    <span className="relic-option-meta">
                      <code>{r.id}</code>
                      {meta.shop && <span>商店遗物</span>}
                      {r.favorite && <Star size={12} fill="currentColor" />}
                    </span>
                    <RelicUsageSummary usage={usages.get(r.handle) ?? null} />
                  </span>
                </button>
                <PresetEffects relic={r} />
              </article>
            );
          })}
      </div>
      <div className="slot-pagination">
        <button
          type="button"
          className="slot-clear"
          aria-label="清空当前遗物槽"
          title="清空当前遗物槽"
          disabled={!handles[slot]}
          onClick={() => onPick(0)}
        >
          <X size={15} />
          <span>移除</span>
        </button>
        <span role="status">{matches.length} 件</span>
        <div className="spacer" />
        <button
          type="button"
          className="tool"
          aria-label="上一页遗物"
          disabled={currentPage === 0}
          onClick={() => setPage(currentPage - 1)}
        >
          <ChevronLeft size={18} />
        </button>
        <span>
          {currentPage + 1} / {pages}
        </span>
        <button
          type="button"
          className="tool"
          aria-label="下一页遗物"
          disabled={currentPage + 1 >= pages}
          onClick={() => setPage(currentPage + 1)}
        >
          <ChevronRight size={18} />
        </button>
      </div>
    </aside>
  );
}
