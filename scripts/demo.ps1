param(
    [ValidateSet("check", "run", "reset", "serve")]
    [string]$Command = "check"
)
$python = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) { throw "Create the local virtual environment first: python -m venv .venv" }
switch ($Command) {
    "check" { & $python -m supportmaster.quality; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; & $python -m supportmaster.release --allow-anonymous }
    "run" { & $python -m supportmaster.demo reset; & $python -m supportmaster.demo run }
    "reset" { & $python -m supportmaster.demo reset }
    "serve" { & $python -m supportmaster.web --host 127.0.0.1 --port 8001 }
}
