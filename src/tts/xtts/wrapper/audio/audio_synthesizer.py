import traceback
import io
import re
from typing import Any
import numpy as np
import torch
import torchaudio  # type: ignore
import librosa
from datetime import datetime

from src.tts.xtts.wrapper.model.model_manager import XttsModelManager
from src.tts.xtts.wrapper.speaker_embedding import SpeakerEmbeddingManager
from src.audio.processor import AudioProcessor
from src.tts.xtts.dto.tts_dto import TtsDto
from src.core.application import Application
from src.utils.clean_memory_after_synthesize import cleanup_memory_after_synthesize as clean_memory

class AudioSynthesizer:
    """Responsible for synthesizing audio using the XTTS model"""
    
    def __init__(
            self,
            tts_processor: XttsModelManager,
            embedding_manager: SpeakerEmbeddingManager):
        self.tts_processor = tts_processor
        self.embedding_manager = embedding_manager
        self.audio_processor = AudioProcessor()
        self.app = Application()

    def synthesize(self, dto: TtsDto) -> np.ndarray:
        """Synthesizes audio from text using the XTTS model"""
        voice = dto.voice.lower()
        model = self.tts_processor.get_model()

        if model is None or not dto.voice:
            message = "Model is not loaded or speaker audio file is missing"
            raise Exception(message)

        try:
            start_loading = datetime.now()
            speaker_data = self.embedding_manager.get_embedding(voice)
            if not speaker_data:
                raise Exception(f"Speaker embedding not found for {voice}")

            gpt_cond_latent = speaker_data.gpt_cond_latent
            speaker_embedding = speaker_data.speaker_embedding

            print(f"!!! Speaker embedding and GPT latent obtained in {datetime.now() - start_loading}")
            start_synthesis = datetime.now()
            audio_buffer = self._get_audio(dto, gpt_cond_latent, speaker_embedding)
            print(f"!!! Audio synthesized in {datetime.now() - start_synthesis}")
            audio_buffer = self.apply_silence(audio_buffer, 150)
            return audio_buffer

        except Exception as e:
            traceback.print_exc()
            print(f"Error during audio synthesis: {e}")
        finally:
            clean_memory()

        return None

    def replace_dot_from_sentence(self, text: str) -> str:
        if text.endswith('.'):
            text = text[:-1] + ','
        return text

    def split_sentences(self, text: str) -> list[str]:
        """Splits text into sentences."""
        return re.split(r'(?<=[,\.!;])\s+', text)

    def apply_silence(self, audio_buffer, audioStartEndTime) -> bytes:
        return self.audio_processor.apply_silences(
            audio_buffer,
            start_end_silence=int(audioStartEndTime)
        )
        

    def _get_audio(self, dto: TtsDto, gpt_cond_latent: Any, speaker_embedding: Any) -> np.ndarray:
        """Generates audio from text by processing it sentence by sentence.

        Uses synthesis parameters from dto with sensible defaults:
        - temperature: Controls randomness (0.0-1.0, default 0.65)
        - length_penalty: Penalty for longer sequences (0.5-2.0, default 1.0)
        - repetition_penalty: Penalty for repetition (1.0-20.0, default 12.0)
        - top_k: Top-K sampling (1-100, default 35)
        - top_p: Nucleus sampling threshold (0.0-1.0, default 0.75)
        - speed: Speech speed multiplier (0.5-2.0, default 0.95)
        - do_sample: Enable sampling (default True)
        - enable_text_splitting: Enable text splitting (default True)
        """
        model = self.tts_processor.get_model()
        if model is None:
            raise Exception("Model is not loaded")
        sentences = self.split_sentences(dto.text)
        if not sentences:
            sentences = [dto.text]

        print("\n\ntext sentences:", sentences)
        outputs = np.array([0], dtype=np.float32)  # Initialize as numpy array
        padding = 0.98
        silence_comma = 150
        silence_punctuation = 200
        time_before_inference = datetime.now()

        for sentence in sentences:
            print(f"$$$ ~ Synthesizing sentence: {sentence}")
            # if sentence not ends with ", or ." add a ,
            if not sentence.endswith((",")):
                sentence += ","
            sentence = self.replace_dot_from_sentence(sentence)
            output = model.inference(
                text=sentence,
                language=dto.lang_code,
                gpt_cond_latent=gpt_cond_latent,
                speaker_embedding=speaker_embedding,
                temperature=dto.temperature,
                length_penalty=dto.length_penalty,
                repetition_penalty=dto.repetition_penalty,
                top_k=dto.top_k,
                top_p=dto.top_p,
                do_sample=dto.do_sample,
                speed=dto.speed,
                enable_text_splitting=dto.enable_text_splitting
            )

            split_type = self.get_split_type(sentence)
            silence_duration = silence_comma if split_type == "COMMA" else silence_punctuation
            silence = np.zeros(silence_duration * int(24000 / 1000 * padding))

            audio_trim = librosa.effects.trim(output["wav"], top_db=50)[0]
            outputs = np.concatenate((outputs, audio_trim, silence))

        print(f"\n\n ~ Inference time: {datetime.now() - time_before_inference}")
        return outputs

    def get_split_type(self, text: str) -> str:
        """Determines the split type for the given text."""
        if text.endswith('.'):
            return "PERIOD"
        if text.endswith(','):
            return "COMMA"
        return "NONE"

    def _convert_tensor_to_bytes(self, tensor: torch.Tensor) -> bytes:
        """Converts a PyTorch tensor to WAV bytes"""
        tensor = tensor.cpu()
        buffer = io.BytesIO()
        torchaudio.backend.sox_io_backend.save(buffer, tensor.unsqueeze(0), 24000, format="wav")
        buffer.seek(0)
        return buffer.read()
