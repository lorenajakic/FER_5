from __future__ import annotations

import json
import os
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from langgraph.graph import END
from langgraph.types import Command
from models.shemas import AccommodationGeocode, GeneratedPlan, PlanPreferences, TripPlanCore
from models.state import CandidateRecord, CandidateValidation, TripPlannerState
from langchain_core.output_parsers import PydanticOutputParser
from services.plan_validator import validate_candidate
from services.plan_scorer import score_plan
from ._shared import L, _bump_timing, _ctx_json, _log, _model_id, _now_ms, lang_directive, llm, llm_fast
from ._plan_utils import _backfill_coords, _format_trip_overview
from ._debug import _dump_candidates

def _extract_plan_preferences(ctx: dict[str, Any], previous: dict | None) -> PlanPreferences:
    history = ctx.get("conversation_history_tail") or []
    history_text = "\n".join(f"{m['role']}: {m['content']}" for m in history[-8:])
    prompt = f"""From the conversation, extract trip itinerary preferences if mentioned.

Conversation:
{history_text}
user: {ctx.get('user_message', '')}

Extract:
- pace: relaxed / moderate / packed
- interests: special interests or things to prioritise or avoid
- budget: rough per-person budget for activities and tickets

has_enough_info: true if the user gave at least one preference, OR clearly said they
have no preference / just want it planned (e.g. "go ahead", "whatever you think")."""
    if previous:
        prompt += f"\n\nAlready collected earlier: {previous}"
    try:
        return llm_fast.with_structured_output(PlanPreferences).invoke(prompt)
    except Exception:
        return PlanPreferences(has_enough_info=True)


_PHOTON_URL = "https://photon.komoot.io/api"


def _geocode_accommodation(
    address: str, destination: str = "", extra_hint: str | None = None
) -> AccommodationGeocode:
    from urllib.parse import urlencode

    query = ", ".join(p.strip() for p in (address, extra_hint, destination) if p and p.strip())
    url = f"{_PHOTON_URL}?{urlencode({'q': query, 'limit': 1})}"
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "llm-agent-trip/1.0 (accommodation geocoder)"}
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
    except Exception as e:
        _log(f"Photon geocode error: {e}")
        return AccommodationGeocode(can_locate=False)

    features = data.get("features") or []
    if not features:
        _log(f"Photon: no match for {query!r}")
        return AccommodationGeocode(can_locate=False)

    coords = (features[0].get("geometry") or {}).get("coordinates") or []
    if len(coords) < 2:
        return AccommodationGeocode(can_locate=False)
    try:
        lon, lat = float(coords[0]), float(coords[1])
    except (TypeError, ValueError):
        return AccommodationGeocode(can_locate=False)
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return AccommodationGeocode(can_locate=False)
    return AccommodationGeocode(latitude=lat, longitude=lon, confidence=0.9, can_locate=True)


def _coords_from_maps_url(text: str) -> tuple[float, float] | None:
    m = re.search(r'https?://\S+', text or "")
    if not m:
        return None
    url = m.group(0).rstrip(').,>"\'')

    final_url = url
    if any(h in url for h in ("maps.app.goo.gl", "goo.gl/maps", "g.co/")):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                final_url = r.geturl()
        except Exception as e:
            _log(f"maps URL resolve error: {e}")
            return None

    for pat in (
        r'@(-?\d+\.\d+),(-?\d+\.\d+)',
        r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)',
        r'[?&](?:q|ll|center|destination|daddr)=(-?\d+\.\d+),(-?\d+\.\d+)',
    ):
        mm = re.search(pat, final_url)
        if mm:
            try:
                lat, lon = float(mm.group(1)), float(mm.group(2))
            except ValueError:
                continue
            if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
                _log(f"maps URL resolved → ({lat:.5f}, {lon:.5f})")
                return lat, lon

    _log("maps URL resolved but no coordinates found in final URL")
    return None


