from __future__ import annotations
from langgraph.graph import END
from langgraph.types import Command
from models.shemas import IntentClassification
from models.state import TripPlannerState
from utils.context import collect_context
from langchain_core.output_parsers import PydanticOutputParser
from ._shared import (
    _bump_timing,
    _ctx_json,
    _extract_text,
    _log,
    _now_ms,
    lang_directive,
    llm_fast,
    resolve_language,
)

def route_intent(state: TripPlannerState) -> Command:
    t0 = _now_ms()
    ctx = collect_context(state)
    has_plan = bool(state.get("current_plan"))
    lang = resolve_language(state, state.get("user_message", ""))
    _log(f"route_intent     language → {lang}")

    history = (ctx.get("conversation_history_tail") or [])[-5:]
    history_text = "\n".join(f"{m['role'].capitalize()}: {m['content']}" for m in history)

    pending = (state.get("pending_intent") or "").strip()
    if pending:
        intent = pending
        _log(f"route_intent → {intent} (from pending_intent)")
        return {
            "collected_context": ctx,
            "intent": intent,
            "pending_intent": None,
            "user_language": lang,
            "node_timings_ms": _bump_timing(state, "route_intent", t0),
        }

    parser = PydanticOutputParser(pydantic_object=IntentClassification)
    prompt = f"""Classify this user message in a trip planning assistant.

{"Recent conversation:" + chr(10) + history_text + chr(10) if history_text else ""}User message: "{state.get('user_message', '')}"
Has existing itinerary: {has_plan}

Intents:
- plan_itinerary: user wants a new day-by-day itinerary generated
- refine_itinerary: user wants to modify, adjust, or update an existing itinerary
- recommend: user wants suggestions for places, cafes, restaurants, activities, or tips
- accommodation: user is asking about hotels, hostels, Airbnb, or where to stay
- transport: user is asking about flights, buses, trains, or how to get to the destination
- general: factual questions, logistics, or general trip chat

{parser.get_format_instructions()}
"""
    try:
        parsed: IntentClassification = (llm_fast | parser).invoke(prompt)
        intent = parsed.intent
    except Exception:
        intent = "general"

    _log(f"route_intent → {intent}")
    return {
        "collected_context": ctx,
        "intent": intent,
        "user_language": lang,
        "node_timings_ms": _bump_timing(state, "route_intent", t0),
    }

def recommend_node(state: TripPlannerState) -> Command:
    t0 = _now_ms()
    ctx = state.get("collected_context") or {}
    user_msg = state.get('user_message', '')
    destination = (ctx.get("trip") or {}).get("destination", "")

    web_context = ""
    if destination:
        from services.web_search import web_search
        search_q = f"{user_msg} {destination}" if destination not in user_msg else user_msg
        results = web_search(search_q, max_results=4)
        if results:
            snippets = "\n".join(
                f"- [{r['title']}]({r['href']}): {r['body'][:150]}"
                for r in results if r.get("href")
            )
            web_context = f"\n\nCurrent web results:\n{snippets}"

    prompt = f"""You are a helpful trip planning assistant giving recommendations.

Trip context:
{_ctx_json(ctx)}
{web_context}
User message: {user_msg}

Give a specific, grounded recommendation based on the trip's saved places, dates, and any participant comments.
If web results are provided, use them to give up-to-date suggestions and include source links where helpful.
Be concise (2-4 sentences or a short list).
{lang_directive(state.get("user_language") or "en")}"""
    try:
        response = llm_fast.invoke(prompt)
        message = _extract_text(response.content if hasattr(response, "content") else response)
    except Exception as e:
        message = f"Could not generate recommendation: {e}"

    _log(f"recommend_node done ({round(_now_ms() - t0)}ms)")
    return Command(
        update={
            "intent": "recommend",
            "message": message,
            "structured_response": {"message": message},
            "node_timings_ms": _bump_timing(state, "recommend_node", t0),
        },
        goto=END,
    )

def general_node(state: TripPlannerState) -> Command:
    t0 = _now_ms()
    ctx = state.get("collected_context") or {}
    history = ctx.get("conversation_history_tail") or []
    history_text = "\n".join(f"{m['role'].capitalize()}: {m['content']}" for m in history[-6:])

    prompt = f"""You are a helpful trip planning assistant.

Trip context:
{_ctx_json(ctx)}

{"Recent conversation:" + chr(10) + history_text if history_text else ""}
User message: {state.get('user_message', '')}
Answer helpfully and concisely. If you don't know something specific, say so and offer what you do know from context.
{lang_directive(state.get("user_language") or "en")}"""
    try:
        response = llm_fast.invoke(prompt)
        message = _extract_text(response.content if hasattr(response, "content") else response)
    except Exception as e:
        message = f"Could not generate response: {e}"

    _log(f"general_node done ({round(_now_ms() - t0)}ms)")
    return Command(
        update={
            "intent": "general",
            "message": message,
            "structured_response": {"message": message},
            "node_timings_ms": _bump_timing(state, "general_node", t0),
        },
        goto=END,
    )
