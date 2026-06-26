const Alexa = require('ask-sdk-core');
const AWS = require('aws-sdk');
const output = require('./alexa_outputs.json')

// Configure S3
const s3 = new AWS.S3();
const BUCKET_NAME = 'alexa-asl-test'; // Replace with your actual bucket name
const amplify_env = output.custom.ENV.amplify_env;
const apiUrl = output.custom.API[`GenASLAPI${amplify_env}`].endpoint;

// Converted getSignVideos method from TypeScript to JavaScript
const getSignVideos = async (input) => {
    console.log(apiUrl);
    console.log("Submitting input:", input);
    console.log(amplify_env);
    
    const initRequest = async (input) => {
        const params = new URLSearchParams(input);
        console.log("params", params);
        console.log(`${apiUrl}audio-to-sign?${params}`);
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

    const checkRequest = async (sfn_execution_arn) => {
        const params = new URLSearchParams({ sfn_execution_arn: sfn_execution_arn });

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
    const delayMs = 2000; // Delay in milliseconds (2 seconds)

    // Helper function to create a delay
    const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
    
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
            
            // Return the processed data instead of setState (since this is Lambda, not React)
            const result = {
                signVideo: data.SignURL,
                poseVideo: data.PoseURL,
                humanAvatarVideo: data.AvatarURL,
                blendedPoseVideo: data.PoseURL,
                gloss: data.Gloss,
                value: data.Text,
            };
            
            console.log("Sign URL:", data.SignURL);
            return result;
        }
    }
    
    // If we reach max attempts without completion
    throw new Error(`Process did not complete after ${maxAttempts} attempts`);
};
// Log user input function
function logUserInput(handlerInput) {
    const request = handlerInput.requestEnvelope.request;
    console.log('=== USER INPUT LOG ===');
    console.log('Request type:', request.type);
    if (request.type === 'IntentRequest') {
        console.log('Intent name:', request.intent.name);
        console.log('User utterance (approximate):', request.intent.name);
        if (request.intent.slots) {
            console.log('Slots:', JSON.stringify(request.intent.slots, null, 2));
        }
    }
    console.log('Timestamp:', request.timestamp);
    console.log('Locale:', request.locale);
}


const LaunchRequestHandler = {
    canHandle(handlerInput) {
        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'LaunchRequest';
    },
    handle(handlerInput) {
        logUserInput(handlerInput);
        console.log('=== LAUNCH REQUEST ===');
        
        const speakOutput = 'Welcome to ASL Translator, your guide to American Sign Language! I am here to help you translate sentences into ASL.';
        const response = handlerInput.responseBuilder
            .speak(speakOutput)
            .reprompt(speakOutput)
            .getResponse();
        console.log('LAUNCH REQUEST Response:', JSON.stringify(response, null, 2));
        return response
    }
};

const HelloWorldIntentHandler = {
    canHandle(handlerInput) {
        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest'
            && Alexa.getIntentName(handlerInput.requestEnvelope) === 'HelloWorldIntent';
    },
    handle(handlerInput) {
        console.log('=== HELLO WORLD INTENT ===');
        console.log('User said:', handlerInput.requestEnvelope.request.intent.name);
        console.log('Raw input text:', handlerInput.requestEnvelope.request.intent);
        console.log('Full request:', JSON.stringify(handlerInput.requestEnvelope, null, 2));
        
        const speakOutput = 'I am ASL Translator, your guide to American Sign Language! I am here to help you translate sentences into ASL.';
        
        return handlerInput.responseBuilder
            .speak(speakOutput)
            .getResponse();
    }
};

