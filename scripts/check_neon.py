"""Verify Neon connectivity without printing credentials or record contents."""

import os
from pathlib import Path
import sys

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.inzira.case_store import NeonCaseStore


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")
    store = NeonCaseStore(database_url)
    print("Neon connection passed:", {"connected": store.health(), "referrals": len(store.list_records())})


if __name__ == "__main__":
    main()
