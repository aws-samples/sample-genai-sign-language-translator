"""
Conversation Monitoring Module

This module provides comprehensive monitoring and observability for the conversational ASL agent,
including conversation metrics tracking, session lifecycle monitoring, and memory usage tracking.
"""

import logging
import time
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class ConversationMetricType(Enum):
    """Types of conversation metrics"""
    CONVERSATION_SUCCESS = "ConversationSuccess"
    CONVERSATION_FAILURE = "ConversationFailure"
    INTENT_CLASSIFICATION_ACCURACY = "IntentClassificationAccuracy"
    SESSIONS_CREATED = "SessionsCreated"
    SESSIONS_ACTIVE = "SessionsActive"
    SESSION_DURATION = "SessionDuration"
    MEMORY_USAGE = "MemoryUsage"
    RESPONSE_TIME = "ResponseTime"
    CONTEXT_RETRIEVAL_TIME = "ContextRetrievalTime"
    TRANSLATION_SUCCESS_RATE = "TranslationSuccessRate"
    ERROR_RECOVERY_SUCCESS = "ErrorRecoverySuccess"

@dataclass
class ConversationMetric:
    """Data class for conversation metrics"""
    metric_type: ConversationMetricType
    value: float
    unit: str
    timestamp: datetime
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    dimensions: Optional[Dict[str, str]] = None

@dataclass
class SessionLifecycleEvent:
    """Data class for session lifecycle events"""
    session_id: str
    event_type: str  # created, updated, expired, cleaned_up
    timestamp: datetime
    user_id: Optional[str] = None
    duration_seconds: Optional[float] = None
    interaction_count: Optional[int] = None
    memory_usage_mb: Optional[float] = None

