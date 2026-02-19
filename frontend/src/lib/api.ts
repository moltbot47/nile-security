import type {
  Agent,
  AgentContribution,
  AssetHealthItem,
  AttackerKPIs,
  BenchmarkBaseline,
  CategoryCount,
  Contract,
  DefenderKPIs,
  EcosystemEvent,
  LeaderboardEntry,
  NileScore,
  OracleEvent,
  Person,
  PersonListItem,
  ValuationSnapshot,
} from "./types";

const BASE_URL = "/api/v1";

async function fetchJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export const api = {
  contracts: {
    list: () => fetchJSON<Contract[]>("/contracts"),
    get: (id: string) => fetchJSON<Contract>(`/contracts/${id}`),
    nileHistory: (id: string) => fetchJSON<NileScore[]>(`/contracts/${id}/nile-history`),
  },
  kpis: {
    attacker: (range = "30d") => fetchJSON<AttackerKPIs>(`/kpis/attacker?time_range=${range}`),
    defender: (range = "30d") => fetchJSON<DefenderKPIs>(`/kpis/defender?time_range=${range}`),
    assetHealth: () => fetchJSON<{ items: AssetHealthItem[] }>("/kpis/asset-health"),
  },
  benchmarks: {
    list: () => fetchJSON<unknown[]>("/benchmarks"),
    baselines: () => fetchJSON<BenchmarkBaseline[]>("/benchmarks/baselines"),
  },
  agents: {
    list: (status?: string) =>
      fetchJSON<Agent[]>(`/agents${status ? `?status=${status}` : ""}`),
    get: (id: string) => fetchJSON<Agent>(`/agents/${id}`),
    leaderboard: (limit = 25) => fetchJSON<LeaderboardEntry[]>(`/agents/leaderboard?limit=${limit}`),
    contributions: (id: string) => fetchJSON<AgentContribution[]>(`/agents/${id}/contributions`),
  },
  events: {
    history: (limit = 50) => fetchJSON<EcosystemEvent[]>(`/events/history?limit=${limit}`),
  },
  persons: {
    list: (params?: { category?: string; search?: string; sort?: string; limit?: number }) => {
      const qs = new URLSearchParams();
      if (params?.category) qs.set("category", params.category);
      if (params?.search) qs.set("search", params.search);
      if (params?.sort) qs.set("sort", params.sort);
      if (params?.limit) qs.set("limit", String(params.limit));
      const q = qs.toString();
      return fetchJSON<PersonListItem[]>(`/persons${q ? `?${q}` : ""}`);
    },
    get: (id: string) => fetchJSON<Person>(`/persons/${id}`),
    trending: (limit = 20) => fetchJSON<PersonListItem[]>(`/persons/trending?limit=${limit}`),
    categories: () => fetchJSON<CategoryCount[]>("/persons/categories"),
    valuationHistory: (id: string, limit = 50) =>
      fetchJSON<ValuationSnapshot[]>(`/persons/${id}/valuation-history?limit=${limit}`),
    oracleEvents: (id: string, status?: string) =>
      fetchJSON<OracleEvent[]>(`/persons/${id}/oracle-events${status ? `?status=${status}` : ""}`),
  },
};

export function createEventSource(): EventSource {
  return new EventSource(`${BASE_URL}/events/stream`);
}
