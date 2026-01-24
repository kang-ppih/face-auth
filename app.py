#!/usr/bin/env python3
"""
Face-Auth IdP System - AWS CDK Application Entry Point

This is the main entry point for the AWS CDK application that deploys
the Face-Auth Identity Provider system infrastructure.
"""

import os
import aws_cdk as cdk
from infrastructure.face_auth_stack import FaceAuthStack

app = cdk.App()

# Get environment configuration
env = cdk.Environment(
    account=os.getenv('CDK_DEFAULT_ACCOUNT'),
    region=os.getenv('CDK_DEFAULT_REGION', 'ap-northeast-1')
)

# Deploy the Face-Auth IdP Stack
FaceAuthStack(
    app, 
    "FaceAuthIdPStack",
    env=env,
    description="Face-Auth Identity Provider System - AWS Infrastructure"
)

app.synth()