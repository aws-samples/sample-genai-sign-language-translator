import "./ASLForm.css";

import React, { Component, FormEvent } from "react";

import IconButton from "@material-ui/core/IconButton";
import ListenImageName from "../assets/voice-blue.png";
import StopImageName from "../assets/stop-button.png";
import Tooltip from "@mui/material/Tooltip";
import TranslateImageName from "../assets/sign-language-green.png";
import UploadImageName from "../assets/upload-red.png";
import { fetchAuthSession } from "aws-amplify/auth";
import outputs from "../../amplify_outputs.json";
import {getUrl, uploadData} from "aws-amplify/storage";
import uuid from "react-uuid";

const amplify_env = outputs.custom.ENV.amplify_env;
// @ts-ignore
const apiUrl = outputs.custom.API[`GenASLAPI${amplify_env}`]?.endpoint || outputs.custom.API['GenASLAPImain']?.endpoint || 'API_NOT_CONFIGURED';

// const apiUrl ="https://8yt8q8ij18.execute-api.us-west-2.amazonaws.com/prod/audio-to-sign";

// const VideoComponent = React.memo(function MyVideoComponent({url}) {
//       // only renders if url have changed!
//       return (<video src={url}></video>)
// });

type ASLFormState = {
  value: string;
  gloss: string;
  signVideo: string;
  humanAvatarVideo: string;
  poseVideo: string;
  blendedPoseVideo: string;
  listening: Boolean;
  letterCount: Number;
  file: any;
  inputVideo: string;
};

type ASLFormProps = {};

class ASLForm extends Component<ASLFormProps, ASLFormState> {
  textareaRef = React.createRef<HTMLTextAreaElement>();
  glossRef = React.createRef<HTMLTextAreaElement>();
  avatarVideoRef = React.createRef<HTMLVideoElement>();
  fileInputRef = React.createRef<HTMLInputElement>();
  state: ASLFormState;
  recognition: SpeechRecognition;

  constructor(props: ASLFormProps) {
    super(props);
    this.state = {
      value: "",
      gloss: "",
      signVideo: "",
      humanAvatarVideo: "",
      poseVideo: "",
      blendedPoseVideo: "",
      inputVideo: "",
      listening: false,
      letterCount: 0,
      file: null,
    };
    this.handleRecording = this.handleRecording.bind(this);
    this.handleChange = this.handleChange.bind(this);
    this.handleSubmit = this.handleSubmit.bind(this);
    this.handleUploadFile = this.handleUploadFile.bind(this);
    let SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    this.recognition = new SpeechRecognition();
    this.recognition.onresult = (event) => {
      console.log("onresult");
      const transcript = event.results[0][0].transcript;
      this.setState({ value: transcript });
      console.log("transcript==" + transcript + "==");
      if (transcript !== "") {
        console.log("getVideos");
        this.getSignVideos({ Text: transcript });
      }
    };
  }

  handleChange = (event: FormEvent<HTMLTextAreaElement>): void => {
    const inputValue = event.currentTarget.value;
    const count = inputValue.replace(/[^a-zA-Z]/g, "").length;
    this.setState({ value: inputValue, letterCount: count });
  };

  handleRecording = () => {
    if (this.state.listening) {
      this.recognition.stop();
      this.setState({ listening: false });
      console.log("stopListening");
      //event.preventDefault();
    } else {
      console.log("handleStartListening");
      this.recognition.start();
      this.setState({ value: "", listening: true });
      // event.preventDefault();
    }
  };

  handleSubmit = (event: FormEvent<HTMLButtonElement>) => {
    event.preventDefault();
    //call the API
    //this.getSignVideos(this.state.value);
    console.log("handleSubmit");
    this.getSignVideos({ Text: this.state.value });
  };

  handleFileEvent = (event: any) => {
    this.setState({ file: event.target.files[0] });
    console.log("file");
    console.log(event.target.files[0]);
  };

