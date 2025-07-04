import React from 'react';

interface VideoCompProps {
  // Add any props here if needed
}

const VideoComp: React.FC<VideoCompProps> = () => {
  return (
        <video controls
         autoPlay
          playsInline
          loop
          muted
        >
            <source src="/Users/ssurpo/Downloads/avatar_5.mp4" type="video/mp4"/>
        </video>
  );
};

export default VideoComp;
