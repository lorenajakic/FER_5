from langgraph.checkpoint.memory import MemorySaver
from models.state import TripPlannerState
from langgraph.graph import StateGraph

from graph.nodes import (
    accommodation_node,
    compose_response,
    execute_plan_node,
    general_node,
    plan_node,
    recommend_node,
    refine_node,
    repair_failed_candidates,
    route_intent,
    score_candidates,
    transport_node,
    validate_candidates,
)

def build_app():
    graph = StateGraph(TripPlannerState)

    graph.add_node("route_intent", route_intent)
    graph.add_node("plan_node", plan_node)
    graph.add_node("refine_node", refine_node)
    graph.add_node("execute_plan_node", execute_plan_node)
    graph.add_node("validate_candidates", validate_candidates)
    graph.add_node("repair_failed_candidates", repair_failed_candidates)
    graph.add_node("score_candidates", score_candidates)
    graph.add_node("compose_response", compose_response)
    graph.add_node("recommend_node", recommend_node)
    graph.add_node("accommodation_node", accommodation_node)
    graph.add_node("transport_node", transport_node)
    graph.add_node("general_node", general_node)

    graph.add_conditional_edges(
        "route_intent",
        lambda state: state.get("intent", "general"),
        {
            "plan_itinerary":   "plan_node",
            "refine_itinerary": "refine_node",
            "recommend":        "recommend_node",
            "accommodation":    "accommodation_node",
            "transport":        "transport_node",
            "general":          "general_node",
        },
    )

    graph.set_entry_point("route_intent")

    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)
