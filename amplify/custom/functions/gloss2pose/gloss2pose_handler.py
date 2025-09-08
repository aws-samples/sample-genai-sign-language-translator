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

pose_bucket = os.environ['POSE_BUCKET']
asl_data_bucket = os.environ['ASL_DATA_BUCKET']
key_prefix = os.environ["KEY_PREFIX"]
table_name = os.environ['TABLE_NAME']
output_ext='webm'


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
    return gloss_to_video(event.get("Gloss"),event.get('Text'))


def gloss_to_video(gloss_sentence,text=None, pose_only=False, pre_sign=True):
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
    manager = multiprocessing.Manager()
    return_dict = manager.dict()
    p1 = Thread(target=process_videos, args=(return_dict, "pose", sign_ids, uniq_key, pre_sign))
    p1.start()
    if not pose_only:
        p2 = Thread(target=process_videos, args=(return_dict, "sign", sign_ids, uniq_key, pre_sign))
        p2.start()
        p3 = Thread(target=process_videos, args=(return_dict, "avatar", sign_ids, uniq_key, pre_sign))
        p3.start()
        p2.join()
        p3.join()
    p1.join()
    if not pose_only:
        print(return_dict)
        return {'PoseURL': return_dict["pose"],
                'SignURL': return_dict["sign"],
                'AvatarURL': return_dict["avatar"],
                'Gloss': gloss_sentence,
                'Text': text}
    else:
        return {'PoseURL': return_dict["pose"]}


    # return {'PoseURL': process_vides("pose", sign_ids,uniq_key),
    #         'SignURL': process_vides("sign", sign_ids,uniq_key)}


def process_videos(return_dict, video_type, sign_ids, uniq_key, pre_sign):
    s3 = boto3.client('s3')
    temp_folder = f"/tmp/{uniq_key}/"
    pathlib.Path(os.path.dirname(temp_folder + f"{video_type}/")).mkdir(parents=True, exist_ok=True)

    with open(f"{temp_folder}{video_type}.txt", 'w') as writer:
        for sign_id in sign_ids:
            if video_type == "sign":
                key = f"{key_prefix}sign/sign-{sign_id}.mp4"
            elif video_type == "pose":
                key = f"{key_prefix}pose2/pose-{sign_id}.mp4"
            else:
                key = f"{key_prefix}avatar/avatar-{sign_id}.mp4"
            local_file_name = f"{temp_folder}{video_type}/{video_type}-{sign_id}.mp4"
            try:
                s3.download_file(pose_bucket, key, local_file_name)
            except:
                print(f"Unable to download {key}")
                continue
            print(f"downloading {key}")
            writer.write(f"file '{local_file_name}' \n")

    # combine the sign videos using subprocess with arguments list
    ffmpeg_args = [
        "/opt/bin/ffmpeg",
        "-f", "concat",
        "-safe", "0",
        "-i", f"{temp_folder}{video_type}.txt",
        "-c:v", "libvpx-vp9",
        f"{temp_folder}{video_type}.{output_ext}"
    ]
    
    print(f"Running command: {' '.join(ffmpeg_args)}")
    try:
        p1 = subprocess.run(
            ffmpeg_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,  # Important: shell=False for security
            check=True    # Raises CalledProcessError if command fails
        )
    except subprocess.CalledProcessError as e:
        print(f"Error running ffmpeg: {e.stderr.decode()}")
        raise

    if pre_sign:
        output_key = f"{uniq_key}/{video_type}.{output_ext}"
        try:
            s3.upload_file(
                f"{temp_folder}{video_type}.{output_ext}",
                asl_data_bucket,
                output_key
            )
            video_url = s3.generate_presigned_url(
                ClientMethod='get_object',
                Params={
                    'Bucket': asl_data_bucket,
                    'Key': output_key
                },
                ExpiresIn=604800
            )
            return_dict[video_type] = video_url
            return video_url
        except Exception as e:
            print(f"Error uploading to S3: {str(e)}")
            raise
    else:
        output_path = f"{temp_folder}{video_type}.{output_ext}"
        return_dict[video_type] = output_path
        return output_path
