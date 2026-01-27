# XTTS API

API REST para síntese de voz (Text-to-Speech) baseada no modelo [XTTS v2](https://huggingface.co/coqui/XTTS-v2) da Coqui TTS.

## Features

- Síntese de voz de alta qualidade com clonagem de voz
- Suporte a múltiplos idiomas (inglês, português, espanhol, etc.)
- API REST com FastAPI
- Suporte a GPU (CUDA) e CPU
- Gerenciamento de múltiplas vozes/speakers
- Processamento de áudio com remoção de silêncio e normalização

## Requisitos

- Python 3.9 ou 3.10
- CUDA 11.8 (para aceleração GPU)
- FFmpeg
- 8GB+ RAM (16GB recomendado)
- GPU com 6GB+ VRAM (opcional, mas recomendado)

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

```bash
pip install -r requirements.txt
pip install torch==2.1.1+cu118 torchaudio==2.1.1+cu118 --index-url https://download.pytorch.org/whl/cu118
```

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

## Configuração

Crie um arquivo `.env` na raiz do projeto:

```env
# Áudio
AUDIO_FACTOR=0.6
SAMPLE_RATE=24000

# Servidor
PORT=8880

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

## Uso

### Iniciando o servidor

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

### Adicionando novas vozes

1. Grave um áudio WAV de 10-30 segundos com a voz desejada
2. Salve o arquivo na pasta `speakers/` com extensão `.wav`
3. Reinicie o servidor

## Estrutura do Projeto

```text
xtts-api/
├── main.py                 # Entry point
├── requirements.txt        # Dependências
├── settings/               # Configurações
├── models/                 # Modelos XTTS
├── speakers/               # Arquivos de voz
└── src/
    ├── audio/              # Processamento de áudio
    ├── core/               # Core da aplicação
    ├── middleware/         # Middlewares HTTP
    ├── routers/            # Endpoints da API
    └── tts/                # Motor TTS
        └── xtts/
            ├── dto/        # Data Transfer Objects
            ├── manager/    # Gerenciador TTS
            └── wrapper/    # Wrappers do modelo
```

Para documentação detalhada da arquitetura, consulte [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Idiomas Suportados

| Código | Idioma     |
| ------ | ---------- |
| en     | Inglês     |
| pt     | Português  |
| es     | Espanhol   |
| fr     | Francês    |
| de     | Alemão     |
| it     | Italiano   |
| pl     | Polonês    |
| tr     | Turco      |
| ru     | Russo      |
| nl     | Holandês   |
| cs     | Tcheco     |
| ar     | Árabe      |
| zh-cn  | Chinês     |
| ja     | Japonês    |
| ko     | Coreano    |
| hu     | Húngaro    |

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
