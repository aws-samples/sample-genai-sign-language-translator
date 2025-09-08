import os
import sys

import boto3
import io

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

import cv2
import numpy as np
from .visualizer import coco_wholebody_openpose
from .visualizer.visualizer import PoseVisualizer
from .visualizer.utils import parse_pose_metainfo
from .smoother import Smoother


def create_video_using_visualizer(keypoints_list, output_file,file_type='mp4', frame_size=(640, 480), fps=30):
    if file_type=='mp4':
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    elif file_type=='webm':
        fourcc = cv2.VideoWriter_fourcc(*'VP90')

    out = cv2.VideoWriter(output_file, fourcc, fps, frame_size)
    parsed_config= parse_pose_metainfo(coco_wholebody_openpose.dataset_info)
    visualizer = PoseVisualizer(
        skeleton=parsed_config['skeleton_links'],
        link_color=parsed_config['skeleton_link_colors'],
        kpt_color=parsed_config['keypoint_colors'],
        radius =4,
        # parsed_config['dataset_keypoint_weights'],
        show_keypoint_weight=True,
        line_width=5
    )



    for keypoints in keypoints_list:
        # Create a blank frame
        img = np.zeros((frame_size[1], frame_size[0], 3), dtype=np.uint8)
        data = keypoints.reshape((1, keypoints.shape[0], keypoints.shape[1]))
        image= visualizer._draw_instances_kpts_openpose(img, data)
        # Write the frame to the video file
        out.write(image)
    # Release the VideoWriter
    out.release()
    print(f"Video saved as {output_file}")



def extract_number_from_path(file_path):
    # Get the base name of the file (6.npy in this case)
    base_name = os.path.basename(file_path)
    # Split the base name by '.' and get the first part
    number = base_name.split('.')[0]
    return number

def get_keypoints(bucket_name,folder_prefixes):
    # Initialize the S3 client
    s3 = boto3.client('s3')
    paginator = s3.get_paginator('list_objects_v2')

    # Initialize an empty list to store the numpy arrays
    poses = []

    for folder_prefix in folder_prefixes:
        # List objects in the specified S3 folder
        pages = paginator.paginate(Bucket=bucket_name, Prefix=folder_prefix)
        frame_cnt=len(poses)
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    # Get the object key
                    key = obj['Key']

                    # Check if the object is a file (not a subfolder)
                    if not key.endswith('/'):
                        # Download the file content
                        response = s3.get_object(Bucket=bucket_name, Key=key)
                        content = response['Body'].read()

                        # Load the numpy array from the content
                        result = {
                            'track_id': frame_cnt+int(extract_number_from_path(key)),
                            'keypoints': np.load(io.BytesIO(content))[0]
                        }
                        poses.append(result)
    return poses




def smooth_video(bucket_name, folder_prefixes,output_file,file_type):
    pose_results = get_keypoints(bucket_name, folder_prefixes)
    # Example 1: Smooth multi-frame pose results offline.
    filter_cfg = dict(type='GaussianFilter', window_size=3)
    smoother = Smoother(filter_cfg, keypoint_dim=2)
    smoothed_results = smoother.smooth(pose_results)
    # smoothed_results=results
    keypoints_list=list(range(len(smoothed_results)))
    for pose_result in smoothed_results:
        keypoints_list[int(pose_result["track_id"])-1] = pose_result["keypoints"]
    create_video_using_visualizer(keypoints_list,output_file,file_type=file_type)


if __name__ == '__main__':
    # Usage example
    bucket_name = 'genasl-avatar'
    folder_prefixes = [ 'aslavatarv2/gloss2pose/lookup/keypoints/1012',
                        'aslavatarv2/gloss2pose/lookup/keypoints/1004',
                        'aslavatarv2/gloss2pose/lookup/keypoints/1009']
    smooth_video(bucket_name, folder_prefixes,"test_out.webm","webm")