from pydantic import BaseModel
from fastapi import APIRouter, Response, Depends
from starlette.background import BackgroundTask
import fastapi.responses
from io import BytesIO
import soundfile as sf  # type: ignore
import numpy as np
import tempfile
import os
from src.model.instance.service import Model
from fastapi.responses import FileResponse, JSONResponse


class TtsDto(BaseModel):
    text: str
    speaker: str


router = APIRouter()

# Dependency to get TTS model instance


def get_model_instance():
    # This assumes Model is a singleton or is managed elsewhere in your app
    return Model()


@router.post("/tts")
async def generate_tts(request: TtsDto, model: Model = Depends(get_model_instance)):
    try:
        audio_data = model.tts(request.text, request.speaker)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
        # If audio_data is bytes, write directly to file
        if isinstance(audio_data, bytes):
            temp_file.write(audio_data)
        else:
            if len(audio_data.shape) == 1:
                audio_data = audio_data.reshape(-1, 1)
            sf.write(temp_file.name, audio_data, 24000)
    
    # Return the file response with cleanup task
    return FileResponse(
        path=temp_file.name,
        media_type="audio/wav",
        filename="tts_output.wav",
        background=BackgroundTask(os.unlink, temp_file.name)
    )


@router.get("/speakers", response_model=dict)
async def get_speakers(model: Model = Depends(get_model_instance)):
    return JSONResponse(content={"speakers": list(model.speaker_embeddings.keys())})