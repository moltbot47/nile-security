"""Pydantic schemas for KPI metrics."""

from pydantic import BaseModel


class AttackerKPIs(BaseModel):
    exploit_success_rate: float = 0.0
    avg_time_to_exploit_seconds: float = 0.0
    attack_vector_distribution: dict[str, float] = {}
    total_value_at_risk_usd: float = 0.0
    avg_complexity_score: float = 0.0
    zero_day_detection_rate: float = 0.0
    time_range: str = "30d"


class DefenderKPIs(BaseModel):
    detection_recall: float = 0.0
    patch_success_rate: float = 0.0
    false_positive_rate: float = 0.0
    avg_time_to_detection_seconds: float = 0.0
    avg_time_to_patch_seconds: float = 0.0
    audit_coverage_score: float = 0.0
    security_posture_score: float = 0.0
    time_range: str = "30d"


class AssetHealthItem(BaseModel):
    contract_id: str
    contract_name: str
    nile_score: float
    grade: str
    open_vulnerabilities: int
    last_scan: str | None = None


class AssetHealthResponse(BaseModel):
    items: list[AssetHealthItem] = []
    total_contracts: int = 0
    avg_nile_score: float = 0.0


class KPITrendPoint(BaseModel):
    timestamp: str
    value: float


class KPITrendsResponse(BaseModel):
    metric_name: str
    dimension: str
    data: list[KPITrendPoint] = []
