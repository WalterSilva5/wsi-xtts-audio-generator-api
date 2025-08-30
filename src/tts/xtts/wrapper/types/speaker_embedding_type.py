from typing import Any
from dataclasses import dataclass

@dataclass
class SpeakerEmbedding:
    gpt_cond_latent: Any
    speaker_embedding: Any