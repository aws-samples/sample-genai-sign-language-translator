#!/usr/bin/env python3
"""Deploy the AgentCore agent using CodeBuild."""

import boto3
import time
import sys
from pathlib import Path

def deploy_agent():
    """Trigger CodeBuild to deploy the agent."""
    
    # Read config from .bedrock_agentcore.yaml
    config_file = Path(__file__).parent / ".bedrock_agentcore.yaml"
    
    # CodeBuild project from config
    project_name = "bedrock-agentcore-slagent-builder"
    region = "us-west-2"
    
    print(f"Deploying agent using CodeBuild project: {project_name}")
    print(f"Region: {region}")
    
    # Create CodeBuild client
    codebuild = boto3.client('codebuild', region_name=region)
    
    try:
        # Start the build
        response = codebuild.start_build(
            projectName=project_name
        )
        
        build_id = response['build']['id']
        build_number = response['build']['buildNumber']
        
        print(f"\n✓ Build started successfully!")
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
                print(f"  Status: {status} - Phase: {current_phase}")
            elif status == 'SUCCEEDED':
                print(f"\n✓ Build completed successfully!")
                print(f"  Agent deployed: slagent-4BncgN2p1h")
                return 0
            elif status in ['FAILED', 'FAULT', 'TIMED_OUT', 'STOPPED']:
                print(f"\n✗ Build failed with status: {status}")
                if 'phases' in build:
                    for phase in build['phases']:
                        if phase.get('phaseStatus') == 'FAILED':
                            print(f"  Failed phase: {phase['phaseType']}")
                return 1
            else:
                print(f"  Status: {status}")
                
    except Exception as e:
        print(f"\n✗ Error deploying agent: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(deploy_agent())
