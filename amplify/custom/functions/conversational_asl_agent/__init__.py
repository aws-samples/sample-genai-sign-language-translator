"""
Conversational ASL Agent Module

This module provides enhanced conversational capabilities for ASL translation
services, building upon the existing SignLanguageAgent infrastructure.

The main entry point is provided by ConversationalASLAgentMain, which maintains
backward compatibility with the existing SignLanguageAgent interface while
providing enhanced conversational capabilities.
"""

from .conversational_agent import ConversationalASLAgent
from .conversational_asl_agent_main import (
    ConversationalASLAgentMain,
    conversational_asl_agent,
    invoke,
    health_check
)
from .memory_manager import ConversationMemoryManager
from .data_models import (
    ConversationContext,
    ConversationInteraction,
    TranslationResult,
    IntentResult,
    ConversationIntent
)

__all__ = [
    'ConversationalASLAgent',
    'ConversationalASLAgentMain',
    'conversational_asl_agent',
    'invoke',
    'health_check',
    'ConversationMemoryManager',
    'ConversationContext',
    'ConversationInteraction',
    'TranslationResult',
    'IntentResult',
    'ConversationIntent'
]