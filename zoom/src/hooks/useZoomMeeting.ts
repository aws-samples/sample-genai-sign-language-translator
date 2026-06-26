import React, { useState, useCallback } from 'react';
import { ZoomMeetingInfo, MeetingConfig } from '@/types/zoom';
import zoomSDK from '@/services/zoomSDK';

export const useZoomMeeting = () => {
  const [meetingInfo, setMeetingInfo] = useState<ZoomMeetingInfo | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const joinMeeting = useCallback(async (config: MeetingConfig) => {
    try {
      setIsLoading(true);
      setError(null);
      
      // Initialize SDK if not already done
      if (!zoomSDK.isSDKInitialized()) {
        await zoomSDK.init({
          sdkKey: config.apiKey,
          sdkSecret: '', // Not needed for mock
          webEndpoint: process.env.REACT_APP_ZOOM_WEB_ENDPOINT || 'http://localhost:3001'
        });
      }

      const meeting = await zoomSDK.joinMeeting(config);
      setMeetingInfo(meeting);
      setIsConnected(true);
      
      return meeting;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to join meeting';
      setError(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const leaveMeeting = useCallback(async () => {
    try {
      await zoomSDK.leaveMeeting();
      setMeetingInfo(null);
      setIsConnected(false);
      setError(null);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to leave meeting';
      setError(errorMessage);
    }
  }, []);

  return {
    meetingInfo,
    isConnected,
    error,
    isLoading,
    joinMeeting,
    leaveMeeting
  };
};
