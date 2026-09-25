from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote_plus

from langgraph.graph import END
from langgraph.types import Command

from models.shemas import TransportPreferences
from models.state import TripPlannerState

from ._shared import L, _bump_timing, _extract_text, _log, _now_ms, lang_directive, llm_fast

_SKYSCANNER_HOST = "skyscanner-flights-travel-api.p.rapidapi.com"


def _skyscrapper_search_airport(query: str, api_key: str) -> tuple[str, str]:
    import urllib.request
    url = f"https://{_SKYSCANNER_HOST}/flights/searchAirport?query={quote_plus(query)}"
    req = urllib.request.Request(url, headers={
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": _SKYSCANNER_HOST,
    })
    with urllib.request.urlopen(req, timeout=8) as r:
        data = json.loads(r.read())
    places = data.get("places") or []
    if not places:
        return "", ""
    best = places[0]
    return best.get("skyId", ""), best.get("entityId", "")


def _skyscrapper_search_flights(
    origin: str, destination: str, date_out: str, date_back: str,
    adults: int, api_key: str, max_results: int = 5
) -> list[dict]:
    import urllib.request
    from urllib.parse import urlencode
    import urllib.error

    try:
        origin_sky, origin_entity = _skyscrapper_search_airport(origin, api_key)
        dest_sky, dest_entity = _skyscrapper_search_airport(destination, api_key)
    except Exception as e:
        _log(f"_skyscrapper airport lookup error: {e}")
        return []

    if not origin_sky or not dest_sky:
        _log("_skyscrapper: could not resolve airport codes")
        return []

    params: dict[str, str] = {
        "originSkyId": origin_sky,
        "destinationSkyId": dest_sky,
        "originEntityId": origin_entity,
        "destinationEntityId": dest_entity,
        "date": date_out,
        "adults": str(adults or 1),
        "currency": "EUR",
        "locale": "en-US",
        "market": "en-US",
        "countryCode": "HR",
        "cabinClass": "economy",
    }
    if date_back:
        params["returnDate"] = date_back

    url = f"https://{_SKYSCANNER_HOST}/flights/searchFlights?{urlencode(params)}"
    req = urllib.request.Request(url, headers={
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": _SKYSCANNER_HOST,
    })
    data = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.loads(r.read())
            break
        except urllib.error.HTTPError as e:
            if e.code in (502, 503, 504) and attempt < 2:
                _log(f"_skyscrapper flight search {e.code}, retry {attempt + 1}")
                time.sleep(2)
            else:
                _log(f"_skyscrapper flight search error: {e.code}")
                return []
        except Exception as e:
            _log(f"_skyscrapper flight search error: {e}")
            return []
    if data is None:
        return []

    itineraries = data.get("itineraries") or (data.get("data") or {}).get("itineraries") or []
    date_short_out = date_out.replace("-", "")[2:]
    date_short_back = date_back.replace("-", "")[2:] if date_back else ""

    flight_url = (
        f"https://www.skyscanner.net/transport/flights"
        f"/{origin_sky.lower()}/{dest_sky.lower()}"
        f"/{date_short_out}/"
        + (f"{date_short_back}/" if date_short_back else "")
        + f"?adults={adults}&cabinclass=economy&ref=home"
    )

    seen: dict[tuple, dict] = {}
    for it in itineraries:
        legs = it.get("legs") or []
        if not legs:
            continue

        def _leg_info(leg: dict) -> tuple[str, str, str, int, str]:
            carriers = leg.get("carriers") or []
            carrier = " + ".join(c.get("name", "") for c in carriers if c.get("name")) or ""
            dep = leg.get("departure", "")[:16].replace("T", " ")
            arr = leg.get("arrival", "")[:16].replace("T", " ")
            duration = leg.get("durationMinutes") or leg.get("durationInMinutes") or 0
            stops = leg.get("stopCount", 0)
            stop_str = "direct" if stops == 0 else f"{stops} stop{'s' if stops > 1 else ''}"
            return carrier, dep, arr, duration, stop_str

        carrier, dep, arr, duration, stop_str = _leg_info(legs[0])

        ret_str = ""
        if date_back and len(legs) > 1:
            _, ret_dep, ret_arr, ret_dur, ret_stops = _leg_info(legs[1])
            ret_str = f" | Return: {ret_dep} → {ret_arr} ({ret_stops}, {ret_dur // 60}h {ret_dur % 60}m)"

        price_obj = it.get("price") or {}
        price_str = price_obj.get("formatted", "")
        try:
            price_num = float(str(price_obj.get("amount") or price_obj.get("raw") or 0))
        except (ValueError, TypeError):
            price_num = float("inf")

        trip_label = "round-trip" if date_back else "one-way"
        pax_note = f"total for {adults} pax, {trip_label}" if adults > 1 else trip_label
        key = (carrier, dep, arr)
        if key not in seen or price_num < seen[key]["price_num"]:
            seen[key] = {
                "price_num": price_num,
                "entry": {
                    "mode": "flights",
                    "title": f"{carrier} | Out: {dep} → {arr} ({stop_str}, {duration // 60}h {duration % 60}m){ret_str} - {price_str} ({pax_note})",
                    "url": flight_url,
                    "snippet": f"Out: {dep}→{arr} ({stop_str}, {duration // 60}h {duration % 60}m){ret_str} | {price_str} ({pax_note})",
                },
            }
    ranked = sorted(seen.values(), key=lambda v: v["price_num"])[:max_results]
    results = [v["entry"] for v in ranked]
    _log(f"_skyscrapper: {len(results)} flights ({origin_sky}→{dest_sky})")
    return results


