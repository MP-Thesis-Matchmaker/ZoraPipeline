"""
Tracks the incremental harvest watermark. Committed to the repo alongside
output files so state survives between scheduled Action runs without
needing any external database.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from . import config


def load_state() -> dict:
    if not os.path.exists(config.STATE_PATH):
        return {"last_accessioned": None, "last_run_at": None, "last_total_publications": 0}
    with open(config.STATE_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_state(last_accessioned: str | None, total_publications: int) -> None:
    os.makedirs(config.DATA_DIR, exist_ok=True)
    state = {
        "last_accessioned": last_accessioned,
        "last_run_at": datetime.now(timezone.utc).isoformat(),
        "last_total_publications": total_publications,
    }
    with open(config.STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
        f.write("\n")
