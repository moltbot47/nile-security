"use client";

import { KPICard } from "./KPICard";
import { formatPercent } from "@/lib/utils";
import type { AttackerKPIs } from "@/lib/types";

// Demo data for initial render
const DEMO_DATA: AttackerKPIs = {
  exploit_success_rate: 0.722,
  avg_time_to_exploit_seconds: 1847,
  attack_vector_distribution: {
    reentrancy: 0.28,
    access_control: 0.22,
    oracle_manipulation: 0.15,
    flash_loan: 0.12,
    logic_error: 0.10,
    other: 0.13,
  },
  total_value_at_risk_usd: 142000000,
  avg_complexity_score: 3.7,
  zero_day_detection_rate: 0.08,
  time_range: "30d",
};

export function AttackerMetrics({ data }: { data?: AttackerKPIs }) {
  const d = data ?? DEMO_DATA;

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4 text-red-400">Attacker-Side KPIs</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <KPICard
          title="Exploit Success Rate"
          value={formatPercent(d.exploit_success_rate)}
          subtitle="EVMbench baseline (GPT-5.3-Codex)"
          color="red"
        />
        <KPICard
          title="Avg Time to Exploit"
          value={`${Math.round(d.avg_time_to_exploit_seconds / 60)}m`}
          subtitle="Per vulnerability average"
          color="red"
        />
        <KPICard
          title="Zero-Day Detection Rate"
          value={formatPercent(d.zero_day_detection_rate)}
          subtitle="Previously unknown vulnerabilities"
          color="red"
        />
        <KPICard
          title="Value at Risk"
          value={`$${(d.total_value_at_risk_usd / 1e6).toFixed(0)}M`}
          subtitle="Total across monitored contracts"
          color="red"
        />
        <KPICard
          title="Complexity Score"
          value={d.avg_complexity_score.toFixed(1)}
          subtitle="Average exploit complexity (1-10)"
          color="red"
        />
        <KPICard
          title="Top Attack Vector"
          value={Object.entries(d.attack_vector_distribution).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "N/A"}
          subtitle={formatPercent(
            Object.entries(d.attack_vector_distribution).sort((a, b) => b[1] - a[1])[0]?.[1] ?? 0
          )}
          color="red"
        />
      </div>

      <div className="mt-6 rounded-xl border border-red-900/30 bg-red-900/5 p-6">
        <h3 className="text-sm font-medium text-gray-400 mb-4">Attack Vector Distribution</h3>
        <div className="space-y-3">
          {Object.entries(d.attack_vector_distribution)
            .sort((a, b) => b[1] - a[1])
            .map(([category, pct]) => (
              <div key={category} className="flex items-center gap-3">
                <span className="text-sm text-gray-300 w-40 capitalize">
                  {category.replace(/_/g, " ")}
                </span>
                <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-red-500 rounded-full transition-all duration-500"
                    style={{ width: `${pct * 100}%` }}
                  />
                </div>
                <span className="text-sm text-gray-400 w-14 text-right">
                  {formatPercent(pct)}
                </span>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}