const WebcamIntentHandler = {
    canHandle(handlerInput) {
        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest'
            && Alexa.getIntentName(handlerInput.requestEnvelope) === 'WebcamIntent';
    },
    handle(handlerInput) {
        try {
            const VIDEO_KEY = 'demo/Iamfine.mp4'; // Replace with your actual file path
            console.log('=== THANKS INTENT TRIGGERED ===');
            console.log('Intent name:', handlerInput.requestEnvelope.request.intent.name);
            console.log('Device ID:', handlerInput.requestEnvelope.context.System.device.deviceId);
            console.log('Device supported interfaces:', JSON.stringify(handlerInput.requestEnvelope.context.System.device.supportedInterfaces, null, 2));
            console.log('Full request envelope:', JSON.stringify(handlerInput.requestEnvelope, null, 2));
            
            const supportedInterfaces = Alexa.getSupportedInterfaces(handlerInput.requestEnvelope);
            console.log('Device interfaces:', JSON.stringify(supportedInterfaces, null, 2));
            
            // Generate S3 signed URL with proper parameters
            const signedUrl = s3.getSignedUrl('getObject', {
                Bucket: BUCKET_NAME,
                Key: VIDEO_KEY,
                Expires: 3600,
                ResponseContentType: 'video/mp4'
            });
            
            console.log('Generated S3 URL:', signedUrl);
            
            // Check device capabilities - FIXED for Echo Show 8
            const hasVideoApp = supportedInterfaces.VideoApp;
            const hasAPL = supportedInterfaces['Alexa.Presentation.APL'];
            const hasViewport = handlerInput.requestEnvelope.context.Viewport;
            
            // Echo Show 8 often reports empty supportedInterfaces, so check for Viewport as fallback
            const isEchoShow = hasViewport || hasAPL || Object.keys(supportedInterfaces).length === 0;
            
            console.log('Has VideoApp interface:', !!hasVideoApp);
            console.log('Has APL interface:', !!hasAPL);
            console.log('Has Viewport context:', !!hasViewport);
            console.log('Detected as Echo Show (fallback):', isEchoShow);
            
            // Fire TV devices - use VideoApp.Launch
            if (hasVideoApp) {
                console.log('SUCCESS: Using VideoApp.Launch for Fire TV');
                
                const response = handlerInput.responseBuilder
                    .speak('Translate I am fine thanks how are you')
                    .addDirective({
                        type: 'VideoApp.Launch',
                        videoItem: {
                            source: signedUrl,
                            metadata: {
                                title: 'Apple Video',
                                subtitle: 'Apple sign language video'
                            }
                        }
                    })
                    .getResponse();
                    
                console.log('VideoApp response:', JSON.stringify(response, null, 2));
                return response;
            }
            // Echo Show devices - use APL Video
            else if (isEchoShow) {
                console.log('SUCCESS: Using APL Video for Echo Show (detected via fallback logic)');
                
                // APL Video test
                const response = handlerInput.responseBuilder
                    .speak('<speak>Translate I am fine thanks how are you<break time="2s"/></speak>')
                    .addDirective({
                        type: 'Alexa.Presentation.APL.RenderDocument',
                        token: 'videoToken',
                        document: {
                            type: 'APL',
                            version: '1.8',
                            mainTemplate: {
                                items: [{
                                    type: 'Video',
                                    id: 'videoPlayer',
                                    width: '60vw',
                                    height: '80vh',
                                    source: signedUrl,
                                    autoplay: false,
                                    scale: 'best-fill',
                                    audioTrack: 'foreground'
                                }]
                            }
                        }
                    })
                    .addDirective({
                        type: 'Alexa.Presentation.APL.ExecuteCommands',
                        token: 'videoToken',
                        commands: [{
                            type: 'Sequential',
                            commands: [
                                {
                                    type: 'Idle',
                                    delay: 1000
                                },
                                {
                                    type: 'ControlMedia',
                                    componentId: 'videoPlayer',
                                    command: 'play'
                                }
                            ]
                        }]
                    })
                    .getResponse();
                    
                    
                console.log('Simple APL Video response:', JSON.stringify(response, null, 2));
                return response;
                
            }
            // No video support
            else {
                console.log('FAIL: No video support detected');
                return handlerInput.responseBuilder
                    .speak('Apple video is available on devices with screens like Echo Show or Fire TV')
                    .getResponse();
            }
        } catch (error) {
            console.error('THANKS INTENT ERROR:', error);
            console.error('Error stack:', error.stack);
            return handlerInput.responseBuilder
                .speak('Sorry, I cannot play the apple video right now')
                .getResponse();
        }
    }
};

