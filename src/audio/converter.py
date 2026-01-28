"""Audio format converter utilities."""
import io
from typing import Literal
from pydub import AudioSegment

AudioFormat = Literal["wav", "mp3", "ogg", "flac"]

SUPPORTED_FORMATS = ["wav", "mp3", "ogg", "flac"]


def convert_audio(
    audio_bytes: bytes,
    output_format: AudioFormat,
    sample_rate: int = 24000
) -> bytes:
    """Convert WAV audio bytes to the specified format.

    Args:
        audio_bytes: Input audio as WAV bytes
        output_format: Target format (wav, mp3, ogg, flac)
        sample_rate: Sample rate of the input audio

    Returns:
        Converted audio bytes
    """
    if output_format == "wav":
        return audio_bytes

    audio = AudioSegment.from_wav(io.BytesIO(audio_bytes))

    buffer = io.BytesIO()

    export_params = {}
    if output_format == "mp3":
        export_params = {"format": "mp3", "bitrate": "192k"}
    elif output_format == "ogg":
        export_params = {"format": "ogg", "codec": "libvorbis"}
    elif output_format == "flac":
        export_params = {"format": "flac"}

    audio.export(buffer, **export_params)
    buffer.seek(0)
    return buffer.read()


def get_mime_type(audio_format: AudioFormat) -> str:
    """Get MIME type for audio format."""
    mime_types = {
        "wav": "audio/wav",
        "mp3": "audio/mpeg",
        "ogg": "audio/ogg",
        "flac": "audio/flac"
    }
    return mime_types.get(audio_format, "audio/wav")


def estimate_duration_seconds(text: str, speed: float = 1.0) -> float:
    """Estimate audio duration based on text length.

    Uses average speech rate of ~150 words per minute (2.5 words/sec).
    Adjusts for pauses at punctuation marks.

    Args:
        text: Text to synthesize
        speed: Speed multiplier (1.0 = normal)

    Returns:
        Estimated duration in seconds
    """
    words = len(text.split())
    sentences = text.count('.') + text.count('!') + text.count('?') + 1

    words_per_second = 2.5 * speed
    base_duration = words / words_per_second

    pause_duration = sentences * 0.3

    return round(base_duration + pause_duration, 2)
