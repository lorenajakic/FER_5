
from __future__ import annotations

import json
import math
import os
import urllib.error
import urllib.request
from typing import Any, Iterable


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def _coords_map(places: Iterable[dict[str, Any]]) -> dict[str, tuple[float, float]]:
    m: dict[str, tuple[float, float]] = {}
    for p in places:
        name = (p.get("name") or "").strip().lower()
        lat, lon = p.get("latitude"), p.get("longitude")
        if not name or lat is None or lon is None:
            continue
        try:
            m[name] = (float(lat), float(lon))
        except (TypeError, ValueError):
            continue
    return m


def suggest_mode_for_distance_km(dist_km: float) -> str:
    thr = float(os.environ.get("TRIP_LEG_TRANSIT_THRESHOLD_KM", "2.5"))
    if dist_km <= thr:
        return "walk"
    return "transit"


def estimate_travel_minutes(dist_km: float, mode: str) -> int:
    mode = (mode or "walk").lower()
    if mode == "walk":
        return max(5, int(dist_km * 14))
    if mode == "taxi":
        return max(8, int(dist_km * 3.5 + 4))
    return max(15, int(dist_km * 4.2 + 14))


def osrm_walk_duration_minutes(lon1: float, lat1: float, lon2: float, lat2: float) -> int | None:
    if os.environ.get("TRIP_USE_OSRM", "").strip().lower() not in ("1", "true", "yes"):
        return None
    url = f"https://router.project-osrm.org/route/v1/walking/{lon1},{lat1};{lon2},{lat2}?overview=false"
    try:
        with urllib.request.urlopen(url, timeout=8) as resp:
            data = json.loads(resp.read().decode())
        routes = data.get("routes") or []
        if not routes:
            return None
        sec = float(routes[0].get("duration", 0))
        return max(1, int(round(sec / 60.0)))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, OSError):
        return None


def annotate_leg_modes_and_times(
    days: list[dict[str, Any]],
    places: list[dict[str, Any]],
) -> None:
    cmap = _coords_map(places)
    for day in days:
        acts = day.get("activities") or []
        if not isinstance(acts, list):
            continue
        for i, act in enumerate(acts):
            if not isinstance(act, dict):
                continue
            nxt = acts[i + 1] if i + 1 < len(acts) else None
            if not nxt or not isinstance(nxt, dict):
                act["travel_method_to_next"] = "none"
                act["travel_duration_to_next_minutes"] = None
                continue
            a = (act.get("place_name") or "").strip().lower()
            b = (nxt.get("place_name") or "").strip().lower()
            if a not in cmap or b not in cmap:
                act.setdefault("travel_method_to_next", "walk")
                act.setdefault("travel_duration_to_next_minutes", 15)
                continue
            la, lo = cmap[a]
            lb, lob = cmap[b]
            dist = haversine_km(la, lo, lb, lob)
            mode = suggest_mode_for_distance_km(dist)
            mins = estimate_travel_minutes(dist, mode)
            if mode == "walk":
                osrm = osrm_walk_duration_minutes(lo, la, lob, lb)
                if osrm is not None:
                    mins = max(mins, osrm)
            act["travel_method_to_next"] = mode
            act["travel_duration_to_next_minutes"] = mins
