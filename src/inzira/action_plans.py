from __future__ import annotations

from dataclasses import dataclass

from .recommendations import Recommendation


@dataclass(frozen=True)
class ServiceLink:
    label: str
    url: str


@dataclass(frozen=True)
class ActionPlan:
    theme: str
    title: str
    outcome: str
    service: str
    steps: tuple[str, ...]
    prepare: tuple[str, ...]
    links: tuple[ServiceLink, ...]


PLAN_CONTENT = {
    "en": {
        "Employment and enterprise": {
            "title": "Employment and skills pathway",
            "outcome": "Connect one work-ready household member to a suitable job, internship or skills route.",
            "service": "Kora Job Portal and Rwanda TVET Board",
            "steps": (
                "Choose the household member who wants work and write down their existing skills and preferred type of work.",
                "Create or update a free Kora profile, then search current jobs, internships and training opportunities.",
                "If practical training is needed, use the RTB Career Portal or ask the nearest TVET school about a suitable course before paying any provider.",
            ),
            "prepare": (
                "Education and skills history",
                "A telephone number or email for the official portal",
                "A CV if available; the app does not need a copy",
            ),
            "links": (
                ("Open Kora Job Portal", "https://jobportal.kora.rw/"),
                ("Open RTB Career Portal", "https://tvetcareerportal.rtb.gov.rw/"),
            ),
        },
        "Health-insurance inclusion": {
            "title": "Restore or complete Mutuelle coverage",
            "outcome": "Confirm the household record and help uninsured members begin or restore Community-Based Health Insurance coverage.",
            "service": "RSSB Community-Based Health Insurance through Irembo",
            "steps": (
                "Dial *909# to check the household contribution and member list, or open the Mutuelle service on Irembo.",
                "If members or the IMIBEREHO level are incorrect, visit the Cell office and ask the Socio-Economic Development Officer (SEDO) to correct the record before payment.",
                "Complete payment through an authorised channel, keep the confirmation message and verify that cover is active.",
            ),
            "prepare": (
                "National ID of the household head for the official service",
                "A valid telephone number or email",
                "Names of members missing from the official household record",
            ),
            "links": (
                ("Mutuelle application guide", "https://support.irembo.gov.rw/en/support/solutions/articles/47001199252-how-to-apply-and-pay-for-community-based-health-insurance-mutuelle-"),
                ("RSSB Mutuelle information", "https://www.beta.rssb.rw/schemes/cbhi"),
            ),
        },
        "Agricultural resilience": {
            "title": "Agricultural extension visit",
            "outcome": "Get a qualified local assessment before choosing inputs, livestock services or a cooperative route.",
            "service": "RAB Twigire Muhinzi extension network",
            "steps": (
                "Contact the local Farmer Promoter, FFS facilitator or Sector Agronomist and request an extension discussion.",
                "Explain the crop or livestock activity, the current constraint and what the household has already tried.",
                "Ask for the relevant demonstration, seasonal advice, livestock service, input channel or cooperative referral—and record the next visit date.",
            ),
            "prepare": (
                "Main crops or livestock kept",
                "Approximate land or herd size",
                "The most urgent production, disease, input or market problem",
            ),
            "links": (
                ("RAB extension services", "https://www.rab.gov.rw/agriculture-development/crop-innovation-tech-transfer"),
            ),
        },
        "Social protection and basic services": {
            "title": "Official household needs assessment",
            "outcome": "Have a local officer assess the household for an appropriate VUP, livelihood or complementary-service pathway.",
            "service": "Cell/Sector office and LODA social-protection programmes",
            "steps": (
                "Visit the Cell or Sector office and ask for the SEDO, Social Affairs Officer or para-social worker.",
                "Request a complete household needs and eligibility assessment, including applicable VUP and complementary services.",
                "Write down the officer's name, the documents or verification still needed, and the agreed follow-up date.",
            ),
            "prepare": (
                "Official household identification documents",
                "Current household composition and livelihood information",
                "A short list of the household's three most urgent needs",
            ),
            "links": (
                ("LODA social protection", "https://www.loda.gov.rw/social-protection"),
                ("VUP programme information", "https://www.loda.gov.rw/sptp"),
            ),
        },
        "Digital and financial inclusion": {
            "title": "Assisted digital-service access",
            "outcome": "Help the household use official digital services safely without exposing passwords, PINs or identity information.",
            "service": "Irembo agent, Cell office and regulated financial providers",
            "steps": (
                "Ask an authorised Irembo agent or Cell officer to identify the exact government service required.",
                "Use only the official service or regulated provider; confirm all fees before continuing.",
                "Never share a mobile-money PIN or one-time code, and keep the official receipt or confirmation message.",
            ),
            "prepare": (
                "The name of the service needed",
                "Required official identification kept outside this app",
                "A trusted telephone number where required",
            ),
            "links": (("Open IremboGov", "https://www.irembo.gov.rw/"),),
        },
        "Education and skills": {
            "title": "Skills assessment and training route",
            "outcome": "Match a household member's goal to a recognised training or prior-learning pathway.",
            "service": "Rwanda TVET Board",
            "steps": (
                "Write down the person's target occupation, existing practical skills and prior training.",
                "Use the RTB portal or contact a recognised TVET school to compare suitable programmes.",
                "Confirm accreditation, total cost, schedule and certification before enrolling or paying.",
            ),
            "prepare": (
                "Education and training history",
                "Preferred occupation",
                "Availability and travel constraints",
            ),
            "links": (("Open RTB Career Portal", "https://tvetcareerportal.rtb.gov.rw/"),),
        },
    },
    "rw": {
        "Employment and enterprise": {
            "title": "Inzira y'akazi n'ubumenyi",
            "outcome": "Guhuza umuntu wo mu rugo ushaka gukora n'akazi, kwimenyereza umwuga cyangwa amahugurwa bimukwiriye.",
            "service": "Kora Job Portal na Rwanda TVET Board",
            "steps": (
                "Hitamo umuntu wo mu rugo ushaka akazi, mwandike ubumenyi asanganywe n'akazi yifuza.",
                "Fungura cyangwa uvugurure konti ya Kora ku buntu, ushakishe akazi, kwimenyereza umwuga n'amahugurwa ahari.",
                "Niba akeneye umwuga ngiro, koresha RTB Career Portal cyangwa ubaze ishuri rya TVET riri hafi mbere yo kwishyura.",
            ),
            "prepare": ("Amashuri n'ubumenyi asanganywe", "Telefoni cyangwa imeyili", "CV niba ihari; ntuyishyire muri iyi porogaramu"),
            "links": (("Fungura Kora Job Portal", "https://jobportal.kora.rw/"), ("Fungura RTB Career Portal", "https://tvetcareerportal.rtb.gov.rw/")),
        },
        "Health-insurance inclusion": {
            "title": "Kuzuza cyangwa gusubizaho Mutuelle",
            "outcome": "Kugenzura amakuru y'urugo no gufasha abadafite ubwishingizi gutangira cyangwa gusubizaho Mutuelle.",
            "service": "Ubwisungane mu kwivuza bwa RSSB binyuze kuri Irembo",
            "steps": (
                "Kanda *909# urebe umusanzu n'abagize urugo, cyangwa ufungure serivisi ya Mutuelle kuri Irembo.",
                "Niba abagize urugo cyangwa urwego rwa IMIBEREHO bitari byo, jya ku biro by'Akagari ubaze SEDO abikosore mbere yo kwishyura.",
                "Ishyura unyuze mu nzira yemewe, ubike ubutumwa bwemeza ko wishyuye kandi urebe ko ubwishingizi bukora.",
            ),
            "prepare": ("Indangamuntu y'umukuru w'urugo ku rubuga rwemewe", "Telefoni cyangwa imeyili ikora", "Amazina y'ababura mu makuru y'urugo ya leta"),
            "links": (("Amabwiriza ya Mutuelle kuri Irembo", "https://support.irembo.gov.rw/en/support/solutions/articles/47001199252-how-to-apply-and-pay-for-community-based-health-insurance-mutuelle-"), ("Amakuru ya Mutuelle muri RSSB", "https://www.beta.rssb.rw/schemes/cbhi")),
        },
        "Agricultural resilience": {
            "title": "Ubufasha bw'umujyanama mu buhinzi",
            "outcome": "Kubona isuzuma ry'umujyanama wo hafi mbere yo guhitamo inyongeramusaruro, serivisi z'amatungo cyangwa koperative.",
            "service": "Urwego rwa RAB Twigire Muhinzi",
            "steps": (
                "Vugana n'Umufashamyumvire w'ubuhinzi, umuyobozi wa FFS cyangwa Agronome w'Umurenge usabe ubujyanama.",
                "Sobanura igihingwa cyangwa amatungo, ikibazo gihari n'ibyo urugo rwagerageje.",
                "Baza ku murima ntangarugero, inama z'igihembwe, serivisi z'amatungo, inyongeramusaruro cyangwa koperative; wandike itariki yo gukurikirana.",
            ),
            "prepare": ("Ibihingwa cyangwa amatungo by'ingenzi", "Ingano y'ubutaka cyangwa amatungo", "Ikibazo cyihutirwa ku musaruro, indwara, inyongeramusaruro cyangwa isoko"),
            "links": (("Serivisi z'ubujyanama za RAB", "https://www.rab.gov.rw/agriculture-development/crop-innovation-tech-transfer"),),
        },
        "Social protection and basic services": {
            "title": "Isuzuma ryemewe ry'ibikenewe mu rugo",
            "outcome": "Gusaba umukozi wo hafi gusuzuma niba urugo rwakwemererwa VUP, ubufasha bw'imibereho cyangwa izindi serivisi.",
            "service": "Ibiro by'Akagari/Umurenge na gahunda za LODA",
            "steps": (
                "Jya ku Kagari cyangwa Umurenge ubaze SEDO, umukozi ushinzwe imibereho myiza cyangwa para-social worker.",
                "Saba isuzuma rirambuye ry'urugo n'ibisabwa kugira ngo harebwe VUP cyangwa izindi serivisi ziboneye.",
                "Andika izina ry'umukozi, ibyangombwa bikibura n'itariki mwumvikanyeho yo gukurikirana.",
            ),
            "prepare": ("Ibyangombwa byemewe by'urugo", "Abagize urugo n'imibereho yabo", "Ibibazo bitatu byihutirwa urugo rushaka gukemura"),
            "links": (("LODA Social Protection", "https://www.loda.gov.rw/social-protection"), ("Amakuru ya VUP", "https://www.loda.gov.rw/sptp")),
        },
        "Digital and financial inclusion": {
            "title": "Gufashwa kubona serivisi z'ikoranabuhanga",
            "outcome": "Gufasha urugo gukoresha serivisi zemewe mu mutekano rutagaragaza PIN cyangwa amakuru bwite.",
            "service": "Umukozi wa Irembo, Akagari n'ibigo by'imari byemewe",
            "steps": ("Baza umukozi wa Irembo cyangwa w'Akagari serivisi nyayo ikenewe.", "Koresha urubuga rwemewe kandi ubanze wemeze amafaranga yose asabwa.", "Ntuzigere utanga PIN cyangwa kode yo kwemeza; bika inyemezabwishyu."),
            "prepare": ("Izina rya serivisi ikenewe", "Icyangombwa kibikwa hanze y'iyi porogaramu", "Telefoni yizewe niba isabwa"),
            "links": (("Fungura IremboGov", "https://www.irembo.gov.rw/"),),
        },
        "Education and skills": {
            "title": "Isuzuma ry'ubumenyi n'amahugurwa",
            "outcome": "Guhuza intego y'umuntu wo mu rugo n'amahugurwa yemewe cyangwa kwemeza ubumenyi asanganywe.",
            "service": "Rwanda TVET Board",
            "steps": ("Andika umwuga yifuza, ubumenyi ngiro asanganywe n'amahugurwa yabonye.", "Koresha RTB portal cyangwa ubaze ishuri rya TVET ryemewe.", "Emeza ko gahunda yemewe, igiciro cyose, igihe n'impamyabushobozi mbere yo kwishyura."),
            "prepare": ("Amashuri n'amahugurwa", "Umwuga yifuza", "Igihe afite n'urugendo ashobora gukora"),
            "links": (("Fungura RTB Career Portal", "https://tvetcareerportal.rtb.gov.rw/"),),
        },
    },
}


def build_action_plans(
    recommendations: list[Recommendation], language: str
) -> list[ActionPlan]:
    localized = PLAN_CONTENT.get(language, PLAN_CONTENT["en"])
    plans: list[ActionPlan] = []
    for recommendation in recommendations:
        content = localized[recommendation.theme]
        plans.append(
            ActionPlan(
                theme=recommendation.theme,
                title=content["title"],
                outcome=content["outcome"],
                service=content["service"],
                steps=tuple(content["steps"]),
                prepare=tuple(content["prepare"]),
                links=tuple(ServiceLink(*link) for link in content["links"]),
            )
        )
    return plans
