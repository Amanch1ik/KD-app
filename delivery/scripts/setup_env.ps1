# Windows PowerShell script to set up Python virtual environment and install dependencies
param(
  [string]$venvDir = "venv"
)

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  Write-Error "Python is not installed or not found in PATH. Install Python and try again."
  exit 1
}

$repoRoot = (Get-Location).Path
$venvPath = Join-Path -Path $repoRoot -ChildPath $venvDir

if (-not (Test-Path $venvPath)) {
  & python -m venv $venvDir
}

$venvPython = Join-Path -Path $venvPath -ChildPath 'Scripts\python.exe'
if (-not (Test-Path $venvPython)) {
  Write-Error "Virtual environment Python not found at $venvPath."
  exit 1
}

& $venvPython -m ensurepip --upgrade
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r "$repoRoot\\requirements.txt"

Write-Output "Dependencies installed in $venvPath."


