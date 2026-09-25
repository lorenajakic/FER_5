from __future__ import annotations

import json
import os
import time

from models.state import TripPlannerState
from ._shared import _log


def _dump_candidates(state: TripPlannerState, structured: dict) -> None:
    dump_dir = os.environ.get("TRIP_DEBUG_DUMP_DIR", "debug_dumps")
    os.makedirs(dump_dir, exist_ok=True)
    ts = int(time.time())
    path = os.path.join(dump_dir, f"candidates_{ts}.json")
    reports = {r["candidate_id"]: r for r in (state.get("validation_reports") or [])}
    payload = {
        "timestamp": ts,
        "selected_candidate_id": state.get("selected_candidate_id"),
        "candidates": [
            {
                "id": c["id"],
                "generation_rationale": c.get("generation_rationale"),
                "assumptions": c.get("assumptions"),
                "preliminary_confidence": c.get("preliminary_confidence"),
                "validation": reports.get(c["id"]),
                "plan": c["plan"],
            }
            for c in (state.get("candidates") or [])
        ],
        "score_report": state.get("score_report") or {},
        "final_structured": structured,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    _log(f"compose          DEBUG dump → {path}")
