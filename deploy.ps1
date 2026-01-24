# Face-Auth IdP System - PowerShell Deployment Script
# This script deploys the AWS CDK infrastructure for the Face-Auth system

Write-Host "🚀 Starting Face-Auth IdP System deployment..." -ForegroundColor Green

# Check if AWS CDK is installed
try {
    cdk --version | Out-Null
} catch {
    Write-Host "❌ AWS CDK is not installed. Please install it first:" -ForegroundColor Red
    Write-Host "npm install -g aws-cdk" -ForegroundColor Yellow
    exit 1
}

# Check if Python virtual environment exists
if (-not (Test-Path "venv")) {
    Write-Host "📦 Creating Python virtual environment..." -ForegroundColor Blue
    python -m venv venv
}

Write-Host "📦 Activating virtual environment and installing dependencies..." -ForegroundColor Blue
& "venv\Scripts\Activate.ps1"
pip install -r requirements.txt

# Bootstrap CDK (only needed once per account/region)
Write-Host "🔧 Bootstrapping CDK..." -ForegroundColor Blue
cdk bootstrap

# Synthesize the CloudFormation template
Write-Host "🔍 Synthesizing CDK template..." -ForegroundColor Blue
cdk synth

# Deploy the stack
Write-Host "🚀 Deploying Face-Auth IdP Stack..." -ForegroundColor Blue
cdk deploy --require-approval never

Write-Host "✅ Deployment completed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Yellow
Write-Host "1. Configure Direct Connect for on-premises AD connection"
Write-Host "2. Create Rekognition collection: aws rekognition create-collection --collection-id face-auth-employees"
Write-Host "3. Populate card templates in DynamoDB"
Write-Host "4. Test the API endpoints"
Write-Host ""
Write-Host "🔗 Check the CloudFormation outputs for important resource information." -ForegroundColor Cyan