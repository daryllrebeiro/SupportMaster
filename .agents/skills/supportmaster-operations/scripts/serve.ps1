# SupportMaster Server Launcher
param (
    [int]$Port = 8001,
    [string]$AuthMode = "REQUIRED",
    [string]$ApiKeys = "secret|operator|demo-acme|RUN_EXECUTE,AUDIT_READ;secret-bad|operator|demo-bad|RUN_EXECUTE",
    [bool]$AutoApprove = $false
)

Write-Host "Configuring SupportMaster Environment Variables..." -ForegroundColor Cyan
$env:SUPPORTMASTER_AUTH_MODE = $AuthMode
$env:SUPPORTMASTER_API_KEYS = $ApiKeys
$env:SUPPORTMASTER_AUTO_APPROVE = if ($AutoApprove) { "true" } else { "false" }

Write-Host "Starting SupportMaster Server on port $Port..." -ForegroundColor Green
Write-Host "Authentication Mode: $AuthMode" -ForegroundColor Cyan
Write-Host "Auto-Approve Enabled: $AutoApprove" -ForegroundColor Cyan

& .\.venv\Scripts\python.exe -m supportmaster.web --port $Port
