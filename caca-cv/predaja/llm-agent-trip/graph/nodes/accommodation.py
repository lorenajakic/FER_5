from __future__ import annotations

import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote_plus

from langgraph.graph import END
from langgraph.types import Command

from models.shemas import AccommodationCuration, AccommodationPreferences
from models.state import TripPlannerState

from ._shared import L, _bump_timing, _extract_text, _log, _now_ms, lang_directive, llm_fast


_BOOKING_HOST = "booking-com.p.rapidapi.com"

_AREA_RADIUS_KM = 3.0
_FX_TO_EUR = {"EUR": 1.0, "GBP": 1.17, "USD": 0.92}
_CCY_SYMBOL = {"€": "EUR", "$": "USD", "£": "GBP"}


def _nights(checkin: str, checkout: str) -> int:
    import datetime
    try:
        d1 = datetime.date.fromisoformat(checkin)
        d2 = datetime.date.fromisoformat(checkout)
        return max((d2 - d1).days, 1)
    except Exception:
        return 1


def _parse_budget_eur(budget: str) -> float | None:
    if not budget:
        return None
    m = re.search(r"[\d.,]+", budget)
    if not m:
        return None
    try:
        return float(m.group().replace(",", "."))
    except ValueError:
        return None


def _airbnb_per_night_eur(price_str: str) -> float | None:
    if not price_str:
        return None
    m = re.search(r"([€$£])\s*([\d,]+)", str(price_str))
    if not m:
        return None
    cur = _CCY_SYMBOL.get(m.group(1), "EUR")
    try:
        return float(m.group(2).replace(",", "")) * _FX_TO_EUR.get(cur, 1.0)
    except ValueError:
        return None


def _parse_km(val) -> float | None:
    if val is None:
        return None
    s = str(val).strip().lower()
    m = re.search(r"[\d.,]+", s)
    if not m:
        return None
    num = float(m.group().replace(",", "."))
    if "m" in s and "km" not in s:
        num /= 1000.0
    return num


def _booking_total_price(hotel: dict) -> tuple[float | None, str]:
    comp = hotel.get("composite_price_breakdown") or {}
    for key in ("all_inclusive_amount", "gross_amount"):
        amt = comp.get(key) or {}
        val = amt.get("value")
        if val is not None:
            return float(val), amt.get("currency") or hotel.get("currency_code", "EUR")

    pb = hotel.get("price_breakdown") or {}
    for key in ("all_inclusive_price", "gross_price"):
        val = pb.get(key)
        if val is not None:
            return float(val), pb.get("currency") or hotel.get("currency_code", "EUR")

    val = hotel.get("min_total_price")
    if val is not None:
        return float(val), hotel.get("currency_code", "EUR")
    return None, hotel.get("currency_code", "EUR")


