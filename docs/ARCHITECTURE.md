# Mapeamento da Aplicação XTTS-API

## Visão Geral

API de Text-to-Speech (TTS) baseada no modelo XTTS v2 da Coqui, construída com FastAPI e PyTorch.

---

## Estrutura de Diretórios

```text
xtts-api/
├── main.py                    # Entry point - FastAPI + Uvicorn (porta 8880)
├── requirements.txt           # Dependências
├── settings/                  # Configurações
│   ├── settings.py           # App settings (debug, versão, hosts)
│   └── environment_variables.py  # Variáveis de ambiente
├── models/                    # Arquivos do modelo XTTS
│   └── v2.0.3/               # model.pth, config.json, vocab.json
├── speakers/                  # Áudios de referência de vozes
└── src/                       # Código fonte principal
    ├── audio/                # Processamento de áudio
    ├── core/                 # Aplicação e logging
    ├── middleware/           # CORS e exceções
    ├── modules/              # Padrões de design (singleton, utils)
    ├── observers/            # Padrão Observer
    ├── routers/              # Endpoints da API
    ├── tts/                  # Motor TTS (XTTS)
    └── utils/                # Utilitários
```

---

## Módulos Principais

### 1. Entry Point (`main.py`)

- Inicializa FastAPI com Uvicorn
- Carrega modelo XTTS no startup via lifespan
- Configura middlewares e routers
- Documentação em `/docs` e `/redoc`

### 2. TTS Engine (`src/tts/xtts/`)

```text
TtsManager (Singleton, Observable)
    └── ModelWrapper (Facade)
            ├── XttsModelManager    → Ciclo de vida do modelo
            ├── SpeakerEmbeddingManager → Embeddings de voz
            └── AudioSynthesizer    → Síntese de áudio
```

| Componente                  | Arquivo                              | Responsabilidade                    |
| --------------------------- | ------------------------------------ | ----------------------------------- |
| **TtsManager**              | `manager/tts_manager.py`             | Singleton central, gerencia ModelWrapper |
| **ModelWrapper**            | `wrapper/model_wrapper.py`           | Facade para subsistemas TTS         |
| **XttsModelManager**        | `wrapper/model/model_manager.py`     | Carrega/descarrega modelo XTTS      |
| **SpeakerEmbeddingManager** | `wrapper/speaker_embedding.py`       | Gerencia embeddings de speakers     |
| **AudioSynthesizer**        | `wrapper/audio/audio_synthesizer.py` | Síntese texto → áudio               |

### 3. Processamento de Áudio (`src/audio/`)

| Componente         | Arquivo        | Responsabilidade                          |
| ------------------ | -------------- | ----------------------------------------- |
| **AudioProcessor** | `processor.py` | Remoção de silêncio, padding, conversão WAV |
| **Compress**       | `compress.py`  | Compressão de áudio                       |

### 4. API Layer (`src/routers/`)

| Endpoint           | Método | Descrição                     |
| ------------------ | ------ | ----------------------------- |
| `/tts/synthesize`  | POST   | Sintetiza áudio (retorna WAV) |
| `/tts/voices`      | GET    | Lista vozes disponíveis       |
| `/tts/audio/speech`| POST   | Endpoint compatibilidade      |

### 5. Core (`src/core/`)

- **Application**: Singleton com event loop e logger
- **EnvironmentVariables**: Configuração via .env

### 6. Middleware (`src/middleware/`)

- CORS (permite todas origens)
- Exception handler (respostas JSON padronizadas)

---

## Fluxos Principais

### Fluxo 1: Inicialização da Aplicação

```text
uvicorn.run("main:app")
    ↓
FastAPI lifespan (startup)
    ↓
TtsManager.get_instance()
    ↓
ModelWrapper.load_model()
    ├── XttsModelManager.load_model()
    │   ├── Carrega config.json
    │   ├── Detecta GPU/CPU
    │   └── Carrega model.pth
    ├── SpeakerEmbeddingManager.load_all()
    │   └── Processa WAVs em speakers/
    └── AudioSynthesizer inicializado
    ↓
App pronta na porta 8880
```

