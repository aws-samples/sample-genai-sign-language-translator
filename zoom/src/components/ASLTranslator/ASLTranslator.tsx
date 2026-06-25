import React from 'react';

const ASLTranslator = (props: any) => {
  const { meetingInfo, settings, onTranslationUpdate, onRecognitionUpdate, onError } = props;

  React.useEffect(() => {
    console.log('ASL Translator initialized for meeting:', meetingInfo?.meetingId);
    console.log('Settings:', settings);
    
    // Mock translation update
    setTimeout(() => {
      if (onTranslationUpdate) {
        onTranslationUpdate({
          translationId: 'mock-translation-1',
          gloss: 'HELLO WORLD',
          avatarUrl: 'https://example.com/avatar.mp4',
          poseUrl: 'https://example.com/pose.mp4',
          userId: 'mock-user',
          timestamp: Date.now()
        });
      }
    }, 2000);
  }, [meetingInfo, settings, onTranslationUpdate]);

  return React.createElement('div', {
    style: {
      position: 'absolute',
      top: 0,
      left: 0,
      width: '100%',
      height: '100%',
      pointerEvents: 'none',
      zIndex: 5
    }
  }, 'ASL Translator Active');
};

export default ASLTranslator;
