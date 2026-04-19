"""
TTS Service - Framework-agnostic interface for TTS operations.
Can be used from Qt UI, CLI, or REST API.
"""
from typing import Optional, List, Callable, Dict, Any
from pathlib import Path
import logging
import shutil
import gc
import io
import os

import numpy as np
import torch

from src.modules.system.torch_util import gpu_is_available, empty_cache

from src.core.models.tts_request import (
    SynthesisRequest,
    SynthesisResult,
    SynthesisStatus,
    Speaker,
    SUPPORTED_LANGUAGES,
)
from src.tts.xtts.manager.tts_manager import TtsManager
from src.tts.xtts.dto.tts_dto import TtsDto


logger = logging.getLogger(__name__)


class TTSService:
    """
    Framework-agnostic TTS service.
    Provides a clean interface for TTS operations.
    """

    def __init__(self):
        self._manager: Optional[TtsManager] = None
        self._is_model_loaded: bool = False
        self._progress_callback: Optional[Callable[[int, str], None]] = None
        self._cancel_requested: bool = False

    def set_progress_callback(self, callback: Callable[[int, str], None]) -> None:
        """
        Set callback for progress updates.

        Args:
            callback: Function that receives (percent: int, message: str)
        """
        self._progress_callback = callback

    def _report_progress(self, percent: int, message: str) -> None:
        """Report progress if callback is set."""
        if self._progress_callback:
            self._progress_callback(percent, message)

    def load_model(self) -> bool:
        """
        Load the TTS model.

        Returns:
            True if model loaded successfully, False otherwise.
        """
        try:
            self._report_progress(0, "Initializing TTS manager...")

            self._manager = TtsManager.get_instance()

            self._report_progress(20, "Loading XTTS model...")

            self._manager.model.load_model()

            self._report_progress(80, "Loading speaker embeddings...")

            # Speakers are loaded as part of model loading

            self._report_progress(100, "Model loaded successfully")

            self._is_model_loaded = True
            return True

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            self._is_model_loaded = False
            return False

    def unload_model(self) -> None:
        """Unload the model and free memory."""
        if self._manager is not None:
            try:
                # Clear references
                self._manager = None
                TtsManager._instance = None

                # Force garbage collection
                gc.collect()

                # Clear CUDA cache if available
                if gpu_is_available():
                    empty_cache()

                self._is_model_loaded = False
                logger.info("Model unloaded successfully")

            except Exception as e:
                logger.error(f"Error unloading model: {e}")

    def is_model_loaded(self) -> bool:
        """Check if the TTS model is loaded."""
        return self._is_model_loaded and self._manager is not None

    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        """
        Synthesize speech from text.

        Args:
            request: SynthesisRequest with text, voice, and parameters.

        Returns:
            SynthesisResult with audio data or error information.
        """
        if not self.is_model_loaded():
            return SynthesisResult(
                status=SynthesisStatus.ERROR,
                error_message="Model not loaded"
            )

        self._cancel_requested = False

        try:
            self._report_progress(0, "Starting synthesis...")

            # Create DTO for the TTS manager with all synthesis parameters
            dto = TtsDto(
                text=request.text,
                voice=request.voice,
                lang_code=request.language,
                temperature=request.temperature,
                length_penalty=request.length_penalty,
                repetition_penalty=request.repetition_penalty,
                top_k=request.top_k,
                top_p=request.top_p,
                speed=request.speed,
                do_sample=request.do_sample,
                enable_text_splitting=request.enable_text_splitting
            )

            self._report_progress(20, "Synthesizing audio...")

            # Check for cancellation
            if self._cancel_requested:
                return SynthesisResult(status=SynthesisStatus.CANCELLED)

            # Perform synthesis
            audio_bytes = self._manager.model.synthesize_audio(dto)

            if audio_bytes is None:
                return SynthesisResult(
                    status=SynthesisStatus.ERROR,
                    error_message="Synthesis returned no audio"
                )

            self._report_progress(80, "Processing audio...")

            # Convert bytes to numpy array
            audio_data = self._bytes_to_numpy(audio_bytes)

            if audio_data is None:
                return SynthesisResult(
                    status=SynthesisStatus.ERROR,
                    error_message="Failed to process audio data"
                )

            # Calculate duration
            sample_rate = 24000  # XTTS default
            duration = len(audio_data) / sample_rate

            self._report_progress(100, "Synthesis complete")

            return SynthesisResult(
                audio_data=audio_data,
                sample_rate=sample_rate,
                duration_seconds=duration,
                status=SynthesisStatus.COMPLETED
            )

        except Exception as e:
            logger.error(f"Synthesis error: {e}")
            return SynthesisResult(
                status=SynthesisStatus.ERROR,
                error_message=str(e)
            )

    def _bytes_to_numpy(self, audio_bytes: io.BytesIO) -> Optional[np.ndarray]:
        """Convert audio bytes (WAV) to numpy array."""
        try:
            import soundfile as sf

            audio_bytes.seek(0)
            audio_data, _ = sf.read(audio_bytes)

            # Ensure float32
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)

            return audio_data

        except Exception as e:
            logger.error(f"Error converting audio bytes: {e}")
            return None

    def list_speakers(self) -> List[str]:
        """Get list of available speaker names."""
        if not self.is_model_loaded():
            return []

        try:
            return self._manager.model.list_speakers()
        except Exception as e:
            logger.error(f"Error listing speakers: {e}")
            return []

    def list_languages(self) -> Dict[str, str]:
        """Get supported languages as {code: name}."""
        return SUPPORTED_LANGUAGES.copy()

    def reload_speakers(self) -> bool:
        """Reload speaker embeddings."""
        if not self.is_model_loaded():
            return False

        try:
            self._manager.model.reload_all_speaker_embeddings()
            return True
        except Exception as e:
            logger.error(f"Error reloading speakers: {e}")
            return False

    def cancel_synthesis(self) -> None:
        """Request cancellation of ongoing synthesis."""
        self._cancel_requested = True

    def get_speaker_info(self, speaker_name: str) -> Optional[Speaker]:
        """Get information about a specific speaker."""
        speakers = self.list_speakers()
        if speaker_name in speakers:
            return Speaker(name=speaker_name)
        return None

    def get_speakers_directory(self) -> str:
        """Get the directory where speaker files are stored."""
        if not self.is_model_loaded():
            return ""
        try:
            return self._manager.model.embedding_manager.get_speakers_dir()
        except Exception as e:
            logger.error(f"Error getting speakers directory: {e}")
            return ""

    def add_speaker(
        self,
        name: str,
        audio_file_path: str,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> bool:
        """
        Add a new speaker from an audio file.

        Args:
            name: Name for the new speaker
            audio_file_path: Path to the source audio file (WAV)
            progress_callback: Optional callback for progress updates

        Returns:
            True if speaker was added successfully
        """
        if not self.is_model_loaded():
            if progress_callback:
                progress_callback(0, "Error: Model not loaded")
            return False

        def report(percent: int, message: str):
            if progress_callback:
                progress_callback(percent, message)

        try:
            report(0, "Validating audio file...")

            # Validate source file
            source_path = Path(audio_file_path)
            if not source_path.exists():
                report(0, f"Error: File not found: {audio_file_path}")
                return False

            if source_path.suffix.lower() != ".wav":
                report(0, "Error: Only WAV files are supported")
                return False

            report(20, "Copying file to speakers directory...")

            # Get speakers directory
            speakers_dir = self.get_speakers_directory()
            if not speakers_dir:
                report(0, "Error: Could not determine speakers directory")
                return False

            # Create speakers directory if needed
            os.makedirs(speakers_dir, exist_ok=True)

            # Sanitize name (remove special characters)
            safe_name = "".join(c for c in name if c.isalnum() or c in "_ -").strip()
            if not safe_name:
                report(0, "Error: Invalid speaker name")
                return False

            # Copy file to speakers directory
            dest_path = Path(speakers_dir) / f"{safe_name}.wav"
            shutil.copy2(source_path, dest_path)

            report(50, "Generating speaker embedding...")

            # Load the speaker embedding
            success = self._manager.model.embedding_manager.add_speaker(
                safe_name,
                str(dest_path)
            )

            if not success:
                # Clean up copied file on failure
                if dest_path.exists():
                    dest_path.unlink()
                report(0, "Error: Failed to generate speaker embedding")
                return False

            report(100, f"Speaker '{safe_name}' added successfully")
            return True

        except Exception as e:
            logger.error(f"Error adding speaker: {e}")
            if progress_callback:
                progress_callback(0, f"Error: {str(e)}")
            return False

    def remove_speaker(self, name: str) -> bool:
        """
        Remove a speaker.

        Args:
            name: Name of the speaker to remove

        Returns:
            True if speaker was removed
        """
        if not self.is_model_loaded():
            return False

        try:
            # Remove embedding from memory
            self._manager.model.embedding_manager.remove_speaker(name)

            # Remove file from disk
            speakers_dir = self.get_speakers_directory()
            if speakers_dir:
                file_path = Path(speakers_dir) / f"{name}.wav"
                if file_path.exists():
                    file_path.unlink()

            return True
        except Exception as e:
            logger.error(f"Error removing speaker: {e}")
            return False


# Singleton instance for easy access
_service_instance: Optional[TTSService] = None


def get_tts_service() -> TTSService:
    """Get or create the singleton TTS service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = TTSService()
    return _service_instance