### Fluxo 2: Síntese de Áudio (POST /tts/synthesize)

```text
HTTP Request {text, voice, lang_code}
    ↓
TtsRouter.synthesize_stream()
    ↓
Validação Pydantic → TtsDto
    ↓
TtsManager.model.synthesize_audio(dto)
    ↓
AudioSynthesizer.synthesize()
    ├── 1. Busca speaker embedding
    ├── 2. Divide texto em sentenças (regex)
    ├── 3. Para cada sentença:
    │       ├── model.inference() com parâmetros
    │       ├── Trim áudio (librosa)
    │       └── Adiciona silêncio (150-200ms)
    ├── 4. Concatena todos os áudios
    └── 5. Retorna np.ndarray
    ↓
AudioProcessor.apply_silences()
    ├── Remove silêncio excessivo
    ├── Trim extremidades
    ├── Adiciona padding (150ms)
    └── Exporta para WAV bytes
    ↓
StreamingResponse (audio/wav)
```

### Fluxo 3: Listagem de Vozes (GET /tts/voices)

```text
HTTP Request
    ↓
TtsRouter.list_speakers()
    ↓
TtsManager.model.list_speakers()
    ↓
SpeakerEmbeddingManager.list_speakers()
    ↓
Escaneia pasta speakers/ (.wav)
    ↓
JSON Response [lista de nomes]
```

---

## Design Patterns

| Padrão        | Onde é Usado                            | Propósito                       |
| ------------- | --------------------------------------- | ------------------------------- |
| **Singleton** | TtsManager, XttsModelManager, Application | Instância única               |
| **Facade**    | ModelWrapper                            | Abstrai subsistemas complexos   |
| **Factory**   | SpeakerEmbeddingFactory                 | Cria managers de embedding      |
| **Observer**  | Observable, TtsManager                  | Notificação de eventos          |
| **DTO**       | TtsDto, SpeakerEmbedding                | Transferência de dados          |
| **Provider**  | CoreModelPathProvider, SpeakerPathProvider | Gerencia caminhos            |

---

## Parâmetros de Síntese

```python
# AudioSynthesizer - parâmetros de inferência
model.inference(
    temperature=0.65,       # Estabilidade
    length_penalty=1.0,     # Sentenças longas
    repetition_penalty=12.0, # Reduz artefatos
    top_k=35,               # Amostragem
    top_p=0.75,             # Nucleus sampling
    speed=0.95              # Velocidade
)
```

---

## DTOs Principais

```python
# TtsDto - entrada para síntese
class TtsDto:
    text: str          # Texto a sintetizar
    voice: str         # Nome da voz
    lang_code: str     # Código do idioma (default: "en")

# SpeakerEmbedding - dados de voz
@dataclass
class SpeakerEmbedding:
    gpt_cond_latent: Any      # Latentes GPT
    speaker_embedding: Any     # Embedding da voz
```

---

## Variáveis de Ambiente (.env)

```bash
AUDIO_FACTOR=0.6
SAMPLE_RATE=24000
PORT=8880
DEVICE=gpu
XTTS_MODEL_FOLDER=/path/to/models/
MODEL_FOLDER=v2.0.3/
MODEL_FILE=model.pth
SPEAKERS_FILE=speakers_xtts.pth
VOCAB_FILE=vocab.json
CONFIG_FILE=config.json
```

---

## Dependências Principais

- **FastAPI + Uvicorn**: Framework web
- **PyTorch + TorchAudio**: Deep learning e áudio
- **Coqui TTS**: Modelo XTTS
- **Librosa + Pydub**: Processamento de áudio
- **faster-whisper**: Reconhecimento de fala
- **Gradio**: Interface UI (scripts)
