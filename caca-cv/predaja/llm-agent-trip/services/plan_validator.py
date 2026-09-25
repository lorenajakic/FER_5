from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from typing import Any, Iterable

from models.state import CandidateValidation, PlanViolation
from services.transit_routing import haversine_km


def _parse_hhmm(s: str | None) -> tuple[int, int] | None:
    if not s:
        return None
    s = str(s).strip()
    parts = s.replace(".", ":").split(":")
    if len(parts) < 2:
        return None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None


def _to_minutes(t: tuple[int, int]) -> int:
    return t[0] * 60 + t[1]


def _activity_end_minutes(start: tuple[int, int], duration_minutes: int | None) -> tuple[int, int] | None:
    if duration_minutes is None or duration_minutes < 0:
        return None
    base = datetime(2000, 1, 1, start[0], start[1])
    end = base + timedelta(minutes=duration_minutes)
    return end.hour, end.minute


def _place_coords_by_name(places: Iterable[dict[str, Any]]) -> dict[str, tuple[float, float]]:
    out: dict[str, tuple[float, float]] = {}
    for p in places:
        name = (p.get("name") or "").strip().lower()
        lat, lon = p.get("latitude"), p.get("longitude")
        if not name or lat is None or lon is None:
            continue
        try:
            out[name] = (float(lat), float(lon))
        except (TypeError, ValueError):
            continue
    return out


