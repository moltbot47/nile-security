"""Soul Valuation Engine — NILE 4-dimension scoring for human NIL value.

Re-maps the NILE framework from smart contract security to human identity:
  Name (25%):     Identity verification, social proof, domain authority
  Image (25%):    Public perception, sentiment, media coverage quality
  Likeness (25%): Market comparables, relative positioning in category
  Essence (25%):  Career trajectory, achievements, earning potential
"""

from dataclasses import dataclass, field

from nile.services.nile_scorer import GRADE_MAP, _clamp


@dataclass
class PersonNameInputs:
    """Identity verification and provenance signals."""

    verification_level: str = "unverified"  # unverified, verified, premium
    social_account_count: int = 0  # number of linked social accounts
    follower_count: int = 0
    domain_authority: float = 0.0  # 0-20
    kyc_completed: bool = False


@dataclass
class PersonImageInputs:
    """Public perception and sentiment signals."""

    positive_events: int = 0  # confirmed positive oracle events
    negative_events: int = 0  # confirmed negative oracle events
    neutral_events: int = 0
    avg_sentiment: float = 0.5  # 0.0 (very negative) to 1.0 (very positive)
    media_mention_count: int = 0
    engagement_rate: float = 0.0  # 0-100


@dataclass
class PersonLikenessInputs:
    """Market comparables and relative positioning."""

    category: str = "general"
    category_rank_percentile: float = 50.0  # 0-100, higher = better
    comparable_token_prices: list[float] = field(default_factory=list)
    peer_avg_market_cap: float = 0.0
    own_market_cap: float = 0.0


@dataclass
class PersonEssenceInputs:
    """Intrinsic value drivers."""

    career_years: int = 0
    achievement_count: int = 0  # awards, records, certifications
    endorsement_count: int = 0
    annual_earning_estimate: float = 0.0
    trajectory_slope: float = 0.0  # -1.0 (declining) to 1.0 (rising)
    consistency_score: float = 0.5  # 0.0-1.0 how consistent their performance is


@dataclass
class PersonValuationResult:
    total_score: float
    name_score: float
    image_score: float
    likeness_score: float
    essence_score: float
    grade: str
    fair_value_usd: float
    details: dict


# Category multipliers for fair value estimation
CATEGORY_MULTIPLIERS = {
    "athlete": 2.5,
    "musician": 2.0,
    "creator": 1.5,
    "entrepreneur": 2.0,
    "actor": 2.2,
    "politician": 1.0,
    "scientist": 1.2,
    "general": 1.0,
}

# Base value anchors by verification level
BASE_VALUES = {
    "unverified": 1_000,
    "verified": 10_000,
    "premium": 100_000,
}


def compute_person_name_score(inputs: PersonNameInputs) -> tuple[float, dict]:
    """Score identity verification and social proof (0-100)."""
    # Verification level (0-30)
    verification_points = {"unverified": 0, "verified": 20, "premium": 30}
    v_score = verification_points.get(inputs.verification_level, 0)

    # Social accounts linked (0-15)
    social_score = min(15.0, inputs.social_account_count * 3.0)

    # Follower reach (0-25, log scale)
    import math

    if inputs.follower_count > 0:
        follower_score = min(25.0, math.log10(inputs.follower_count) * 5)
    else:
        follower_score = 0.0

    # Domain authority (0-20)
    domain_score = min(20.0, inputs.domain_authority)

    # KYC bonus (0-10)
    kyc_score = 10.0 if inputs.kyc_completed else 0.0

    total = _clamp(v_score + social_score + follower_score + domain_score + kyc_score)
    details = {
        "verification": v_score,
        "social_presence": social_score,
        "follower_reach": round(follower_score, 2),
        "domain_authority": domain_score,
        "kyc_bonus": kyc_score,
    }
    return total, details


def compute_person_image_score(inputs: PersonImageInputs) -> tuple[float, dict]:
    """Score public perception and sentiment (0-100)."""
    # Sentiment base (0-50, centered at 25 for neutral 0.5)
    sentiment_score = inputs.avg_sentiment * 50

    # Event impact (0-25)
    event_total = inputs.positive_events + inputs.negative_events + inputs.neutral_events
    if event_total > 0:
        positive_ratio = inputs.positive_events / event_total
        event_score = positive_ratio * 25
    else:
        event_score = 12.5  # neutral baseline

    # Media coverage (0-15)
    media_score = min(15.0, inputs.media_mention_count * 1.5)

    # Engagement (0-10)
    engagement_score = min(10.0, inputs.engagement_rate * 0.1)

    total = _clamp(sentiment_score + event_score + media_score + engagement_score)
    details = {
        "sentiment": round(sentiment_score, 2),
        "event_impact": round(event_score, 2),
        "media_coverage": round(media_score, 2),
        "engagement": round(engagement_score, 2),
        "positive_events": inputs.positive_events,
        "negative_events": inputs.negative_events,
    }
    return total, details


