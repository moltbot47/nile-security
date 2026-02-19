"""Tests for the NILE scoring engine."""

from nile.services.nile_scorer import (
    EssenceInputs,
    ImageInputs,
    LikenessInputs,
    NameInputs,
    compute_essence_score,
    compute_image_score,
    compute_likeness_score,
    compute_name_score,
    compute_nile_score,
)


def test_name_score_verified_contract():
    inputs = NameInputs(
        is_verified=True, audit_count=3, age_days=730, team_identified=True, ecosystem_score=15.0
    )
    score, details = compute_name_score(inputs)
    assert score >= 80.0
    assert details["source_verified"] == 20.0
    assert details["team_identification"] == 20.0


def test_name_score_unverified_anonymous():
    inputs = NameInputs(is_verified=False, audit_count=0, age_days=0, team_identified=False)
    score, _ = compute_name_score(inputs)
    assert score == 5.0  # Only partial team score


def test_image_score_clean_contract():
    inputs = ImageInputs(open_critical=0, open_high=0, open_medium=0, trend=5.0)
    score, _ = compute_image_score(inputs)
    assert score == 100.0  # Capped at 100


def test_image_score_critical_vulns():
    inputs = ImageInputs(open_critical=2, open_high=1)
    score, _ = compute_image_score(inputs)
    assert score == 35.0  # 100 - 50 - 15


def test_likeness_score_no_patterns():
    inputs = LikenessInputs()
    score, _ = compute_likeness_score(inputs)
    assert score == 100.0


def test_likeness_score_high_confidence_match():
    inputs = LikenessInputs(
        evmbench_pattern_matches=[{"confidence": 0.9}, {"confidence": 0.7}]
    )
    score, details = compute_likeness_score(inputs)
    assert score == 70.0  # 100 - 20 - 10
    assert details["evmbench_match_count"] == 2


def test_essence_score_well_tested():
    inputs = EssenceInputs(
        test_coverage_pct=90.0,
        avg_cyclomatic_complexity=3.0,
        has_proxy_pattern=False,
        has_admin_keys=False,
        has_timelock=True,
        external_call_count=2,
    )
    score, details = compute_essence_score(inputs)
    assert score >= 85.0


def test_essence_score_risky_contract():
    inputs = EssenceInputs(
        test_coverage_pct=10.0,
        avg_cyclomatic_complexity=15.0,
        has_proxy_pattern=True,
        has_admin_keys=True,
        has_timelock=False,
        external_call_count=10,
    )
    score, _ = compute_essence_score(inputs)
    assert score < 30.0


def test_composite_nile_score():
    result = compute_nile_score(
        name_inputs=NameInputs(is_verified=True, audit_count=2, age_days=365, team_identified=True),
        image_inputs=ImageInputs(open_critical=0, open_high=1),
        likeness_inputs=LikenessInputs(
            slither_findings=[{"severity": "medium"}],
            evmbench_pattern_matches=[{"confidence": 0.5}],
        ),
        essence_inputs=EssenceInputs(test_coverage_pct=80.0, avg_cyclomatic_complexity=6.0),
    )
    assert 0 <= result.total_score <= 100
    assert result.grade in ("A+", "A", "B", "C", "D", "F")
    assert "name" in result.details
    assert "image" in result.details
    assert "likeness" in result.details
    assert "essence" in result.details


def test_grade_assignment():
    # A+ grade
    result = compute_nile_score(
        name_inputs=NameInputs(
            is_verified=True, audit_count=3, age_days=730,
            team_identified=True, ecosystem_score=20,
        ),
        image_inputs=ImageInputs(open_critical=0, open_high=0, trend=5),
        likeness_inputs=LikenessInputs(),
        essence_inputs=EssenceInputs(test_coverage_pct=95, avg_cyclomatic_complexity=3),
    )
    assert result.grade == "A+"
    assert result.total_score >= 90
