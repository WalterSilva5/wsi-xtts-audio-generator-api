from src.core.application import Application
from src.tts.xtts.manager.tts_manager import TtsManager
from src.tts.xtts.dto.tts_dto import TtsDto
from src.audio.converter import (
    convert_audio, get_mime_type, estimate_duration_seconds,
    SUPPORTED_FORMATS, AudioFormat
)
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
import typing
import io
import os
import tempfile
import shutil
from datetime import datetime

from pydantic import BaseModel, Field


class TtsRequest(BaseModel):
    # Internally we use `text`/`voice` (same as TtsDto) but accept client aliases
    text: str = Field(..., alias="text_input")
    # voice is required for backward compatibility; default is 'walter' if not provided
    voice: str = Field("voice", alias="voice_name")

    # Other optional client parameters (kept for compatibility, not used internally here)
    response_format: typing.Optional[str] = None
    download_format: typing.Optional[str] = None
    stream: typing.Optional[bool] = None
    return_download_link: typing.Optional[bool] = None
    lang_code: typing.Optional[str] = Field("en")
    volume_multiplier: typing.Optional[float] = None

    # Synthesis parameters (passed to TtsDto)
    temperature: typing.Optional[float] = Field(default=0.65, ge=0.0, le=1.0)
    length_penalty: typing.Optional[float] = Field(default=1.0, ge=0.5, le=2.0)
    repetition_penalty: typing.Optional[float] = Field(default=12.0, ge=1.0, le=20.0)
    top_k: typing.Optional[int] = Field(default=35, ge=1, le=100)
    top_p: typing.Optional[float] = Field(default=0.75, ge=0.0, le=1.0)
    speed: typing.Optional[float] = Field(default=0.95, ge=0.5, le=2.0)
    do_sample: typing.Optional[bool] = Field(default=True)
    enable_text_splitting: typing.Optional[bool] = Field(default=True)

    # Output format (wav, mp3, ogg, flac)
    output_format: typing.Optional[str] = Field(default="wav")

    class Config:
        extra = "allow"
        allow_population_by_field_name = True


class BatchSynthesisItem(BaseModel):
    """Single item in a batch synthesis request."""
    text: str
    voice: typing.Optional[str] = None
    lang_code: typing.Optional[str] = None


class BatchSynthesisRequest(BaseModel):
    """Batch synthesis request model."""
    items: typing.List[BatchSynthesisItem]
    default_voice: str = "voice"
    default_lang_code: str = "en"
    output_format: str = "wav"


class BatchSynthesisResult(BaseModel):
    """Result for a single batch item."""
    index: int
    success: bool
    text: str
    error: typing.Optional[str] = None
    duration_seconds: typing.Optional[float] = None


class BatchSynthesisResponse(BaseModel):
    """Batch synthesis response model."""
    total: int
    successful: int
    failed: int
    results: typing.List[BatchSynthesisResult]


class DurationEstimateRequest(BaseModel):
    """Request for duration estimation."""
    text: str
    speed: float = Field(default=1.0, ge=0.5, le=2.0)


class DurationEstimateResponse(BaseModel):
    """Response for duration estimation."""
    text_length: int
    word_count: int
    estimated_duration_seconds: float
    estimated_duration_formatted: str


class ModelInfoResponse(BaseModel):
    """Model information response."""
    model_loaded: bool
    model_version: typing.Optional[str] = None
    device: typing.Optional[str] = None
    speakers_count: int = 0
    supported_languages: typing.List[str] = []
    supported_formats: typing.List[str] = SUPPORTED_FORMATS


class AddSpeakerResponse(BaseModel):
    """Response for add speaker endpoint."""
    success: bool
    speaker_name: str
    message: str


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

    dto = TtsDto(
        text=text,
        voice=voice,
        lang_code=request.lang_code or "en",
        temperature=request.temperature,
        length_penalty=request.length_penalty,
        repetition_penalty=request.repetition_penalty,
        top_k=request.top_k,
        top_p=request.top_p,
        speed=request.speed,
        do_sample=request.do_sample,
        enable_text_splitting=request.enable_text_splitting
    )

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


