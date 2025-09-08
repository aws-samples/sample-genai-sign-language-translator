import multiprocessing
import os
import re
import subprocess
import sys
from threading import Thread

import boto3
from boto3.dynamodb.conditions import Key
import uuid
import pathlib

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from blending.smooth_video import smooth_video

pose_bucket = os.environ['POSE_BUCKET']
asl_data_bucket = os.environ['ASL_DATA_BUCKET']
key_prefix = os.environ["KEY_PREFIX"]
table_name = os.environ['TABLE_NAME']
file_type='webm'

def lambda_handler(event, context):
    """.
    This function takes gloss sentence as input and split them by spaces to individual gloss
    and query DynamoDB to get the items matching gloss and returns a list of temporary signed URls as output
    Parameters
    ----------
    event: dict, required
        Input event to the Lambda function

    context: object, required
        Lambda Context runtime methods and attributes

    Returns
    ------
        dict: Object containing details of the stock selling transaction
    """
    # Get the Gloss from event
    return gloss_to_video(event.get("Gloss"))


def gloss_to_video(gloss_sentence,pose_only=False, pre_sign=True):
    uniq_key = str(uuid.uuid4())

    sign_ids = []

    for gloss in gloss_sentence.split(" "):
        gloss = re.sub('[,!?.]', '', gloss.strip())
        # query dynamodb table
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(table_name)
        response = table.query(
            KeyConditionExpression=Key('Gloss').eq(gloss)
        )
        # for now pick the first item in the response
        if response['Count'] == 0:
            #if not sign found finger spell it
            for c in gloss:
                response = table.query(
                    KeyConditionExpression=Key('Gloss').eq(c)
                )
                if response['Count'] > 0:
                    sign_ids.append(response['Items'][0]['SignID'])
        else:
            sign_ids.append(response['Items'][0]['SignID'])
    # print(sign_ids)

    return {
        'SmoothPoseURL': create_smooth_videos("smooth_pose",sign_ids, uniq_key, pre_sign)
             }



def create_smooth_videos(video_type, sign_ids, uniq_key,pre_sign):
    s3 = boto3.client('s3')
    temp_folder = f"/tmp/{uniq_key}/"
    pathlib.Path(os.path.dirname(temp_folder + f"{video_type}/")).mkdir(parents=True, exist_ok=True)
    keypoint_prefixes=[]
    for sign_id in sign_ids:
        keypoint_prefixes.append(f"{key_prefix}keypoints/{sign_id}")
    output_file=f"{temp_folder}{video_type}.mp4"
    smooth_video(pose_bucket, keypoint_prefixes,output_file,file_type=file_type)
    if pre_sign:
        s3.upload_file(output_file, asl_data_bucket, f"{uniq_key}/{video_type}.{file_type}")
        video_url = s3.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': asl_data_bucket,
                'Key': f"{uniq_key}/{video_type}.{file_type}"
            },
            ExpiresIn=604800
        )
        return video_url
    else:
        return f"{temp_folder}{video_type}.{file_type}"
