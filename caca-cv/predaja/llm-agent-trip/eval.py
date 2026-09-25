#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from typing import Any

from dotenv import load_dotenv

load_dotenv(os.path.join("config", ".env"))
load_dotenv(".env", override=True)

from graph.build_graph import build_app
from graph.nodes._shared import default_chat_model, default_router_model
from models.state import TripPlannerState
from services.plan_validator import validate_candidate
from utils.context import collect_context

_agent = build_app()

def run(state: TripPlannerState) -> dict[str, Any]:
    cfg = {"configurable": {"thread_id": f"eval-{id(state)}"}}
    return _agent.invoke(state, config=cfg)


def activities_from_result(result: dict) -> list[dict]:
    plan = (result.get("structured_response") or {}).get("plan") or {}
    return [act for day in (plan.get("days") or []) for act in (day.get("activities") or [])]


def activities_by_day(result: dict) -> dict[int, list[str]]:
    plan = (result.get("structured_response") or {}).get("plan") or {}
    return {
        day["day_number"]: [a["place_name"] for a in (day.get("activities") or [])]
        for day in (plan.get("days") or [])
    }


def parse_hhmm(s: str) -> int:
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def _extract_plan_summary(result: dict) -> dict:
    sr = result.get("structured_response") or {}
    plan = sr.get("plan") or {}
    days = plan.get("days") or []

    days_summary = []
    for day in days:
        acts = day.get("activities") or []
        days_summary.append({
            "day_number": day.get("day_number"),
            "date": str(day.get("date") or ""),
            "activities": [
                {
                    "place_name": a.get("place_name"),
                    "start_time": a.get("start_time"),
                    "duration_minutes": a.get("duration_minutes"),
                    "time_block": a.get("time_block"),
                    "travel_method_to_next": a.get("travel_method_to_next"),
                    "travel_duration_to_next_minutes": a.get("travel_duration_to_next_minutes"),
                }
                for a in acts
            ],
        })

    constraint_report = sr.get("constraint_report") or {}
    score_report = sr.get("score_report") or {}

    return {
        "days": days_summary,
        "constraint_report": {
            "hard_pass": constraint_report.get("hard_pass"),
            "violations": constraint_report.get("violations") or [],
            "warnings": constraint_report.get("warnings") or [],
        },
        "score_report": score_report,
        "node_timings_ms": result.get("node_timings_ms") or {},
        "intent": result.get("intent"),
        "message_preview": (result.get("message") or "")[:300],
    }


BASE_TRIP = {
    "destination": "Paris, France",
    "start_date": "2026-04-15",
    "end_date": "2026-04-17",
    "participant_count": 2,
}

BASE_PLACES = [
    {"name": "Eiffel Tower",         "latitude": 48.8584, "longitude": 2.2945, "category": "landmark"},
    {"name": "Louvre Museum",         "latitude": 48.8606, "longitude": 2.3376, "category": "museum"},
    {"name": "Notre-Dame",            "latitude": 48.8530, "longitude": 2.3499, "category": "landmark"},
    {"name": "Montmartre",            "latitude": 48.8867, "longitude": 2.3431, "category": "landmark"},
    {"name": "Jardin du Luxembourg",  "latitude": 48.8462, "longitude": 2.3372, "category": "park"},
]

def scenario_mandatory_places() -> dict[str, Any]:
    result = run({
        "trip": BASE_TRIP,
        "places": BASE_PLACES,
        "place_comments": [],
        "current_plan": None,
        "conversation_history": [],
        "user_message": "Make a 3-day plan including all saved places.",
    })
    acts = activities_from_result(result)
    covered = {a["place_name"].lower() for a in acts}
    missing = [p["name"] for p in BASE_PLACES if p["name"].lower() not in covered]
    return {
        "pass": len(missing) == 0,
        "detail": f"Missing: {missing}" if missing else f"All {len(BASE_PLACES)} places covered",
        "result": result,
    }