const HelpResponseIntentHandler = {
    canHandle(handlerInput) {
        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest'
            && Alexa.getIntentName(handlerInput.requestEnvelope) === 'HelpResponseIntent';
    },
    handle(handlerInput) {
        try {
            const VIDEO_KEY = 'demo/help.mp4'; // Replace with your actual file path
            console.log('=== HELP INTENT TRIGGERED ===');
            console.log('Intent name:', handlerInput.requestEnvelope.request.intent.name);
            console.log('Device ID:', handlerInput.requestEnvelope.context.System.device.deviceId);
            console.log('Device supported interfaces:', JSON.stringify(handlerInput.requestEnvelope.context.System.device.supportedInterfaces, null, 2));
            console.log('Full request envelope:', JSON.stringify(handlerInput.requestEnvelope, null, 2));
            
            const supportedInterfaces = Alexa.getSupportedInterfaces(handlerInput.requestEnvelope);
            console.log('Device interfaces:', JSON.stringify(supportedInterfaces, null, 2));
            
            // Generate S3 signed URL with proper parameters
            const signedUrl = s3.getSignedUrl('getObject', {
                Bucket: BUCKET_NAME,
                Key: VIDEO_KEY,
                Expires: 3600,
                ResponseContentType: 'video/mp4'
            });
            
            console.log('Generated S3 URL:', signedUrl);
            
            // Check device capabilities - FIXED for Echo Show 8
            const hasVideoApp = supportedInterfaces.VideoApp;
            const hasAPL = supportedInterfaces['Alexa.Presentation.APL'];
            const hasViewport = handlerInput.requestEnvelope.context.Viewport;
            
            // Echo Show 8 often reports empty supportedInterfaces, so check for Viewport as fallback
            const isEchoShow = hasViewport || hasAPL || Object.keys(supportedInterfaces).length === 0;
            
            console.log('Has VideoApp interface:', !!hasVideoApp);
            console.log('Has APL interface:', !!hasAPL);
            console.log('Has Viewport context:', !!hasViewport);
            console.log('Detected as Echo Show (fallback):', isEchoShow);
            
            // Fire TV devices - use VideoApp.Launch
            if (hasVideoApp) {
                console.log('SUCCESS: Using VideoApp.Launch for Fire TV');
                
                const response = handlerInput.responseBuilder
                    .speak('Translate How may help you today')
                    .addDirective({
                        type: 'VideoApp.Launch',
                        videoItem: {
                            source: signedUrl,
                            metadata: {
                                title: 'Apple Video',
                                subtitle: 'Apple sign language video'
                            }
                        }
                    })
                    .getResponse();
                    
                console.log('VideoApp response:', JSON.stringify(response, null, 2));
                return response;
            }
            // Echo Show devices - use APL Video
            else if (isEchoShow) {
                console.log('SUCCESS: Using APL Video for Echo Show (detected via fallback logic)');
                
                // APL Video test
                const response = handlerInput.responseBuilder
                    .speak('<speak>Translate How may help you today<break time="2s"/></speak>')
                    .addDirective({
                        type: 'Alexa.Presentation.APL.RenderDocument',
                        token: 'videoToken',
                        document: {
                            type: 'APL',
                            version: '1.8',
                            mainTemplate: {
                                items: [{
                                    type: 'Video',
                                    id: 'videoPlayer',
                                    width: '60vw',
                                    height: '80vh',
                                    source: signedUrl,
                                    autoplay: false,
                                    scale: 'best-fill',
                                    audioTrack: 'foreground'
                                }]
                            }
                        }
                    })
                    .addDirective({
                        type: 'Alexa.Presentation.APL.ExecuteCommands',
                        token: 'videoToken',
                        commands: [{
                            type: 'Sequential',
                            commands: [
                                {
                                    type: 'Idle',
                                    delay: 1000
                                },
                                {
                                    type: 'ControlMedia',
                                    componentId: 'videoPlayer',
                                    command: 'play'
                                }
                            ]
                        }]
                    })
                    .getResponse();
                    
                    
                console.log('Simple APL Video response:', JSON.stringify(response, null, 2));
                return response;
                
            }
            // No video support
            else {
                console.log('FAIL: No video support detected');
                return handlerInput.responseBuilder
                    .speak('Video is available on devices with screens like Echo Show or Fire TV')
                    .getResponse();
            }
        } catch (error) {
            console.error('HELP INTENT ERROR:', error);
            console.error('Error stack:', error.stack);
            return handlerInput.responseBuilder
                .speak('Sorry, I cannot play the video right now')
                .getResponse();
        }
    }
};

const ColorsIntentHandler = {
    canHandle(handlerInput) {
        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest'
            && Alexa.getIntentName(handlerInput.requestEnvelope) === 'ColorsIntent';
    },
    handle(handlerInput) {
        try {
            const VIDEO_KEY = 'demo/colors.mp4'; // Replace with your actual file path
            console.log('=== COLORS INTENT TRIGGERED ===');
            console.log('Intent name:', handlerInput.requestEnvelope.request.intent.name);
            console.log('Device ID:', handlerInput.requestEnvelope.context.System.device.deviceId);
            console.log('Device supported interfaces:', JSON.stringify(handlerInput.requestEnvelope.context.System.device.supportedInterfaces, null, 2));
            console.log('Full request envelope:', JSON.stringify(handlerInput.requestEnvelope, null, 2));
            
            const supportedInterfaces = Alexa.getSupportedInterfaces(handlerInput.requestEnvelope);
            console.log('Device interfaces:', JSON.stringify(supportedInterfaces, null, 2));
            
            // Generate S3 signed URL with proper parameters
            const signedUrl = s3.getSignedUrl('getObject', {
                Bucket: BUCKET_NAME,
                Key: VIDEO_KEY,
                Expires: 3600,
                ResponseContentType: 'video/mp4'
            });
            
            console.log('Generated S3 URL:', signedUrl);
            
            // Check device capabilities - FIXED for Echo Show 8
            const hasVideoApp = supportedInterfaces.VideoApp;
            const hasAPL = supportedInterfaces['Alexa.Presentation.APL'];
            const hasViewport = handlerInput.requestEnvelope.context.Viewport;
            
            // Echo Show 8 often reports empty supportedInterfaces, so check for Viewport as fallback
            const isEchoShow = hasViewport || hasAPL || Object.keys(supportedInterfaces).length === 0;
            
            console.log('Has VideoApp interface:', !!hasVideoApp);
            console.log('Has APL interface:', !!hasAPL);
            console.log('Has Viewport context:', !!hasViewport);
            console.log('Detected as Echo Show (fallback):', isEchoShow);
            
            // Fire TV devices - use VideoApp.Launch
            if (hasVideoApp) {
                console.log('SUCCESS: Using VideoApp.Launch for Fire TV');
                
                const response = handlerInput.responseBuilder
                    .speak('Translate Can you teach me signs for colors')
                    .addDirective({
                        type: 'VideoApp.Launch',
                        videoItem: {
                            source: signedUrl,
                            metadata: {
                                title: 'Apple Video',
                                subtitle: 'Apple sign language video'
                            }
                        }
                    })
                    .getResponse();
                    
                console.log('VideoApp response:', JSON.stringify(response, null, 2));
                return response;
            }
            // Echo Show devices - use APL Video
            else if (isEchoShow) {
                console.log('SUCCESS: Using APL Video for Echo Show (detected via fallback logic)');
                
                // APL Video test
                const response = handlerInput.responseBuilder
                    .speak('<speak>Translate Can you teach me signs for colors<break time="2s"/></speak>')
                    .addDirective({
                        type: 'Alexa.Presentation.APL.RenderDocument',
                        token: 'videoToken',
                        document: {
                            type: 'APL',
                            version: '1.8',
                            mainTemplate: {
                                items: [{
                                    type: 'Video',
                                    id: 'videoPlayer',
                                    width: '60vw',
                                    height: '80vh',
                                    source: signedUrl,
                                    autoplay: false,
                                    scale: 'best-fill',
                                    audioTrack: 'foreground'
                                }]
                            }
                        }
                    })
                    .addDirective({
                        type: 'Alexa.Presentation.APL.ExecuteCommands',
                        token: 'videoToken',
                        commands: [{
                            type: 'Sequential',
                            commands: [
                                {
                                    type: 'Idle',
                                    delay: 1000
                                },
                                {
                                    type: 'ControlMedia',
                                    componentId: 'videoPlayer',
                                    command: 'play'
                                }
                            ]
                        }]
                    })
                    .getResponse();
                    
                    
                console.log('Simple APL Video response:', JSON.stringify(response, null, 2));
                return response;
                
            }
            // No video support
            else {
                console.log('FAIL: No video support detected');
                return handlerInput.responseBuilder
                    .speak('Video is available on devices with screens like Echo Show or Fire TV')
                    .getResponse();
            }
        } catch (error) {
            console.error('COLORS ERROR:', error);
            console.error('Error stack:', error.stack);
            return handlerInput.responseBuilder
                .speak('Sorry, I cannot play the video right now')
                .getResponse();
        }
    }
};

