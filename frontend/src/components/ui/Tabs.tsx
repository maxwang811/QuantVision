"use client";

import { cn } from "./utils";

interface Tab<T extends string> {
  value: T;
  label: string;
}

interface TabsProps<T extends string> {
  value: T;
  onChange: (value: T) => void;
  tabs: Tab<T>[];
  size?: "sm" | "md";
  className?: string;
}

export function Tabs<T extends string>({ value, onChange, tabs, size = "md", className }: TabsProps<T>) {
  return (
    <div
      role="tablist"
      className={cn(
        "inline-flex items-center gap-0.5 rounded-lg border border-border bg-surface p-1",
        className,
      )}
    >
      {tabs.map((tab) => {
        const active = value === tab.value;
        return (
          <button
            key={tab.value}
            role="tab"
            aria-selected={active}
            type="button"
            onClick={() => onChange(tab.value)}
            className={cn(
              "rounded-md font-medium transition-colors focus-ring",
              size === "sm" ? "px-2.5 py-1 text-xs" : "px-3 py-1.5 text-sm",
              active
                ? "bg-accent text-accent-fg shadow-soft"
                : "text-muted hover:bg-surface-2 hover:text-fg",
            )}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
