import "./ASL2English.css";
import { Component, FormEvent } from "react";
import { getUrl, uploadData } from "aws-amplify/storage";
import CameraImageName from "../assets/camera.png";
import IconButton from "@material-ui/core/IconButton";
import ListenAudioImageName from "../assets/play-button.png";
import React from "react";
import StopCameraImageName from "../assets/stop-button.png";
import StopListenImageName from "../assets/stop-button.png";
import StopStreamingImageName from "../assets/translate-stop.png";
// import StreamingImageName from "../assets/translate-english.png";
import StreamingImageName from "../assets/sign-language-green.png";

import Tooltip from "@mui/material/Tooltip";
import UploadImageName from "../assets/upload-red.png";
import outputs from "../../amplify_outputs.json";
import uuid from "react-uuid";

const amplify_env = outputs.custom.ENV.amplify_env;
// @ts-ignore
const apiUrl = outputs.custom.API[`GenASLAPI${amplify_env}`].endpoint;
// @ts-ignore
const wssUrl = outputs.custom.WSS[`GenASLWSS${amplify_env}`].endpoint;
//const region = outputs.custom.ENV.region; // Provide a default if not set

type ASL2EnglishState = {
  inputVideo: string;
  outputText: string;
  camera: Boolean;
  playing: Boolean;
  streaming: Boolean;
  translating: Boolean;
  wsConnected: Boolean;
  inputFile:string;
  streamName:string;
};

type ASL2EnglishProps = {};
async function compressWebMWithCanvas(
  blob: Blob, 
  options: {
    scaleRatio?: number,
    bitrate?: number,
    frameRate?: number
  } = {}
): Promise<Blob> {
  // Default compression settings
  const {
    scaleRatio = 0.5, // Scale to 50% of original size
    bitrate = 250000, // 250 kbps
    frameRate = 10    // 15fps
  } = options;
  
  return new Promise((resolve, reject) => {
    // Create video element to load source
    const video = document.createElement('video');
    video.src = URL.createObjectURL(blob);
    video.muted = true;
    
    video.onloadedmetadata = () => {
      // Calculate new dimensions
      const width = Math.floor(video.videoWidth * scaleRatio);
      const height = Math.floor(video.videoHeight * scaleRatio);
      
      // Create canvas with scaled dimensions
      const canvas = document.createElement('canvas');
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext('2d')!;
      
      // Create media stream from canvas
      const stream = canvas.captureStream(frameRate);
      
      // Setup MediaRecorder with compression settings
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'video/webm',
        videoBitsPerSecond: bitrate
      });
      
      const chunks: Blob[] = [];
      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunks.push(e.data);
        }
      };
      
      mediaRecorder.onstop = () => {
        URL.revokeObjectURL(video.src);
        const compressedBlob = new Blob(chunks, { type: 'video/webm' });
        console.log(`Compressed from ${blob.size} to ${compressedBlob.size} bytes`);
        console.log(`Compression ratio: ${(100 * compressedBlob.size / blob.size).toFixed(1)}%`);
        resolve(compressedBlob);
      };
      
      // Start recording and play the video
      mediaRecorder.start(100);
      video.play();
      
      // Draw video frames to canvas at reduced size
      function drawFrame() {
        ctx.drawImage(video, 0, 0, width, height);
        
        if (video.ended || video.paused) {
          mediaRecorder.stop();
        } else {
          requestAnimationFrame(drawFrame);
        }
      }
      
      drawFrame();
    };
    
    video.onerror = (err) => {
      reject(new Error(`Failed to load video for compression: ${err}`));
    };
  });
}
class ASL2EnglishForm extends Component<ASL2EnglishProps, ASL2EnglishState> {
  state: ASL2EnglishState;
  fileInputRef = React.createRef<HTMLInputElement>();
  outputTextRef = React.createRef<HTMLTextAreaElement>();
  videoRef = React.createRef<HTMLVideoElement>();
  playButtonRef=React.createRef<HTMLButtonElement>();
  stream?: MediaStream;
  // mediaRecorderRef = React.createRef<MediaRecorder>();
  speech = new Audio();
  recordedChunks: Blob[] = [];
  mediaRecorder!: MediaRecorder;
  constructor(props: ASL2EnglishProps) {
    super(props);

    this.state = {
      inputVideo: "",
      outputText: "",
      camera: false,
      translating: false,
      playing: false,
      streaming: false,
      wsConnected: false,
      inputFile: "",
      streamName:"",
    };
    this.handleCamera = this.handleCamera.bind(this);
    this.handleTranslation = this.handleTranslation.bind(this);
    this.handleUploadFile = this.handleUploadFile.bind(this);
    this.recordedChunks = [];
  }