const BlueColorIntentHandler = {
    canHandle(handlerInput) {
        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest'
            && Alexa.getIntentName(handlerInput.requestEnvelope) === 'BlueColorIntent';
    },
    handle(handlerInput) {
        try {
            const VIDEO_KEY = 'demo/blue.mp4'; // Replace with your actual file path
            console.log('=== BLUE COLOR INTENT TRIGGERED ===');
            console.log('Intent name:', handlerInput.requestEnvelope.request.intent.name);
            console.log('Device ID:', handlerInput.requestEnvelope.context.System.device.deviceId);
            console.log('Device supported interfaces:', JSON.stringify(handlerInput.requestEnvelope.context.System.device.supportedInterfaces, null, 2));
            console.log('Full request envelope:', JSON.stringify(handlerInput.requestEnvelope, null, 2));
            
            const supportedInterfaces = Alexa.getSupportedInterfaces(handlerInput.requestEnvelope);
            console.log('Device interfaces:', JSON.stringify(supportedInterfaces, null, 2));
            
            // Generate S3 signed URL with proper parameters
            const signedUrl = s3.getSignedUrl('getObject', {
                Bucket: BUCKET_NAME,
                Key: VIDEO_KEY,
                Expires: 3600,
                ResponseContentType: 'video/mp4'
            });
            
            console.log('Generated S3 URL:', signedUrl);
            
            // Check device capabilities - FIXED for Echo Show 8
            const hasVideoApp = supportedInterfaces.VideoApp;
            const hasAPL = supportedInterfaces['Alexa.Presentation.APL'];
            const hasViewport = handlerInput.requestEnvelope.context.Viewport;
            
            // Echo Show 8 often reports empty supportedInterfaces, so check for Viewport as fallback
            const isEchoShow = hasViewport || hasAPL || Object.keys(supportedInterfaces).length === 0;
            
            console.log('Has VideoApp interface:', !!hasVideoApp);
            console.log('Has APL interface:', !!hasAPL);
            console.log('Has Viewport context:', !!hasViewport);
            console.log('Detected as Echo Show (fallback):', isEchoShow);
            
            // Fire TV devices - use VideoApp.Launch
            if (hasVideoApp) {
                console.log('SUCCESS: Using VideoApp.Launch for Fire TV');
                
                const response = handlerInput.responseBuilder
                    .speak('Translate YES, PRACTICE SIGN BLUE')
                    .addDirective({
                        type: 'VideoApp.Launch',
                        videoItem: {
                            source: signedUrl,
                            metadata: {
                                title: 'Apple Video',
                                subtitle: 'Apple sign language video'
                            }
                        }
                    })
                    .getResponse();
                    
                console.log('VideoApp response:', JSON.stringify(response, null, 2));
                return response;
            }
            // Echo Show devices - use APL Video
            else if (isEchoShow) {
                console.log('SUCCESS: Using APL Video for Echo Show (detected via fallback logic)');
                
                // APL Video test
                const response = handlerInput.responseBuilder
                    .speak('<speak>Translate YES, PRACTICE SIGN BLUE<break time="2s"/></speak>')
                    .addDirective({
                        type: 'Alexa.Presentation.APL.RenderDocument',
                        token: 'videoToken',
                        document: {
                            type: 'APL',
                            version: '1.8',
                            mainTemplate: {
                                items: [{
                                    type: 'Video',
                                    id: 'videoPlayer',
                                    width: '60vw',
                                    height: '80vh',
                                    source: signedUrl,
                                    autoplay: false,
                                    scale: 'best-fill',
                                    audioTrack: 'foreground'
                                }]
                            }
                        }
                    })
                    .addDirective({
                        type: 'Alexa.Presentation.APL.ExecuteCommands',
                        token: 'videoToken',
                        commands: [{
                            type: 'Sequential',
                            commands: [
                                {
                                    type: 'Idle',
                                    delay: 1000
                                },
                                {
                                    type: 'ControlMedia',
                                    componentId: 'videoPlayer',
                                    command: 'play'
                                }
                            ]
                        }]
                    })
                    .getResponse();
                    
                    
                console.log('Simple APL Video response:', JSON.stringify(response, null, 2));
                return response;
                
            }
            // No video support
            else {
                console.log('FAIL: No video support detected');
                return handlerInput.responseBuilder
                    .speak('Video is available on devices with screens like Echo Show or Fire TV')
                    .getResponse();
            }
        } catch (error) {
            console.error('BLUE COLORS ERROR:', error);
            console.error('Error stack:', error.stack);
            return handlerInput.responseBuilder
                .speak('Sorry, I cannot play the video right now')
                .getResponse();
        }
    }
};

