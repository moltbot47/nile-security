"""NILE Scoring Engine — composite security scoring for smart contracts.

Each contract receives a 0-100 score across four equally-weighted dimensions:
  Name (25%):     Identity verification, provenance, audit history
  Image (25%):    Security posture, vulnerability count, patch cadence
  Likeness (25%): Pattern matching against known vulnerability signatures
  Essence (25%):  Test coverage, complexity, upgrade risk, dependencies
"""

from dataclasses import dataclass, field


@dataclass
class NameInputs:
    is_verified: bool = False
    audit_count: int = 0
    age_days: int = 0
    team_identified: bool = False
    ecosystem_score: float = 0.0  # 0-20


@dataclass
class ImageInputs:
    open_critical: int = 0
    open_high: int = 0
    open_medium: int = 0
    avg_patch_time_days: float | None = None
    trend: float = 0.0  # -10 to +10


@dataclass
class LikenessInputs:
    slither_findings: list[dict] = field(default_factory=list)
    evmbench_pattern_matches: list[dict] = field(default_factory=list)


@dataclass
class EssenceInputs:
    test_coverage_pct: float = 0.0  # 0-100
    avg_cyclomatic_complexity: float = 5.0
    has_proxy_pattern: bool = False
    has_admin_keys: bool = False
    has_timelock: bool = True
    external_call_count: int = 0


@dataclass
class NileScoreResult:
    total_score: float
    name_score: float
    image_score: float
    likeness_score: float
    essence_score: float
    grade: str
    details: dict


GRADE_MAP = [
    (90, "A+"),
    (80, "A"),
    (70, "B"),
    (60, "C"),
    (50, "D"),
    (0, "F"),
]


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def compute_name_score(inputs: NameInputs) -> tuple[float, dict]:
    source_score = 20.0 if inputs.is_verified else 0.0
    audit_score = min(20.0, inputs.audit_count * 6.67)
    maturity_score = min(20.0, inputs.age_days / 365 * 20) if inputs.age_days > 0 else 0.0
    team_score = 20.0 if inputs.team_identified else 5.0
    ecosystem = min(20.0, inputs.ecosystem_score)

    total = _clamp(source_score + audit_score + maturity_score + team_score + ecosystem)
    details = {
        "source_verified": source_score,
        "audit_history": audit_score,
        "maturity": maturity_score,
        "team_identification": team_score,
        "ecosystem_presence": ecosystem,
    }
    return total, details


def compute_image_score(inputs: ImageInputs) -> tuple[float, dict]:
    base = 100.0
    base -= inputs.open_critical * 25
    base -= inputs.open_high * 15
    base -= inputs.open_medium * 5

    patch_bonus = 0.0
    if inputs.avg_patch_time_days is not None:
        patch_bonus = max(0.0, 10 - inputs.avg_patch_time_days)

    total = _clamp(base + patch_bonus + inputs.trend)
    details = {
        "base_from_vulns": base,
        "patch_cadence_bonus": patch_bonus,
        "trend_adjustment": inputs.trend,
        "open_critical": inputs.open_critical,
        "open_high": inputs.open_high,
        "open_medium": inputs.open_medium,
    }
    return total, details


def compute_likeness_score(inputs: LikenessInputs) -> tuple[float, dict]:
    score = 100.0
    severity_penalty = {"high": 15, "medium": 8, "low": 3, "info": 0}

    slither_deductions = 0.0
    for finding in inputs.slither_findings:
        sev = finding.get("severity", "info")
        slither_deductions += severity_penalty.get(sev, 0)

    pattern_deductions = 0.0
    for match in inputs.evmbench_pattern_matches:
        confidence = match.get("confidence", 0.0)
        if confidence > 0.8:
            pattern_deductions += 20
        elif confidence > 0.6:
            pattern_deductions += 10
        elif confidence > 0.4:
            pattern_deductions += 5

    total = _clamp(score - slither_deductions - pattern_deductions)
    details = {
        "slither_deductions": slither_deductions,
        "pattern_match_deductions": pattern_deductions,
        "slither_finding_count": len(inputs.slither_findings),
        "evmbench_match_count": len(inputs.evmbench_pattern_matches),
    }
    return total, details


def compute_essence_score(inputs: EssenceInputs) -> tuple[float, dict]:
    coverage = min(25.0, inputs.test_coverage_pct * 0.25)
    complexity_score = max(0.0, 25 - (inputs.avg_cyclomatic_complexity - 5) * 2.5)
    complexity_score = min(25.0, complexity_score)

    upgrade_score = 25.0
    if inputs.has_proxy_pattern:
        upgrade_score -= 10
    if inputs.has_admin_keys:
        upgrade_score -= 5
    if not inputs.has_timelock:
        upgrade_score -= 5

    dep_score = max(0.0, 25 - inputs.external_call_count * 2)

    total = _clamp(coverage + complexity_score + upgrade_score + dep_score)
    details = {
        "test_coverage": coverage,
        "complexity": complexity_score,
        "upgrade_risk": upgrade_score,
        "dependency_risk": dep_score,
    }
    return total, details


def compute_nile_score(
    name_inputs: NameInputs,
    image_inputs: ImageInputs,
    likeness_inputs: LikenessInputs,
    essence_inputs: EssenceInputs,
    weights: dict[str, float] | None = None,
) -> NileScoreResult:
    w = weights or {"name": 0.25, "image": 0.25, "likeness": 0.25, "essence": 0.25}

    name_score, name_details = compute_name_score(name_inputs)
    image_score, image_details = compute_image_score(image_inputs)
    likeness_score, likeness_details = compute_likeness_score(likeness_inputs)
    essence_score, essence_details = compute_essence_score(essence_inputs)

    total = (
        name_score * w["name"]
        + image_score * w["image"]
        + likeness_score * w["likeness"]
        + essence_score * w["essence"]
    )
    total = round(total, 2)

    grade = "F"
    for threshold, g in GRADE_MAP:
        if total >= threshold:
            grade = g
            break

    return NileScoreResult(
        total_score=total,
        name_score=round(name_score, 2),
        image_score=round(image_score, 2),
        likeness_score=round(likeness_score, 2),
        essence_score=round(essence_score, 2),
        grade=grade,
        details={
            "name": name_details,
            "image": image_details,
            "likeness": likeness_details,
            "essence": essence_details,
        },
    )
