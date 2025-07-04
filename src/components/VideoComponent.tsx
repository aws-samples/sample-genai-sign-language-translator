import React, { useState, useRef, useEffect } from 'react';
import { uploadData } from 'aws-amplify/storage';
import { fetchAuthSession } from 'aws-amplify/auth';
import { KinesisVideo } from '@aws-sdk/client-kinesis-video';
import { KinesisVideoMedia } from '@aws-sdk/client-kinesis-video-media';
import {Amplify} from "aws-amplify";


const VideoComponent: React.FC = () => {
  const awsconfig = Amplify.getConfig();
  const [isCamera, setIsCamera] = useState(true);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamName] = useState(`my-stream-${Date.now()}`);
  const [uploadProgress, setUploadProgress] = useState(0);

  const videoRef = useRef<HTMLVideoElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const region = awsconfig.Storage.S3.region; // Provide a default if not set

  useEffect(() => {
    const setupStream = async () => {
      try {
        const { credentials } = await fetchAuthSession();
        if (!credentials) throw new Error('No credentials');
        console.log(awsconfig)

        const kinesisVideo = new KinesisVideo({
          region: region,
          credentials: credentials,
        });


        console.log('StreamName',streamName)
        await kinesisVideo.createStream({
          StreamName: streamName,
          DataRetentionInHours: 24,
          MediaType: 'video/webm',
        });

        console.log('Stream created successfully');
      } catch (error) {
        console.error('Error setting up stream:', error);
      }
    };

    if (isCamera) {
      setupStream();
    }
  }, [isCamera, streamName]);

  const startStreaming = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }

      const { credentials } = await fetchAuthSession();
      if (!credentials) throw new Error('No credentials');

      // const kinesisVideoMedia = new KinesisVideoMedia({
      //   region: region,
      //   credentials: credentials,
      // });

      const kinesisVideo = new KinesisVideo({
          region: region,
          credentials: credentials,
        });


       const endPoint= await kinesisVideo.getDataEndpoint({
          APIName: 'PUT_MEDIA',
          StreamName: streamName,
        });

      mediaRecorderRef.current = new MediaRecorder(stream, { mimeType: 'video/webm' });

      mediaRecorderRef.current.ondataavailable = async (event) => {
        if (event.data.size > 0) {
          const chunk = await event.data.arrayBuffer();
          await endPoint.putMedia({
            StreamName: streamName,
            Data: new Uint8Array(chunk),
            ProducerTimestamp: new Date(),
          });
        }
      };

      mediaRecorderRef.current.start(1000); // Collect data every second
      setIsStreaming(true);
    } catch (error) {
      console.error('Error starting stream:', error);
    }
  };

  const stopStreaming = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
    }
    if (videoRef.current && videoRef.current.srcObject) {
      const tracks = (videoRef.current.srcObject as MediaStream).getTracks();
      tracks.forEach(track => track.stop());
    }
    setIsStreaming(false);
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      const result = await uploadData({
        key: `public/videos/${file.name}`,
        data: file,
        options: {
          onProgress: ({ loaded, total }) => {
            setUploadProgress(Math.round((loaded / total) * 100));
          },
        },
      }).result;

      console.log('Upload successful:', result);
      setUploadProgress(0);
    } catch (error) {
      console.error('Error uploading file:', error);
      setUploadProgress(0);
    }
  };

  return (
    <div>
      <div>
        <label>
          <input
            type="checkbox"
            checked={isCamera}
            onChange={() => setIsCamera(!isCamera)}
          />
          Use Camera
        </label>
      </div>

      {isCamera ? (
        <div>
          <video ref={videoRef} autoPlay playsInline muted />
          <button onClick={isStreaming ? stopStreaming : startStreaming}>
            {isStreaming ? 'Stop Streaming' : 'Start Streaming'}
          </button>
        </div>
      ) : (
        <div>
          <input
            type="file"
            accept="video/*"
            onChange={handleFileUpload}
            ref={fileInputRef}
          />
          {uploadProgress > 0 && <progress value={uploadProgress} max="100" />}
        </div>
      )}
    </div>
  );
};

export default VideoComponent;
