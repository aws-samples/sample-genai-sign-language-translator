FROM public.ecr.aws/lambda/python:3.12

# Copy source files
COPY . ${LAMBDA_TASK_ROOT}/

# Install the specified packages
RUN python -m pip install --upgrade --force-reinstall pip wheel==0.43.0
RUN pip install -r requirements.txt
RUN dnf install -y mesa-libGL

# Create a non-root user and group
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set permissions for the Lambda task root
RUN chown -R appuser:appuser ${LAMBDA_TASK_ROOT}

# Switch to non-root user
USER appuser

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "blendedpose_handler.lambda_handler" ]