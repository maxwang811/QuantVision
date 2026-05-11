import type { ReactNode } from "react";
import { cn } from "./utils";

interface SectionEyebrowProps {
  children: ReactNode;
  className?: string;
  as?: "h2" | "h3" | "h4" | "div";
}

export function SectionEyebrow({ children, className, as: Tag = "h3" }: SectionEyebrowProps) {
  return (
    <Tag
      className={cn(
        "text-[11px] font-semibold uppercase tracking-eyebrow text-muted",
        className,
      )}
    >
      {children}
    </Tag>
  );
}
