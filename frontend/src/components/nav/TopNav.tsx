import Link from "next/link";

const links: { href: string; label: string }[] = [
  { href: "/", label: "Home" },
  { href: "/portfolio", label: "Portfolio" },
  { href: "/backtest", label: "Backtest" },
  { href: "/forecast", label: "Forecast" },
  { href: "/experiments", label: "History" },
];

export function TopNav() {
  return (
    <nav className="border-b border-border/60 bg-bg/80 backdrop-blur sticky top-0 z-10">
      <div className="mx-auto max-w-6xl px-4 py-3 flex items-center justify-between">
        <Link href="/" className="font-semibold tracking-tight text-fg">
          QuantVision
        </Link>
        <ul className="flex gap-5 text-sm">
          {links.map((l) => (
            <li key={l.href}>
              <Link href={l.href} className="text-muted hover:text-fg transition-colors">
                {l.label}
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </nav>
  );
}