const TranslateIntentHandler = {
    canHandle(handlerInput) {
        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest'
            && Alexa.getIntentName(handlerInput.requestEnvelope) === 'TranslateIntent';
    },
    async handle(handlerInput) {
        try {
            const phrase = Alexa.getSlotValue(handlerInput.requestEnvelope, 'phrase');
            console.log('=== TRANSLATE INTENT ===');
            console.log('User phrase captured:', phrase);
            
            if (!phrase) {
                return handlerInput.responseBuilder
                    .speak('I didn\'t catch what you wanted to translate. Please try again.')
                    .reprompt('What would you like me to translate to sign language?')
                    .getResponse();
            }

            // Use the getSignVideos function to process the translation
            console.log('Calling getSignVideos with phrase:', phrase);
            const translationResult = await getSignVideos({ text: phrase });
            
            console.log('Translation result:', translationResult);
            
            // Check device capabilities
            const supportedInterfaces = Alexa.getSupportedInterfaces(handlerInput.requestEnvelope);
            const hasVideoApp = supportedInterfaces.VideoApp;
            const hasAPL = supportedInterfaces['Alexa.Presentation.APL'];
            const hasViewport = handlerInput.requestEnvelope.context.Viewport;
            const isEchoShow = hasViewport || hasAPL || Object.keys(supportedInterfaces).length === 0;
            
            if (translationResult && translationResult.humanAvatarVideo) {
                // Fire TV devices - use VideoApp.Launch
                if (hasVideoApp) {
                    console.log('SUCCESS: Using VideoApp.Launch for Fire TV');
                    
                    return handlerInput.responseBuilder
                        .speak(`Translating "${phrase}" to sign language`)
                        .addDirective({
                            type: 'VideoApp.Launch',
                            videoItem: {
                                source: translationResult.humanAvatarVideo,
                                metadata: {
                                    title: 'ASL Translation',
                                    subtitle: `Sign language for: ${phrase}`
                                }
                            }
                        })
                        .getResponse();
                }
                // Echo Show devices - use APL Video
                else if (isEchoShow) {
                    console.log('SUCCESS: Using APL Video for Echo Show');
                    
                    return handlerInput.responseBuilder
                        .speak(`<speak>Translating "${phrase}" to sign language<break time="1s"/></speak>`)
                        .addDirective({
                            type: 'Alexa.Presentation.APL.RenderDocument',
                            token: 'translationVideoToken',
                            document: {
                                type: 'APL',
                                version: '1.8',
                                mainTemplate: {
                                    items: [{
                                        type: 'Video',
                                        id: 'translationVideoPlayer',
                                        width: '60vw',
                                        height: '80vh',
                                        source: translationResult.humanAvatarVideo,
                                        autoplay: false,
                                        scale: 'best-fill',
                                        audioTrack: 'foreground'
                                    }]
                                }
                            }
                        })
                        .addDirective({
                            type: 'Alexa.Presentation.APL.ExecuteCommands',
                            token: 'translationVideoToken',
                            commands: [{
                                type: 'Sequential',
                                commands: [
                                    {
                                        type: 'Idle',
                                        delay: 1000
                                    },
                                    {
                                        type: 'ControlMedia',
                                        componentId: 'translationVideoPlayer',
                                        command: 'play'
                                    }
                                ]
                            }]
                        })
                        .getResponse();
                }
                // No video support
                else {
                    console.log('No video support detected');
                    return handlerInput.responseBuilder
                        .speak(`I've translated "${phrase}" to sign language, but video playback is only available on devices with screens like Echo Show or Fire TV. The gloss translation is: ${translationResult.gloss || 'not available'}`)
                        .getResponse();
                }
            } else {
                console.log('No translation result received');
                return handlerInput.responseBuilder
                    .speak(`I'm sorry, I couldn't generate a sign language translation for "${phrase}" right now. Please try again later.`)
                    .getResponse();
            }
            
        } catch (error) {
            console.error('TRANSLATE INTENT ERROR:', error);
            console.error('Error stack:', error.stack);
            return handlerInput.responseBuilder
                .speak('Sorry, I encountered an error while translating. Please try again.')
                .getResponse();
        }
    }
};

