from __future__ import annotations
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse
from graph.build_graph import build_app
from graph import nodes as trip_nodes
from models.state import TripPlannerState

import json
import os
import uuid
from typing import Any, AsyncIterator, List, Optional

load_dotenv(os.path.join("config", ".env"))
load_dotenv(".env", override=True)

APP_VERSION = "0.1.0"

_agent = build_app()

class TripPayload(BaseModel):
    id: Optional[int] = None
    title: Optional[str] = None
    destination: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    participant_count: Optional[int] = None
    accommodation_address: Optional[str] = None
    accommodation_details: Optional[str] = None
    accommodation_latitude: Optional[float] = None
    accommodation_longitude: Optional[float] = None
    arrival_transport_mode: Optional[str] = None
    arrival_at: Optional[str] = None
    arrival_details: Optional[str] = None
    departure_transport_mode: Optional[str] = None
    departure_at: Optional[str] = None
    departure_details: Optional[str] = None

class PlacePayload(BaseModel):
    name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    category: Optional[str] = None

class CommentPayload(BaseModel):
    place_name: str
    user_name: Optional[str] = None
    body: str

class MessagePayload(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    trip: TripPayload
    places: List[PlacePayload] = Field(default_factory=list)
    place_comments: List[CommentPayload] = Field(default_factory=list)
    current_plan: Optional[dict[str, Any]] = None
    conversation_history: List[MessagePayload] = Field(default_factory=list)
    user_message: str
    thread_id: Optional[str] = None

def _verify_token(provided: Optional[str]) -> None:
    expected = os.environ.get("AGENT_TOKEN", "").strip()
    if not expected:
        return
    if (provided or "").strip() != expected:
        raise HTTPException(status_code=401, detail="invalid agent token")


def _request_to_state(req: ChatRequest) -> TripPlannerState:
    return {
        "trip": req.trip.model_dump(exclude_none=True),
        "places": [p.model_dump(exclude_none=True) for p in req.places],
        "place_comments": [c.model_dump(exclude_none=True) for c in req.place_comments],
        "current_plan": req.current_plan,
        "conversation_history": [m.model_dump() for m in req.conversation_history],
        "user_message": req.user_message,
    }


def _log_timings(timings: dict[str, float]) -> None:
    if not timings:
        return
    total = sum(timings.values())
    lines = ["[trip_planner] --- timings ---"]
    for node, ms in timings.items():
        bar = "█" * int(ms / total * 20)
        lines.append(f"[trip_planner]   {node:<30} {ms:>8.0f} ms  {bar}")
    lines.append(f"[trip_planner]   {'TOTAL':<30} {total:>8.0f} ms")
    print("\n".join(lines), flush=True)


def _final_payload(final_state: dict[str, Any]) -> dict[str, Any]:
    timings = final_state.get("node_timings_ms") or {}
    _log_timings(timings)
    return {
        "intent": final_state.get("intent") or "plan_itinerary",
        "message": final_state.get("message") or "",
        "structured_response": final_state.get("structured_response") or {},
        "node_timings_ms": timings,
    }

app = FastAPI(title="Trip Planner Agent", version=APP_VERSION)

@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "model": trip_nodes.default_chat_model(),
        "version": APP_VERSION,
    }


@app.post("/chat")
async def chat(
    req: ChatRequest,
    request: Request,
    x_agent_token: Optional[str] = Header(default=None, alias="X-Agent-Token"),
) -> EventSourceResponse:
    _verify_token(x_agent_token)

    thread_id = req.thread_id or f"trip-{req.trip.id or 'anon'}-{uuid.uuid4().hex[:8]}"
    cfg = {"configurable": {"thread_id": thread_id}}
    state = _request_to_state(req)

    async def event_stream() -> AsyncIterator[dict[str, Any]]:
        yield {"event": "status", "data": json.dumps({"stage": "start", "thread_id": thread_id})}

        final_state: dict[str, Any] = {}
        try:
            async for chunk in _agent.astream(state, config=cfg, stream_mode="updates"):
                if await request.is_disconnected():
                    return
                if not isinstance(chunk, dict):
                    continue
                for node_name, node_update in chunk.items():
                    payload = {"stage": node_name}
                    if isinstance(node_update, dict):
                        timings = node_update.get("node_timings_ms")
                        if isinstance(timings, dict) and node_name in timings:
                            payload["elapsed_ms"] = timings[node_name]
                        if node_update.get("message"):
                            payload["message"] = node_update["message"]
                        final_state.update(node_update)
                    yield {"event": "status", "data": json.dumps(payload)}
        except Exception as e:
            yield {"event": "error", "data": json.dumps({"message": str(e)})}
            return

        yield {"event": "final", "data": json.dumps(_final_payload(final_state))}

    return EventSourceResponse(event_stream())
