"""
Comprehensive logging and monitoring for the GenASL Sign Language Agent

This module provides:
- Structured logging throughout the agent and tools
- Performance metrics collection
- Alerting for critical error conditions
- CloudWatch integration for operational monitoring
"""

import json
import logging
import time
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import boto3
from botocore.exceptions import ClientError
import uuid
import os

# Configure structured logging
class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'session_id'):
            log_entry['session_id'] = record.session_id
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'operation'):
            log_entry['operation'] = record.operation
        if hasattr(record, 'duration'):
            log_entry['duration_ms'] = record.duration
        if hasattr(record, 'error_type'):
            log_entry['error_type'] = record.error_type
        if hasattr(record, 'metadata'):
            log_entry['metadata'] = record.metadata
        
        return json.dumps(log_entry)


class MetricType(Enum):
    """Types of metrics to collect"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Metric:
    """Metric data structure"""
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime = field(default_factory=datetime.utcnow)
    dimensions: Dict[str, str] = field(default_factory=dict)
    unit: str = "Count"


@dataclass
class Alert:
    """Alert data structure"""
    name: str
    level: AlertLevel
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class PerformanceTracker:
    """Track performance metrics for operations"""
    
    def __init__(self):
        self.active_operations: Dict[str, float] = {}
        self.operation_stats: Dict[str, List[float]] = {}
        self.lock = threading.Lock()
    
    def start_operation(self, operation_id: str, operation_name: str) -> str:
        """Start tracking an operation"""
        with self.lock:
            self.active_operations[operation_id] = time.time()
            if operation_name not in self.operation_stats:
                self.operation_stats[operation_name] = []
        return operation_id
    
    def end_operation(self, operation_id: str, operation_name: str) -> float:
        """End tracking an operation and return duration"""
        with self.lock:
            if operation_id in self.active_operations:
                start_time = self.active_operations.pop(operation_id)
                duration = (time.time() - start_time) * 1000  # Convert to milliseconds
                self.operation_stats[operation_name].append(duration)
                
                # Keep only last 1000 measurements
                if len(self.operation_stats[operation_name]) > 1000:
                    self.operation_stats[operation_name] = self.operation_stats[operation_name][-1000:]
                
                return duration
        return 0.0
    
    def get_operation_stats(self, operation_name: str) -> Dict[str, float]:
        """Get statistics for an operation"""
        with self.lock:
            if operation_name not in self.operation_stats or not self.operation_stats[operation_name]:
                return {}
            
            durations = self.operation_stats[operation_name]
            return {
                'count': len(durations),
                'avg_ms': sum(durations) / len(durations),
                'min_ms': min(durations),
                'max_ms': max(durations),
                'p95_ms': sorted(durations)[int(len(durations) * 0.95)] if len(durations) > 20 else max(durations),
                'p99_ms': sorted(durations)[int(len(durations) * 0.99)] if len(durations) > 100 else max(durations)
            }


class MetricsCollector:
    """Collect and publish metrics to CloudWatch"""
    
    def __init__(self, namespace: str = "GenASL/Agent"):
        self.namespace = namespace
        self.metrics_buffer: List[Metric] = []
        self.buffer_lock = threading.Lock()
        self.cloudwatch = None
        self.performance_tracker = PerformanceTracker()
        
        # Initialize CloudWatch client
        try:
            self.cloudwatch = boto3.client('cloudwatch')
        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to initialize CloudWatch client: {e}")
    
    def record_metric(self, name: str, value: float, metric_type: MetricType = MetricType.COUNTER,
                     dimensions: Dict[str, str] = None, unit: str = "Count"):
        """Record a metric"""
        metric = Metric(
            name=name,
            value=value,
            metric_type=metric_type,
            dimensions=dimensions or {},
            unit=unit
        )
        
        with self.buffer_lock:
            self.metrics_buffer.append(metric)
            
            # Auto-flush if buffer is getting large
            if len(self.metrics_buffer) >= 20:
                self._flush_metrics()
    
    def increment_counter(self, name: str, value: float = 1.0, dimensions: Dict[str, str] = None):
        """Increment a counter metric"""
        self.record_metric(name, value, MetricType.COUNTER, dimensions)
    
    def record_gauge(self, name: str, value: float, dimensions: Dict[str, str] = None, unit: str = "Count"):
        """Record a gauge metric"""
        self.record_metric(name, value, MetricType.GAUGE, dimensions, unit)
    
    def record_timer(self, name: str, duration_ms: float, dimensions: Dict[str, str] = None):
        """Record a timer metric"""
        self.record_metric(name, duration_ms, MetricType.TIMER, dimensions, "Milliseconds")
    
    def start_timer(self, operation_name: str, session_id: str = None) -> str:
        """Start a timer for an operation"""
        operation_id = f"{operation_name}_{uuid.uuid4().hex[:8]}"
        self.performance_tracker.start_operation(operation_id, operation_name)
        return operation_id
    
    def end_timer(self, operation_id: str, operation_name: str, session_id: str = None):
        """End a timer and record the metric"""
        duration = self.performance_tracker.end_operation(operation_id, operation_name)
        if duration > 0:
            dimensions = {"operation": operation_name}
            if session_id:
                dimensions["session_id"] = session_id
            self.record_timer(f"{operation_name}_duration", duration, dimensions)
    
    def _flush_metrics(self):
        """Flush metrics to CloudWatch"""
        if not self.cloudwatch or not self.metrics_buffer:
            return
        
        try:
            # Prepare metric data for CloudWatch
            metric_data = []
            
            for metric in self.metrics_buffer:
                metric_datum = {
                    'MetricName': metric.name,
                    'Value': metric.value,
                    'Unit': metric.unit,
                    'Timestamp': metric.timestamp
                }
                
                if metric.dimensions:
                    metric_datum['Dimensions'] = [
                        {'Name': k, 'Value': v} for k, v in metric.dimensions.items()
                    ]
                
                metric_data.append(metric_datum)
            
            # Send to CloudWatch in batches of 20 (AWS limit)
            for i in range(0, len(metric_data), 20):
                batch = metric_data[i:i+20]
                self.cloudwatch.put_metric_data(
                    Namespace=self.namespace,
                    MetricData=batch
                )
            
            # Clear buffer
            self.metrics_buffer.clear()
            
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to flush metrics to CloudWatch: {e}")
    
    def flush(self):
        """Manually flush metrics"""
        with self.buffer_lock:
            self._flush_metrics()
    
    def get_performance_stats(self) -> Dict[str, Dict[str, float]]:
        """Get performance statistics for all operations"""
        stats = {}
        for operation_name in self.performance_tracker.operation_stats:
            stats[operation_name] = self.performance_tracker.get_operation_stats(operation_name)
        return stats


class AlertManager:
    """Manage alerts and notifications"""
    
    def __init__(self, sns_topic_arn: str = None):
        self.sns_topic_arn = sns_topic_arn
        self.alert_history: List[Alert] = []
        self.alert_thresholds = {
            'error_rate': 0.1,  # 10% error rate
            'response_time_p95': 30000,  # 30 seconds
            'consecutive_failures': 5
        }
        self.sns = None
        
        # Initialize SNS client if topic provided
        if sns_topic_arn:
            try:
                self.sns = boto3.client('sns')
            except Exception as e:
                logging.getLogger(__name__).warning(f"Failed to initialize SNS client: {e}")
    
    def create_alert(self, name: str, level: AlertLevel, message: str, metadata: Dict[str, Any] = None):
        """Create and process an alert"""
        alert = Alert(
            name=name,
            level=level,
            message=message,
            metadata=metadata or {}
        )
        
        self.alert_history.append(alert)
        
        # Keep only last 1000 alerts
        if len(self.alert_history) > 1000:
            self.alert_history = self.alert_history[-1000:]
        
        # Log the alert
        logger = logging.getLogger(__name__)
        log_level = {
            AlertLevel.INFO: logger.info,
            AlertLevel.WARNING: logger.warning,
            AlertLevel.ERROR: logger.error,
            AlertLevel.CRITICAL: logger.critical
        }[level]
        
        log_level(f"ALERT [{level.value.upper()}] {name}: {message}", extra={
            'alert_name': name,
            'alert_level': level.value,
            'metadata': metadata
        })
        
        # Send notification for critical alerts
        if level in [AlertLevel.ERROR, AlertLevel.CRITICAL] and self.sns:
            self._send_notification(alert)
    
    def _send_notification(self, alert: Alert):
        """Send alert notification via SNS"""
        try:
            message = {
                'alert_name': alert.name,
                'level': alert.level.value,
                'message': alert.message,
                'timestamp': alert.timestamp.isoformat(),
                'metadata': alert.metadata
            }
            
            self.sns.publish(
                TopicArn=self.sns_topic_arn,
                Message=json.dumps(message),
                Subject=f"GenASL Agent Alert: {alert.name}"
            )
            
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to send alert notification: {e}")
    
    def check_error_rate_threshold(self, error_count: int, total_count: int):
        """Check if error rate exceeds threshold"""
        if total_count > 0:
            error_rate = error_count / total_count
            if error_rate > self.alert_thresholds['error_rate']:
                self.create_alert(
                    "high_error_rate",
                    AlertLevel.ERROR,
                    f"Error rate {error_rate:.2%} exceeds threshold {self.alert_thresholds['error_rate']:.2%}",
                    {"error_count": error_count, "total_count": total_count, "error_rate": error_rate}
                )
    
    def check_response_time_threshold(self, p95_response_time: float):
        """Check if response time exceeds threshold"""
        if p95_response_time > self.alert_thresholds['response_time_p95']:
            self.create_alert(
                "high_response_time",
                AlertLevel.WARNING,
                f"P95 response time {p95_response_time:.0f}ms exceeds threshold {self.alert_thresholds['response_time_p95']:.0f}ms",
                {"p95_response_time": p95_response_time, "threshold": self.alert_thresholds['response_time_p95']}
            )


class MonitoringManager:
    """Central monitoring manager"""
    
    def __init__(self, namespace: str = "GenASL/Agent", sns_topic_arn: str = None):
        self.metrics_collector = MetricsCollector(namespace)
        self.alert_manager = AlertManager(sns_topic_arn)
        self.logger = self._setup_structured_logging()
        
        # Operation counters
        self.operation_counts = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'text_to_asl_requests': 0,
            'audio_to_asl_requests': 0,
            'asl_to_text_requests': 0
        }
        self.lock = threading.Lock()
    
    def _setup_structured_logging(self) -> logging.Logger:
        """Set up structured logging"""
        logger = logging.getLogger('genasl_monitoring')
        
        # Remove existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Add structured handler
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        return logger
    
    def log_request_start(self, session_id: str, user_id: str, request_type: str, message: str) -> str:
        """Log the start of a request"""
        operation_id = self.metrics_collector.start_timer("request_processing", session_id)
        
        with self.lock:
            self.operation_counts['total_requests'] += 1
            if request_type == 'text':
                self.operation_counts['text_to_asl_requests'] += 1
            elif request_type == 'audio':
                self.operation_counts['audio_to_asl_requests'] += 1
            elif request_type == 'video':
                self.operation_counts['asl_to_text_requests'] += 1
        
        self.logger.info("Request started", extra={
            'session_id': session_id,
            'user_id': user_id,
            'operation': 'request_start',
            'metadata': {
                'request_type': request_type,
                'message_length': len(message),
                'operation_id': operation_id
            }
        })
        
        self.metrics_collector.increment_counter("requests_total", dimensions={
            "request_type": request_type
        })
        
        return operation_id
    
    def log_request_success(self, operation_id: str, session_id: str, response_length: int):
        """Log successful request completion"""
        self.metrics_collector.end_timer(operation_id, "request_processing", session_id)
        
        with self.lock:
            self.operation_counts['successful_requests'] += 1
        
        self.logger.info("Request completed successfully", extra={
            'session_id': session_id,
            'operation': 'request_success',
            'metadata': {
                'response_length': response_length,
                'operation_id': operation_id
            }
        })
        
        self.metrics_collector.increment_counter("requests_successful")
    
    def log_request_failure(self, operation_id: str, session_id: str, error: Exception, error_type: str):
        """Log failed request"""
        self.metrics_collector.end_timer(operation_id, "request_processing", session_id)
        
        with self.lock:
            self.operation_counts['failed_requests'] += 1
        
        self.logger.error("Request failed", extra={
            'session_id': session_id,
            'operation': 'request_failure',
            'error_type': error_type,
            'metadata': {
                'error_message': str(error),
                'operation_id': operation_id
            }
        })
        
        self.metrics_collector.increment_counter("requests_failed", dimensions={
            "error_type": error_type
        })
        
        # Check if we should create an alert
        self._check_failure_alerts()
    
    def log_tool_execution(self, tool_name: str, session_id: str, duration_ms: float, success: bool):
        """Log tool execution"""
        self.logger.info(f"Tool execution: {tool_name}", extra={
            'session_id': session_id,
            'operation': 'tool_execution',
            'duration': duration_ms,
            'metadata': {
                'tool_name': tool_name,
                'success': success
            }
        })
        
        self.metrics_collector.record_timer(f"tool_{tool_name}_duration", duration_ms, dimensions={
            "tool": tool_name,
            "success": str(success)
        })
        
        if success:
            self.metrics_collector.increment_counter(f"tool_{tool_name}_success")
        else:
            self.metrics_collector.increment_counter(f"tool_{tool_name}_failure")
    
    def _check_failure_alerts(self):
        """Check if failure rate warrants an alert"""
        with self.lock:
            total = self.operation_counts['total_requests']
            failed = self.operation_counts['failed_requests']
        
        if total > 10:  # Only check after we have some data
            self.alert_manager.check_error_rate_threshold(failed, total)
    
    def get_health_metrics(self) -> Dict[str, Any]:
        """Get current health metrics"""
        with self.lock:
            counts = self.operation_counts.copy()
        
        performance_stats = self.metrics_collector.get_performance_stats()
        
        # Calculate rates
        total_requests = counts['total_requests']
        success_rate = counts['successful_requests'] / total_requests if total_requests > 0 else 0
        error_rate = counts['failed_requests'] / total_requests if total_requests > 0 else 0
        
        return {
            'request_counts': counts,
            'success_rate': success_rate,
            'error_rate': error_rate,
            'performance_stats': performance_stats,
            'recent_alerts': len([a for a in self.alert_manager.alert_history 
                                if (datetime.utcnow() - a.timestamp).seconds < 3600])  # Last hour
        }
    
    def flush_metrics(self):
        """Flush all pending metrics"""
        self.metrics_collector.flush()


# Global monitoring instance
monitoring_manager = MonitoringManager(
    namespace=os.environ.get('CLOUDWATCH_NAMESPACE', 'GenASL/Agent'),
    sns_topic_arn=os.environ.get('ALERT_SNS_TOPIC_ARN')
)