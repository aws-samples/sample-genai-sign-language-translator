# Conversational ASL Agent Foundation

This module provides the foundational components for a conversational ASL translation agent with AgentCore Memory integration.

## Overview

The Conversational ASL Agent extends the existing SignLanguageAgent with enhanced conversational capabilities, context awareness, and session persistence using AgentCore Memory.

## Components

### 1. ConversationalASLAgent (`conversational_agent.py`)
The main agent class that provides conversational capabilities:
- Natural conversation flow management
- Context-aware interactions
- Session persistence across invocations
- Enhanced response formatting

### 2. ConversationMemoryManager (`memory_manager.py`)
Manages conversation data using AgentCore Memory:
- Session and context storage
- Memory key generation and management
- Data serialization/deserialization utilities
- Memory cleanup and lifecycle management

### 3. Data Models (`data_models.py`)
Comprehensive data structures for conversational interactions:
- `ConversationContext`: Session information and conversation state
- `ConversationInteraction`: Individual conversation exchanges
- `TranslationResult`: Translation operation results
- `IntentResult`: Intent classification results
- `ConversationIntent`: Enumeration of conversation intents

## Key Features

### AgentCore Memory Integration
- **Session Storage**: Persistent conversation contexts across invocations
- **Structured Keys**: Organized memory key patterns (`session:{id}:context`, etc.)
- **Automatic Cleanup**: TTL-based session lifecycle management
- **Data Serialization**: JSON serialization with datetime and enum handling

### Memory Key Patterns
```python
session:{session_id}:context          # Current conversation context
session:{session_id}:history          # Conversation interaction history
session:{session_id}:preferences      # User preferences and settings
session:{session_id}:last_result      # Most recent translation result
user:{user_id}:global_preferences     # Cross-session user preferences
```

### Conversation Context Management
- **Session Persistence**: Maintain context across multiple invocations
- **History Tracking**: Store and retrieve conversation interactions
- **User Preferences**: Remember user-specific settings and patterns
- **Error Tracking**: Monitor and respond to error patterns

## Usage Example

```python
from conversational_asl_agent import ConversationalASLAgent

# Initialize the agent
agent = ConversationalASLAgent()

# Handle a conversation
response = agent.handle_conversation(
    user_input="Hello, can you help me translate text to ASL?",
    session_id="user_session_123",
    user_id="user_456"
)

# Get session information
session_info = agent.get_session_info("user_session_123")

# Clean up when done
agent.cleanup_session("user_session_123")
```

## Data Model Examples

### Creating Translation Results
```python
from data_models import create_text_translation_result

result = create_text_translation_result(
    input_text="Hello world",
    gloss="HELLO WORLD",
    video_urls={
        "pose": "https://example.com/pose.mp4",
        "sign": "https://example.com/sign.mp4",
        "avatar": "https://example.com/avatar.mp4"
    },
    processing_time=1.5,
    success=True
)
```

### Working with Conversation Context
```python
from data_models import ConversationContext, ConversationInteraction, ConversationIntent

# Create context
context = ConversationContext(
    session_id="session_123",
    user_id="user_456"
)

# Add interaction
interaction = ConversationInteraction(
    timestamp=datetime.now(),
    user_input="Translate 'hello' to ASL",
    intent=ConversationIntent.TEXT_TO_ASL,
    agent_response="I'll translate that for you...",
    translation_result=result
)

context.add_interaction(interaction)
```

## Memory Manager Usage

```python
from memory_manager import ConversationMemoryManager

# Initialize memory manager
memory_manager = ConversationMemoryManager()

# Get or create conversation context
context = memory_manager.get_conversation_context("session_123", "user_456")

# Update context
memory_manager.update_conversation_context("session_123", context)

# Clean up session
memory_manager.cleanup_session("session_123")
```

## Integration with Existing SignLanguageAgent

This foundation is designed to enhance the existing SignLanguageAgent:

1. **Backward Compatibility**: Maintains existing API compatibility
2. **Enhanced Workflows**: Adds conversational orchestration to existing tools
3. **Memory Integration**: Provides persistent context across invocations
4. **Natural Responses**: Formats results into conversational language

## Next Steps

This foundation provides the core infrastructure for:

1. **Intent Classification**: Analyze user input to determine conversation intent
2. **Workflow Orchestration**: Coordinate translation workflows based on intent
3. **Response Formatting**: Generate natural conversational responses
4. **Error Handling**: Provide user-friendly error recovery
5. **Help System**: Offer contextual assistance and capability explanations

## Requirements Addressed

This implementation addresses the following requirements from the specification:

- **2.1**: Context management and session storage
- **2.2**: AgentCore Memory integration for persistence
- **2.3**: Conversation history and user preferences
- **2.4**: Memory key patterns and data organization
- **2.5**: Session lifecycle and cleanup management

## Testing

Run the basic functionality tests:

```bash
python test_basic_functionality.py
```

This validates:
- Data model creation and serialization
- Memory manager structure
- Agent initialization patterns
- Core functionality without full AgentCore integration

## Dependencies

- `bedrock_agentcore.runtime`: AgentCore Memory integration
- `dataclasses`: Data structure definitions
- `datetime`: Timestamp handling
- `json`: Data serialization
- `logging`: Structured logging
- `typing`: Type annotations

## Configuration

The memory manager uses the following default settings:
- **Session TTL**: 24 hours
- **History Limit**: 50 interactions per session
- **Cleanup Interval**: 1 hour

These can be configured during initialization or through environment variables in the full deployment.