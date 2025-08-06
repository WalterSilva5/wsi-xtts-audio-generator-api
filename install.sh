#!/bin/bash

# Create a Python virtual environment
#use python 3.9
# python -m venv venv -p python3.10
# Activate the virtual environment
source venv/bin/activate

# Install other dependencies from requirements.txt
pip install -r requirements.txt
pip install torch==2.1.1+cu118 torchaudio==2.1.1+cu118 --index-url https://download.pytorch.org/whl/cu118

if [ ! -f "./models/XTTS-v2-config.json" ]; then
    echo "Downloading XTTS model files"
    wget https://huggingface.co/coqui/XTTS-v2/resolve/${version}/config.json -O ./models/XTTS-v2-config.json
    wget https://coqui.gateway.scarf.sh/hf-coqui/XTTS-v2/${version}/vocab.json -O ./models/XTTS-v2-vocab.json
    wget https://coqui.gateway.scarf.sh/hf-coqui/XTTS-v2/${version}/model.pth -O ./models/XTTS-v2-model.pth
    wget https://coqui.gateway.scarf.sh/hf-coqui/XTTS-v2/${version}/speakers_xtts.pth -O ./models/XTTS-v2-speakers.pth

    echo "XTTS model files downloaded successfully"

    mkdir -p ./models/speaker_embeddings/
    sample_wav_url="https://github.com/daswer123/xtts-api-server/raw/main/example/"
    audio_names=("calm_female" "female" "male.wav")

    for((i=0; i<3; i++))
    do
        wget $sample_wav_url${audio_names[i]}.wav -O ./models/speaker_embeddings/${audio_names[i]}.wav
    done
else
    echo "XTTS model files already exists"
fi


echo "Install deepspeed for Linux for python 3.10.x and CUDA 11.8"
python scripts/modeldownloader.py
python3 -m spacy download pt_core_news_sm
echo "Install complete."