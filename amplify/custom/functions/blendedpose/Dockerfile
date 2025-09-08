FROM public.ecr.aws/lambda/python:3.11

# Install system dependencies
RUN dnf update -y && \
    dnf install -y mesa-libGL libgomp && \
    dnf clean all

# Upgrade pip and install wheel
RUN python -m pip install --upgrade pip wheel

# Copy requirements first for better caching
COPY requirements.txt ${LAMBDA_TASK_ROOT}/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source files
COPY . ${LAMBDA_TASK_ROOT}/

# Set the CMD to your handler
CMD [ "blendedpose_handler.lambda_handler" ]