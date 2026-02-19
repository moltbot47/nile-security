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
