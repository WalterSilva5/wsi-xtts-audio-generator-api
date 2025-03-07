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
from typing import Optional
import librosa
import soundfile as sf


class TtsDto(BaseModel):
    text: str
    speaker: str
    rvc_speaker: Optional[str]


router = APIRouter()

# Dependency to get TTS model instance


def get_model_instance():
    # This assumes Model is a singleton or is managed elsewhere in your app
    return Model()


@router.post("/tts")
async def generate_tts(dto: TtsDto, model: Model = Depends(get_model_instance)):
    audio_data = model.tts(dto.text, dto.speaker)
    
    if dto.rvc_speaker:
        rvc_file_path = "/home/wsi/repositorios/GitHub/rvc_test/rvc-cli/"

        # Salvar arquivo de entrada
        with open(rvc_file_path + "input.wav", "wb") as f:
            f.write(audio_data)

        # Executar o RVC
        command = f"cd {rvc_file_path} && {rvc_file_path}venv/bin/python rvc_cli.py infer --input input.wav --output output.wav --pth_path ./models/{dto.rvc_speaker}.pth --index_path ./models/{dto.rvc_speaker}.index"
        os.system(command)

        # Caminho do arquivo gerado pelo RVC
        output_file = os.path.join(rvc_file_path, "output.wav")

        # Retornar diretamente o arquivo gerado pelo RVC
        return FileResponse(
            path=output_file,
            media_type="audio/wav",
            filename="tts_output.wav"
        )

    # Criar arquivo temporário
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
        if isinstance(audio_data, bytes):
            temp_file.write(audio_data)
            temp_file.flush()
        else:
            audio_data = audio_data.reshape(-1, 1) if len(audio_data.shape) == 1 else audio_data
            sf.write(temp_file.name, audio_data, 24000)  # ⚠️ NÃO altera sample rate
    
    # Retornar resposta com áudio processado
    return FileResponse(
        path=temp_file.name,
        media_type="audio/wav",
        filename="tts_output.wav",
        background=BackgroundTask(os.unlink, temp_file.name)
    )



@router.get("/speakers", response_model=dict)
async def get_speakers(model: Model = Depends(get_model_instance)):
    return JSONResponse(content={"speakers": list(model.speaker_embeddings.keys())})