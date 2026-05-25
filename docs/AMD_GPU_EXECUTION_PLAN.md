# Execução com GPU AMD (ROCm) — Linux nativo

## Sumário Executivo

Este documento descreve o procedimento **validado** para executar a aplicação
(API REST + App Desktop) com aceleração de GPU AMD em **Linux nativo**, usando
**PyTorch com ROCm**.

> Procedimento testado e funcionando em:
> - **GPU**: AMD Radeon RX 9060 XT (Navi 44, RDNA4, `gfx1201`)
> - **SO**: Manjaro Linux, kernel 6.12
> - **PyTorch**: `torch 2.8.0+rocm6.4` (device reportado como `cuda`/HIP)
> - **Python**: 3.10 (obrigatório — coqui-tts exige `>=3.9,<3.13`)

> **Nota sobre Windows/WSL2:** o ROCm não tem suporte nativo no Windows. Se você
> estiver no Windows, a única rota com GPU é via **WSL2 + Ubuntu** seguindo
> essencialmente os mesmos passos da seção 4 abaixo. Em Linux nativo, **não há
> necessidade de WSL2**.

---

## 1. Como funciona (por que não precisa instalar o ROCm do sistema)

As *wheels* `torch==X+rocmY.Z` distribuídas em `download.pytorch.org` **já trazem
o runtime ROCm embutido** (bibliotecas HIP, rocBLAS, MIOpen, etc.). Portanto:

- **NÃO** é necessário instalar o pacote `rocm-dev` / `/opt/rocm` do sistema só
  para rodar esta aplicação.
- O que precisa existir no host:
  1. Driver de kernel **`amdgpu`** carregado (vem no kernel do Manjaro/Arch).
  2. Acesso aos devices de compute: **`/dev/kfd`** e **`/dev/dri/renderD*`**.
  3. Permissão de acesso a esses devices (usuário nos grupos `render`/`video`,
     ou os devices acessíveis — no ambiente testado estavam `crw-rw-rw-`).

No código, `src/modules/system/torch_util.py` detecta a GPU AMD via
`torch.version.hip` e a aplicação usa a API `torch.cuda.*`, que no build ROCm
mapeia para HIP. Por isso o device aparece como `"cuda"` mesmo em GPU AMD.

---

## 2. Escolha da versão do PyTorch / ROCm

| Índice ROCm | Versões de `torch` (cp310) | Suporta RDNA4 (gfx1201)? | Compatível com coqui-tts 0.24.2? |
|-------------|----------------------------|--------------------------|----------------------------------|
| `rocm6.3`   | 2.7.x, 2.8.0, 2.9.x        | ❌ Não                   | sim (torch 2.8)                  |
| **`rocm6.4`** | **2.8.0**, 2.9.0, 2.9.1  | ✅ **Sim**               | ✅ **sim (torch 2.8 — usado)**   |
| `rocm7.1`   | 2.10, 2.11, 2.12           | ✅ Sim                   | arriscado (torch novo demais)    |

**Decisão:** `torch 2.8.0+rocm6.4`.
- `rocm6.3` **não** reconhece RDNA4 (RX 9060 XT).
- `rocm7.1` só oferece `torch >= 2.10`, novo demais para `coqui-tts 0.24.2` /
  `transformers 4.42`.
- `rocm6.4` + `torch 2.8.0` atende RDNA4 **e** as restrições do coqui-tts.

> Restrições do `coqui-tts==0.24.2`: `python >=3.9,<3.13`, `torch>=2.1`,
> `transformers>=4.42,<4.43`, `numpy>=1.25.2`. Por isso fixamos `numpy<2`.

---

## 3. Pré-requisitos

```bash
# 1) GPU AMD visível e driver carregado
lspci | grep -Ei 'vga|3d|display'      # deve listar a GPU AMD
lsmod | grep '^amdgpu'                  # módulo amdgpu carregado

# 2) Devices de compute acessíveis
ls -l /dev/kfd /dev/dri/renderD128

# 3) Se NÃO tiver acesso (permissão negada), entre nos grupos e reabra a sessão:
sudo usermod -aG render,video "$USER"   # depois: logout/login

# 4) ffmpeg (usado pelo pydub/torchaudio)
ffmpeg -version

# 5) uv (gerenciador de venv/python) — usado por causa do Python 3.10
uv --version
```

> O sistema testado tinha apenas Python 3.14; o `uv` baixa e gerencia o Python
> 3.10 automaticamente, sem precisar alterar o Python do sistema.

---

## 4. Instalação (passo a passo validado)

A partir da **raiz do projeto**:

```bash
# 4.1 — venv com Python 3.10 (uv baixa o 3.10 se necessário)
uv venv --python 3.10 .venv

# 4.2 — PyTorch ROCm 6.4 (instale ANTES do resto p/ fixar o build ROCm)
uv pip install -p .venv/bin/python --index-strategy unsafe-best-match \
  --extra-index-url https://download.pytorch.org/whl/rocm6.4 \
  "torch==2.8.0+rocm6.4" "torchaudio==2.8.0+rocm6.4" "torchvision==0.23.0+rocm6.4"

# 4.3 — dependências da aplicação (mantêm o torch ROCm já instalado)
uv pip install -p .venv/bin/python \
  "numpy<2" \
  "coqui-tts[languages]==0.24.2" \
  fastapi "uvicorn[standard]" python-decouple pydantic-settings \
  pydub soundfile psutil PySide6 spacy python-multipart
```

> **Por que `--index-strategy unsafe-best-match`:** permite que o `uv` resolva o
> `torch` (local version `+rocm6.4`) no índice do PyTorch e o restante das
> dependências no PyPI, sem puxar acidentalmente o `torch` de CPU.