def _resolve_accommodation(
    state: TripPlannerState,
    ctx: dict[str, Any],
    trip: dict[str, Any],
    pending_slots: dict[str, Any],
    real_intent: str,
    node_name: str,
    t0: float,
) -> tuple[Command | None, dict[str, Any], dict[str, Any], dict[str, Any] | None]:
    accom_addr = (trip.get("accommodation_address") or "").strip()
    accom_lat = trip.get("accommodation_latitude")
    accom_lon = trip.get("accommodation_longitude")
    _accom_asked = bool(pending_slots.get("_accommodation_asked"))
    user_msg = (ctx.get("user_message") or "").strip()
    accom_geo_update: dict[str, Any] | None = None

    saved_geo = state.get("accommodation_geo") or {}
    if (
        accom_addr and not (accom_lat and accom_lon)
        and saved_geo.get("address") == accom_addr
        and saved_geo.get("latitude") and saved_geo.get("longitude")
    ):
        accom_lat, accom_lon = saved_geo["latitude"], saved_geo["longitude"]
        ctx = {**ctx, "trip": {**trip, "accommodation_latitude": accom_lat, "accommodation_longitude": accom_lon}}
        trip = ctx["trip"]
        _log(f"{node_name}        accommodation reused from saved geo ({accom_lat:.4f}, {accom_lon:.4f})")

    if accom_addr and not (accom_lat and accom_lon) and "skip" not in user_msg.lower():
        link_coords = _coords_from_maps_url(user_msg) if _accom_asked else None
        if link_coords:
            accom_lat, accom_lon = link_coords
            ctx = {**ctx, "trip": {**trip, "accommodation_latitude": accom_lat, "accommodation_longitude": accom_lon}}
            trip = ctx["trip"]
            accom_geo_update = {"address": accom_addr, "latitude": accom_lat, "longitude": accom_lon}
            _log(f"{node_name}        accommodation from maps link ({accom_lat:.4f}, {accom_lon:.4f})")
        else:
            destination = (trip.get("destination") or "").strip()
            geo = _geocode_accommodation(
                accom_addr, destination=destination, extra_hint=user_msg if _accom_asked else None
            )
            if geo.can_locate and geo.latitude and geo.longitude:
                ctx = {**ctx, "trip": {**trip, "accommodation_latitude": geo.latitude, "accommodation_longitude": geo.longitude}}
                trip = ctx["trip"]
                accom_geo_update = {"address": accom_addr, "latitude": geo.latitude, "longitude": geo.longitude}
                _log(f"{node_name}        accommodation geocoded ({geo.latitude:.4f}, {geo.longitude:.4f}, conf={geo.confidence:.2f})")
            elif not _accom_asked:
                lang = state.get("user_language") or "en"
                message = L(lang,
                    f"I'd like to pin your accommodation on the map, but I couldn't reliably locate "
                    f"**\"{accom_addr}\"**. Could you give me a bit more detail - the hotel name, "
                    f"postal code, or a nearby landmark?\n\n"
                    f"(Type **\"skip\"** and I'll plan without the accommodation pin.)",
                    f"Želim označiti vaš smještaj na karti, ali nisam mogao pouzdano locirati "
                    f"**\"{accom_addr}\"**. Možete li dati malo više detalja - naziv hotela, "
                    f"poštanski broj ili obližnju znamenitost?\n\n"
                    f"(Upišite **\"skip\"** i isplanirat ću bez oznake smještaja.)")
                _log(f"{node_name}        → asking for accommodation location (geocoding failed)")
                interrupt = Command(
                    update={
                        "intent": real_intent,
                        "pending_intent": real_intent,
                        "pending_slots": {
                            **pending_slots,
                            "_accommodation_asked": True,
                            "_original_request": pending_slots.get("_original_request") or user_msg,
                        },
                        "message": message,
                        "structured_response": {"message": message},
                        "node_timings_ms": _bump_timing(state, node_name, t0),
                    },
                    goto=END,
                )
                return interrupt, ctx, trip, accom_geo_update

    return None, ctx, trip, accom_geo_update


def plan_node(state: TripPlannerState) -> Command:
    t0 = _now_ms()
    ctx = state.get("collected_context") or {}
    trip = ctx.get("trip") or {}
    pending_slots = state.get("pending_slots") or {}
    real_intent = state.get("intent") or "plan_itinerary"
    lang = state.get("user_language") or "en"
    plan_prefs = {
        "pace": pending_slots.get("pace", ""),
        "interests": pending_slots.get("interests", ""),
        "budget": pending_slots.get("budget", ""),
    }

    interrupt, ctx, trip, accom_geo_update = _resolve_accommodation(
        state, ctx, trip, pending_slots, real_intent, "plan_node", t0
    )
    if interrupt is not None:
        return interrupt
    
    accom_addr = (trip.get("accommodation_address") or "").strip()
    if not accom_addr and not pending_slots.get("_accommodation_prompted"):
        message = L(lang,
            "Quick heads-up: you haven't set accommodation for this trip yet. "
            "If you add it in the app and let me know when it's ready, I'll "
            "anchor each day around where you're staying, so the plan comes out "
            "noticeably tidier.\n\nNo worries if you'd rather not - just say "
            "\"plan anyway\" and I'll go ahead without it.",
            "Mala napomena: za ovo putovanje još nisi postavila smještaj. "
            "Ako ga dodaš u aplikaciji i javiš mi kad je spremno, posložit ću "
            "svaki dan oko mjesta gdje odsjedaš, pa plan ispadne osjetno "
            "uredniji.\n\nNema frke ako ne želiš - samo reci \"isplaniraj "
            "svejedno\" pa krećem bez njega.")
        _log("plan_node        → nudging user to set accommodation (one-time)")
        return Command(
            update={
                "intent": real_intent,
                "pending_intent": real_intent,
                "pending_slots": {**pending_slots, "_accommodation_prompted": True},
                "message": message,
                "structured_response": {"message": message},
                "node_timings_ms": _bump_timing(state, "plan_node", t0),
            },
            goto=END,
        )

    already_asked = bool(pending_slots.get("_asked"))
    prefs = _extract_plan_preferences(ctx, plan_prefs if already_asked else None)
    plan_prefs = {
        "pace": prefs.pace or plan_prefs["pace"],
        "interests": prefs.interests or plan_prefs["interests"],
        "budget": prefs.budget or plan_prefs["budget"],
    }
    if not already_asked and not prefs.has_enough_info:
        message = L(lang,
            "Happy to plan this for you. A few quick optional questions - "
            "skip any and I'll use sensible defaults:\n"
            "- How do you like to **pace** a trip - relaxed, moderate, or packed?\n"
            "- Any **special interests** or things to prioritise/avoid "
            "(museums, food, nightlife, crowds, early starts)?\n"
            "- A rough **per-person budget** for activities and tickets?\n\n"
            'Just say "go ahead" and I\'ll plan with sensible defaults.',
            "Rado ću ovo isplanirati za vas. Nekoliko kratkih neobaveznih pitanja - "
            "preskočite koje god želite i koristit ću razumne pretpostavke:\n"
            "- Kakav **tempo** putovanja volite - opušten, umjeren ili nabijen?\n"
            "- Imate li **posebne interese** ili stvari koje treba istaknuti/izbjeći "
            "(muzeji, hrana, noćni život, gužve, rani ustanci)?\n"
            "- Okvirni **budžet po osobi** za aktivnosti i ulaznice?\n\n"
            'Samo recite "može" i isplanirat ću s razumnim pretpostavkama.')
        _log("plan_node        → asking planning preferences (one-time)")
        return Command(
            update={
                "intent": real_intent,
                "pending_intent": real_intent,
                "pending_slots": {**pending_slots, **plan_prefs, "_asked": True},
                "message": message,
                "structured_response": {"message": message},
                "node_timings_ms": _bump_timing(state, "plan_node", t0),
                **({"accommodation_geo": accom_geo_update} if accom_geo_update else {}),
            },
            goto=END,
        )

    original_request = pending_slots.get("_original_request")
    if original_request:
        ctx = {**ctx, "user_message": original_request}
    ctx = {**ctx, "plan_preferences": plan_prefs}

    ack = L(lang,
        "Great, I have everything I need! Building your day-by-day itinerary - this usually takes about 30 seconds...",
        "Super, imam sve što mi treba! Slažem vaš plan po danima - ovo obično traje oko 30 sekundi...")
    _log("plan_node        → routing to execute_plan_node")
    return Command(
        update={
            "collected_context": ctx,
            "pending_slots": None,
            "message": ack,
            "structured_response": {"message": ack},
            "node_timings_ms": _bump_timing(state, "plan_node", t0),
            **({"accommodation_geo": accom_geo_update} if accom_geo_update else {}),
        },
        goto="execute_plan_node",
    )


