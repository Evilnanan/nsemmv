import { useEffect, useId, useRef, useState } from "react";
import { Check, ChevronDown } from "lucide-react";

export function CharacterSelect({
  characters,
  value,
  disabled,
  onChange,
}: {
  characters: { slot: number; name: string }[];
  value: number;
  disabled: boolean;
  onChange: (slot: number) => void | Promise<unknown>;
}) {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState<number | null>(null);
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const restoreFocus = useRef(false);
  const listId = useId();
  const selected = characters.findIndex((c) => c.slot === value);
  const label = (c: { slot: number; name: string }) =>
    `${String(c.slot + 1).padStart(2, "0")} · ${c.name}`;
  const optionId = (index: number) => `${listId}-${index}`;
  function close() {
    setOpen(false);
    setActive(null);
  }
  function choose(index: number) {
    close();
    trigger.current?.focus();
    if (characters[index] && characters[index].slot !== value)
      restoreFocus.current =
        onChange(characters[index].slot) instanceof Promise;
  }
  useEffect(() => {
    if (!open) return;
    const outside = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) close();
    };
    document.addEventListener("pointerdown", outside);
    return () => document.removeEventListener("pointerdown", outside);
  }, [open]);
  useEffect(() => {
    if (disabled) close();
    else if (restoreFocus.current) {
      restoreFocus.current = false;
      if (document.activeElement === document.body) trigger.current?.focus();
    }
  }, [disabled]);
  useEffect(() => {
    if (open && active !== null)
      document
        .getElementById(optionId(active))
        ?.scrollIntoView({ block: "nearest" });
  }, [open, active, listId]);
  return (
    <div
      className="character-select"
      ref={root}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) close();
      }}
      onKeyDown={(event) => {
        if (disabled) return;
        if (event.key === "Escape" && open) {
          event.preventDefault();
          event.stopPropagation();
          close();
          trigger.current?.focus();
        } else if (
          ["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)
        ) {
          event.preventDefault();
          if (event.altKey && event.key === "ArrowUp") {
            close();
            return;
          }
          const base = active ?? Math.max(0, selected);
          setActive(
            event.key === "Home"
              ? 0
              : event.key === "End"
                ? characters.length - 1
                : !open
                  ? Math.max(0, selected)
                  : Math.max(
                      0,
                      Math.min(
                        characters.length - 1,
                        base + (event.key === "ArrowDown" ? 1 : -1),
                      ),
                    ),
          );
          setOpen(true);
        } else if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          if (open) choose(active ?? selected);
          else {
            setActive(Math.max(0, selected));
            setOpen(true);
          }
        } else if (event.key === "Tab") close();
      }}
    >
      <button
        ref={trigger}
        type="button"
        role="combobox"
        aria-label="角色槽"
        aria-describedby={`${listId}-value`}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listId}
        aria-activedescendant={
          open && active !== null ? optionId(active) : undefined
        }
        className="character-select-trigger"
        disabled={disabled}
        onClick={() => {
          if (open) close();
          else {
            setActive(null);
            setOpen(true);
          }
        }}
      >
        <span id={`${listId}-value`}>
          {characters[selected] ? label(characters[selected]) : "—"}
        </span>
        <ChevronDown size={16} aria-hidden="true" />
      </button>
      {open && (
        <div
          className="character-select-options"
          role="listbox"
          aria-label="角色"
          id={listId}
          onPointerLeave={() => setActive(null)}
        >
          {characters.map((c, index) => (
            <button
              key={c.slot}
              id={optionId(index)}
              type="button"
              role="option"
              aria-selected={c.slot === value}
              tabIndex={-1}
              className={`character-select-option ${active === index ? "active" : ""}`}
              onPointerEnter={() => setActive(index)}
              onPointerMove={() => setActive(index)}
              onFocus={() => setActive(index)}
              onClick={() => choose(index)}
            >
              <span>{label(c)}</span>
              {c.slot === value && <Check size={16} aria-hidden="true" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
