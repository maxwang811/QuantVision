"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { IconLogo, IconMenu, IconX } from "@/components/ui/Icons";
import { cn } from "@/components/ui/utils";

const links: { href: string; label: string; description?: string }[] = [
  { href: "/", label: "Home" },
  { href: "/backtest", label: "Backtest", description: "Test strategies" },
  { href: "/forecast", label: "Forecast", description: "Simulate outcomes" },
  { href: "/experiments", label: "History", description: "Compare runs" },
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
    <nav className="sticky top-0 z-30 border-b border-border bg-bg/90 backdrop-blur-xl supports-[backdrop-filter]:bg-bg/80">
      <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-6 px-4 py-3 sm:px-6 lg:px-8">
        {/* Logo */}
        <Link
          href="/"
          className="group inline-flex items-center gap-2.5 text-fg focus-ring rounded-lg"
          aria-label="QuantVision home"
        >
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-accent text-accent-fg shadow-soft transition-all duration-200 group-hover:shadow-glow">
            <IconLogo width={18} height={18} />
          </span>
          <span className="text-base font-semibold tracking-tight">QuantVision</span>
        </Link>

        {/* Desktop Navigation */}
        <ul className="hidden items-center gap-1 sm:flex">
          {links.map((link) => {
            const active = isActive(pathname, link.href);
            return (
              <li key={link.href}>
                <Link
                  href={link.href}
                  className={cn(
                    "relative inline-flex items-center rounded-lg px-3.5 py-2 text-sm font-medium transition-all duration-200 focus-ring",
                    active
                      ? "text-fg bg-surface-2"
                      : "text-muted hover:text-fg hover:bg-surface-2/50",
                  )}
                  aria-current={active ? "page" : undefined}
                >
                  {link.label}
                  {active && (
                    <span
                      aria-hidden
                      className="pointer-events-none absolute inset-x-3 -bottom-[13px] h-0.5 rounded-full bg-accent"
                    />
                  )}
                </Link>
              </li>
            );
          })}
        </ul>

        {/* Mobile Menu Button */}
        <button
          type="button"
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
          onClick={() => setOpen((value) => !value)}
          className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-border bg-surface text-fg transition-colors hover:bg-surface-2 sm:hidden focus-ring"
        >
          {open ? <IconX width={20} height={20} /> : <IconMenu width={20} height={20} />}
        </button>
      </div>

      {/* Mobile Menu */}
      {open && (
        <div className="border-t border-border bg-surface animate-fade-in sm:hidden">
          <ul className="mx-auto flex w-full max-w-7xl flex-col gap-1 px-4 py-4">
            {links.map((link) => {
              const active = isActive(pathname, link.href);
              return (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className={cn(
                      "flex flex-col rounded-xl px-4 py-3 transition-all duration-200",
                      active
                        ? "bg-accent-soft text-accent"
                        : "text-fg hover:bg-surface-2",
                    )}
                    aria-current={active ? "page" : undefined}
                  >
                    <span className="font-medium">{link.label}</span>
                    {link.description && (
                      <span className={cn(
                        "text-xs mt-0.5",
                        active ? "text-accent/70" : "text-muted"
                      )}>
                        {link.description}
                      </span>
                    )}
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
