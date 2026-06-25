import { initGenASLAPI } from '@/services/genASLAPI';
import { ZoomMeetingInfo, AppSettings } from '@/types/zoom';

export const useASLTranslation = () => {
  const startTranslation = (meetingInfo: ZoomMeetingInfo, settings: AppSettings) => {
    console.log('Starting ASL translation for meeting:', meetingInfo.meetingId);
    console.log('Settings:', settings);
    
    // Initialize GenASL API if needed
    try {
      initGenASLAPI({
        apiUrl: process.env.REACT_APP_GENASL_API_URL || 'https://api.genasl.com',
        apiKey: process.env.REACT_APP_GENASL_API_KEY,
      });
    } catch (error) {
      console.log('GenASL API initialization (mock mode):', error);
    }
  };

  const stopTranslation = () => {
    console.log('Stopping ASL translation');
  };

  return {
    startTranslation,
    stopTranslation,
    isTranslating: false,
    error: null
  };
};
