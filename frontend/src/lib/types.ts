export interface NileScore {
  id: string;
  contract_id: string;
  total_score: number;
  name_score: number;
  image_score: number;
  likeness_score: number;
  essence_score: number;
  score_details: Record<string, unknown>;
  trigger_type: string;
  computed_at: string;
}

export interface Contract {
  id: string;
  address: string | null;
  name: string;
  source_url: string | null;
  chain: string;
  is_verified: boolean;
  created_at: string;
  latest_nile_score?: NileScore | null;
}

export interface AttackerKPIs {
  exploit_success_rate: number;
  avg_time_to_exploit_seconds: number;
  attack_vector_distribution: Record<string, number>;
  total_value_at_risk_usd: number;
  avg_complexity_score: number;
  zero_day_detection_rate: number;
  time_range: string;
}

export interface DefenderKPIs {
  detection_recall: number;
  patch_success_rate: number;
  false_positive_rate: number;
  avg_time_to_detection_seconds: number;
  avg_time_to_patch_seconds: number;
  audit_coverage_score: number;
  security_posture_score: number;
  time_range: string;
}

export interface AssetHealthItem {
  contract_id: string;
  contract_name: string;
  nile_score: number;
  grade: string;
  open_vulnerabilities: number;
  last_scan: string | null;
}

export interface BenchmarkBaseline {
  agent: string;
  mode: string;
  score_pct: number;
  source: string;
}

export type NileGrade = "A+" | "A" | "B" | "C" | "D" | "F";

// --- Agent Ecosystem Types ---

export interface Agent {
  id: string;
  name: string;
  description: string | null;
  version: string;
  owner_id: string;
  capabilities: string[];
  status: string;
  nile_score_total: number;
  nile_score_name: number;
  nile_score_image: number;
  nile_score_likeness: number;
  nile_score_essence: number;
  total_points: number;
  total_contributions: number;
  is_online: boolean;
  created_at: string;
}

export interface AgentContribution {
  id: string;
  contribution_type: string;
  severity_found: string | null;
  verified: boolean;
  points_awarded: number;
  summary: string | null;
  created_at: string;
}

export interface LeaderboardEntry {
  id: string;
  name: string;
  total_points: number;
  total_contributions: number;
  nile_score_total: number;
  capabilities: string[];
  is_online: boolean;
}

export interface EcosystemEvent {
  id: number;
  event_type: string;
  actor_id: string | null;
  target_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface ScanJob {
  id: string;
  contract_id: string;
  status: string;
  mode: string;
  agent: string;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

// --- Soul Token Market Types ---

export interface Person {
  id: string;
  display_name: string;
  slug: string;
  bio: string | null;
  avatar_url: string | null;
  banner_url: string | null;
  verification_level: string;
  category: string;
  tags: string[];
  social_links: Record<string, string>;
  nile_name_score: number;
  nile_image_score: number;
  nile_likeness_score: number;
  nile_essence_score: number;
  nile_total_score: number;
  created_at: string;
  token_symbol: string | null;
  token_price_usd: number | null;
  token_market_cap_usd: number | null;
}

export interface PersonListItem {
  id: string;
  display_name: string;
  slug: string;
  avatar_url: string | null;
  verification_level: string;
  category: string;
  nile_total_score: number;
  token_symbol: string | null;
  token_price_usd: number | null;
  token_market_cap_usd: number | null;
}

export interface ValuationSnapshot {
  id: string;
  name_score: number;
  image_score: number;
  likeness_score: number;
  essence_score: number;
  total_score: number;
  fair_value_usd: number;
  trigger_type: string;
  computed_at: string;
}

export interface OracleEvent {
  id: string;
  event_type: string;
  source: string;
  headline: string;
  impact_score: number;
  confidence: number;
  status: string;
  confirmations: number;
  rejections: number;
  created_at: string;
}

export interface CategoryCount {
  category: string;
  count: number;
}

export interface SoulToken {
  id: string;
  person_id: string;
  token_address: string | null;
  curve_address: string | null;
  name: string;
  symbol: string;
  phase: string;
  chain: string;
  current_price_eth: number;
  current_price_usd: number;
  market_cap_usd: number;
  total_supply: number;
  reserve_balance_eth: number;
  volume_24h_usd: number;
  price_change_24h_pct: number;
  holder_count: number;
  nile_valuation_total: number;
  graduation_threshold_eth: number;
  graduated_at: string | null;
  creator_address: string | null;
  created_at: string;
  person_name: string | null;
  person_slug: string | null;
  person_category: string | null;
}

export interface SoulTokenListItem {
  id: string;
  name: string;
  symbol: string;
  phase: string;
  current_price_usd: number;
  market_cap_usd: number;
  volume_24h_usd: number;
  price_change_24h_pct: number;
  holder_count: number;
  person_name: string | null;
  person_slug: string | null;
}

export interface MarketOverview {
  total_tokens: number;
  total_market_cap_usd: number;
  total_volume_24h_usd: number;
  graduating_soon_count: number;
}

export interface Trade {
  id: string;
  soul_token_id: string;
  side: string;
  token_amount: number;
  eth_amount: number;
  price_eth: number;
  price_usd: number;
  fee_total_eth: number;
  tx_hash: string | null;
  trader_address: string | null;
  phase: string;
  created_at: string;
}

export interface PriceCandle {
  open_time: string;
  close_time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume_eth: number;
  volume_usd: number;
  trade_count: number;
}

export interface QuoteResponse {
  person_id: string;
  side: string;
  input_amount: number;
  output_amount: number;
  fee: number;
  price_impact_pct: number;
  estimated_price: number;
}

export interface PortfolioItem {
  id: string;
  soul_token_id: string;
  token_symbol: string | null;
  person_name: string | null;
  balance: number;
  avg_buy_price_eth: number;
  total_invested_eth: number;
  realized_pnl_eth: number;
  current_price_eth: number | null;
  unrealized_pnl_eth: number | null;
}

export interface RiskSummary {
  soul_token_id: string;
  circuit_breaker_active: boolean;
  circuit_breaker_expiry: string | null;
  last_hour: {
    trade_count: number;
    unique_traders: number;
    total_volume_eth: number;
  };
}