def scenario_departure_cutoff() -> dict[str, Any]:
    trip = {**BASE_TRIP, "departure_at": "2026-04-17T14:00:00", "departure_transport_mode": "flight"}
    result = run({
        "trip": trip,
        "places": BASE_PLACES[:3],
        "place_comments": [],
        "current_plan": None,
        "conversation_history": [],
        "user_message": "Make a plan. We have a flight on the last day at 14:00.",
    })
    violations = []
    plan = (result.get("structured_response") or {}).get("plan") or {}
    for day in (plan.get("days") or []):
        if str(day.get("date")) != "2026-04-17":
            continue
        for act in (day.get("activities") or []):
            start = act.get("start_time")
            dur = act.get("duration_minutes") or 0
            if not start:
                continue
            end_min = parse_hhmm(start) + dur
            if end_min > parse_hhmm("11:00"):
                violations.append(f"{act['place_name']} ends {end_min // 60:02d}:{end_min % 60:02d}")
    return {
        "pass": len(violations) == 0,
        "detail": f"Cutoff violations: {violations}" if violations else "All activities end before 11:00",
        "result": result,
    }


def scenario_arrival_cutoff() -> dict[str, Any]:
    trip = {**BASE_TRIP, "arrival_at": "2026-04-15T12:00:00", "arrival_transport_mode": "flight"}
    result = run({
        "trip": trip,
        "places": BASE_PLACES[:3],
        "place_comments": [],
        "current_plan": None,
        "conversation_history": [],
        "user_message": "Make a plan. We arrive by flight at noon on the first day.",
    })
    violations = []
    plan = (result.get("structured_response") or {}).get("plan") or {}
    for day in (plan.get("days") or []):
        if str(day.get("date")) != "2026-04-15":
            continue
        for act in (day.get("activities") or []):
            start = act.get("start_time")
            if start and parse_hhmm(start) < parse_hhmm("14:00"):
                violations.append(f"{act['place_name']} starts at {start}")
    return {
        "pass": len(violations) == 0,
        "detail": f"Early start violations: {violations}" if violations else "All activities start after 14:00",
        "result": result,
    }


def scenario_refinement_precision() -> dict[str, Any]:
    current_plan = {
        "plan": {
            "days": [
                {"day_number": 1, "date": "2026-04-15", "activities": [
                    {"position": 1, "place_name": "Louvre Museum", "start_time": "09:00",
                     "duration_minutes": 120, "time_block": "morning",
                     "travel_method_to_next": "walk", "latitude": 48.8606, "longitude": 2.3376},
                    {"position": 2, "place_name": "Jardin du Luxembourg", "start_time": "12:00",
                     "duration_minutes": 60, "time_block": "lunch",
                     "travel_method_to_next": "none", "latitude": 48.8462, "longitude": 2.3372},
                ]},
                {"day_number": 2, "date": "2026-04-16", "activities": [
                    {"position": 1, "place_name": "Eiffel Tower", "start_time": "10:00",
                     "duration_minutes": 90, "time_block": "morning",
                     "travel_method_to_next": "none", "latitude": 48.8584, "longitude": 2.2945},
                ]},
                {"day_number": 3, "date": "2026-04-17", "activities": [
                    {"position": 1, "place_name": "Notre-Dame", "start_time": "10:00",
                     "duration_minutes": 90, "time_block": "morning",
                     "travel_method_to_next": "walk", "latitude": 48.8530, "longitude": 2.3499},
                    {"position": 2, "place_name": "Montmartre", "start_time": "14:00",
                     "duration_minutes": 120, "time_block": "afternoon",
                     "travel_method_to_next": "none", "latitude": 48.8867, "longitude": 2.3431},
                ]},
            ]
        }
    }
    result = run({
        "trip": BASE_TRIP,
        "places": BASE_PLACES,
        "place_comments": [],
        "current_plan": current_plan,
        "conversation_history": [],
        "user_message": "Move the Louvre Museum to day 2.",
    })
    by_day = activities_by_day(result)
    louvre_days  = [d for d, names in by_day.items() if any("louvre" in n.lower() for n in names)]
    notre_days   = [d for d, names in by_day.items() if any("notre" in n.lower() for n in names)]

    louvre_on_2  = louvre_days == [2]
    notre_on_3   = notre_days == [3]
    passed = louvre_on_2 and notre_on_3

    details = []
    if not louvre_on_2:
        details.append(f"Louvre on day(s) {louvre_days}, expected [2]")
    if not notre_on_3:
        details.append(f"Notre-Dame on day(s) {notre_days}, expected [3]")
    return {
        "pass": passed,
        "detail": "; ".join(details) if details else "Louvre moved to day 2, other places unchanged",
        "result": result,
    }