const NumbersIntentHandler = {
    canHandle(handlerInput) {
        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest'
            && Alexa.getIntentName(handlerInput.requestEnvelope) === 'NumbersIntent';
    },
    handle(handlerInput) {
        try {
            const VIDEO_KEY = 'demo/numbers.mp4'; // Replace with your actual file path
            console.log('=== NUMBERS INTENT TRIGGERED ===');
            console.log('Intent name:', handlerInput.requestEnvelope.request.intent.name);
            console.log('Device ID:', handlerInput.requestEnvelope.context.System.device.deviceId);
            console.log('Device supported interfaces:', JSON.stringify(handlerInput.requestEnvelope.context.System.device.supportedInterfaces, null, 2));
            console.log('Full request envelope:', JSON.stringify(handlerInput.requestEnvelope, null, 2));
            
            const supportedInterfaces = Alexa.getSupportedInterfaces(handlerInput.requestEnvelope);
            console.log('Device interfaces:', JSON.stringify(supportedInterfaces, null, 2));
            
            // Generate S3 signed URL with proper parameters
            const signedUrl = s3.getSignedUrl('getObject', {
                Bucket: BUCKET_NAME,
                Key: VIDEO_KEY,
                Expires: 3600,
                ResponseContentType: 'video/mp4'
            });
            
            console.log('Generated S3 URL:', signedUrl);
            
            // Check device capabilities - FIXED for Echo Show 8
            const hasVideoApp = supportedInterfaces.VideoApp;
            const hasAPL = supportedInterfaces['Alexa.Presentation.APL'];
            const hasViewport = handlerInput.requestEnvelope.context.Viewport;
            
            // Echo Show 8 often reports empty supportedInterfaces, so check for Viewport as fallback
            const isEchoShow = hasViewport || hasAPL || Object.keys(supportedInterfaces).length === 0;
            
            console.log('Has VideoApp interface:', !!hasVideoApp);
            console.log('Has APL interface:', !!hasAPL);
            console.log('Has Viewport context:', !!hasViewport);
            console.log('Detected as Echo Show (fallback):', isEchoShow);
            
            // Fire TV devices - use VideoApp.Launch
            if (hasVideoApp) {
                console.log('SUCCESS: Using VideoApp.Launch for Fire TV');
                
                const response = handlerInput.responseBuilder
                    .speak('Translate can you teach me numbers one to five')
                    .addDirective({
                        type: 'VideoApp.Launch',
                        videoItem: {
                            source: signedUrl,
                            metadata: {
                                title: 'Apple Video',
                                subtitle: 'Apple sign language video'
                            }
                        }
                    })
                    .getResponse();
                    
                console.log('VideoApp response:', JSON.stringify(response, null, 2));
                return response;
            }
            // Echo Show devices - use APL Video
            else if (isEchoShow) {
                console.log('SUCCESS: Using APL Video for Echo Show (detected via fallback logic)');
                
                // APL Video test
                const response = handlerInput.responseBuilder
                    .speak('<speak>Translate can you teach me numbers one to five<break time="2s"/></speak>')
                    .addDirective({
                        type: 'Alexa.Presentation.APL.RenderDocument',
                        token: 'videoToken',
                        document: {
                            type: 'APL',
                            version: '1.8',
                            mainTemplate: {
                                items: [{
                                    type: 'Video',
                                    id: 'videoPlayer',
                                    width: '60vw',
                                    height: '80vh',
                                    source: signedUrl,
                                    autoplay: false,
                                    scale: 'best-fill',
                                    audioTrack: 'foreground'
                                }]
                            }
                        }
                    })
                    .addDirective({
                        type: 'Alexa.Presentation.APL.ExecuteCommands',
                        token: 'videoToken',
                        commands: [{
                            type: 'Sequential',
                            commands: [
                                {
                                    type: 'Idle',
                                    delay: 1000
                                },
                                {
                                    type: 'ControlMedia',
                                    componentId: 'videoPlayer',
                                    command: 'play'
                                }
                            ]
                        }]
                    })
                    .getResponse();
                    
                    
                console.log('Simple APL Video response:', JSON.stringify(response, null, 2));
                return response;
                
            }
            // No video support
            else {
                console.log('FAIL: No video support detected');
                return handlerInput.responseBuilder
                    .speak('Video is available on devices with screens like Echo Show or Fire TV')
                    .getResponse();
            }
        } catch (error) {
            console.error('NUMBERS ERROR:', error);
            console.error('Error stack:', error.stack);
            return handlerInput.responseBuilder
                .speak('Sorry, I cannot play the video right now')
                .getResponse();
        }
    }
};

