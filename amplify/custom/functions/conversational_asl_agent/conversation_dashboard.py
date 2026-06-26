"""
Conversation Quality Dashboard

This module provides utilities for creating and managing CloudWatch dashboards
specifically for monitoring conversation quality and agent performance.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class ConversationDashboardManager:
    """
    Manager for conversation quality dashboards and alerting
    
    This class handles:
    - Dashboard creation and updates
    - Custom metric widgets
    - Alert configuration
    - Performance monitoring views
    """
    
    def __init__(self, region: str = "us-west-2", environment: str = "dev"):
        """
        Initialize dashboard manager
        
        Args:
            region: AWS region
            environment: Deployment environment
        """
        self.region = region
        self.environment = environment
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        self.dashboard_name = f"ConversationalASL-Dashboard-{environment}"
        self.namespace = "GenASL/Conversation"
        
        logger.info(f"ConversationDashboardManager initialized for {environment} in {region}")
    
    def create_conversation_quality_dashboard(self) -> bool:
        """
        Create comprehensive conversation quality dashboard
        
        Returns:
            bool: True if dashboard was created successfully
        """
        try:
            dashboard_body = self._build_dashboard_body()
            
            response = self.cloudwatch.put_dashboard(
                DashboardName=self.dashboard_name,
                DashboardBody=json.dumps(dashboard_body)
            )
            
            logger.info(f"Conversation quality dashboard created: {self.dashboard_name}")
            return True
            
        except ClientError as e:
            logger.error(f"Error creating conversation quality dashboard: {e}")
            return False
    
    def _build_dashboard_body(self) -> Dict[str, Any]:
        """
        Build the dashboard body configuration
        
        Returns:
            Dict containing dashboard configuration
        """
        return {
            "widgets": [
                # Row 1: Overview metrics
                self._create_metric_widget(
                    title="Conversation Success Rate",
                    metrics=[
                        ["GenASL/Conversation", "ConversationSuccess", {"stat": "Sum"}],
                        [".", "ConversationFailure", {"stat": "Sum"}]
                    ],
                    width=8,
                    height=6,
                    x=0,
                    y=0,
                    view="timeSeries"
                ),
                self._create_metric_widget(
                    title="Active Sessions",
                    metrics=[
                        ["GenASL/Conversation", "SessionsActive", {"stat": "Average"}],
                        [".", "SessionsCreated", {"stat": "Sum"}]
                    ],
                    width=8,
                    height=6,
                    x=8,
                    y=0,
                    view="timeSeries"
                ),
                self._create_metric_widget(
                    title="Intent Classification Accuracy",
                    metrics=[
                        ["GenASL/Conversation", "IntentClassificationAccuracy", {"stat": "Average"}]
                    ],
                    width=8,
                    height=6,
                    x=16,
                    y=0,
                    view="timeSeries"
                ),
                
                # Row 2: Performance metrics
                self._create_metric_widget(
                    title="Response Time Distribution",
                    metrics=[
                        ["GenASL/Conversation", "ResponseTime", {"stat": "Average"}],
                        ["...", {"stat": "p95"}],
                        ["...", {"stat": "p99"}]
                    ],
                    width=12,
                    height=6,
                    x=0,
                    y=6,
                    view="timeSeries"
                ),
                self._create_metric_widget(
                    title="Memory Usage",
                    metrics=[
                        ["GenASL/Conversation", "MemoryUsage", {"stat": "Average"}],
                        ["...", {"stat": "Maximum"}]
                    ],
                    width=12,
                    height=6,
                    x=12,
                    y=6,
                    view="timeSeries"
                ),
                
                # Row 3: Session lifecycle
                self._create_metric_widget(
                    title="Session Duration",
                    metrics=[
                        ["GenASL/Conversation", "SessionDuration", {"stat": "Average"}],
                        ["...", {"stat": "p95"}]
                    ],
                    width=8,
                    height=6,
                    x=0,
                    y=12,
                    view="timeSeries"
                ),
                self._create_metric_widget(
                    title="Context Retrieval Performance",
                    metrics=[
                        ["GenASL/Conversation", "ContextRetrievalTime", {"stat": "Average"}],
                        [".", "ContextSize", {"stat": "Average"}]
                    ],
                    width=8,
                    height=6,
                    x=8,
                    y=12,
                    view="timeSeries"
                ),
                self._create_metric_widget(
                    title="Translation Success Rate",
                    metrics=[
                        ["GenASL/Conversation", "TranslationSuccessRate", {"stat": "Average"}]
                    ],
                    width=8,
                    height=6,
                    x=16,
                    y=12,
                    view="timeSeries"
                ),
                
                # Row 4: Error tracking
                self._create_metric_widget(
                    title="Error Recovery Success",
                    metrics=[
                        ["GenASL/Conversation", "ErrorRecoverySuccess", {"stat": "Sum"}]
                    ],
                    width=12,
                    height=6,
                    x=0,
                    y=18,
                    view="timeSeries"
                ),
                
                # Row 5: Lambda function metrics
                self._create_metric_widget(
                    title="Lambda Function Performance",
                    metrics=[
                        ["AWS/Lambda", "Duration", "FunctionName", f"SignLanguageAgentFunction-{self.environment}"],
                        [".", "Errors", ".", "."],
                        [".", "Invocations", ".", "."]
                    ],
                    width=12,
                    height=6,
                    x=12,
                    y=18,
                    view="timeSeries"
                ),
                
                # Row 6: Text widgets for insights
                self._create_text_widget(
                    title="Conversation Quality Insights",
                    markdown=self._generate_insights_markdown(),
                    width=24,
                    height=4,
                    x=0,
                    y=24
                )
            ]
        }
    
    def _create_metric_widget(self, title: str, metrics: List[List], width: int, height: int,
                            x: int, y: int, view: str = "timeSeries") -> Dict[str, Any]:
        """
        Create a metric widget configuration
        
        Args:
            title: Widget title
            metrics: List of metric configurations
            width: Widget width
            height: Widget height
            x: X position
            y: Y position
            view: View type (timeSeries, singleValue, etc.)
        
        Returns:
            Dict containing widget configuration
        """
        return {
            "type": "metric",
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "properties": {
                "metrics": metrics,
                "view": view,
                "stacked": False,
                "region": self.region,
                "title": title,
                "period": 300,
                "stat": "Average"
            }
        }
    
    def _create_text_widget(self, title: str, markdown: str, width: int, height: int,
                          x: int, y: int) -> Dict[str, Any]:
        """
        Create a text widget configuration
        
        Args:
            title: Widget title
            markdown: Markdown content
            width: Widget width
            height: Widget height
            x: X position
            y: Y position
        
        Returns:
            Dict containing widget configuration
        """
        return {
            "type": "text",
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "properties": {
                "markdown": f"# {title}\n\n{markdown}"
            }
        }
    
    def _generate_insights_markdown(self) -> str:
        """
        Generate markdown content for insights widget
        
        Returns:
            str: Markdown content
        """
        return """
