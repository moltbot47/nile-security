"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { PersonCard } from "@/components/persons/PersonCard";
import { api } from "@/lib/api";
import type { MarketOverview, PersonListItem, SoulTokenListItem } from "@/lib/types";

const DEMO_TRENDING: PersonListItem[] = [
  { id: "1", display_name: "LeBron James", slug: "lebron-james", avatar_url: null, verification_level: "premium", category: "athlete", nile_total_score: 92, token_symbol: "BRON", token_price_usd: 14.50, token_market_cap_usd: 2_500_000 },
  { id: "2", display_name: "Taylor Swift", slug: "taylor-swift", avatar_url: null, verification_level: "premium", category: "musician", nile_total_score: 88, token_symbol: "SWIFT", token_price_usd: 22.30, token_market_cap_usd: 4_100_000 },
  { id: "4", display_name: "Elon Musk", slug: "elon-musk", avatar_url: null, verification_level: "premium", category: "entrepreneur", nile_total_score: 85, token_symbol: "ELON", token_price_usd: 31.20, token_market_cap_usd: 6_200_000 },
];

function formatUSD(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(1)}K`;
  return `$${value.toFixed(2)}`;
}

export default function MarketPage() {
  const [trending, setTrending] = useState<PersonListItem[]>(DEMO_TRENDING);
  const [newListings, setNewListings] = useState<PersonListItem[]>([]);
  const [tokens, setTokens] = useState<SoulTokenListItem[]>([]);
  const [overview, setOverview] = useState<MarketOverview | null>(null);
  const [sort, setSort] = useState("market_cap");

  useEffect(() => {
    api.persons.trending().then(setTrending).catch(() => {});
    api.persons.list({ sort: "newest", limit: 6 }).then(setNewListings).catch(() => {});
    api.soulTokens.marketOverview().then(setOverview).catch(() => {});
  }, []);

  useEffect(() => {
    api.soulTokens.list(sort).then(setTokens).catch(() => {});
  }, [sort]);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Soul Token Market</h1>
        <p className="text-gray-400 mt-1">
          Trade human NIL value on bonding curves
        </p>
      </div>

      {/* Market Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="rounded-xl border border-gray-800 p-4 text-center">
          <p className="text-xs text-gray-500">Total Tokens</p>
          <p className="text-xl font-mono mt-1">{overview?.total_tokens ?? "--"}</p>
        </div>
        <div className="rounded-xl border border-gray-800 p-4 text-center">
          <p className="text-xs text-gray-500">24h Volume</p>
          <p className="text-xl font-mono mt-1">
            {overview ? formatUSD(overview.total_volume_24h_usd) : "--"}
          </p>
        </div>
        <div className="rounded-xl border border-gray-800 p-4 text-center">
          <p className="text-xs text-gray-500">Total Market Cap</p>
          <p className="text-xl font-mono mt-1">
            {overview ? formatUSD(overview.total_market_cap_usd) : "--"}
          </p>
        </div>
        <div className="rounded-xl border border-gray-800 p-4 text-center">
          <p className="text-xs text-gray-500">Graduating Soon</p>
          <p className="text-xl font-mono mt-1">{overview?.graduating_soon_count ?? "--"}</p>
        </div>
      </div>

      {/* Trending */}
      <div>
        <h2 className="text-xl font-semibold mb-3">Trending</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {trending.map((p) => (
            <PersonCard key={p.id} person={p} />
          ))}
        </div>
      </div>

      {/* Token Table */}
      {tokens.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xl font-semibold">All Tokens</h2>
            <div className="flex gap-2">
              {[
                { value: "market_cap", label: "MCap" },
                { value: "volume", label: "Volume" },
                { value: "new", label: "New" },
              ].map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setSort(opt.value)}
                  className={`px-3 py-1 rounded text-xs border transition-colors ${
                    sort === opt.value
                      ? "border-nile-500 text-nile-400 bg-nile-500/10"
                      : "border-gray-700 text-gray-400 hover:border-gray-600"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
          <div className="rounded-xl border border-gray-800 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-400 border-b border-gray-800 bg-gray-900/50">
                  <th className="text-left py-3 px-4">Token</th>
                  <th className="text-left py-3 px-4">Person</th>
                  <th className="text-center py-3 px-4">Phase</th>
                  <th className="text-right py-3 px-4">Price</th>
                  <th className="text-right py-3 px-4">MCap</th>
                  <th className="text-right py-3 px-4">24h Vol</th>
                  <th className="text-right py-3 px-4">24h</th>
                </tr>
              </thead>
              <tbody>
                {tokens.map((t) => (
                  <tr key={t.id} className="border-b border-gray-800/50 hover:bg-gray-900/30">
                    <td className="py-3 px-4 font-mono text-nile-400">${t.symbol}</td>
                    <td className="py-3 px-4">
                      {t.person_slug ? (
                        <Link href={`/persons/${t.person_slug}`} className="text-gray-200 hover:text-nile-400">
                          {t.person_name}
                        </Link>
                      ) : (
                        t.name
                      )}
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span className={`px-2 py-0.5 rounded text-xs ${
                        t.phase === "bonding" ? "bg-yellow-500/20 text-yellow-400"
                        : t.phase === "amm" ? "bg-green-500/20 text-green-400"
                        : "bg-blue-500/20 text-blue-400"
                      }`}>
                        {t.phase}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right font-mono">{formatUSD(t.current_price_usd)}</td>
                    <td className="py-3 px-4 text-right font-mono">{formatUSD(t.market_cap_usd)}</td>
                    <td className="py-3 px-4 text-right font-mono">{formatUSD(t.volume_24h_usd)}</td>
                    <td className={`py-3 px-4 text-right font-mono ${
                      t.price_change_24h_pct >= 0 ? "text-green-400" : "text-red-400"
                    }`}>
                      {t.price_change_24h_pct >= 0 ? "+" : ""}{t.price_change_24h_pct.toFixed(2)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* New Listings */}
      {newListings.length > 0 && (
        <div>
          <h2 className="text-xl font-semibold mb-3">New Listings</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {newListings.map((p) => (
              <PersonCard key={p.id} person={p} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
