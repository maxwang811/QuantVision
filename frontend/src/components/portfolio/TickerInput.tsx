"use client";

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
        className="w-full rounded-md border border-border bg-bg px-3 py-2 text-sm text-fg outline-none focus:border-accent"
        aria-label="Ticker search"
        aria-autocomplete="list"
        aria-expanded={open}
        aria-controls="ticker-listbox"
      />
      {open && (
        <div
          id="ticker-listbox"
          role="listbox"
          className="absolute left-0 right-0 mt-1 rounded-md border border-border bg-bg shadow-lg z-20"
        >
          {isLoading && <div className="px-3 py-2 text-sm text-muted">Loading…</div>}
          {!isLoading && data && data.length === 0 && (
            <div className="px-3 py-2 text-sm text-muted">No matches</div>
          )}
          {!isLoading &&
            data?.map((a) => (
              <button
                key={a.id}
                type="button"
                onClick={() => choose(a)}
                className="w-full text-left px-3 py-2 hover:bg-border/40 flex items-baseline gap-2"
              >
                <span className="font-mono font-semibold text-fg">{a.ticker}</span>
                <span className="text-sm text-muted truncate">{a.name}</span>
              </button>
            ))}
        </div>
      )}
    </div>
  );
}
