from typing import Dict, Type
from settings.environment_variables import environment_variables as envs, EnvironmentVariablesDto
from typing import Optional, List
from pydantic import BaseModel

class Singleton(type):
    _instances: Dict[Type, Type] = {}
    
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Settings(BaseModel):
    app_name: str = "Advanced FastAPI Application"
    debug_mode: bool = False
    api_version: str = "v1"
    secret_key: str = "your-super-secret-key"
    allowed_hosts: List[str] = ["*"]
    envs: EnvironmentVariablesDto = envs

settings = Settings()