  private ws: WebSocket | null = null;
  
  async wsscomponentMount() {

    // Replace with WebSocket server URL
    console.log(wssUrl);
    this.ws = new WebSocket(wssUrl);
    console.log("connection ----",this.ws.readyState)
    const delayMs=1000
    const maxAttempts=10
    let attempts=0
    const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
    while (attempts < maxAttempts) {
      await delay(delayMs);
      console.log("WS status",this.ws.readyState,"==", WebSocket.OPEN)
      if (this.ws.readyState === WebSocket.OPEN) {
        break;
      }
      attempts++;
      console.log("attempt==",attempts)
    }

    this.ws.onopen = () => {
      console.log("WebSocket connection established");
      this.setState({ wsConnected: true });
    };

    this.ws.onmessage = async (event) => {
      console.log("Message from server:", event.data);
      // Parse the received message as JSON
      try {
        // const parsedData = JSON.parse(event.data);
        // Update the output text with the received message
         this.setState({ outputText:  event.data }, () => {
  // This callback function will be executed after the state update is complete
        console.log("outputtext",this.state.outputText);
        //play the message
        // this.playButtonRef.current?.click();
});
        //wait for the data change to complete


      } catch (error) {
        console.error("Error parsing WebSocket message:", error);
        // If parsing fails, update with the raw data
        this.setState({ outputText: event.data });
      }
    };

    this.ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      this.setState({ wsConnected: false });
    };

