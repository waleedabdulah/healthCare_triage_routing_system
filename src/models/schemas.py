from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class UrgencyLevel(str, Enum):
    EMERGENCY = "EMERGENCY"
    URGENT = "URGENT"
    NON_URGENT = "NON_URGENT"
    SELF_CARE = "SELF_CARE"


class Department(str, Enum):
    ER = "Emergency Room"
    CARDIOLOGY = "Cardiology"
    NEUROLOGY = "Neurology"
    ENT = "ENT"
    DERMATOLOGY = "Dermatology"
    GASTROENTEROLOGY = "Gastroenterology"
    PULMONOLOGY = "Pulmonology"
    ORTHOPEDICS = "Orthopedics"
    OPHTHALMOLOGY = "Ophthalmology"
    GYNECOLOGY = "Gynecology"
    UROLOGY = "Urology"
    PSYCHIATRY = "Psychiatry"
    GENERAL_MEDICINE = "General Medicine"
    PEDIATRICS = "Pediatrics"


class UrgencyAssessment(BaseModel):
    """Structured output from the urgency_assessor node."""
    urgency: UrgencyLevel
    confidence: float = Field(ge=0.0, le=1.0)
    red_flags: list[str] = Field(default_factory=list)
    reasoning: str = Field(
        description="Symptom-based reasoning. Must NOT mention any diagnosis or condition name."
    )


class DepartmentRouting(BaseModel):
    """Structured output from the department_router node."""
    department: Department
    reasoning: str = Field(
        description="Why these symptoms map to this department. No diagnosis."
    )


class SymptomExtraction(BaseModel):
    """Structured output from the symptom_collector node."""
    symptoms: list[str]
    duration: Optional[str] = None
    severity: Optional[int] = Field(default=None, ge=1, le=10)
    age_group: Optional[str] = None      # child | adult | elderly
    gender: Optional[str] = None
    red_flags: list[str] = Field(default_factory=list)
    ready_for_triage: bool = False        # True when enough info collected
    message: Optional[str] = None        # Patient-facing question/response


# ── API schemas ───────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    age_group: Optional[str] = None


class TriageResultResponse(BaseModel):
    session_id: str
    urgency_level: Optional[str]
    routed_department: Optional[str]
    estimated_wait_minutes: Optional[int]
    next_available_slot: Optional[str]
    final_response: str
    is_emergency: bool
