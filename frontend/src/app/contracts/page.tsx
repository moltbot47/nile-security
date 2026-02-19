"use client";

import { NileScoreGauge } from "@/components/dashboard/NileScoreGauge";

const DEMO_CONTRACTS = [
  { id: "1", name: "Noya Vault", chain: "Ethereum", score: 82, vulns: 2, verified: true },
  { id: "2", name: "Tempo Bridge", chain: "Tempo", score: 65, vulns: 5, verified: true },
  { id: "3", name: "DeFi Pool v2", chain: "Ethereum", score: 91, vulns: 0, verified: true },
  { id: "4", name: "Oracle Aggregator", chain: "Ethereum", score: 45, vulns: 8, verified: false },
  { id: "5", name: "Lending Protocol", chain: "Arbitrum", score: 73, vulns: 3, verified: true },
  { id: "6", name: "Staking Rewards", chain: "Ethereum", score: 88, vulns: 1, verified: true },
];

export default function ContractsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Smart Contracts</h1>
        <p className="text-gray-400 mt-1">
          Monitored contracts with NILE security scores
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {DEMO_CONTRACTS.map((c) => (
          <div
            key={c.id}
            className="rounded-xl border border-gray-800 p-6 hover:border-nile-500/30 transition-colors cursor-pointer"
          >
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="font-semibold text-lg">{c.name}</h3>
                <p className="text-sm text-gray-400">{c.chain}</p>
              </div>
              <NileScoreGauge score={c.score} size="sm" />
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">
                {c.vulns} open vuln{c.vulns !== 1 ? "s" : ""}
              </span>
              {c.verified && (
                <span className="text-nile-400 text-xs">Verified</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