## Key Performance Indicators

- **Success Rate Target**: > 85%
- **Response Time Target**: < 5 seconds (average)
- **Intent Accuracy Target**: > 80%
- **Memory Usage Target**: < 1GB (average)

## Monitoring Guidelines

1. **High Priority Alerts**:
   - Conversation success rate drops below 85%
   - Average response time exceeds 10 seconds
   - Intent classification accuracy below 75%

2. **Medium Priority Alerts**:
   - Memory usage consistently above 1.5GB
   - Session duration exceeds 30 minutes
   - Error recovery success rate below 70%

3. **Performance Optimization**:
   - Monitor context retrieval times for memory optimization opportunities
   - Track session patterns for cleanup policy tuning
   - Analyze translation success rates by input type

## Dashboard Links

- [Lambda Function Logs](https://console.aws.amazon.com/cloudwatch/home?region=us-west-2#logsV2:log-groups)
- [X-Ray Traces](https://console.aws.amazon.com/xray/home?region=us-west-2#/traces)
- [Agent Configuration](https://console.aws.amazon.com/bedrock/home?region=us-west-2#/agents)
        """
    
    def create_conversation_alarms(self) -> List[str]:
        """
        Create CloudWatch alarms for conversation monitoring
        
        Returns:
            List of created alarm names
        """
        alarms_created = []
        
        alarm_configs = [
            {
                "name": f"ConversationSuccessRate-{self.environment}",
                "description": "Alert when conversation success rate is too low",
                "metric_name": "ConversationSuccess",
                "statistic": "Sum",
                "threshold": 85,
                "comparison_operator": "LessThanThreshold",
                "evaluation_periods": 3,
                "period": 300
            },
            {
                "name": f"ConversationResponseTime-{self.environment}",
                "description": "Alert when response time is too high",
                "metric_name": "ResponseTime",
                "statistic": "Average",
                "threshold": 10,
                "comparison_operator": "GreaterThanThreshold",
                "evaluation_periods": 2,
                "period": 300
            },
            {
                "name": f"IntentClassificationAccuracy-{self.environment}",
                "description": "Alert when intent classification accuracy is too low",
                "metric_name": "IntentClassificationAccuracy",
                "statistic": "Average",
                "threshold": 75,
                "comparison_operator": "LessThanThreshold",
                "evaluation_periods": 3,
                "period": 300
            },
            {
                "name": f"ConversationMemoryUsage-{self.environment}",
                "description": "Alert when memory usage is too high",
                "metric_name": "MemoryUsage",
                "statistic": "Average",
                "threshold": 1500,  # 1.5GB in MB
                "comparison_operator": "GreaterThanThreshold",
                "evaluation_periods": 2,
                "period": 300
            }
        ]
        
        for alarm_config in alarm_configs:
            try:
                self.cloudwatch.put_metric_alarm(
                    AlarmName=alarm_config["name"],
                    ComparisonOperator=alarm_config["comparison_operator"],
                    EvaluationPeriods=alarm_config["evaluation_periods"],
                    MetricName=alarm_config["metric_name"],
                    Namespace=self.namespace,
                    Period=alarm_config["period"],
                    Statistic=alarm_config["statistic"],
                    Threshold=alarm_config["threshold"],
                    ActionsEnabled=True,
                    AlarmDescription=alarm_config["description"],
                    Unit="None"
                )
                
                alarms_created.append(alarm_config["name"])
                logger.info(f"Created alarm: {alarm_config['name']}")
                
            except ClientError as e:
                logger.error(f"Error creating alarm {alarm_config['name']}: {e}")
        
        return alarms_created
    
    def get_dashboard_url(self) -> str:
        """
        Get the URL for the conversation quality dashboard
        
        Returns:
            str: Dashboard URL
        """
        return (f"https://console.aws.amazon.com/cloudwatch/home?"
               f"region={self.region}#dashboards:name={self.dashboard_name}")
    
    def update_dashboard_insights(self, custom_insights: str) -> bool:
        """
        Update the insights section of the dashboard
        
        Args:
            custom_insights: Custom insights markdown content
        
        Returns:
            bool: True if update was successful
        """
        try:
            # Get current dashboard
            response = self.cloudwatch.get_dashboard(DashboardName=self.dashboard_name)
            dashboard_body = json.loads(response["DashboardBody"])
            
            # Find and update the insights widget
            for widget in dashboard_body["widgets"]:
                if (widget.get("type") == "text" and 
                    "Conversation Quality Insights" in widget.get("properties", {}).get("markdown", "")):
                    widget["properties"]["markdown"] = f"# Conversation Quality Insights\n\n{custom_insights}"
                    break
            
            # Update dashboard
            self.cloudwatch.put_dashboard(
                DashboardName=self.dashboard_name,
                DashboardBody=json.dumps(dashboard_body)
            )
            
            logger.info("Dashboard insights updated successfully")
            return True
            
        except ClientError as e:
            logger.error(f"Error updating dashboard insights: {e}")
            return False
    
    def generate_monitoring_report(self, hours: int = 24) -> Dict[str, Any]:
        """
        Generate a monitoring report for the specified time period
        
        Args:
            hours: Number of hours to analyze
        
        Returns:
            Dict containing monitoring report
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        report = {
            "report_period": {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_hours": hours
            },
            "dashboard_url": self.get_dashboard_url(),
            "metrics": {},
            "recommendations": []
        }
        
        # Get key metrics
        metrics_to_fetch = [
            ("ConversationSuccess", "Sum"),
            ("ConversationFailure", "Sum"),
            ("IntentClassificationAccuracy", "Average"),
            ("ResponseTime", "Average"),
            ("MemoryUsage", "Average"),
            ("SessionDuration", "Average")
        ]
        
        for metric_name, statistic in metrics_to_fetch:
            try:
                response = self.cloudwatch.get_metric_statistics(
                    Namespace=self.namespace,
                    MetricName=metric_name,
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=3600,
                    Statistics=[statistic]
                )
                
                if response["Datapoints"]:
                    values = [dp[statistic] for dp in response["Datapoints"]]
                    report["metrics"][metric_name] = {
                        "value": sum(values) / len(values),
                        "statistic": statistic,
                        "datapoints_count": len(values)
                    }
                
            except ClientError as e:
                logger.error(f"Error fetching metric {metric_name}: {e}")
        
        # Generate recommendations based on metrics
        report["recommendations"] = self._generate_recommendations(report["metrics"])
        
        return report
    
    def _generate_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """
        Generate recommendations based on metrics
        
        Args:
            metrics: Dictionary of metric values
        
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        # Check success rate
        success = metrics.get("ConversationSuccess", {}).get("value", 0)
        failure = metrics.get("ConversationFailure", {}).get("value", 0)
        if success + failure > 0:
            success_rate = success / (success + failure) * 100
            if success_rate < 85:
                recommendations.append(
                    f"Conversation success rate ({success_rate:.1f}%) is below target (85%). "
                    "Review error logs and consider improving error handling."
                )
        
        # Check response time
        response_time = metrics.get("ResponseTime", {}).get("value", 0)
        if response_time > 5:
            recommendations.append(
                f"Average response time ({response_time:.1f}s) exceeds target (5s). "
                "Consider optimizing context retrieval or translation pipeline."
            )
        
        # Check intent accuracy
        intent_accuracy = metrics.get("IntentClassificationAccuracy", {}).get("value", 0)
        if intent_accuracy < 80:
            recommendations.append(
                f"Intent classification accuracy ({intent_accuracy:.1f}%) is below target (80%). "
                "Review intent classification patterns and training data."
            )
        
        # Check memory usage
        memory_usage = metrics.get("MemoryUsage", {}).get("value", 0)
        if memory_usage > 1000:  # 1GB
            recommendations.append(
                f"Average memory usage ({memory_usage:.0f}MB) is high. "
                "Consider optimizing context storage or implementing more aggressive cleanup."
            )
        
        if not recommendations:
            recommendations.append("All metrics are within acceptable ranges. Continue monitoring.")
        
        return recommendations

def create_conversation_dashboard(environment: str = "dev", region: str = "us-west-2") -> bool:
    """
    Convenience function to create conversation quality dashboard
    
    Args:
        environment: Deployment environment
        region: AWS region
    
    Returns:
        bool: True if dashboard was created successfully
    """
    dashboard_manager = ConversationDashboardManager(region, environment)
    return dashboard_manager.create_conversation_quality_dashboard()

def setup_conversation_monitoring(environment: str = "dev", region: str = "us-west-2") -> Dict[str, Any]:
    """
    Set up complete conversation monitoring (dashboard + alarms)
    
    Args:
        environment: Deployment environment
        region: AWS region
    
    Returns:
        Dict containing setup results
    """
    dashboard_manager = ConversationDashboardManager(region, environment)
    
    results = {
        "dashboard_created": False,
        "alarms_created": [],
        "dashboard_url": dashboard_manager.get_dashboard_url(),
        "errors": []
    }
    
    try:
        # Create dashboard
        results["dashboard_created"] = dashboard_manager.create_conversation_quality_dashboard()
        
        # Create alarms
        results["alarms_created"] = dashboard_manager.create_conversation_alarms()
        
        logger.info(f"Conversation monitoring setup completed for {environment}")
        
    except Exception as e:
        results["errors"].append(str(e))
        logger.error(f"Error setting up conversation monitoring: {e}")
    
    return results

if __name__ == "__main__":
    # Test dashboard creation
    import sys
    
    environment = sys.argv[1] if len(sys.argv) > 1 else "dev"
    results = setup_conversation_monitoring(environment)
    
    print(f"Dashboard setup results: {json.dumps(results, indent=2)}")