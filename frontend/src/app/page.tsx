"use client";

import { KPICard } from "@/components/dashboard/KPICard";
import { NileScoreGauge } from "@/components/dashboard/NileScoreGauge";
import { AttackerMetrics } from "@/components/dashboard/AttackerMetrics";
import { DefenderMetrics } from "@/components/dashboard/DefenderMetrics";

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">NILE Security Dashboard</h1>
        <p className="text-gray-400 mt-1">
          Smart contract security intelligence — attacker and defender KPIs
        </p>
      </div>

      {/* Overview KPI Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="col-span-1 flex justify-center items-center rounded-xl border border-nile-500/20 bg-nile-500/5 p-6">
          <NileScoreGauge score={74.5} size="md" label="Avg NILE Score" />
        </div>
        <KPICard title="Contracts Monitored" value="40" subtitle="From EVMbench audits" color="blue" />
        <KPICard
          title="Open Vulnerabilities"
          value="120"
          subtitle="Across all contracts"
          color="yellow"
        />
        <KPICard
          title="Benchmark Runs"
          value="3"
          subtitle="Detect / Patch / Exploit"
          color="blue"
        />
      </div>

      {/* Benchmark Baseline Comparison */}
      <div className="rounded-xl border border-gray-800 p-6">
        <h2 className="text-lg font-semibold mb-4">EVMbench Baseline Comparison</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="text-center p-4 rounded-lg bg-gray-900">
            <p className="text-sm text-gray-400">GPT-5.3-Codex (Exploit)</p>
            <p className="text-2xl font-bold text-red-400">72.2%</p>
          </div>
          <div className="text-center p-4 rounded-lg bg-gray-900">
            <p className="text-sm text-gray-400">GPT-5 (Exploit)</p>
            <p className="text-2xl font-bold text-orange-400">31.9%</p>
          </div>
          <div className="text-center p-4 rounded-lg bg-gray-900 border border-nile-500/30">
            <p className="text-sm text-gray-400">NILE Agent (Target)</p>
            <p className="text-2xl font-bold text-nile-400">--.--%</p>
            <p className="text-xs text-gray-500 mt-1">Run benchmark to populate</p>
          </div>
        </div>
      </div>

      {/* Attacker + Defender Metrics */}
      <AttackerMetrics />
      <DefenderMetrics />

      {/* Contract Health Table */}
      <div className="rounded-xl border border-gray-800 p-6">
        <h2 className="text-lg font-semibold mb-4">Contract Security Ratings</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 border-b border-gray-800">
                <th className="text-left py-3 px-4">Contract</th>
                <th className="text-left py-3 px-4">Chain</th>
                <th className="text-center py-3 px-4">NILE Score</th>
                <th className="text-center py-3 px-4">Grade</th>
                <th className="text-center py-3 px-4">Open Vulns</th>
                <th className="text-center py-3 px-4">Status</th>
              </tr>
            </thead>
            <tbody className="text-gray-300">
              {[
                { name: "Noya Vault", score: 82, grade: "A", vulns: 2, chain: "Ethereum" },
                { name: "Tempo Bridge", score: 65, grade: "C", vulns: 5, chain: "Tempo" },
                { name: "DeFi Pool", score: 91, grade: "A+", vulns: 0, chain: "Ethereum" },
                { name: "Oracle Aggregator", score: 45, grade: "F", vulns: 8, chain: "Ethereum" },
                { name: "Lending Protocol", score: 73, grade: "B", vulns: 3, chain: "Arbitrum" },
              ].map((c) => (
                <tr key={c.name} className="border-b border-gray-800/50 hover:bg-gray-900/30">
                  <td className="py-3 px-4 font-medium">{c.name}</td>
                  <td className="py-3 px-4 text-gray-400">{c.chain}</td>
                  <td className="py-3 px-4 text-center">{c.score}</td>
                  <td className={`py-3 px-4 text-center font-bold ${
                    c.score >= 80 ? "text-security-safe" :
                    c.score >= 60 ? "text-security-warning" :
                    "text-security-danger"
                  }`}>{c.grade}</td>
                  <td className="py-3 px-4 text-center">{c.vulns}</td>
                  <td className="py-3 px-4 text-center">
                    <span className={`inline-block w-2 h-2 rounded-full ${
                      c.vulns === 0 ? "bg-security-safe" :
                      c.vulns <= 3 ? "bg-security-warning" :
                      "bg-security-danger"
                    }`} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
