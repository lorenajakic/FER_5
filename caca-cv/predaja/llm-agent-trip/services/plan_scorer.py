from __future__ import annotations

import math
import re
from statistics import pstdev
from typing import Any, Iterator, Optional

DEFAULT_WEIGHTS: dict[str, float] = {
    "travel_efficiency": 0.25,
    "preference_fit": 0.25,
    "day_balance": 0.15,
    "schedule_quality": 0.15,
    "participant_fairness": 0.10,
    "budget_fit": 0.10,
}

_TIME_BLOCK_KEYWORDS: dict[str, str] = {
    "morning": "morning",
    "ujutro": "morning",
    "jutro": "morning",
    "sunrise": "morning",
    "lunch": "lunch",
    "rucak": "lunch",
    "ručak": "lunch",
    "afternoon": "afternoon",
    "poslijepodne": "afternoon",
    "popodne": "afternoon",
    "dinner": "dinner",
    "vecera": "dinner",
    "večera": "dinner",
    "evening": "evening",
    "navecer": "evening",
    "naveče": "evening",
    "night": "evening",
    "sunset": "evening",
    "zalazak": "evening",
}


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _iter_activities(plan: dict[str, Any]) -> Iterator[tuple[dict, dict]]:
    for day in (plan or {}).get("days") or []:
        if not isinstance(day, dict):
            continue
        for act in day.get("activities") or []:
            if isinstance(act, dict):
                yield day, act


