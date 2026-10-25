from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Iterable

from src.inzira.impact_tracking import CASE_FIELDS, CaseRecord, validate_case_record


class CaseStoreError(RuntimeError):
    """Raised when the persistent case store cannot complete an operation."""


def _record_from_document(document: dict[str, Any]) -> CaseRecord:
    record = CaseRecord(**{field: str(document.get(field, "")) for field in CASE_FIELDS})
    validate_case_record(record)
    return record


class MongoCaseStore:
    """Persistent anonymous referral storage with a minimal admin audit trail."""

    def __init__(self, uri: str, database: str) -> None:
        try:
            from pymongo import ASCENDING, DESCENDING, MongoClient
        except ImportError as exc:  # pragma: no cover - deployment dependency guard
            raise CaseStoreError("PyMongo is not installed") from exc

        try:
            self.client = MongoClient(
                uri,
                appname="inzira-ai",
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=8000,
                retryWrites=True,
            )
            self.client.admin.command("ping")
            db = self.client[database]
            self.cases = db["referrals"]
            self.audit = db["admin_audit"]
            self.cases.create_index("case_id", unique=True)
            self.cases.create_index(
                [("status", ASCENDING), ("next_followup", ASCENDING)]
            )
            self.audit.create_index([("created_at", DESCENDING)])
        except Exception as exc:
            raise CaseStoreError(f"MongoDB connection failed: {exc}") from exc

    def _audit(self, *, actor: str, action: str, case_id: str = "") -> None:
        self.audit.insert_one(
            {
                "actor": actor.lower().strip(),
                "action": action,
                "case_id": case_id,
                "created_at": datetime.now(timezone.utc),
            }
        )

    def list_records(self) -> list[CaseRecord]:
        try:
            documents = self.cases.find({}, {"_id": 0}).sort("created_date", -1)
            return [_record_from_document(document) for document in documents]
        except Exception as exc:
            raise CaseStoreError(f"Could not load referrals: {exc}") from exc

    def create_record(self, record: CaseRecord, *, actor: str) -> None:
        validate_case_record(record)
        try:
            self.cases.insert_one(asdict(record))
            self._audit(actor=actor, action="referral_created", case_id=record.case_id)
        except Exception as exc:
            raise CaseStoreError(f"Could not create referral: {exc}") from exc

    def update_record(self, record: CaseRecord, *, actor: str) -> None:
        validate_case_record(record)
        try:
            result = self.cases.replace_one(
                {"case_id": record.case_id}, asdict(record), upsert=False
            )
            if result.matched_count != 1:
                raise CaseStoreError("Referral was not found")
            self._audit(actor=actor, action="referral_updated", case_id=record.case_id)
        except CaseStoreError:
            raise
        except Exception as exc:
            raise CaseStoreError(f"Could not update referral: {exc}") from exc

    def import_records(
        self, records: Iterable[CaseRecord], *, actor: str
    ) -> int:
        items = list(records)
        try:
            for record in items:
                validate_case_record(record)
                self.cases.replace_one(
                    {"case_id": record.case_id}, asdict(record), upsert=True
                )
            self._audit(actor=actor, action=f"referrals_imported:{len(items)}")
            return len(items)
        except Exception as exc:
            raise CaseStoreError(f"Could not import referrals: {exc}") from exc

    def recent_audit(self, limit: int = 30) -> list[dict[str, str]]:
        try:
            documents = self.audit.find({}, {"_id": 0}).sort("created_at", -1).limit(limit)
            return [
                {
                    "actor": str(item.get("actor", "")),
                    "action": str(item.get("action", "")),
                    "case_id": str(item.get("case_id", "")),
                    "created_at": item.get("created_at").isoformat()
                    if item.get("created_at")
                    else "",
                }
                for item in documents
            ]
        except Exception as exc:
            raise CaseStoreError(f"Could not load audit activity: {exc}") from exc

    def health(self) -> bool:
        try:
            self.client.admin.command("ping")
            return True
        except Exception:
            return False
