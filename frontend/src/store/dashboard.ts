import { create } from "zustand";
import type { Agent, AttackerKPIs, Contract, DefenderKPIs, EcosystemEvent, LeaderboardEntry } from "@/lib/types";
import { api } from "@/lib/api";

interface DashboardState {
  contracts: Contract[];
  agents: Agent[];
  leaderboard: LeaderboardEntry[];
  events: EcosystemEvent[];
  attackerKPIs: AttackerKPIs | null;
  defenderKPIs: DefenderKPIs | null;
  loading: boolean;
  error: string | null;

  fetchContracts: () => Promise<void>;
  fetchAgents: () => Promise<void>;
  fetchLeaderboard: () => Promise<void>;
  fetchEvents: () => Promise<void>;
  fetchAttackerKPIs: () => Promise<void>;
  fetchDefenderKPIs: () => Promise<void>;
  addEvent: (event: EcosystemEvent) => void;
}

export const useDashboard = create<DashboardState>((set) => ({
  contracts: [],
  agents: [],
  leaderboard: [],
  events: [],
  attackerKPIs: null,
  defenderKPIs: null,
  loading: false,
  error: null,

  fetchContracts: async () => {
    try {
      const contracts = await api.contracts.list();
      set({ contracts });
    } catch (e) {
      set({ error: "Failed to load contracts" });
    }
  },

  fetchAgents: async () => {
    try {
      const agents = await api.agents.list("active");
      set({ agents });
    } catch (e) {
      set({ error: "Failed to load agents" });
    }
  },

  fetchLeaderboard: async () => {
    try {
      const leaderboard = await api.agents.leaderboard();
      set({ leaderboard });
    } catch (e) {
      set({ error: "Failed to load leaderboard" });
    }
  },

  fetchEvents: async () => {
    try {
      const events = await api.events.history();
      set({ events });
    } catch (e) {
      set({ error: "Failed to load events" });
    }
  },

  fetchAttackerKPIs: async () => {
    try {
      const attackerKPIs = await api.kpis.attacker();
      set({ attackerKPIs });
    } catch (e) {
      set({ error: "Failed to load attacker KPIs" });
    }
  },

  fetchDefenderKPIs: async () => {
    try {
      const defenderKPIs = await api.kpis.defender();
      set({ defenderKPIs });
    } catch (e) {
      set({ error: "Failed to load defender KPIs" });
    }
  },

  addEvent: (event) => {
    set((state) => ({
      events: [event, ...state.events].slice(0, 100),
    }));
  },
}));
