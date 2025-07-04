import json
import os
import boto3
import time
import logging


def lambda_handler(event, context):
    print('received event:')
    print(event)
    # invoke step function
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    sfn_client = boto3.client('stepfunctions')
    if "sfn_execution_arn" in event["queryStringParameters"]:
        exec_response = sfn_client.describe_execution(executionArn=event["queryStringParameters"]["sfn_execution_arn"])
        if exec_response.get('status') == 'RUNNING':
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Headers': '*',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
                },
                'body': json.dumps({"sfn_execution_arn" : exec_response['executionArn']})
            }
        else:
            # (exec_response.get('status') == 'SUCCEEDED'):
            print("lambda success")
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Headers': '*',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
                },
                'body': exec_response['output']
            }
    if "Gloss" in event["queryStringParameters"]:
        input = json.dumps({"Gloss": event["queryStringParameters"]["Gloss"]})
        stateMachineArn = os.environ['STATE_MACHINE_ARN_BLENDED_POSE']
    elif "Text" in event["queryStringParameters"]:
        input = json.dumps({"Text": event["queryStringParameters"]["Text"]})
        stateMachineArn = os.environ['STATE_MACHINE_ARN']
    else:
        input = json.dumps({
            "BucketName": event["queryStringParameters"]["BucketName"],
            "KeyName": event["queryStringParameters"]["KeyName"]})
        stateMachineArn = os.environ['STATE_MACHINE_ARN']

    sfn_execution_arn = sfn_client.start_execution(
        stateMachineArn=stateMachineArn,
        input=input
    ).get('executionArn')
    logger.info({'stateMachineArn': sfn_execution_arn})
    exec_response = sfn_client.describe_execution(executionArn=sfn_execution_arn)
    print(exec_response)
    return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Headers': '*',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': json.dumps({"sfn_execution_arn" : sfn_execution_arn})
        }

