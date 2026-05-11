"use client";

import { IconSearch } from "@/components/ui/Icons";
import { api, type Asset } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

interface Props {
  onSelect?: (asset: Asset) => void;
  placeholder?: string;
  autoFocus?: boolean;
}

export function TickerInput({ onSelect, placeholder = "Search ticker or name…", autoFocus }: Props) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["assets", query],
    queryFn: () => api.searchAssets(query, 8),
    enabled: open,
  });

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const choose = (a: Asset) => {
    onSelect?.(a);
    setQuery(a.ticker);
    setOpen(false);
  };

  return (
    <div ref={ref} className="relative w-full max-w-md">
      <div className="relative">
        <IconSearch
          width={16}
          height={16}
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted"
        />
        <input
          type="text"
          role="combobox"
          value={query}
          autoFocus={autoFocus}
          placeholder={placeholder}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          className="w-full rounded-md border border-border bg-surface py-2 pl-9 pr-3 text-sm text-fg outline-none transition-colors placeholder:text-muted/70 hover:border-border-strong focus:border-accent focus:ring-2 focus:ring-accent/30"
          aria-label="Ticker search"
          aria-autocomplete="list"
          aria-expanded={open}
          aria-controls="ticker-listbox"
        />
      </div>
      {open && (
        <div
          id="ticker-listbox"
          role="listbox"
          className="absolute left-0 right-0 z-20 mt-1.5 overflow-hidden rounded-lg border border-border bg-surface-elevated shadow-pop"
        >
          {isLoading && <div className="px-3 py-2 text-sm text-muted">Loading…</div>}
          {!isLoading && data && data.length === 0 && (
            <div className="px-3 py-3 text-sm text-muted">No matches.</div>
          )}
          {!isLoading &&
            data?.map((a) => (
              <button
                key={a.id}
                type="button"
                onClick={() => choose(a)}
                className="flex w-full items-baseline gap-2 px-3 py-2 text-left transition-colors hover:bg-surface-2"
              >
                <span className="font-mono text-sm font-semibold text-fg">{a.ticker}</span>
                <span className="truncate text-xs text-muted">{a.name}</span>
              </button>
            ))}
        </div>
      )}
    </div>
  );
}
