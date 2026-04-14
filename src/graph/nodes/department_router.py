from langchain_core.messages import SystemMessage, HumanMessage
from src.models.state import TriageState
from src.models.schemas import DepartmentRouting
from src.config.prompts import DEPARTMENT_ROUTER_SYSTEM
from src.llm.client import get_llm
from src.llm.structured_output import parse_structured_output
import logging

logger = logging.getLogger(__name__)


async def department_routing_node(state: TriageState) -> dict:
    """Route patient to the appropriate hospital department."""
    llm = get_llm()

    symptoms = state.get("extracted_symptoms", [])
    age_group = state.get("patient_age_group", "unknown")
    urgency = state.get("urgency_level", "NON_URGENT")
    rag_context = state.get("rag_context", [])

    rag_text = ""
    if rag_context:
        rag_text = "\n\nRELEVANT PROTOCOL CONTEXT:\n"
        for chunk in rag_context[:3]:
            text = chunk.get('text', '')[:600]
            rag_text += f"- {text}\n"

    prompt = (
        f"PATIENT SYMPTOMS: {', '.join(symptoms) if symptoms else 'not specified'}\n"
        f"AGE GROUP: {age_group}\n"
        f"URGENCY LEVEL: {urgency}\n"
        f"SYMPTOM DURATION: {state.get('symptom_duration') or 'not specified'}\n"
        f"SELF-REPORTED SEVERITY: {str(state.get('symptom_severity')) + '/10' if state.get('symptom_severity') else 'not specified'}\n"
        f"{rag_text}\n"
        f"Which department should this patient visit? Choose the single most appropriate department."
    )

    messages = [
        SystemMessage(content=DEPARTMENT_ROUTER_SYSTEM),
        HumanMessage(content=prompt),
    ]

    try:
        response = await llm.ainvoke(messages)
        routing = parse_structured_output(response.content, DepartmentRouting)

        return {
            "routed_department": routing.department.value,
            "routing_reasoning": routing.reasoning,
        }

    except Exception as e:
        logger.error(f"department_routing error: {e} — defaulting to General Medicine")
        return {
            "routed_department": "General Medicine",
            "routing_reasoning": "Routing failed — defaulting to General Medicine for assessment",
        }
