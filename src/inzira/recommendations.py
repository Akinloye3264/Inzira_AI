from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Recommendation:
    theme: str
    title: str
    action: str
    reason: str


CONTENT = {
    "en": {
        "Agricultural resilience": (
            "Agricultural resilience",
            "Ask about extension services, livestock support, resilient inputs and cooperative market access.",
            "Agriculture or livestock is part of the household livelihood.",
        ),
        "Employment and enterprise": (
            "Employment and enterprise",
            "Explore job matching, vocational training, apprenticeships and suitable enterprise support.",
            "No wage employment or non-farm business was reported.",
        ),
        "Digital and financial inclusion": (
            "Digital and financial inclusion",
            "Offer safe digital-skills support and information about regulated mobile and financial services.",
            "Limited access to a mobile phone or recent internet use was reported.",
        ),
        "Health-insurance inclusion": (
            "Health-insurance inclusion",
            "Check current eligibility and support enrolment in an appropriate health-insurance programme.",
            "Some household members were reported without health insurance.",
        ),
        "Social protection and basic services": (
            "Social protection and basic services",
            "Offer a caseworker assessment covering social protection, housing and essential services.",
            "The answers indicate possible pressure from crowding, dependency or limited basic services.",
        ),
    },
    "rw": {
        "Agricultural resilience": (
            "Ubuhinzi n'ubworozi birambye",
            "Baza ku bujyanama mu buhinzi, ubufasha ku matungo, inyongeramusaruro n'amasoko y'amakoperative.",
            "Ubuhinzi cyangwa ubworozi biri mu mibereho y'urugo.",
        ),
        "Employment and enterprise": (
            "Akazi n'ubucuruzi",
            "Shakisha ubufasha mu kubona akazi, amahugurwa y'imyuga no guteza imbere ubucuruzi buboneye.",
            "Nta kazi k'umushahara cyangwa ubucuruzi butari ubuhinzi byatangajwe.",
        ),
        "Digital and financial inclusion": (
            "Ikoranabuhanga na serivisi z'imari",
            "Tanga ubufasha mu gukoresha ikoranabuhanga neza no kumenya serivisi z'imari zemewe.",
            "Hatangajwe uburyo buke bwo kubona telefoni cyangwa gukoresha interineti.",
        ),
        "Health-insurance inclusion": (
            "Ubwishingizi bw'ubuzima",
            "Suzuma uko ubwishingizi buhagaze kandi ufashe ababyemerewe kwiyandikisha.",
            "Hari abo mu rugo batangajwe ko badafite ubwishingizi bw'ubuzima.",
        ),
        "Social protection and basic services": (
            "Imibereho myiza na serivisi z'ibanze",
            "Saba umukozi ubishinzwe gusuzuma ubufasha bw'imibereho, imiturire na serivisi z'ibanze.",
            "Ibisubizo bigaragaza ko hashobora kuba ubucucike, abantu benshi batunzwe n'abandi cyangwa serivisi nke.",
        ),
    },
}


def _known_number(value: Any) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def suggest_support(
    answers: dict[str, Any], language: str, elevated_risk: bool
) -> list[Recommendation]:
    scores: dict[str, int] = {}

    def add(theme: str, points: int) -> None:
        scores[theme] = scores.get(theme, 0) + points

    if answers.get("agricultural_activity") == 1:
        add("Agricultural resilience", 3)
    if answers.get("livestock_range") == "none":
        add("Agricultural resilience", 1)

    if answers.get("wage_employment") == 0:
        add("Employment and enterprise", 2)
    if answers.get("nonfarm_business") == 0:
        add("Employment and enterprise", 2)

    if answers.get("mobile_phone") == 0:
        add("Digital and financial inclusion", 3)
    if answers.get("recent_internet_use") == 0:
        add("Digital and financial inclusion", 2)

    members = _known_number(answers.get("household_members"))
    insured = _known_number(answers.get("insured_members"))
    if members and insured is not None and insured < members:
        add("Health-insurance inclusion", 4)

    rooms = _known_number(answers.get("sleeping_rooms"))
    children = _known_number(answers.get("children_count"))
    elderly = _known_number(answers.get("elderly_count"))
    if members and rooms and members / rooms >= 3:
        add("Social protection and basic services", 3)
    if answers.get("electricity_access") == 0:
        add("Social protection and basic services", 2)
    if members and children is not None and elderly is not None:
        working = members - children - elderly
        if working > 0 and (children + elderly) / working >= 1:
            add("Social protection and basic services", 2)
    if elevated_risk:
        add("Social protection and basic services", 1)

    if not scores:
        add("Social protection and basic services", 1)

    localized = CONTENT.get(language, CONTENT["en"])
    recommendations: list[Recommendation] = []
    for theme, _ in sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:3]:
        title, action, reason = localized[theme]
        recommendations.append(
            Recommendation(theme=theme, title=title, action=action, reason=reason)
        )
    return recommendations