def _format_one_way_legs(flights: list[dict]) -> str:
    lines = []
    for f in flights:
        title = f.get("title", "")
        snippet = f.get("snippet", "")
        url = f.get("url", "")

        carrier = title.split(" | ")[0].strip() if " | " in title else title.split(" - ")[0].strip()
        price = title.split(" - ")[-1].split(" (")[0].strip() if " - " in title else ""

        out_raw = next((p.strip() for p in snippet.split(" | ") if p.strip().startswith("Out:")), "")

        def _fmt(raw: str) -> str:
            raw = raw.replace("Out: ", "").replace("Return: ", "")
            if "(" in raw:
                times, rest = raw.split("(", 1)
                return f"{times.replace('→', ' → ').strip()} · {rest.rstrip(')')}"
            return raw

        line = f"**[{carrier}]({url})** - {price}"
        if out_raw:
            line += f"\n- {_fmt(out_raw)}"
        lines.append(line)
    return "\n\n".join(lines)


def _format_flight_sections(
    origin: str, destination: str, start_date: str, end_date: str,
    flights_out: list[dict], flights_ret: list[dict], footer: str, is_round_trip: bool,
    lang: str = "en",
) -> str:
    out_label = L(lang, "Outbound", "Polazak")
    ret_label = L(lang, "Return", "Povratak")
    parts = []
    if flights_out:
        parts.append(f"**{out_label} - {origin} → {destination} ({start_date})**\n\n{_format_one_way_legs(flights_out)}")
    if is_round_trip and flights_ret:
        parts.append(f"**{ret_label} - {destination} → {origin} ({end_date})**\n\n{_format_one_way_legs(flights_ret)}")
    return "\n\n---\n\n".join(parts) + f"\n\n---\n{footer}"


