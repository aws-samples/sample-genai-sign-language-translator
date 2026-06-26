#!/usr/bin/env python3
"""Package and deploy the AgentCore agent."""

import boto3
import time
import sys
import zipfile
import tempfile
from pathlib import Path

def create_source_zip():
    """Create a zip file with the agent source code."""
    print("Creating source package...")
    
    base_dir = Path(__file__).parent
    
    # Directories to include
    include_dirs = [
        "signlanguageagent",
        "text2gloss",
        "gloss2pose",
        "audio_processing",
        "asl_analysis",
        "audio2sign"
    ]
    
    # Create temporary zip file
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.zip', delete=False) as tmp:
        zip_path = tmp.name
        
        with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add Dockerfile
            dockerfile = base_dir / "Dockerfile"
            if dockerfile.exists():
                zipf.write(dockerfile, "Dockerfile")
                print(f"  Added: Dockerfile")
            
            # Add .dockerignore if exists
            dockerignore = base_dir / ".dockerignore"
            if dockerignore.exists():
                zipf.write(dockerignore, ".dockerignore")
                print(f"  Added: .dockerignore")
            
            # Add all required directories
            for dir_name in include_dirs:
                dir_path = base_dir / dir_name
                if dir_path.exists():
                    for file in dir_path.rglob("*"):
                        if file.is_file() and not file.name.startswith('.') and '__pycache__' not in str(file):
                            arcname = file.relative_to(base_dir)
                            zipf.write(file, arcname)
                            print(f"  Added: {arcname}")
                else:
                    print(f"  Warning: Directory not found: {dir_name}")
    
    print(f"✓ Source package created: {zip_path}")
    return zip_path

def upload_to_s3(zip_path):
    """Upload the source package to S3."""
    bucket = "bedrock-agentcore-codebuild-sources-853513360253-us-west-2"
    key = "slagent/source.zip"
    region = "us-west-2"
    
    print(f"\nUploading to S3...")
    print(f"  Bucket: {bucket}")
    print(f"  Key: {key}")
    
    s3 = boto3.client('s3', region_name=region)
    
    try:
        s3.upload_file(zip_path, bucket, key)
        print(f"✓ Source uploaded successfully")
        return True
    except Exception as e:
        print(f"✗ Error uploading to S3: {e}")
        return False

def trigger_build():
    """Trigger CodeBuild to deploy the agent."""
    project_name = "bedrock-agentcore-slagent-builder"
    region = "us-west-2"
    
    print(f"\nTriggering CodeBuild...")
    print(f"  Project: {project_name}")
    
    codebuild = boto3.client('codebuild', region_name=region)
    
    try:
        response = codebuild.start_build(projectName=project_name)
        
        build_id = response['build']['id']
        build_number = response['build']['buildNumber']
        
        print(f"✓ Build started!")
        print(f"  Build ID: {build_id}")
        print(f"  Build Number: {build_number}")
        print(f"\nMonitoring build progress...")
        
        # Monitor the build
        while True:
            time.sleep(5)
            
            build_info = codebuild.batch_get_builds(ids=[build_id])
            build = build_info['builds'][0]
            status = build['buildStatus']
            
            if status == 'IN_PROGRESS':
                current_phase = build.get('currentPhase', 'UNKNOWN')
                print(f"  {current_phase}...", end='\r')
            elif status == 'SUCCEEDED':
                print(f"\n\n✓ Deployment completed successfully!")
                print(f"  Agent ID: slagent-4BncgN2p1h")
                print(f"  Region: {region}")
                return 0
            elif status in ['FAILED', 'FAULT', 'TIMED_OUT', 'STOPPED']:
                print(f"\n\n✗ Build failed with status: {status}")
                return 1
                
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return 1

def main():
    """Main deployment workflow."""
    print("=" * 60)
    print("AgentCore Agent Deployment")
    print("=" * 60)
    
    # Step 1: Create source package
    zip_path = create_source_zip()
    
    # Step 2: Upload to S3
    if not upload_to_s3(zip_path):
        return 1
    
    # Step 3: Trigger build
    return trigger_build()

if __name__ == "__main__":
    sys.exit(main())
