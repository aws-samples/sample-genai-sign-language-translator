import json
import os
import boto3
from botocore.exceptions import BotoCoreError, ClientError
import base64

polly = boto3.client('polly')
s3 = boto3.client('s3')

asl_data_bucket = os.environ['ASL_DATA_BUCKET']


def lambda_handler(event, context):
    try:
        # Parse the input
        body = json.loads(event['body'])
        text = body.get('text')
        voice_id = body.get('voiceId', 'Joanna')
        print(event)
        print(text)

        if not text:
            return {
                'statusCode': 400,
                'body': json.dumps({'message': 'Text is required'})
            }

        # Call Polly to synthesize speech
        response = polly.synthesize_speech(
            Engine='generative',
            LanguageCode='en-US',
            OutputFormat='mp3',
            Text=text,
            VoiceId=voice_id
        )

        # Get the audio stream from the response
        audio_stream = response['AudioStream'].read()

        # Encode the audio stream to base64
        audio_base64 = base64.b64encode(audio_stream).decode('utf-8')
        print({
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
                },
                'body': json.dumps({
                    'audioContent': audio_base64
                }),
                'isBase64Encoded': True
            })
        return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
                },
                'body': json.dumps({
                    'audioContent': audio_base64
                }),
                'isBase64Encoded': True
            }
    except (BotoCoreError, ClientError) as error:
        print(error)
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': json.dumps({'message': 'Error processing your request'})
        }
    except Exception as e:
        print(e)
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': json.dumps({'message': 'Internal server error'})
        }