def _format_flight_md(flights: list[dict], sky_url: str, gf_url: str) -> str:
    lines = []
    for f in flights:
        title = f.get("title", "")
        snippet = f.get("snippet", "")

        carrier = title.split(" | ")[0].strip() if " | " in title else title.split(" - ")[0].strip()

        price = ""
        if " - " in title:
            price = title.split(" - ")[-1].split(" (")[0].strip()

        parts = [p.strip() for p in snippet.split(" | ")]
        out_raw = next((p for p in parts if p.startswith("Out:")), "")
        ret_raw = next((p for p in parts if p.startswith("Return:")), "")

        def _fmt_leg(raw: str) -> str:
            raw = raw.replace("Out: ", "").replace("Return: ", "")
            if "(" in raw:
                times, rest = raw.split("(", 1)
                times = times.replace("→", " → ").strip()
                details = ", ".join(x.strip() for x in rest.rstrip(")").split(","))
                return f"{times} · {details}"
            return raw

        block = f"**[{carrier}]({sky_url})** - {price}"
        if out_raw:
            block += f"\n- Outbound: {_fmt_leg(out_raw)}"
        if ret_raw:
            block += f"\n- Return: {_fmt_leg(ret_raw)}"
        lines.append(block)

    body = "\n\n".join(lines)
    return f"{body}\n\n---\n[Search on Skyscanner]({sky_url}) · [Search on Google Flights]({gf_url})"


_TRANSPORT_DOMAINS = {
    "buses":  ["flixbus.com", "omio.com", "busbud.com", "eurolines.com"],
    "trains": ["thetrainline.com", "raileurope.com", "omio.com", "bahn.com"],
}


