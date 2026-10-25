from __future__ import annotations

import csv
import io
import secrets
from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Iterable


CASE_FIELDS = (
    "case_id",
    "created_date",
    "updated_date",
    "province",
    "household_size_band",
    "screening_route",
    "opportunity_id",
    "opportunity_title",
    "provider",
    "status",
    "outcome",
    "barrier",
    "next_followup",
)

ALLOWED_STATUSES = {
    "referred",
    "contacted",
    "application_started",
    "accepted",
    "not_eligible",
    "no_response",
    "closed",
}
ALLOWED_OUTCOMES = {
    "pending",
    "interview",
    "internship",
    "job",
    "training_started",
    "business_support",
    "agriculture_support",
    "not_placed",
}
ALLOWED_BARRIERS = {
    "none",
    "no_internet",
    "documents",
    "transport",
    "eligibility",
    "no_opening",
    "other",
}
POSITIVE_OUTCOMES = {
    "interview",
    "internship",
    "job",
    "training_started",
    "business_support",
    "agriculture_support",
}


@dataclass(frozen=True)
class CaseRecord:
    case_id: str
    created_date: str
    updated_date: str
    province: str
    household_size_band: str
    screening_route: str
    opportunity_id: str
    opportunity_title: str
    provider: str
    status: str
    outcome: str
    barrier: str
    next_followup: str


def create_case_id(today: date | None = None) -> str:
    today = today or date.today()
    return f"IA-{today:%Y%m%d}-{secrets.token_hex(2).upper()}"


def household_size_band(size: int | None) -> str:
    if size is None:
        return "unknown"
    if size <= 3:
        return "1-3"
    if size <= 5:
        return "4-5"
    return "6+"


def create_case_record(
    *,
    opportunity_id: str,
    opportunity_title: str,
    provider: str,
    province: str = "unknown",
    household_size: int | None = None,
    screening_route: str = "not_completed",
    next_followup: str = "",
    today: date | None = None,
) -> CaseRecord:
    today = today or date.today()
    stamp = today.isoformat()
    record = CaseRecord(
        case_id=create_case_id(today),
        created_date=stamp,
        updated_date=stamp,
        province=str(province or "unknown"),
        household_size_band=household_size_band(household_size),
        screening_route=screening_route,
        opportunity_id=opportunity_id,
        opportunity_title=opportunity_title,
        provider=provider,
        status="referred",
        outcome="pending",
        barrier="none",
        next_followup=next_followup,
    )
    validate_case_record(record)
    return record


def update_case_record(
    record: CaseRecord,
    *,
    status: str,
    outcome: str,
    barrier: str,
    next_followup: str,
    today: date | None = None,
) -> CaseRecord:
    values = asdict(record)
    values.update(
        status=status,
        outcome=outcome,
        barrier=barrier,
        next_followup=next_followup,
        updated_date=(today or date.today()).isoformat(),
    )
    updated = CaseRecord(**values)
    validate_case_record(updated)
    return updated


def validate_case_record(record: CaseRecord) -> None:
    if not record.case_id.startswith("IA-"):
        raise ValueError("Invalid anonymous case ID")
    if record.status not in ALLOWED_STATUSES:
        raise ValueError(f"Invalid status: {record.status}")
    if record.outcome not in ALLOWED_OUTCOMES:
        raise ValueError(f"Invalid outcome: {record.outcome}")
    if record.barrier not in ALLOWED_BARRIERS:
        raise ValueError(f"Invalid barrier: {record.barrier}")
    for value in (record.created_date, record.updated_date):
        datetime.strptime(value, "%Y-%m-%d")
    if record.next_followup:
        datetime.strptime(record.next_followup, "%Y-%m-%d")


def records_to_csv(records: Iterable[CaseRecord]) -> str:
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=CASE_FIELDS, lineterminator="\n")
    writer.writeheader()
    for record in records:
        validate_case_record(record)
        writer.writerow(asdict(record))
    return stream.getvalue()


def records_from_csv(payload: str) -> list[CaseRecord]:
    reader = csv.DictReader(io.StringIO(payload))
    if tuple(reader.fieldnames or ()) != CASE_FIELDS:
        raise ValueError("CSV columns do not match the Inzira case schema")
    records: list[CaseRecord] = []
    for row in reader:
        record = CaseRecord(**{field: row.get(field, "") for field in CASE_FIELDS})
        validate_case_record(record)
        records.append(record)
    return records


def impact_summary(
    records: Iterable[CaseRecord], today: date | None = None
) -> dict[str, int]:
    items = list(records)
    today = today or date.today()
    contacted = sum(item.status != "referred" for item in items)
    applications = sum(
        item.status in {"application_started", "accepted", "closed"} for item in items
    )
    positive = sum(item.outcome in POSITIVE_OUTCOMES for item in items)
    due = sum(
        bool(item.next_followup)
        and datetime.strptime(item.next_followup, "%Y-%m-%d").date() <= today
        and item.status not in {"closed", "accepted"}
        for item in items
    )
    return {
        "total": len(items),
        "contacted": contacted,
        "applications": applications,
        "positive_outcomes": positive,
        "followups_due": due,
    }


def count_by(records: Iterable[CaseRecord], field: str) -> dict[str, int]:
    if field not in CASE_FIELDS:
        raise ValueError(f"Unsupported grouping field: {field}")
    counts: dict[str, int] = {}
    for record in records:
        value = str(getattr(record, field))
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))
