from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class Opportunity:
    id: str
    provider: str
    title_en: str
    title_rw: str
    summary_en: str
    summary_rw: str
    goals: tuple[str, ...]
    profiles: tuple[str, ...]
    skills: tuple[str, ...]
    support_types: tuple[str, ...]
    delivery: tuple[str, ...]
    digital_help_available: bool
    eligibility_en: tuple[str, ...]
    eligibility_rw: tuple[str, ...]
    availability_en: str
    availability_rw: str
    next_steps_en: tuple[str, ...]
    next_steps_rw: tuple[str, ...]
    apply_url: str
    source_url: str

    def title(self, language: str) -> str:
        return self.title_rw if language == "rw" else self.title_en

    def summary(self, language: str) -> str:
        return self.summary_rw if language == "rw" else self.summary_en

    def eligibility(self, language: str) -> tuple[str, ...]:
        return self.eligibility_rw if language == "rw" else self.eligibility_en

    def availability(self, language: str) -> str:
        return self.availability_rw if language == "rw" else self.availability_en

    def next_steps(self, language: str) -> tuple[str, ...]:
        return self.next_steps_rw if language == "rw" else self.next_steps_en


@dataclass(frozen=True)
class MatchProfile:
    goals: tuple[str, ...]
    participant_profiles: tuple[str, ...]
    skills: tuple[str, ...]
    support_types: tuple[str, ...]
    access_mode: str
    readiness: str


@dataclass(frozen=True)
class OpportunityMatch:
    opportunity: Opportunity
    score: int
    reasons: tuple[str, ...]
    cautions: tuple[str, ...]


def load_catalogue(path: str | Path) -> list[Opportunity]:
    """Load the reviewed static catalogue. It contains pathways, not live vacancies."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    sequence_fields = {
        "goals",
        "profiles",
        "skills",
        "support_types",
        "delivery",
        "eligibility_en",
        "eligibility_rw",
        "next_steps_en",
        "next_steps_rw",
    }
    opportunities: list[Opportunity] = []
    for raw in payload["opportunities"]:
        values = dict(raw)
        for field in sequence_fields:
            values[field] = tuple(values[field])
        opportunities.append(Opportunity(**values))
    return opportunities


def _names(values: Iterable[str]) -> str:
    return ", ".join(value.replace("_", " ") for value in values)


def _text(language: str, en: str, rw: str) -> str:
    return rw if language == "rw" else en


def rank_opportunities(
    opportunities: Iterable[Opportunity],
    profile: MatchProfile,
    household_answers: dict[str, Any] | None = None,
    language: str = "en",
) -> list[OpportunityMatch]:
    """Rank pathways using explainable fit rules; never infer programme eligibility."""
    household_answers = household_answers or {}
    selected_goals = set(profile.goals)
    selected_profiles = set(profile.participant_profiles)
    selected_skills = set(profile.skills)
    selected_support = set(profile.support_types)
    matches: list[OpportunityMatch] = []

    for opportunity in opportunities:
        reasons: list[str] = []
        cautions: list[str] = []
        score = 0.0

        goal_overlap = selected_goals.intersection(opportunity.goals)
        if goal_overlap:
            goal_points = 35 * len(goal_overlap) / max(1, len(selected_goals))
            score += goal_points
            reasons.append(
                _text(
                    language,
                    f"Matches your goal: {_names(sorted(goal_overlap))}.",
                    f"Bihuye n'intego yawe: {_names(sorted(goal_overlap))}.",
                )
            )

        profile_overlap = selected_profiles.intersection(opportunity.profiles)
        if profile_overlap:
            score += 20
            reasons.append(
                _text(
                    language,
                    f"Serves your selected profile: {_names(sorted(profile_overlap))}.",
                    f"Byakira icyiciro wahisemo: {_names(sorted(profile_overlap))}.",
                )
            )
        else:
            cautions.append(
                _text(
                    language,
                    "Your selected participant profile is not explicitly named by this pathway.",
                    "Icyiciro wahisemo ntikivugwa neza muri iyi gahunda.",
                )
            )

        if "any" in opportunity.skills:
            score += 15
            reasons.append(
                _text(
                    language,
                    "Open to a broad range of skills.",
                    "Yakira abantu bafite ubumenyi butandukanye.",
                )
            )
        else:
            skill_overlap = selected_skills.intersection(opportunity.skills)
            if skill_overlap:
                score += 15
                reasons.append(
                    _text(
                        language,
                        f"Matches your skills or sector: {_names(sorted(skill_overlap))}.",
                        f"Bihuye n'ubumenyi cyangwa urwego rwawe: {_names(sorted(skill_overlap))}.",
                    )
                )

        support_overlap = selected_support.intersection(opportunity.support_types)
        if support_overlap:
            score += 15 * len(support_overlap) / max(1, len(selected_support))
            reasons.append(
                _text(
                    language,
                    f"Offers requested support: {_names(sorted(support_overlap))}.",
                    f"Itanga ubufasha wasabye: {_names(sorted(support_overlap))}.",
                )
            )

        access_match = (
            profile.access_mode == "either"
            or profile.access_mode in opportunity.delivery
            or (profile.access_mode == "local" and "assisted" in opportunity.delivery)
        )
        if access_match:
            score += 10
            reasons.append(
                _text(
                    language,
                    "Its access route fits how you want to apply.",
                    "Uburyo bwo kuyigeraho buhuye n'uko ushaka gusaba.",
                )
            )
        else:
            cautions.append(
                _text(
                    language,
                    "This pathway is mainly online; arrange trusted digital assistance if needed.",
                    "Iyi gahunda ikoreshwa cyane kuri interineti; shakisha ubufasha bwizewe niba bukenewe.",
                )
            )

        context_match = False
        if opportunity.id == "rab_twigire_muhinzi" and household_answers.get("agricultural_activity") == 1:
            context_match = True
        elif opportunity.id == "loda_economic_inclusion" and (
            household_answers.get("agricultural_activity") == 1
            or household_answers.get("wage_employment") == 0
        ):
            context_match = True
        elif opportunity.id == "rdb_business_support" and household_answers.get("nonfarm_business") == 1:
            context_match = True
        if context_match:
            score += 5
            reasons.append(
                _text(
                    language,
                    "Also aligns with the household livelihood answers already provided.",
                    "Kandi bihuye n'ibisubizo by'imibereho y'urugo byatanzwe.",
                )
            )
        elif profile.readiness == "within_30_days":
            score += 3
            reasons.append(
                _text(
                    language,
                    "You indicated that you are ready to take action soon.",
                    "Wavuze ko witeguye gutangira vuba.",
                )
            )

        cautions.append(
            _text(
                language,
                "Fit does not confirm eligibility, selection, funding or a current opening.",
                "Guhuza ntibyemeza ko wujuje ibisabwa, ko watoranyijwe, ko uzahabwa inkunga cyangwa ko hari umwanya ufunguye.",
            )
        )
        matches.append(
            OpportunityMatch(
                opportunity=opportunity,
                score=min(100, round(score)),
                reasons=tuple(reasons),
                cautions=tuple(cautions),
            )
        )

    return sorted(matches, key=lambda item: (-item.score, item.opportunity.title(language)))
