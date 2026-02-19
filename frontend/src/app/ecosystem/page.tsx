"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { api, createEventSource } from "@/lib/api";
import type { Agent, EcosystemEvent } from "@/lib/types";
import { scoreToGrade, gradeColor } from "@/lib/utils";

interface GraphNode {
  id: string;
  name: string;
  type: "agent" | "contract";
  score: number;
  capabilities: string[];
  isOnline: boolean;
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
}

interface GraphEdge {
  source: string;
  target: string;
  type: string;
}

const CAPABILITY_COLORS: Record<string, string> = {
  detect: "#3b82f6",
  patch: "#22c55e",
  exploit: "#ef4444",
};

function getNodeColor(node: GraphNode): string {
  if (node.type === "contract") return "#6366f1";
  const cap = node.capabilities[0];
  return CAPABILITY_COLORS[cap] || "#8b5cf6";
}

export default function EcosystemPage() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [events, setEvents] = useState<EcosystemEvent[]>([]);
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const animationRef = useRef<number>(0);

  // Load data
  useEffect(() => {
    api.agents.list("active").then(setAgents).catch(() => {});
    api.events.history(100).then(setEvents).catch(() => {});
  }, []);

  // Build graph from agents
  useEffect(() => {
    const graphNodes: GraphNode[] = agents.map((a, i) => {
      const angle = (2 * Math.PI * i) / Math.max(agents.length, 1);
      const radius = 200;
      return {
        id: a.id,
        name: a.name,
        type: "agent" as const,
        score: a.nile_score_total,
        capabilities: a.capabilities,
        isOnline: a.is_online,
        x: 400 + Math.cos(angle) * radius + (Math.random() - 0.5) * 50,
        y: 300 + Math.sin(angle) * radius + (Math.random() - 0.5) * 50,
        vx: 0,
        vy: 0,
        radius: Math.max(12, a.nile_score_total / 3),
      };
    });

    // If no agents, add demo nodes
    if (graphNodes.length === 0) {
      const demoAgents = [
        { name: "SlitherBot", cap: "detect", score: 72 },
        { name: "PatchMaster", cap: "patch", score: 65 },
        { name: "ExploitVerifier", cap: "exploit", score: 58 },
        { name: "AuditAI", cap: "detect", score: 80 },
        { name: "VulnScanner", cap: "detect", score: 45 },
        { name: "RemediateAgent", cap: "patch", score: 70 },
      ];
      demoAgents.forEach((d, i) => {
        const angle = (2 * Math.PI * i) / demoAgents.length;
        graphNodes.push({
          id: `demo-${i}`,
          name: d.name,
          type: "agent",
          score: d.score,
          capabilities: [d.cap],
          isOnline: Math.random() > 0.3,
          x: 400 + Math.cos(angle) * 200 + (Math.random() - 0.5) * 30,
          y: 300 + Math.sin(angle) * 200 + (Math.random() - 0.5) * 30,
          vx: (Math.random() - 0.5) * 0.5,
          vy: (Math.random() - 0.5) * 0.5,
          radius: Math.max(12, d.score / 3),
        });
      });
    }

    setNodes(graphNodes);
  }, [agents]);

  // Canvas animation loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || nodes.length === 0) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;

    function tick() {
      if (!ctx || !canvas) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Draw edges between nearby nodes
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[i].x - nodes[j].x;
          const dy = nodes[i].y - nodes[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 200) {
            const alpha = 1 - dist / 200;
            ctx.beginPath();
            ctx.moveTo(nodes[i].x, nodes[i].y);
            ctx.lineTo(nodes[j].x, nodes[j].y);
            ctx.strokeStyle = `rgba(56, 189, 248, ${alpha * 0.15})`;
            ctx.lineWidth = 1;
            ctx.stroke();
          }
        }
      }

      // Apply simple physics
      for (const node of nodes) {
        // Gravity toward center
        node.vx += (centerX - node.x) * 0.0002;
        node.vy += (centerY - node.y) * 0.0002;

        // Random drift
        node.vx += (Math.random() - 0.5) * 0.05;
        node.vy += (Math.random() - 0.5) * 0.05;

        // Damping
        node.vx *= 0.98;
        node.vy *= 0.98;

        node.x += node.vx;
        node.y += node.vy;

        // Bounds
        node.x = Math.max(node.radius, Math.min(canvas.width - node.radius, node.x));
        node.y = Math.max(node.radius, Math.min(canvas.height - node.radius, node.y));
      }

      // Draw nodes
      for (const node of nodes) {
        const color = getNodeColor(node);

        // Glow
        const gradient = ctx.createRadialGradient(
          node.x, node.y, 0,
          node.x, node.y, node.radius * 2
        );
        gradient.addColorStop(0, `${color}33`);
        gradient.addColorStop(1, "transparent");
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius * 2, 0, Math.PI * 2);
        ctx.fill();

        // Node circle
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.globalAlpha = node.isOnline ? 1 : 0.4;
        ctx.fill();
        ctx.globalAlpha = 1;

        // Online indicator
        if (node.isOnline) {
          ctx.beginPath();
          ctx.arc(node.x + node.radius * 0.6, node.y - node.radius * 0.6, 4, 0, Math.PI * 2);
          ctx.fillStyle = "#22c55e";
          ctx.fill();
        }

        // Label
        ctx.fillStyle = "#e5e7eb";
        ctx.font = "11px monospace";
        ctx.textAlign = "center";
        ctx.fillText(node.name, node.x, node.y + node.radius + 14);
      }

      animationRef.current = requestAnimationFrame(tick);
    }

    animationRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animationRef.current);
  }, [nodes]);

  // Mouse hover detection
  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      setMousePos({ x: e.clientX, y: e.clientY });

      const found = nodes.find((n) => {
        const dx = n.x - x;
        const dy = n.y - y;
        return Math.sqrt(dx * dx + dy * dy) < n.radius + 5;
      });
      setHoveredNode(found || null);
    },
    [nodes]
  );

  // SSE for live updates
  useEffect(() => {
    const es = createEventSource();
    es.onmessage = (e) => {
      try {
        const event: EcosystemEvent = JSON.parse(e.data);
        setEvents((prev) => [event, ...prev].slice(0, 100));
      } catch {}
    };
    return () => es.close();
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">
          <span className="text-nile-400">NILE</span> Ecosystem
        </h1>
        <p className="text-gray-400 mt-1">
          Live agent network — {agents.length || 6} agents connected
        </p>
      </div>

      {/* Legend */}
      <div className="flex gap-6 text-sm text-gray-400">
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-blue-500" />
          Detect
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-green-500" />
          Patch
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-red-500" />
          Exploit
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-green-500" />
          Online
        </div>
      </div>

      {/* Network Graph */}
      <div className="relative rounded-xl border border-gray-800 overflow-hidden bg-[#050510]">
        <canvas
          ref={canvasRef}
          width={800}
          height={600}
          className="w-full"
          onMouseMove={handleMouseMove}
          style={{ cursor: hoveredNode ? "pointer" : "default" }}
        />

        {/* Tooltip */}
        {hoveredNode && (
          <div
            className="fixed z-50 bg-gray-900 border border-gray-700 rounded-lg p-3 text-sm pointer-events-none"
            style={{ left: mousePos.x + 12, top: mousePos.y + 12 }}
          >
            <p className="font-semibold text-white">{hoveredNode.name}</p>
            <p className="text-gray-400">
              Score: {hoveredNode.score.toFixed(1)} ({scoreToGrade(hoveredNode.score)})
            </p>
            <p className="text-gray-400">
              Capabilities: {hoveredNode.capabilities.join(", ")}
            </p>
            <p className={hoveredNode.isOnline ? "text-green-400" : "text-gray-500"}>
              {hoveredNode.isOnline ? "Online" : "Offline"}
            </p>
          </div>
        )}
      </div>

      {/* Activity Feed */}
      <div className="rounded-xl border border-gray-800 p-6">
        <h2 className="text-lg font-semibold mb-4">Live Activity Feed</h2>
        <div className="space-y-2 max-h-80 overflow-y-auto">
          {events.length === 0 ? (
            <p className="text-gray-500 text-sm">No events yet. Agents will post activity here.</p>
          ) : (
            events.map((e) => (
              <div
                key={e.id}
                className="flex items-center gap-3 py-2 px-3 rounded-lg hover:bg-gray-900/50 text-sm"
              >
                <span
                  className={`w-2 h-2 rounded-full flex-shrink-0 ${
                    e.event_type.includes("joined") ? "bg-green-500" :
                    e.event_type.includes("vuln") || e.event_type.includes("detection") ? "bg-red-500" :
                    e.event_type.includes("patch") ? "bg-blue-500" :
                    "bg-gray-500"
                  }`}
                />
                <span className="text-gray-300 flex-1">{e.event_type}</span>
                <span className="text-gray-600 text-xs">
                  {new Date(e.created_at).toLocaleTimeString()}
                </span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
