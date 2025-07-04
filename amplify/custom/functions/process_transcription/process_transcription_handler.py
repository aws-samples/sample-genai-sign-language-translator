import json
import re

import boto3
import requests


def lambda_handler(event, context):
    """
    Write a function to get the output from AWS Transcription Job
    Parameters
    ----------
    event: dict, required
        Input event to the Lambda function
    context: object, required
        Lambda Context runtime methods and attributes
    Returns
    ------
        String: Audio to text transcription created by transcription job
    """
    job_name=event.get("TranscriptionJobName")
    #get the transcription job
    transcribe = boto3.client('transcribe')
    job = transcribe.get_transcription_job(TranscriptionJobName=job_name)
    #get the output from the transcription job
    output_uri = job.get("TranscriptionJob").get("Transcript").get("TranscriptFileUri")
    print(output_uri)
    # Validate that the URL is from an expected AWS domain
    if not re.match(r'^https://.*\.amazonaws\.com/.*', output_uri):
        error_msg = "Invalid URL: The URL does not point to an AWS domain"
        print(error_msg)
        return {"Error": error_msg}
        
    try:
        response = requests.get(output_uri, timeout=10)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        # Parse the JSON response
        json_text = response.json()
        
        # Extract the transcript text
        output = json_text.get("results", {}).get("transcripts", [{}])[0].get("transcript", "")
        print(output)
        print("json text", json_text)
        return {"Text": output}
    except requests.exceptions.RequestException as e:
        print(f"Error accessing the transcript: {e}")
        return {"Error": f"Failed to access the transcript: {str(e)}"}
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return {"Error": f"Failed to decode JSON: {str(e)}"}
    except Exception as e:
        print(f"Unexpected error: {e}")
        return {"Error": f"Unexpected error occurred: {str(e)}"}
