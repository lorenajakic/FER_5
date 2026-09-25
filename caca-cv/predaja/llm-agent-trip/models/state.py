from __future__ import annotations
from typing import Any, List, Literal, TypedDict

Intent = Literal[
    "plan_itinerary",
    "refine_itinerary",
    "recommend",
    "accommodation",
    "transport",
    "general",
]

class PlanViolation(TypedDict):
    code: str
    severity: Literal["hard", "soft"]
    message: str

class CandidateValidation(TypedDict):
    candidate_id: str
    hard_pass: bool
    violations: List[PlanViolation]
    warnings: List[PlanViolation]

class CandidateRecord(TypedDict):
    id: str
    plan: dict[str, Any]
    generation_rationale: str
    assumptions: List[str]
    preliminary_confidence: float

class TripPlannerState(TypedDict, total=False):

    trip: dict[str, Any]
    places: List[dict[str, Any]]
    place_comments: List[dict[str, Any]]
    current_plan: dict[str, Any] | None
    conversation_history: List[dict[str, str]]
    user_message: str

    collected_context: dict[str, Any]

    pending_intent: str | None
    pending_slots: dict[str, Any] | None

    accommodation_geo: dict[str, Any] | None

    excluded_places: List[str]

    intent: Intent | None
    intent_rationale: str | None

    user_language: str

    candidates: List[CandidateRecord]
    validation_reports: List[CandidateValidation]
    repair_round: int
    max_repair_rounds: int

    selected_candidate_id: str | None
    score_report: dict[str, Any] | None
    constraint_report: dict[str, Any] | None
    message: str
    structured_response: dict[str, Any]

    node_timings_ms: dict[str, float]
