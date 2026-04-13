from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
import uuid


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
