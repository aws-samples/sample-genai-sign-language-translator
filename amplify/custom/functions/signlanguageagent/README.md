# GenASL Sign Language Agent

This module implements the main Strands-based agent for the GenASL (Generative AI-powered American Sign Language) translation system. The agent is deployed on AWS Bedrock AgentCore and provides conversational ASL translation capabilities.

## Architecture

The agent is built using the Strands framework and consists of the following components:

- **Agent Core** (`slagent.py`): Main agent implementation with entry point
- **Configuration** (`config.py`): Centralized configuration management
- **Utilities** (`utils.py`): Common utility functions and decorators
- **Tests** (`test_agent.py`): Basic validation and testing functionality

## Features

- **Text to ASL Translation**: Converts English text to ASL gloss and video
- **Conversational Interface**: Natural language interaction capabilities
- **Error Handling**: Robust error handling with retry mechanisms
- **Configuration Management**: Environment-based configuration
- **Health Monitoring**: Built-in health check endpoints
- **Logging**: Comprehensive logging and observability

## Configuration

The agent uses environment variables for configuration:

### Required Variables
- `ENG_TO_ASL_MODEL`: Bedrock model for English to ASL translation (default: us.amazon.nova-lite-v1:0)
- `POSE_BUCKET`: S3 bucket for pose data (default: genasl-avatar)
- `ASL_DATA_BUCKET`: S3 bucket for generated ASL data (default: genasl-data)
- `TABLE_NAME`: DynamoDB table for pose data (default: Pose_Data6)
- `KEY_PREFIX`: S3 key prefix for pose data (default: aslavatarv2/gloss2pose/lookup/)

### Optional Variables
- `AWS_REGION`: AWS region (default: us-west-2)
- `MAX_TOKENS`: Maximum tokens for model responses (default: 3000)
- `TEMPERATURE`: Model temperature (default: 0.0)
- `TOP_P`: Model top-p parameter (default: 0.5)
- `LOG_LEVEL`: Logging level (default: INFO)
- `TIMEOUT_SECONDS`: Request timeout (default: 300)
- `MAX_RETRIES`: Maximum retry attempts (default: 3)
- `RETRY_DELAY`: Initial retry delay (default: 1.0)

## Tools

The agent includes the following Strands tools:

1. **text_to_asl_gloss**: Converts English text to ASL gloss notation
2. **gloss_to_video**: Converts ASL gloss to pose sequences and videos

## Usage

### Direct Invocation
```python
from signlanguageagent import invoke

payload = {
    "message": "Hello, how are you?",
    "type": "text",
    "metadata": {"user_id": "example_user"}
}

response = invoke(payload)
print(response)
```

### Health Check
```python
from signlanguageagent import health_check

status = health_check()
print(status)
```

## Deployment

The agent is deployed using AWS Bedrock AgentCore with the following configuration:

- **Platform**: linux/arm64
- **Runtime**: Docker container
- **Entry Point**: `signlanguageagent/slagent.py`
- **Observability**: Enabled with CloudWatch integration

### Docker Build

The agent is containerized using the provided Dockerfile:

```bash
docker build -t genasl-agent .
```

### AgentCore Configuration

The agent configuration is defined in `.bedrock_agentcore.yaml`:

- Agent ID: `slagent-4BncgN2p1h`
- Model: Amazon Nova Lite v1:0
- Tools: text2gloss, gloss2pose
- Network: Public mode
- Protocol: HTTP

## Testing

Run the test suite to validate the agent setup:

```bash
python test_agent.py
```

The test suite validates:
- Module imports
- Configuration loading
- Payload validation
- Agent initialization

## Error Handling

The agent implements comprehensive error handling:

- **Retry Logic**: Exponential backoff for transient failures
- **Validation**: Input payload validation with clear error messages
- **Logging**: Detailed error logging for debugging
- **Graceful Degradation**: Fallback responses when tools fail

## Monitoring

The agent provides monitoring capabilities:

- **Health Checks**: `/health` endpoint for status monitoring
- **Logging**: Structured logging with configurable levels
- **Metrics**: Integration with AWS CloudWatch
- **Tracing**: X-Ray tracing support (when enabled)

## Development

### Adding New Tools

To add new Strands tools:

1. Create the tool function with `@tool` decorator
2. Import the tool in `slagent.py`
3. Add the tool to the agent's tools list
4. Update the system prompt if needed

### Configuration Changes

To add new configuration options:

1. Update the configuration classes in `config.py`
2. Add environment variable handling
3. Update validation logic
4. Document the new options

### Testing

Always run the test suite after making changes:

```bash
python test_agent.py
```

For integration testing, deploy to a test environment and validate end-to-end functionality.

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed and paths are correct
2. **Configuration Errors**: Verify all required environment variables are set
3. **Tool Failures**: Check AWS permissions and service availability
4. **Memory Issues**: Adjust container memory allocation if needed

### Debugging

Enable debug logging by setting `LOG_LEVEL=DEBUG` to get detailed execution logs.

### Support

For issues and questions, refer to the main project documentation or contact the GenASL development team.