# Use the same base image as the existing SignLanguageAgent for consistency
FROM public.ecr.aws/lambda/python:3.11

# Copy requirements and install dependencies
COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install -r requirements.txt

# Copy all conversational agent code
COPY . ${LAMBDA_TASK_ROOT}

# Set the handler
CMD ["conversational_asl_agent_main.invoke"]