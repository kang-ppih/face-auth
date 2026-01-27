# Face-Auth IdP System - Frontend Deployment Script
# このスクリプトはフロントエンドをビルドしてS3にデプロイします

param(
    [Parameter(Mandatory=$false)]
    [string]$Profile = "dev",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipBuild = $false
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Face-Auth Frontend Deployment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# エラー時に停止
$ErrorActionPreference = "Stop"

# フロントエンドディレクトリに移動
Set-Location frontend

# ビルドをスキップしない場合
if (-not $SkipBuild) {
    Write-Host "Building frontend..." -ForegroundColor Yellow
    npm run build
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Build failed!" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Build completed successfully!" -ForegroundColor Green
    Write-Host ""
}

# CloudFormationスタックから情報を取得
Write-Host "Getting deployment information from CloudFormation..." -ForegroundColor Yellow

$stackName = "FaceAuthStack"

try {
    # S3バケット名を取得
    $bucketName = aws cloudformation describe-stacks `
        --stack-name $stackName `
        --query "Stacks[0].Outputs[?OutputKey=='FrontendBucketName'].OutputValue" `
        --output text `
        --profile $Profile
    
    # CloudFront Distribution IDを取得
    $distributionId = aws cloudformation describe-stacks `
        --stack-name $stackName `
        --query "Stacks[0].Outputs[?OutputKey=='FrontendDistributionId'].OutputValue" `
        --output text `
        --profile $Profile
    
    # Frontend URLを取得
    $frontendUrl = aws cloudformation describe-stacks `
        --stack-name $stackName `
        --query "Stacks[0].Outputs[?OutputKey=='FrontendURL'].OutputValue" `
        --output text `
        --profile $Profile
    
    Write-Host "Bucket Name: $bucketName" -ForegroundColor Cyan
    Write-Host "Distribution ID: $distributionId" -ForegroundColor Cyan
    Write-Host "Frontend URL: $frontendUrl" -ForegroundColor Cyan
    Write-Host ""
    
} catch {
    Write-Host "Failed to get stack information. Make sure the infrastructure is deployed." -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    exit 1
}

# S3にアップロード
Write-Host "Uploading files to S3..." -ForegroundColor Yellow

aws s3 sync build/ s3://$bucketName/ `
    --delete `
    --profile $Profile `
    --cache-control "public, max-age=31536000, immutable" `
    --exclude "index.html" `
    --exclude "asset-manifest.json" `
    --exclude "manifest.json"

# index.htmlは短いキャッシュ時間で
aws s3 cp build/index.html s3://$bucketName/index.html `
    --profile $Profile `
    --cache-control "public, max-age=0, must-revalidate" `
    --content-type "text/html"

# manifest.jsonもアップロード
aws s3 cp build/manifest.json s3://$bucketName/manifest.json `
    --profile $Profile `
    --cache-control "public, max-age=3600" `
    --content-type "application/json"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Upload failed!" -ForegroundColor Red
    exit 1
}

Write-Host "Upload completed successfully!" -ForegroundColor Green
Write-Host ""

# CloudFrontキャッシュをクリア
Write-Host "Invalidating CloudFront cache..." -ForegroundColor Yellow

$invalidationId = aws cloudfront create-invalidation `
    --distribution-id $distributionId `
    --paths "/*" `
    --profile $Profile `
    --query "Invalidation.Id" `
    --output text

if ($LASTEXITCODE -ne 0) {
    Write-Host "Cache invalidation failed!" -ForegroundColor Red
    exit 1
}

Write-Host "Cache invalidation created: $invalidationId" -ForegroundColor Green
Write-Host ""

# 元のディレクトリに戻る
Set-Location ..

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Deployment completed successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Frontend URL: $frontendUrl" -ForegroundColor Cyan
Write-Host ""
Write-Host "Note: CloudFront cache invalidation may take a few minutes to complete." -ForegroundColor Yellow
Write-Host "You can check the status with:" -ForegroundColor Yellow
Write-Host "aws cloudfront get-invalidation --distribution-id $distributionId --id $invalidationId --profile $Profile" -ForegroundColor Gray
