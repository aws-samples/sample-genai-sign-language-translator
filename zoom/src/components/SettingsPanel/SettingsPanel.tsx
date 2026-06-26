import React from 'react';

const SettingsPanel = (props: any) => {
  const { settings, onSettingsChange, onClose } = props;

  return React.createElement('div', {
    style: {
      position: 'fixed',
      top: '50%',
      left: '50%',
      transform: 'translate(-50%, -50%)',
      backgroundColor: 'white',
      padding: '20px',
      borderRadius: '8px',
      boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
      zIndex: 2000,
      minWidth: '300px'
    }
  }, [
    React.createElement('h3', { key: 'title' }, 'GenASL Settings'),
    React.createElement('div', { key: 'content' }, 'Settings panel coming soon...'),
    React.createElement('button', {
      key: 'close',
      onClick: onClose,
      style: {
        marginTop: '10px',
        padding: '8px 16px',
        backgroundColor: '#2196f3',
        color: 'white',
        border: 'none',
        borderRadius: '4px',
        cursor: 'pointer'
      }
    }, 'Close')
  ]);
};

export default SettingsPanel;