def _num(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return float(value)
    return None


def _desired_time_block(comments: list[dict[str, Any]]) -> Optional[str]:
    for c in comments:
        body = (c.get("body") or "").lower()
        for keyword, block in _TIME_BLOCK_KEYWORDS.items():
            if keyword in body:
                return block
    return None


def _parse_budget_cents(budget: Any) -> Optional[int]:
    if not budget:
        return None
    m = re.search(r"\d[\d.,]*", str(budget))
    if not m:
        return None
    digits = re.sub(r"[.,]", "", m.group(0))
    return int(digits) * 100 if digits else None


def _travel_efficiency(plan: dict[str, Any]) -> float:
    n_days = max(1, len((plan or {}).get("days") or []))
    total_travel = 0.0
    for _, act in _iter_activities(plan):
        v = _num(act.get("travel_duration_to_next_minutes"))
        if v is not None:
            total_travel += v
    per_day = total_travel / n_days
    return _clamp(1.0 - (per_day - 30.0) / 150.0)


def _day_load(day: dict[str, Any]) -> float:
    load = 0.0
    for act in day.get("activities") or []:
        if not isinstance(act, dict):
            continue
        for key in ("duration_minutes", "travel_duration_to_next_minutes"):
            v = _num(act.get(key))
            if v is not None:
                load += v
    return load


def _day_balance(plan: dict[str, Any], context: dict[str, Any] | None = None) -> float:
    ctx = context or {}
    edge_dates = {str(ctx.get("arrival_date") or ""), str(ctx.get("departure_date") or "")}
    edge_dates.discard("")
    loads = [
        _day_load(d)
        for d in (plan or {}).get("days") or []
        if isinstance(d, dict) and str(d.get("date") or "") not in edge_dates
    ]
    loads = [l for l in loads if l > 0]
    if len(loads) < 2:
        return 1.0
    mean = sum(loads) / len(loads)
    if mean <= 0:
        return 1.0
    return _clamp(1.0 - pstdev(loads) / mean)


def _parse_hhmm(value: Any) -> Optional[int]:
    if not isinstance(value, str):
        return None
    m = re.match(r"^\s*(\d{1,2}):(\d{2})\s*$", value)
    if not m:
        return None
    return int(m.group(1)) * 60 + int(m.group(2))


def _idle_minutes(day: dict[str, Any]) -> float:
    acts = [a for a in day.get("activities") or [] if isinstance(a, dict)]
    idle = 0.0
    for cur, nxt in zip(acts, acts[1:]):
        start = _parse_hhmm(cur.get("start_time"))
        nxt_start = _parse_hhmm(nxt.get("start_time"))
        if start is None or nxt_start is None:
            continue
        dur = _num(cur.get("duration_minutes")) or 0.0
        travel = _num(cur.get("travel_duration_to_next_minutes")) or 0.0
        gap = nxt_start - (start + dur + travel)
        if gap > 0:
            idle += gap
    return idle


def _detour_ratio(day: dict[str, Any]) -> Optional[float]:
    pts: list[tuple[float, float]] = []
    for act in day.get("activities") or []:
        if not isinstance(act, dict):
            continue
        lat, lon = _num(act.get("latitude")), _num(act.get("longitude"))
        if lat is not None and lon is not None:
            pts.append((lat, lon))
    if len(pts) < 3:
        return None
    lat0, lon0 = pts[0]
    klon = 111.32 * math.cos(math.radians(lat0))
    xy = [((lon - lon0) * klon, (lat - lat0) * 111.32) for lat, lon in pts]
    ordered = sum(math.dist(a, b) for a, b in zip(xy, xy[1:]))
    direct = math.dist(xy[0], xy[-1])
    if direct < 0.25:
        return None
    return ordered / direct


def _schedule_quality(plan: dict[str, Any]) -> float:
    days = [d for d in (plan or {}).get("days") or [] if isinstance(d, dict)]
    if not days:
        return 1.0

    excess_idle = sum(max(0.0, _idle_minutes(d) - 60.0) for d in days)
    idle_factor = _clamp(excess_idle / (len(days) * 150.0))

    ratios = [r for r in (_detour_ratio(d) for d in days) if r is not None]
    backtrack_factor = (
        _clamp((sum(ratios) / len(ratios) - 1.5) / 1.5) if ratios else 0.0
    )

    return _clamp(1.0 - 0.55 * idle_factor - 0.45 * backtrack_factor)


def _scheduled_places(plan: dict[str, Any]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for _, act in _iter_activities(plan):
        name = (act.get("place_name") or "").strip().lower()
        if name:
            out.setdefault(name, act)
    return out


def _preference_fit(plan: dict[str, Any], context: dict[str, Any]) -> float:
    scheduled = _scheduled_places(plan)
    saved = [str(n).strip().lower() for n in (context.get("mandatory_place_names") or []) if n]
    coverage = (
        sum(1 for n in saved if n in scheduled) / len(saved) if saved else 1.0
    )

    comments_by_place = context.get("comments_by_place") or {}
    timing_total = 0
    timing_ok = 0
    for place, comments in comments_by_place.items():
        wanted = _desired_time_block(comments or [])
        if not wanted:
            continue
        timing_total += 1
        act = scheduled.get((place or "").strip().lower())
        if act and (act.get("time_block") or "").lower() == wanted:
            timing_ok += 1

    if timing_total:
        return _clamp(0.5 * coverage + 0.5 * (timing_ok / timing_total))
    return _clamp(coverage)


def _participant_fairness(plan: dict[str, Any], context: dict[str, Any]) -> float:
    scheduled = set(_scheduled_places(plan))
    by_user: dict[str, set[str]] = {}
    for c in context.get("place_comments") or []:
        user = (c.get("user_name") or "").strip()
        place = (c.get("place_name") or "").strip().lower()
        if user and place:
            by_user.setdefault(user, set()).add(place)
    if not by_user:
        return 1.0
    per_user = [
        sum(1 for p in places if p in scheduled) / len(places)
        for places in by_user.values()
    ]
    return _clamp(0.5 * min(per_user) + 0.5 * (sum(per_user) / len(per_user)))


def _budget_fit(plan: dict[str, Any], context: dict[str, Any]) -> Optional[float]:
    prefs = context.get("plan_preferences") or {}
    budget_cents = _parse_budget_cents(prefs.get("budget"))
    if not budget_cents:
        return None
    total = 0.0
    for _, act in _iter_activities(plan):
        v = _num(act.get("cost_estimate_cents"))
        if v is not None:
            total += v
    if total <= budget_cents:
        return 1.0
    overshoot = (total - budget_cents) / budget_cents
    return _clamp(1.0 - overshoot)


def score_plan(
    *,
    candidate_id: str,
    plan_root: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    plan = (plan_root or {}).get("plan") or plan_root or {}

    metrics: dict[str, Optional[float]] = {
        "travel_efficiency": _travel_efficiency(plan),
        "preference_fit": _preference_fit(plan, context),
        "day_balance": _day_balance(plan, context),
        "schedule_quality": _schedule_quality(plan),
        "participant_fairness": _participant_fairness(plan, context),
        "budget_fit": _budget_fit(plan, context),
    }

    weights = {k: v for k, v in DEFAULT_WEIGHTS.items() if metrics[k] is not None}
    total_w = sum(weights.values()) or 1.0
    final = sum(metrics[k] * w for k, w in weights.items()) / total_w

    bf = metrics["budget_fit"]
    return {
        "candidate_id": candidate_id,
        "travel_efficiency_score": round(metrics["travel_efficiency"], 4),
        "preference_fit_score": round(metrics["preference_fit"], 4),
        "day_balance_score": round(metrics["day_balance"], 4),
        "schedule_quality_score": round(metrics["schedule_quality"], 4),
        "participant_fairness_score": round(metrics["participant_fairness"], 4),
        "budget_fit_score": round(bf, 4) if bf is not None else None,
        "final_score": round(final, 4),
        "weights": {k: round(w / total_w, 4) for k, w in weights.items()},
    }