# ==================== NEW ENDPOINTS ====================

SUPPORTED_LANGUAGES = [
    "en", "pt", "es", "fr", "de", "it", "pl", "tr",
    "ru", "nl", "cs", "ar", "zh-cn", "ja", "ko", "hu"
]


@router.get("/model/info", tags=swagger_tags, response_model=ModelInfoResponse)
async def get_model_info():
    """Get information about the loaded model and its capabilities."""
    model_loaded = stream_manager.model.model_manager.is_loaded()

    response = ModelInfoResponse(
        model_loaded=model_loaded,
        supported_languages=SUPPORTED_LANGUAGES,
        supported_formats=SUPPORTED_FORMATS
    )

    if model_loaded:
        response.speakers_count = len(stream_manager.model.list_speakers())
        response.device = str(stream_manager.model.model_manager.device)
        response.model_version = "XTTS v2"

    return response


@router.post("/synthesize/with-format", tags=swagger_tags)
async def synthesize_with_format(dto: TtsDto, output_format: str = "wav"):
    """Synthesize audio and return in the specified format (wav, mp3, ogg, flac)."""
    if output_format not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {output_format}. Supported: {SUPPORTED_FORMATS}"
        )

    audio = synthesize_audio(dto)
    if not audio:
        raise HTTPException(status_code=500, detail="Failed to synthesize audio")

    converted = convert_audio(audio, output_format)
    buffer = io.BytesIO(converted)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type=get_mime_type(output_format),
        headers={"Content-Disposition": f'attachment; filename="synthesis.{output_format}"'},
    )


