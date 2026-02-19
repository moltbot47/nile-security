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
