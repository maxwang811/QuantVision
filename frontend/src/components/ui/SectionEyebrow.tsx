import type { ReactNode } from "react";
import { cn } from "./utils";

interface SectionEyebrowProps {
  children: ReactNode;
  className?: string;
  as?: "h2" | "h3" | "h4" | "div" | "span";
}

export function SectionEyebrow({ children, className, as: Tag = "h3" }: SectionEyebrowProps) {
  return (
    <Tag
      className={cn(
        "text-xs font-medium text-muted",
        className,
      )}
    >
      {children}
    </Tag>
  );
}
