# SupportMaster Test Suite Runner
Write-Host "Running SupportMaster Unit & Integration Tests..." -ForegroundColor Cyan

& .\.venv\Scripts\python.exe -m unittest discover -s tests -v

if ($LASTEXITCODE -eq 0) {
    Write-Host "All tests passed successfully!" -ForegroundColor Green
} else {
    Write-Host "Some tests failed! Check logs above." -ForegroundColor Red
    exit $LASTEXITCODE
}
