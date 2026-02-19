"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", label: "Dashboard", icon: "grid" },
  { href: "/contracts", label: "Contracts", icon: "file" },
  { href: "/kpis/attacker", label: "Attacker KPIs", icon: "zap" },
  { href: "/kpis/defender", label: "Defender KPIs", icon: "shield" },
  { href: "/benchmarks", label: "Benchmarks", icon: "bar-chart" },
  { href: "/scans", label: "Scans", icon: "search" },
  { href: "/agents", label: "Agents", icon: "users" },
  { href: "/ecosystem", label: "Ecosystem", icon: "globe" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 border-r border-gray-800 bg-[#0d0d0d] min-h-screen p-4 flex flex-col">
      <div className="mb-8">
        <h1 className="text-2xl font-bold">
          <span className="text-nile-400">NILE</span>
          <span className="text-gray-500 text-sm ml-2">Security</span>
        </h1>
        <p className="text-xs text-gray-600 mt-1">Smart Contract Intelligence</p>
      </div>

      <nav className="flex-1 space-y-1">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "block px-3 py-2 rounded-lg text-sm transition-colors",
              pathname === item.href
                ? "bg-nile-500/10 text-nile-400 border border-nile-500/20"
                : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"
            )}
          >
            {item.label}
          </Link>
        ))}
      </nav>

      <div className="mt-auto pt-4 border-t border-gray-800">
        <div className="text-xs text-gray-600">
          <p>NILE v0.2.0</p>
          <p>Agent Ecosystem</p>
        </div>
      </div>
    </aside>
  );
}
