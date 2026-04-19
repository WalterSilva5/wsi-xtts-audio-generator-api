# XTTS API & Desktop

Aplicação de síntese de voz (Text-to-Speech) baseada no modelo [XTTS v2](https://huggingface.co/coqui/XTTS-v2) da Coqui TTS, disponível como **App Desktop** e **API REST**.

![Python](https://img.shields.io/badge/Python-3.9%20%7C%203.10-blue)
![License](https://img.shields.io/badge/License-GPL--3.0-green)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey)

## Features

- Síntese de voz de alta qualidade com clonagem de voz
- Suporte a 16+ idiomas (inglês, português, espanhol, etc.)
- **App Desktop** com interface gráfica moderna (PySide6)
- **API REST** com FastAPI
- Suporte a GPU (CUDA) e CPU
- Gerenciamento de múltiplas vozes/speakers
- Processamento de áudio com remoção de silêncio e normalização
- **Múltiplos formatos de saída** (WAV, MP3, OGG, FLAC)
- **Batch synthesis** - sintetize múltiplos textos de uma vez
- **API de gerenciamento de speakers** - adicione/remova vozes via API
- **Estimativa de duração** - calcule a duração antes de sintetizar
- **Health check** - monitoramento de status do servidor e modelo
- **Fila de processamento assíncrona** - processe sínteses em background com persistência em arquivo

## Requisitos

- Python 3.9 ou 3.10
- FFmpeg
- 8GB+ RAM (16GB recomendado)
- GPU com 6GB+ VRAM (opcional, mas recomendado)

### Suporte a GPU

A aplicação suporta tanto GPUs **NVIDIA** (CUDA) quanto **AMD** (ROCm).

| Fabricante | Backend | Versão Recomendada |
|----------|---------|----------------|
| NVIDIA | CUDA | 11.8 ou 12.1 |
| AMD | ROCm | 7.1 ou 7.2 |

O tipo de GPU é selecionado automaticamente durante a instalação.

## Instalação

### Instalação Automática (Recomendado)

#### Linux/macOS

```bash
git clone https://github.com/seu-usuario/xtts-api.git
cd xtts-api
chmod +x install.sh
./install.sh
```

#### Windows (CMD)

```cmd
git clone https://github.com/seu-usuario/xtts-api.git
cd xtts-api
install.bat
```

#### Windows (PowerShell)

```powershell
git clone https://github.com/seu-usuario/xtts-api.git
cd xtts-api
powershell -ExecutionPolicy Bypass -File install.ps1
```

### Instalação Manual

<details>
<summary>Clique para expandir</summary>

#### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/xtts-api.git
cd xtts-api
```

#### 2. Crie e ative o ambiente virtual

```bash
python -m venv venv

# Linux/macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

#### 3. Instale as dependências

**NVIDIA (padrão):**
```bash
pip install -r requirements.txt
pip install torch==2.1.1+cu118 torchaudio==2.1.1+cu118 --index-url https://download.pytorch.org/whl/cu118
```

**AMD (ROCm):**
```bash
pip install -r requirements.txt
pip install torch==2.8.0 torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm7.1
```

> Nota: Para AMD, certifique-se de ter o ROCm 7.1+ instalado no sistema.

#### 4. Baixe os modelos

Os modelos serão baixados automaticamente na primeira execução, ou execute:

```bash
python scripts/modeldownloader.py
```

#### 5. Configure as variáveis de ambiente

```bash
cp .env_example .env
# Edite o arquivo .env conforme necessário
```

</details>

## Uso

### App Desktop (Interface Gráfica)

```bash
python main_desktop.py
```

O app desktop oferece uma interface moderna com:

- **Síntese de texto para voz** - Digite o texto e gere áudio
- **Seleção de vozes** - Escolha entre múltiplas vozes disponíveis
- **Seleção de idiomas** - Suporte a 16+ idiomas
- **Controles de síntese** - Velocidade, temperatura, top-k, top-p
- **Player de áudio integrado** - Play, pause, stop, seek
- **Exportação** - Salve o áudio como WAV ou MP3

#### Screenshot

```text
┌─────────────────────────────────────────────────────────┐
│  XTTS Desktop                                           │
├──────────────┬──────────────────────────────────────────┤
│              │  Text Input                              │
│  🔊 Synthesis │  ┌────────────────────────────────────┐ │
│              │  │ Digite o texto aqui...             │ │
│  🎭 Voice    │  └────────────────────────────────────┘ │
│     Conversion│                                         │
│              │  Voice Settings                         │
│  🌐 Translation│  [Voice ▼] [Language ▼] [Speed ━━●━━] │
│              │                                         │
│  📁 Batch    │  [████████████████] 100%               │
│              │  [🔊 Synthesize] [Cancel]               │
│              │                                         │
│  ──────────  │  Audio Preview                          │
│  ⚙️ Settings │  [▶] [■] ━━━━━●━━━━━ 00:05/00:12       │
│  ℹ️ About    │  [💾 Save Audio]                        │
└──────────────┴──────────────────────────────────────────┘
```

### API REST (Servidor)

```bash
python main.py
```

O servidor estará disponível em `http://localhost:8880`.

### Documentação da API

- Swagger UI: `http://localhost:8880/docs`
- ReDoc: `http://localhost:8880/redoc`

### Endpoints

#### POST /tts/synthesize

Sintetiza áudio a partir de texto.

**Request:**

```json
{
  "text": "Olá, este é um teste de síntese de voz.",
  "voice": "feminina",
  "lang_code": "pt"
}
```

**Response:** Arquivo WAV (audio/wav)

**Exemplo com cURL:**

```bash
curl -X POST "http://localhost:8880/tts/synthesize" \
  -H "Content-Type: application/json" \
  -d '{"text": "Olá mundo!", "voice": "feminina", "lang_code": "pt"}' \
  --output output.wav
```

#### GET /tts/voices

Lista as vozes disponíveis.

**Response:**

```json
["feminina", "masculina", "feminina_calma"]
```

#### POST /tts/audio/speech

Endpoint de compatibilidade com formatos alternativos.

**Request:**

```json
{
  "input": "Texto para sintetizar",
  "voice": "feminina"
}
```

#### GET /health

Verifica se a API está funcionando.

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "version": "1.0.0"
}
```

#### GET /health/ready

Verifica se o modelo está carregado e pronto para receber requisições.

#### GET /health/system

Retorna informações do sistema (CPU, memória, GPU).

#### GET /tts/model/info

Retorna informações sobre o modelo carregado.

**Response:**

```json
{
  "model_loaded": true,
  "model_version": "XTTS v2",
  "device": "cuda",
  "speakers_count": 5,
  "supported_languages": ["en", "pt", "es", ...],
  "supported_formats": ["wav", "mp3", "ogg", "flac"]
}
```

#### POST /tts/synthesize/with-format

Sintetiza áudio com formato de saída específico.

**Query Parameters:**
- `output_format`: wav, mp3, ogg, flac (padrão: wav)

**Exemplo:**

```bash
curl -X POST "http://localhost:8880/tts/synthesize/with-format?output_format=mp3" \
  -H "Content-Type: application/json" \
  -d '{"text": "Olá mundo!", "voice": "feminina", "lang_code": "pt"}' \
  --output output.mp3
```

#### POST /tts/estimate-duration

Estima a duração do áudio sem sintetizar.

**Request:**

```json
{
  "text": "Texto para estimar duração",
  "speed": 1.0
}
```

**Response:**

```json
{
  "text_length": 26,
  "word_count": 4,
  "estimated_duration_seconds": 2.3,
  "estimated_duration_formatted": "00:02"
}
```

#### POST /tts/batch/synthesize

Sintetiza múltiplos textos em uma única requisição. Retorna um arquivo ZIP.

**Request:**

```json
{
  "items": [
    {"text": "Primeiro texto"},
    {"text": "Segundo texto", "voice": "masculina"},
    {"text": "Third text", "lang_code": "en"}
  ],
  "default_voice": "feminina",
  "default_lang_code": "pt",
  "output_format": "mp3"
}
```

**Response:** Arquivo ZIP contendo os áudios e um `manifest.json` com os resultados.

#### POST /tts/speakers/add

Adiciona uma nova voz via upload de arquivo de áudio.

**Form Data:**
- `speaker_name`: Nome da nova voz
- `audio_file`: Arquivo WAV (10-30 segundos recomendado)

**Exemplo com cURL:**

```bash
curl -X POST "http://localhost:8880/tts/speakers/add" \
  -F "speaker_name=minha_voz" \
  -F "audio_file=@meu_audio.wav"
```

#### DELETE /tts/speakers/{speaker_name}

Remove uma voz da memória.

#### POST /tts/speakers/reload

Recarrega todas as vozes do diretório de speakers.

#### GET /tts/languages

Lista todos os idiomas suportados.

#### GET /tts/formats

Lista todos os formatos de áudio suportados.

### Sistema de Filas (Processamento Assíncrono)

O sistema de filas permite processar sínteses em background, ideal para textos longos ou batch processing. As tarefas são persistidas em arquivo JSON e processadas sequencialmente por um consumer em background.

#### POST /queue/enqueue/synthesis

Adiciona uma síntese à fila. Retorna imediatamente com o ID da tarefa.

**Request:**

```json
{
  "text": "Texto longo para sintetizar...",
  "voice": "feminina",
  "lang_code": "pt",
  "output_format": "mp3"
}
```

**Response:**

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "position_in_queue": 1,
  "estimated_wait_seconds": 15.5,
  "message": "Task enqueued successfully. Position: 1"
}
```

#### POST /queue/enqueue/batch

Adiciona uma síntese em lote à fila.

**Request:**

```json
{
  "items": [
    {"text": "Primeiro texto"},
    {"text": "Segundo texto", "voice": "masculina"}
  ],
  "default_voice": "feminina",
  "default_lang_code": "pt",
  "output_format": "mp3"
}
```

#### GET /queue/task/{task_id}

Consulta o status de uma tarefa.

**Response:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "task_type": "synthesis",
  "status": "processing",
  "progress": 45.0,
  "created_at": "2024-01-15T10:30:00.000Z",
  "started_at": "2024-01-15T10:30:05.000Z",
  "estimated_wait_seconds": null
}
```

**Status possíveis:** `pending`, `processing`, `completed`, `failed`, `cancelled`

#### GET /queue/task/{task_id}/result

Baixa o resultado de uma tarefa completada (áudio ou ZIP).

#### DELETE /queue/task/{task_id}

Cancela uma tarefa pendente.

#### GET /queue/tasks

Lista todas as tarefas na fila.

**Query Parameters:**

- `status`: Filtrar por status (pending, processing, completed, failed, cancelled)
- `limit`: Limite de resultados (padrão: 50)
- `offset`: Offset para paginação

#### GET /queue/stats

Retorna estatísticas da fila.

**Response:**

```json
{
  "total_tasks": 100,
  "pending": 5,
  "processing": 1,
  "completed": 90,
  "failed": 3,
  "cancelled": 1,
  "consumer_running": true
}
```

#### POST /queue/consumer/start

Inicia o consumer (se não estiver rodando).

#### POST /queue/consumer/stop

Para o consumer.

#### POST /queue/cleanup

Remove tarefas antigas (completadas/falhadas/canceladas).

**Query Parameters:**

- `older_than_hours`: Remove tarefas mais antigas que X horas (padrão: 24)

#### Exemplo de Uso da Fila

```bash
# 1. Enfileirar uma síntese
TASK_ID=$(curl -s -X POST "http://localhost:8880/queue/enqueue/synthesis" \
  -H "Content-Type: application/json" \
  -d '{"text": "Texto longo...", "voice": "feminina", "lang_code": "pt"}' \
  | jq -r '.task_id')

echo "Task ID: $TASK_ID"

# 2. Verificar status periodicamente
while true; do
  STATUS=$(curl -s "http://localhost:8880/queue/task/$TASK_ID" | jq -r '.status')
  echo "Status: $STATUS"

  if [ "$STATUS" = "completed" ]; then
    break
  fi

  sleep 2
done

# 3. Baixar resultado
curl -o resultado.mp3 "http://localhost:8880/queue/task/$TASK_ID/result"
```

### Adicionando novas vozes

1. Grave um áudio WAV de 10-30 segundos com a voz desejada
2. Salve o arquivo na pasta `speakers/` com extensão `.wav`
3. Reinicie a aplicação (desktop ou servidor)

## Configuração

Crie um arquivo `.env` na raiz do projeto:

```env
# Áudio
AUDIO_FACTOR=0.6
SAMPLE_RATE=24000

# Servidor
PORT=8880

# GPU (nvidia ou amd)
GPU_TYPE=nvidia

# Modelo
DEVICE=gpu
XTTS_MODEL_FOLDER=./models/
MODEL_FOLDER=v2.0.3/
MODEL_FILE=model.pth
CONFIG_FILE=config.json
VOCAB_FILE=vocab.json
SPEAKERS_FILE=speakers_xtts.pth

# Speakers
SAMPLE_SPEAKERS_FOLDER=speakers/
```

## Estrutura do Projeto

```text
xtts-api/
├── main.py                 # Entry point API REST
├── main_desktop.py         # Entry point App Desktop
├── requirements.txt        # Dependências
├── install.sh              # Script instalação Linux/macOS
├── install.bat             # Script instalação Windows
├── install.ps1             # Script instalação PowerShell
│
├── ui/                     # Interface Desktop (PySide6)
│   ├── main_window.py      # Janela principal
│   ├── pages/              # Páginas da aplicação
│   │   └── synthesis_page.py
│   ├── widgets/            # Componentes reutilizáveis
│   │   ├── audio_player.py
│   │   └── speaker_selector.py
│   └── workers/            # Workers para operações em background
│       ├── synthesis_worker.py
│       └── model_loader_worker.py
│
├── src/
│   ├── core/               # Core da aplicação
│   │   ├── services/       # Serviços (TTS, Audio)
│   │   └── models/         # DTOs e configurações
│   ├── audio/              # Processamento de áudio
│   ├── queue/              # Sistema de filas assíncrono
│   │   ├── models.py       # Modelos de dados (Task, Status)
│   │   ├── file_queue.py   # Persistência em arquivo JSON
│   │   └── consumer.py     # Worker de processamento
│   ├── routers/            # Endpoints da API
│   ├── middleware/         # Middlewares HTTP
│   └── tts/                # Motor TTS
│       └── xtts/
│           ├── manager/    # Gerenciador TTS
│           ├── wrapper/    # Wrappers do modelo
│           └── dto/        # Data Transfer Objects
│
├── data/                   # Dados da aplicação
│   └── queue/              # Fila de tarefas
│       ├── tasks.json      # Tarefas persistidas
│       └── output/         # Arquivos de resultado
├── models/                 # Modelos XTTS (baixados automaticamente)
├── speakers/               # Arquivos de voz
├── settings/               # Configurações
├── scripts/                # Scripts utilitários
├── resources/              # Recursos (ícones, traduções)
├── build/                  # Scripts de build
└── docs/                   # Documentação
```

Para documentação detalhada da arquitetura, consulte [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Idiomas Suportados

| Código | Idioma     | Código | Idioma   |
| ------ | ---------- | ------ | -------- |
| en     | Inglês     | nl     | Holandês |
| pt     | Português  | cs     | Tcheco   |
| es     | Espanhol   | ar     | Árabe    |
| fr     | Francês    | zh-cn  | Chinês   |
| de     | Alemão     | ja     | Japonês  |
| it     | Italiano   | ko     | Coreano  |
| pl     | Polonês    | hu     | Húngaro  |
| tr     | Turco      | ru     | Russo    |

## Build Executável

Para criar um executável standalone que pode ser distribuído sem necessidade de Python instalado.

### Windows

```cmd
python build/scripts/build_windows.py
```

Opções disponíveis:

```cmd
python build/scripts/build_windows.py --clean      # Limpa builds anteriores
python build/scripts/build_windows.py --onefile    # Cria executável único (maior, startup mais lento)
```

O executável será criado em `dist/XTTS-Desktop/XTTS-Desktop.exe`.

### Linux

```bash
python build/scripts/build_linux.py
```

Opções disponíveis:

```bash
python build/scripts/build_linux.py --clean        # Limpa builds anteriores
python build/scripts/build_linux.py --onefile      # Cria executável único
python build/scripts/build_linux.py --appimage     # Cria AppImage (requer appimagetool)
```

O executável será criado em `dist/XTTS-Desktop/XTTS-Desktop`.

### Distribuição

Após o build:

1. Copie toda a pasta `dist/XTTS-Desktop/` para o computador de destino
2. Execute `XTTS-Desktop.exe` (Windows) ou `./XTTS-Desktop` (Linux)
3. Na primeira execução, o modelo XTTS (~1.8GB) será baixado automaticamente

## Parâmetros de Síntese

A API e o App Desktop agora suportam parâmetros avançados de síntese:

| Parâmetro | Tipo | Padrão | Faixa | Descrição |
|-----------|------|--------|-------|-----------|
| temperature | float | 0.65 | 0.0-1.0 | Aleatoriedade. Menor = mais estável |
| length_penalty | float | 1.0 | 0.5-2.0 | Penalidade para sequências longas |
| repetition_penalty | float | 12.0 | 1.0-20.0 | Penalidade para repetição |
| top_k | int | 35 | 1-100 | Top-K sampling |
| top_p | float | 0.75 | 0.0-1.0 | Nucleus sampling |
| speed | float | 0.95 | 0.5-2.0 | Velocidade da fala |
| do_sample | bool | true | - | Habilita sampling |
| enable_text_splitting | bool | true | - | Divide texto em frases |

Exemplo com parâmetros customizados:

```bash
curl -X POST "http://localhost:8880/tts/synthesize" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Olá mundo!",
    "voice": "feminina",
    "lang_code": "pt",
    "temperature": 0.5,
    "speed": 1.0,
    "top_k": 50
  }' \
  --output output.wav