const AppleIntentHandler = {
    canHandle(handlerInput) {
        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest'
            && Alexa.getIntentName(handlerInput.requestEnvelope) === 'AppleIntent';
    },
    async handle(handlerInput) {
        try {
            const VIDEO_KEY = 'demo/GAhowareyou.mp4'; // Replace with your actual file path
            console.log('=== HOW ARE YOU INTENT TRIGGERED ===');
            console.log('Intent name:', handlerInput.requestEnvelope.request.intent.name);
            console.log('Device ID:', handlerInput.requestEnvelope.context.System.device.deviceId);
            console.log('Device supported interfaces:', JSON.stringify(handlerInput.requestEnvelope.context.System.device.supportedInterfaces, null, 2));
            console.log('Full request envelope:', JSON.stringify(handlerInput.requestEnvelope, null, 2));
            
            const supportedInterfaces = Alexa.getSupportedInterfaces(handlerInput.requestEnvelope);
            console.log('Device interfaces:', JSON.stringify(supportedInterfaces, null, 2));
            
            // Generate S3 signed URL with proper parameters
            const signedUrl = s3.getSignedUrl('getObject', {
                Bucket: BUCKET_NAME,
                Key: VIDEO_KEY,
                Expires: 3600,
                ResponseContentType: 'video/mp4'
            });
            
            console.log('Generated S3 URL:', signedUrl);
            
            // Check device capabilities - FIXED for Echo Show 8
            const hasVideoApp = supportedInterfaces.VideoApp;
            const hasAPL = supportedInterfaces['Alexa.Presentation.APL'];
            const hasViewport = handlerInput.requestEnvelope.context.Viewport;
            
            // Echo Show 8 often reports empty supportedInterfaces, so check for Viewport as fallback
            const isEchoShow = hasViewport || hasAPL || Object.keys(supportedInterfaces).length === 0;
            
            console.log('Has VideoApp interface:', !!hasVideoApp);
            console.log('Has APL interface:', !!hasAPL);
            console.log('Has Viewport context:', !!hasViewport);
            console.log('Detected as Echo Show (fallback):', isEchoShow);
            
            // Fire TV devices - use VideoApp.Launch
            if (hasVideoApp) {
                console.log('SUCCESS: Using VideoApp.Launch for Fire TV');
                
                const response = handlerInput.responseBuilder
                    .speak('Translate good afternoon how are you')
                    .addDirective({
                        type: 'VideoApp.Launch',
                        videoItem: {
                            source: signedUrl,
                            metadata: {
                                title: 'Apple Video',
                                subtitle: 'Apple sign language video'
                            }
                        }
                    })
                    .getResponse();
                    
                console.log('VideoApp response:', JSON.stringify(response, null, 2));
                return response;
            }
            // Echo Show devices - use APL Video
            else if (isEchoShow) {
                console.log('SUCCESS: Using APL Video for Echo Show (detected via fallback logic)');
                
                // APL Video with speech delay
                const response = handlerInput.responseBuilder
                    .speak('<speak>Translate good afternoon how are you <break time="1s"/></speak>')
                    .addDirective({
                        type: 'Alexa.Presentation.APL.RenderDocument',
                        token: 'videoToken',
                        document: {
                            type: 'APL',
                            version: '1.8',
                            mainTemplate: {
                                items: [{
                                    type: 'Video',
                                    id: 'videoPlayer',
                                    width: '60vw',
                                    height: '80vh',
                                    source: signedUrl,
                                    autoplay: false,
                                    scale: 'best-fill',
                                    audioTrack: 'foreground'
                                }]
                            }
                        }
                    })
                    .addDirective({
                        type: 'Alexa.Presentation.APL.ExecuteCommands',
                        token: 'videoToken',
                        commands: [{
                            type: 'Sequential',
                            commands: [
                                {
                                    type: 'Idle',
                                    delay: 1000
                                },
                                {
                                    type: 'ControlMedia',
                                    componentId: 'videoPlayer',
                                    command: 'play'
                                }
                            ]
                        }]
                    })
                    .getResponse();
                    
                    
                console.log('Simple APL Video response:', JSON.stringify(response, null, 2));
                return response;
                
                // ORIGINAL COMPLEX VERSION (commented out for testing)
                // const response = handlerInput.responseBuilder
                //                 .speak('Playing apple video')
                //                 .addDirective({
                //                     type: 'Alexa.Presentation.APL.RenderDocument',
                //                     token: "documentToken",
                //                     document: require('./apl/video'), 
                //                     datasources: {
                //                         "payload": {
                //                                 "data": {
                //                                     "properties": {
                //                                         "videoURL": signedUrl
                //                                     }
                //                             }
                //                         }
                //                     }
                //                 })
                //                 .addDirective({
                //                         "type": "Alexa.Presentation.APL.ExecuteCommands",
                //                         "token": "documentToken",
                //                         "commands": [
                //                             {  
                //                                         "type": "ControlMedia",
                //                                         "componentId": "videoPlayerId",
                //                                         "command": "play"
                //                                     }
                //                 ]
                //             })
                //             .getResponse()
            }
            // No video support
            else {
                console.log('FAIL: No video support detected');
                return handlerInput.responseBuilder
                    .speak('Apple video is available on devices with screens like Echo Show or Fire TV')
                    .getResponse();
            }
        } catch (error) {
            console.error('APPLE INTENT ERROR:', error);
            console.error('Error stack:', error.stack);
            return handlerInput.responseBuilder
                .speak('Sorry, I cannot play the apple video right now')
                .getResponse();
        }
    }
};

