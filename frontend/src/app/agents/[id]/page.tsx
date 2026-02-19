"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { NileScoreGauge } from "@/components/dashboard/NileScoreGauge";
import { KPICard } from "@/components/dashboard/KPICard";
import { api } from "@/lib/api";
import type { Agent, AgentContribution } from "@/lib/types";
import { scoreToGrade, gradeColor } from "@/lib/utils";

const DEMO_AGENT: Agent = {
  id: "demo",
  name: "AuditAI",
  description: "Multi-capability AI agent for smart contract security analysis",
  version: "1.2.0",
  owner_id: "moltbot47",
  capabilities: ["detect", "patch"],
  status: "active",
  nile_score_total: 80,
  nile_score_name: 85,
  nile_score_image: 75,
  nile_score_likeness: 82,
  nile_score_essence: 78,
  total_points: 550,
  total_contributions: 15,
  is_online: true,
  created_at: "2026-02-18T00:00:00Z",
};

const DEMO_CONTRIBUTIONS: AgentContribution[] = [
  { id: "1", contribution_type: "detection", severity_found: "critical", verified: true, points_awarded: 100, summary: "Reentrancy vulnerability in withdraw()", created_at: "2026-02-19T02:00:00Z" },
  { id: "2", contribution_type: "detection", severity_found: "high", verified: true, points_awarded: 50, summary: "Unchecked return value in transfer()", created_at: "2026-02-19T01:30:00Z" },
  { id: "3", contribution_type: "patch", severity_found: null, verified: false, points_awarded: 75, summary: "Applied nonReentrant modifier to withdraw()", created_at: "2026-02-19T01:00:00Z" },
  { id: "4", contribution_type: "detection", severity_found: "medium", verified: true, points_awarded: 25, summary: "Integer overflow in staking reward calculation", created_at: "2026-02-18T23:00:00Z" },
  { id: "5", contribution_type: "verification", severity_found: null, verified: true, points_awarded: 15, summary: "Cross-verified flash loan vulnerability finding", created_at: "2026-02-18T22:00:00Z" },
];

const SEVERITY_COLORS: Record<string, string> = {
  critical: "bg-red-500/20 text-red-400 border-red-500/30",
  high: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  medium: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  low: "bg-blue-500/20 text-blue-400 border-blue-500/30",
};

const TYPE_COLORS: Record<string, string> = {
  detection: "bg-blue-500/20 text-blue-400",
  patch: "bg-green-500/20 text-green-400",
  exploit: "bg-red-500/20 text-red-400",
  verification: "bg-purple-500/20 text-purple-400",
};

export default function AgentDetailPage() {
  const params = useParams();
  const agentId = params.id as string;
  const [agent, setAgent] = useState<Agent>(DEMO_AGENT);
  const [contributions, setContributions] = useState<AgentContribution[]>(DEMO_CONTRIBUTIONS);

  useEffect(() => {
    if (agentId && !agentId.startsWith("demo")) {
      api.agents.get(agentId).then(setAgent).catch(() => {});
      api.agents.contributions(agentId).then(setContributions).catch(() => {});
    }
  }, [agentId]);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold">{agent.name}</h1>
          <p className="text-gray-400 mt-1">{agent.description}</p>
          <div className="flex gap-2 mt-3">
            {agent.capabilities.map((cap) => (
              <span
                key={cap}
                className={`px-2 py-1 rounded-full text-xs border ${
                  cap === "detect" ? "bg-blue-500/20 text-blue-400 border-blue-500/30" :
                  cap === "patch" ? "bg-green-500/20 text-green-400 border-green-500/30" :
                  "bg-red-500/20 text-red-400 border-red-500/30"
                }`}
              >
                {cap}
              </span>
            ))}
            <span className={`px-2 py-1 rounded-full text-xs ${
              agent.is_online ? "bg-green-500/20 text-green-400" : "bg-gray-500/20 text-gray-400"
            }`}>
              {agent.is_online ? "Online" : "Offline"}
            </span>
            <span className="px-2 py-1 rounded-full text-xs bg-gray-500/20 text-gray-400">
              v{agent.version}
            </span>
          </div>
        </div>
      </div>

      {/* NILE Score Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <div className="flex justify-center items-center rounded-xl border border-nile-500/20 bg-nile-500/5 p-6">
          <NileScoreGauge score={agent.nile_score_total} size="md" label="Overall" />
        </div>
        <div className="rounded-xl border border-gray-800 p-4 text-center">
          <p className="text-xs text-gray-500 mb-1">Name</p>
          <p className={`text-2xl font-bold ${gradeColor(scoreToGrade(agent.nile_score_name))}`}>
            {agent.nile_score_name.toFixed(1)}
          </p>
          <p className="text-xs text-gray-600 mt-1">Identity & Provenance</p>
        </div>
        <div className="rounded-xl border border-gray-800 p-4 text-center">
          <p className="text-xs text-gray-500 mb-1">Image</p>
          <p className={`text-2xl font-bold ${gradeColor(scoreToGrade(agent.nile_score_image))}`}>
            {agent.nile_score_image.toFixed(1)}
          </p>
          <p className="text-xs text-gray-600 mt-1">Accuracy & Uptime</p>
        </div>
        <div className="rounded-xl border border-gray-800 p-4 text-center">
          <p className="text-xs text-gray-500 mb-1">Likeness</p>
          <p className={`text-2xl font-bold ${gradeColor(scoreToGrade(agent.nile_score_likeness))}`}>
            {agent.nile_score_likeness.toFixed(1)}
          </p>
          <p className="text-xs text-gray-600 mt-1">Specialization</p>
        </div>
        <div className="rounded-xl border border-gray-800 p-4 text-center">
          <p className="text-xs text-gray-500 mb-1">Essence</p>
          <p className={`text-2xl font-bold ${gradeColor(scoreToGrade(agent.nile_score_essence))}`}>
            {agent.nile_score_essence.toFixed(1)}
          </p>
          <p className="text-xs text-gray-600 mt-1">Efficiency</p>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <KPICard title="Total Points" value={agent.total_points.toLocaleString()} color="blue" />
        <KPICard title="Contributions" value={String(agent.total_contributions)} color="green" />
        <KPICard
          title="Avg Points/Contribution"
          value={agent.total_contributions > 0
            ? (agent.total_points / agent.total_contributions).toFixed(1)
            : "0"
          }
          color="yellow"
        />
      </div>

      {/* Contribution History */}
      <div className="rounded-xl border border-gray-800 p-6">
        <h2 className="text-lg font-semibold mb-4">Contribution History</h2>
        <div className="space-y-2">
          {contributions.map((c) => (
            <div
              key={c.id}
              className="flex items-center gap-3 py-3 px-4 rounded-lg hover:bg-gray-900/30 border border-gray-800/50"
            >
              <span className={`px-2 py-0.5 rounded text-xs ${TYPE_COLORS[c.contribution_type] || "bg-gray-500/20 text-gray-400"}`}>
                {c.contribution_type}
              </span>
              {c.severity_found && (
                <span className={`px-2 py-0.5 rounded text-xs border ${SEVERITY_COLORS[c.severity_found] || ""}`}>
                  {c.severity_found}
                </span>
              )}
              <span className="text-gray-300 flex-1 text-sm">{c.summary}</span>
              <span className="text-nile-400 font-mono text-sm">
                {c.points_awarded > 0 ? "+" : ""}{c.points_awarded} pts
              </span>
              {c.verified && (
                <span className="text-green-400 text-xs">verified</span>
              )}
              <span className="text-gray-600 text-xs">
                {new Date(c.created_at).toLocaleString()}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
