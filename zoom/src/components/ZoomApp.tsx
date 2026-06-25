import React, { useState, useEffect, useCallback } from 'react';
import { Box, Container, Alert, CircularProgress } from '@mui/material';
import { 
  ZoomMeetingInfo, 
  AppState, 
  AppSettings, 
  ASLTranslationResponse, 
  ASLRecognitionResponse,
  ASLError 
} from '@/types/zoom';
import { useZoomMeeting } from '@/hooks/useZoomMeeting';
import { useASLTranslation } from '@/hooks/useASLTranslation';
import MeetingControls from './MeetingControls/MeetingControls';
import ASLTranslator from './ASLTranslator/ASLTranslator';
import AvatarDisplay from './AvatarDisplay/AvatarDisplay';
import SettingsPanel from './SettingsPanel/SettingsPanel';

const defaultSettings: AppSettings = {
  autoStart: false,
  showCaptions: true,
  avatarSize: 'medium',
  avatarPosition: 'bottom-right',
  translationLanguage: 'en',
  signLanguage: 'ASL',
  audioSensitivity: 0.5,
  videoQuality: 'medium'
};

const ZoomApp: React.FC = () => {
  const [appState, setAppState] = useState<AppState>({
    isConnected: false,
    meetingInfo: null,
    aslEnabled: false,
    translationMode: 'both',
    avatarType: '3d',
    currentTranslations: new Map(),
    currentRecognitions: new Map(),
    settings: defaultSettings
  });

  const [showSettings, setShowSettings] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Custom hooks
  const { 
    meetingInfo, 
    isConnected, 
    joinMeeting, 
    leaveMeeting, 
    error: zoomError 
  } = useZoomMeeting();

  const {
    startTranslation,
    stopTranslation,
    isTranslating,
    error: translationError
  } = useASLTranslation();

  // Update app state when meeting info changes
  useEffect(() => {
    setAppState(prev => ({
      ...prev,
      isConnected,
      meetingInfo
    }));
  }, [isConnected, meetingInfo]);

  // Handle errors
  useEffect(() => {
    if (zoomError) {
      setError(`Zoom Error: ${zoomError}`);
    } else if (translationError) {
      setError(`Translation Error: ${translationError}`);
    } else {
      setError(null);
    }
  }, [zoomError, translationError]);

  // Initialize app
  useEffect(() => {
    const initializeApp = async () => {
      try {
        setIsLoading(true);
        
        // Check if we're in a Zoom meeting context
        const urlParams = new URLSearchParams(window.location.search);
        const meetingNumber = urlParams.get('meetingNumber');
        const signature = urlParams.get('signature');
        
        if (meetingNumber && signature) {
          // Auto-join meeting if parameters are provided
          await joinMeeting({
            apiKey: process.env.REACT_APP_ZOOM_API_KEY || '',
            meetingNumber,
            passWord: urlParams.get('password') || '',
            userName: urlParams.get('userName') || 'GenASL User',
            userEmail: urlParams.get('userEmail') || '',
            signature,
            role: parseInt(urlParams.get('role') || '0')
          });
        }
      } catch (error) {
        console.error('Failed to initialize app:', error);
        setError(`Initialization failed: ${error}`);
      } finally {
        setIsLoading(false);
      }
    };

    initializeApp();
  }, [joinMeeting]);

  // Event handlers
  const handleToggleASL = useCallback(() => {
    setAppState(prev => {
      const newEnabled = !prev.aslEnabled;
      
      if (newEnabled && meetingInfo) {
        startTranslation(meetingInfo, prev.settings);
      } else {
        stopTranslation();
      }
      
      return {
        ...prev,
        aslEnabled: newEnabled
      };
    });
  }, [meetingInfo, startTranslation, stopTranslation]);

  const handleChangeMode = useCallback((mode: 'speech-to-asl' | 'asl-to-text' | 'both') => {
    setAppState(prev => ({
      ...prev,
      translationMode: mode
    }));
  }, []);

  const handleChangeAvatarType = useCallback((type: '2d' | '3d') => {
    setAppState(prev => ({
      ...prev,
      avatarType: type
    }));
  }, []);

  const handleOpenSettings = useCallback(() => {
    setShowSettings(true);
  }, []);

  const handleCloseSettings = useCallback(() => {
    setShowSettings(false);
  }, []);

  const handleSettingsChange = useCallback((newSettings: Partial<AppSettings>) => {
    setAppState(prev => ({
      ...prev,
      settings: {
        ...prev.settings,
        ...newSettings
      }
    }));
  }, []);

  const handleTranslationUpdate = useCallback((translation: ASLTranslationResponse) => {
    setAppState(prev => {
      const newTranslations = new Map(prev.currentTranslations);
      newTranslations.set(translation.userId, translation);
      return {
        ...prev,
        currentTranslations: newTranslations
      };
    });
  }, []);

  const handleRecognitionUpdate = useCallback((recognition: ASLRecognitionResponse) => {
    setAppState(prev => {
      const newRecognitions = new Map(prev.currentRecognitions);
      newRecognitions.set(recognition.userId, recognition);
      return {
        ...prev,
        currentRecognitions: newRecognitions
      };
    });
  }, []);

  const handleError = useCallback((error: ASLError) => {
    console.error('ASL Error:', error);
    setError(`ASL Error: ${error.message}`);
  }, []);

  const handleCloseAvatar = useCallback(() => {
    setAppState(prev => ({
      ...prev,
      aslEnabled: false
    }));
    stopTranslation();
  }, [stopTranslation]);

  // Loading state
  if (isLoading) {
    return (
      <Container maxWidth="sm" sx={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh' 
      }}>
        <Box textAlign="center">
          <CircularProgress size={60} />
          <Box mt={2}>Initializing GenASL...</Box>
        </Box>
      </Container>
    );
  }

  // Not connected state
  if (!appState.isConnected || !appState.meetingInfo) {
    return (
      <Container maxWidth="md" sx={{ mt: 4 }}>
        <Alert severity="info">
          GenASL is ready. Join a Zoom meeting to start using sign language translation.
        </Alert>
      </Container>
    );
  }

  // Get current translation for avatar display
  const currentTranslation = Array.from(appState.currentTranslations.values())[0];

  return (
    <Box sx={{ 
      position: 'relative', 
      width: '100%', 
      height: '100vh',
      overflow: 'hidden'
    }}>
      {/* Error Alert */}
      {error && (
        <Alert 
          severity="error" 
          onClose={() => setError(null)}
          sx={{ 
            position: 'absolute', 
            top: 16, 
            left: 16, 
            right: 16, 
            zIndex: 1000 
          }}
        >
          {error}
        </Alert>
      )}

      {/* Meeting Controls */}
      <MeetingControls
        isASLEnabled={appState.aslEnabled}
        translationMode={appState.translationMode}
        avatarType={appState.avatarType}
        onToggleASL={handleToggleASL}
        onChangeMode={handleChangeMode}
        onChangeAvatarType={handleChangeAvatarType}
        onOpenSettings={handleOpenSettings}
      />

      {/* ASL Translator (handles audio/video processing) */}
      {appState.aslEnabled && appState.meetingInfo && (
        <ASLTranslator
          meetingInfo={appState.meetingInfo}
          settings={appState.settings}
          onTranslationUpdate={handleTranslationUpdate}
          onRecognitionUpdate={handleRecognitionUpdate}
          onError={handleError}
        />
      )}

      {/* Avatar Display */}
      {appState.aslEnabled && currentTranslation && (
        <AvatarDisplay
          avatarUrl={appState.avatarType === '3d' ? currentTranslation.avatarUrl : currentTranslation.poseUrl}
          avatarType={appState.avatarType}
          size={appState.settings.avatarSize}
          position={appState.settings.avatarPosition}
          isVisible={appState.aslEnabled}
          onClose={handleCloseAvatar}
        />
      )}

      {/* Captions Display */}
      {appState.settings.showCaptions && appState.currentRecognitions.size > 0 && (
        <Box sx={{
          position: 'absolute',
          bottom: 100,
          left: '50%',
          transform: 'translateX(-50%)',
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          color: 'white',
          padding: 2,
          borderRadius: 1,
          maxWidth: '80%',
          textAlign: 'center',
          zIndex: 999
        }}>
          {Array.from(appState.currentRecognitions.values()).map(recognition => (
            <Box key={recognition.recognitionId}>
              {recognition.text}
            </Box>
          ))}
        </Box>
      )}

      {/* Settings Panel */}
      {showSettings && (
        <SettingsPanel
          settings={appState.settings}
          onSettingsChange={handleSettingsChange}
          onClose={handleCloseSettings}
        />
      )}

      {/* Loading Indicator for Translation */}
      {isTranslating && (
        <Box sx={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          zIndex: 1001
        }}>
          <CircularProgress />
        </Box>
      )}
    </Box>
  );
};

export default ZoomApp;
