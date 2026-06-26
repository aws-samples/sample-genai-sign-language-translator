"""
Progress Tracking and Status Management

This module provides progress tracking and status update capabilities for long-running
translation operations, with AgentCore Memory integration for persistent status storage.
"""

import logging
import time
import logging
import json
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timedelta
from dataclasses import asdict

try:
    from .data_models import (
        OperationStatus,
        TranslationStatus,
        TranslationResult
    )
    from .memory_manager import ConversationMemoryManager
except ImportError:
    from data_models import (
        OperationStatus,
        TranslationStatus,
        TranslationResult
    )
    from memory_manager import ConversationMemoryManager

logger = logging.getLogger(__name__)

class ProgressTracker:
    """
    Tracks progress of long-running operations and provides status updates
    
    Integrates with AgentCore Memory for persistent operation tracking and
    provides callback system for real-time progress updates.
    """
    
    def __init__(self, memory_manager: Optional[ConversationMemoryManager] = None):
        """
        Initialize progress tracker
        
        Args:
            memory_manager: Optional memory manager for persistent storage
        """
        self.memory_manager = memory_manager or ConversationMemoryManager()
        self.progress_callbacks: Dict[str, List[Callable]] = {}
        self.status_update_threshold = 3.0  # seconds - when to start providing status updates
        
        logger.info("ProgressTracker initialized with AgentCore Memory integration")
    
    def start_operation(self, operation_id: str, operation_type: str, 
                       session_id: Optional[str] = None,
                       estimated_duration: Optional[float] = None) -> OperationStatus:
        """
        Start tracking a new operation
        
        Args:
            operation_id: Unique operation identifier
            operation_type: Type of operation (e.g., 'text_to_asl', 'audio_to_asl')
            session_id: Optional session ID for context
            estimated_duration: Optional estimated duration in seconds
        
        Returns:
            OperationStatus: Created operation status
        """
        try:
            # Create operation status
            operation_status = OperationStatus(
                operation_id=operation_id,
                operation_type=operation_type,
                status=TranslationStatus.IN_PROGRESS,
                started_at=datetime.now()
            )
            
            if estimated_duration:
                operation_status.estimated_completion = (
                    datetime.now() + timedelta(seconds=estimated_duration)
                )
            
            # Store in memory if session provided
            if session_id:
                self._store_operation_status(session_id, operation_status)
            
            logger.info(f"Started tracking operation: {operation_id} ({operation_type})")
            return operation_status
            
        except Exception as e:
            logger.error(f"Failed to start operation tracking: {e}")
            raise
    
    def update_progress(self, operation_id: str, progress: float, 
                       current_step: Optional[str] = None,
                       session_id: Optional[str] = None) -> None:
        """
        Update operation progress
        
        Args:
            operation_id: Operation identifier
            progress: Progress value (0.0 to 1.0)
            current_step: Optional description of current step
            session_id: Optional session ID for persistent storage
        """
        try:
            # Clamp progress between 0 and 1
            progress = max(0.0, min(1.0, progress))
            
            # Get operation status
            operation_status = None
            if session_id:
                operation_status = self._get_operation_status(session_id, operation_id)
            
            if operation_status:
                # Update existing status
                operation_status.update_progress(progress, current_step)
                self._store_operation_status(session_id, operation_status)
            
            # Trigger progress callbacks
            self._trigger_progress_callbacks(operation_id, progress, current_step)
            
            # Check if we should provide status updates
            if operation_status and self._should_provide_status_update(operation_status):
                self._generate_status_update(operation_status, session_id)
            
            logger.debug(f"Updated progress for {operation_id}: {progress:.1%} - {current_step or 'N/A'}")
            
        except Exception as e:
            logger.warning(f"Failed to update progress for {operation_id}: {e}")
    
    def complete_operation(self, operation_id: str, result: Optional[TranslationResult] = None,
                          session_id: Optional[str] = None) -> None:
        """
        Mark operation as completed
        
        Args:
            operation_id: Operation identifier
            result: Optional translation result
            session_id: Optional session ID for persistent storage
        """
        try:
            if session_id:
                operation_status = self._get_operation_status(session_id, operation_id)
                if operation_status:
                    operation_status.mark_completed(result)
                    self._store_operation_status(session_id, operation_status)
                    
                    # Generate completion status update
                    self._generate_completion_update(operation_status, session_id)
            
            # Trigger completion callbacks
            self._trigger_completion_callbacks(operation_id, result)
            
            # Clean up callbacks
            if operation_id in self.progress_callbacks:
                del self.progress_callbacks[operation_id]
            
            logger.info(f"Completed operation: {operation_id}")
            
        except Exception as e:
            logger.warning(f"Failed to complete operation {operation_id}: {e}")
    
    def fail_operation(self, operation_id: str, error_message: str,
                      session_id: Optional[str] = None) -> None:
        """
        Mark operation as failed
        
        Args:
            operation_id: Operation identifier
            error_message: Error description
            session_id: Optional session ID for persistent storage
        """
        try:
            if session_id:
                operation_status = self._get_operation_status(session_id, operation_id)
                if operation_status:
                    operation_status.mark_failed(error_message)
                    self._store_operation_status(session_id, operation_status)
                    
                    # Generate failure status update
                    self._generate_failure_update(operation_status, session_id)
            
            # Trigger failure callbacks
            self._trigger_failure_callbacks(operation_id, error_message)
            
            # Clean up callbacks
            if operation_id in self.progress_callbacks:
                del self.progress_callbacks[operation_id]
            
            logger.info(f"Failed operation: {operation_id} - {error_message}")
            
        except Exception as e:
            logger.warning(f"Failed to mark operation as failed {operation_id}: {e}")
    
    def add_progress_callback(self, operation_id: str, 
                            callback: Callable[[float, Optional[str]], None]) -> None:
        """
        Add progress callback for an operation
        
        Args:
            operation_id: Operation identifier
            callback: Callback function that receives (progress, current_step)
        """
        if operation_id not in self.progress_callbacks:
            self.progress_callbacks[operation_id] = []
        
        self.progress_callbacks[operation_id].append(callback)
        logger.debug(f"Added progress callback for operation: {operation_id}")
    
    def get_operation_status(self, operation_id: str, 
                           session_id: Optional[str] = None) -> Optional[OperationStatus]:
        """
        Get current status of an operation
        
        Args:
            operation_id: Operation identifier
            session_id: Optional session ID for persistent lookup
        
        Returns:
            OperationStatus or None if not found
        """
        if session_id:
            return self._get_operation_status(session_id, operation_id)
        return None
    
    def get_active_operations(self, session_id: str) -> List[OperationStatus]:
        """
        Get all active operations for a session
        
        Args:
            session_id: Session identifier
        
        Returns:
            List of active operation statuses
        """
        try:
            # Get all operations for session
            operations_key = f"session:{session_id}:operations"
            operations_data = self.memory_manager.memory.retrieve(operations_key)
            
            if not operations_data:
                return []
            
            # Parse and filter active operations
            active_operations = []
            for op_data in operations_data:
                try:
                    operation_status = OperationStatus.from_dict(op_data)
                    if operation_status.status in [TranslationStatus.PENDING, TranslationStatus.IN_PROGRESS]:
                        active_operations.append(operation_status)
                except Exception as e:
                    logger.warning(f"Failed to parse operation data: {e}")
            
            return active_operations
            
        except Exception as e:
            logger.error(f"Failed to get active operations for session {session_id}: {e}")
            return []
    
    def cleanup_completed_operations(self, session_id: str, 
                                   max_age_hours: int = 24) -> int:
        """
        Clean up completed operations older than specified age
        
        Args:
            session_id: Session identifier
            max_age_hours: Maximum age in hours for completed operations
        
        Returns:
            int: Number of operations cleaned up
        """
        try:
            operations_key = f"session:{session_id}:operations"
            operations_data = self.memory_manager.memory.retrieve(operations_key)
            
            if not operations_data:
                return 0
            
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            cleaned_count = 0
            remaining_operations = []
            
            for op_data in operations_data:
                try:
                    operation_status = OperationStatus.from_dict(op_data)
                    
                    # Keep if active or recent
                    if (operation_status.status in [TranslationStatus.PENDING, TranslationStatus.IN_PROGRESS] or
                        (operation_status.completed_at and operation_status.completed_at > cutoff_time)):
                        remaining_operations.append(op_data)
                    else:
                        cleaned_count += 1
                        
                except Exception as e:
                    logger.warning(f"Failed to parse operation for cleanup: {e}")
                    # Keep unparseable operations to avoid data loss
                    remaining_operations.append(op_data)
            
            # Store cleaned operations list
            if remaining_operations != operations_data:
                self.memory_manager.memory.store(operations_key, remaining_operations)
            
            logger.info(f"Cleaned up {cleaned_count} completed operations for session {session_id}")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup operations for session {session_id}: {e}")
            return 0
    
    def _store_operation_status(self, session_id: str, operation_status: OperationStatus) -> None:
        """Store operation status in memory"""
        try:
            operations_key = f"session:{session_id}:operations"
            
            # Get existing operations
            operations_data = self.memory_manager.memory.retrieve(operations_key) or []
            
            # Update or add operation
            operation_dict = operation_status.to_dict()
            updated = False
            
            for i, op_data in enumerate(operations_data):
                if op_data.get('operation_id') == operation_status.operation_id:
                    operations_data[i] = operation_dict
                    updated = True
                    break
            
            if not updated:
                operations_data.append(operation_dict)
            
            # Store updated operations
            self.memory_manager.memory.store(operations_key, operations_data)
            
        except Exception as e:
            logger.error(f"Failed to store operation status: {e}")
    
    def _get_operation_status(self, session_id: str, operation_id: str) -> Optional[OperationStatus]:
        """Get operation status from memory"""
        try:
            operations_key = f"session:{session_id}:operations"
            operations_data = self.memory_manager.memory.retrieve(operations_key)
            
            if not operations_data:
                return None
            
            for op_data in operations_data:
                if op_data.get('operation_id') == operation_id:
                    return OperationStatus.from_dict(op_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get operation status: {e}")
            return None
    
    def _should_provide_status_update(self, operation_status: OperationStatus) -> bool:
        """Check if we should provide a status update"""
        duration = operation_status.get_duration()
        return duration >= self.status_update_threshold
    
    def _generate_status_update(self, operation_status: OperationStatus, session_id: str) -> None:
        """Generate and store status update message"""
        try:
            duration = operation_status.get_duration()
            progress_percent = int(operation_status.progress * 100)
            
            if operation_status.current_step:
                message = (f"Status update: {operation_status.current_step} "
                          f"({progress_percent}% complete, {duration:.1f}s elapsed)")
            else:
                message = (f"Status update: {operation_status.operation_type} "
                          f"({progress_percent}% complete, {duration:.1f}s elapsed)")
            
            # Store status update in memory
            self._store_status_message(session_id, operation_status.operation_id, message)
            
        except Exception as e:
            logger.warning(f"Failed to generate status update: {e}")
    
    def _generate_completion_update(self, operation_status: OperationStatus, session_id: str) -> None:
        """Generate completion status update"""
        try:
            duration = operation_status.get_duration()
            message = f"✅ {operation_status.operation_type} completed successfully in {duration:.1f}s"
            
            self._store_status_message(session_id, operation_status.operation_id, message)
            
        except Exception as e:
            logger.warning(f"Failed to generate completion update: {e}")
    
    def _generate_failure_update(self, operation_status: OperationStatus, session_id: str) -> None:
        """Generate failure status update"""
        try:
            duration = operation_status.get_duration()
            message = (f"❌ {operation_status.operation_type} failed after {duration:.1f}s: "
                      f"{operation_status.error_message}")
            
            self._store_status_message(session_id, operation_status.operation_id, message)
            
        except Exception as e:
            logger.warning(f"Failed to generate failure update: {e}")
    
    def _store_status_message(self, session_id: str, operation_id: str, message: str) -> None:
        """Store status message in memory"""
        try:
            status_key = f"session:{session_id}:status_updates"
            
            # Get existing status updates
            status_updates = self.memory_manager.memory.retrieve(status_key) or []
            
            # Add new status update
            status_update = {
                'operation_id': operation_id,
                'message': message,
                'timestamp': datetime.now().isoformat()
            }
            
            status_updates.append(status_update)
            
            # Keep only recent status updates (last 50)
            if len(status_updates) > 50:
                status_updates = status_updates[-50:]
            
            # Store updated status updates
            self.memory_manager.memory.store(status_key, status_updates)
            
        except Exception as e:
            logger.error(f"Failed to store status message: {e}")
    
    def get_recent_status_updates(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent status updates for a session
        
        Args:
            session_id: Session identifier
            limit: Maximum number of updates to return
        
        Returns:
            List of recent status updates
        """
        try:
            status_key = f"session:{session_id}:status_updates"
            status_updates = self.memory_manager.memory.retrieve(status_key) or []
            
            # Return most recent updates
            return status_updates[-limit:] if status_updates else []
            
        except Exception as e:
            logger.error(f"Failed to get status updates for session {session_id}: {e}")
            return []
    
    def _trigger_progress_callbacks(self, operation_id: str, progress: float, 
                                  current_step: Optional[str]) -> None:
        """Trigger progress callbacks for an operation"""
        if operation_id in self.progress_callbacks:
            for callback in self.progress_callbacks[operation_id]:
                try:
                    callback(progress, current_step)
                except Exception as e:
                    logger.warning(f"Progress callback failed for {operation_id}: {e}")
    
    def _trigger_completion_callbacks(self, operation_id: str, 
                                    result: Optional[TranslationResult]) -> None:
        """Trigger completion callbacks for an operation"""
        # This could be extended to support completion callbacks
        pass
    
    def _trigger_failure_callbacks(self, operation_id: str, error_message: str) -> None:
        """Trigger failure callbacks for an operation"""
        # This could be extended to support failure callbacks
        pass


class OperationQueue:
    """
    Manages queuing of operations with AgentCore Memory integration
    
    Provides operation queuing capabilities for managing concurrent operations
    and ensuring proper resource utilization.
    """
    
    def __init__(self, memory_manager: Optional[ConversationMemoryManager] = None,
                 max_concurrent_operations: int = 3):
        """
        Initialize operation queue
        
        Args:
            memory_manager: Optional memory manager for persistent storage
            max_concurrent_operations: Maximum number of concurrent operations
        """
        self.memory_manager = memory_manager or ConversationMemoryManager()
        self.max_concurrent_operations = max_concurrent_operations
        
        logger.info(f"OperationQueue initialized with max {max_concurrent_operations} concurrent operations")
    
    def queue_operation(self, session_id: str, operation_id: str, 
                       operation_type: str, parameters: Dict[str, Any]) -> bool:
        """
        Queue an operation for execution
        
        Args:
            session_id: Session identifier
            operation_id: Operation identifier
            operation_type: Type of operation
            parameters: Operation parameters
        
        Returns:
            bool: True if queued successfully, False if queue is full
        """
        try:
            queue_key = f"session:{session_id}:operation_queue"
            
            # Get current queue
            queue_data = self.memory_manager.memory.retrieve(queue_key) or []
            
            # Check if we can queue more operations
            active_count = len([op for op in queue_data if op.get('status') == 'queued'])
            
            if active_count >= self.max_concurrent_operations:
                logger.warning(f"Operation queue full for session {session_id}")
                return False
            
            # Add operation to queue
            queue_item = {
                'operation_id': operation_id,
                'operation_type': operation_type,
                'parameters': parameters,
                'status': 'queued',
                'queued_at': datetime.now().isoformat()
            }
            
            queue_data.append(queue_item)
            
            # Store updated queue
            self.memory_manager.memory.store(queue_key, queue_data)
            
            logger.info(f"Queued operation {operation_id} for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to queue operation: {e}")
            return False
    
    def get_queue_status(self, session_id: str) -> Dict[str, Any]:
        """
        Get queue status for a session
        
        Args:
            session_id: Session identifier
        
        Returns:
            Dict containing queue status information
        """
        try:
            queue_key = f"session:{session_id}:operation_queue"
            queue_data = self.memory_manager.memory.retrieve(queue_key) or []
            
            queued_count = len([op for op in queue_data if op.get('status') == 'queued'])
            processing_count = len([op for op in queue_data if op.get('status') == 'processing'])
            
            return {
                'queued_operations': queued_count,
                'processing_operations': processing_count,
                'total_operations': len(queue_data),
                'max_concurrent': self.max_concurrent_operations,
                'queue_full': queued_count >= self.max_concurrent_operations
            }
            
        except Exception as e:
            logger.error(f"Failed to get queue status: {e}")
            return {
                'queued_operations': 0,
                'processing_operations': 0,
                'total_operations': 0,
                'max_concurrent': self.max_concurrent_operations,
                'queue_full': False
            }