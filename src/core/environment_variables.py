from types import SimpleNamespace
from decouple import config#type: ignore


environment_variables = SimpleNamespace(**{
    "AUDIO_FACTOR": config("AUDIO_FACTOR", cast=float, default=0.6),
    "SAMPLE_RATE": config("SAMPLE_RATE", cast=int, default=24000),
    "PORT": config("PORT", cast=int, default=8000),
    "REDIS_HOST": config("REDIS_HOST", default='redis-svc'),
    "REDIS_PORT": config("REDIS_PORT", cast=int, default=6379),
    "LOG_DIR_PATH": config("LOG_DIR_PATH", default="/mnt/data/logs"),
    "LOG_LEVEL": config("LOG_LEVEL", default="INFO"),
    "DEVICE": config("DEVICE", default="gpu"),
    "XTTS_MODEL_FOLDER": config("XTTS_MODEL_FOLDER", default="/mnt/data/models/xtts/"),
    "MODEL_FOLDER": config("MODEL_FOLDER", default="xtts_model/"),
    "MODEL_FILE": config("MODEL_FILE", default="model.pth"),
    "SPEAKERS_FILE": config("SPEAKERS_FILE", default="speakers_xtts.pth"),
    "SAMPLE_SPEAKERS_FOLDER": config("SAMPLE_SPEAKERS_FOLDER", default="speakers_audios/"),
    "VOCAB_FILE": config("VOCAB_FILE", default="vocab.json"),
    "CONFIG_FILE": config("CONFIG_FILE", default="config.json"),
})
