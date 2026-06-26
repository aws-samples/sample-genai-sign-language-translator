"""
Conversation Data Models

This module defines data classes and enums for conversational ASL agent interactions,
including conversation context, interactions, translation results, and intent classification.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional

class ConversationIntent(Enum):
    """Enumeration of conversation intents"""
    TEXT_TO_ASL = "text_to_asl"
    AUDIO_TO_ASL = "audio_to_asl"
    ASL_TO_TEXT = "asl_to_text"
    HELP_REQUEST = "help_request"
    STATUS_CHECK = "status_check"
    RETRY_REQUEST = "retry_request"
    CONTEXT_REFERENCE = "context_reference"
    GREETING = "greeting"
    UNKNOWN = "unknown"

class InputType(Enum):
    """Enumeration of input types"""
    TEXT = "text"
    AUDIO = "audio"
    VIDEO = "video"
    STREAM = "stream"
    IMAGE = "image"
    UNKNOWN = "unknown"

class TranslationStatus(Enum):
    """Enumeration of translation status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class TranslationResult:
    """
    Data class representing a translation result
    
    Contains all information about a completed (or attempted) translation,
    including input, output, metadata, and status information.
    """
    input_text: Optional[str] = None
    input_type: InputType = InputType.UNKNOWN
    gloss: Optional[str] = None
    video_urls: Dict[str, str] = field(default_factory=dict)  # pose, sign, avatar URLs
    interpreted_text: Optional[str] = None  # for ASL-to-text translations
    processing_time: float = 0.0
    success: bool = False
    error_message: Optional[str] = None
    status: TranslationStatus = TranslationStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = {
            'input_text': self.input_text,
            'input_type': self.input_type.value if self.input_type else None,
            'gloss': self.gloss,
            'video_urls': self.video_urls,
            'interpreted_text': self.interpreted_text,
            'processing_time': self.processing_time,
            'success': self.success,
            'error_message': self.error_message,
            'status': self.status.value if self.status else None,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TranslationResult':
        """Create from dictionary for deserialization"""
        # Convert enum strings back to enums
        if 'input_type' in data and data['input_type']:
            data['input_type'] = InputType(data['input_type'])
        if 'status' in data and data['status']:
            data['status'] = TranslationStatus(data['status'])
        if 'timestamp' in data and data['timestamp']:
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        
        return cls(**data)

@dataclass
class IntentResult:
    """
    Data class representing intent classification result
    
    Contains the classified intent, confidence score, extracted parameters,
    and additional context information.
    """
    intent: ConversationIntent
    confidence: float
    parameters: Dict[str, Any] = field(default_factory=dict)
    input_type: InputType = InputType.UNKNOWN
    requires_context: bool = False
    alternative_intents: List[tuple] = field(default_factory=list)  # (intent, confidence) pairs
    reasoning: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'intent': self.intent.value,
            'confidence': self.confidence,
            'parameters': self.parameters,
            'input_type': self.input_type.value,
            'requires_context': self.requires_context,
            'alternative_intents': [(intent.value, conf) for intent, conf in self.alternative_intents],
            'reasoning': self.reasoning
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IntentResult':
        """Create from dictionary for deserialization"""
        # Convert enum strings back to enums
        data['intent'] = ConversationIntent(data['intent'])
        data['input_type'] = InputType(data['input_type'])
        
        # Convert alternative intents back to enum tuples
        if 'alternative_intents' in data:
            data['alternative_intents'] = [
                (ConversationIntent(intent), conf) 
                for intent, conf in data['alternative_intents']
            ]
        
        return cls(**data)

@dataclass
class ConversationInteraction:
    """
    Data class representing a single conversation interaction
    
    Contains the user input, agent response, intent classification,
    translation result, and interaction metadata.
    """
    timestamp: datetime
    user_input: str
    intent: ConversationIntent
    agent_response: str
    translation_result: Optional[TranslationResult] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    processing_time: float = 0.0
    error_occurred: bool = False
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = {
            'timestamp': self.timestamp.isoformat(),
            'user_input': self.user_input,
            'intent': self.intent.value,
            'agent_response': self.agent_response,
            'translation_result': self.translation_result.to_dict() if self.translation_result else None,
            'metadata': self.metadata,
            'processing_time': self.processing_time,
            'error_occurred': self.error_occurred,
            'error_message': self.error_message
        }
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationInteraction':
        """Create from dictionary for deserialization"""
        # Convert timestamp string back to datetime
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        
        # Convert intent string back to enum
        data['intent'] = ConversationIntent(data['intent'])
        
        # Convert translation result back to object
        if data.get('translation_result'):
            data['translation_result'] = TranslationResult.from_dict(data['translation_result'])
        
        return cls(**data)

@dataclass
class ConversationContext:
    """
    Data class representing conversation context and state
    
    Contains session information, conversation history, user preferences,
    and current conversation state for context-aware interactions.
    """
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    session_start_time: datetime = field(default_factory=datetime.now)
    last_activity_time: datetime = field(default_factory=datetime.now)
    conversation_history: List[ConversationInteraction] = field(default_factory=list)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    last_translation: Optional[TranslationResult] = None
    current_operations: List[str] = field(default_factory=list)
    error_count: int = 0
    total_interactions: int = 0
    
    def add_interaction(self, interaction: ConversationInteraction) -> None:
        """Add a new interaction to the conversation history"""
        self.conversation_history.append(interaction)
        self.total_interactions += 1
        self.last_activity_time = datetime.now()
        
        if interaction.error_occurred:
            self.error_count += 1
        
        # Update last translation if present
        if interaction.translation_result:
            self.last_translation = interaction.translation_result
    
    def get_recent_interactions(self, count: int = 5) -> List[ConversationInteraction]:
        """Get the most recent interactions"""
        return self.conversation_history[-count:] if self.conversation_history else []
    
    def get_interactions_by_intent(self, intent: ConversationIntent) -> List[ConversationInteraction]:
        """Get all interactions with a specific intent"""
        return [interaction for interaction in self.conversation_history 
                if interaction.intent == intent]
    
    def get_successful_translations(self) -> List[ConversationInteraction]:
        """Get all interactions that resulted in successful translations"""
        return [interaction for interaction in self.conversation_history 
                if interaction.translation_result and interaction.translation_result.success]
    
    def get_session_duration(self) -> float:
        """Get session duration in seconds"""
        return (self.last_activity_time - self.session_start_time).total_seconds()
    
    def get_error_rate(self) -> float:
        """Get error rate as a percentage"""
        if self.total_interactions == 0:
            return 0.0
        return (self.error_count / self.total_interactions) * 100
    
    def update_user_preference(self, key: str, value: Any) -> None:
        """Update a user preference"""
        self.user_preferences[key] = value
        self.last_activity_time = datetime.now()
    
    def get_user_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference with optional default"""
        return self.user_preferences.get(key, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'session_start_time': self.session_start_time.isoformat(),
            'last_activity_time': self.last_activity_time.isoformat(),
            'conversation_history': [interaction.to_dict() for interaction in self.conversation_history],
            'user_preferences': self.user_preferences,
            'last_translation': self.last_translation.to_dict() if self.last_translation else None,
            'current_operations': self.current_operations,
            'error_count': self.error_count,
            'total_interactions': self.total_interactions
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationContext':
        """Create from dictionary for deserialization"""
        # Convert timestamp strings back to datetime objects
        data['session_start_time'] = datetime.fromisoformat(data['session_start_time'])
        data['last_activity_time'] = datetime.fromisoformat(data['last_activity_time'])
        
        # Convert conversation history back to objects
        if 'conversation_history' in data:
            data['conversation_history'] = [
                ConversationInteraction.from_dict(interaction_data)
                for interaction_data in data['conversation_history']
            ]
        
        # Convert last translation back to object
        if data.get('last_translation'):
            data['last_translation'] = TranslationResult.from_dict(data['last_translation'])
        
        return cls(**data)

@dataclass
class OperationStatus:
    """
    Data class representing the status of an ongoing operation
    
    Used for tracking long-running translation operations and providing
    status updates to users.
    """
    operation_id: str
    operation_type: str
    status: TranslationStatus
    progress: float = 0.0  # 0.0 to 1.0
    current_step: Optional[str] = None
    estimated_completion: Optional[datetime] = None
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result: Optional[TranslationResult] = None
    
    def update_progress(self, progress: float, current_step: Optional[str] = None) -> None:
        """Update operation progress"""
        self.progress = max(0.0, min(1.0, progress))  # Clamp between 0 and 1
        if current_step:
            self.current_step = current_step
    
    def mark_completed(self, result: Optional[TranslationResult] = None) -> None:
        """Mark operation as completed"""
        self.status = TranslationStatus.COMPLETED
        self.progress = 1.0
        self.completed_at = datetime.now()
        if result:
            self.result = result
    
    def mark_failed(self, error_message: str) -> None:
        """Mark operation as failed"""
        self.status = TranslationStatus.FAILED
        self.completed_at = datetime.now()
        self.error_message = error_message
    
    def get_duration(self) -> float:
        """Get operation duration in seconds"""
        end_time = self.completed_at or datetime.now()
        return (end_time - self.started_at).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'operation_id': self.operation_id,
            'operation_type': self.operation_type,
            'status': self.status.value,
            'progress': self.progress,
            'current_step': self.current_step,
            'estimated_completion': self.estimated_completion.isoformat() if self.estimated_completion else None,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error_message': self.error_message,
            'result': self.result.to_dict() if self.result else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OperationStatus':
        """Create from dictionary for deserialization"""
        # Convert enum string back to enum
        data['status'] = TranslationStatus(data['status'])
        
        # Convert timestamp strings back to datetime objects
        data['started_at'] = datetime.fromisoformat(data['started_at'])
        if data.get('completed_at'):
            data['completed_at'] = datetime.fromisoformat(data['completed_at'])
        if data.get('estimated_completion'):
            data['estimated_completion'] = datetime.fromisoformat(data['estimated_completion'])
        
        # Convert result back to object
        if data.get('result'):
            data['result'] = TranslationResult.from_dict(data['result'])
        
        return cls(**data)

# Utility functions for data model operations

def create_text_translation_result(input_text: str, gloss: str, video_urls: Dict[str, str], 
                                 processing_time: float = 0.0, success: bool = True,
                                 error_message: Optional[str] = None) -> TranslationResult:
    """
    Create a TranslationResult for text-to-ASL translation
    
    Args:
        input_text: The original input text
        gloss: The generated ASL gloss
        video_urls: Dictionary of video URLs (pose, sign, avatar)
        processing_time: Time taken for processing
        success: Whether the translation was successful
        error_message: Optional error message if translation failed
    
    Returns:
        TranslationResult: Configured translation result
    """
    return TranslationResult(
        input_text=input_text,
        input_type=InputType.TEXT,
        gloss=gloss,
        video_urls=video_urls,
        processing_time=processing_time,
        success=success,
        error_message=error_message,
        status=TranslationStatus.COMPLETED if success else TranslationStatus.FAILED,
        timestamp=datetime.now()
    )

def create_audio_translation_result(input_text: str, transcribed_text: str, gloss: str, 
                                  video_urls: Dict[str, str], processing_time: float = 0.0,
                                  success: bool = True, error_message: Optional[str] = None) -> TranslationResult:
    """
    Create a TranslationResult for audio-to-ASL translation
    
    Args:
        input_text: The original audio file reference
        transcribed_text: The transcribed text from audio
        gloss: The generated ASL gloss
        video_urls: Dictionary of video URLs (pose, sign, avatar)
        processing_time: Time taken for processing
        success: Whether the translation was successful
        error_message: Optional error message if translation failed
    
    Returns:
        TranslationResult: Configured translation result
    """
    return TranslationResult(
        input_text=input_text,
        input_type=InputType.AUDIO,
        gloss=gloss,
        video_urls=video_urls,
        interpreted_text=transcribed_text,  # Store transcribed text
        processing_time=processing_time,
        success=success,
        error_message=error_message,
        status=TranslationStatus.COMPLETED if success else TranslationStatus.FAILED,
        metadata={'transcribed_text': transcribed_text},
        timestamp=datetime.now()
    )

def create_asl_analysis_result(input_reference: str, interpreted_text: str, 
                             processing_time: float = 0.0, success: bool = True,
                             error_message: Optional[str] = None, 
                             input_type: InputType = InputType.VIDEO) -> TranslationResult:
    """
    Create a TranslationResult for ASL-to-text analysis
    
    Args:
        input_reference: Reference to the input video/stream
        interpreted_text: The interpreted English text
        processing_time: Time taken for processing
        success: Whether the analysis was successful
        error_message: Optional error message if analysis failed
        input_type: Type of input (VIDEO or STREAM)
    
    Returns:
        TranslationResult: Configured translation result
    """
    return TranslationResult(
        input_text=input_reference,
        input_type=input_type,
        interpreted_text=interpreted_text,
        processing_time=processing_time,
        success=success,
        error_message=error_message,
        status=TranslationStatus.COMPLETED if success else TranslationStatus.FAILED,
        timestamp=datetime.now()
    )