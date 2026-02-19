"use client";

import Link from "next/link";
import { NileScoreGauge } from "@/components/dashboard/NileScoreGauge";
import type { PersonListItem } from "@/lib/types";

const VERIFICATION_BADGE: Record<string, string> = {
  premium: "bg-purple-500/20 text-purple-400 border-purple-500/30",
  verified: "bg-green-500/20 text-green-400 border-green-500/30",
  unverified: "bg-gray-500/20 text-gray-400 border-gray-500/30",
};

const CATEGORY_COLORS: Record<string, string> = {
  athlete: "text-blue-400",
  musician: "text-pink-400",
  creator: "text-yellow-400",
  entrepreneur: "text-green-400",
  actor: "text-red-400",
  politician: "text-gray-400",
  scientist: "text-cyan-400",
  general: "text-gray-500",
};

function formatUSD(value: number | null): string {
  if (value == null) return "--";
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(1)}K`;
  return `$${value.toFixed(2)}`;
}

export function PersonCard({ person }: { person: PersonListItem }) {
  return (
    <Link href={`/persons/${person.slug}`}>
      <div className="rounded-xl border border-gray-800 bg-gray-900/30 p-5 hover:border-nile-500/40 transition-all hover:bg-gray-900/60 cursor-pointer">
        <div className="flex items-start gap-4">
          {/* Avatar */}
          <div className="w-14 h-14 rounded-full bg-gray-800 flex items-center justify-center text-xl font-bold text-gray-500 flex-shrink-0 overflow-hidden">
            {person.avatar_url ? (
              <img
                src={person.avatar_url}
                alt={person.display_name}
                className="w-full h-full object-cover"
              />
            ) : (
              person.display_name.charAt(0).toUpperCase()
            )}
          </div>

          {/* Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-gray-200 truncate">
                {person.display_name}
              </h3>
              <span
                className={`px-2 py-0.5 rounded-full text-[10px] border ${
                  VERIFICATION_BADGE[person.verification_level] || VERIFICATION_BADGE.unverified
                }`}
              >
                {person.verification_level}
              </span>
            </div>
            <p className={`text-xs mt-0.5 ${CATEGORY_COLORS[person.category] || "text-gray-500"}`}>
              {person.category}
            </p>
          </div>

          {/* Score */}
          <NileScoreGauge score={person.nile_total_score} size="sm" />
        </div>

        {/* Token info */}
        {person.token_symbol && (
          <div className="mt-4 pt-3 border-t border-gray-800 flex items-center justify-between text-sm">
            <span className="font-mono text-nile-400">${person.token_symbol}</span>
            <div className="flex gap-4">
              <span className="text-gray-400">
                {formatUSD(person.token_price_usd)}
              </span>
              <span className="text-gray-500">
                MCap {formatUSD(person.token_market_cap_usd)}
              </span>
            </div>
          </div>
        )}
      </div>
    </Link>
  );
}
