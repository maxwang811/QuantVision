"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { IconLogo, IconMenu, IconX } from "@/components/ui/Icons";
import { cn } from "@/components/ui/utils";

const links: { href: string; label: string }[] = [
  { href: "/", label: "Home" },
  { href: "/portfolio", label: "Portfolio" },
  { href: "/backtest", label: "Backtest" },
  { href: "/forecast", label: "Forecast" },
  { href: "/experiments", label: "History" },
];

function isActive(pathname: string | null, href: string): boolean {
  if (!pathname) return false;
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function TopNav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  return (
    <nav className="sticky top-0 z-30 border-b border-border/70 bg-bg/85 backdrop-blur supports-[backdrop-filter]:bg-bg/70">
      <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6 lg:px-8">
        <Link
          href="/"
          className="group inline-flex items-center gap-2 text-fg focus-ring rounded-md"
          aria-label="QuantVision home"
        >
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-accent/10 text-accent transition-colors group-hover:bg-accent/15">
            <IconLogo width={18} height={18} />
          </span>
          <span className="text-[15px] font-semibold tracking-tight">QuantVision</span>
        </Link>

        <ul className="hidden items-center gap-1 sm:flex">
          {links.map((link) => {
            const active = isActive(pathname, link.href);
            return (
              <li key={link.href}>
                <Link
                  href={link.href}
                  className={cn(
                    "relative inline-flex items-center rounded-md px-3 py-1.5 text-sm font-medium transition-colors focus-ring",
                    active
                      ? "text-fg"
                      : "text-muted hover:bg-surface-2 hover:text-fg",
                  )}
                  aria-current={active ? "page" : undefined}
                >
                  {link.label}
                  {active && (
                    <span
                      aria-hidden
                      className="pointer-events-none absolute inset-x-2 -bottom-[13px] h-[2px] rounded-full bg-accent"
                    />
                  )}
                </Link>
              </li>
            );
          })}
        </ul>

        <button
          type="button"
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
          onClick={() => setOpen((value) => !value)}
          className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-border bg-surface text-fg hover:bg-surface-2 sm:hidden focus-ring"
        >
          {open ? <IconX width={18} height={18} /> : <IconMenu width={18} height={18} />}
        </button>
      </div>

      {open && (
        <div className="border-t border-border/60 bg-surface sm:hidden">
          <ul className="mx-auto flex w-full max-w-7xl flex-col gap-1 px-4 py-3">
            {links.map((link) => {
              const active = isActive(pathname, link.href);
              return (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className={cn(
                      "block rounded-md px-3 py-2 text-sm font-medium transition-colors",
                      active
                        ? "bg-accent/10 text-accent"
                        : "text-muted hover:bg-surface-2 hover:text-fg",
                    )}
                    aria-current={active ? "page" : undefined}
                  >
                    {link.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </nav>
  );
}