def _detect_place_exclusions(user_message: str, mandatory_place_names: list[str]) -> list[str]:
    if not mandatory_place_names or not user_message:
        return []

    from pydantic import BaseModel as _BM, Field as _F

    class _ExclusionResult(_BM):
        excluded: list[str] = _F(default_factory=list)

    names_str = ", ".join(f'"{n}"' for n in mandatory_place_names)
    prompt = (
        f'Saved trip places: [{names_str}]\n'
        f'User message: "{user_message}"\n\n'
        "List the place names from the saved list that the user explicitly does NOT want to visit, "
        "skip, or remove. Use the exact names from the list. Return an empty list if none."
    )
    try:
        result = llm_fast.with_structured_output(_ExclusionResult).invoke(prompt)
        lower_map = {n.lower(): n for n in mandatory_place_names}
        return [lower_map[r.lower()] for r in (result.excluded or []) if r.lower() in lower_map]
    except Exception:
        return []


def refine_node(state: TripPlannerState) -> Command:
    t0 = _now_ms()
    ctx = state.get("collected_context") or {}
    trip = ctx.get("trip") or {}
    pending_slots = state.get("pending_slots") or {}
    real_intent = state.get("intent") or "refine_itinerary"

    interrupt, ctx, trip, accom_geo_update = _resolve_accommodation(
        state, ctx, trip, pending_slots, real_intent, "refine_node", t0
    )
    if interrupt is not None:
        return interrupt

    original_request = pending_slots.get("_original_request")
    if original_request:
        ctx = {**ctx, "user_message": original_request}

    plan_prefs = {
        "pace": pending_slots.get("pace", ""),
        "interests": pending_slots.get("interests", ""),
        "budget": pending_slots.get("budget", ""),
    }
    ctx = {**ctx, "plan_preferences": plan_prefs}

    existing_exclusions = list(state.get("excluded_places") or [])
    new_exclusions = _detect_place_exclusions(
        ctx.get("user_message", ""),
        ctx.get("mandatory_place_names") or [],
    )
    if new_exclusions:
        _log(f"refine_node      → excluding places: {new_exclusions}")
        merged_exclusions = list({*existing_exclusions, *new_exclusions})
        excluded_lower = {e.lower() for e in merged_exclusions}
        ctx = {
            **ctx,
            "mandatory_place_names": [
                n for n in (ctx.get("mandatory_place_names") or [])
                if n.lower() not in excluded_lower
            ],
        }
    else:
        merged_exclusions = existing_exclusions

    ack = L(state.get("user_language") or "en",
        "Got it! Applying your changes to the itinerary now...",
        "U redu! Sada primjenjujem vaše izmjene na plan...")
    _log("refine_node      → routing to execute_plan_node")
    return Command(
        update={
            "collected_context": ctx,
            "excluded_places": merged_exclusions,
            "pending_slots": None,
            "message": ack,
            "structured_response": {"message": ack},
            "node_timings_ms": _bump_timing(state, "refine_node", t0),
            **({"accommodation_geo": accom_geo_update} if accom_geo_update else {}),
        },
        goto="execute_plan_node",
    )


