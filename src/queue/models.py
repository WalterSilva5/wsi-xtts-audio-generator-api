"""Queue task models."""
import uuid
from enum import Enum
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Status of a queue task."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    """Type of queue task."""
    SYNTHESIS = "synthesis"
    BATCH_SYNTHESIS = "batch_synthesis"


class SynthesisTaskPayload(BaseModel):
    """Payload for a synthesis task."""
    text: str
    voice: str = "voice"
    lang_code: str = "en"
    output_format: str = "wav"
    temperature: float = 0.65
    length_penalty: float = 1.0
    repetition_penalty: float = 12.0
    top_k: int = 35
    top_p: float = 0.75
    speed: float = 0.95
    do_sample: bool = True
    enable_text_splitting: bool = True


class QueueTask(BaseModel):
    """A task in the queue."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_type: TaskType
    status: TaskStatus = TaskStatus.PENDING
    payload: Dict[str, Any]
    result_file: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0

    class Config:
        use_enum_values = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = self.dict()
        data['created_at'] = self.created_at.isoformat() if self.created_at else None
        data['started_at'] = self.started_at.isoformat() if self.started_at else None
        data['completed_at'] = self.completed_at.isoformat() if self.completed_at else None
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueueTask":
        """Create from dictionary."""
        if data.get('created_at') and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('started_at') and isinstance(data['started_at'], str):
            data['started_at'] = datetime.fromisoformat(data['started_at'])
        if data.get('completed_at') and isinstance(data['completed_at'], str):
            data['completed_at'] = datetime.fromisoformat(data['completed_at'])
        return cls(**data)


class TaskResponse(BaseModel):
    """Response model for task status."""
    id: str
    task_type: str
    status: str
    progress: float
    result_file: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    estimated_wait_seconds: Optional[float] = None


class QueueStats(BaseModel):
    """Queue statistics."""
    total_tasks: int
    pending: int
    processing: int
    completed: int
    failed: int
    cancelled: int
    consumer_running: bool
