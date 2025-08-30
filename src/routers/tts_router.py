from src.core.application import Application
from src.tts.xtts.manager.tts_manager import TtsManager
from src.tts.xtts.dto.tts_dto import TtsDto
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
import typing
import io

from pydantic import BaseModel, Field


class TtsRequest(BaseModel):
    # Internally we use `text`/`voice` (same as TtsDto) but accept client aliases
    text: str = Field(..., alias="text_input")
    # voice is required for backward compatibility; default is 'walter' if not provided
    voice: str = Field("voice", alias="voice_name")

    # Other optional client parameters (kept for compatibility, not used internally here)
    response_format: typing.Optional[str] = None
    download_format: typing.Optional[str] = None
    speed: typing.Optional[float] = None
    stream: typing.Optional[bool] = None
    return_download_link: typing.Optional[bool] = None
    lang_code: typing.Optional[str] = Field("en")
    volume_multiplier: typing.Optional[float] = None

    class Config:
        extra = "allow"
        allow_population_by_field_name = True


app = Application()

swagger_tags = ['xtts-synthesizer']

router = APIRouter(
    prefix="/tts",
    tags=swagger_tags
)
stream_manager = TtsManager()

def synthesize_audio(dto: TtsDto) -> bytes:
    return stream_manager.model.synthesize_audio(dto)

@router.post("/synthesize", tags=swagger_tags)
async def synthesize_stream(dto: TtsDto):
    """Synthesize and return WAV audio as a file download (application/octet-stream / audio/wav).

    Returns a StreamingResponse with Content-Disposition set to attachment so clients
    receive a file instead of base64 data.
    """
    audio = synthesize_audio(dto)
    if audio:
        buffer = io.BytesIO(audio)
        buffer.seek(0)
        return StreamingResponse(
            buffer,
            media_type="audio/wav",
            headers={"Content-Disposition": 'attachment; filename="synthesis.wav"'},
        )

    raise HTTPException(status_code=500, detail="Failed to synthesize audio")

@router.get("/voices", tags=swagger_tags, response_model=list[str])
async def list_speakers():
    print(f"instance id: {id(stream_manager)}")
    return stream_manager.model.list_speakers()


@router.post("/audio/speech", tags=swagger_tags)
async def audio_speech(payload: typing.Dict[str, typing.Any]):
    """Compatibility endpoint for external clients.

    Accepts payloads like the NestJS client (keys: text_input, voice_name, response_format, download_format, ...)
    Returns application/json when the model returns JSON, otherwise returns an arraybuffer (audio bytes).
    """
    # Accept flexible client payloads (legacy keys like 'input'/'voice') and normalize
    data = dict(payload or {})

    # map legacy keys to the Pydantic aliases expected by TtsRequest
    if 'input' in data and 'text_input' not in data and 'text' not in data:
        data['text_input'] = data.pop('input')
    if 'voice' in data and 'voice_name' not in data and 'voice' not in data:
        data['voice_name'] = data.pop('voice')

    try:
        request = TtsRequest.parse_obj(data)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    text = request.text
    voice = request.voice

    if not text:
        raise HTTPException(status_code=400, detail="Missing 'input' (text) in request payload")

    dto = TtsDto(text=text, voice=voice)

    audio = synthesize_audio(dto)

    # If model returns JSON-like response, forward as JSON
    if isinstance(audio, dict):
        return JSONResponse(content=audio)

    if isinstance(audio, (bytes, bytearray)):
        # Always return WAV bytes (no format conversion) to remain compatible with the client
        buffer = io.BytesIO(audio)
        buffer.seek(0)
        return StreamingResponse(
            buffer,
            media_type="audio/wav",
            headers={"Content-Disposition": 'attachment; filename="synthesis.wav"'},
        )

    raise HTTPException(status_code=500, detail="Failed to synthesize audio")
