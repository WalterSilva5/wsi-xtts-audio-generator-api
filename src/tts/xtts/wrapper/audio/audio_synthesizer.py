import io
import os
import traceback
from datetime import datetime
from typing import Any, List

import numpy as np
import librosa
import soundfile as sf

from src.tts.xtts.wrapper.model.model_manager import XttsModelManager
from src.tts.xtts.wrapper.speaker_embedding import SpeakerEmbeddingManager
from src.audio.processor import AudioProcessor
from src.tts.xtts.dto.tts_dto import TtsDto
from src.tts.text.chunker import chunk_text, TextChunk, MAX_SECONDS
from src.core.application import Application
from src.utils.clean_memory_after_synthesize import cleanup_memory_after_synthesize as clean_memory

SAMPLE_RATE = 24000

# Pause (ms) inserted between consecutive chunks, chosen by the boundary type of
# the chunk that just finished. Longer after a sentence, shorter after a comma,
# minimal when we were forced to cut mid-phrase. These are NOT crushed by the
# post-processing anymore, so they actually shape the rhythm.
PAUSE_MS = {
    "sentence": int(os.getenv("XTTS_PAUSE_SENTENCE_MS", "300")),
    "clause": int(os.getenv("XTTS_PAUSE_CLAUSE_MS", "150")),
    "word": int(os.getenv("XTTS_PAUSE_WORD_MS", "60")),
}

EDGE_FADE_MS = 8          # tiny fade at each chunk edge to avoid clicks/seams
LEAD_TRAIL_MS = 150       # leading/trailing padding of the final audio
TRIM_TOP_DB = 45          # gentle edge trim (higher = less aggressive)
INTERNAL_SILENCE_CAP_MS = 350  # cap only *pathological* gaps inside a chunk


class AudioSynthesizer:
    """Synthesizes audio with the XTTS model using duration-aware chunking.

    Long inputs are split into ~10-14s chunks (see :mod:`src.tts.text.chunker`),
    synthesized one by one and concatenated with intonation-aware pauses so the
    result keeps a natural rhythm instead of sounding robotic.

    Returns WAV bytes (consumed by both the API and the desktop paths).
    """

    def __init__(
            self,
            tts_processor: XttsModelManager,
            embedding_manager: SpeakerEmbeddingManager):
        self.tts_processor = tts_processor
        self.embedding_manager = embedding_manager
        self.audio_processor = AudioProcessor()
        self.app = Application()

    # -- public ---------------------------------------------------------------

    def synthesize(self, dto: TtsDto) -> bytes:
        """Synthesizes audio from text and returns WAV bytes (or None on error)."""
        voice = dto.voice.lower()
        model = self.tts_processor.get_model()

        if model is None or not dto.voice:
            raise Exception("Model is not loaded or speaker audio file is missing")

        try:
            start_loading = datetime.now()
            speaker_data = self.embedding_manager.get_embedding(voice)
            if not speaker_data:
                raise Exception(f"Speaker embedding not found for {voice}")

            gpt_cond_latent = speaker_data.gpt_cond_latent
            speaker_embedding = speaker_data.speaker_embedding
            print(f"!!! Speaker embedding and GPT latent obtained in {datetime.now() - start_loading}")

            audio = self._synthesize_chunks(dto, gpt_cond_latent, speaker_embedding)
            if audio is None or audio.size == 0:
                return None

            return self._finalize(audio)

        except Exception as e:
            traceback.print_exc()
            print(f"Error during audio synthesis: {e}")
            return None
        finally:
            clean_memory()

    # -- synthesis ------------------------------------------------------------

    def _synthesize_chunks(self, dto: TtsDto, gpt_cond_latent: Any,
                           speaker_embedding: Any) -> np.ndarray:
        model = self.tts_processor.get_model()
        if model is None:
            raise Exception("Model is not loaded")

        chunks: List[TextChunk] = chunk_text(dto.text, speed=dto.speed)
        if not chunks:
            return np.zeros(0, dtype=np.float32)

        print(f"\n\n[chunker] {len(chunks)} chunk(s), target <= {MAX_SECONDS:.0f}s:")
        for i, c in enumerate(chunks):
            print(f"  [{i + 1}/{len(chunks)}] ~{c.est_seconds:.1f}s ({c.boundary}): {c.text!r}")

        segments: List[np.ndarray] = []
        time_before_inference = datetime.now()

        for i, chunk in enumerate(chunks):
            print(f"$$$ ~ Synthesizing chunk {i + 1}/{len(chunks)}")
            output = model.inference(
                text=chunk.text,
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
                # We already chunked to a safe size; let the model render each
                # chunk as one coherent utterance (no internal re-splitting).
                enable_text_splitting=False,
            )

            wav = self._clean_chunk(np.asarray(output["wav"], dtype=np.float32))
            if wav.size == 0:
                continue

            segments.append(wav)
            if i < len(chunks) - 1:
                segments.append(self._silence(PAUSE_MS.get(chunk.boundary, PAUSE_MS["clause"])))

        print(f"\n\n ~ Inference time ({len(chunks)} chunk(s)): {datetime.now() - time_before_inference}")

        if not segments:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(segments).astype(np.float32)

    # -- per-chunk audio cleanup ---------------------------------------------

    def _clean_chunk(self, wav: np.ndarray) -> np.ndarray:
        """Tidy a single chunk: cap pathological gaps, trim edges, add fades."""
        if wav.size == 0:
            return wav

        # Cap only abnormally long internal silences; natural pauses survive.
        try:
            wav = self.audio_processor.remove_excessive_silence(
                wav,
                max_silence_duration=INTERNAL_SILENCE_CAP_MS,
                sample_rate=SAMPLE_RATE,
            )
        except Exception:
            pass

        # Gentle leading/trailing trim of dead air / model artifacts.
        try:
            trimmed = librosa.effects.trim(wav, top_db=TRIM_TOP_DB)[0]
            if trimmed.size > 0:
                wav = trimmed
        except Exception:
            pass

        return self._edge_fades(np.ascontiguousarray(wav, dtype=np.float32), EDGE_FADE_MS)

    def _edge_fades(self, wav: np.ndarray, ms: int) -> np.ndarray:
        n = int(SAMPLE_RATE * ms / 1000)
        if n > 0 and wav.size > 2 * n:
            ramp = np.linspace(0.0, 1.0, n, dtype=np.float32)
            wav[:n] *= ramp
            wav[-n:] *= ramp[::-1]
        return wav

    def _silence(self, ms: int) -> np.ndarray:
        return np.zeros(max(0, int(SAMPLE_RATE * ms / 1000)), dtype=np.float32)

    # -- finalize -------------------------------------------------------------

    def _finalize(self, audio: np.ndarray) -> bytes:
        """Peak-limit, pad and export the assembled audio to WAV bytes."""
        peak = float(np.max(np.abs(audio))) if audio.size else 0.0
        if peak > 1.0:
            audio = (audio / peak) * 0.99

        pad = self._silence(LEAD_TRAIL_MS)
        audio = np.concatenate([pad, audio, pad]).astype(np.float32)

        buffer = io.BytesIO()
        sf.write(buffer, audio, SAMPLE_RATE, format="WAV", subtype="PCM_16")
        buffer.seek(0)
        return buffer.read()
