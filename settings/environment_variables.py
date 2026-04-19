import typing
import types
from pydantic import BaseModel
import os
import sys
from pathlib import Path


class EnvironmentVariablesDto(BaseModel):
    ENVIRONMENT: str = 'development'
    GPU_TYPE: str = 'nvidia'
    MODEL_VERSION: str = 'v2.0.3'
    MODEL_DIR: str = 'models'
    ROOT_DIR: Path = Path(__file__).parent.parent
    TEMP_DIR: str = 'temp'
    SPEAKERS_DIR: str = 'speakers'


environment_variables = EnvironmentVariablesDto(
    ENVIRONMENT='development',
    GPU_TYPE=os.environ.get('GPU_TYPE', 'nvidia'),
    MODEL_VERSION='v2.0.3',
    MODEL_DIR='models',
    ROOT_DIR=Path(__file__).parent.parent.resolve(),
    TEMP_DIR='temp',
    SPEAKERS_DIR='speakers'
)