  handleUploadFile = async () => {
    await fetchAuthSession({ forceRefresh: true });
    // const session = await fetchAuthSession();
    // console.log("id token", session.tokens.idToken)
    // console.log("access token", session.tokens.accessToken)

    console.log("upload triggered");

    // @ts-ignore
    const file = this.fileInputRef.current.files[0];
    const keyName = uuid() + "/" + file.name;
    console.log(keyName);
    try {
      const uploadTask = await uploadData({ path: "public/" + keyName, data: file });
      await uploadTask.result;
      console.log("finished uploading");
      console.log(keyName);

       const linkToUploadedFile = await getUrl({
        path: "public/" + keyName,
      });
      console.log("signed URL: ", linkToUploadedFile.url.href);
      this.setState({ inputVideo: linkToUploadedFile.url.href });

      this.getSignVideos({
        BucketName: outputs.storage.bucket_name,
        KeyName: "public/" + keyName,
      });
    } catch (error) {
      console.error("Error uploading file:", error);
    }

    // await Storage.put(keyName, file, {});
  };

  getSignVideos = async (input: Record<string, string>) => {
    //   this.setState({signVideo:"",
    // poseVideo:"", gloss:"" ,humanAvatarVideo:""})
    console.log(apiUrl);
    console.log("Submitting input:", input);
    console.log(amplify_env);
    const initRequest = async (input: Record<string, string>) => {
      const params = new URLSearchParams(input);
      console.log("params", params);
      console.log(`${apiUrl}audio-to-sign?${params}`)
      const response = await fetch(`${apiUrl}audio-to-sign?${params}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });
      return await response.text();
    };

    let sfn_execution_arn = "starting";
    const rawResponse = await initRequest(input);
    let data;
    data = JSON.parse(rawResponse);
    if (data.sfn_execution_arn) {
      sfn_execution_arn = data.sfn_execution_arn;
    }

    const checkRequest = async (sfn_execution_arn: String) => {
      const params = new URLSearchParams({ sfn_execution_arn: sfn_execution_arn } as unknown as Record<string, string>);

      const response = await fetch(`${apiUrl}audio-to-sign?${params}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });
      return await response.text();
    };

    let attempts = 0;
    const maxAttempts = 1000; // Adjust as needed
    const delayMs = 2000; // Delay in milliseconds (1 second in this example)