def execute_plan_node(state: TripPlannerState) -> Command:
    t0 = _now_ms()
    lang = state.get("user_language") or "en"
    ctx = state.get("collected_context") or {}
    trip = ctx.get("trip") or {}
    is_refinement = bool(ctx.get("current_plan"))
    plan_prefs = ctx.get("plan_preferences") or {"pace": "", "interests": "", "budget": ""}

    departure_date = ctx.get("departure_date")
    departure_cutoff = ctx.get("departure_cutoff")
    arrival_date = ctx.get("arrival_date")
    arrival_cutoff = ctx.get("arrival_cutoff")

    departure_block = ""
    if departure_cutoff and departure_date:
        dep_mode = trip.get("departure_transport_mode", "transport")
        dep_time = (trip.get("departure_at") or "")[:16].replace("T", " ")
        departure_block = f"""
DEPARTURE CONSTRAINT (HARD - must be enforced in the plan):
- Departure: {dep_time} ({dep_mode}) on {departure_date}
- All activities on {departure_date} MUST end by {departure_cutoff} (includes travel to airport/station).
- Do NOT schedule any activity that ends after {departure_cutoff} on {departure_date}.
"""

    arrival_block = ""
    if arrival_cutoff and arrival_date:
        arr_mode = trip.get("arrival_transport_mode", "transport")
        arr_time = (trip.get("arrival_at") or "")[:16].replace("T", " ")
        arrival_block = f"""
ARRIVAL CONSTRAINT (HARD - must be enforced in the plan):
- Arrival: {arr_time} ({arr_mode}) on {arrival_date}
- On {arrival_date}, no activity may start before {arrival_cutoff} (includes transfer from airport/station + hotel check-in).
"""

    checkin_block = ""
    accommodation_details = ctx.get("accommodation_details")
    if accommodation_details:
        checkin_block = f"""
ACCOMMODATION DETAILS (use as soft constraints when scheduling):
{accommodation_details}
- If check-in time is mentioned and participants may arrive earlier, consider scheduling a luggage storage activity first.
- If checkout time is mentioned and departure is later that day, consider scheduling a luggage storage activity after checkout.
"""
    parser = PydanticOutputParser(pydantic_object=GeneratedPlan)

    mode_block = (
        "REFINEMENT MODE: Apply user_message as a delta on top of current_plan. "
        "Keep valid parts unchanged; modify only what the user asked."
        if is_refinement
        else "FRESH PLAN: Build the itinerary from scratch using saved places and trip dates."
    )

    accommodation_address = (trip.get("accommodation_address") or "").strip()
    if accommodation_address:
        ordering_hint = (
            f"\nORDERING - MINIMISE BACKTRACKING (apply to every day):\n"
            f"- The accommodation is at \"{accommodation_address}\".\n"
            f"- Order each day's stops as ONE geographic sweep: start at the stop nearest the "
            f"accommodation, then move steadily in a single direction.\n"
            f"- Never walk past a stop you already visited, and never head back toward the "
            f"accommodation between two later stops. If two nearby stops sit on the same side, "
            f"do them consecutively.\n"
        )
    else:
        ordering_hint = (
            "\nORDERING - MINIMISE BACKTRACKING (apply to every day):\n"
            "- Order each day's stops as ONE geographic sweep in a single direction; never "
            "schedule a later stop that sits back past an earlier one.\n"
            "- Cluster the day so the last stop is near the dinner venue.\n"
        )

    prefs_block = ""
    _pref_lines = []
    if plan_prefs.get("pace"):
        _pref_lines.append(f"- Preferred pace: {plan_prefs['pace']}")
    if plan_prefs.get("interests"):
        _pref_lines.append(f"- Special interests / wishes: {plan_prefs['interests']}")
    if plan_prefs.get("budget"):
        _pref_lines.append(f"- Per-person budget for activities and tickets: {plan_prefs['budget']}")
    if _pref_lines:
        prefs_block = (
            "\nPARTICIPANT PREFERENCES (soft constraints - honor where feasible):\n"
            + "\n".join(_pref_lines)
            + "\n- Pace governs activities per day and walking distance; budget governs cost_estimate_cents per activity.\n"
        )

    if is_refinement:
        strategies: list[tuple[str, str]] = [("c1", "")]
    else:
        strategies = [
            (
                "c1",
                "OPTIMISATION STRATEGY - TIGHT GEOGRAPHY: cluster each day's activities as "
                "close together as possible to minimise transit time, even if it means less "
                "category variety within a day.",
            ),
            (
                "c2",
                "OPTIMISATION STRATEGY - VARIED DAYS: spread iconic sights and categories "
                "across days so every day mixes culture, food and leisure; accept slightly "
                "more travel between stops in exchange for better-balanced, varied days.",
            ),
        ]

    ctx_json = _ctx_json(ctx)
    format_instructions = parser.get_format_instructions()
    lang_block = ("" if lang != "hr" else
        "\nLANGUAGE - write every human-readable field in Croatian: generation_rationale, "
        "notes, assumptions, hard_constraints, soft_constraints, and all suggestion "
        "titles/details. Keep proper names (places, stations, transport lines, restaurants) "
        "in their original form. Times, schema keys and enum values stay unchanged.\n")

    def _build_prompt(strategy_block: str) -> str:
        return f"""{mode_block}

You are an expert travel planner. Build the best possible day-by-day itinerary.

WORK IN THIS ORDER:
1. Fill hard_constraints: list every hard rule below as ONE short line each.
2. Fill soft_constraints: list the soft preferences as short lines.
3. Then build plan.days so EVERY hard constraint holds and soft ones are honoured where feasible.
This up-front list is your reasoning scratchpad - do it before scheduling, keep each line short.
{strategy_block}
{departure_block}{arrival_block}{checkin_block}{ordering_hint}{prefs_block}
HARD RULES - list each in hard_constraints, then satisfy every one:
- Trip date bounds (all days within start_date..end_date)
- Departure cutoff on {departure_date or "N/A"} if present above
- Arrival cutoff on {arrival_date or "N/A"} if present above
- All MUST-VISIT places (see below) scheduled at least once

CRITICAL - DO NOT schedule airport arrival, flight landing, or airport transfer as an activity in plan.days. The arrival is already encoded in the arrival cutoff above. The first activity on {arrival_date or "the arrival day"} must start at or after {arrival_cutoff or "the arrival cutoff"}.

PLACE PRIORITY - classify each saved place before scheduling:
- MUST-VISIT: places where participant comments express strong desire or urgency
  (e.g. "we absolutely must see this", "this is the whole reason we're going", "non-negotiable")
  AND iconic landmarks any visitor to this destination would consider essential
  (e.g. Eiffel Tower in Paris, Colosseum in Rome) - use your knowledge of the destination.
- SHOULD-VISIT: places with comments expressing timing preference (e.g. "only in the morning",
  "book in advance") but no strong urgency - include if schedule allows.
- NICE-TO-HAVE: places with no comments and not iconic - include only if time and geography permit.

If the trip is too short to include everything, drop NICE-TO-HAVE first, then SHOULD-VISIT.
Never drop a MUST-VISIT place.

MEALS - schedule them as REAL activities, never just a time_block label on sightseeing:
- Every FULL day must have a LUNCH activity (start 12:00–14:00) and a DINNER activity (start 17:30–21:00).
- Dinner time is FLEXIBLE within that window - there is no fixed dinner hour. Pull dinner earlier (e.g. 18:00) whenever the afternoon would otherwise finish with a long empty stretch; only push it late if the day's sightseeing genuinely runs long.
- A meal is its own activity entry. Use a saved restaurant whose location fits that day's area. If no saved restaurant fits, pick a REAL, well-known restaurant or café you know in that area of the destination city - use its actual name (e.g. "Café de Flore", "L'As du Fallafel"). NEVER use a generic placeholder like "Lunch - bistro near X". In the notes field add 2 short alternatives: "Alternatives: [Name 1], [Name 2]". duration 60–90 min, time_block "lunch"/"dinner".
- cost_estimate_cents realistic per person: lunch ~1500–2500, dinner ~3000–5000 (scale to the stated budget if given).
- Spread saved restaurants across days - one per meal slot, never reuse one and never stack two restaurants on one day while another full day has no dinner.
- Breakfast is assumed at the accommodation before the first activity - do NOT add an activity for it, but no full day's first activity may start before 09:00. Exception: if the user explicitly requests a breakfast stop (e.g. on a checkout/departure day), add it as an activity and name a specific, real café or brasserie near the accommodation - never use a generic placeholder like "Breakfast - café near X".
- Arrival day: skip a meal only if it falls entirely before the arrival cutoff. Departure day: skip a meal only if it falls after the departure cutoff.
- NO DEAD TIME: the gap between one activity's end (including its travel) and the next activity's start must stay under ~90 min. A long empty afternoon before dinner is a planning failure - close it by moving dinner earlier, adding a real extra stop (a nearby NICE-TO-HAVE place, park, café, viewpoint or neighbourhood walk, each as its own activity), or extending nearby durations. Never leave 2+ unscheduled hours.

Soft preferences - list these in soft_constraints: pace, category diversity, per-place participant timing preferences.

For the itinerary optimize:
- Sensible geography per day, balanced day load, meal timing, cost realism
- Respect comments_by_place timing preferences (morning/evening/etc.)
- Honor participant comments and stated preferences from conversation

KEEP OUTPUT TERSE - every extra word slows generation:
- hard_constraints / soft_constraints: ONE short line per item, no nested detail or explanation.
- generation_rationale: exactly ONE short sentence.
- notes: at most ONE short sentence per activity, only essential non-obvious info; never describe the place.
- assumptions / suggestion details: short and factual, no padding.

For plan.days[].activities each entry needs:
- position, place_name, start_time (HH:MM), duration_minutes, time_block
- cost_estimate_cents: realistic PER-PERSON cost in euro cents for entry/tickets (0 if free)
- travel_method_to_next: "transit" if distance > ~2.5 km in city, else "walk"
- travel_duration_to_next_minutes: realistic (transit: 20-45 min including transfers)
- transit_details: REQUIRED whenever travel_method_to_next == "transit". Fill with:
  - line: the specific public transport line to take (e.g. "Métro 1", "RER B", "Bus 72", "Tram T3a")
  - boarding_station: exact name of the station/stop where the traveller boards
  - exit_station: exact name of the station/stop where the traveller gets off
  - direction: direction of travel on that line (e.g. "direction La Défense", "direction Château de Vincennes")
  Use real station names for the destination city. If a transfer is needed, describe the most direct single-line option.
- latitude, longitude: For places that appear in the saved places list, LEAVE BOTH null - they are filled in automatically from saved data, do not waste output echoing them. For any place NOT in the saved list, provide your best-guess coordinates for the destination city.

SELF-CHECK BEFORE RETURNING (MANDATORY - run on every day, for every consecutive pair of activities, before outputting):
Compute this.end = this.start_time + this.duration_minutes + this.travel_duration_to_next_minutes.
The next activity MUST satisfy: next.start_time >= this.end.
If next.start_time < this.end, push next.start_time forward to exactly this.end (and cascade the shift to every later activity that day). There must be ZERO pairs where the earlier activity (including its travel time) ends after the next one starts.

Then verify EVERY full day also passes (fix the day if it fails):
- A lunch activity starts 12:00–14:00 and a dinner activity starts 17:30–21:00 (skip a meal only when an arrival/departure cutoff makes it impossible).
- No consecutive pair has an idle gap over ~90 min: next.start_time - this.end <= 90. If a gap is larger, move dinner earlier, insert a filler activity, or extend durations, then re-run this check.
- Ordering does not backtrack: the stops progress in one geographic direction, never returning past an earlier stop.
Do NOT return the plan until EVERY day passes all of these checks.

Context:
{ctx_json}
{lang_block}
{format_instructions}
"""

    chain = llm | parser

    def _run_candidate(item: tuple[str, str]) -> Any:
        cid, strategy = item
        c0 = _now_ms()
        try:
            res = chain.invoke(_build_prompt(strategy))
            _log(f"execute_plan     {cid} LLM returned in {round(_now_ms() - c0)}ms")
            return res
        except Exception as e:
            _log(f"execute_plan     {cid} LLM error after {round(_now_ms() - c0)}ms: {e}")
            return e

    _log(f"execute_plan     → LLM ({_model_id}) × {len(strategies)} candidate(s) (parallel) ...")
    batch_t0 = _now_ms()
    with ThreadPoolExecutor(max_workers=len(strategies)) as executor:
        results = list(executor.map(_run_candidate, strategies))
    _log(f"execute_plan     all LLM calls done in {round(_now_ms() - batch_t0)}ms wall-clock")

    candidates: list[CandidateRecord] = []

    for (cid, _), res in zip(strategies, results):
        if isinstance(res, Exception):
            _log(f"execute_plan     {cid} failed: {res}")
            continue
        out: GeneratedPlan = res
        if not (out.plan and out.plan.days):
            _log(f"execute_plan     {cid} returned an empty plan - skipping")
            continue
        plan_dict = out.plan.model_dump()
        _backfill_coords(plan_dict, ctx.get("places") or [])
        n_days = len(plan_dict.get("days") or [])
        _log(f"execute_plan     {cid} ok - {n_days} days, confidence {out.preliminary_confidence:.2f}")
        candidates.append(
            CandidateRecord(
                id=cid,
                plan={
                    "plan": plan_dict,
                    "accommodation_suggestions": [s.model_dump() for s in out.accommodation_suggestions],
                    "transport_suggestions": [s.model_dump() for s in out.transport_suggestions],
                },
                generation_rationale=out.generation_rationale,
                assumptions=out.assumptions,
                preliminary_confidence=out.preliminary_confidence,
            )
        )

    if not candidates:
        raise RuntimeError("execute_plan_node: no candidate could be generated.")

    elapsed = round(_now_ms() - t0)
    _log(f"execute_plan     done ({elapsed}ms) - {len(candidates)} candidate(s)")

    return Command(
        update={
            "collected_context": ctx,
            "pending_slots": None,
            "candidates": candidates,
            "repair_round": 0,
            "max_repair_rounds": int(os.environ.get("TRIP_PLANNER_MAX_REPAIRS", "2")),
            "node_timings_ms": _bump_timing(state, "execute_plan_node", t0),
        },
        goto="validate_candidates",
    )


