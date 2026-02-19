"use client";

import { useEffect, useState } from "react";
import { PersonCard } from "@/components/persons/PersonCard";
import { api } from "@/lib/api";
import type { PersonListItem } from "@/lib/types";

const DEMO_TRENDING: PersonListItem[] = [
  { id: "1", display_name: "LeBron James", slug: "lebron-james", avatar_url: null, verification_level: "premium", category: "athlete", nile_total_score: 92, token_symbol: "BRON", token_price_usd: 14.50, token_market_cap_usd: 2_500_000 },
  { id: "2", display_name: "Taylor Swift", slug: "taylor-swift", avatar_url: null, verification_level: "premium", category: "musician", nile_total_score: 88, token_symbol: "SWIFT", token_price_usd: 22.30, token_market_cap_usd: 4_100_000 },
  { id: "4", display_name: "Elon Musk", slug: "elon-musk", avatar_url: null, verification_level: "premium", category: "entrepreneur", nile_total_score: 85, token_symbol: "ELON", token_price_usd: 31.20, token_market_cap_usd: 6_200_000 },
];

export default function MarketPage() {
  const [trending, setTrending] = useState<PersonListItem[]>(DEMO_TRENDING);
  const [newListings, setNewListings] = useState<PersonListItem[]>([]);

  useEffect(() => {
    api.persons.trending().then(setTrending).catch(() => {});
    api.persons.list({ sort: "newest", limit: 6 }).then(setNewListings).catch(() => {});
  }, []);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Soul Token Market</h1>
        <p className="text-gray-400 mt-1">
          Trade human NIL value on bonding curves
        </p>
      </div>

      {/* Market Stats (placeholder) */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Total Tokens", value: String(trending.length + newListings.length) },
          { label: "24h Volume", value: "--" },
          { label: "Total Market Cap", value: "--" },
          { label: "Graduating Soon", value: "--" },
        ].map((stat) => (
          <div
            key={stat.label}
            className="rounded-xl border border-gray-800 p-4 text-center"
          >
            <p className="text-xs text-gray-500">{stat.label}</p>
            <p className="text-xl font-mono mt-1">{stat.value}</p>
          </div>
        ))}
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
