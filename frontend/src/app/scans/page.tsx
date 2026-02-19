"use client";

export default function ScansPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Security Scans</h1>
        <p className="text-gray-400 mt-1">
          AI-powered audit jobs — detect, patch, and exploit evaluations
        </p>
      </div>

      <div className="flex gap-4">
        <button className="px-4 py-2 bg-nile-600 text-white rounded-lg hover:bg-nile-500 transition-colors text-sm">
          New Scan
        </button>
        <select className="px-4 py-2 bg-gray-900 border border-gray-700 text-gray-300 rounded-lg text-sm">
          <option value="">All Statuses</option>
          <option value="queued">Queued</option>
          <option value="running">Running</option>
          <option value="succeeded">Succeeded</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      <div className="rounded-xl border border-gray-800">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-400 border-b border-gray-800">
              <th className="text-left py-3 px-4">Contract</th>
              <th className="text-left py-3 px-4">Mode</th>
              <th className="text-left py-3 px-4">Agent</th>
              <th className="text-center py-3 px-4">Status</th>
              <th className="text-right py-3 px-4">Tokens</th>
              <th className="text-right py-3 px-4">Cost</th>
              <th className="text-right py-3 px-4">Started</th>
            </tr>
          </thead>
          <tbody className="text-gray-300">
            {[
              { contract: "Noya Vault", mode: "detect", agent: "claude-opus-4.6", status: "succeeded", tokens: 45200, cost: 1.24, time: "2m ago" },
              { contract: "Tempo Bridge", mode: "patch", agent: "claude-opus-4.6", status: "running", tokens: 0, cost: 0, time: "Just now" },
              { contract: "DeFi Pool", mode: "exploit", agent: "codex-gpt-5.3", status: "queued", tokens: 0, cost: 0, time: "Pending" },
            ].map((s, i) => (
              <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-900/30">
                <td className="py-3 px-4 font-medium">{s.contract}</td>
                <td className="py-3 px-4">
                  <span className={`px-2 py-1 rounded text-xs ${
                    s.mode === "detect" ? "bg-nile-500/20 text-nile-400" :
                    s.mode === "patch" ? "bg-green-500/20 text-green-400" :
                    "bg-red-500/20 text-red-400"
                  }`}>{s.mode}</span>
                </td>
                <td className="py-3 px-4 text-gray-400">{s.agent}</td>
                <td className="py-3 px-4 text-center">
                  <span className={`px-2 py-1 rounded text-xs ${
                    s.status === "succeeded" ? "bg-green-500/20 text-green-400" :
                    s.status === "running" ? "bg-yellow-500/20 text-yellow-400" :
                    "bg-gray-500/20 text-gray-400"
                  }`}>{s.status}</span>
                </td>
                <td className="py-3 px-4 text-right text-gray-400">
                  {s.tokens > 0 ? s.tokens.toLocaleString() : "--"}
                </td>
                <td className="py-3 px-4 text-right text-gray-400">
                  {s.cost > 0 ? `$${s.cost.toFixed(2)}` : "--"}
                </td>
                <td className="py-3 px-4 text-right text-gray-400">{s.time}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
