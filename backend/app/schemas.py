import datetime
from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict

# User schemas
class UserCreate(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)

# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[int] = None

# Chat Session schemas
class ChatSessionCreate(BaseModel):
    mode: str  # casual, interview, ielts, business, daily

class ChatSessionResponse(BaseModel):
    id: int
    user_id: int
    mode: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)

# Message schemas
class MessageResponse(BaseModel):
    id: int
    session_id: int
    role: str
    original_text: Optional[str] = None
    corrected_text: Optional[str] = None
    explanation: Optional[str] = None
    suggestions: Optional[str] = None
    response_text: str
    grammar_score: Optional[float] = None
    vocabulary_score: Optional[float] = None
    fluency_score: Optional[float] = None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)

# Session detail including messages
class ChatSessionDetail(ChatSessionResponse):
    messages: List[MessageResponse] = []

    model_config = ConfigDict(from_attributes=True)

# Dashboard Stats schemas
class DashboardStats(BaseModel):
    avg_grammar_score: float
    avg_vocabulary_score: float
    avg_fluency_score: float
    total_sessions: int
    total_messages: int
    mode_counts: Dict[str, int]
    score_progress: List[Dict[str, str | float]]
