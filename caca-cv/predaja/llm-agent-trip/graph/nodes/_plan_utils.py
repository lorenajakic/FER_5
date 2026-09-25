from __future__ import annotations

from datetime import datetime
from typing import Any

from ._shared import L

_SKIP_OPERATIONAL = ("luggage", "storage", "airport", "shuttle", "arrival", "transfer", "landing")

_HR_WEEKDAYS = [
    "ponedjeljak", "utorak", "srijeda", "četvrtak", "petak", "subota", "nedjelja",
]
_HR_MONTHS = [
    "siječnja", "veljače", "ožujka", "travnja", "svibnja", "lipnja",
    "srpnja", "kolovoza", "rujna", "listopada", "studenoga", "prosinca",
]


def _date_label(dt: datetime, lang: str) -> str:
    if lang == "hr":
        return f"{_HR_WEEKDAYS[dt.weekday()]}, {dt.day}. {_HR_MONTHS[dt.month - 1]}"
    return dt.strftime("%A, %b %-d")


def _backfill_coords(plan: dict[str, Any], places: list[dict[str, Any]]) -> None:
    coords: dict[str, tuple[float, float]] = {}
    for p in places or []:
        name = (p.get("name") or "").strip().lower()
        lat, lon = p.get("latitude"), p.get("longitude")
        if name and lat is not None and lon is not None:
            try:
                coords[name] = (float(lat), float(lon))
            except (TypeError, ValueError):
                continue
    for day in (plan or {}).get("days") or []:
        if not isinstance(day, dict):
            continue
        for act in day.get("activities") or []:
            if not isinstance(act, dict):
                continue
            hit = coords.get((act.get("place_name") or "").strip().lower())
            if hit:
                act["latitude"], act["longitude"] = hit


def _format_trip_overview(chosen: dict, rep: dict, accommodation: str | None = None, lang: str = "en") -> str:
    plan_root = chosen["plan"]
    plan = plan_root.get("plan") or plan_root
    days = plan.get("days") or []
    accom_suggestions = plan_root.get("accommodation_suggestions") or []
    transport_suggestions = plan_root.get("transport_suggestions") or []

    rationale = (chosen.get("generation_rationale") or "").strip()
    first_sentence = rationale.split(".")[0].strip() if rationale else ""

    breakdown = L(lang, "Here's your day-by-day breakdown:", "Evo vašeg plana po danima:")
    if first_sentence:
        header = f"{first_sentence}. {breakdown}"
    else:
        if days:
            header = L(lang,
                "Your itinerary is ready. Here's the day-by-day breakdown:",
                "Vaš plan je spreman. Evo razrade po danima:")
        else:
            return L(lang, "Your itinerary is ready.", "Vaš plan je spreman.")

    lines = [header, ""]
    if accommodation:
        lines.append(L(lang,
            f"**Where you're based:** {accommodation} - each full day starts and ends here.",
            f"**Vaša baza:** {accommodation} - svaki puni dan počinje i završava ovdje."))
        lines.append("")

    for day in days:
        day_num = day.get("day_number")
        date_str = str(day.get("date") or "")
        acts = day.get("activities") or []

        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            date_label = _date_label(dt, lang)
        except (ValueError, TypeError):
            date_label = date_str

        places = [
            a["place_name"]
            for a in acts
            if isinstance(a, dict) and a.get("place_name")
            and not any(kw in (a.get("place_name") or "").lower() for kw in _SKIP_OPERATIONAL)
        ]
        if not places:
            places = [
                a["place_name"]
                for a in acts
                if isinstance(a, dict) and a.get("place_name")
            ]

        places_str = " · ".join(places[:5])
        if len(places) > 5:
            places_str += L(lang, f" (+{len(places) - 5} more)", f" (+{len(places) - 5} više)")

        day_word = L(lang, "Day", "Dan")
        lines.append(f"**{day_word} {day_num} – {date_label}**")
        if places_str:
            lines.append(places_str)
        lines.append("")

    if transport_suggestions or accom_suggestions:
        lines.append("---")

    if transport_suggestions:
        lines.append(L(lang, "**Getting around:**", "**Kretanje:**"))
        for t in transport_suggestions:
            lines.append(f"- **{t['title']}** - {t['details']}")
        lines.append("")

    if accom_suggestions:
        lines.append(L(lang, "**Accommodation:**", "**Smještaj:**"))
        for a in accom_suggestions:
            lines.append(f"- **{a['title']}** - {a['details']}")
        lines.append("")

    w = len(rep.get("warnings") or [])
    if w:
        lines.append(L(lang,
            f"*{w} soft constraint{'s' if w != 1 else ''} noted (pacing / budget) - no blockers.*",
            f"*Zabilježeno mekih ograničenja: {w} (tempo / budžet) - nema blokera.*"))

    return "\n".join(lines)
