"use client";

import { AttackerMetrics } from "@/components/dashboard/AttackerMetrics";

export default function AttackerKPIsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Attacker-Side Intelligence</h1>
        <p className="text-gray-400 mt-1">
          Exploit capabilities, attack vectors, and offensive metrics from EVMbench evaluations
        </p>
      </div>
      <AttackerMetrics />
    </div>
  );
}
