from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
import uuid
import secrets


class TriageSession(SQLModel, table=True):
    __tablename__ = "triage_sessions"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    session_id: str = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Patient context — NO PII
    age_group: Optional[str] = None
    gender: Optional[str] = None

    # Symptoms (stored as JSON strings)
    symptoms_extracted: Optional[str] = None   # JSON list
    red_flags: Optional[str] = None            # JSON list

    # Decision
    urgency_level: Optional[str] = None
    urgency_confidence: Optional[float] = None
    urgency_reasoning: Optional[str] = None
    routed_department: Optional[str] = None
    routing_reasoning: Optional[str] = None

    # RAG traceability
    rag_chunks_used: Optional[str] = None      # JSON list of chunk IDs

    # Wait times
    estimated_wait_minutes: Optional[int] = None

    # Safety flags
    emergency_flag: bool = Field(default=False)
    human_review_flag: bool = Field(default=False)

    # LLM metadata
    llm_model_used: Optional[str] = None
    total_llm_calls: int = Field(default=0)

    # Conversation
    conversation_turns: int = Field(default=0)
    full_conversation: Optional[str] = None    # JSON message list


class Appointment(SQLModel, table=True):
    __tablename__ = "appointments"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    session_id: str = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Patient contact
    patient_name: str
    patient_email: str
    patient_phone: str

    # Booking details
    department: str
    doctor_id: str
    doctor_name: str
    doctor_specialization: str
    slot_id: str = Field(index=True)   # unique slot key for dedup
    slot_date: str                      # ISO "2026-04-15"
    slot_time: str                      # "09:30 AM"
    slot_label: str                     # "Tue, Apr 15 at 09:30 AM"

    # Status — starts pending until user clicks email confirmation link
    status: str = Field(default="pending_confirmation")   # pending_confirmation | confirmed | cancelled
    confirmation_code: str = Field(
        default_factory=lambda: secrets.token_hex(3).upper()   # e.g. "A3F9C1"
    )
    confirmation_token: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32)       # for the email link
    )
