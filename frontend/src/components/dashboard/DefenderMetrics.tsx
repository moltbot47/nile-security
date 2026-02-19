"use client";

import { KPICard } from "./KPICard";
import { NileScoreGauge } from "./NileScoreGauge";
import { formatPercent } from "@/lib/utils";
import type { DefenderKPIs } from "@/lib/types";

const DEMO_DATA: DefenderKPIs = {
  detection_recall: 0.68,
  patch_success_rate: 0.54,
  false_positive_rate: 0.12,
  avg_time_to_detection_seconds: 420,
  avg_time_to_patch_seconds: 2100,
  audit_coverage_score: 0.75,
  security_posture_score: 0.72,
  time_range: "30d",
};

export function DefenderMetrics({ data }: { data?: DefenderKPIs }) {
  const d = data ?? DEMO_DATA;

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4 text-security-safe">Defender-Side KPIs</h2>

      <div className="flex flex-col lg:flex-row gap-6">
        <div className="flex-shrink-0 flex flex-col items-center">
          <NileScoreGauge score={d.security_posture_score * 100} size="lg" label="Security Posture" />
        </div>

        <div className="flex-1 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <KPICard
            title="Detection Recall"
            value={formatPercent(d.detection_recall)}
            subtitle="Vulnerabilities found by AI agents"
            color="green"
          />
          <KPICard
            title="Patch Success Rate"
            value={formatPercent(d.patch_success_rate)}
            subtitle="Fixes that preserve functionality"
            color="green"
          />
          <KPICard
            title="False Positive Rate"
            value={formatPercent(d.false_positive_rate)}
            subtitle="Lower is better"
            color={d.false_positive_rate > 0.2 ? "yellow" : "green"}
          />
          <KPICard
            title="Time to Detection"
            value={`${Math.round(d.avg_time_to_detection_seconds / 60)}m`}
            subtitle="Average per vulnerability"
            color="green"
          />
          <KPICard
            title="Time to Patch"
            value={`${Math.round(d.avg_time_to_patch_seconds / 60)}m`}
            subtitle="Detection to fix"
            color="green"
          />
          <KPICard
            title="Audit Coverage"
            value={formatPercent(d.audit_coverage_score)}
            subtitle="Contract code analyzed"
            color="green"
          />
        </div>
      </div>
    </div>
  );
}
