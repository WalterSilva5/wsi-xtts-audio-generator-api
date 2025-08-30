from pydantic import BaseModel

class TtsDto(BaseModel):
    text: str
    voice: str
    lang_code: str = "en"
