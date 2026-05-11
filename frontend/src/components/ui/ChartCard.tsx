import type { ReactNode } from "react";
import { cn } from "./utils";

interface ChartCardProps {
  title: ReactNode;
  meta?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}

export function ChartCard({ title, meta, children, className, bodyClassName }: ChartCardProps) {
  return (
    <section
      className={cn("rounded-xl border border-border bg-surface p-5 shadow-soft", className)}
    >
      <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-sm font-semibold text-fg">{title}</h3>
        {meta && <div className="text-xs text-muted">{meta}</div>}
      </div>
      <div className={cn("w-full", bodyClassName)}>{children}</div>
    </section>
  );
}
