import os
import subprocess
import sys

os.environ['POSE_BUCKET'] = "genasl-avatar"
os.environ['ASL_DATA_BUCKET'] = "genasl-data"
os.environ['KEY_PREFIX'] = "aslavatarv2/gloss2pose/lookup/"

os.environ['TABLE_NAME'] = 'Pose_Data6'

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
shared_dir = os.path.normpath(os.path.join(SCRIPT_DIR, '..'))
sys.path.append(shared_dir)
sys.path.append(os.path.join(shared_dir, 'text2gloss'))
print(os.path.join(shared_dir, 'text2gloss'))

import text2gloss_handler
from gloss2pose_handler import gloss_to_video


def generate_realtime_asl_avatar(caption_text, duration):
    gloss = text2gloss_handler.text_to_asl_gloss(caption_text)
    result = gloss_to_video(gloss, text=caption_text, pose_only=False, pre_sign=False)
    print(result['PoseURL'])
    print(result['SignURL'])
    print(result['AvatarURL'])
    resync_video([result['PoseURL'], result['SignURL'], result['AvatarURL']], duration)

if __name__ == "__main__":
    text = "Hello, everyone, Welcome to re:Invent 2023 this year..."  # Your text here
    duration = 45
    generate_realtime_asl_avatar(text, duration)


def get_length(filename):
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        filename
    ]
    
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=False  # Explicitly set shell=False for security
    )
    return float(result.stdout)



def resync_video(video_file_names, duration):
    for video_file_name in video_file_names:
        video_duration = get_length(video_file_name)
        if duration:
            speed_up = duration/video_duration
        else:
            speed_up = 1
            
        # Create ffmpeg command as a list of arguments
        ffmpeg_cmd = [
            "ffmpeg",
            "-i", video_file_name,
            "-filter:v", f"setpts={speed_up}*PTS",
            f"{video_file_name}.out.webm"
        ]
        
        print(f"Running command: {' '.join(ffmpeg_cmd)}")
        try:
            result = subprocess.run(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,  # Explicitly set shell=False for security
                check=True    # Raise CalledProcessError if command fails
            )
        except subprocess.CalledProcessError as e:
            print(f"Error running ffmpeg: {e.stderr.decode()}")
            raise


if __name__ == "__main__":
    # text = "Hi, my name is Emily Weber. I'm a machine learning specialist at Amazon Web services. And today we're going to talk about Amazon Sage Maker. Amazon Sage Maker is a fully-managed machine learning service that developers and data scientists can use to build train and deploy machine learning models. Today, we're going to talk about notebook instances and this is your deep dive. So with the notebook instances on stage maker, it all starts with a notebook, right? And within the notebook, it starts with your EC two instance, your EC two instance, that's your elastic compute cloud, that's your virtual machine that's going to spin up and let us do all of our processing. This is a managed EC two instance that means that even though we're turning it on and off, it's not going to show."
    text= "Hello, everyone, Welcome to re:Invent 2023 this year. I'm especially excited to stand on this stage and share our vision with all of you. That's because this year we are standing at the edge of another technological era, an era in which a powerful relationship between humans and technology is unfolding right before us. Generative A. I is augmenting human productivity in many unexpected ways while also fueling human intelligence and creativity. This relationship, in which both humans and a I for new innovations is rife with so many possible"
    duration=45
    generate_realtime_asl_avatar(text,duration)
