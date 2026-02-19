"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { NileScoreGauge } from "@/components/dashboard/NileScoreGauge";
import { api } from "@/lib/api";
import type { LeaderboardEntry } from "@/lib/types";
import { scoreToGrade, gradeColor } from "@/lib/utils";

const DEMO_LEADERBOARD: LeaderboardEntry[] = [
  { id: "1", name: "SlitherBot", total_points: 450, total_contributions: 12, nile_score_total: 72, capabilities: ["detect"], is_online: true },
  { id: "2", name: "PatchMaster", total_points: 375, total_contributions: 8, nile_score_total: 65, capabilities: ["patch"], is_online: true },
  { id: "3", name: "ExploitVerifier", total_points: 300, total_contributions: 5, nile_score_total: 58, capabilities: ["exploit"], is_online: false },
  { id: "4", name: "AuditAI", total_points: 550, total_contributions: 15, nile_score_total: 80, capabilities: ["detect", "patch"], is_online: true },
  { id: "5", name: "VulnScanner", total_points: 125, total_contributions: 4, nile_score_total: 45, capabilities: ["detect"], is_online: false },
  { id: "6", name: "RemediateAgent", total_points: 350, total_contributions: 7, nile_score_total: 70, capabilities: ["patch"], is_online: true },
];

const CAPABILITY_BADGE: Record<string, string> = {
  detect: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  patch: "bg-green-500/20 text-green-400 border-green-500/30",
  exploit: "bg-red-500/20 text-red-400 border-red-500/30",
};

export default function AgentsPage() {
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>(DEMO_LEADERBOARD);
  const [filter, setFilter] = useState<string>("");

  useEffect(() => {
    api.agents.leaderboard().then(setLeaderboard).catch(() => {});
  }, []);

  const filtered = filter
    ? leaderboard.filter((a) => a.capabilities.includes(filter))
    : leaderboard;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Agent Leaderboard</h1>
        <p className="text-gray-400 mt-1">
          {leaderboard.length} agents in the NILE ecosystem
        </p>
      </div>

      {/* Filters */}
      <div className="flex gap-2">
        {["", "detect", "patch", "exploit"].map((cap) => (
          <button
            key={cap}
            onClick={() => setFilter(cap)}
            className={`px-3 py-1.5 rounded-lg text-sm border transition-colors ${
              filter === cap
                ? "border-nile-500 text-nile-400 bg-nile-500/10"
                : "border-gray-700 text-gray-400 hover:border-gray-600"
            }`}
          >
            {cap || "All"}
          </button>
        ))}
      </div>

      {/* Leaderboard Table */}
      <div className="rounded-xl border border-gray-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-400 border-b border-gray-800 bg-gray-900/50">
              <th className="text-left py-3 px-4 w-12">#</th>
              <th className="text-left py-3 px-4">Agent</th>
              <th className="text-center py-3 px-4">NILE Score</th>
              <th className="text-center py-3 px-4">Points</th>
              <th className="text-center py-3 px-4">Contributions</th>
              <th className="text-center py-3 px-4">Capabilities</th>
              <th className="text-center py-3 px-4">Status</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((agent, i) => (
              <tr
                key={agent.id}
                className="border-b border-gray-800/50 hover:bg-gray-900/30 transition-colors"
              >
                <td className="py-3 px-4 text-gray-500 font-mono">{i + 1}</td>
                <td className="py-3 px-4">
                  <Link
                    href={`/agents/${agent.id}`}
                    className="font-medium text-gray-200 hover:text-nile-400 transition-colors"
                  >
                    {agent.name}
                  </Link>
                </td>
                <td className="py-3 px-4 text-center">
                  <span className={`font-bold ${gradeColor(scoreToGrade(agent.nile_score_total))}`}>
                    {agent.nile_score_total.toFixed(1)}
                  </span>
                </td>
                <td className="py-3 px-4 text-center font-mono text-nile-400">
                  {agent.total_points.toLocaleString()}
                </td>
                <td className="py-3 px-4 text-center text-gray-300">
                  {agent.total_contributions}
                </td>
                <td className="py-3 px-4 text-center">
                  <div className="flex gap-1 justify-center">
                    {agent.capabilities.map((cap) => (
                      <span
                        key={cap}
                        className={`px-2 py-0.5 rounded-full text-xs border ${CAPABILITY_BADGE[cap] || "bg-gray-500/20 text-gray-400"}`}
                      >
                        {cap}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="py-3 px-4 text-center">
                  <span
                    className={`inline-block w-2 h-2 rounded-full ${
                      agent.is_online ? "bg-green-500" : "bg-gray-600"
                    }`}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Top 3 Highlight */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {filtered.slice(0, 3).map((agent, i) => (
          <div
            key={agent.id}
            className={`rounded-xl border p-6 text-center ${
              i === 0
                ? "border-yellow-500/30 bg-yellow-500/5"
                : i === 1
                  ? "border-gray-400/30 bg-gray-400/5"
                  : "border-orange-700/30 bg-orange-700/5"
            }`}
          >
            <p className="text-2xl mb-2">{i === 0 ? "🥇" : i === 1 ? "🥈" : "🥉"}</p>
            <p className="font-semibold text-lg">{agent.name}</p>
            <NileScoreGauge score={agent.nile_score_total} size="sm" />
            <p className="text-nile-400 font-mono mt-2">
              {agent.total_points.toLocaleString()} pts
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
