import React from 'react';

const MeetingControls = (props: any) => {
  const {
    isASLEnabled,
    translationMode,
    avatarType,
    onToggleASL,
    onChangeMode,
    onChangeAvatarType,
    onOpenSettings
  } = props;

  return (
    <div
      style={{
        position: 'fixed',
        bottom: '20px',
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 1000,
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        borderRadius: '8px',
        padding: '16px',
        display: 'flex',
        gap: '8px'
      }}
    >
      <button
        onClick={onToggleASL}
        style={{
          padding: '8px 16px',
          backgroundColor: isASLEnabled ? '#f44336' : '#2196f3',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer'
        }}
      >
        {isASLEnabled ? 'Stop ASL' : 'Start ASL'}
      </button>
      
      <button
        onClick={() => {
          const modes = ['speech-to-asl', 'asl-to-text', 'both'];
          const currentIndex = modes.indexOf(translationMode);
          const nextMode = modes[(currentIndex + 1) % modes.length];
          onChangeMode(nextMode);
        }}
        disabled={!isASLEnabled}
        style={{
          padding: '8px 16px',
          backgroundColor: isASLEnabled ? '#4caf50' : '#666',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: isASLEnabled ? 'pointer' : 'not-allowed'
        }}
      >
        {translationMode === 'both' ? 'Both' : 
         translationMode === 'speech-to-asl' ? 'Speech→ASL' : 'ASL→Text'}
      </button>
      
      <button
        onClick={() => onChangeAvatarType(avatarType === '2d' ? '3d' : '2d')}
        disabled={!isASLEnabled}
        style={{
          padding: '8px 16px',
          backgroundColor: isASLEnabled ? '#ff9800' : '#666',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: isASLEnabled ? 'pointer' : 'not-allowed'
        }}
      >
        {avatarType === '2d' ? '2D Avatar' : '3D Avatar'}
      </button>
      
      <button
        onClick={onOpenSettings}
        style={{
          padding: '8px 16px',
          backgroundColor: '#9c27b0',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer'
        }}
      >
        Settings
      </button>
    </div>
  );
};

export default MeetingControls;
