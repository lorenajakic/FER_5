from __future__ import annotations
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

class TransitDetails(BaseModel):
    line: str = Field(description="Specific line name, e.g. 'Métro 1', 'RER B', 'Bus 72', 'Tram T3a'")
    boarding_station: str = Field(description="Name of the stop/station where you board")
    exit_station: str = Field(description="Name of the stop/station where you get off")
    direction: Optional[str] = Field(default=None, description="Direction of travel, e.g. 'direction La Défense'")

class PlanActivity(BaseModel):
    position: int
    place_name: str
    start_time: Optional[str] = None
    duration_minutes: Optional[int] = None
    time_block: Literal["morning", "lunch", "afternoon", "dinner", "evening"]
    cost_estimate_cents: Optional[int] = None
    cost_currency: str = "EUR"
    travel_method_to_next: Literal["walk", "transit", "taxi", "none"] = "none"
    travel_duration_to_next_minutes: Optional[int] = None
    transit_details: Optional[TransitDetails] = Field(
        default=None,
        description="Required when travel_method_to_next is 'transit'. Specific line, boarding and exit stations."
    )
    notes: Optional[str] = Field(
        default=None,
        description="At most ONE short sentence with only essential, non-obvious info (e.g. 'book tickets ahead'). Do NOT describe the place.",
    )
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class PlanDay(BaseModel):
    day_number: int
    date: str
    activities: List[PlanActivity] = Field(default_factory=list)

class TripPlanCore(BaseModel):
    days: List[PlanDay] = Field(default_factory=list)

class SuggestionItem(BaseModel):
    title: str
    details: str
    estimated_cost_cents: Optional[int] = None

class GeneratedPlan(BaseModel):
    candidate_id: str = Field(default="c1")
    hard_constraints: List[str] = Field(
        default_factory=list,
        description="BEFORE scheduling, list each hard rule to obey as ONE short line "
                    "(trip date bounds, departure/arrival cutoffs, every must-visit place).",
    )
    soft_constraints: List[str] = Field(
        default_factory=list,
        description="Each soft preference as ONE short line (pace, category variety, "
                    "meal timing, per-place timing wishes).",
    )
    generation_rationale: str = Field(
        default="",
        description="Exactly ONE short sentence summarising the itinerary's approach.",
    )
    assumptions: List[str] = Field(default_factory=list)
    preliminary_confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    plan: TripPlanCore
    accommodation_suggestions: List[SuggestionItem] = Field(default_factory=list)
    transport_suggestions: List[SuggestionItem] = Field(default_factory=list)

class IntentClassification(BaseModel):
    intent: Literal["plan_itinerary", "refine_itinerary", "recommend", "accommodation", "transport", "general"]
    rationale: str

class TransportPreferences(BaseModel):
    origin: str = Field(default="", description="Departure city/airport, e.g. 'Zagreb' or empty string")
    transport_type: str = Field(default="", description="Comma-separated list of the modes the user named, each one of 'flight'/'bus'/'train' (e.g. 'bus' or 'bus,flight'); 'all' ONLY if the user explicitly says any/all/doesn't matter; '' if not mentioned")
    travel_scope: str = Field(default="intercity", description="'intercity' if user wants to get TO the destination, 'local' if user wants to get around WITHIN the destination city")
    trip_type: str = Field(default="", description="'one_way' if user wants only outbound, 'round_trip' if user wants return ticket too, '' if not clear from context")
    has_enough_info: bool = Field(description="True if origin is known (for intercity), or if user is asking about local transport (scope=local always has enough info)")

class AccommodationPreferences(BaseModel):
    budget: str = Field(default="", description="Budget per night, e.g. '100 EUR' or empty string")
    neighborhood: str = Field(default="", description="Preferred area/neighborhood or empty string")
    accommodation_type: str = Field(default="", description="Type: hotel, hostel, airbnb, apartment, etc. or empty string")
    preferences: str = Field(default="", description="Soft/qualitative wants that are NOT budget, area, or type - e.g. 'quiet', 'central', 'has a kitchen', 'family-friendly', 'good for couples'. Empty string if none mentioned.")
    has_enough_info: bool = Field(description="True if at least one preference is known OR user is clearly asking for general options")


class AccommodationCuration(BaseModel):
    keep_indices: list[int] = Field(description="Indices (from the numbered candidate list) to keep, best match first. Only drop a listing if it clearly conflicts with a stated soft preference; when unsure, keep it.")
    note: str = Field(default="", description="One short, natural sentence for the user explaining the selection (e.g. how many matched, what was prioritised or dropped and why). In the user's language.")

class PlanPreferences(BaseModel):
    pace: str = Field(default="", description="'relaxed', 'moderate', 'packed', or '' if not mentioned")
    interests: str = Field(default="", description="Free-form special interests or things to prioritise/avoid (museums, food, crowds, early starts), or ''")
    budget: str = Field(default="", description="Rough per-person budget for activities and tickets, e.g. '300 EUR', or ''")
    has_enough_info: bool = Field(description="True if the user gave at least one preference, OR explicitly said they have no preference / just want it planned.")


class AccommodationGeocode(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Geocoding confidence 0–1")
    can_locate: bool = Field(
        description="True if coordinates can be provided with confidence >= 0.7; false if address is too vague or unrecognisable"
    )

class PlaceExclusion(BaseModel):
    excluded: List[str] = Field(
        default_factory=list,
        description="Place names the user explicitly said they do NOT want to visit, want removed, or want to skip. Return exact or near-exact matches from the known places list only. Empty list if none.",
    )
