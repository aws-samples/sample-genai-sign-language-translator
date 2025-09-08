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
RUN pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118 \
    && pip3 install -U openmim \
    && mim install mmengine \
    && mim install "mmdet>=3.0.0" \
    && pip3 install git+https://github.com/jin-s13/xtcocoapi

# Clone and install mmpose
RUN git clone https://github.com/open-mmlab/mmpose.git \
    && cd mmpose \
    && pip3 install -r requirements.txt \
    && pip3 install -v -e .

# Create checkpoints directory
RUN mkdir -p ${TASK_ROOT}/dataprep/checkpoints

# Download model checkpoints
RUN wget https://download.openmmlab.com/mmpose/v1/projects/rtmposev1/rtmpose-l_simcc-coco-wholebody_pt-aic-coco_270e-384x288-eaeb96c8_20230125.pth -P ${LAMBDA_TASK_ROOT}/dataprep/checkpoints \
    && wget https://download.openmmlab.com/mmdetection/v2.0/faster_rcnn/faster_rcnn_r50_fpn_1x_coco/faster_rcnn_r50_fpn_1x_coco_20200130-047c8118.pth -P ${LAMBDA_TASK_ROOT}/dataprep/checkpoints

# Copy your application code
COPY . .

# Set the entrypoint to your handler
#CMD [ "python3", "-m", "app.handler" ]