```

## Roadmap

### Implementado

- [x] MVP - Síntese TTS básica
- [x] Build executável (PyInstaller)
- [x] Parâmetros de síntese configuráveis
- [x] Múltiplos formatos de saída (WAV, MP3, OGG, FLAC)
- [x] Batch Processing - síntese de múltiplos textos
- [x] API de gerenciamento de speakers (add/remove/reload)
- [x] Estimativa de duração do áudio
- [x] Health check e monitoramento do sistema
- [x] Endpoint de informações do modelo
- [x] Fila de processamento assíncrona (baseada em arquivo JSON)

### Em Desenvolvimento

- [ ] Voice Conversion (RVC/OpenVoice)
- [ ] Video Translation Pipeline

### Sugestões de Funcionalidades Futuras

#### Alta Prioridade

| Funcionalidade | Descrição | Benefício |
|----------------|-----------|-----------|
| **Streaming de Áudio** | Retornar áudio em chunks enquanto sintetiza | Reduz latência para textos longos |
| **Cache de Síntese** | Armazenar em cache áudios já sintetizados | Evita reprocessamento, economia de recursos |
| **WebSocket API** | Conexão persistente para síntese em tempo real | Menor overhead, ideal para apps interativos |
| **SSML Support** | Suporte a Speech Synthesis Markup Language | Controle fino sobre pausas, ênfase, pronúncia |
| **Rate Limiting** | Controle de taxa de requisições por IP/API key | Proteção contra abuso da API |

#### Média Prioridade

| Funcionalidade | Descrição | Benefício |
|----------------|-----------|-----------|
| **Webhook Callbacks** | Notificar URLs quando síntese estiver pronta | Integração assíncrona com outros sistemas |
| **API de Tradução + TTS** | Traduzir texto e sintetizar em um único endpoint | Simplifica fluxo de tradução de áudio |
| **Emotion/Style Control** | Controlar emoção/estilo da voz (feliz, triste, etc.) | Vozes mais expressivas |
| **Audio Preview** | Sintetizar apenas os primeiros segundos | Teste rápido de configurações |
| **Speaker Mixing** | Misturar características de múltiplas vozes | Criar vozes híbridas/customizadas |

#### Baixa Prioridade (Futuro)

| Funcionalidade | Descrição | Benefício |
|----------------|-----------|-----------|
| **Multi-tenant** | Suporte a múltiplos usuários/organizações | Deploy SaaS |
| **Métricas/Analytics** | Dashboard com estatísticas de uso | Monitoramento e otimização |
| **Plugin System** | Sistema de plugins para extensões | Extensibilidade |
| **Voice Fine-tuning** | Ajuste fino de vozes com poucos samples | Melhores clones de voz |
| **Background Music** | Adicionar música de fundo ao áudio | Produção de conteúdo |
| **Multi-speaker Dialogue** | Gerar diálogos com múltiplas vozes | Podcasts, audiobooks |
| **Phoneme Editor** | Editor visual de fonemas | Correção de pronúncia |

#### Integrações Sugeridas

- **Discord Bot** - Bot para síntese de voz em servidores
- **Telegram Bot** - Bot para mensagens de voz
- **OBS Plugin** - Integração com streaming
- **Home Assistant** - Integração com automação residencial
- **Slack App** - Notificações em áudio
- **VS Code Extension** - Leitura de código/documentação

## Contribuindo

Contribuições são bem-vindas! Por favor:

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

## Créditos

Este projeto foi baseado no [xtts-webui](https://github.com/daswer123/xtts-webui) por daswer123.

## Licença

Este projeto está licenciado sob a GNU General Public License v3.0 - veja o arquivo [LICENSE](LICENSE) para detalhes.

## Links Úteis

- [XTTS v2 no Hugging Face](https://huggingface.co/coqui/XTTS-v2)
- [Coqui TTS](https://github.com/coqui-ai/TTS)
- [FastAPI](https://fastapi.tiangolo.com/)
- [PySide6](https://doc.qt.io/qtforpython-6/)
