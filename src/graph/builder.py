"""
Assembles and compiles the LangGraph StateGraph for the triage workflow.
"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.models.state import TriageState
from src.graph.nodes.session_node import start_session_node
from src.graph.nodes.symptom_collector import symptom_collector_node
from src.graph.nodes.rag_retrieval_node import rag_retrieval_node
from src.graph.nodes.urgency_assessor import urgency_assessor_node
from src.graph.nodes.emergency_node import emergency_escalation_node
from src.graph.nodes.escalation_node import escalation_node
from src.graph.nodes.department_router import department_routing_node
from src.graph.nodes.response_composer import response_composer_node
from src.graph.nodes.audit_node import audit_node
from src.graph.edges import route_after_collection, route_after_urgency

from functools import lru_cache


def build_graph():
    """Build and return the compiled triage StateGraph."""
    graph = StateGraph(TriageState)

    # ── Register nodes ────────────────────────────────────────────────────────
    graph.add_node("start_session", start_session_node)
    graph.add_node("collect_symptoms", symptom_collector_node)
    graph.add_node("rag_retrieval", rag_retrieval_node)
    graph.add_node("urgency_assessment", urgency_assessor_node)
    graph.add_node("emergency_node", emergency_escalation_node)
    graph.add_node("escalation_node", escalation_node)
    graph.add_node("department_routing", department_routing_node)
    graph.add_node("compose_response", response_composer_node)
    graph.add_node("audit_log", audit_node)

    # ── Entry point ───────────────────────────────────────────────────────────
    graph.set_entry_point("start_session")

    # ── Fixed edges ───────────────────────────────────────────────────────────
    graph.add_edge("start_session", "collect_symptoms")
    graph.add_edge("rag_retrieval", "urgency_assessment")
    graph.add_edge("emergency_node", "compose_response")
    graph.add_edge("escalation_node", "department_routing")
    graph.add_edge("department_routing", "compose_response")
    graph.add_edge("compose_response", "audit_log")
    graph.add_edge("audit_log", END)

    # ── Conditional edges ─────────────────────────────────────────────────────
    graph.add_conditional_edges(
        "collect_symptoms",
        route_after_collection,
        {
            "collect_symptoms": "collect_symptoms",
            "rag_retrieval": "rag_retrieval",
        },
    )

    graph.add_conditional_edges(
        "urgency_assessment",
        route_after_urgency,
        {
            "emergency_node": "emergency_node",
            "escalation_node": "escalation_node",
            "department_routing": "department_routing",
        },
    )

    # ── Compile with in-memory checkpointer (session state persistence) ───────
    # interrupt_after=["collect_symptoms"] ensures the graph pauses after each
    # symptom collection turn and waits for a new user message — prevents the
    # node from being called multiple times inside a single API request.
    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer, interrupt_after=["collect_symptoms"])


@lru_cache()
def get_compiled_graph():
    """Cached singleton — build the graph once per process."""
    return build_graph()
