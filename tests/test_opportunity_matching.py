from pathlib import Path

from src.inzira.opportunity_matching import (
    MatchProfile,
    load_catalogue,
    rank_opportunities,
)


CATALOGUE = Path(__file__).parents[1] / "data" / "opportunities.json"


def profile(**overrides):
    values = {
        "goals": ("employment",),
        "participant_profiles": ("job_seeker",),
        "skills": ("no_formal_skill",),
        "support_types": ("job_listings",),
        "access_mode": "either",
        "readiness": "within_30_days",
    }
    values.update(overrides)
    return MatchProfile(**values)


def test_catalogue_loads_verified_pathways():
    opportunities = load_catalogue(CATALOGUE)
    assert len(opportunities) >= 7
    assert all(item.source_url.startswith("https://") for item in opportunities)
    assert all(item.apply_url.startswith("https://") for item in opportunities)
    assert all("jobportal.kora.rw" not in item.apply_url for item in opportunities)


def test_recent_graduate_internship_profile_ranks_internship_first():
    matches = rank_opportunities(
        load_catalogue(CATALOGUE),
        profile(
            goals=("internship",),
            participant_profiles=("student_or_recent_graduate",),
            skills=("digital",),
            support_types=("internship", "work_experience"),
            access_mode="online",
        ),
    )
    assert matches[0].opportunity.id == "professional_internship"


def test_farmer_profile_prioritises_agricultural_route():
    matches = rank_opportunities(
        load_catalogue(CATALOGUE),
        profile(
            goals=("agriculture",),
            participant_profiles=("farmer",),
            skills=("agriculture",),
            support_types=("extension", "market_linkage"),
            access_mode="local",
        ),
        {"agricultural_activity": 1},
    )
    assert matches[0].opportunity.id == "rab_twigire_muhinzi"


def test_existing_business_profile_prioritises_rdb_support():
    matches = rank_opportunities(
        load_catalogue(CATALOGUE),
        profile(
            goals=("business",),
            participant_profiles=("existing_business",),
            skills=("business",),
            support_types=("business_advice", "finance_readiness"),
            access_mode="local",
        ),
        {"nonfarm_business": 1},
    )
    assert matches[0].opportunity.id == "rdb_business_support"


def test_scores_are_bounded_and_explained():
    matches = rank_opportunities(load_catalogue(CATALOGUE), profile())
    assert all(0 <= match.score <= 100 for match in matches)
    assert all(match.reasons for match in matches[:3])
    assert all(match.cautions for match in matches)