### 4.4 — Modelos XTTS

Coloque os arquivos em `models/v2.0.3/`:

```bash
MODEL_DIR=models/v2.0.3
curl -L "https://huggingface.co/coqui/XTTS-v2/resolve/v2.0.3/config.json"          -o "$MODEL_DIR/config.json"
curl -L "https://huggingface.co/coqui/XTTS-v2/resolve/v2.0.3/vocab.json"           -o "$MODEL_DIR/vocab.json"
curl -L "https://huggingface.co/coqui/XTTS-v2/resolve/v2.0.3/speakers_xtts.pth"    -o "$MODEL_DIR/speakers_xtts.pth"
curl -L "https://huggingface.co/coqui/XTTS-v2/resolve/v2.0.3/model.pth"            -o "$MODEL_DIR/model.pth"   # ~1.8GB
```

### 4.5 — Arquivo `.env`

```env
AUDIO_FACTOR=0.6
SAMPLE_RATE=24000
PORT=8880
GPU_TYPE=amd
DEVICE=gpu
XTTS_MODEL_FOLDER=./models/
MODEL_FOLDER=v2.0.3/
MODEL_FILE=model.pth
CONFIG_FILE=config.json
VOCAB_FILE=vocab.json
SPEAKERS_FILE=speakers_xtts.pth
# aponta a busca de speakers para ./speakers/ (relativo a XTTS_MODEL_FOLDER+MODEL_FOLDER)
SAMPLE_SPEAKERS_FOLDER=../../speakers/
```

> **Importante:** `GPU_TYPE` é lido de **`os.environ`** (em
> `settings/environment_variables.py`), e **não** do `.env`. Mantenha no `.env`
> por documentação, mas **exporte** `GPU_TYPE=amd` ao executar (veja seção 6).
> Sem isso, o tipo de GPU cairia no default `nvidia` para fins de *report* do
> endpoint de health — a inferência ainda usa a GPU (detecção via
> `torch.version.hip`), mas o `/health/system` reportaria errado.

---

## 5. Verificação da GPU

```bash
# Detecção
.venv/bin/python -c "import torch; print(torch.__version__, '| hip', torch.version.hip, '| avail', torch.cuda.is_available(), '|', torch.cuda.get_device_name(0))"
# Saída esperada (exemplo):
# 2.8.0+rocm6.4 | hip 6.4.43482-... | avail True | AMD Radeon Graphics

# Compute real na GPU (não só detecção)
.venv/bin/python -c "import torch; a=torch.randn(1024,1024,device='cuda'); b=torch.randn(1024,1024,device='cuda'); c=a@b; torch.cuda.synchronize(); print('matmul ok', float(c.sum()))"
```

> **`HSA_OVERRIDE_GFX_VERSION`:** não foi necessário com `rocm6.4` na RX 9060 XT.
> Só use se a sua GPU não for reconhecida pelo ROCm da wheel (ex.: arquiteturas
> mais antigas), apontando para a arch suportada mais próxima.

---

## 6. Execução

Sempre a partir da **raiz do projeto**, com `GPU_TYPE=amd` exportado:

```bash
source .venv/bin/activate

# API REST  -> http://localhost:8880/docs
GPU_TYPE=amd python main.py

# App Desktop (PySide6) — requer sessão gráfica (X11/Wayland)
GPU_TYPE=amd python main_desktop.py
```

Teste rápido da API (gera um WAV na GPU):

```bash
curl -s -X POST "http://localhost:8880/tts/synthesize" \
  -H "Content-Type: application/json" \
  -d '{"text":"Olá! Síntese rodando na GPU AMD via ROCm.","voice":"feminina","lang_code":"pt"}' \
  --output /tmp/teste.wav
```

---

## 7. Resultados observados (RX 9060 XT)

- `torch.cuda.is_available()` → `True`; device name `AMD Radeon Graphics`.
- Carregamento do modelo: usa o *fallback* `weights_only=False`
  (`model_manager.py`) — esperado no torch >= 2.6.
- `/tts/model/info` → `"device": "cuda"`, modelo carregado, 16 idiomas.
- Síntese PT-BR de ~5,5s de áudio em ~13s na primeira chamada (inclui warm-up);
  chamadas seguintes são mais rápidas.

---

## 8. Troubleshooting

| Sintoma | Causa provável | Ação |
|--------|----------------|------|
| `torch.cuda.is_available()` = False | wheel CPU instalada por cima | reinstalar `torch==2.8.0+rocm6.4` (seção 4.2) |
| `HIP error: invalid device function` / crash em kernel | ROCm da wheel não suporta a arch | usar índice ROCm mais novo (`rocm7.1`) **ou** `HSA_OVERRIDE_GFX_VERSION` |
| `Permission denied` em `/dev/kfd` | usuário sem grupo `render`/`video` | `sudo usermod -aG render,video $USER` e relogar |
| `/health/system` mostra GPU como nvidia | `GPU_TYPE` não exportado | exportar `GPU_TYPE=amd` ao rodar |
| `coqui-tts` falha ao instalar | Python != 3.10/3.11/3.12 | usar venv 3.10 (`uv venv --python 3.10`) |

---

## 9. Referências

- [PyTorch ROCm](https://pytorch.org/docs/stable/notes/hip.html)
- [Índices de wheels ROCm do PyTorch](https://download.pytorch.org/whl/rocm6.4/)
- [ROCm — matriz de compatibilidade](https://rocm.docs.amd.com/en/latest/compatibility/compatibility-matrix.html)
- [coqui-tts (fork idiap)](https://pypi.org/project/coqui-tts/)
- [XTTS v2 — Hugging Face](https://huggingface.co/coqui/XTTS-v2)
