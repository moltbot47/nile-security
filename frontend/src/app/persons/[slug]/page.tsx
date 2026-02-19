"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { NileScoreGauge } from "@/components/dashboard/NileScoreGauge";
import { api } from "@/lib/api";
import type { OracleEvent, Person, ValuationSnapshot } from "@/lib/types";
import { gradeColor, scoreToGrade } from "@/lib/utils";

const VERIFICATION_BADGE: Record<string, string> = {
  premium: "bg-purple-500/20 text-purple-400 border-purple-500/30",
  verified: "bg-green-500/20 text-green-400 border-green-500/30",
  unverified: "bg-gray-500/20 text-gray-400 border-gray-500/30",
};

const IMPACT_COLOR: Record<string, string> = {
  positive: "text-green-400",
  negative: "text-red-400",
  neutral: "text-gray-400",
};

function formatUSD(value: number | null): string {
  if (value == null) return "--";
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(1)}K`;
  return `$${value.toFixed(2)}`;
}

function impactLabel(score: number): string {
  if (score > 0) return "positive";
  if (score < 0) return "negative";
  return "neutral";
}

const DEMO_PERSON: Person = {
  id: "1",
  display_name: "LeBron James",
  slug: "lebron-james",
  bio: "4x NBA Champion, 4x NBA MVP, all-time leading scorer. Cultural icon and business mogul.",
  avatar_url: null,
  banner_url: null,
  verification_level: "premium",
  category: "athlete",
  tags: ["basketball", "nba", "entrepreneur"],
  social_links: { twitter: "@KingJames", instagram: "@kingjames" },
  nile_name_score: 95,
  nile_image_score: 88,
  nile_likeness_score: 82,
  nile_essence_score: 90,
  nile_total_score: 92,
  created_at: new Date().toISOString(),
  token_symbol: "BRON",
  token_price_usd: 14.50,
  token_market_cap_usd: 2_500_000,
};

export default function PersonDetailPage() {
  const params = useParams();
  const slug = params.slug as string;

  const [person, setPerson] = useState<Person | null>(null);
  const [valuations, setValuations] = useState<ValuationSnapshot[]>([]);
  const [events, setEvents] = useState<OracleEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    // The API uses UUID — try slug lookup via list endpoint first
    api.persons
      .list({ search: slug, limit: 1 })
      .then((results) => {
        if (results.length > 0) {
          return api.persons.get(results[0].id);
        }
        return null;
      })
      .then((p) => {
        if (p) {
          setPerson(p);
          api.persons.valuationHistory(p.id).then(setValuations).catch(() => {});
          api.persons.oracleEvents(p.id).then(setEvents).catch(() => {});
        } else {
          setPerson(DEMO_PERSON);
        }
      })
      .catch(() => {
        setPerson(DEMO_PERSON);
      })
      .finally(() => setLoading(false));
  }, [slug]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  if (!person) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Person not found</div>
      </div>
    );
  }

  const dimensions = [
    { label: "Name", score: person.nile_name_score, desc: "Identity verification & social proof" },
    { label: "Image", score: person.nile_image_score, desc: "Public perception & sentiment" },
    { label: "Likeness", score: person.nile_likeness_score, desc: "Market comparables & positioning" },
    { label: "Essence", score: person.nile_essence_score, desc: "Intrinsic value & trajectory" },
  ];

  return (
    <div className="space-y-6">
      {/* Banner + Profile Header */}
      <div className="rounded-xl border border-gray-800 overflow-hidden">
        <div className="h-32 bg-gradient-to-r from-nile-600/30 to-purple-600/30" />
        <div className="p-6 -mt-12">
          <div className="flex items-end gap-4">
            <div className="w-24 h-24 rounded-full bg-gray-800 border-4 border-[#0d0d0d] flex items-center justify-center text-3xl font-bold text-gray-500 flex-shrink-0 overflow-hidden">
              {person.avatar_url ? (
                <img src={person.avatar_url} alt={person.display_name} className="w-full h-full object-cover" />
              ) : (
                person.display_name.charAt(0).toUpperCase()
              )}
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold">{person.display_name}</h1>
                <span
                  className={`px-2 py-0.5 rounded-full text-xs border ${
                    VERIFICATION_BADGE[person.verification_level] || VERIFICATION_BADGE.unverified
                  }`}
                >
                  {person.verification_level}
                </span>
              </div>
              <p className="text-gray-400 text-sm mt-1">{person.category}</p>
            </div>
          </div>
          {person.bio && <p className="text-gray-300 mt-4 text-sm">{person.bio}</p>}

          {/* Tags + Social */}
          <div className="flex flex-wrap gap-2 mt-3">
            {person.tags.map((tag) => (
              <span
                key={tag}
                className="px-2 py-0.5 rounded-full text-xs bg-gray-800 text-gray-400 border border-gray-700"
              >
                {tag}
              </span>
            ))}
          </div>
          {Object.keys(person.social_links).length > 0 && (
            <div className="flex gap-3 mt-3 text-sm">
              {Object.entries(person.social_links).map(([platform, handle]) => (
                <span key={platform} className="text-nile-400">
                  {platform}: {handle}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Token Widget + Total Score */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Total NILE Score */}
        <div className="rounded-xl border border-gray-800 p-6 flex flex-col items-center justify-center">
          <NileScoreGauge score={person.nile_total_score} size="lg" label="NILE Total" />
          <span className={`text-lg font-bold mt-2 ${gradeColor(scoreToGrade(person.nile_total_score))}`}>
            Grade {scoreToGrade(person.nile_total_score)}
          </span>
        </div>

        {/* Token Info */}
        <div className="rounded-xl border border-gray-800 p-6 col-span-2">
          <h2 className="text-lg font-semibold mb-4">Soul Token</h2>
          {person.token_symbol ? (
            <div className="grid grid-cols-3 gap-4">
              <div>
                <p className="text-xs text-gray-500">Symbol</p>
                <p className="text-xl font-mono text-nile-400">${person.token_symbol}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Price</p>
                <p className="text-xl font-mono">{formatUSD(person.token_price_usd)}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Market Cap</p>
                <p className="text-xl font-mono">{formatUSD(person.token_market_cap_usd)}</p>
              </div>
            </div>
          ) : (
            <div className="text-gray-500 text-center py-6">
              No Soul Token deployed yet
            </div>
          )}
        </div>
      </div>

      {/* NILE 4-Dimension Breakdown */}
      <div className="rounded-xl border border-gray-800 p-6">
        <h2 className="text-lg font-semibold mb-4">NILE Dimension Breakdown</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          {dimensions.map((dim) => (
            <div key={dim.label} className="text-center">
              <NileScoreGauge score={dim.score} size="sm" label={dim.label} />
              <p className="text-xs text-gray-500 mt-1">{dim.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Oracle Events Timeline */}
      <div className="rounded-xl border border-gray-800 p-6">
        <h2 className="text-lg font-semibold mb-4">Oracle Events</h2>
        {events.length === 0 ? (
          <p className="text-gray-500 text-center py-4">No oracle events yet</p>
        ) : (
          <div className="space-y-3">
            {events.map((evt) => (
              <div
                key={evt.id}
                className="flex items-start gap-3 p-3 rounded-lg bg-gray-900/50 border border-gray-800/50"
              >
                <div
                  className={`w-2 h-2 rounded-full mt-2 flex-shrink-0 ${
                    evt.status === "confirmed"
                      ? "bg-green-500"
                      : evt.status === "rejected"
                        ? "bg-red-500"
                        : "bg-yellow-500"
                  }`}
                />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-200">{evt.headline}</p>
                  <div className="flex gap-3 mt-1 text-xs">
                    <span className="text-gray-500">{evt.source}</span>
                    <span className={IMPACT_COLOR[impactLabel(evt.impact_score)]}>
                      Impact: {evt.impact_score > 0 ? "+" : ""}{evt.impact_score}
                    </span>
                    <span className="text-gray-500">
                      {evt.confirmations}/{evt.confirmations + evt.rejections} confirmed
                    </span>
                  </div>
                </div>
                <span
                  className={`px-2 py-0.5 rounded text-xs ${
                    evt.status === "confirmed"
                      ? "bg-green-500/20 text-green-400"
                      : evt.status === "rejected"
                        ? "bg-red-500/20 text-red-400"
                        : "bg-yellow-500/20 text-yellow-400"
                  }`}
                >
                  {evt.status}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Valuation History */}
      {valuations.length > 0 && (
        <div className="rounded-xl border border-gray-800 p-6">
          <h2 className="text-lg font-semibold mb-4">Valuation History</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-400 border-b border-gray-800">
                  <th className="text-left py-2 px-3">Date</th>
                  <th className="text-center py-2 px-3">Total</th>
                  <th className="text-center py-2 px-3">N</th>
                  <th className="text-center py-2 px-3">I</th>
                  <th className="text-center py-2 px-3">L</th>
                  <th className="text-center py-2 px-3">E</th>
                  <th className="text-right py-2 px-3">Fair Value</th>
                  <th className="text-center py-2 px-3">Trigger</th>
                </tr>
              </thead>
              <tbody>
                {valuations.map((v) => (
                  <tr key={v.id} className="border-b border-gray-800/50">
                    <td className="py-2 px-3 text-gray-400">
                      {new Date(v.computed_at).toLocaleDateString()}
                    </td>
                    <td className="py-2 px-3 text-center font-mono">
                      <span className={gradeColor(scoreToGrade(v.total_score))}>
                        {v.total_score.toFixed(1)}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-center text-gray-300">{v.name_score.toFixed(1)}</td>
                    <td className="py-2 px-3 text-center text-gray-300">{v.image_score.toFixed(1)}</td>
                    <td className="py-2 px-3 text-center text-gray-300">{v.likeness_score.toFixed(1)}</td>
                    <td className="py-2 px-3 text-center text-gray-300">{v.essence_score.toFixed(1)}</td>
                    <td className="py-2 px-3 text-right font-mono text-nile-400">
                      {formatUSD(v.fair_value_usd)}
                    </td>
                    <td className="py-2 px-3 text-center text-gray-500">{v.trigger_type}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
