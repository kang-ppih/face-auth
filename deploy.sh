#!/bin/bash

# Face-Auth IdP System - Deployment Script
# This script deploys the AWS CDK infrastructure for the Face-Auth system

set -e

echo "🚀 Starting Face-Auth IdP System deployment..."

# Check if AWS CDK is installed
if ! command -v cdk &> /dev/null; then
    echo "❌ AWS CDK is not installed. Please install it first:"
    echo "npm install -g aws-cdk"
    exit 1
fi

# Check if Python dependencies are installed
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

echo "📦 Activating virtual environment and installing dependencies..."
source venv/bin/activate
pip install -r requirements.txt

# Bootstrap CDK (only needed once per account/region)
echo "🔧 Bootstrapping CDK..."
cdk bootstrap

# Synthesize the CloudFormation template
echo "🔍 Synthesizing CDK template..."
cdk synth

# Deploy the stack
echo "🚀 Deploying Face-Auth IdP Stack..."
cdk deploy --require-approval never

echo "✅ Deployment completed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Configure Direct Connect for on-premises AD connection"
echo "2. Create Rekognition collection: aws rekognition create-collection --collection-id face-auth-employees"
echo "3. Populate card templates in DynamoDB"
echo "4. Test the API endpoints"
echo ""
echo "🔗 Check the CloudFormation outputs for important resource information."