def compute_person_likeness_score(inputs: PersonLikenessInputs) -> tuple[float, dict]:
    """Score market comparables and relative positioning (0-100)."""
    # Category rank percentile (0-50)
    rank_score = inputs.category_rank_percentile * 0.5

    # Market cap vs peers (0-30)
    if inputs.peer_avg_market_cap > 0 and inputs.own_market_cap > 0:
        ratio = inputs.own_market_cap / inputs.peer_avg_market_cap
        peer_score = min(30.0, ratio * 15)
    else:
        peer_score = 15.0  # neutral

    # Comparable diversity (0-20)
    comp_count = len(inputs.comparable_token_prices)
    comp_score = min(20.0, comp_count * 4) if comp_count > 0 else 10.0

    total = _clamp(rank_score + peer_score + comp_score)
    details = {
        "category_rank": round(rank_score, 2),
        "peer_comparison": round(peer_score, 2),
        "comparable_depth": round(comp_score, 2),
        "category": inputs.category,
    }
    return total, details


def compute_person_essence_score(inputs: PersonEssenceInputs) -> tuple[float, dict]:
    """Score intrinsic value drivers (0-100)."""
    # Career maturity (0-20)
    career_score = min(20.0, inputs.career_years * 2)

    # Achievements (0-25)
    achievement_score = min(25.0, inputs.achievement_count * 5)

    # Endorsements (0-15)
    endorsement_score = min(15.0, inputs.endorsement_count * 3)

    # Earning potential (0-20, log scale)
    import math

    if inputs.annual_earning_estimate > 0:
        earning_score = min(20.0, math.log10(inputs.annual_earning_estimate) * 3)
    else:
        earning_score = 0.0

    # Trajectory momentum (0-20)
    trajectory_score = (inputs.trajectory_slope + 1) * 10  # maps -1..1 to 0..20
    trajectory_score = _clamp(trajectory_score, 0, 20)

    total = _clamp(
        career_score + achievement_score + endorsement_score
        + earning_score + trajectory_score
    )
    details = {
        "career_maturity": round(career_score, 2),
        "achievements": round(achievement_score, 2),
        "endorsements": round(endorsement_score, 2),
        "earning_potential": round(earning_score, 2),
        "trajectory": round(trajectory_score, 2),
        "consistency": round(inputs.consistency_score, 2),
    }
    return total, details


def compute_person_valuation(
    name_inputs: PersonNameInputs,
    image_inputs: PersonImageInputs,
    likeness_inputs: PersonLikenessInputs,
    essence_inputs: PersonEssenceInputs,
    weights: dict[str, float] | None = None,
) -> PersonValuationResult:
    """Compute full NILE valuation for a person's NIL token."""
    w = weights or {"name": 0.25, "image": 0.25, "likeness": 0.25, "essence": 0.25}

    name_score, name_details = compute_person_name_score(name_inputs)
    image_score, image_details = compute_person_image_score(image_inputs)
    likeness_score, likeness_details = compute_person_likeness_score(likeness_inputs)
    essence_score, essence_details = compute_person_essence_score(essence_inputs)

    total = round(
        name_score * w["name"]
        + image_score * w["image"]
        + likeness_score * w["likeness"]
        + essence_score * w["essence"],
        2,
    )

    grade = "F"
    for threshold, g in GRADE_MAP:
        if total >= threshold:
            grade = g
            break

    # Fair value estimation
    base_value = BASE_VALUES.get(name_inputs.verification_level, 1_000)
    category = likeness_inputs.category
    category_mult = CATEGORY_MULTIPLIERS.get(category, 1.0)
    momentum = 1.0 + (essence_inputs.trajectory_slope * 0.3)  # -0.7 to 1.3
    nile_mult = total / 50.0  # score=50 => 1x, score=100 => 2x, score=0 => 0x

    fair_value = round(base_value * nile_mult * category_mult * momentum, 2)

    return PersonValuationResult(
        total_score=total,
        name_score=round(name_score, 2),
        image_score=round(image_score, 2),
        likeness_score=round(likeness_score, 2),
        essence_score=round(essence_score, 2),
        grade=grade,
        fair_value_usd=fair_value,
        details={
            "name": name_details,
            "image": image_details,
            "likeness": likeness_details,
            "essence": essence_details,
        },
    )
