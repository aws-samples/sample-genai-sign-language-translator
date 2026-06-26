import React from 'react';

const AvatarDisplay = (props: any) => {
  const { avatarUrl, avatarType, size, position, isVisible, onClose } = props;

  if (!isVisible) return null;

  return React.createElement('div', {
    style: {
      position: 'fixed',
      bottom: '20px',
      right: '20px',
      width: size === 'large' ? '400px' : size === 'medium' ? '300px' : '200px',
      height: size === 'large' ? '300px' : size === 'medium' ? '200px' : '150px',
      backgroundColor: '#000',
      borderRadius: '8px',
      zIndex: 15,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      color: 'white'
    }
  }, [
    React.createElement('div', { key: 'content' }, `${avatarType.toUpperCase()} Avatar`),
    React.createElement('button', {
      key: 'close',
      onClick: onClose,
      style: {
        position: 'absolute',
        top: '5px',
        right: '5px',
        background: 'rgba(255,255,255,0.2)',
        border: 'none',
        color: 'white',
        cursor: 'pointer',
        borderRadius: '50%',
        width: '24px',
        height: '24px'
      }
    }, '×')
  ]);
};

export default AvatarDisplay;