def _booking_search_hotels(
    destination: str, checkin: str, checkout: str,
    adults: int, api_key: str, max_results: int = 7, area: str = "",
    max_per_night_eur: float | None = None,
) -> list[dict]:
    import urllib.request
    from urllib.parse import urlencode

    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": _BOOKING_HOST,
    }

    loc_query = f"{area}, {destination}" if area else destination
    loc_url = f"https://{_BOOKING_HOST}/v1/hotels/locations?{urlencode({'name': loc_query, 'locale': 'en-gb'})}"
    try:
        req = urllib.request.Request(loc_url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as r:
            loc_data = json.loads(r.read())
    except Exception as e:
        _log(f"Booking locations error: {e}")
        return []

    preferred = (
        ("landmark", "district", "city_district", "neighborhood", "region", "city")
        if area else ("city", "region")
    )
    dest_id = None
    dest_type = "city"
    for want in preferred:
        for loc in (loc_data or []):
            if loc.get("dest_type") == want:
                dest_id = loc.get("dest_id")
                dest_type = want
                break
        if dest_id:
            break
    if not dest_id and loc_data:
        dest_id = loc_data[0].get("dest_id")
        dest_type = loc_data[0].get("dest_type", "city")
    if not dest_id:
        _log("Booking: could not resolve destination ID")
        return []
    _log(f"Booking: resolved '{loc_query}' → dest_id={dest_id} (dest_type={dest_type})")

    search_params = {
        "dest_id": dest_id,
        "dest_type": dest_type,
        "checkin_date": checkin,
        "checkout_date": checkout,
        "adults_number": str(adults or 1),
        "room_number": str(-(-(adults or 1) // 2)),
        "locale": "en-gb",
        "currency": "EUR",
        "order_by": "distance" if area else "popularity",
        "units": "metric",
        "filter_by_currency": "EUR",
        "page_number": "0",
    }
    search_url = f"https://{_BOOKING_HOST}/v1/hotels/search?{urlencode(search_params)}"
    try:
        req = urllib.request.Request(search_url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as r:
            data = json.loads(r.read())
    except Exception as e:
        _log(f"Booking hotel search error: {e}")
        return []

    nights = _nights(checkin, checkout)
    results = []
    for hotel in (data.get("result") or [])[:40]:
        name = hotel.get("hotel_name", "")
        url = hotel.get("url", "") or hotel.get("hotel_url", "")
        if url and not url.startswith("http"):
            url = "https://www.booking.com" + url
        if url and "?" not in url:
            url += f"?checkin={checkin}&checkout={checkout}&group_adults={adults or 1}&no_rooms=1"
        elif url:
            url += f"&checkin={checkin}&checkout={checkout}&group_adults={adults or 1}&no_rooms=1"
        rating = hotel.get("review_score")
        review_word = hotel.get("review_score_word", "")
        price, currency = _booking_total_price(hotel)

        if max_per_night_eur and price is not None:
            fx = _FX_TO_EUR.get((currency or "EUR").upper(), 1.0)
            if price * fx / nights > max_per_night_eur:
                continue
        address = hotel.get("address", "") + (f", {hotel.get('city', '')}" if hotel.get("city") else "")
        if not name:
            continue

        dist_km = _parse_km(hotel.get("distance")) if area else None
        parts = []
        if rating:
            parts.append(f"⭐ {rating}/10 {review_word}")
        if price:
            parts.append(f"{currency} {price:.0f} total (incl. taxes)")
        if dist_km is not None:
            parts.append(f"{dist_km:.1f} km from {area}")
        if address:
            parts.append(address)
        try:
            rating_val = float(rating) if rating is not None else None
        except (TypeError, ValueError):
            rating_val = None
        results.append({
            "source": "Booking.com",
            "title": name,
            "url": url or f"https://www.booking.com/search.html?ss={quote_plus(destination)}",
            "snippet": " | ".join(parts),
            "distance_km": dist_km,
            "rating_val": rating_val,
        })

    if area and any(r["distance_km"] is not None for r in results):
        near = [r for r in results if r["distance_km"] is not None and r["distance_km"] <= _AREA_RADIUS_KM]
        if not near:
            near = sorted(
                (r for r in results if r["distance_km"] is not None),
                key=lambda r: r["distance_km"],
            )[:3]
        _log(f"Booking.com: filtered {len(results)} → {len(near)} within {_AREA_RADIUS_KM}km of '{area}'")
        results = near

    results.sort(key=lambda r: (r["rating_val"] is not None, r["rating_val"] or 0), reverse=True)
    results = results[:max_results]

    for r in results:
        r.pop("distance_km", None)
        r.pop("rating_val", None)
    _log(f"Booking.com: {len(results)} hotels for '{loc_query}' ({checkin} → {checkout})")
    return results


def _curate_listings(
    listings: list[dict], preferences: str, context: str, lang: str
) -> tuple[list[dict], str]:
    numbered = "\n".join(
        f"{i}. [{l.get('source', '')}] {l.get('title', '')} - {l.get('snippet', '')}"
        for i, l in enumerate(listings)
    )
    prompt = f"""The user is choosing accommodation and expressed these soft preferences: "{preferences}".

These candidates already passed hard filters (budget, area, dates). Judge ONLY how well each fits the soft preferences above, using its name and details:

{numbered}

Keep the ones that fit (best first). Only drop a listing if it clearly conflicts with a stated preference; when unsure, keep it. Never invent listings or indices outside the list.{lang_directive(lang)}"""
    try:
        result = llm_fast.with_structured_output(AccommodationCuration).invoke(prompt)
        kept = [listings[i] for i in result.keep_indices if 0 <= i < len(listings)]
        if not kept:
            _log("accommodation curation kept 0 → ignoring")
            return listings, ""
        _log(f"accommodation curation: {len(listings)} → {len(kept)}")
        return kept, (result.note or "").strip()
    except Exception as e:
        _log(f"accommodation curation error: {e}")
        return listings, ""


def _extract_accommodation_prefs(pref_prompt: str) -> AccommodationPreferences:
    try:
        return llm_fast.with_structured_output(AccommodationPreferences).invoke(pref_prompt)
    except Exception:
        return AccommodationPreferences(has_enough_info=True)


_AIRBNB_HOST = "airbnb-search.p.rapidapi.com"


def _airbnb_search(
    destination: str, checkin: str, checkout: str,
    adults: int, api_key: str, max_results: int = 7, area: str = "",
    max_per_night_eur: float | None = None,
) -> list[dict]:
    import urllib.request
    from urllib.parse import urlencode

    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": _AIRBNB_HOST,
    }

    ac_query = f"{area}, {destination}" if area else destination
    ac_url = f"https://{_AIRBNB_HOST}/common/auto-complete?{urlencode({'query': ac_query})}"
    try:
        req = urllib.request.Request(ac_url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as r:
            ac_data = json.loads(r.read())
    except Exception as e:
        _log(f"Airbnb auto-complete error: {e}")
        return []

    place_id = None
    for item in (ac_data.get("data") or []):
        esp = item.get("explore_search_params") or {}
        place_id = esp.get("place_id") or item.get("placeId") or item.get("place_id")
        if place_id:
            break
    if not place_id:
        _log(f"Airbnb: could not resolve placeId for '{destination}'")
        return []

    search_params = urlencode({
        "placeId": place_id,
        "checkin": checkin,
        "checkout": checkout,
        "adults": str(adults or 1),
        "currency": "EUR",
    })
    search_url = f"https://{_AIRBNB_HOST}/stays/search?{search_params}"
    try:
        req = urllib.request.Request(search_url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as r:
            data = json.loads(r.read())
    except Exception as e:
        _log(f"Airbnb stays/search error: {e}")
        return []

    outer = data.get("data") or {}
    if isinstance(outer, dict):
        raw = outer.get("searchResults") or outer.get("results") or outer.get("listings") or []
    else:
        raw = outer
    if isinstance(raw, dict):
        raw = raw.get("results") or raw.get("listings") or []
    _log(f"Airbnb stays/search: {len(raw)} raw items")
    results = []
    for item in raw[:max_results]:
        listing = item.get("listing") or {}

        name_raw = item.get("nameLocalized") or listing.get("name") or item.get("title", "")
        if isinstance(name_raw, dict):
            name_raw = name_raw.get("localizedStringWithTranslationPreference") or name_raw.get("translatedText") or ""
        name = str(name_raw).strip()
        property_id = item.get("propertyId") or listing.get("id", "")
        rating = item.get("avgRatingLocalized") or listing.get("avg_rating")
        room_type = listing.get("room_type_category", "") or listing.get("room_type", "")

        price_obj = item.get("structuredDisplayPrice") or {}
        price_line = (price_obj.get("primaryLine") or price_obj.get("primary_line") or {})
        price = price_line.get("price") or price_line.get("displayComponentsPrice", {}).get("formattedAmount", "")
        if not price:
            pq = item.get("pricingQuote") or {}
            price = (pq.get("structuredStayDisplayPrice") or {}).get("primaryLine", {}).get("price", "")

        url = (
            f"https://www.airbnb.com/rooms/{property_id}"
            f"?check_in={checkin}&check_out={checkout}&adults={adults or 1}&guests={adults or 1}"
        ) if property_id else ""
        if not name or not url:
            continue

        if max_per_night_eur:
            pn = _airbnb_per_night_eur(price)
            if pn is not None and pn > max_per_night_eur:
                continue

        parts = []
        if rating:
            parts.append(f"⭐ {rating}")
        if room_type:
            parts.append(room_type.replace("_", " ").title())
        if price:
            parts.append(f"{price}/night")

        rating_m = re.search(r"[\d.]+", str(rating)) if rating else None
        rating_val = float(rating_m.group()) if rating_m else None
        results.append({
            "source": "Airbnb",
            "title": name,
            "url": url,
            "snippet": " | ".join(str(p) for p in parts),
            "rating_val": rating_val,
        })

    if not results:
        _log(f"Airbnb: 0 listings for '{destination}' ({checkin} → {checkout})")
        return results

    def _is_available(property_id: str) -> bool:
        from urllib.parse import urlencode
        import datetime
        try:
            checkin_dt = datetime.date.fromisoformat(checkin)
            checkout_dt = datetime.date.fromisoformat(checkout)

            months = []
            y, m = checkin_dt.year, checkin_dt.month
            while (y, m) <= (checkout_dt.year, checkout_dt.month):
                months.append((y, m))
                m += 1
                if m > 12:
                    m = 1
                    y += 1

            blocked: set[str] = set()
            saw_any_days = False
            for yy, mm in months:
                params = urlencode({"listingId": property_id, "month": mm, "year": yy})
                url = f"https://{_AIRBNB_HOST}/stays/availability-calendar?{params}"
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=8) as r:
                    cal = json.loads(r.read())
                days = (cal.get("data") or {}).get("days") or cal.get("days") or []
                if days:
                    saw_any_days = True
                blocked |= {
                    d.get("date") or d.get("calendarDate")
                    for d in days
                    if not (d.get("available") if "available" in d else d.get("isAvailable", True))
                }

            if not saw_any_days:
                return True
            cur = checkin_dt
            while cur < checkout_dt:
                if cur.isoformat() in blocked:
                    return False
                cur += datetime.timedelta(days=1)
            return True
        except Exception as e:
            _log(f"Airbnb availability check error ({property_id}): {e}")
            return True 

    property_ids = [r["url"].split("/rooms/")[1].split("?")[0] for r in results if "/rooms/" in r["url"]]
    with ThreadPoolExecutor(max_workers=7) as ex:
        availability = dict(zip(property_ids, ex.map(_is_available, property_ids)))

    results = [r for r in results if availability.get(r["url"].split("/rooms/")[1].split("?")[0], True)]
    results.sort(key=lambda r: (r["rating_val"] is not None, r["rating_val"] or 0), reverse=True)
    for r in results:
        r.pop("rating_val", None)
    _log(f"Airbnb: {len(results)} available listings for '{destination}' ({checkin} → {checkout})")
    return results


def accommodation_node(state: TripPlannerState) -> Command:
    t0 = _now_ms()
    lang = state.get("user_language") or "en"
    ctx = state.get("collected_context") or {}
    trip = ctx.get("trip") or {}

    destination = trip.get("destination", "")
    start_date = trip.get("start_date", "")
    end_date = trip.get("end_date", "")
    participant_count = trip.get("participant_count", 2)
    accommodation_set = trip.get("accommodation_address", "")
    accommodation_details = trip.get("accommodation_details", "")

    history = ctx.get("conversation_history_tail") or []
    history_text = "\n".join(f"{m['role']}: {m['content']}" for m in history[-8:])
    user_msg = state.get("user_message", "")
    full_context = history_text + f"\nuser: {user_msg}"

    pref_prompt = f"""From the conversation below, extract accommodation preferences if mentioned.

Conversation:
{full_context}

Extract: budget per night, preferred neighborhood/area, accommodation type (hotel/hostel/airbnb/apartment/etc.), and any soft/qualitative wants (quiet, central, kitchen, family-friendly, good for couples, etc.).
has_enough_info is true if at least one preference is known OR the user is clearly asking for general options."""

    pending_slots = state.get("pending_slots") or {}
    if pending_slots:
        pref_prompt += f"\n\nPreviously collected preferences: {pending_slots}"

    prefs: AccommodationPreferences = _extract_accommodation_prefs(pref_prompt)

    budget = prefs.budget or pending_slots.get("budget", "")
    neighborhood = prefs.neighborhood or pending_slots.get("neighborhood", "")
    accommodation_type = prefs.accommodation_type or pending_slots.get("accommodation_type", "")
    soft_preferences = prefs.preferences or pending_slots.get("preferences", "")

    if not budget and user_msg:
        _m = re.search(r'(\d+)\s*(?:euro|eur|€|\$|usd)', user_msg, re.I)
        if _m:
            budget = f"{_m.group(1)} EUR"

    if not prefs.has_enough_info:
        questions = [L(lang,
            "- What's your approximate **budget per night**?",
            "- Koliki je vaš približan **budžet po noćenju**?")]
        if not neighborhood:
            questions.append(L(lang,
                "- Do you have a preferred **neighborhood or area**, or are you open to anywhere?",
                "- Imate li željeni **kvart ili područje**, ili ste otvoreni za bilo gdje?"))
        intro = L(lang,
            f"Before I search for accommodation in {destination}, a couple of quick questions:",
            f"Prije nego potražim smještaj u {destination}, par kratkih pitanja:")
        message = intro + "\n" + "\n".join(questions)
        _log("accommodation_node → asking for clarification")
        return Command(
            update={
                "intent": "accommodation",
                "pending_intent": "accommodation",
                "pending_slots": {
                    "budget": budget,
                    "accommodation_type": accommodation_type,
                    "neighborhood": neighborhood,
                    "preferences": soft_preferences,
                },
                "message": message,
                "structured_response": {"message": message, "search_links": {}},
                "node_timings_ms": _bump_timing(state, "accommodation_node", t0),
            },
            goto=END,
        )

    city = destination.split(",")[0].strip()

    max_per_night_eur = _parse_budget_eur(budget)

    listings: list[dict] = []
    rapidapi_key = os.environ.get("RAPIDAPI_KEY", "").strip()
    if rapidapi_key:
        with ThreadPoolExecutor(max_workers=2) as ex:
            fut_booking = ex.submit(_booking_search_hotels, city, start_date, end_date, participant_count, rapidapi_key, 7, neighborhood, max_per_night_eur)
            fut_airbnb = ex.submit(_airbnb_search, city, start_date, end_date, participant_count, rapidapi_key, 7, neighborhood, max_per_night_eur)
            try:
                listings += fut_booking.result()
            except Exception as e:
                _log(f"Booking search error: {e}")
            try:
                listings += fut_airbnb.result()
            except Exception as e:
                _log(f"Airbnb search error: {e}")

    _log(f"accommodation_node → {len(listings)} listings (type={accommodation_type!r}, budget={budget!r}, area={neighborhood!r})")

    curation_note = ""
    if listings and soft_preferences:
        listings, curation_note = _curate_listings(listings, soft_preferences, full_context, lang)

    _SOURCE_HEADINGS = {
        "Booking.com": L(lang, "🏨 **Hotels (Booking.com)**", "🏨 **Hoteli (Booking.com)**"),
        "Airbnb": L(lang, "🏠 **Airbnb**", "🏠 **Airbnb**"),
    }

    def _fmt_listings(items: list[dict]) -> str:
        grouped: dict[str, list[dict]] = {}
        for l in items:
            grouped.setdefault(l.get("source", ""), []).append(l)
        blocks = []
        for source, group in grouped.items():
            lines = [f"**[{l['title']}]({l['url']})** - {l['snippet']}" for l in group]
            heading = _SOURCE_HEADINGS.get(source)
            blocks.append((heading + "\n\n" if heading else "") + "\n\n".join(lines))
        return "\n\n---\n\n".join(blocks)

    formatted_listings = _fmt_listings(listings)

    if not listings:
        from services.web_search import web_search
        type_hint = accommodation_type or "hotel"
        budget_hint = f"budget {budget}" if budget else ""
        area_hint = f"in {neighborhood}" if neighborhood else ""
        tavily_q = f"{type_hint} {area_hint} {budget_hint} {city} {start_date}".strip()
        tavily_results = web_search(
            tavily_q,
            max_results=4,
            include_domains=["booking.com", "airbnb.com", "hotels.com", "hostelworld.com"],
        )
        listings = [
            {
                "title": r["title"],
                "url": r["href"],
                "snippet": r["body"][:180],
            }
            for r in tavily_results if r.get("href")
        ]
        _log(f"accommodation_node → Tavily fallback: {len(listings)} results")
        formatted_listings = _fmt_listings(listings)

    if listings:
        example = L(lang,
            'a natural intro like "Here\'s what I found for your stay in London:"',
            'a natural intro like "Evo što sam pronašao za vaš boravak u Londonu:"')
        constraints = []
        if max_per_night_eur:
            constraints.append(f"under €{max_per_night_eur:.0f} per night")
        if neighborhood:
            constraints.append(f"in/near {neighborhood}")
        constraint_line = (
            f"\nThe results are already filtered to: {', '.join(constraints)}. "
            "Mention these constraints naturally in the sentence so the user knows they were applied."
            if constraints else ""
        )

        if curation_note:
            intro = curation_note
        else:
            intro_prompt = f"""You are a helpful trip planning assistant. Write ONE short conversational sentence introducing these accommodation results for {destination} ({start_date} → {end_date}, {participant_count} people, {len(listings)} options found). Do not list hotels, do not use headers - just {example}.{constraint_line} Output only that one sentence.{lang_directive(lang)}"""
            try:
                intro_resp = llm_fast.invoke(intro_prompt)
                intro = _extract_text(intro_resp.content if hasattr(intro_resp, "content") else intro_resp).strip()
            except Exception:
                intro = L(lang,
                    f"Here's what I found for your stay in {destination}:",
                    f"Evo što sam pronašao za vaš boravak u {destination}:")
        message = f"{intro}\n\n{formatted_listings}"
    else:
        message = L(lang,
            f"I couldn't find any listings for {destination} for those dates. Try searching directly on [Booking.com](https://www.booking.com/searchresults.html?ss={quote_plus(destination)}&checkin={start_date}&checkout={end_date}) or [Airbnb](https://www.airbnb.com/s/{quote_plus(destination)}/homes?checkin={start_date}&checkout={end_date}&adults={participant_count}).",
            f"Nisam pronašao smještaj u {destination} za te datume. Pokušajte pretražiti izravno na [Booking.com](https://www.booking.com/searchresults.html?ss={quote_plus(destination)}&checkin={start_date}&checkout={end_date}) ili [Airbnb](https://www.airbnb.com/s/{quote_plus(destination)}/homes?checkin={start_date}&checkout={end_date}&adults={participant_count}).")

    search_links = {}
    if destination:
        search_links["booking"] = (
            f"https://www.booking.com/searchresults.html"
            f"?ss={quote_plus(destination)}&checkin={start_date}&checkout={end_date}&group_adults={participant_count}"
        )
        search_links["airbnb"] = (
            f"https://www.airbnb.com/s/{quote_plus(destination)}/homes"
            f"?checkin={start_date}&checkout={end_date}&adults={participant_count}"
        )

    _log(f"accommodation_node done ({round(_now_ms() - t0)}ms)")
    return Command(
        update={
            "intent": "accommodation",
            "message": message,
            "structured_response": {"message": message, "search_links": search_links},
            "node_timings_ms": _bump_timing(state, "accommodation_node", t0),
        },
        goto=END,
    )
