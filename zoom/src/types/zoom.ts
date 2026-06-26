// Zoom SDK Types and Interfaces

export interface ZoomConfig {
  sdkKey: string;
  sdkSecret: string;
  webEndpoint?: string;
  language?: string;
  customize?: {
    meetingInfo?: string[];
    toolbar?: {
      buttons?: ToolbarButton[];
    };
  };
}

export interface ToolbarButton {
  text: string;
  className: string;
  onClick: () => void;
}

export interface MeetingConfig {
  apiKey: string;
  meetingNumber: string;
  passWord: string;
  userName: string;
  userEmail?: string;
  leaveUrl?: string;
  role?: number; // 0 for attendee, 1 for host
  signature: string;
}

export interface ZoomMeetingInfo {
  meetingId: string;
  meetingNumber: string;
  topic: string;
  hostId: string;
  participants: Participant[];
  isHost: boolean;
  isRecording: boolean;
}

export interface Participant {
  userId: string;
  userName: string;
  isHost: boolean;
  isMuted: boolean;
  isVideoOn: boolean;
  isHandRaised: boolean;
}

export interface AudioStream {
  userId: string;
  audioData: ArrayBuffer;
  timestamp: number;
}

export interface VideoStream {
  userId: string;
  videoData: ImageData;
  timestamp: number;
}

// GenASL Integration Types
export interface ASLTranslationRequest {
  type: 'audio' | 'text';
  data: string | ArrayBuffer;
  userId: string;
  meetingId: string;
  timestamp: number;
}

export interface ASLTranslationResponse {
  translationId: string;
  gloss: string;
  avatarUrl: string;
  poseUrl: string;
  userId: string;
  timestamp: number;
}

export interface ASLRecognitionRequest {
  videoData: ArrayBuffer;
  userId: string;
  meetingId: string;
  timestamp: number;
}

export interface ASLRecognitionResponse {
  recognitionId: string;
  text: string;
  confidence: number;
  userId: string;
  timestamp: number;
}

// App State Types
export interface AppState {
  isConnected: boolean;
  meetingInfo: ZoomMeetingInfo | null;
  aslEnabled: boolean;
  translationMode: 'speech-to-asl' | 'asl-to-text' | 'both';
  avatarType: '2d' | '3d';
  currentTranslations: Map<string, ASLTranslationResponse>;
  currentRecognitions: Map<string, ASLRecognitionResponse>;
  settings: AppSettings;
}

export interface AppSettings {
  autoStart: boolean;
  showCaptions: boolean;
  avatarSize: 'small' | 'medium' | 'large';
  avatarPosition: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';
  translationLanguage: string;
  signLanguage: 'ASL' | 'BSL' | 'LSF'; // American, British, French Sign Language
  audioSensitivity: number;
  videoQuality: 'low' | 'medium' | 'high';
}

// Event Types
export interface ZoomEvent {
  type: string;
  payload: any;
  timestamp: number;
}

export interface ASLEvent extends ZoomEvent {
  type: 'asl-translation' | 'asl-recognition' | 'asl-error';
  payload: ASLTranslationResponse | ASLRecognitionResponse | Error;
}

// Error Types
export interface ZoomError {
  code: number;
  message: string;
  details?: any;
}

export interface ASLError extends Error {
  code: 'TRANSLATION_FAILED' | 'RECOGNITION_FAILED' | 'NETWORK_ERROR' | 'PERMISSION_DENIED';
  userId?: string;
  meetingId?: string;
}

// WebSocket Message Types
export interface WebSocketMessage {
  type: 'translation-request' | 'translation-response' | 'recognition-request' | 'recognition-response' | 'error';
  payload: any;
  messageId: string;
  timestamp: number;
}

// API Response Types
export interface GenASLAPIResponse<T = any> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: any;
  };
  timestamp: number;
}

// Component Props Types
export interface ASLTranslatorProps {
  meetingInfo: ZoomMeetingInfo;
  settings: AppSettings;
  onTranslationUpdate: (translation: ASLTranslationResponse) => void;
  onRecognitionUpdate: (recognition: ASLRecognitionResponse) => void;
  onError: (error: ASLError) => void;
}

export interface AvatarDisplayProps {
  avatarUrl: string;
  avatarType: '2d' | '3d';
  size: 'small' | 'medium' | 'large';
  position: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';
  isVisible: boolean;
  onClose: () => void;
}

export interface MeetingControlsProps {
  isASLEnabled: boolean;
  translationMode: 'speech-to-asl' | 'asl-to-text' | 'both';
  avatarType: '2d' | '3d';
  onToggleASL: () => void;
  onChangeMode: (mode: 'speech-to-asl' | 'asl-to-text' | 'both') => void;
  onChangeAvatarType: (type: '2d' | '3d') => void;
  onOpenSettings: () => void;
}

export interface SettingsPanelProps {
  settings: AppSettings;
  onSettingsChange: (settings: Partial<AppSettings>) => void;
  onClose: () => void;
}