const ShowVideoIntentHandler = {
    canHandle(handlerInput) {
        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest'
            && Alexa.getIntentName(handlerInput.requestEnvelope) === 'ShowVideoIntent';
    },
    async handle(handlerInput) {
        try {
            console.log('ShowVideoIntentHandler - Full request:', JSON.stringify(handlerInput.requestEnvelope, null, 2));
            
            const videoName = Alexa.getSlotValue(handlerInput.requestEnvelope, 'videoName');
            console.log('Video name requested:', videoName);
            
            const supportedInterfaces = Alexa.getSupportedInterfaces(handlerInput.requestEnvelope);
            console.log('Device supported interfaces:', JSON.stringify(supportedInterfaces, null, 2));
            
            if (videoName && (videoName.toLowerCase() === 'apple' || videoName.toLowerCase() === 'fruit')) {
                const signedUrl = s3.getSignedUrl('getObject', {
                    Bucket: BUCKET_NAME,
                    Key: VIDEO_KEY,
                    Expires: 3600
                });
                
                console.log('Generated S3 URL:', signedUrl);
                
                const supportsVideo = supportedInterfaces.VideoApp;
                console.log('VideoApp support:', supportsVideo);
                
                if (supportsVideo) {
                    const response = handlerInput.responseBuilder
                        .speak('Here is your apple video!')
                        .addVideoAppLaunchDirective(signedUrl, 'Apple Video', 'Watch this apple video')
                        .getResponse();
                    
                    console.log('Video response:', JSON.stringify(response, null, 2));
                    return response;
                } else {
                    console.log('No video support - providing audio response');
                    return handlerInput.responseBuilder
                        .speak('Here is information about apples. Apples are nutritious fruits that come in many varieties. This content is best viewed on a device with a screen.')
                        .getResponse();
                }
            } else {
                console.log('Invalid video name or no video name provided');
                return handlerInput.responseBuilder
                    .speak('I can only show you apple videos right now. Try saying show me apple.')
                    .reprompt('Say show me apple to see the video.')
                    .getResponse();
            }
        } catch (error) {
            console.error('ShowVideoIntentHandler error:', error);
            console.error('Error stack:', error.stack);
            return handlerInput.responseBuilder
                .speak('Sorry, I had trouble accessing the video. Please try again later.')
                .getResponse();
        }
    }
};

const HelpIntentHandler = {
    canHandle(handlerInput) {
        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest'
            && Alexa.getIntentName(handlerInput.requestEnvelope) === 'AMAZON.HelpIntent';
    },
    handle(handlerInput) {
        const speakOutput = 'You can say hello to me or say show me apple to see a video! How can I help?';
        
        return handlerInput.responseBuilder
            .speak(speakOutput)
            .reprompt(speakOutput)
            .getResponse();
    }
};

const CancelAndStopIntentHandler = {
    canHandle(handlerInput) {
        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest'
            && (Alexa.getIntentName(handlerInput.requestEnvelope) === 'AMAZON.CancelIntent'
                || Alexa.getIntentName(handlerInput.requestEnvelope) === 'AMAZON.StopIntent');
    },
    handle(handlerInput) {
        logUserInput(handlerInput);
        console.log('=== CANCEL/STOP INTENT TRIGGERED ===');
        console.log('Intent name:', Alexa.getIntentName(handlerInput.requestEnvelope));
        
        const speakOutput = 'Goodbye! Thanks for using ASL translator';
        
        const response = handlerInput.responseBuilder
            .speak(speakOutput)
            .withShouldEndSession(true)
            .getResponse();
            
        console.log('Exit response:', JSON.stringify(response, null, 2));
        return response;
    }
};

const SessionEndedRequestHandler = {
    canHandle(handlerInput) {
        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'SessionEndedRequest';
    },
    handle(handlerInput) {
        return handlerInput.responseBuilder.getResponse();
    }
};

const ErrorHandler = {
    canHandle() {
        return true;
    },
    handle(handlerInput, error) {
        console.log('=== ERROR HANDLER ===');
        console.log('Error message:', error.message);
        console.log('Error stack:', error.stack);
        console.log('Request that caused error:', JSON.stringify(handlerInput.requestEnvelope, null, 2));
        
        const speakOutput = `Sorry, I had trouble doing what you asked. Please try again.`;
        
        return handlerInput.responseBuilder
            .speak(speakOutput)
            .reprompt(speakOutput)
            .getResponse();
    }
};

const LoggingRequestInterceptor = {
    process(handlerInput) {
        const request = handlerInput.requestEnvelope.request;
        console.log('=== USER INPUT INTERCEPTOR ===');
        console.log('Request type:', request.type);
        if (request.type === 'IntentRequest') {
            console.log('Intent triggered:', request.intent.name);
            console.log('User likely said something that matched:', request.intent.name);
        }
        console.log('Full request:', JSON.stringify(request, null, 2));
    }
};

exports.handler = Alexa.SkillBuilders.custom()
    .addRequestHandlers(
        LaunchRequestHandler,
        HelloWorldIntentHandler,
        AppleIntentHandler,
        WebcamIntentHandler,
        HelpResponseIntentHandler,
        ColorsIntentHandler,
        BlueColorIntentHandler,
        NumbersIntentHandler,
        TranslateIntentHandler,
        HelpIntentHandler,
        CancelAndStopIntentHandler,
        SessionEndedRequestHandler
    )
    .addRequestInterceptors(LoggingRequestInterceptor)
    .addErrorHandlers(ErrorHandler)
    .lambda();
