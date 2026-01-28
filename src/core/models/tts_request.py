"""
TTS Request and Response models.
"""
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import numpy as np


class SynthesisStatus(Enum):
    """Status of a synthesis operation."""
    IDLE = "idle"
    LOADING_MODEL = "loading_model"
    SYNTHESIZING = "synthesizing"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class SynthesisRequest:
    """Request for TTS synthesis.

    Attributes:
        text: Text to synthesize
        voice: Speaker/voice name
        language: Language code (default: "en")
        speed: Speech speed multiplier 0.5-2.0 (default: 0.95)
        temperature: Randomness control 0.0-1.0 (default: 0.65)
        top_k: Top-K sampling 1-100 (default: 35)
        top_p: Nucleus sampling 0.0-1.0 (default: 0.75)
        repetition_penalty: Repetition penalty 1.0-20.0 (default: 12.0)
        length_penalty: Length penalty 0.5-2.0 (default: 1.0)
        do_sample: Enable sampling (default: True)
        enable_text_splitting: Enable text splitting (default: True)
    """
    text: str
    voice: str
    language: str = "en"
    speed: float = 0.95
    temperature: float = 0.65
    top_k: int = 35
    top_p: float = 0.75
    repetition_penalty: float = 12.0
    length_penalty: float = 1.0
    do_sample: bool = True
    enable_text_splitting: bool = True


@dataclass
class SynthesisResult:
    """Result of TTS synthesis."""
    audio_data: Optional[np.ndarray] = None
    sample_rate: int = 24000
    duration_seconds: float = 0.0
    status: SynthesisStatus = SynthesisStatus.IDLE
    error_message: Optional[str] = None

    @property
    def is_success(self) -> bool:
        return self.status == SynthesisStatus.COMPLETED and self.audio_data is not None


@dataclass
class Speaker:
    """Speaker/voice model."""
    name: str
    file_path: Optional[str] = None
    is_builtin: bool = False

    def __str__(self) -> str:
        return self.name


# Supported languages with their codes
SUPPORTED_LANGUAGES = {
    "en": "English",
    "pt": "Portuguese",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pl": "Polish",
    "tr": "Turkish",
    "ru": "Russian",
    "nl": "Dutch",
    "cs": "Czech",
    "ar": "Arabic",
    "zh-cn": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "hu": "Hungarian",
}
