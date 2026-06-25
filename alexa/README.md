# Alexa ASL Translator Skill

An Alexa skill that translates spoken text into American Sign Language (ASL) videos, providing an interactive way to learn and communicate in sign language.

## Features

- **Dynamic ASL Translation**: Converts any spoken phrase into sign language videos
- **Pre-built ASL Lessons**: Includes demo videos for common phrases, colors, and numbers
- **Multi-Device Support**: Works on Echo Show, Fire TV, and audio-only devices
- **Real-time Video Generation**: Uses AWS Step Functions to generate custom ASL videos
- **Device-Aware Responses**: Automatically detects device capabilities and provides appropriate content

## Architecture

The skill integrates with a comprehensive ASL translation pipeline:
- **Text-to-Gloss Translation**: Converts English text to ASL gloss notation
- **Gloss-to-Pose Generation**: Creates 3D pose sequences from gloss
- **Video Rendering**: Generates sign language videos with human avatars
- **S3 Storage**: Securely stores and serves video content

## Prerequisites

1. **Amazon Developer Account**: Sign up at https://developer.amazon.com
2. **AWS Account**: Sign up at https://aws.amazon.com
3. **ASK CLI**: Install the Alexa Skills Kit CLI
4. **Node.js**: Version 18 or higher
5. **Amplify Backend**: Deployed ASL translation API and infrastructure

## Setup Instructions

### 1. Install ASK CLI
```bash
npm install -g ask-cli
```

### 2. Configure ASK CLI
```bash
ask configure
```
Follow the prompts to link your Amazon Developer and AWS accounts.

### 3. Configure API Settings
The skill automatically loads configuration from `alexa_outputs.json`:
```javascript
const amplify_env = output.custom.ENV.amplify_env;
const apiUrl = output.custom.API[`GenASLAPI${amplify_env}`].endpoint;
```

### 4. Install Dependencies
```bash
cd lambda
npm install
cd ..
```

### 5. Set Required Permissions
Your Lambda execution role needs:
- S3 read permissions for video storage
- API Gateway invoke permissions for the translation API

## Available Intents

### Core Translation
- **TranslateIntent**: `"translate hello world"` - Dynamically generates ASL video for any phrase
- **LaunchRequest**: `"open ASL translator"` - Welcome message and skill introduction

### Pre-built Lessons
- **WebcamIntent**: `"I am fine thanks how are you"` - Common greeting phrase
- **HelpResponseIntent**: `"how may I help you today"` - Assistance phrase
- **ColorsIntent**: `"teach me colors"` - Color signs lesson
- **BlueColorIntent**: `"practice sign blue"` - Specific color practice
- **NumbersIntent**: `"teach me numbers one to five"` - Number signs lesson
- **AppleIntent**: `"good afternoon how are you"` - Afternoon greeting

### Utility
- **HelpIntent**: `"help"` - Shows available commands
- **CancelAndStopIntent**: `"stop"` or `"cancel"` - Exits the skill

## Key Implementation Details

### Dynamic Translation Function

The `getSignVideos` function handles the complete translation pipeline:

```javascript
const getSignVideos = async (input) => {
    // 1. Submit translation request
    const initRequest = async (input) => {
        const params = new URLSearchParams(input);
        const response = await fetch(`${apiUrl}audio-to-sign?${params}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" }
        });
        return await response.text();
    };

    // 2. Poll for completion (up to 1000 attempts, 2-second intervals)
    let attempts = 0;
    const maxAttempts = 1000;
    const delayMs = 2000;
    
    while (attempts < maxAttempts) {
        await delay(delayMs);
        const rawResponse = await checkRequest(sfn_execution_arn);
        
        if (data.sfn_execution_arn) {
            // Still processing
            attempts++;
        } else {
            // Complete - return video URLs and metadata
            return {
                signVideo: data.SignURL,
                poseVideo: data.PoseURL,
                humanAvatarVideo: data.AvatarURL,
                blendedPoseVideo: data.PoseURL,
                gloss: data.Gloss,
                value: data.Text
            };
        }
    }
};
```

### Enhanced TranslateIntent Handler

The `TranslateIntentHandler` demonstrates full integration:

```javascript
const TranslateIntentHandler = {
    canHandle(handlerInput) {
        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest'
            && Alexa.getIntentName(handlerInput.requestEnvelope) === 'TranslateIntent';
    },
    async handle(handlerInput) {
        const phrase = Alexa.getSlotValue(handlerInput.requestEnvelope, 'phrase');
        
        // Generate ASL video
        const translationResult = await getSignVideos({ text: phrase });
        
        // Device capability detection
        const supportedInterfaces = Alexa.getSupportedInterfaces(handlerInput.requestEnvelope);
        const hasVideoApp = supportedInterfaces.VideoApp;
        const hasAPL = supportedInterfaces['Alexa.Presentation.APL'];
        const isEchoShow = hasViewport || hasAPL;
        
        if (hasVideoApp) {
            // Fire TV - use VideoApp.Launch
            return handlerInput.responseBuilder
                .speak(`Translating "${phrase}" to sign language`)
                .addDirective({
                    type: 'VideoApp.Launch',
                    videoItem: {
                        source: translationResult.signVideo,
                        metadata: {
                            title: 'ASL Translation',
                            subtitle: `Sign language for: ${phrase}`
                        }
                    }
                })
                .getResponse();
        } else if (isEchoShow) {
            // Echo Show - use APL Video
            return handlerInput.responseBuilder
                .speak(`Translating "${phrase}" to sign language`)
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
                                source: translationResult.signVideo,
                                autoplay: false
                            }]
                        }
                    }
                })
                .getResponse();
        } else {
            // Audio-only devices - provide gloss translation
            return handlerInput.responseBuilder
                .speak(`The gloss translation is: ${translationResult.gloss}`)
                .getResponse();
        }
    }
};
```

## Deployment

### Deploy the skill
```bash
ask deploy
```

This command will:
- Create the skill in your developer console
- Deploy the Lambda function to AWS
- Configure the interaction model with all intents
- Set up video interface support for compatible devices

## Testing

### Test Commands

**Dynamic Translation:**
- "Alexa, open ASL translator"
- "translate hello world"
- "translate I love you"
- "translate what is your name"

**Pre-built Lessons:**
- "I am fine thanks how are you"
- "teach me colors"
- "practice sign blue"
- "teach me numbers one to five"
- "good afternoon how are you"

**Utility:**
- "help" - Shows available commands
- "stop" - Exits the skill

### Device-Specific Behavior

- **Echo Show/Fire TV**: Displays full ASL videos with automatic playback
- **Echo Dot/Audio devices**: Provides gloss translations and audio descriptions
- **Tablets/Phones**: Uses APL video rendering for optimal display

## Project Structure

```
alexa/
├── skill-package/
│   ├── skill.json                    # Skill manifest
│   └── interactionModels/
│       └── custom/
│           └── en-US.json           # Interaction model with all intents
├── lambda/
│   ├── index.js                     # Lambda function with getSignVideos
│   ├── package.json                 # Dependencies
│   ├── alexa_outputs.json          # API configuration
│   └── apl/
│       └── video.json              # APL video template
├── ask-resources.json              # ASK CLI configuration
└── README.md
```

## API Integration

The skill integrates with the GenASL API pipeline:

1. **Text Input**: User speaks a phrase to translate
2. **API Request**: Sends text to `audio-to-sign` endpoint
3. **Step Function**: Initiates ASL translation workflow
4. **Polling**: Checks status every 2 seconds (max 1000 attempts)
5. **Video Generation**: Creates sign language video with human avatar
6. **Response**: Returns video URLs and gloss translation
7. **Playback**: Displays video on compatible Alexa devices

### API Endpoints Used

- `POST /audio-to-sign` - Initiates translation process
- Query parameters: `text`, `sfn_execution_arn` (for status checks)
- Response: Step Function execution ARN or completed translation data

## Error Handling

The skill includes comprehensive error handling:

- **API Timeouts**: Graceful fallback after maximum polling attempts
- **Device Compatibility**: Automatic detection and appropriate responses
- **Network Issues**: Retry logic and user-friendly error messages
- **Invalid Input**: Validation and re-prompting for missing phrases

## Enhancing Your Skill

### Adding New Pre-built Lessons

1. **Create Intent Handler**:
```javascript
const NewLessonIntentHandler = {
    canHandle(handlerInput) {
        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest'
            && Alexa.getIntentName(handlerInput.requestEnvelope) === 'NewLessonIntent';
    },
    async handle(handlerInput) {
        const VIDEO_KEY = 'demo/new-lesson.mp4';
        // Use existing video playback logic
    }
};
```

2. **Update Interaction Model** (`skill-package/interactionModels/custom/en-US.json`):
```json
{
  "name": "NewLessonIntent",
  "samples": [
    "teach me greetings",
    "show me greeting signs"
  ]
}
```

### Adding Custom Slots for Translation

```json
{
  "name": "TranslateIntent",
  "slots": [
    {
      "name": "phrase",
      "type": "AMAZON.SearchQuery"
    }
  ],
  "samples": [
    "translate {phrase}",
    "show me how to sign {phrase}",
    "convert {phrase} to sign language"
  ]
}
```

## Performance Considerations

- **Video Generation**: Can take 30-60 seconds for complex phrases
- **Caching**: Consider implementing result caching for common phrases
- **Timeout Handling**: Maximum 1000 polling attempts (33+ minutes)
- **Device Memory**: Large video files may impact older Echo Show devices

## Monitoring and Debugging

### CloudWatch Logs
Monitor Lambda execution and API calls:
```bash
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/ask-"
```

### Key Log Messages
- `Submitting input:` - Translation request initiated
- `Process not complete, polling...` - Step Function still running
- `Process complete, existing...` - Translation finished
- `Translation result:` - Final video URLs and metadata

## Security Considerations

- **S3 Signed URLs**: Videos use temporary signed URLs (1-hour expiration)
- **API Authentication**: Ensure proper IAM roles for Lambda execution
- **Input Validation**: Sanitize user input before API calls
- **Rate Limiting**: Consider implementing request throttling for production

## Next Steps

1. **Add More Lessons**: Expand pre-built vocabulary (family, food, emotions)
2. **Implement Caching**: Store common translations to reduce API calls
3. **Add Progress Tracking**: Remember user's learning progress
4. **Multi-language Support**: Extend to other sign languages (BSL, ASL variants)
5. **Interactive Quizzes**: Test user's sign language recognition
6. **Publish to Store**: Submit for Alexa Skills Store certification

## Resources

- [Alexa Skills Kit Documentation](https://developer.amazon.com/docs/ask-overviews/build-skills-with-the-alexa-skills-kit.html)
- [ASK SDK for Node.js](https://github.com/alexa/alexa-skills-kit-sdk-for-nodejs)
- [APL Video Documentation](https://developer.amazon.com/docs/alexa-presentation-language/apl-video.html)
- [Alexa Developer Console](https://developer.amazon.com/alexa/console/ask)
- [AWS Step Functions](https://docs.aws.amazon.com/step-functions/)
- [CloudWatch Logs Console](https://console.aws.amazon.com/cloudwatch/home#logs:)