class ConversationMonitoringManager:
    """
    Comprehensive monitoring manager for conversational ASL agent
    
    This class handles:
    - Conversation success/failure tracking
    - Intent classification accuracy monitoring
    - Session lifecycle monitoring
    - Memory usage tracking
    - Performance metrics collection
    - CloudWatch metrics publishing
    """
    
    def __init__(self, namespace: str = "GenASL/Conversation"):
        """
        Initialize monitoring manager
        
        Args:
            namespace: CloudWatch metrics namespace
        """
        self.namespace = namespace
        self.cloudwatch = boto3.client('cloudwatch')
        self.session_metrics: Dict[str, Dict[str, Any]] = {}
        self.active_sessions: Dict[str, datetime] = {}
        
        logger.info(f"ConversationMonitoringManager initialized with namespace: {namespace}")
    
    def track_conversation_start(self, session_id: str, user_id: Optional[str] = None,
                               intent: Optional[str] = None) -> str:
        """
        Track the start of a conversation
        
        Args:
            session_id: Session identifier
            user_id: Optional user identifier
            intent: Optional detected intent
        
        Returns:
            str: Operation ID for tracking
        """
        operation_id = f"conv_{session_id}_{int(time.time())}"
        
        # Track session creation
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = datetime.now()
            self._publish_metric(ConversationMetricType.SESSIONS_CREATED, 1, "Count", session_id, user_id)
            
            # Log session lifecycle event
            event = SessionLifecycleEvent(
                session_id=session_id,
                event_type="created",
                timestamp=datetime.now(),
                user_id=user_id
            )
            self._log_session_event(event)
        
        # Initialize session metrics
        self.session_metrics[operation_id] = {
            "session_id": session_id,
            "user_id": user_id,
            "intent": intent,
            "start_time": time.time(),
            "success": None,
            "error_count": 0,
            "intent_accuracy": None
        }
        
        # Update active sessions count
        self._publish_metric(ConversationMetricType.SESSIONS_ACTIVE, len(self.active_sessions), "Count")
        
        logger.info(f"Conversation tracking started: {operation_id}")
        return operation_id
    
    def track_conversation_success(self, operation_id: str, intent_accuracy: Optional[float] = None,
                                 translation_success: bool = True, response_time: Optional[float] = None):
        """
        Track successful conversation completion
        
        Args:
            operation_id: Operation identifier from track_conversation_start
            intent_accuracy: Optional intent classification accuracy (0-100)
            translation_success: Whether translation was successful
            response_time: Optional response time in seconds
        """
        if operation_id not in self.session_metrics:
            logger.warning(f"Operation ID not found for success tracking: {operation_id}")
            return
        
        metrics = self.session_metrics[operation_id]
        metrics["success"] = True
        
        session_id = metrics["session_id"]
        user_id = metrics["user_id"]
        
        # Track conversation success
        self._publish_metric(ConversationMetricType.CONVERSATION_SUCCESS, 1, "Count", session_id, user_id)
        
        # Track intent classification accuracy
        if intent_accuracy is not None:
            metrics["intent_accuracy"] = intent_accuracy
            self._publish_metric(ConversationMetricType.INTENT_CLASSIFICATION_ACCURACY, 
                               intent_accuracy, "Percent", session_id, user_id)
        
        # Track translation success rate
        if translation_success:
            self._publish_metric(ConversationMetricType.TRANSLATION_SUCCESS_RATE, 100, "Percent", session_id, user_id)
        else:
            self._publish_metric(ConversationMetricType.TRANSLATION_SUCCESS_RATE, 0, "Percent", session_id, user_id)
        
        # Track response time
        if response_time is not None:
            self._publish_metric(ConversationMetricType.RESPONSE_TIME, response_time, "Seconds", session_id, user_id)
        elif "start_time" in metrics:
            calculated_response_time = time.time() - metrics["start_time"]
            self._publish_metric(ConversationMetricType.RESPONSE_TIME, calculated_response_time, "Seconds", session_id, user_id)
        
        logger.info(f"Conversation success tracked: {operation_id}")
    
    def track_conversation_failure(self, operation_id: str, error: Exception, 
                                 error_recovery_attempted: bool = False,
                                 error_recovery_successful: bool = False):
        """
        Track conversation failure
        
        Args:
            operation_id: Operation identifier from track_conversation_start
            error: The error that occurred
            error_recovery_attempted: Whether error recovery was attempted
            error_recovery_successful: Whether error recovery was successful
        """
        if operation_id not in self.session_metrics:
            logger.warning(f"Operation ID not found for failure tracking: {operation_id}")
            return
        
        metrics = self.session_metrics[operation_id]
        metrics["success"] = False
        metrics["error_count"] += 1
        
        session_id = metrics["session_id"]
        user_id = metrics["user_id"]
        
        # Track conversation failure
        self._publish_metric(ConversationMetricType.CONVERSATION_FAILURE, 1, "Count", session_id, user_id)
        
        # Track error recovery if attempted
        if error_recovery_attempted:
            recovery_value = 1 if error_recovery_successful else 0
            self._publish_metric(ConversationMetricType.ERROR_RECOVERY_SUCCESS, recovery_value, "Count", session_id, user_id)
        
        logger.error(f"Conversation failure tracked: {operation_id}, error: {str(error)}")
    
    def track_session_lifecycle(self, session_id: str, event_type: str, 
                              interaction_count: Optional[int] = None,
                              memory_usage_mb: Optional[float] = None):
        """
        Track session lifecycle events
        
        Args:
            session_id: Session identifier
            event_type: Type of lifecycle event (updated, expired, cleaned_up)
            interaction_count: Number of interactions in session
            memory_usage_mb: Memory usage in MB
        """
        # Calculate session duration if ending
        duration_seconds = None
        if event_type in ["expired", "cleaned_up"] and session_id in self.active_sessions:
            start_time = self.active_sessions[session_id]
            duration_seconds = (datetime.now() - start_time).total_seconds()
            
            # Publish session duration metric
            self._publish_metric(ConversationMetricType.SESSION_DURATION, duration_seconds, "Seconds", session_id)
            
            # Remove from active sessions
            del self.active_sessions[session_id]
            
            # Update active sessions count
            self._publish_metric(ConversationMetricType.SESSIONS_ACTIVE, len(self.active_sessions), "Count")
        
        # Track memory usage
        if memory_usage_mb is not None:
            self._publish_metric(ConversationMetricType.MEMORY_USAGE, memory_usage_mb, "Megabytes", session_id)
        
        # Log session lifecycle event
        event = SessionLifecycleEvent(
            session_id=session_id,
            event_type=event_type,
            timestamp=datetime.now(),
            duration_seconds=duration_seconds,
            interaction_count=interaction_count,
            memory_usage_mb=memory_usage_mb
        )
        self._log_session_event(event)
        
        logger.info(f"Session lifecycle tracked: {session_id}, event: {event_type}")
    
    def track_context_retrieval_performance(self, session_id: str, retrieval_time: float,
                                          context_size_kb: Optional[float] = None):
        """
        Track context retrieval performance
        
        Args:
            session_id: Session identifier
            retrieval_time: Time taken to retrieve context in seconds
            context_size_kb: Size of retrieved context in KB
        """
        self._publish_metric(ConversationMetricType.CONTEXT_RETRIEVAL_TIME, retrieval_time, "Seconds", session_id)
        
        if context_size_kb is not None:
            # Custom metric for context size
            self._publish_custom_metric("ContextSize", context_size_kb, "Kilobytes", session_id)
        
        logger.debug(f"Context retrieval performance tracked: {session_id}, time: {retrieval_time}s")
    
    def get_conversation_quality_metrics(self, time_range_hours: int = 24) -> Dict[str, Any]:
        """
        Get conversation quality metrics for the specified time range
        
        Args:
            time_range_hours: Time range in hours to analyze
        
        Returns:
            Dict containing quality metrics
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=time_range_hours)
        
        try:
            # Get conversation success rate
            success_data = self._get_metric_statistics(
                ConversationMetricType.CONVERSATION_SUCCESS, start_time, end_time, "Sum"
            )
            failure_data = self._get_metric_statistics(
                ConversationMetricType.CONVERSATION_FAILURE, start_time, end_time, "Sum"
            )
            
            total_conversations = success_data + failure_data
            success_rate = (success_data / total_conversations * 100) if total_conversations > 0 else 0
            
            # Get intent classification accuracy
            intent_accuracy = self._get_metric_statistics(
                ConversationMetricType.INTENT_CLASSIFICATION_ACCURACY, start_time, end_time, "Average"
            )
            
            # Get average response time
            avg_response_time = self._get_metric_statistics(
                ConversationMetricType.RESPONSE_TIME, start_time, end_time, "Average"
            )
            
            # Get session metrics
            avg_session_duration = self._get_metric_statistics(
                ConversationMetricType.SESSION_DURATION, start_time, end_time, "Average"
            )
            
            return {
                "time_range_hours": time_range_hours,
                "total_conversations": total_conversations,
                "success_rate_percent": success_rate,
                "intent_classification_accuracy_percent": intent_accuracy,
                "average_response_time_seconds": avg_response_time,
                "average_session_duration_seconds": avg_session_duration,
                "active_sessions_count": len(self.active_sessions)
            }
            
        except Exception as e:
            logger.error(f"Error getting conversation quality metrics: {e}")
            return {"error": str(e)}
    
    def cleanup_expired_sessions(self, max_age_hours: int = 2):
        """
        Clean up expired sessions from monitoring
        
        Args:
            max_age_hours: Maximum age of sessions to keep active
        """
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        expired_sessions = []
        
        for session_id, start_time in self.active_sessions.items():
            if start_time < cutoff_time:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            self.track_session_lifecycle(session_id, "expired")
        
        logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
    
    def _publish_metric(self, metric_type: ConversationMetricType, value: float, unit: str,
                       session_id: Optional[str] = None, user_id: Optional[str] = None):
        """
        Publish metric to CloudWatch
        
        Args:
            metric_type: Type of metric
            value: Metric value
            unit: Metric unit
            session_id: Optional session ID for dimensions
            user_id: Optional user ID for dimensions
        """
        try:
            dimensions = []
            if session_id:
                dimensions.append({"Name": "SessionId", "Value": session_id})
            if user_id:
                dimensions.append({"Name": "UserId", "Value": user_id})
            
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[
                    {
                        "MetricName": metric_type.value,
                        "Value": value,
                        "Unit": unit,
                        "Timestamp": datetime.now(),
                        "Dimensions": dimensions
                    }
                ]
            )
            
        except ClientError as e:
            logger.error(f"Error publishing metric {metric_type.value}: {e}")
    
    def _publish_custom_metric(self, metric_name: str, value: float, unit: str,
                             session_id: Optional[str] = None):
        """
        Publish custom metric to CloudWatch
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Metric unit
            session_id: Optional session ID for dimensions
        """
        try:
            dimensions = []
            if session_id:
                dimensions.append({"Name": "SessionId", "Value": session_id})
            
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[
                    {
                        "MetricName": metric_name,
                        "Value": value,
                        "Unit": unit,
                        "Timestamp": datetime.now(),
                        "Dimensions": dimensions
                    }
                ]
            )
            
        except ClientError as e:
            logger.error(f"Error publishing custom metric {metric_name}: {e}")
    
    def _get_metric_statistics(self, metric_type: ConversationMetricType, 
                             start_time: datetime, end_time: datetime, 
                             statistic: str) -> float:
        """
        Get metric statistics from CloudWatch
        
        Args:
            metric_type: Type of metric
            start_time: Start time for query
            end_time: End time for query
            statistic: Statistic type (Sum, Average, etc.)
        
        Returns:
            float: Metric value
        """
        try:
            response = self.cloudwatch.get_metric_statistics(
                Namespace=self.namespace,
                MetricName=metric_type.value,
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,  # 1 hour periods
                Statistics=[statistic]
            )
            
            if response["Datapoints"]:
                return sum(dp[statistic] for dp in response["Datapoints"]) / len(response["Datapoints"])
            return 0.0
            
        except ClientError as e:
            logger.error(f"Error getting metric statistics for {metric_type.value}: {e}")
            return 0.0
    
    def _log_session_event(self, event: SessionLifecycleEvent):
        """
        Log session lifecycle event
        
        Args:
            event: Session lifecycle event to log
        """
        event_data = asdict(event)
        event_data["timestamp"] = event.timestamp.isoformat()
        
        logger.info(f"Session lifecycle event: {json.dumps(event_data)}")

# Global monitoring manager instance
conversation_monitoring = ConversationMonitoringManager()

def get_monitoring_manager() -> ConversationMonitoringManager:
    """
    Get the global monitoring manager instance
    
    Returns:
        ConversationMonitoringManager: The monitoring manager
    """
    return conversation_monitoring

# Convenience functions for easy monitoring integration
def track_conversation_start(session_id: str, user_id: Optional[str] = None, 
                           intent: Optional[str] = None) -> str:
    """Convenience function to track conversation start"""
    return conversation_monitoring.track_conversation_start(session_id, user_id, intent)

def track_conversation_success(operation_id: str, intent_accuracy: Optional[float] = None,
                             translation_success: bool = True, response_time: Optional[float] = None):
    """Convenience function to track conversation success"""
    conversation_monitoring.track_conversation_success(operation_id, intent_accuracy, translation_success, response_time)

def track_conversation_failure(operation_id: str, error: Exception, 
                             error_recovery_attempted: bool = False,
                             error_recovery_successful: bool = False):
    """Convenience function to track conversation failure"""
    conversation_monitoring.track_conversation_failure(operation_id, error, error_recovery_attempted, error_recovery_successful)

def track_session_lifecycle(session_id: str, event_type: str, 
                          interaction_count: Optional[int] = None,
                          memory_usage_mb: Optional[float] = None):
    """Convenience function to track session lifecycle"""
    conversation_monitoring.track_session_lifecycle(session_id, event_type, interaction_count, memory_usage_mb)

def get_conversation_quality_metrics(time_range_hours: int = 24) -> Dict[str, Any]:
    """Convenience function to get conversation quality metrics"""
    return conversation_monitoring.get_conversation_quality_metrics(time_range_hours)