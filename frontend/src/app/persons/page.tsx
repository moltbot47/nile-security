"use client";

import { useEffect, useState } from "react";
import { PersonCard } from "@/components/persons/PersonCard";
import { api } from "@/lib/api";
import type { CategoryCount, PersonListItem } from "@/lib/types";

const DEMO_PERSONS: PersonListItem[] = [
  { id: "1", display_name: "LeBron James", slug: "lebron-james", avatar_url: null, verification_level: "premium", category: "athlete", nile_total_score: 92, token_symbol: "BRON", token_price_usd: 14.50, token_market_cap_usd: 2_500_000 },
  { id: "2", display_name: "Taylor Swift", slug: "taylor-swift", avatar_url: null, verification_level: "premium", category: "musician", nile_total_score: 88, token_symbol: "SWIFT", token_price_usd: 22.30, token_market_cap_usd: 4_100_000 },
  { id: "3", display_name: "MrBeast", slug: "mrbeast", avatar_url: null, verification_level: "verified", category: "creator", nile_total_score: 76, token_symbol: "BEAST", token_price_usd: 5.80, token_market_cap_usd: 890_000 },
  { id: "4", display_name: "Elon Musk", slug: "elon-musk", avatar_url: null, verification_level: "premium", category: "entrepreneur", nile_total_score: 85, token_symbol: "ELON", token_price_usd: 31.20, token_market_cap_usd: 6_200_000 },
  { id: "5", display_name: "Zendaya", slug: "zendaya", avatar_url: null, verification_level: "verified", category: "actor", nile_total_score: 71, token_symbol: "ZEN", token_price_usd: 3.40, token_market_cap_usd: 420_000 },
  { id: "6", display_name: "Patrick Mahomes", slug: "patrick-mahomes", avatar_url: null, verification_level: "verified", category: "athlete", nile_total_score: 82, token_symbol: "MAHOMES", token_price_usd: 9.10, token_market_cap_usd: 1_600_000 },
];

const SORT_OPTIONS = [
  { value: "score", label: "NILE Score" },
  { value: "newest", label: "Newest" },
  { value: "name", label: "Name" },
];

export default function PersonsPage() {
  const [persons, setPersons] = useState<PersonListItem[]>(DEMO_PERSONS);
  const [categories, setCategories] = useState<CategoryCount[]>([]);
  const [activeCategory, setActiveCategory] = useState("");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState("score");

  useEffect(() => {
    api.persons.categories().then(setCategories).catch(() => {});
  }, []);

  useEffect(() => {
    api.persons
      .list({
        category: activeCategory || undefined,
        search: search || undefined,
        sort,
      })
      .then(setPersons)
      .catch(() => {});
  }, [activeCategory, sort, search]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Persons</h1>
        <p className="text-gray-400 mt-1">
          Discover and trade NIL (Name, Image, Likeness) Soul Tokens
        </p>
      </div>

      {/* Search + Sort */}
      <div className="flex flex-col sm:flex-row gap-3">
        <input
          type="text"
          placeholder="Search persons..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 px-4 py-2 rounded-lg bg-gray-900 border border-gray-700 text-gray-200 placeholder-gray-500 focus:outline-none focus:border-nile-500"
        />
        <div className="flex gap-2">
          {SORT_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setSort(opt.value)}
              className={`px-3 py-2 rounded-lg text-sm border transition-colors ${
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

      {/* Category Filters */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setActiveCategory("")}
          className={`px-3 py-1.5 rounded-lg text-sm border transition-colors ${
            activeCategory === ""
              ? "border-nile-500 text-nile-400 bg-nile-500/10"
              : "border-gray-700 text-gray-400 hover:border-gray-600"
          }`}
        >
          All
        </button>
        {categories.map((cat) => (
          <button
            key={cat.category}
            onClick={() => setActiveCategory(cat.category)}
            className={`px-3 py-1.5 rounded-lg text-sm border transition-colors ${
              activeCategory === cat.category
                ? "border-nile-500 text-nile-400 bg-nile-500/10"
                : "border-gray-700 text-gray-400 hover:border-gray-600"
            }`}
          >
            {cat.category}{" "}
            <span className="text-gray-600">({cat.count})</span>
          </button>
        ))}
      </div>

      {/* Person Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {persons.map((person) => (
          <PersonCard key={person.id} person={person} />
        ))}
      </div>

      {persons.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          No persons found matching your criteria.
        </div>
      )}
    </div>
  );
}