def validate_candidates(state: TripPlannerState) -> Command:
    t0 = _now_ms()
    ctx = state.get("collected_context") or {}
    reports: list[CandidateValidation] = []
    for c in state.get("candidates") or []:
        reports.append(validate_candidate(candidate_id=c["id"], plan_root=c["plan"], context=ctx))

    any_pass = any(r["hard_pass"] for r in reports)
    all_fail = not any_pass

    for r in reports:
        cid = r["candidate_id"]
        if r["hard_pass"]:
            w = len(r.get("warnings") or [])
            _log(f"validate         {cid}  PASS  ({w} warning{'s' if w != 1 else ''})")
        else:
            codes = [v["code"] for v in (r.get("violations") or [])]
            _log(f"validate         {cid}  FAIL  {' · '.join(codes)}")

    update = {
        "validation_reports": reports,
        "node_timings_ms": _bump_timing(state, "validate_candidates", t0),
    }

    if any_pass:
        return Command(update=update, goto="score_candidates")

    rounds = int(state.get("repair_round") or 0)
    max_r = int(state.get("max_repair_rounds") or 2)
    if all_fail and rounds < max_r:
        return Command(update=update, goto="repair_failed_candidates")

    return Command(update=update, goto="compose_response")


def repair_failed_candidates(state: TripPlannerState) -> Command:
    t0 = _now_ms()

    lang = state.get("user_language") or "en"
    ctx = state.get("collected_context") or {}
    reports = state.get("validation_reports") or []
    failing_ids = {r["candidate_id"] for r in reports if not r["hard_pass"]}
    violations_by_id = {r["candidate_id"]: r.get("violations") or [] for r in reports}

    parser = PydanticOutputParser(pydantic_object=TripPlanCore)
    format_instructions = parser.get_format_instructions()
    ctx_json = _ctx_json(ctx)

    max_r = int(state.get("max_repair_rounds") or 2)
    next_round = int(state.get("repair_round") or 0) + 1

    candidates = state.get("candidates") or []
    to_repair = [c for c in candidates if c["id"] in failing_ids]

    prompts: list[str] = []
    for c in to_repair:
        violations = violations_by_id.get(c["id"]) or []
        violation_text = "\n".join(f"- [{v['code']}] {v['message']}" for v in violations)
        current_plan_json = json.dumps(c["plan"], ensure_ascii=False)
        prompts.append(f"""You are a travel planner fixing a broken itinerary.

The following itinerary failed validation with these errors:
{violation_text}

Current itinerary:
{current_plan_json}

Trip context:
{ctx_json}

Fix ONLY the listed errors. Keep everything else unchanged:
- Do not remove or reorder places unless required by a violation
- Preserve start times, durations and travel methods that are not causing violations
- If a TIME_OVERLAP exists, adjust start times to avoid it
- If MANDATORY_PLACE_MISSING, add the missing place on the most appropriate day
- If DEPARTURE_CONFLICT, move the activity to end before the departure cutoff
- If ARRIVAL_CONFLICT, move the activity to start after the arrival cutoff
- If TRAVEL_INFEASIBLE, change travel_method_to_next from "walk" to "transit"
{"" if lang != "hr" else chr(10) + "Keep all human-readable text (rationale, notes, suggestions) in Croatian, as in the current itinerary." + chr(10)}
{format_instructions}
""")

    _log(f"repair [{next_round}/{max_r}]     → LLM repair × {len(prompts)} candidate(s)")
    results = (llm | parser).batch(prompts, return_exceptions=True) if prompts else []

    repaired_by_id: dict[str, CandidateRecord] = {}
    for c, res in zip(to_repair, results):
        if isinstance(res, Exception):
            _log(f"repair [{next_round}/{max_r}]     {c['id']}  failed: {res} - keeping original")
            continue
        repaired_plan = res.model_dump()
        _backfill_coords(repaired_plan, ctx.get("places") or [])
        fixed = dict(c)
        fixed["plan"] = {**c["plan"], "plan": repaired_plan}
        fixed["assumptions"] = list(c.get("assumptions") or []) + [f"LLM repair round {next_round}"]
        repaired_by_id[c["id"]] = fixed

    new_candidates = [repaired_by_id.get(c["id"], c) for c in candidates]

    return Command(
        update={
            "candidates": new_candidates,
            "repair_round": next_round,
            "node_timings_ms": _bump_timing(state, "repair_failed_candidates", t0),
        },
        goto="validate_candidates",
    )


