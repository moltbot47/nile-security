"use client";

import { DefenderMetrics } from "@/components/dashboard/DefenderMetrics";

export default function DefenderKPIsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Defender-Side Intelligence</h1>
        <p className="text-gray-400 mt-1">
          Detection recall, patch success, and defensive posture metrics
        </p>
      </div>
      <DefenderMetrics />
    </div>
  );
}
