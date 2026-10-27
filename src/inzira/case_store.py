from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime
from typing import Any, Iterable

from src.inzira.impact_tracking import CASE_FIELDS, CaseRecord, validate_case_record


class CaseStoreError(RuntimeError):
    """Raised when the persistent case store cannot complete an operation."""


def _iso_date(value: Any) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value or "")


def _record_from_row(row: dict[str, Any]) -> CaseRecord:
    values = {field: str(row.get(field, "") or "") for field in CASE_FIELDS}
    for field in ("created_date", "updated_date", "next_followup"):
        values[field] = _iso_date(row.get(field))
    record = CaseRecord(**values)
    validate_case_record(record)
    return record


class NeonCaseStore:
    """PostgreSQL-backed anonymous referral storage with an admin audit trail."""

    def __init__(self, database_url: str) -> None:
        if not database_url.strip():
            raise CaseStoreError("Neon database URL is missing")
        self.database_url = database_url.strip()
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:  # pragma: no cover
            raise CaseStoreError("Psycopg is not installed") from exc
        self._psycopg = psycopg
        self._dict_row = dict_row
        self._initialize_schema()

    def _connect(self):
        return self._psycopg.connect(
            self.database_url,
            connect_timeout=8,
            row_factory=self._dict_row,
        )

    def _initialize_schema(self) -> None:
        statements = (
            """
            CREATE TABLE IF NOT EXISTS referrals (
                case_id TEXT PRIMARY KEY,
                created_date DATE NOT NULL,
                updated_date DATE NOT NULL,
                province TEXT NOT NULL,
                household_size_band TEXT NOT NULL,
                screening_route TEXT NOT NULL,
                opportunity_id TEXT NOT NULL,
                opportunity_title TEXT NOT NULL,
                provider TEXT NOT NULL,
                status TEXT NOT NULL,
                outcome TEXT NOT NULL,
                barrier TEXT NOT NULL,
                next_followup DATE NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS admin_audit (
                id BIGSERIAL PRIMARY KEY,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                case_id TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,
            "CREATE INDEX IF NOT EXISTS referrals_status_followup_idx ON referrals(status, next_followup)",
            "CREATE INDEX IF NOT EXISTS admin_audit_created_idx ON admin_audit(created_at DESC)",
        )
        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    for statement in statements:
                        cursor.execute(statement)
        except Exception as exc:
            raise CaseStoreError(f"Neon schema initialization failed: {exc}") from exc

    @staticmethod
    def _record_values(record: CaseRecord) -> tuple[Any, ...]:
        values = asdict(record)
        return tuple(
            (values[field] or None) if field == "next_followup" else values[field]
            for field in CASE_FIELDS
        )

    @staticmethod
    def _audit(cursor: Any, *, actor: str, action: str, case_id: str = "") -> None:
        cursor.execute(
            "INSERT INTO admin_audit(actor, action, case_id) VALUES (%s, %s, %s)",
            (actor.lower().strip(), action, case_id),
        )

    def list_records(self) -> list[CaseRecord]:
        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT * FROM referrals ORDER BY created_date DESC, case_id DESC")
                    return [_record_from_row(dict(row)) for row in cursor.fetchall()]
        except Exception as exc:
            raise CaseStoreError(f"Could not load referrals: {exc}") from exc

    def create_record(self, record: CaseRecord, *, actor: str) -> None:
        validate_case_record(record)
        placeholders = ", ".join(["%s"] * len(CASE_FIELDS))
        fields = ", ".join(CASE_FIELDS)
        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"INSERT INTO referrals ({fields}) VALUES ({placeholders})",
                        self._record_values(record),
                    )
                    self._audit(cursor, actor=actor, action="referral_created", case_id=record.case_id)
        except Exception as exc:
            raise CaseStoreError(f"Could not create referral: {exc}") from exc

    def update_record(self, record: CaseRecord, *, actor: str) -> None:
        validate_case_record(record)
        update_fields = [field for field in CASE_FIELDS if field != "case_id"]
        assignments = ", ".join(f"{field} = %s" for field in update_fields)
        values = asdict(record)
        parameters = [
            (values[field] or None) if field == "next_followup" else values[field]
            for field in update_fields
        ]
        parameters.append(record.case_id)
        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"UPDATE referrals SET {assignments} WHERE case_id = %s",
                        tuple(parameters),
                    )
                    if cursor.rowcount != 1:
                        raise CaseStoreError("Referral was not found")
                    self._audit(cursor, actor=actor, action="referral_updated", case_id=record.case_id)
        except CaseStoreError:
            raise
        except Exception as exc:
            raise CaseStoreError(f"Could not update referral: {exc}") from exc

    def import_records(self, records: Iterable[CaseRecord], *, actor: str) -> int:
        items = list(records)
        fields = ", ".join(CASE_FIELDS)
        placeholders = ", ".join(["%s"] * len(CASE_FIELDS))
        updates = ", ".join(
            f"{field} = EXCLUDED.{field}" for field in CASE_FIELDS if field != "case_id"
        )
        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    for record in items:
                        validate_case_record(record)
                        cursor.execute(
                            f"INSERT INTO referrals ({fields}) VALUES ({placeholders}) "
                            f"ON CONFLICT (case_id) DO UPDATE SET {updates}",
                            self._record_values(record),
                        )
                    self._audit(cursor, actor=actor, action=f"referrals_imported:{len(items)}")
            return len(items)
        except Exception as exc:
            raise CaseStoreError(f"Could not import referrals: {exc}") from exc

    def recent_audit(self, limit: int = 30) -> list[dict[str, str]]:
        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT actor, action, case_id, created_at FROM admin_audit "
                        "ORDER BY created_at DESC LIMIT %s",
                        (max(1, min(limit, 200)),),
                    )
                    return [
                        {
                            "actor": str(row["actor"]),
                            "action": str(row["action"]),
                            "case_id": str(row["case_id"]),
                            "created_at": row["created_at"].isoformat(),
                        }
                        for row in cursor.fetchall()
                    ]
        except Exception as exc:
            raise CaseStoreError(f"Could not load audit activity: {exc}") from exc

    def health(self) -> bool:
        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    return cursor.fetchone() is not None
        except Exception:
            return False
