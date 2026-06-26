# AgentCore Migration Guide

## Overview
This document describes the migration from Lambda-based conversational agent to AWS Bedrock AgentCore deployed agent.

## Changes Made

### 1. Infrastructure Changes (resource.ts)

#### Audio2Sign Function
- **Removed**: `AGENT_FUNCTION_NAME` environment variable
- **Added**: AgentCore configuration environment variables:
  - `AGENTCORE_AGENT_ID`: `slagent-4BncgN2p1h`
  - `AGENTCORE_AGENT_ARN`: `arn:aws:bedrock-agentcore:us-west-2:853513360253:runtime/slagent-4BncgN2p1h`
  - `AGENTCORE_REGION`: `us-west-2`

- **IAM Permissions Updated**:
  - Removed: `lambda:InvokeFunction` permission
  - Added: `bedrock-agentcore:InvokeAgent` and `bedrock-agentcore:InvokeAgentStreaming` permissions

#### WebSocket OnDefaultFunction
- **Removed**: `AGENT_FUNCTION_NAME` environment variable
- **Added**: Same AgentCore configuration environment variables as Audio2Sign
- **IAM Permissions Updated**: Same as Audio2Sign function

### 2. WebSocket Handler Changes (handler.py)

#### Client Initialization
- **Removed**: Import and initialization of local Strands agent (`slagent.app`)
- **Added**: Boto3 client for `bedrock-agentcore-runtime`

#### Agent Invocation
- **Changed**: `agent_app.invoke()` → `bedrock_agentcore.invoke_agent()`
- **Parameters**:
  - `agentId`: The AgentCore agent ID
  - `sessionId`: Connection ID for session management
  - `inputText`: The user's message/request

#### Response Processing
- **Added**: `process_agentcore_response()` function to handle streaming responses
- Processes event stream chunks, traces, and return control events
- Attempts to parse JSON responses, falls back to plain text

### 3. Audio2Sign Handler Changes (audio2sign_handler.py)

#### Similar Changes to WebSocket Handler
- Replaced local agent import with AgentCore client
- Updated `build_agent_payload()` → `build_agent_input()` to return simple text input
- Added `process_agentcore_response()` for streaming response handling
- Updated all agent invocation calls to use `bedrock_agentcore.invoke_agent()`

## AgentCore Agent Details

### Deployed Agent Information
- **Agent ID**: `slagent-4BncgN2p1h`
- **Agent ARN**: `arn:aws:bedrock-agentcore:us-west-2:853513360253:runtime/slagent-4BncgN2p1h`
- **Region**: `us-west-2`
- **Execution Role**: `arn:aws:iam::853513360253:role/AmazonBedrockAgentCoreSDKRuntime-us-west-2-ae8ba35af8`
- **ECR Repository**: `853513360253.dkr.ecr.us-west-2.amazonaws.com/bedrock-agentcore-slagent`

### Agent Configuration
From `.bedrock_agentcore.yaml`:
- **Platform**: `linux/arm64`
- **Container Runtime**: Docker
- **Network Mode**: PUBLIC
- **Protocol**: HTTP
- **Observability**: Enabled with INFO log level

### Environment Variables
The agent has access to:
- `ENG_TO_ASL_MODEL`: `us.amazon.nova-lite-v1:0`
- `POSE_BUCKET`: `genasl-avatar`
- `ASL_DATA_BUCKET`: `genasl-data`
- `KEY_PREFIX`: `aslavatarv2/gloss2pose/lookup/`
- `TABLE_NAME`: `Pose_Data6`
- `AWS_REGION`: `us-west-2`
- `MAX_TOKENS`: `3000`
- `TEMPERATURE`: `0.0`

## API Compatibility

### Request Format
The API maintains backward compatibility. Requests can still use:
- Query parameters: `Text`, `Gloss`, `BucketName`, `KeyName`
- WebSocket messages: JSON or plain text

### Response Format
Responses are formatted to maintain compatibility with existing clients:
- URLs for generated videos (PoseURL, SignURL, AvatarURL)
- Gloss and Text fields
- Status and timestamp information

## Session Management

### WebSocket Sessions
- Session ID: Uses WebSocket connection ID
- Maintains conversation context across messages
- Automatic session cleanup on disconnect

### REST API Sessions
- Session ID: Uses API Gateway request ID
- Each request is independent but can reference previous context

## Deployment Steps

1. **Ensure AgentCore agent is deployed**:
   ```bash
   cd sample-genai-sign-language-translator/amplify/custom/functions
   # Deploy using bedrock-agentcore CLI or existing deployment
   ```

2. **Deploy Amplify backend**:
   ```bash
   cd sample-genai-sign-language-translator
   npx ampx sandbox
   # or
   npx ampx pipeline-deploy --branch <branch-name>
   ```

3. **Verify deployment**:
   - Check CloudWatch logs for AgentCore invocations
   - Test WebSocket connections
   - Test REST API endpoints

## Testing

### WebSocket Testing
```javascript
// Connect to WebSocket
const ws = new WebSocket('wss://your-websocket-url');

// Send text message
ws.send('Translate "hello" to ASL');

// Send structured message
ws.send(JSON.stringify({
  text: 'hello',
  type: 'text'
}));
```

### REST API Testing
```bash
# Text to ASL
curl -X POST "https://your-api-url/audio-to-sign?Text=hello"

# Gloss to video
curl -X POST "https://your-api-url/audio-to-sign?Gloss=HELLO+WORLD"

# Audio file processing
curl -X POST "https://your-api-url/audio-to-sign?BucketName=my-bucket&KeyName=audio.mp3"
```

## Monitoring

### CloudWatch Metrics
- Lambda function invocations and errors
- AgentCore agent invocations
- Response times and latencies

### CloudWatch Logs
- Lambda function logs: `/aws/lambda/OnDefaultFunction-*` and `/aws/lambda/Audio2SignFunction-*`
- AgentCore agent logs: Check AgentCore observability settings

### X-Ray Tracing
- End-to-end request tracing enabled
- Trace AgentCore invocations and responses

## Rollback Plan

If issues occur, you can rollback by:

1. **Revert code changes**:
   ```bash
   git revert <commit-hash>
   ```

2. **Redeploy previous version**:
   ```bash
   npx ampx sandbox
   ```

3. **Update environment variables** to point back to Lambda function if needed

## Benefits of AgentCore Migration

1. **Scalability**: AgentCore handles scaling automatically
2. **Observability**: Built-in logging and tracing
3. **Deployment**: Containerized deployment with ECR
4. **Session Management**: Native session handling
5. **Streaming**: Built-in support for streaming responses
6. **Cost Optimization**: Pay only for agent invocations

## Known Limitations

1. **Cold Starts**: Initial invocations may have higher latency
2. **Regional**: Agent is deployed in us-west-2 only
3. **Streaming**: Full streaming support requires client-side handling

## Support

For issues or questions:
- Check CloudWatch logs for error details
- Review AgentCore documentation
- Contact the development team