def _clean_snippet(text: str, max_len: int = 180) -> str:
    import re
    text = re.sub(r"#+\s*", "", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text[:max_len]


def _tavily_search_transport(mode: str, query: str, max_results: int = 5) -> list[dict]:
    from services.web_search import web_search
    preferred = _TRANSPORT_DOMAINS.get(mode, [])
    results = web_search(query, max_results=max_results)
    preferred_results = [r for r in results if any(d in r.get("href", "") for d in preferred)]
    other_results = [r for r in results if r not in preferred_results]
    ordered = (preferred_results + other_results)[:3]
    out = [
        {
            "mode": mode,
            "title": r["title"],
            "url": r["href"],
            "snippet": _clean_snippet(r["body"]),
        }
        for r in ordered if r.get("href")
    ]
    _log(f"Tavily search: {len(out)} results [{mode}]")
    return out


def _extract_transport_prefs(prompt: str) -> TransportPreferences:
    try:
        return llm_fast.with_structured_output(TransportPreferences).invoke(prompt)
    except Exception:
        return TransportPreferences(has_enough_info=False)


def transport_node(state: TripPlannerState) -> Command:
    t0 = _now_ms()
    lang = state.get("user_language") or "en"
    ctx = state.get("collected_context") or {}
    trip = ctx.get("trip") or {}

    destination = trip.get("destination", "")
    start_date = trip.get("start_date", "")
    end_date = trip.get("end_date", "")
    participant_count = trip.get("participant_count", 1)
    arrival_mode = trip.get("arrival_transport_mode", "")
    arrival_details = trip.get("arrival_details", "")

    history = ctx.get("conversation_history_tail") or []
    history_text = "\n".join(f"{m['role']}: {m['content']}" for m in history[-6:])
    user_msg = state.get("user_message", "")

    pref_prompt = f"""From the conversation and trip context below, extract transport preferences.

Trip destination: {destination}
Trip start date: {start_date or "unknown"}
Trip end date: {end_date or "unknown"}
Arrival transport mode hint: {arrival_mode or "unknown"}
Arrival details: {arrival_details or "none"}

Conversation:
{history_text}
user: {user_msg}

Determine travel_scope:
- "local" if user is asking how to get AROUND the destination city (metro, tram, bus pass, day ticket, public transport within the city)
- "intercity" if user is asking how to GET TO the destination (flights, buses, trains from another city)

Determine trip_type from what the user EXPLICITLY says in their message only:
- "round_trip" if the user explicitly says return, round-trip, both ways, or similar
- "one_way" if the user explicitly says one-way, only going, or similar
- "" if the user did not say either - do NOT infer from dates in trip context

Extract origin city only for intercity travel.
has_enough_info is True if: scope is "local" (no origin needed), OR scope is "intercity" and origin can be inferred."""

    try:
        prefs = _extract_transport_prefs(pref_prompt)
    except Exception:
        prefs = TransportPreferences(has_enough_info=False)

    saved = state.get("pending_slots") or {}
    if saved.get("transport_type") and (not prefs.transport_type or prefs.transport_type == "all"):
        prefs.transport_type = saved["transport_type"]
    if saved.get("travel_scope") and not prefs.travel_scope:
        prefs.travel_scope = saved["travel_scope"]
    if saved.get("trip_type") and not prefs.trip_type:
        prefs.trip_type = saved["trip_type"]

    if prefs.travel_scope == "local":
        prompt = f"""You are a helpful trip planning assistant giving local transport advice.

Destination city: {destination}
Trip dates: {start_date} → {end_date}
Group size: {participant_count} people

User message: {user_msg}

Give practical, specific local transport info for {destination}: types of public transport available (metro, tram, bus), typical ticket prices (single ride, day pass, multi-day pass), any tourist cards worth buying, and any app or card needed to pay. Use real approximate prices in EUR.

Formatting rules - follow exactly:
- Use **bold** for section labels (e.g. **Public transport**, **Uber/Taxi**, **Car rental**)
- Use plain bullet points with - for details
- Do NOT use # ## ### headers
- Do NOT invent links or booking sites{lang_directive(lang)}"""

        try:
            response = llm_fast.invoke(prompt)
            message = _extract_text(response.content if hasattr(response, "content") else response)
        except Exception as e:
            message = f"Could not generate local transport info: {e}"

        _log(f"transport_node (local) done ({round(_now_ms() - t0)}ms)")
        return Command(
            update={
                "intent": "transport",
                "message": message,
                "structured_response": {"message": message},
                "node_timings_ms": _bump_timing(state, "transport_node", t0),
            },
            goto=END,
        )

    missing = []
    if not prefs.has_enough_info or not prefs.origin:
        missing.append(L(lang,
            "- Where are you travelling **from**? (city or airport)",
            "- Odakle **putujete**? (grad ili zračna luka)"))
    if not prefs.transport_type:
        missing.append(L(lang,
            "- Which **means of transport**: bus, train, or flight? (or say \"any\")",
            "- Kojim **prijevoznim sredstvom**: autobus, vlak ili avion? (ili recite \"svejedno\")"))
    if not prefs.trip_type:
        missing.append(L(lang,
            "- Are you looking for a **one-way** or **round-trip** ticket?",
            "- Tražite li **jednosmjernu** ili **povratnu** kartu?"))

    if missing:
        intro = L(lang,
            f"To find transport options to {destination}, could you tell me:",
            f"Da pronađem opcije prijevoza do {destination}, recite mi:")
        message = intro + "\n" + "\n".join(missing)
        return Command(
            update={
                "intent": "transport",
                "pending_intent": "transport",
                "pending_slots": {
                    "transport_type": prefs.transport_type,
                    "travel_scope": prefs.travel_scope,
                    "trip_type": prefs.trip_type,
                },
                "message": message,
                "structured_response": {"message": message},
                "node_timings_ms": _bump_timing(state, "transport_node", t0),
            },
            goto=END,
        )

    origin = prefs.origin
    transport_type = prefs.transport_type or "all"
    is_round_trip = prefs.trip_type == "round_trip"

    date_out = start_date.replace("-", "")[2:] if start_date else ""

    types = {t.strip() for t in transport_type.split(",") if t.strip()}
    search_all = "all" in types or not types
    search_flights = search_all or "flight" in types
    search_buses = search_all or "bus" in types
    search_trains = search_all or "train" in types

    rapidapi_key = os.environ.get("RAPIDAPI_KEY", "").strip()
    o_enc = quote_plus(origin)
    d_enc = quote_plus(destination)

    flights_out: list[dict] = []
    flights_ret: list[dict] = []

    if search_flights and rapidapi_key:
        with ThreadPoolExecutor(max_workers=2) as ex:
            fut_out = ex.submit(
                _skyscrapper_search_flights,
                origin, destination, start_date, "", participant_count, rapidapi_key, 7
            )
            fut_ret = ex.submit(
                _skyscrapper_search_flights,
                destination, origin, end_date, "", participant_count, rapidapi_key, 7
            ) if is_round_trip and end_date else None

            try:
                flights_out = fut_out.result()
            except Exception as e:
                _log(f"transport search error [outbound]: {e}")
            if fut_ret:
                try:
                    flights_ret = fut_ret.result()
                except Exception as e:
                    _log(f"transport search error [return]: {e}")

    buses_out: list[dict] = []
    buses_ret: list[dict] = []
    trains_out: list[dict] = []
    trains_ret: list[dict] = []

    ground_futures = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        if search_buses:
            ground_futures["buses_out"] = ex.submit(
                _tavily_search_transport, "buses",
                f"bus ticket {origin} to {destination} {start_date}".strip()
            )
            if is_round_trip and end_date:
                ground_futures["buses_ret"] = ex.submit(
                    _tavily_search_transport, "buses",
                    f"bus ticket {destination} to {origin} {end_date}".strip()
                )
        if search_trains:
            ground_futures["trains_out"] = ex.submit(
                _tavily_search_transport, "trains",
                f"train ticket {origin} to {destination} {start_date}".strip()
            )
            if is_round_trip and end_date:
                ground_futures["trains_ret"] = ex.submit(
                    _tavily_search_transport, "trains",
                    f"train ticket {destination} to {origin} {end_date}".strip()
                )
        for key, fut in ground_futures.items():
            try:
                result = fut.result()
                if key == "buses_out": buses_out = result
                elif key == "buses_ret": buses_ret = result
                elif key == "trains_out": trains_out = result
                elif key == "trains_ret": trains_ret = result
            except Exception as e:
                _log(f"ground search error [{key}]: {e}")

    deeplinks: dict[str, str] = {}
    if search_flights:
        import re as _re
        sky_url_out = (flights_out[0].get("url") if flights_out else None) or (
            f"https://www.skyscanner.net/transport/flights"
            f"/{o_enc.lower()}/{d_enc.lower()}/{date_out}/"
            f"?adults={participant_count}&cabinclass=economy"
        )
        deeplinks["Skyscanner"] = sky_url_out

        _m = _re.search(r"/transport/flights/([^/?]+)/([^/?]+)/", sky_url_out)
        if _m:
            oc, dc = _m.group(1).upper(), _m.group(2).upper()
            gf_flt = f"{oc}.{dc}.{start_date}"
            if is_round_trip and end_date:
                gf_flt += f"*{dc}.{oc}.{end_date}"
            pax_part = f";px:{participant_count}" if int(participant_count or 1) > 1 else ""
            deeplinks["Google Flights"] = (
                f"https://www.google.com/travel/flights#flt={gf_flt};c:EUR;e:1;sd:1;t:f{pax_part}"
            )
        else:
            deeplinks["Google Flights"] = (
                f"https://www.google.com/travel/flights?q=flights+from+{o_enc}+to+{d_enc}"
            )

    o_name = quote_plus(origin)
    d_name = quote_plus(destination.split(",")[0].strip())

    if search_buses:
        deeplinks["FlixBus"] = "https://www.flixbus.com/"
        deeplinks["Omio (out)"] = (
            f"https://www.omio.com/search?from_name={o_name}&to_name={d_name}"
            + (f"&departure_date={start_date}" if start_date else "")
            + f"&adult={participant_count or 1}"
        )
        if is_round_trip and end_date:
            deeplinks["Omio (ret)"] = (
                f"https://www.omio.com/search?from_name={d_name}&to_name={o_name}"
                f"&departure_date={end_date}&adult={participant_count or 1}"
            )

    if search_trains:
        deeplinks["Trainline"] = "https://www.thetrainline.com/"
        deeplinks["Rail Europe"] = "https://www.raileurope.com/"
        deeplinks["Omio trains (out)"] = (
            f"https://www.omio.com/search?from_name={o_name}&to_name={d_name}"
            + (f"&departure_date={start_date}" if start_date else "")
            + f"&adult={participant_count or 1}"
        )

    sections: list[str] = []

    def _fmt_ground_section(
        header: str, results_out: list[dict], results_ret: list[dict],
        is_rt: bool, date_out: str, date_ret: str,
        fallback_out: str, fallback_ret: str,
    ) -> str:
        out_label = L(lang, "Outbound", "Polazak")
        ret_label = L(lang, "Return", "Povratak")
        no_results = L(lang, "No live results. Search on:", "Nema rezultata uživo. Pretražite na:")
        parts = []
        leg_header_out = f"{header} - {out_label} ({date_out})" if date_out else f"{header} - {out_label}"
        if results_out:
            lines = []
            for r in results_out:
                lines.append(f"**[{r['title']}]({r['url']})**")
                if r.get("snippet"):
                    lines.append(f"- {r['snippet'][:180]}")
            parts.append(leg_header_out + "\n\n" + "\n\n".join(lines))
        else:
            parts.append(f"{leg_header_out}\n\n{no_results} {fallback_out}")

        if is_rt:
            leg_header_ret = f"{header} - {ret_label} ({date_ret})" if date_ret else f"{header} - {ret_label}"
            if results_ret:
                lines = []
                for r in results_ret:
                    lines.append(f"**[{r['title']}]({r['url']})**")
                    if r.get("snippet"):
                        lines.append(f"- {r['snippet'][:180]}")
                parts.append(leg_header_ret + "\n\n" + "\n\n".join(lines))
            else:
                parts.append(f"{leg_header_ret}\n\n{no_results} {fallback_ret}")

        return "\n\n---\n\n".join(parts)

    if search_flights:
        sky_url = deeplinks.get("Skyscanner", "")
        gf_url = deeplinks.get("Google Flights", "")
        flight_footer = f"[Skyscanner]({sky_url}) · [Google Flights]({gf_url})"
        if flights_out or flights_ret:
            sections.append(_format_flight_sections(
                origin, destination, start_date, end_date,
                flights_out, flights_ret, flight_footer, is_round_trip, lang
            ))
        else:
            sections.append(
                L(lang, "**Flights", "**Letovi") + f" - {origin} → {destination}**\n\n"
                + L(lang, "No live flight results found.", "Nema rezultata letova uživo.")
                + f"\n\n{flight_footer}"
            )

    if search_buses:
        sections.append(_fmt_ground_section(
            L(lang, "**Buses**", "**Autobusi**"),
            buses_out, buses_ret, is_round_trip, start_date, end_date,
            fallback_out=f"[FlixBus]({deeplinks['FlixBus']}) · [Omio]({deeplinks['Omio (out)']})",
            fallback_ret=f"[FlixBus]({deeplinks['FlixBus']}) · [Omio]({deeplinks.get('Omio (ret)', deeplinks['Omio (out)'])})",
        ))

    if search_trains:
        sections.append(_fmt_ground_section(
            L(lang, "**Trains**", "**Vlakovi**"),
            trains_out, trains_ret, is_round_trip, start_date, end_date,
            fallback_out=f"[Trainline]({deeplinks['Trainline']}) · [Rail Europe]({deeplinks['Rail Europe']}) · [Omio]({deeplinks['Omio trains (out)']})",
            fallback_ret=f"[Trainline]({deeplinks['Trainline']}) · [Rail Europe]({deeplinks['Rail Europe']})",
        ))

    message = "\n\n---\n\n".join(sections) if sections else L(lang,
        f"Could not find {transport_type} options for {origin} → {destination}.",
        f"Nisam pronašao opcije ({transport_type}) za {origin} → {destination}.")

    _log(f"transport_node (intercity) done ({round(_now_ms() - t0)}ms)")
    return Command(
        update={
            "intent": "transport",
            "message": message,
            "structured_response": {"message": message, "search_links": deeplinks},
            "node_timings_ms": _bump_timing(state, "transport_node", t0),
        },
        goto=END,
    )
