const BASE_URL = "/api/v1";

async function fetchJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export const api = {
  contracts: {
    list: () => fetchJSON<import("./types").Contract[]>("/contracts"),
    get: (id: string) => fetchJSON<import("./types").Contract>(`/contracts/${id}`),
    nileHistory: (id: string) =>
      fetchJSON<import("./types").NileScore[]>(`/contracts/${id}/nile-history`),
  },
  kpis: {
    attacker: (range = "30d") =>
      fetchJSON<import("./types").AttackerKPIs>(`/kpis/attacker?time_range=${range}`),
    defender: (range = "30d") =>
      fetchJSON<import("./types").DefenderKPIs>(`/kpis/defender?time_range=${range}`),
    assetHealth: () => fetchJSON<{ items: import("./types").AssetHealthItem[] }>("/kpis/asset-health"),
  },
  benchmarks: {
    list: () => fetchJSON<unknown[]>("/benchmarks"),
    baselines: () => fetchJSON<import("./types").BenchmarkBaseline[]>("/benchmarks/baselines"),
  },
};
