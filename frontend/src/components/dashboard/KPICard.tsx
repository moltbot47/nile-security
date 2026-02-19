"use client";

import { cn } from "@/lib/utils";

interface KPICardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: "up" | "down" | "neutral";
  color?: "green" | "yellow" | "red" | "blue";
}

export function KPICard({ title, value, subtitle, trend, color = "blue" }: KPICardProps) {
  const colorMap = {
    green: "border-security-safe/30 bg-security-safe/5",
    yellow: "border-security-warning/30 bg-security-warning/5",
    red: "border-security-danger/30 bg-security-danger/5",
    blue: "border-nile-500/30 bg-nile-500/5",
  };

  const valueColorMap = {
    green: "text-security-safe",
    yellow: "text-security-warning",
    red: "text-security-danger",
    blue: "text-nile-400",
  };

  return (
    <div className={cn("rounded-xl border p-6", colorMap[color])}>
      <p className="text-sm text-gray-400 mb-1">{title}</p>
      <p className={cn("text-3xl font-bold", valueColorMap[color])}>{value}</p>
      {subtitle && (
        <p className="text-xs text-gray-500 mt-2 flex items-center gap-1">
          {trend === "up" && <span className="text-security-safe">+</span>}
          {trend === "down" && <span className="text-security-danger">-</span>}
          {subtitle}
        </p>
      )}
    </div>
  );
}