def scenario_repair_improvement() -> dict[str, Any]:
    broken_plan = {
        "plan": {
            "days": [
                {"day_number": 1, "date": "2026-04-15", "activities": [
                    {"position": 1, "place_name": "Eiffel Tower", "start_time": "09:00",
                     "duration_minutes": 180, "time_block": "morning",
                     "travel_method_to_next": "walk", "latitude": 48.8584, "longitude": 2.2945},
                    {"position": 2, "place_name": "Louvre Museum", "start_time": "09:30",
                     "duration_minutes": 120, "time_block": "morning",
                     "travel_method_to_next": "none", "latitude": 48.8606, "longitude": 2.3376},
                ]},
                {"day_number": 2, "date": "2026-04-16", "activities": [
                    {"position": 1, "place_name": "Notre-Dame", "start_time": "10:00",
                     "duration_minutes": 60, "time_block": "morning",
                     "travel_method_to_next": "walk", "latitude": 48.8530, "longitude": 2.3499},
                ]},
                {"day_number": 3, "date": "2026-04-17", "activities": [
                    {"position": 1, "place_name": "Montmartre", "start_time": "10:00",
                     "duration_minutes": 90, "time_block": "morning",
                     "travel_method_to_next": "none", "latitude": 48.8867, "longitude": 2.3431},
                    {"position": 2, "place_name": "Jardin du Luxembourg", "start_time": "12:00",
                     "duration_minutes": 60, "time_block": "afternoon",
                     "travel_method_to_next": "none", "latitude": 48.8462, "longitude": 2.3372},
                ]},
            ]
        }
    }

    ctx = collect_context({
        "trip": BASE_TRIP, "places": BASE_PLACES, "place_comments": [],
        "current_plan": None, "conversation_history": [], "user_message": "",
    })
    report_before = validate_candidate(candidate_id="broken", plan_root=broken_plan, context=ctx)
    violations_before = len([v for v in report_before["violations"] if v["severity"] == "hard"])

    result = run({
        "trip": BASE_TRIP,
        "places": BASE_PLACES,
        "place_comments": [],
        "current_plan": broken_plan,
        "conversation_history": [],
        "user_message": "Fix the schedule - there are timing conflicts.",
    })
    final_plan = {"plan": (result.get("structured_response") or {}).get("plan") or {}}
    report_after = validate_candidate(candidate_id="fixed", plan_root=final_plan, context=ctx)
    violations_after = len([v for v in report_after["violations"] if v["severity"] == "hard"])

    return {
        "pass": violations_after < violations_before,
        "detail": f"Hard violations: {violations_before} → {violations_after}",
        "result": result,
        "extra": {
            "violations_before": violations_before,
            "violations_after": violations_after,
            "report_before": report_before,
            "report_after": report_after,
        },
    }



SCENARIOS = [
    ("Mandatory places in plan",   scenario_mandatory_places),
    ("Departure cutoff respected", scenario_departure_cutoff),
    ("Arrival cutoff respected",   scenario_arrival_cutoff),
    ("Refinement precision",       scenario_refinement_precision),
    ("Repair improves plan",       scenario_repair_improvement),
]