@router.post("/estimate-duration", tags=swagger_tags, response_model=DurationEstimateResponse)
async def estimate_duration(request: DurationEstimateRequest):
    """Estimate the duration of the synthesized audio without actually generating it."""
    text = request.text
    speed = request.speed

    duration = estimate_duration_seconds(text, speed)
    minutes = int(duration // 60)
    seconds = int(duration % 60)
    formatted = f"{minutes:02d}:{seconds:02d}"

    return DurationEstimateResponse(
        text_length=len(text),
        word_count=len(text.split()),
        estimated_duration_seconds=duration,
        estimated_duration_formatted=formatted
    )


@router.post("/speakers/add", tags=swagger_tags, response_model=AddSpeakerResponse)
async def add_speaker(
    speaker_name: str = Form(..., description="Name for the new speaker/voice"),
    audio_file: UploadFile = File(..., description="WAV audio file (10-30 seconds recommended)")
):
    """Add a new speaker/voice from an uploaded audio file.

    The audio file should be:
    - WAV format
    - 10-30 seconds of clear speech
    - Good audio quality (no background noise)
    """
    if not audio_file.filename.lower().endswith('.wav'):
        raise HTTPException(
            status_code=400,
            detail="Only WAV files are supported. Please upload a .wav file."
        )

    speakers_dir = stream_manager.model.embedding_manager.get_speakers_dir()

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            temp_path = temp_file.name
            content = await audio_file.read()
            temp_file.write(content)

        success = stream_manager.model.embedding_manager.add_speaker(
            speaker_name=speaker_name,
            audio_path=temp_path
        )

        if success:
            dest_path = os.path.join(speakers_dir, f"{speaker_name.lower()}.wav")
            shutil.copy2(temp_path, dest_path)

            return AddSpeakerResponse(
                success=True,
                speaker_name=speaker_name,
                message=f"Speaker '{speaker_name}' added successfully"
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process audio for speaker '{speaker_name}'"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


@router.delete("/speakers/{speaker_name}", tags=swagger_tags)
async def remove_speaker(speaker_name: str):
    """Remove a speaker/voice.

    Note: This only removes from memory. The audio file is not deleted.
    """
    success = stream_manager.model.embedding_manager.remove_speaker(speaker_name)

    if success:
        return {"success": True, "message": f"Speaker '{speaker_name}' removed"}
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Speaker '{speaker_name}' not found"
        )


@router.post("/speakers/reload", tags=swagger_tags)
async def reload_speakers():
    """Reload all speaker embeddings from the speakers directory."""
    stream_manager.model.reload_all_speaker_embeddings()
    speakers = stream_manager.model.list_speakers()

    return {
        "success": True,
        "message": "Speakers reloaded successfully",
        "speakers_count": len(speakers),
        "speakers": speakers
    }


@router.post("/batch/synthesize", tags=swagger_tags)
async def batch_synthesize(request: BatchSynthesisRequest):
    """Synthesize multiple texts in a single request.

    Returns a ZIP file containing all generated audio files.
    """
    import zipfile

    results = []
    audio_files = []

    for idx, item in enumerate(request.items):
        voice = item.voice or request.default_voice
        lang_code = item.lang_code or request.default_lang_code

        try:
            dto = TtsDto(
                text=item.text,
                voice=voice,
                lang_code=lang_code
            )

            audio = synthesize_audio(dto)
            if audio:
                converted = convert_audio(audio, request.output_format)
                audio_files.append((f"audio_{idx:03d}.{request.output_format}", converted))

                results.append(BatchSynthesisResult(
                    index=idx,
                    success=True,
                    text=item.text[:50] + "..." if len(item.text) > 50 else item.text,
                    duration_seconds=estimate_duration_seconds(item.text)
                ))
            else:
                results.append(BatchSynthesisResult(
                    index=idx,
                    success=False,
                    text=item.text[:50] + "..." if len(item.text) > 50 else item.text,
                    error="Synthesis returned empty audio"
                ))

        except Exception as e:
            results.append(BatchSynthesisResult(
                index=idx,
                success=False,
                text=item.text[:50] + "..." if len(item.text) > 50 else item.text,
                error=str(e)
            ))

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for filename, audio_data in audio_files:
            zip_file.writestr(filename, audio_data)

        import json
        manifest = {
            "total": len(request.items),
            "successful": sum(1 for r in results if r.success),
            "failed": sum(1 for r in results if not r.success),
            "results": [r.dict() for r in results]
        }
        zip_file.writestr("manifest.json", json.dumps(manifest, indent=2))

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="batch_synthesis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip"'
        }
    )


@router.get("/languages", tags=swagger_tags)
async def list_languages():
    """List all supported languages with their codes and names."""
    languages = [
        {"code": "en", "name": "English"},
        {"code": "pt", "name": "Portuguese"},
        {"code": "es", "name": "Spanish"},
        {"code": "fr", "name": "French"},
        {"code": "de", "name": "German"},
        {"code": "it", "name": "Italian"},
        {"code": "pl", "name": "Polish"},
        {"code": "tr", "name": "Turkish"},
        {"code": "ru", "name": "Russian"},
        {"code": "nl", "name": "Dutch"},
        {"code": "cs", "name": "Czech"},
        {"code": "ar", "name": "Arabic"},
        {"code": "zh-cn", "name": "Chinese (Simplified)"},
        {"code": "ja", "name": "Japanese"},
        {"code": "ko", "name": "Korean"},
        {"code": "hu", "name": "Hungarian"},
    ]
    return {"languages": languages, "count": len(languages)}


@router.get("/formats", tags=swagger_tags)
async def list_formats():
    """List all supported audio output formats."""
    formats = [
        {"format": "wav", "mime_type": "audio/wav", "description": "Uncompressed, highest quality"},
        {"format": "mp3", "mime_type": "audio/mpeg", "description": "Compressed, good quality, small size"},
        {"format": "ogg", "mime_type": "audio/ogg", "description": "Open format, good compression"},
        {"format": "flac", "mime_type": "audio/flac", "description": "Lossless compression"},
    ]
    return {"formats": formats, "count": len(formats)}
