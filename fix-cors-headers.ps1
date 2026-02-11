# fix-cors-headers.ps1
# すべてのLambda関数のCORSヘッダーを一括修正

Write-Host "=== CORS Headers Fix Script ===" -ForegroundColor Cyan
Write-Host ""

$files = @(
    "lambda/face_login/handler.py",
    "lambda/emergency_auth/handler.py",
    "lambda/re_enrollment/handler.py",
    "lambda/status/handler.py",
    "lambda/liveness/create_session_handler.py",
    "lambda/liveness/get_result_handler.py"
)

$updatedCount = 0
$errorCount = 0

foreach ($file in $files) {
    if (-not (Test-Path $file)) {
        Write-Host "⚠️  File not found: $file" -ForegroundColor Yellow
        $errorCount++
        continue
    }
    
    Write-Host "Processing: $file" -ForegroundColor White
    
    try {
        $content = Get-Content $file -Raw -Encoding UTF8
        $originalContent = $content
        
        # Pattern 1: Single line format
        $pattern1 = "'Access-Control-Allow-Origin': '\*'"
        $replacement1 = "'Access-Control-Allow-Origin': '*',`n            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',`n            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'"
        
        $content = $content -replace $pattern1, $replacement1
        
        # Pattern 2: Multi-line format (already has newline)
        $pattern2 = "'Access-Control-Allow-Origin': '\*'\s*\n"
        $replacement2 = "'Access-Control-Allow-Origin': '*',`n            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',`n            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'`n"
        
        $content = $content -replace $pattern2, $replacement2
        
        if ($content -ne $originalContent) {
            Set-Content $file $content -NoNewline -Encoding UTF8
            Write-Host "  ✓ Updated successfully" -ForegroundColor Green
            $updatedCount++
        } else {
            Write-Host "  ℹ️  No changes needed (already updated or no match)" -ForegroundColor Gray
        }
    }
    catch {
        Write-Host "  ✗ Error: $_" -ForegroundColor Red
        $errorCount++
    }
    
    Write-Host ""
}

Write-Host "=== Summary ===" -ForegroundColor Cyan
Write-Host "Files updated: $updatedCount" -ForegroundColor Green
Write-Host "Errors: $errorCount" -ForegroundColor $(if ($errorCount -gt 0) { "Red" } else { "Green" })
Write-Host ""

if ($updatedCount -gt 0) {
    Write-Host "✓ CORS headers updated successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Review the changes: git diff" -ForegroundColor White
    Write-Host "2. Deploy to AWS: cdk deploy --require-approval never" -ForegroundColor White
    Write-Host "3. Test in browser (clear cache with Ctrl+Shift+R)" -ForegroundColor White
} else {
    Write-Host "ℹ️  No files were updated. They may already have the correct CORS headers." -ForegroundColor Gray
}