    this.ws.onclose = () => {
      console.log("WebSocket connection closed");
      this.setState({ wsConnected: false });
    };
  }


  wsscomponentWillUnmount() {
    // Clean up the WebSocket connection when the component unmounts
    if (this.ws) {
      this.ws.close();
    }
  }
  
  handleTranslation = async (event: FormEvent<HTMLButtonElement>) => {
    console.log(event);
    if (this.state.translating) {
      console.log("Stopping Translation");
      this.setState({ translating: false });
      //close the WSS connection
      if (this.ws) {
        this.ws.close();
      }
    } else {
      console.log("Starting Translation");
      this.setState({ translating: true });
      //send kinesis or s3 information
      let command={}
        console.log("file")
        command={BucketName:outputs.storage.bucket_name, KeyName:"public/" + this.state.inputFile}
      //establish the WSS connection if it's not already established
      if (!this.ws || this.ws.readyState === WebSocket.CLOSED) {
        await this.wsscomponentMount();
      }
      console.log(command)
      this.sendCustomMessage(JSON.stringify(command));
    }
  };

  sendCustomMessage = (message: string) => {
    if (this.ws && this.ws.readyState === WebSocket.OPEN ) {
      console.log("sending comment", message)
      this.ws.send(message);
    } else {
      console.error("WebSocket is not connected");
    }
  };

  handleCamera = async (): Promise<{ success: boolean; message: string; url?: string }> => {
    if (this.state.camera) {
      try {
        // Stop camera
        this.setState({ camera: false });
        if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
          this.mediaRecorder.stop();
        }
        // Stop all tracks
        if (this.stream) {
          this.stream.getTracks().forEach(track => track.stop());
        }
        if (this.videoRef.current) {
          this.videoRef.current.srcObject = null;
        }
        return { success: true, message: "Camera stopped successfully" };
      } catch (error) {
        console.error('Error stopping camera:', error);
        return { success: false, message: `Error stopping camera: ${error}` };
      }
    } else {
      try {
        this.setState({ camera: true });
        const videoConstraints = { 
        width: { ideal: 640 },     
        height: { ideal: 480 },
        frameRate: { max: 10 }     
      };
        this.stream = await navigator.mediaDevices.getUserMedia({ 
          video: videoConstraints, 
          audio: true 
        });
        
        if (this.videoRef.current) {
          this.videoRef.current.srcObject = this.stream;
        }

        const options = {
          mimeType: 'video/webm;codecs=h264',
          videoBitsPerSecond: 2500000,
        };

        this.mediaRecorder = new MediaRecorder(this.stream, options);
        this.recordedChunks = [];

        return new Promise((resolve) => {
          if (!this.mediaRecorder) {
            resolve({ success: false, message: "MediaRecorder not initialized" });
            return;
          }

          this.mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
              this.recordedChunks.push(event.data);
            }
          };

          this.mediaRecorder.onstop = async () => {
            console.log("Recording stopped")
            try {
              const webmBlob = new Blob(this.recordedChunks, {
                type: 'video/webm'
              });
              console.log("Original webmBlob size:", Math.round(webmBlob.size / 1024), "KB");
    
              // Compress the WebM blob
              const compressedBlob = await compressWebMWithCanvas(webmBlob, {
               scaleRatio: 0.5,   
               bitrate: 250000,   
               frameRate: 10
               });
    console.log("Compressed blob size:", Math.round(compressedBlob.size / 1024), "KB");
              console.log("webmBlob", webmBlob);
              // Generate unique filename
              const fileName = `${uuid()}.webm`;
              const path= `public/recordings/${fileName}`;
              // Upload to S3
              const uploadTask = await uploadData({
                path: path,
                data: webmBlob,
                options: {
                  contentType: 'video/webm'
                }
              });
              await uploadTask.result;

              // Get the URL of the uploaded video
              const linkToUploadedFile = await getUrl({
                path: path,
              });

              // Update state with the new video URL
              this.setState({ 
                inputVideo: linkToUploadedFile.url.href,
                inputFile: fileName 
              });

              resolve({ 
                success: true, 
                message: "Video recorded and uploaded successfully",
                url: linkToUploadedFile.url.href
               });
               console.log("Video recorded and uploaded successfully");
              let command={};
              command={BucketName:outputs.storage.bucket_name, KeyName:path};
              //establish the WSS connection if it's not already established
              if (!this.ws || this.ws.readyState === WebSocket.CLOSED) {
                 await this.wsscomponentMount();
              }
              console.log(command)
              this.sendCustomMessage(JSON.stringify(command));
            } catch (error) {
              resolve({ 
                success: false, 
                message: `Error processing or uploading video: ${error}`
              });
            }
          };

          // Start recording
          this.mediaRecorder.start(1000);
        });

      } catch (error) {
        console.error('Error accessing camera:', error);
        this.setState({ camera: false });
        return { 
          success: false, 
          message: `Error accessing camera: ${error}`
        };
      }
    }
  };
  handlePlayAudio = async () => {
    if (this.state.playing) {
      this.setState({ playing: false });
      this.speech.pause();
      console.log("stopPlaying");
    } else {
      console.log("handleStartPlaying",this.state.outputText);

      if(this.state.outputText==""){
        return;
      }
      this.setState({ playing: true });

      try {
        // Call the API to get the audio content
        console.log(apiUrl + "text-to-speech");
        console.log(JSON.stringify({ text: this.state.outputText }));
        const response = await fetch(apiUrl + "text-to-speech", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ text: this.state.outputText, voiceId :"Stephen" }),
        });

        if (!response.ok) {
          throw new Error("Network response was not ok");
        }
        console.log(response);
        const data = await response.json();

        // Decode the base64 audio content
        const audioContent = atob(data.audioContent);

        // Convert the decoded content to an ArrayBuffer
        const arrayBuffer = new ArrayBuffer(audioContent.length);
        const uintArray = new Uint8Array(arrayBuffer);
        for (let i = 0; i < audioContent.length; i++) {
          uintArray[i] = audioContent.charCodeAt(i);
        }

        // Create a Blob from the ArrayBuffer
        const blob = new Blob([arrayBuffer], { type: "audio/mp3" });
        // Create an audio element and play it
        const audioUrl = URL.createObjectURL(blob);
        this.speech.src = audioUrl;
        this.speech.onended = () => {
          this.setState({ playing: false });
          URL.revokeObjectURL(audioUrl); // Clean up the Blob URL
        };
        this.speech.play();
      } catch (error) {
        console.error("Error fetching or playing audio:", error);
        this.setState({ playing: false });
      }
    }
  };

  handleUploadFile = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      const keyName = "videos/" + file.name;
    
      
      // Upload the file
      const uploadTask = await uploadData({
        path: "public/" + keyName,
        data: file
      });
      await uploadTask.result;
      console.log("finished uploading");
      
      console.log("bucketName", outputs.storage.bucket_name);
 
      this.setState({ inputFile: keyName });

      const linkToUploadedFile = await getUrl({
        path: "public/" + keyName,
      });
      console.log("uploaded video URL: ", linkToUploadedFile.url.href);
      this.setState({ inputVideo: linkToUploadedFile.url.href });
      console.log("after setting the input url");
    } catch (error) {
      console.error("Error uploading file:", error);
    }
  };
  handleChange = () => {
    console.log(this.state.outputText);
  };

  render() {
    return (
      <div>
        <table id="ASL2ENG-Table-Container" className="ASL2ENG_Container">
          <th></th>
          <th></th>
          <tbody>
            <tr>
              <td>
                <div id="ASL2ENG-Div-Input" className="ASL2ENG_InputPanel">
                  <table id="ASL2ENG-Table-Input" className="ASL2ENG_InputSection">
                    <th>
                      <p>ASL Video</p>
                    </th>
                    <tbody>
                      <tr>
                        <td>
                          <div id="ASL2ENG-Div-Input-Video" className="ASL2ENG_Video-Box">
                            <video
                              key={"input" + this.state.inputVideo}
                              autoPlay
                              playsInline
                              loop
                              muted
                              ref={this.videoRef}
                              style={{ width: "100%", height: "100%" }}
                            >
                              <source src={this.state.inputVideo} />
                            </video>
                          </div>
                        </td>
                      </tr>
                      <tr>
                        <td>
                          <table id="ASL2ENG-Table-ButtonGroup" className="ASL2ENG_ButtonGroup">
                            <tr>
                              <td>
                                <div className="ASL2ENG_Icon-Btn">
                                  <input
                                    accept="video/*"
                                    id="icon-button-file"
                                    type="file"
                                    onChange={this.handleUploadFile}
                                    style={{ display: "none" }}
                                    ref={this.fileInputRef}
                                  />
                                  <Tooltip title="Upload Video" className="ASL2ENG_Icon-Btn-Tooltip">
                                    <IconButton
                                      color="primary"
                                      aria-label="upload video"
                                      component="span"
                                      // onClick={this.handleUploadFile}
                                      onClick={() => this.fileInputRef.current?.click()}
                                    >
                                      <img className="ASL2ENG_Icon-Btn-Img" src={UploadImageName} alt="Upload Button" />
                                    </IconButton>
                                  </Tooltip>
                                </div>
                              </td>
                              <td>
                                <div className="ASL2ENG_Icon-Btn">
                                  <Tooltip
                                    title={this.state.camera ? "Stop Camera" : "Start Camera"}
                                    className="ASL2ENG_Icon-Btn-Tooltip"
                                  >
                                    <IconButton onClick={this.handleCamera}>
                                      <img
                                        className="ASL2ENG_Icon-Btn-Img"
                                        src={this.state.camera ? StopCameraImageName : CameraImageName}
                                        alt="Camera Button"
                                      />
                                    </IconButton>
                                  </Tooltip>
                                </div>
                              </td>
                              <td>
                                <div className="ASL2ENG_Icon-Btn">
                                  <Tooltip
                                    title={this.state.streaming ? "Stop Translation" : "Start Translation"}
                                    className="ASL2ENG_Icon-Btn-Tooltip"
                                  >
                                    <IconButton onClick={this.handleTranslation}>
                                      <img
                                        className="ASL2ENG_Icon-Btn-Img"
                                        src={this.state.translating ? StopStreamingImageName : StreamingImageName}
                                        alt="Translate Button"
                                      />
                                    </IconButton>
                                  </Tooltip>
                                </div>
                              </td>
                            </tr>
                          </table>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </td>
              <td>
                <div id="ASL2ENG-Div-Output" className="ASL2ENG_OutputPanel">
                  <table id="ASL2ENG-Table-Output" className="ASL2ENG_OutputSection">
                    <th>
                      <p>English Translation</p>
                    </th>
                    <tbody>
                      <tr>
                        <td>
                          <div id="ASL2ENG-Div-Output-Text" className="ASL2ENG_TextPanel">
                            <textarea
                              id="ASL2ENG-TextArea-Output"
                              ref={this.outputTextRef!}
                              value={this.state.outputText}
                              onChange={this.handleChange}
                              className="ASL2ENG_TextOutput"
                            />
                          </div>
                        </td>
                      </tr>
                      <tr>
                        <td>
                          <table id="ASL2ENG-Table-ButtonGroup" className="ASL2ENG_ButtonGroup">
                            <tr>
                              <td>
                                <div className="ASL2ENG_Icon-Btn">
                                  <Tooltip
                                    title={this.state.playing ? "Stop Playing" : "Play Audio"}
                                    className="ASL2ENG_Icon-Btn-Tooltip"
                                  >
                                    <IconButton onClick={this.handlePlayAudio} ref={this.playButtonRef}>
                                      <img
                                        className="ASL2ENG_Icon-Btn-Img"
                                        src={this.state.playing ? StopListenImageName : ListenAudioImageName}
                                        alt="Record Video Button"
                                      />
                                    </IconButton>
                                  </Tooltip>
                                </div>
                              </td>
                            </tr>
                          </table>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    );
  }
}

export default ASL2EnglishForm;
