import os
from typing import Dict, Optional
from TTS.tts.models.xtts import Xtts #type: ignore
from src.tts.xtts.wrapper.types.speaker_embedding_type import SpeakerEmbedding
from src.tts.xtts.wrapper.model_wrapper_paths import ModelWrapperPaths
from src.core.application import Application

class SpeakerEmbeddingManager():
    """Default implementation of the speaker embedding manager."""
    def __init__(self, model: Xtts, model_paths: ModelWrapperPaths):
        self.model = model
        self.model_paths = model_paths
        self.app = Application()
        self._embeddings: Dict[str, SpeakerEmbedding] = {}

    def get_embedding(self, speaker: str) -> Optional[SpeakerEmbedding]:
        """Returns the speaker embedding for the given speaker."""
        return self._embeddings.get(speaker.lower())

    def load_embeddings(self) -> None:
        """Loads all speaker embeddings."""
        print("\n\n\nLoading speaker embeddings")
        self._embeddings = self.get_all_embeddings()

    def get_all_embeddings(self) -> Dict[str, SpeakerEmbedding]:
        """Returns all speaker embeddings."""
        embeddings = {}
        speakers_files = self.list_speakers()
        for speaker_path in speakers_files:
            speaker = os.path.splitext(os.path.basename(speaker_path))[0].lower()
            gpt_cond_latent, speaker_embedding = self.model.get_conditioning_latents(
                audio_path=speaker_path,
                gpt_cond_len=self.model.config.gpt_cond_len,
                max_ref_length=self.model.config.max_ref_len,
                sound_norm_refs=self.model.config.sound_norm_refs
            )
            embeddings[speaker] = SpeakerEmbedding(
                gpt_cond_latent=gpt_cond_latent,
                speaker_embedding=speaker_embedding
            )
        return embeddings

    def list_speakers(self) -> list[str]:
        """Lists all speakers."""
        speakers: list[str] = []
        if not os.path.exists(self.model_paths.speakers_dir_path):
            print(f"Speakers folder not found: {self.model_paths.speakers_dir_path}")
            return speakers
        for file in os.listdir(self.model_paths.speakers_dir_path):
            if file.endswith(".wav"):
                speakers.append(os.path.join(self.model_paths.speakers_dir_path, file))
        return speakers

    def add_speaker(self, speaker_name: str, audio_path: str) -> bool:
        """Adds a new speaker embedding from an audio file.

        Args:
            speaker_name: Name for the new speaker
            audio_path: Path to the WAV audio file

        Returns:
            True if speaker was added successfully
        """
        speaker_key = speaker_name.lower()

        if speaker_key in self._embeddings:
            print(f"Speaker '{speaker_name}' already exists, updating embedding...")

        try:
            gpt_cond_latent, speaker_embedding = self.model.get_conditioning_latents(
                audio_path=audio_path,
                gpt_cond_len=self.model.config.gpt_cond_len,
                max_ref_length=self.model.config.max_ref_len,
                sound_norm_refs=self.model.config.sound_norm_refs
            )
            self._embeddings[speaker_key] = SpeakerEmbedding(
                gpt_cond_latent=gpt_cond_latent,
                speaker_embedding=speaker_embedding
            )
            print(f"Speaker '{speaker_name}' added successfully")
            return True
        except Exception as e:
            print(f"Error adding speaker '{speaker_name}': {e}")
            return False

    def remove_speaker(self, speaker_name: str) -> bool:
        """Removes a speaker embedding.

        Args:
            speaker_name: Name of the speaker to remove

        Returns:
            True if speaker was removed
        """
        speaker_key = speaker_name.lower()
        if speaker_key in self._embeddings:
            del self._embeddings[speaker_key]
            return True
        return False

    def get_speakers_dir(self) -> str:
        """Returns the speakers directory path."""
        return self.model_paths.speakers_dir_path

class SpeakerEmbeddingFactory:
    """Factory for creating speaker embedding managers."""
    @staticmethod
    def create_manager(
        manager_type: str, model: Xtts,
        model_paths: ModelWrapperPaths) -> SpeakerEmbeddingManager:
        """Creates a speaker embedding manager of the specified type."""
        print(f"Creating speaker embedding manager of type: {manager_type}")
        if manager_type == "default":
            return SpeakerEmbeddingManager(model, model_paths)
        raise ValueError(f"Unknown manager type: {manager_type}")
