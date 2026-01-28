from typing import Optional
from pydantic import BaseModel, Field


class TtsDto(BaseModel):
    """Data Transfer Object for TTS synthesis requests."""

    # Required fields
    text: str
    voice: str

    # Language
    lang_code: str = "en"

    # Synthesis parameters with sensible defaults
    temperature: float = Field(
        default=0.65,
        ge=0.0,
        le=1.0,
        description="Controls randomness. Lower = more stable, higher = more varied"
    )
    length_penalty: float = Field(
        default=1.0,
        ge=0.5,
        le=2.0,
        description="Penalty for longer sequences. Higher = shorter outputs"
    )
    repetition_penalty: float = Field(
        default=12.0,
        ge=1.0,
        le=20.0,
        description="Penalty for repetition. Higher = less repetitive"
    )
    top_k: int = Field(
        default=35,
        ge=1,
        le=100,
        description="Top-K sampling. Lower = more focused, higher = more diverse"
    )
    top_p: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling threshold. Lower = more focused"
    )
    speed: float = Field(
        default=0.95,
        ge=0.5,
        le=2.0,
        description="Speech speed multiplier. 1.0 = normal speed"
    )
    do_sample: bool = Field(
        default=True,
        description="Enable sampling for more natural output"
    )
    enable_text_splitting: bool = Field(
        default=True,
        description="Enable automatic text splitting for long sentences"
    )