    // Helper function to create a delay
    const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
    while (attempts < maxAttempts) {
      await delay(delayMs);
      const rawResponse = await checkRequest(sfn_execution_arn);
      console.log(`Raw response (attempt ${attempts + 1}):`, rawResponse);

      let data;
      data = JSON.parse(rawResponse);
      if (data.sfn_execution_arn) {
        sfn_execution_arn = data.sfn_execution_arn;
        console.log("Process not complete, polling...", data);
        attempts++;
      } else {
        console.log("Process complete, existing...", data);
        data = data.Payload;
        console.log("gloss", data.Gloss);
        console.log("Avatar URL", data.AvatarURL);
        this.setState({
          signVideo: data.SignURL,
          poseVideo: data.PoseURL,
          humanAvatarVideo: data.AvatarURL,
          blendedPoseVideo:data.PoseURL,
          gloss: data.Gloss,
          value: data.Text,
        });

  console.log(data.SignURL)
        // this.getBlendedVideos({ Gloss: data.Gloss });
        break;
      }
    }
  };

  getBlendedVideos = async (input: Record<string, string>) => {
    //   this.setState({signVideo:"",
    // poseVideo:"", gloss:"" ,humanAvatarVideo:""})

    console.log(apiUrl);
    console.log("Submitting input:", input);
    console.log(amplify_env);
    const initRequest = async (input: Record<string, string>) => {
      const params = new URLSearchParams(input);
      const response = await fetch(`${apiUrl}audio-to-sign?${params}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });
      return await response.text();
    };

    let sfn_execution_arn = "starting";
    const rawResponse = await initRequest(input);
    let data;
    data = JSON.parse(rawResponse);
    if (data.sfn_execution_arn) {
      sfn_execution_arn = data.sfn_execution_arn;
    }

    const checkRequest = async (sfn_execution_arn: String) => {
      const params = new URLSearchParams({ sfn_execution_arn: sfn_execution_arn } as unknown as Record<string, string>);

      const response = await fetch(`${apiUrl}audio-to-sign?${params}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });
      return await response.text();
    };

    let attempts = 0;
    const maxAttempts = 1000; // Adjust as needed
    const delayMs = 2000; // Delay in milliseconds (1 second in this example)

    // Helper function to create a delay
    const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
    while (attempts < maxAttempts) {
      await delay(delayMs);
      const rawResponse = await checkRequest(sfn_execution_arn);
      console.log(`Raw response (attempt ${attempts + 1}):`, rawResponse);

      let data;
      data = JSON.parse(rawResponse);
      if (data.sfn_execution_arn) {
        sfn_execution_arn = data.sfn_execution_arn;
        console.log("Process not complete, polling...", data);
        attempts++;
      } else {
        console.log("Process complete, existing...", data);
        // data=data.Payload
        console.log("Blended URL", data.SmoothPoseURL);

        this.setState({
          blendedPoseVideo: data.SmoothPoseURL,
        });
        break;
      }
    }
  };

  //     const response = await fetch(`${apiUrl}?${new URLSearchParams({Text:text} as Record<string, string>)}`, {
  //         method: 'POST',
  //         headers: {
  //           'Content-Type': 'application/json',
  //         }
  //       });
  //     const rawResponse = await response.text();
  //     console.log('Raw response:', rawResponse);

  //   }

  render() {
    // @ts-ignore
    return (
      <div>
        <table id="ENG2ASL-Table-Container" className="ENG2ASL_Container">
          <thead>
          <tr>
            <th></th>
            <th></th>
            <th></th>
            <th></th>
          </tr></thead>
            <tbody>
            <tr>
              <td rowSpan={2}>
                <div id="ENG2ASL-Div-Input" className="ENG2ASL_InputPanel">
                  <table id="ENG2ASL-Table-Input" className="ENG2ASL_InputSection">

                      <th>
                        <p>English
                          (Video/Audio/Text)</p>
                      </th>

                    <tbody>
                    <tr>
                      <td>
                          <textarea
                              id="ENG2ASL-TextArea-Input"
                              ref={this.textareaRef!}
                              value={this.state.value}
                              onChange={this.handleChange}
                              className="ENG2ASL_TextInput"
                          />
                      </td>
                    </tr>
                    <tr>
                      <td>
                        {/*<div id="ENG2ASL-Div-Input-Video" className="ENG2ASL_Video-Box">*/}
                          <video
                              key={"inputVideo" + this.state.inputVideo}
                              autoPlay
                              playsInline
                              loop
                              muted
                              style={{width: "100%", height: "100%"}}
                          >
                            <source src={this.state.inputVideo}/>
                          </video>
                        {/*</div>*/}
                      </td>
                    </tr>
                    <tr>
                      <td>
                        <div>
                          <p className="ENG2ASL_TextInputCount">{this.state.letterCount.toString()}/500</p>
                        </div>
                      </td>
                    </tr>
                    <tr>
                      <td>
                        <table id="ENG2ASL-Table-ButtonGroup" className="ENG2ASL_ButtonGroup">
                          <tbody>
                          <tr>
                            <td>
                              <div className="ENG2ASL_Icon-Btn">
                                <input
                                    accept="audio/*"
                                    id="icon-button-file"
                                    type="file"
                                    onChange={this.handleUploadFile}
                                    style={{display: "none"}}
                                    ref={this.fileInputRef}
                                />
                                <Tooltip title="Upload" className="ENG2ASL_Icon-Btn-Tooltip">
                                  <IconButton
                                      color="primary"
                                      aria-label="upload"
                                      component="span"
                                      // onClick={this.handleUploadFile}
                                      onClick={() => this.fileInputRef.current?.click()}
                                  >
                                    <img className="ENG2ASL_Icon-Btn-Img" src={UploadImageName} alt="Upload Button"/>
                                  </IconButton>
                                </Tooltip>
                              </div>
                            </td>
                            <td>
                              <div className="ENG2ASL_Icon-Btn">
                                <Tooltip
                                    title={this.state.listening ? "Stop Recording" : "Record"}
                                    className="ENG2ASL_Icon-Btn-Tooltip"
                                >
                                  <IconButton onClick={this.handleRecording}>
                                    <img
                                        className="ENG2ASL_Icon-Btn-Img"
                                        src={this.state.listening ? StopImageName : ListenImageName}
                                        alt="Speak Button"
                                    />
                                  </IconButton>
                                </Tooltip>
                              </div>
                            </td>
                            <td>
                              <div className="ENG2ASL_Icon-Btn">
                                <Tooltip title="Translate" className="ENG2ASL_Icon-Btn-Tooltip">
                                  <IconButton onClick={this.handleSubmit}>
                                    <img
                                        className="ENG2ASL_Icon-Btn-Img"
                                        src={TranslateImageName}
                                        alt="Translate"
                                    />
                                  </IconButton>
                                </Tooltip>
                              </div>
                            </td>
                          </tr>
                          </tbody>
                        </table>
                      </td>
                    </tr>
                    </tbody>
                  </table>
                </div>
              </td>
              <td rowSpan={2}>
                <div id="ENG2ASL-Div-Gloss" className="ENG2ASL_GlossPanel">
                  <table id="ENG2ASL-Table-Gloss" className="ENG2ASL_GlossSection">
                    <thead>
                    <tr>
                      <th>ASL Gloss</th>
                    </tr>
                    </thead>
                    <tbody>
                    <tr>
                      <td>
                      <div id="ENG2ASL-Div-Gloss-Video" className="ENG2ASL_Video-Box">
                            <textarea
                                id="ENG2ASL-TextArea-Gloss"
                                ref={this.glossRef!}
                                value={this.state.gloss}
                                readOnly
                                className="ENG2ASL_TextInput"
                            />
                        </div>
                      </td>
                    </tr>
                    </tbody>
                  </table>
                </div>
              </td>
              <td>
                <div id="ENG2ASL-Div-Sign" className="ENG2ASL_VideoPanel">
                  <table id="ENG2ASL-Table-Sign" className="ENG2ASL_VideoSection">
                    <thead>
                    <tr>
                      <th>Sign Video</th>
                    </tr>
                    </thead>
                    <tbody>
                    <tr>
                      <td>
                        <div id="ENG2ASL-Div-Sign-Video" className="ENG2ASL_Video-Box">
                          <video
                              key={"sign" + this.state.signVideo}
                              autoPlay
                              playsInline
                              loop
                              muted
                              style={{width: "100%", height: "100%"}}
                          >
                            <source src={this.state.signVideo}/>
                          </video>
                        </div>
                      </td>
                    </tr>
                    </tbody>
                  </table>
                </div>
              </td>
              <td rowSpan={2}>
                <div id="ENG2ASL-Div-HumanAvatar" className="ENG2ASL_3DAvatarPanel">
                  <table id="ENG2ASL-Table-HumanAvatar" className="ENG2ASL_VideoSection">
                    <thead>
                    <tr>
                      <th>3D Avatar</th>
                    </tr>
                    </thead>
                    <tbody>
                    <tr>
                      <td>
                        <div id="ENG2ASL-Div-HumanAvatar-Video" className="ENG2ASL_Avatar-Video-Box">
                          <video
                              key={"humanAvatar" + this.state.humanAvatarVideo}
                              ref={this.avatarVideoRef}
                              autoPlay
                              playsInline
                              loop
                              muted
                              style={{width: "100%", height: "100%"}}
                          >
                            <source src={this.state.humanAvatarVideo}/>

                            {/*<source src={this.state.humanAvatarVideo}/>*/}
                          </video>
                        </div>
                      </td>
                    </tr>
                    </tbody>
                  </table>
                </div>
              </td>
            </tr>
            <tr>
              <td>
                <div id="ENG2ASL-Div-StickAvatar" className="ENG2ASL_VideoPanel">
                  <table id="ENG2ASL-Table-StickAvatar" className="ENG2ASL_VideoSection">
                    <thead>
                    <tr>
                      <th>2D Avatar</th>
                    </tr>
                    </thead>
                    <tbody>
                    <tr>
                      <td>
                        <div id="ENG2ASL-Div-StickAvatar-Video" className="ENG2ASL_Video-Box">
                          <video
                              key={"stickAvatar" + this.state.blendedPoseVideo}
                              autoPlay
                              playsInline
                              loop
                              muted
                              style={{width: "100%", height: "100%"}}
                          >
                            <source src={this.state.blendedPoseVideo}/>
                          </video>
                        </div>
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

export default ASLForm;
