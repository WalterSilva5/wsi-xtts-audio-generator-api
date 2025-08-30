from src.core.application import Application
import contextlib
import io
import librosa
import soundfile as sf
import numpy as np

app = Application()

def compress_audio(data: bytes, audio_factor: float, sample_rate: int = 8000, bit_rate: int = 128000, subtype='ALAW') -> bytes:
    """Compress audio data and adjust volume based on audio_factor."""
    subtype = 'ALAW'  # deve se manter fixo
    print("audio_factor: ", audio_factor, " ~ sample_rate: ", sample_rate, " ~ bit_rate: ", bit_rate, " ~ subtype: ", subtype)
    app.logger.info(f"\n\nCompressing wav data with audio factor {audio_factor}")

    # Carregar o áudio
    audio_data, sr = librosa.load(io.BytesIO(data), sr=sample_rate, mono=True)

    # Calcular o volume atual do áudio
    max_val = np.max(np.abs(audio_data))
    current_db = 20 * np.log10(max_val) if max_val > 0 else -np.inf
    app.logger.info(f"Current max volume: {current_db} dB")

    # O volume máximo desejado (em amplitude) deve ser igual a audio_factor
    limit = audio_factor  # O valor de audio_factor já está em [0.0, 1.0]

    # Se o volume máximo atual for maior que o limite, ajuste
    if max_val > limit:
        scale_factor = limit / max_val
        audio_data *= scale_factor
        app.logger.info(f"Applied scaling factor: {scale_factor} to limit audio to {limit}")

    # Recalcular o volume máximo após o ajuste
    final_max_val = np.max(np.abs(audio_data))
    final_adjusted_db = 20 * np.log10(final_max_val) if final_max_val > 0 else -np.inf
    app.logger.info(f"Final max volume after adjustments: {final_adjusted_db} dB")

    # Gravar o áudio comprimido no formato especificado
    with contextlib.closing(io.BytesIO()) as compressed_output:
        sf.write(compressed_output, audio_data, sr, subtype=subtype.upper(), format='WAV')
        compressed_output.seek(0)
        return compressed_output.getvalue()
