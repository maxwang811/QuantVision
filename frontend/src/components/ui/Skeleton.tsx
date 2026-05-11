import { cn } from "./utils";

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      aria-hidden
      className={cn("shimmer rounded-lg border border-border/60", className)}
    />
  );
}