def score_candidates(state: TripPlannerState) -> Command:
    t0 = _now_ms()
    ctx = state.get("collected_context") or {}
    reports = {r["candidate_id"]: r for r in (state.get("validation_reports") or [])}
    best_id = None
    best_score = -1e9
    table: list[dict[str, Any]] = []
    weights: dict[str, float] = {}

    for c in state.get("candidates") or []:
        rid = c["id"]
        rep = reports.get(rid)
        if rep and not rep["hard_pass"]:
            continue

        row = score_plan(candidate_id=rid, plan_root=c["plan"], context=ctx)
        weights = row.pop("weights", {}) or weights
        table.append(row)
        if row["final_score"] > best_score:
            best_score = row["final_score"]
            best_id = rid

    for row in table:
        marker = "selected" if row["candidate_id"] == best_id else "        "
        _log(
            f"score            {row['candidate_id']} {marker}  final={row.get('final_score', 0):.3f}  "
            f"(travel {row.get('travel_efficiency_score')}, "
            f"pref {row.get('preference_fit_score')}, "
            f"balance {row.get('day_balance_score')}, "
            f"schedule {row.get('schedule_quality_score')}, "
            f"fairness {row.get('participant_fairness_score')}, "
            f"budget {row.get('budget_fit_score')})"
        )

    if not best_id:
        _log("score            no candidate passed - falling through to compose")

    score_report = {
        "candidates": table,
        "selected_candidate_id": best_id,
        "weights": weights,
    }
    return Command(
        update={
            "selected_candidate_id": best_id,
            "score_report": score_report,
            "node_timings_ms": _bump_timing(state, "score_candidates", t0),
        },
        goto="compose_response",
    )


