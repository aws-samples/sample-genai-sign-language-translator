import json
import os

import boto3

eng_to_asl_model = os.environ['ENG_TO_ASL_MODEL']


def construct_query(text):
    return f"""

Human: Here are some examples of translations from english text to ASL gloss 
Examples:
Apples ==> APPLE
you  ==> IX-2P
your  ==> IX-2P
Love ==> LIKE
My ==> IX-1P
Thanks ==> THANK-YOU
am ==> 
and ==> 
be ==>
of ==>
video ==> MOVIE
image ==> PICTURE
conversations ==> TALK
type of ==> TYPE
Watch ==> SEE

Translate the following english text to ASL Gloss and return only the gloss. Don't provide any explanation.
{text} ==>


Assistant:"""


def lambda_handler(event, context):
    """Invoke Bedrock to convert English text to ASL Gloss
    Parameters
    ----------
    event: dict, required
        Input event to the Lambda function
    context: object, required
        Lambda Context runtime methods and attributes
    Returns
    ------
        dict: text consists of ASL Gloss
    """
    #

    return {'Gloss': text_to_asl_gloss(event.get("Text")),
            'Text': event.get("Text")}


def text_to_asl_gloss(text):
    bedrock_client = boto3.client(service_name="bedrock-runtime")
    # create the prompt
    prompt_data = construct_query(text)
    conversation = [
        {
            "role": "user",
            "content": [{"text": prompt_data}],
        }
    ]
    inferenceConfig = {"maxTokens": 3000, "temperature": 0.0, "topP": 0.5, }

    modelId = eng_to_asl_model

    response = bedrock_client.converse(
        modelId=modelId,
        messages=conversation,
        inferenceConfig=inferenceConfig,
    )

    gloss = response["output"]["message"]["content"][0]["text"]

    print(gloss)
    return gloss


if __name__ == "__main__":
    lambda_handler({"Text": "what is your name"}, {})
    lambda_handler({"Text": "How are you?"}, {})
    lambda_handler({"Text": "She is watching a movie"}, {})
    lambda_handler({"Text": "He wants to play"}, {})
    lambda_handler({"Text": "Can you come with me?"}, {})