def validate_candidate(
    *,
    candidate_id: str,
    plan_root: dict[str, Any],
    context: dict[str, Any],
    max_walk_km_between_stops: float | None = None,
    max_day_active_minutes: int = 600,
    min_travel_buffer_minutes: int = 5,
) -> CandidateValidation:
    if max_walk_km_between_stops is None:
        max_walk_km_between_stops = float(os.environ.get("TRIP_VALIDATOR_MAX_WALK_KM", "3"))
    violations: list[PlanViolation] = []
    warnings: list[PlanViolation] = []

    trip = context.get("trip") or {}
    start_date = trip.get("start_date")
    end_date = trip.get("end_date")
    places = context.get("places") or []
    mandatory = [n.lower() for n in (context.get("mandatory_place_names") or []) if n]

    departure_cutoff = context.get("departure_cutoff")
    departure_date_str = context.get("departure_date")
    arrival_cutoff = context.get("arrival_cutoff")
    arrival_date_str = context.get("arrival_date")

    plan = (plan_root or {}).get("plan") or plan_root
    days = (plan or {}).get("days")
    if not isinstance(days, list) or not days:
        violations.append(
            {
                "code": "MISSING_PLAN_DAYS",
                "severity": "hard",
                "message": "Plan must include plan.days as a non-empty array.",
            }
        )
        return {"candidate_id": candidate_id, "hard_pass": False, "violations": violations, "warnings": warnings}

    allowed_dates: set[str] = set()
    if start_date and end_date:
        try:
            s = date.fromisoformat(str(start_date))
            e = date.fromisoformat(str(end_date))
            d = s
            while d <= e:
                allowed_dates.add(d.isoformat())
                d += timedelta(days=1)
        except ValueError:
            allowed_dates = set()

    coords = _place_coords_by_name(places)
    covered_mandatory: set[str] = set()

    for day in days:
        if not isinstance(day, dict):
            continue
        day_date = day.get("date")
        if allowed_dates and day_date and str(day_date) not in allowed_dates:
            violations.append(
                {
                    "code": "DATE_OUT_OF_RANGE",
                    "severity": "hard",
                    "message": f"Day date {day_date} is outside trip bounds {start_date}..{end_date}.",
                }
            )

        is_departure_day = bool(departure_date_str and day_date and str(day_date) == departure_date_str)
        is_arrival_day = bool(arrival_date_str and day_date and str(day_date) == arrival_date_str)

        activities = day.get("activities") or []
        if not isinstance(activities, list):
            continue

        prev_end: tuple[int, int] | None = None
        day_active = 0

        for i, act in enumerate(activities):
            if not isinstance(act, dict):
                continue
            pname = (act.get("place_name") or "").strip()
            if pname.lower() in mandatory:
                covered_mandatory.add(pname.lower())

            st = _parse_hhmm(act.get("start_time"))
            dur = act.get("duration_minutes")
            if isinstance(dur, int):
                dur_int: int | None = dur
            elif isinstance(dur, str) and dur.isdigit():
                dur_int = int(dur)
            else:
                dur_int = None

            if st and prev_end:
                gap = (
                    datetime(2000, 1, 1, st[0], st[1]) - datetime(2000, 1, 1, prev_end[0], prev_end[1])
                ).total_seconds() / 60.0
                if gap < min_travel_buffer_minutes:
                    violations.append(
                        {
                            "code": "TIME_OVERLAP",
                            "severity": "hard",
                            "message": f"Activity '{pname}' overlaps or is too tight vs previous (gap {gap:.0f} min).",
                        }
                    )

            end_t: tuple[int, int] | None = None
            if st and dur_int is not None:
                end_t = _activity_end_minutes(st, dur_int)
                if end_t:
                    prev_end = end_t
                day_active += dur_int
            elif st:
                prev_end = st

            if is_departure_day and departure_cutoff:
                dep_cut = _parse_hhmm(departure_cutoff)
                if end_t and dep_cut and _to_minutes(end_t) > _to_minutes(dep_cut):
                    violations.append(
                        {
                            "code": "DEPARTURE_CONFLICT",
                            "severity": "hard",
                            "message": (
                                f"Activity '{pname}' ends at {end_t[0]:02d}:{end_t[1]:02d}, "
                                f"after departure cutoff {departure_cutoff}."
                            ),
                        }
                    )

            if is_arrival_day and arrival_cutoff:
                arr_cut = _parse_hhmm(arrival_cutoff)
                if st and arr_cut and _to_minutes(st) < _to_minutes(arr_cut):
                    violations.append(
                        {
                            "code": "ARRIVAL_CONFLICT",
                            "severity": "hard",
                            "message": (
                                f"Activity '{pname}' starts at {act.get('start_time')}, "
                                f"before arrival cutoff {arrival_cutoff}."
                            ),
                        }
                    )

            nxt = activities[i + 1] if i + 1 < len(activities) else None
            if nxt and isinstance(nxt, dict):
                a, b = pname.lower(), (nxt.get("place_name") or "").strip().lower()
                if a in coords and b in coords:
                    dist = haversine_km(coords[a][0], coords[a][1], coords[b][0], coords[b][1])
                    method = (act.get("travel_method_to_next") or "walk").lower()
                    if method == "walk" and dist > max_walk_km_between_stops:
                        violations.append(
                            {
                                "code": "TRAVEL_INFEASIBLE",
                                "severity": "hard",
                                "message": f"Walk between '{pname}' and '{nxt.get('place_name')}' is ~{dist:.1f} km (> {max_walk_km_between_stops} km).",
                            }
                        )
                    elif method in ("transit", "taxi") and dist > 45:
                        warnings.append(
                            {
                                "code": "LONG_TRANSIT_LEG",
                                "severity": "soft",
                                "message": f"Long {method} leg ~{dist:.0f} km '{pname}' -> '{nxt.get('place_name')}' - verify connections.",
                            }
                        )

        if day_active > max_day_active_minutes:
            warnings.append(
                {
                    "code": "HIGH_DAY_LOAD",
                    "severity": "soft",
                    "message": f"Day {day.get('day_number')} active time ~{day_active} min exceeds soft threshold {max_day_active_minutes}.",
                }
            )

    missing = [m for m in mandatory if m not in covered_mandatory]
    for m in missing:
        violations.append(
            {
                "code": "MANDATORY_PLACE_MISSING",
                "severity": "hard",
                "message": f"Mandatory place '{m}' never scheduled.",
            }
        )

    hard_pass = not any(v["severity"] == "hard" for v in violations)
    return {"candidate_id": candidate_id, "hard_pass": hard_pass, "violations": violations, "warnings": warnings}