def _safe_model_slug(model_id: str) -> str:
    return model_id.replace(":", "_").replace("/", "_").replace("-", "_")


def main() -> int:
    planner_model = default_chat_model()
    router_model = default_router_model()
    run_ts = int(time.time())
    run_dt = datetime.utcfromtimestamp(run_ts).strftime("%Y-%m-%d %H:%M UTC")

    print("\n" + "=" * 60)
    print("TRIP PLANNER - EVALUATION")
    print(f"  planner model : {planner_model}")
    print(f"  router model  : {router_model}")
    print(f"  started       : {run_dt}")
    print("=" * 60)

    log_entries: list[dict] = []
    results = []

    for name, fn in SCENARIOS:
        print(f"\n▶ {name} ...", flush=True)
        t0 = time.perf_counter()
        entry: dict[str, Any] = {"scenario": name, "pass": False}
        try:
            r = fn()
            elapsed = round((time.perf_counter() - t0) * 1000)
            status = "✓ PASS" if r["pass"] else "✗ FAIL"
            print(f"  {status}  {r['detail']}  ({elapsed} ms)")
            results.append(r["pass"])

            plan_summary = _extract_plan_summary(r["result"])

            entry.update({
                "pass": r["pass"],
                "detail": r["detail"],
                "elapsed_ms": elapsed,
                "plan_summary": plan_summary,
            })
            if "extra" in r:
                entry["extra"] = r["extra"]

            timings = plan_summary.get("node_timings_ms") or {}
            if timings:
                total = sum(timings.values())
                print(f"  {'Node timings':}")
                for node, ms in timings.items():
                    bar = "█" * int(ms / total * 20) if total else ""
                    print(f"    {node:<35} {ms:>7.0f} ms  {bar}")
                print(f"    {'TOTAL':<35} {total:>7.0f} ms")

            days = plan_summary.get("days") or []
            if days:
                print(f"  {'Plan':}")
                for day in days:
                    acts = day.get("activities") or []
                    names = " → ".join(
                        f"{a['place_name']} ({a['start_time']}, {a['duration_minutes']}min)"
                        for a in acts if a.get("place_name")
                    )
                    print(f"    Day {day['day_number']} ({day['date']}): {names or '(prazno)'}")

            cr = plan_summary.get("constraint_report") or {}
            violations = cr.get("violations") or []
            warnings = cr.get("warnings") or []
            if violations:
                print(f"  Violations ({len(violations)}):")
                for v in violations:
                    print(f"    [{v.get('severity','?').upper()}] [{v.get('code','?')}] {v.get('message','')}")
            if warnings:
                print(f"  Warnings ({len(warnings)}):")
                for w in warnings:
                    print(f"    [{w.get('code','?')}] {w.get('message','')}")

        except Exception as e:
            elapsed = round((time.perf_counter() - t0) * 1000)
            print(f"  ✗ ERROR  {e}  ({elapsed} ms)")
            results.append(False)
            entry.update({"pass": False, "detail": f"ERROR: {e}", "elapsed_ms": elapsed})

        log_entries.append(entry)

    passed = sum(results)
    total = len(results)
    print(f"\n{'=' * 60}")
    print(f"SCORE: {passed}/{total} passed")
    print("=" * 60 + "\n")

    log_dir = os.environ.get("EVAL_LOG_DIR", "eval_logs")
    os.makedirs(log_dir, exist_ok=True)
    slug = _safe_model_slug(planner_model)
    log_path = os.path.join(log_dir, f"{slug}_{run_ts}.json")
    log_payload = {
        "timestamp": run_ts,
        "datetime_utc": run_dt,
        "planner_model": planner_model,
        "router_model": router_model,
        "score": f"{passed}/{total}",
        "scenarios": log_entries,
    }
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log_payload, f, ensure_ascii=False, indent=2)
    print(f"Log saved → {log_path}\n")

    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
