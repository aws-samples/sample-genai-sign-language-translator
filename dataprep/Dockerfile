# Use NVIDIA CUDA base image with Python support
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu20.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV TASK_ROOT=/var/task

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    git \
    gcc \
    g++ \
    make \
    cmake \
    ninja-build \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR ${TASK_ROOT}

# Upgrade pip
RUN python3 -m pip install --upgrade pip

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install PyTorch with CUDA support and other dependencies
# Versions pinned for reproducible, auditable builds
RUN pip3 install torch==2.1.0 torchvision==0.16.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/cu118 \
    && pip3 install -U openmim==0.3.9 \
    && mim install mmengine==0.10.4 \
    && mim install "mmdet==3.2.0" \
    && pip3 install "git+https://github.com/jin-s13/xtcocoapi.git@6edccc2e7d1de1dc1180167bbc2f136cd2bf0b2b"

# Clone and install mmpose (pinned to v1.3.2 commit for reproducibility)
RUN git clone https://github.com/open-mmlab/mmpose.git \
    && cd mmpose \
    && git checkout 5408bc76f5b848cf925a0d1857899011d8c5b497 \
    && pip3 install -r requirements.txt \
    && pip3 install -v -e .

# Create checkpoints directory
RUN mkdir -p ${TASK_ROOT}/dataprep/checkpoints

# Download model checkpoints (URLs reference specific dated artifacts and are immutable)
RUN wget https://download.openmmlab.com/mmpose/v1/projects/rtmposev1/rtmpose-l_simcc-coco-wholebody_pt-aic-coco_270e-384x288-eaeb96c8_20230125.pth -P ${TASK_ROOT}/dataprep/checkpoints \
    && wget https://download.openmmlab.com/mmdetection/v2.0/faster_rcnn/faster_rcnn_r50_fpn_1x_coco/faster_rcnn_r50_fpn_1x_coco_20200130-047c8118.pth -P ${TASK_ROOT}/dataprep/checkpoints

# Copy your application code
COPY . .

# Set the entrypoint to your handler
#CMD [ "python3", "-m", "app.handler" ]
