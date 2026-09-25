from __future__ import annotations

from datetime import date, datetime, timedelta
from models.state import TripPlannerState
from collections import defaultdict
from typing import Any, List

def collect_context(state: TripPlannerState) -> dict[str, Any]:
    trip = state.get("trip") or {}
    places = state.get("places") or []
    raw_comments = state.get("place_comments") or []
    current_plan = state.get("current_plan")
    history = state.get("conversation_history") or []
    user_message = (state.get("user_message") or "").strip()

    start = trip.get("start_date")
    end = trip.get("end_date")
    duration_days = _compute_duration_days(start, end)

    excluded_place_names = [p for p in (state.get("excluded_places") or []) if p]
    excluded_lower = {p.lower() for p in excluded_place_names}
    mandatory_place_names = [
        p.get("name") for p in places
        if p.get("name") and (p.get("name") or "").lower() not in excluded_lower
    ]
    normalized_comments = [_normalize_comment(c) for c in raw_comments if isinstance(c, dict)]
    comments_by_place = _group_comments_by_place(normalized_comments)

    departure_date, departure_cutoff = _compute_departure_info(trip)
    arrival_date, arrival_cutoff = _compute_arrival_info(trip)
    accommodation_details = _extract_accommodation_details(trip)

    return {
        "user_message": user_message,
        "conversation_history_tail": history[-20:],
        "trip": trip,
        "places": places,
        "place_comments": normalized_comments,
        "comments_by_place": comments_by_place,
        "mandatory_place_names": [n for n in mandatory_place_names if n],
        "excluded_place_names": excluded_place_names,
        "participant_count": trip.get("participant_count"),
        "duration_days": duration_days,
        "date_range": {"start_date": start, "end_date": end},
        "departure_date": departure_date,
        "departure_cutoff": departure_cutoff,
        "arrival_date": arrival_date,
        "arrival_cutoff": arrival_cutoff,
        "accommodation_details": accommodation_details,
        "snapshot_at": datetime.utcnow().isoformat() + "Z",
        "current_plan": current_plan,
    }

def _compute_duration_days(start: Any, end: Any) -> int | None:
    if not (start and end):
        return None
    try:
        s = date.fromisoformat(str(start))
        e = date.fromisoformat(str(end))
        return (e - s).days + 1
    except ValueError:
        return None
    
def _normalize_comment(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "place_name": (raw.get("place_name") or "").strip(),
        "user_name": (raw.get("user_name") or "").strip() or None,
        "body": (raw.get("body") or "").strip(),
        "created_at": raw.get("created_at"),
    }

def _group_comments_by_place(comments: List[dict[str, Any]]) -> dict[str, List[dict[str, Any]]]:
    out: dict[str, List[dict[str, Any]]] = defaultdict(list)
    for c in comments:
        key = (c.get("place_name") or "").strip()
        if not key or not (c.get("body") or "").strip():
            continue
        out[key].append(c)
    return dict(out)

def _compute_departure_info(trip: dict[str, Any]) -> tuple[str | None, str | None]:
    departure_at = trip.get("departure_at")
    if not departure_at:
        return None, None
    try:
        dep_dt = datetime.fromisoformat(str(departure_at).replace("Z", "+00:00"))
        dep_dt = dep_dt.replace(tzinfo=None)
        mode = trip.get("departure_transport_mode", "")
        buffer_before, _ = _transport_buffers(mode)
        cutoff_dt = dep_dt - timedelta(minutes=buffer_before)
        return dep_dt.date().isoformat(), f"{cutoff_dt.hour:02d}:{cutoff_dt.minute:02d}"
    except (ValueError, TypeError, AttributeError):
        return None, None
    
def _compute_arrival_info(trip: dict[str, Any]) -> tuple[str | None, str | None]:
    arrival_at = trip.get("arrival_at")
    if not arrival_at:
        return None, None
    try:
        arr_dt = datetime.fromisoformat(str(arrival_at).replace("Z", "+00:00"))
        arr_dt = arr_dt.replace(tzinfo=None)
        mode = trip.get("arrival_transport_mode", "")
        _, buffer_after = _transport_buffers(mode)
        cutoff_dt = arr_dt + timedelta(minutes=buffer_after)
        return arr_dt.date().isoformat(), f"{cutoff_dt.hour:02d}:{cutoff_dt.minute:02d}"
    except (ValueError, TypeError, AttributeError):
        return None, None

def _transport_buffers(mode: str) -> tuple[int, int]:
    m = (mode or "").lower()
    if m in ("flight", "plane", "fly", "air"):
        return 180, 120
    return 60, 60

def _extract_accommodation_details(trip: dict[str, Any]) -> str | None:
    details = (trip.get("accommodation_details") or "").strip()
    return details if details else None