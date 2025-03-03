from six import add_metaclass#type: ignore
from typing import Dict, Type
from settings.environment_variables import environment_variables as envs
from typing import Optional, List
from pydantic import BaseModel
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    app_name: str = "Advanced FastAPI Application"
    debug_mode: bool = False
    api_version: str = "v1"
    secret_key: str = "your-super-secret-key"
    allowed_hosts: List[str] = ["*"]

    class Config:
        env_file = ".env"

settings = Settings() 
