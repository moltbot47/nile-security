"use client";

import { KPICard } from "@/components/dashboard/KPICard";

const BASELINES = [
  { agent: "GPT-5.3-Codex", mode: "exploit", score: 72.2 },
  { agent: "GPT-5", mode: "exploit", score: 31.9 },
  { agent: "Claude Opus 4.6", mode: "detect", score: 37824, unit: "$" },
];

export default function BenchmarksPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">EVMbench Benchmarks</h1>
        <p className="text-gray-400 mt-1">
          Benchmark results against published EVMbench baselines (120 vulnerabilities, 40 audits)
        </p>
      </div>

      <div className="rounded-xl border border-gray-800 p-6">
        <h2 className="text-lg font-semibold mb-4">Published Baselines</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {BASELINES.map((b) => (
            <KPICard
              key={`${b.agent}-${b.mode}`}
              title={`${b.agent} (${b.mode})`}
              value={b.unit === "$" ? `$${(b.score / 1000).toFixed(1)}K` : `${b.score}%`}
              subtitle="Published EVMbench result"
              color="blue"
            />
          ))}
        </div>
      </div>

      <div className="rounded-xl border border-gray-800 p-6">
        <h2 className="text-lg font-semibold mb-4">NILE Agent Runs</h2>
        <div className="text-center py-12 text-gray-500">
          <p className="text-lg mb-2">No benchmark runs yet</p>
          <p className="text-sm">
            Configure your EVMbench integration and run your first benchmark
          </p>
          <button className="mt-4 px-6 py-2 bg-nile-600 text-white rounded-lg hover:bg-nile-500 transition-colors">
            Start Benchmark Run
          </button>
        </div>
      </div>

      <div className="rounded-xl border border-gray-800 p-6">
        <h2 className="text-lg font-semibold mb-4">Three Evaluation Modes</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-lg bg-gray-900">
            <h3 className="font-medium text-nile-400 mb-2">Detect</h3>
            <p className="text-sm text-gray-400">
              Audit smart contracts and score on recall of ground-truth vulnerabilities
            </p>
          </div>
          <div className="p-4 rounded-lg bg-gray-900">
            <h3 className="font-medium text-security-safe mb-2">Patch</h3>
            <p className="text-sm text-gray-400">
              Modify vulnerable contracts while preserving functionality
            </p>
          </div>
          <div className="p-4 rounded-lg bg-gray-900">
            <h3 className="font-medium text-security-danger mb-2">Exploit</h3>
            <p className="text-sm text-gray-400">
              Execute end-to-end fund-draining attacks in sandboxed environments
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
