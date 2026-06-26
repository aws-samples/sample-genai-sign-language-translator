"""
Workflow orchestration module for the GenASL Sign Language Agent

This module provides workflow management capabilities including sequential
and parallel processing, decision logic, and workflow state management.
"""

import logging
import time
import asyncio
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import concurrent.futures
from threading import Thread, Event

logger = logging.getLogger(__name__)

class WorkflowStatus(Enum):
    """Enumeration of workflow statuses"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class StepStatus(Enum):
    """Enumeration of step statuses"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class WorkflowStep:
    """Represents a single step in a workflow"""
    name: str
    function: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3

@dataclass
class WorkflowExecution:
    """Represents a workflow execution instance"""
    workflow_id: str
    name: str
    steps: Dict[str, WorkflowStep] = field(default_factory=dict)
    status: WorkflowStatus = WorkflowStatus.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    results: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    progress: float = 0.0

class WorkflowOrchestrator:
    """Orchestrates workflow execution with support for sequential and parallel processing"""
    
    def __init__(self):
        self.active_workflows: Dict[str, WorkflowExecution] = {}
        self.workflow_templates: Dict[str, Dict[str, Any]] = {}
        self._setup_default_workflows()
        logger.info("WorkflowOrchestrator initialized")
    
    def _setup_default_workflows(self):
        """Set up default workflow templates for common ASL translation patterns"""
        
        # Text-to-ASL workflow
        self.workflow_templates["text_to_asl"] = {
            "name": "Text to ASL Translation",
            "steps": [
                {
                    "name": "text_to_gloss",
                    "function": "text_to_asl_gloss",
                    "dependencies": []
                },
                {
                    "name": "gloss_to_video",
                    "function": "gloss_to_video",
                    "dependencies": ["text_to_gloss"]
                }
            ]
        }
        
        # Audio-to-ASL workflow
        self.workflow_templates["audio_to_asl"] = {
            "name": "Audio to ASL Translation",
            "steps": [
                {
                    "name": "process_audio",
                    "function": "process_audio_input",
                    "dependencies": []
                },
                {
                    "name": "text_to_gloss",
                    "function": "text_to_asl_gloss",
                    "dependencies": ["process_audio"]
                },
                {
                    "name": "gloss_to_video",
                    "function": "gloss_to_video",
                    "dependencies": ["text_to_gloss"]
                }
            ]
        }
        
        # ASL-to-Text workflow
        self.workflow_templates["asl_to_text"] = {
            "name": "ASL to Text Analysis",
            "steps": [
                {
                    "name": "analyze_asl",
                    "function": "analyze_asl_video_stream",  # or analyze_asl_from_s3
                    "dependencies": []
                }
            ]
        }
        
        logger.info(f"Set up {len(self.workflow_templates)} default workflow templates")
    
    def create_workflow(self, template_name: str, workflow_id: str, 
                       parameters: Dict[str, Any]) -> WorkflowExecution:
        """Create a new workflow execution from a template"""
        
        if template_name not in self.workflow_templates:
            raise ValueError(f"Unknown workflow template: {template_name}")
        
        template = self.workflow_templates[template_name]
        workflow = WorkflowExecution(
            workflow_id=workflow_id,
            name=template["name"]
        )
        
        # Create workflow steps from template
        for step_config in template["steps"]:
            step = WorkflowStep(
                name=step_config["name"],
                function=self._resolve_function(step_config["function"]),
                dependencies=step_config["dependencies"],
                max_retries=step_config.get("max_retries", 3)
            )
            
            # Set step parameters based on workflow parameters
            step.args, step.kwargs = self._resolve_step_parameters(
                step_config["name"], parameters
            )
            
            workflow.steps[step.name] = step
        
        self.active_workflows[workflow_id] = workflow
        logger.info(f"Created workflow '{template_name}' with ID: {workflow_id}")
        
        return workflow
    
    def _resolve_function(self, function_name: str) -> Callable:
        """Resolve function name to actual function reference"""
        # Import functions dynamically to avoid circular imports
        function_map = {}
        
        try:
            # Import text2gloss function
            import sys
            from pathlib import Path
            current_dir = Path(__file__).parent
            functions_dir = current_dir.parent
            
            # Add text2gloss module path
            text2gloss_path = functions_dir / 'text2gloss'
            if text2gloss_path.exists() and str(text2gloss_path) not in sys.path:
                sys.path.insert(0, str(text2gloss_path))
            
            from text2gloss_handler import text_to_asl_gloss
            function_map["text_to_asl_gloss"] = text_to_asl_gloss
        except ImportError:
            logger.warning("Could not import text_to_asl_gloss function")
        
        try:
            # Add gloss2pose module path
            gloss2pose_path = functions_dir / 'gloss2pose'
            if gloss2pose_path.exists() and str(gloss2pose_path) not in sys.path:
                sys.path.insert(0, str(gloss2pose_path))
            
            from gloss2pose_handler import gloss_to_video
            function_map["gloss_to_video"] = gloss_to_video
        except ImportError:
            logger.warning("Could not import gloss_to_video function")
        
        try:
            # Add audio processing module path
            audio_path = functions_dir / 'audio_processing'
            if audio_path.exists() and str(audio_path) not in sys.path:
                sys.path.insert(0, str(audio_path))
            
            from audio_processing_handler import process_audio_input
            function_map["process_audio_input"] = process_audio_input
        except ImportError:
            logger.warning("Could not import process_audio_input function")
        
        try:
            # Add ASL analysis module path
            asl_path = functions_dir / 'asl_analysis'
            if asl_path.exists() and str(asl_path) not in sys.path:
                sys.path.insert(0, str(asl_path))
            
            from asl_analysis_handler import analyze_asl_video_stream, analyze_asl_from_s3
            function_map["analyze_asl_video_stream"] = analyze_asl_video_stream
            function_map["analyze_asl_from_s3"] = analyze_asl_from_s3
        except ImportError:
            logger.warning("Could not import ASL analysis functions")
        
        if function_name not in function_map:
            raise ValueError(f"Unknown function: {function_name}")
        
        return function_map[function_name]
    
    def _resolve_step_parameters(self, step_name: str, 
                               parameters: Dict[str, Any]) -> tuple:
        """Resolve step parameters based on step name and workflow parameters"""
        args = ()
        kwargs = {}
        
        if step_name == "text_to_gloss":
            # Text to gloss conversion
            text = parameters.get("text", parameters.get("message", ""))
            args = (text,)
        
        elif step_name == "gloss_to_video":
            # Gloss to video conversion - will get gloss from previous step
            kwargs = {
                "text": parameters.get("text", parameters.get("message", "")),
                "pose_only": parameters.get("pose_only", False),
                "pre_sign": parameters.get("pre_sign", True)
            }
        
        elif step_name == "process_audio":
            # Audio processing
            bucket_name = parameters.get("bucket_name", parameters.get("BucketName", ""))
            key_name = parameters.get("key_name", parameters.get("KeyName", ""))
            args = (bucket_name, key_name)
        
        elif step_name == "analyze_asl":
            # ASL analysis
            stream_name = parameters.get("stream_name", parameters.get("StreamName", ""))
            bucket_name = parameters.get("bucket_name", parameters.get("BucketName", ""))
            key_name = parameters.get("key_name", parameters.get("KeyName", ""))
            
            if stream_name:
                args = (stream_name,)
            elif bucket_name and key_name:
                args = (bucket_name, key_name)
        
        return args, kwargs
    
    def execute_workflow(self, workflow_id: str, 
                        progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Execute a workflow with support for sequential and parallel processing"""
        
        if workflow_id not in self.active_workflows:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        workflow = self.active_workflows[workflow_id]
        workflow.status = WorkflowStatus.RUNNING
        workflow.start_time = time.time()
        
        logger.info(f"Starting workflow execution: {workflow.name} ({workflow_id})")
        
        try:
            # Execute steps in dependency order
            executed_steps = set()
            
            while len(executed_steps) < len(workflow.steps):
                # Find steps that can be executed (dependencies satisfied)
                ready_steps = []
                
                for step_name, step in workflow.steps.items():
                    if (step_name not in executed_steps and 
                        step.status == StepStatus.PENDING and
                        all(dep in executed_steps for dep in step.dependencies)):
                        ready_steps.append(step)
                
                if not ready_steps:
                    # Check if we have failed steps blocking progress
                    failed_steps = [s for s in workflow.steps.values() if s.status == StepStatus.FAILED]
                    if failed_steps:
                        raise RuntimeError(f"Workflow blocked by failed steps: {[s.name for s in failed_steps]}")
                    else:
                        raise RuntimeError("Workflow deadlock: no steps can be executed")
                
                # Execute ready steps (can be parallel if multiple)
                if len(ready_steps) == 1:
                    # Sequential execution
                    step = ready_steps[0]
                    self._execute_step(step, workflow)
                    executed_steps.add(step.name)
                else:
                    # Parallel execution
                    self._execute_steps_parallel(ready_steps, workflow)
                    executed_steps.update(step.name for step in ready_steps)
                
                # Update progress
                workflow.progress = len(executed_steps) / len(workflow.steps)
                if progress_callback:
                    progress_callback(workflow.progress, workflow_id)
            
            # Check final status
            failed_steps = [s for s in workflow.steps.values() if s.status == StepStatus.FAILED]
            if failed_steps:
                workflow.status = WorkflowStatus.FAILED
                workflow.errors.extend([f"Step '{s.name}' failed: {s.error}" for s in failed_steps])
            else:
                workflow.status = WorkflowStatus.COMPLETED
                # Collect results
                workflow.results = {step.name: step.result for step in workflow.steps.values()}
            
            workflow.end_time = time.time()
            execution_time = workflow.end_time - workflow.start_time
            
            logger.info(f"Workflow completed: {workflow.name} in {execution_time:.2f}s")
            
            return {
                "workflow_id": workflow_id,
                "status": workflow.status.value,
                "results": workflow.results,
                "errors": workflow.errors,
                "execution_time": execution_time,
                "progress": workflow.progress
            }
            
        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            workflow.end_time = time.time()
            error_msg = f"Workflow execution failed: {str(e)}"
            workflow.errors.append(error_msg)
            logger.error(error_msg)
            
            return {
                "workflow_id": workflow_id,
                "status": workflow.status.value,
                "results": workflow.results,
                "errors": workflow.errors,
                "execution_time": workflow.end_time - workflow.start_time if workflow.start_time else 0,
                "progress": workflow.progress
            }
    
    def _execute_step(self, step: WorkflowStep, workflow: WorkflowExecution):
        """Execute a single workflow step with error handling and retries"""
        
        step.status = StepStatus.RUNNING
        step.start_time = time.time()
        
        logger.info(f"Executing step: {step.name}")
        
        for attempt in range(step.max_retries + 1):
            try:
                # Resolve step arguments from previous step results if needed
                resolved_args, resolved_kwargs = self._resolve_runtime_parameters(
                    step, workflow
                )
                
                # Execute the step function
                result = step.function(*resolved_args, **resolved_kwargs)
                
                step.result = result
                step.status = StepStatus.COMPLETED
                step.end_time = time.time()
                
                logger.info(f"Step completed: {step.name} in {step.end_time - step.start_time:.2f}s")
                return
                
            except Exception as e:
                step.retry_count = attempt
                error_msg = f"Step '{step.name}' attempt {attempt + 1} failed: {str(e)}"
                logger.warning(error_msg)
                
                if attempt == step.max_retries:
                    step.status = StepStatus.FAILED
                    step.error = str(e)
                    step.end_time = time.time()
                    logger.error(f"Step failed after {step.max_retries + 1} attempts: {step.name}")
                    return
                
                # Wait before retry
                time.sleep(2 ** attempt)  # Exponential backoff
    
    def _execute_steps_parallel(self, steps: List[WorkflowStep], 
                               workflow: WorkflowExecution):
        """Execute multiple steps in parallel using threading"""
        
        logger.info(f"Executing {len(steps)} steps in parallel: {[s.name for s in steps]}")
        
        threads = []
        for step in steps:
            thread = Thread(target=self._execute_step, args=(step, workflow))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        logger.info(f"Parallel execution completed for steps: {[s.name for s in steps]}")
    
    def _resolve_runtime_parameters(self, step: WorkflowStep, 
                                   workflow: WorkflowExecution) -> tuple:
        """Resolve step parameters at runtime using results from previous steps"""
        
        args = list(step.args)
        kwargs = dict(step.kwargs)
        
        # Special handling for steps that depend on previous results
        if step.name == "gloss_to_video" and "text_to_gloss" in step.dependencies:
            # Get gloss from previous step
            text_to_gloss_step = workflow.steps.get("text_to_gloss")
            if text_to_gloss_step and text_to_gloss_step.result:
                # Insert gloss as first argument
                args.insert(0, text_to_gloss_step.result)
        
        elif step.name == "text_to_gloss" and "process_audio" in step.dependencies:
            # Get transcribed text from audio processing step
            audio_step = workflow.steps.get("process_audio")
            if audio_step and audio_step.result:
                args = [audio_step.result]
        
        return tuple(args), kwargs
    
    def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get current status of a workflow"""
        
        if workflow_id not in self.active_workflows:
            return {"error": f"Workflow not found: {workflow_id}"}
        
        workflow = self.active_workflows[workflow_id]
        
        step_statuses = {
            step.name: {
                "status": step.status.value,
                "progress": 1.0 if step.status == StepStatus.COMPLETED else 0.0,
                "error": step.error,
                "retry_count": step.retry_count
            }
            for step in workflow.steps.values()
        }
        
        return {
            "workflow_id": workflow_id,
            "name": workflow.name,
            "status": workflow.status.value,
            "progress": workflow.progress,
            "steps": step_statuses,
            "errors": workflow.errors,
            "start_time": workflow.start_time,
            "end_time": workflow.end_time
        }
    
    def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow"""
        
        if workflow_id not in self.active_workflows:
            return False
        
        workflow = self.active_workflows[workflow_id]
        
        if workflow.status == WorkflowStatus.RUNNING:
            workflow.status = WorkflowStatus.CANCELLED
            workflow.end_time = time.time()
            
            # Mark running steps as cancelled
            for step in workflow.steps.values():
                if step.status == StepStatus.RUNNING:
                    step.status = StepStatus.FAILED
                    step.error = "Workflow cancelled"
                    step.end_time = time.time()
            
            logger.info(f"Workflow cancelled: {workflow_id}")
            return True
        
        return False
    
    def cleanup_completed_workflows(self, max_age_hours: int = 24):
        """Clean up old completed workflows to manage memory"""
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        workflows_to_remove = []
        
        for workflow_id, workflow in self.active_workflows.items():
            if (workflow.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED] and
                workflow.end_time and 
                current_time - workflow.end_time > max_age_seconds):
                workflows_to_remove.append(workflow_id)
        
        for workflow_id in workflows_to_remove:
            del self.active_workflows[workflow_id]
        
        if workflows_to_remove:
            logger.info(f"Cleaned up {len(workflows_to_remove)} old workflows")

# Global workflow orchestrator instance
workflow_orchestrator = WorkflowOrchestrator()