def compose_response(state: TripPlannerState) -> Command:
    t0 = _now_ms()
    lang = state.get("user_language") or "en"
    selected = state.get("selected_candidate_id")
    candidates = {c["id"]: c for c in (state.get("candidates") or [])}
    reports = {r["candidate_id"]: r for r in (state.get("validation_reports") or [])}

    ctx_for_compose = state.get("collected_context") or {}
    trip = ctx_for_compose.get("trip") or {}
    accommodation = (trip.get("accommodation_address") or "").strip() or None

    _accom_location: dict | None = None
    _al, _ao = trip.get("accommodation_latitude"), trip.get("accommodation_longitude")
    if _al and _ao:
        _accom_location = {"address": accommodation or "", "latitude": _al, "longitude": _ao}

    chosen = candidates.get(selected) if selected else None
    rep = reports.get(selected) if selected else None

    if chosen and rep and rep["hard_pass"]:
        w = len(rep.get("warnings") or [])
        _log(f"compose          PASS - {selected}, {w} soft warning{'s' if w != 1 else ''}")
        msg = _format_trip_overview(chosen, rep, accommodation, lang)
        structured = {
            **chosen["plan"],
            "accommodation_suggestions": chosen["plan"].get("accommodation_suggestions") or [],
            "transport_suggestions": chosen["plan"].get("transport_suggestions") or [],
            "constraint_report": {
                "hard_pass": True,
                "selected_candidate_id": selected,
                "violations": rep.get("violations") or [],
                "warnings": rep.get("warnings") or [],
            },
            "score_report": state.get("score_report") or {},
            "message": msg,
        }
        if _accom_location:
            structured["accommodation_location"] = _accom_location
    else:
        ranked: list[tuple[int, float, dict, dict]] = []
        for c in state.get("candidates") or []:
            r = reports.get(c["id"])
            days = ((c.get("plan") or {}).get("plan") or {}).get("days") or []
            if not r or not days:
                continue
            ranked.append((
                len(r.get("violations") or []),
                -float(c.get("preliminary_confidence") or 0.0),
                c,
                r,
            ))
        ranked.sort(key=lambda t: (t[0], t[1]))

        if ranked:
            _, _, best_effort, best_rep = ranked[0]
            violations = best_rep.get("violations") or []
            warnings = best_rep.get("warnings") or []
            codes = " · ".join(v["code"] for v in violations)
            _log(
                f"compose          BEST-EFFORT - {best_effort['id']}, "
                f"{len(violations)} unresolved violation{'s' if len(violations) != 1 else ''}  {codes}"
            )
            caveat_lines = "\n".join(f"- [{v['code']}] {v['message']}" for v in violations)
            overview = _format_trip_overview(best_effort, best_rep, accommodation, lang)
            msg = L(lang,
                "I couldn't fully resolve every constraint, but here's the closest "
                "workable itinerary - please double-check the flagged points and tell "
                "me how you'd like to adjust:\n\n"
                f"**Needs your attention:**\n{caveat_lines}\n\n---\n\n{overview}",
                "Nisam uspio riješiti baš svako ograničenje, ali evo najbližeg "
                "izvedivog plana - provjerite označene točke i recite mi "
                "kako biste ga željeli prilagoditi:\n\n"
                f"**Treba vašu pozornost:**\n{caveat_lines}\n\n---\n\n{overview}")
            structured = {
                **best_effort["plan"],
                "accommodation_suggestions": best_effort["plan"].get("accommodation_suggestions") or [],
                "transport_suggestions": best_effort["plan"].get("transport_suggestions") or [],
                "constraint_report": {
                    "hard_pass": False,
                    "best_effort": True,
                    "selected_candidate_id": best_effort["id"],
                    "violations": violations,
                    "warnings": warnings,
                },
                "score_report": state.get("score_report") or {},
                "message": msg,
            }
            if _accom_location:
                structured["accommodation_location"] = _accom_location
        else:
            violations_all: list[dict[str, Any]] = []
            for r in state.get("validation_reports") or []:
                for v in r.get("violations") or []:
                    violations_all.append({"candidate_id": r["candidate_id"], **v})
            codes = " · ".join(v["code"] for v in violations_all)
            _log(f"compose          FAIL - {len(violations_all)} violation{'s' if len(violations_all) != 1 else ''}  {codes}")
            violation_lines = [f"- [{v['code']}] {v['message']}" for v in violations_all]
            violation_summary = "\n".join(violation_lines) if violation_lines else L(lang,
                "No specific violations recorded.", "Nema zabilježenih konkretnih prekršaja.")
            msg = L(lang,
                f"Could not build a feasible itinerary.\n\n"
                f"**Issues found:**\n{violation_summary}\n\n"
                f"**Suggestions:** remove one mandatory stop, add an extra day, or allow transit between distant locations.",
                f"Nisam mogao izraditi izvediv plan.\n\n"
                f"**Pronađeni problemi:**\n{violation_summary}\n\n"
                f"**Prijedlozi:** uklonite jednu obaveznu stanicu, dodajte još jedan dan ili dopustite prijevoz između udaljenih lokacija.")
            structured = {
                "plan": {"days": []},
                "accommodation_suggestions": [],
                "transport_suggestions": [],
                "constraint_report": {
                    "hard_pass": False,
                    "violations": violations_all,
                    "warnings": [],
                    "suggested_relaxations": [
                        "Remove one mandatory place",
                        "Add an extra day",
                        "Allow transit instead of walking between distant stops",
                    ],
                },
                "score_report": state.get("score_report") or {},
                "message": msg,
            }

    if os.environ.get("TRIP_DEBUG_DUMP", "").strip().lower() in ("1", "true", "yes"):
        _dump_candidates(state, structured)

    return Command(
        update={
            "constraint_report": structured["constraint_report"],
            "message": structured["message"],
            "structured_response": structured,
            "node_timings_ms": _bump_timing(state, "compose_response", t0),
        },
        goto=END,
    )


