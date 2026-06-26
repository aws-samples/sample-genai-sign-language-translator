FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim
# FROM ghcr.io/astral-sh/uv:0.8.15-python3.13-bookworm-slim@sha256:862111034b138be47412c0df7209f51c5997371688f08be25a3c45f88b052506
WORKDIR /app

# Configure UV for container environment
ENV UV_SYSTEM_PYTHON=1 UV_COMPILE_BYTECODE=1

# Install system dependencies including ffmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Create /opt/bin directory and link ffmpeg
RUN mkdir -p /opt/bin && ln -s /usr/bin/ffmpeg /opt/bin/ffmpeg

# Copy requirements and install Python dependencies
COPY signlanguageagent/requirements.txt signlanguageagent/requirements.txt
RUN uv pip install -r signlanguageagent/requirements.txt

# Install OpenTelemetry for observability
RUN uv pip install aws-opentelemetry-distro>=0.10.1

# Set environment variables for AWS and agent configuration
ENV AWS_REGION=us-west-2
ENV AWS_DEFAULT_REGION=us-west-2
ENV ENG_TO_ASL_MODEL=us.amazon.nova-lite-v1:0
ENV POSE_BUCKET=genasl-avatar
ENV ASL_DATA_BUCKET=genasl-data
ENV KEY_PREFIX=aslavatarv2/gloss2pose/lookup/
ENV TABLE_NAME=Pose_Data6
ENV MAX_TOKENS=3000
ENV TEMPERATURE=0.0

# Signal that this is running in Docker for host binding logic
ENV DOCKER_CONTAINER=1

# Set Python path to include the functions directory
ENV PYTHONPATH=/app:$PYTHONPATH

# Create non-root user
RUN useradd -m -u 1000 bedrock_agentcore

# Copy entire project (respecting .dockerignore)
COPY . .

# Change ownership of the app directory to the non-root user
RUN chown -R bedrock_agentcore:bedrock_agentcore /app

# Switch to non-root user
USER bedrock_agentcore

# Expose ports for the agent
EXPOSE 8080
EXPOSE 8000

# Health check to ensure the agent is running properly
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from signlanguageagent.slagent import health_check; import sys; sys.exit(0 if health_check()['status'] == 'healthy' else 1)"

# Use the full module path with OpenTelemetry instrumentation
CMD ["opentelemetry-instrument", "python", "-m", "signlanguageagent.slagent"]
