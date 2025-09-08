import './Text2Speech.css';
import { post } from 'aws-amplify/api';
import React, { useState } from 'react';
// import axios from 'axios';
import outputs from "../../amplify_outputs.json";

const TextToSpeechConverter: React.FC = () => {
  const [inputText, setInputText] = useState('');
  const [audioUrl, setAudioUrl] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const amplify_env=outputs.custom.ENV.amplify_env;


  const handleConvert = async () => {
    setIsLoading(true);
    setError('');
    setAudioUrl('');

     try {
      const restOperation = post({
        apiName: 'GenASLAPI' + amplify_env,
        path: 'text-to-speech',
        options: {
          body: {
            text: inputText,
            voiceId: 'Joanna' // You can make this configurable if you want
          }
        }
      });

        const { body } = await restOperation.response;
        const response = await body.json();

        console.log('POST call succeeded');
        console.log(response);
        // if (response !=null)
        //     setAudioUrl(response.data.audioUrl);

    } catch (err) {
      console.error('Error converting text to speech:', err);
      setError('An error occurred while converting text to speech. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="text-to-speech-converter">
      <h2>Text to Speech Converter</h2>
      <textarea
        value={inputText}
        onChange={(e) => setInputText(e.target.value)}
        placeholder="Enter English text here..."
        rows={5}
        cols={50}
      />
      <br />
      <button onClick={handleConvert} disabled={isLoading || !inputText.trim()}>
        {isLoading ? 'Converting...' : 'Convert to Speech'}
      </button>
      {error && <p className="error">{error}</p>}
      {audioUrl && (
        <div className="audio-player">
          <h3>Generated Audio:</h3>
          <audio controls src={audioUrl}>
            Your browser does not support the audio element.
          </audio>
          <a href={audioUrl} download="generated_speech.mp3">Download Audio</a>
        </div>
      )}
    </div>
  );
};

export default TextToSpeechConverter;
