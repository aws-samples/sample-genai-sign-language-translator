"""
Response formatting module for the GenASL Sign Language Agent

This module provides response formatters for different API endpoints to ensure
backward compatibility with existing client applications while adding enhanced
response metadata for debugging and monitoring.
"""

import json
import time
import re
import logging
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

class ResponseFormat(Enum):
    """Enumeration of response formats"""
    REST_API = "rest_api"
    WEBSOCKET = "websocket"
    LEGACY_STEP_FUNCTIONS = "legacy_step_functions"
    ENHANCED = "enhanced"

@dataclass
class FormattedResponse:
    """Structured response with metadata"""
    data: Dict[str, Any]
    format_type: ResponseFormat
    metadata: Dict[str, Any] = field(default_factory=dict)
    debug_info: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

class ResponseFormatter:
    """Formats agent responses for different API endpoints"""
    
    def __init__(self):
        self.url_pattern = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+')
        self.gloss_pattern = re.compile(r'(?:ASL Gloss|Gloss):\s*([^\n]+)', re.IGNORECASE)
        self.text_pattern = re.compile(r'(?:Original text|Text):\s*"([^"]+)"', re.IGNORECASE)
        logger.info("ResponseFormatter initialized")
    
    def format_for_rest_api(self, agent_response: Union[str, Dict], 
                           request_params: Dict[str, Any],
                           include_debug: bool = False) -> FormattedResponse:
        """
        Format agent response for REST API endpoints
        Maintains backward compatibility with Step Functions response format
        """
        try:
            # Parse agent response if it's a string
            if isinstance(agent_response, str):
                parsed_data = self._parse_agent_text_response(agent_response)
            else:
                parsed_data = dict(agent_response)
            
            # Build REST API compatible response
            rest_response = {}
            
            # Map standard fields for backward compatibility
            if 'Gloss' in parsed_data:
                rest_response['Gloss'] = parsed_data['Gloss']
            if 'Text' in parsed_data:
                rest_response['Text'] = parsed_data['Text']
            
            # Map video URLs
            for url_key in ['PoseURL', 'SignURL', 'AvatarURL']:
                if url_key in parsed_data:
                    rest_response[url_key] = parsed_data[url_key]
            
            # Add status and timing information
            rest_response['status'] = 'SUCCEEDED'
            rest_response['timestamp'] = int(time.time())
            
            # Include original request parameters for context
            if 'Gloss' in request_params:
                rest_response['Gloss'] = rest_response.get('Gloss', request_params['Gloss'])
            if 'Text' in request_params:
                rest_response['Text'] = rest_response.get('Text', request_params['Text'])
            
            # Add enhanced metadata
            metadata = {
                'request_type': self._determine_request_type(request_params),
                'processing_method': 'strands_agent',
                'response_format': 'rest_api_compatible'
            }
            
            # Add debug information if requested
            debug_info = {}
            if include_debug:
                debug_info = {
                    'raw_agent_response': str(agent_response)[:500],
                    'parsed_fields': list(parsed_data.keys()),
                    'request_params': request_params,
                    'processing_time': time.time()
                }
            
            return FormattedResponse(
                data=rest_response,
                format_type=ResponseFormat.REST_API,
                metadata=metadata,
                debug_info=debug_info
            )
            
        except Exception as e:
            logger.error(f"Error formatting REST API response: {e}")
            return self._create_error_response(str(e), ResponseFormat.REST_API)
    
    def format_for_websocket(self, agent_response: Union[str, Dict],
                           original_message: Dict[str, Any],
                           connection_id: str,
                           include_debug: bool = False) -> FormattedResponse:
        """
        Format agent response for WebSocket endpoints
        Provides user-friendly conversational responses
        """
        try:
            # For WebSocket, prioritize user-friendly text responses
            if isinstance(agent_response, str):
                formatted_message = self._format_websocket_text_response(agent_response)
            else:
                formatted_message = self._format_websocket_structured_response(agent_response)
            
            websocket_response = {
                'message': formatted_message,
                'type': 'agent_response',
                'timestamp': int(time.time()),
                'connection_id': connection_id
            }
            
            # Add any structured data for client processing
            if isinstance(agent_response, dict):
                if 'Gloss' in agent_response:
                    websocket_response['gloss'] = agent_response['Gloss']
                
                # Include video URLs for client handling
                video_urls = {}
                for url_key in ['PoseURL', 'SignURL', 'AvatarURL']:
                    if url_key in agent_response:
                        video_urls[url_key.lower().replace('url', '')] = agent_response[url_key]
                
                if video_urls:
                    websocket_response['videos'] = video_urls
            
            metadata = {
                'connection_id': connection_id,
                'message_type': self._determine_websocket_message_type(original_message),
                'processing_method': 'strands_agent',
                'response_format': 'websocket_friendly'
            }
            
            debug_info = {}
            if include_debug:
                debug_info = {
                    'raw_agent_response': str(agent_response)[:500],
                    'original_message': original_message,
                    'formatting_method': 'websocket_conversational'
                }
            
            return FormattedResponse(
                data=websocket_response,
                format_type=ResponseFormat.WEBSOCKET,
                metadata=metadata,
                debug_info=debug_info
            )
            
        except Exception as e:
            logger.error(f"Error formatting WebSocket response: {e}")
            return self._create_error_response(str(e), ResponseFormat.WEBSOCKET)
    
    def format_for_legacy_compatibility(self, agent_response: Union[str, Dict],
                                      execution_arn: Optional[str] = None) -> FormattedResponse:
        """
        Format agent response to mimic Step Functions output format
        For backward compatibility with existing clients
        """
        try:
            # Parse agent response
            if isinstance(agent_response, str):
                parsed_data = self._parse_agent_text_response(agent_response)
            else:
                parsed_data = dict(agent_response)
            
            # Create Step Functions-like response
            legacy_response = {
                'executionArn': execution_arn or f"arn:aws:states:us-east-1:123456789012:execution:GenASL-Agent:{int(time.time())}",
                'status': 'SUCCEEDED',
                'startDate': time.time(),
                'stopDate': time.time(),
                'output': json.dumps(parsed_data)
            }
            
            metadata = {
                'compatibility_mode': 'step_functions',
                'processing_method': 'strands_agent',
                'response_format': 'legacy_compatible'
            }
            
            return FormattedResponse(
                data=legacy_response,
                format_type=ResponseFormat.LEGACY_STEP_FUNCTIONS,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error formatting legacy response: {e}")
            return self._create_error_response(str(e), ResponseFormat.LEGACY_STEP_FUNCTIONS)
    
    def format_enhanced_response(self, agent_response: Union[str, Dict],
                               request_context: Dict[str, Any],
                               processing_metrics: Optional[Dict[str, Any]] = None) -> FormattedResponse:
        """
        Format enhanced response with full metadata and debugging information
        For monitoring, debugging, and advanced client applications
        """
        try:
            # Parse agent response
            if isinstance(agent_response, str):
                parsed_data = self._parse_agent_text_response(agent_response)
            else:
                parsed_data = dict(agent_response)
            
            # Build enhanced response
            enhanced_response = {
                'result': parsed_data,
                'status': 'success',
                'timestamp': time.time(),
                'request_id': request_context.get('request_id', f"req_{int(time.time())}"),
                'processing_info': {
                    'method': 'strands_agent',
                    'model': request_context.get('model', 'amazon.nova-lite-v1:0'),
                    'tools_used': self._extract_tools_used(agent_response),
                    'workflow_type': self._determine_workflow_type(request_context)
                }
            }
            
            # Add processing metrics if available
            if processing_metrics:
                enhanced_response['metrics'] = processing_metrics
            
            # Add comprehensive metadata
            metadata = {
                'format_version': '1.0',
                'response_type': 'enhanced',
                'capabilities': {
                    'text_to_asl': True,
                    'audio_to_asl': True,
                    'asl_to_text': True,
                    'conversational': True
                },
                'client_compatibility': {
                    'rest_api': True,
                    'websocket': True,
                    'legacy_step_functions': True
                }
            }
            
            # Add debug information
            debug_info = {
                'raw_agent_response': str(agent_response),
                'parsing_method': 'enhanced_parser',
                'request_context': request_context,
                'response_size': len(str(agent_response)),
                'processing_timestamp': time.time()
            }
            
            return FormattedResponse(
                data=enhanced_response,
                format_type=ResponseFormat.ENHANCED,
                metadata=metadata,
                debug_info=debug_info
            )
            
        except Exception as e:
            logger.error(f"Error formatting enhanced response: {e}")
            return self._create_error_response(str(e), ResponseFormat.ENHANCED)
    
    def _parse_agent_text_response(self, response_text: str) -> Dict[str, Any]:
        """Parse agent text response to extract structured data"""
        parsed_data = {}
        
        # Extract URLs
        urls = self.url_pattern.findall(response_text)
        if urls:
            for i, url in enumerate(urls):
                if 'pose' in url.lower():
                    parsed_data['PoseURL'] = url
                elif 'sign' in url.lower():
                    parsed_data['SignURL'] = url
                elif 'avatar' in url.lower():
                    parsed_data['AvatarURL'] = url
                elif i == 0 and 'PoseURL' not in parsed_data:
                    parsed_data['PoseURL'] = url
                elif i == 1 and 'SignURL' not in parsed_data:
                    parsed_data['SignURL'] = url
                elif i == 2 and 'AvatarURL' not in parsed_data:
                    parsed_data['AvatarURL'] = url
        
        # Extract gloss
        gloss_match = self.gloss_pattern.search(response_text)
        if gloss_match:
            parsed_data['Gloss'] = gloss_match.group(1).strip()
        
        # Extract text
        text_match = self.text_pattern.search(response_text)
        if text_match:
            parsed_data['Text'] = text_match.group(1).strip()
        
        # If no structured data found, include the full response
        if not parsed_data:
            parsed_data['message'] = response_text
        
        return parsed_data
    
    def _format_websocket_text_response(self, response_text: str) -> str:
        """Format text response for WebSocket with user-friendly formatting"""
        # Clean up the response for better readability
        lines = response_text.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if line:
                # Add emoji for better visual appeal
                if 'completed successfully' in line.lower():
                    line = f"✅ {line}"
                elif 'error' in line.lower() or 'failed' in line.lower():
                    line = f"❌ {line}"
                elif line.startswith('ASL Gloss:'):
                    line = f"🤟 {line}"
                elif 'video' in line.lower() and 'url' in line.lower():
                    line = f"🎥 {line}"
                
                formatted_lines.append(line)
        
        return '\n'.join(formatted_lines)
    
    def _format_websocket_structured_response(self, response_data: Dict[str, Any]) -> str:
        """Format structured response data for WebSocket display"""
        formatted_parts = []
        
        if 'message' in response_data:
            formatted_parts.append(response_data['message'])
        
        if 'Text' in response_data:
            formatted_parts.append(f"📝 Original: \"{response_data['Text']}\"")
        
        if 'Gloss' in response_data:
            formatted_parts.append(f"🤟 ASL Gloss: {response_data['Gloss']}")
        
        # Format video URLs
        video_urls = []
        for url_key in ['PoseURL', 'SignURL', 'AvatarURL']:
            if url_key in response_data and response_data[url_key]:
                video_type = url_key.replace('URL', '').lower()
                video_urls.append(f"• {video_type.title()}: {response_data[url_key]}")
        
        if video_urls:
            formatted_parts.append("🎥 Generated Videos:")
            formatted_parts.extend(video_urls)
        
        return '\n'.join(formatted_parts) if formatted_parts else str(response_data)
    
    def _determine_request_type(self, request_params: Dict[str, Any]) -> str:
        """Determine the type of request from parameters"""
        if 'Gloss' in request_params:
            return 'gloss_to_video'
        elif 'Text' in request_params:
            return 'text_to_asl'
        elif 'BucketName' in request_params and 'KeyName' in request_params:
            return 'audio_to_asl'
        else:
            return 'unknown'
    
    def _determine_websocket_message_type(self, message: Dict[str, Any]) -> str:
        """Determine WebSocket message type"""
        if 'StreamName' in message:
            return 'video_stream_analysis'
        elif 'BucketName' in message and 'KeyName' in message:
            return 'file_analysis'
        elif 'text' in message or 'message' in message:
            return 'text_translation'
        else:
            return 'unknown'
    
    def _determine_workflow_type(self, request_context: Dict[str, Any]) -> str:
        """Determine workflow type from request context"""
        request_type = request_context.get('type', 'unknown')
        if request_type == 'text':
            return 'text_to_asl'
        elif request_type == 'audio':
            return 'audio_to_asl'
        elif request_type == 'video':
            return 'asl_to_text'
        else:
            return 'unknown'
    
    def _extract_tools_used(self, agent_response: Union[str, Dict]) -> List[str]:
        """Extract information about which tools were used"""
        tools_used = []
        response_str = str(agent_response).lower()
        
        if 'gloss' in response_str:
            tools_used.append('text_to_asl_gloss')
        if any(url_type in response_str for url_type in ['poseurl', 'signurl', 'avatarurl']):
            tools_used.append('gloss_to_video')
        if 'transcrib' in response_str:
            tools_used.append('process_audio_input')
        if 'stream' in response_str or 'video' in response_str:
            tools_used.append('analyze_asl_video')
        
        return tools_used
    
    def _create_error_response(self, error_message: str, format_type: ResponseFormat) -> FormattedResponse:
        """Create standardized error response"""
        error_data = {
            'error': error_message,
            'status': 'failed',
            'timestamp': time.time()
        }
        
        if format_type == ResponseFormat.LEGACY_STEP_FUNCTIONS:
            error_data = {
                'executionArn': f"arn:aws:states:us-east-1:123456789012:execution:GenASL-Agent-Error:{int(time.time())}",
                'status': 'FAILED',
                'error': error_message
            }
        
        return FormattedResponse(
            data=error_data,
            format_type=format_type,
            metadata={'error': True, 'error_type': 'formatting_error'}
        )

# Global response formatter instance
response_formatter = ResponseFormatter()

# Convenience functions for different endpoints
def format_rest_api_response(agent_response: Union[str, Dict], 
                           request_params: Dict[str, Any],
                           include_debug: bool = False) -> Dict[str, Any]:
    """Format response for REST API endpoints"""
    formatted = response_formatter.format_for_rest_api(agent_response, request_params, include_debug)
    return formatted.data

def format_websocket_response(agent_response: Union[str, Dict],
                            original_message: Dict[str, Any],
                            connection_id: str,
                            include_debug: bool = False) -> Dict[str, Any]:
    """Format response for WebSocket endpoints"""
    formatted = response_formatter.format_for_websocket(agent_response, original_message, connection_id, include_debug)
    return formatted.data

def format_legacy_response(agent_response: Union[str, Dict],
                         execution_arn: Optional[str] = None) -> Dict[str, Any]:
    """Format response for legacy Step Functions compatibility"""
    formatted = response_formatter.format_for_legacy_compatibility(agent_response, execution_arn)
    return formatted.data

def format_enhanced_response(agent_response: Union[str, Dict],
                           request_context: Dict[str, Any],
                           processing_metrics: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Format enhanced response with full metadata"""
    formatted = response_formatter.format_enhanced_response(agent_response, request_context, processing_metrics)
    return formatted.data