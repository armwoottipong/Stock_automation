$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ComfyRoot = Join-Path $ProjectRoot 'vendor\ComfyUI'
$PythonExe = Join-Path $ProjectRoot '.venv-comfyui\Scripts\python.exe'

if (-not (Test-Path -LiteralPath (Join-Path $ComfyRoot 'main.py'))) {
    throw "ComfyUI is missing from $ComfyRoot"
}
if (-not (Test-Path -LiteralPath $PythonExe)) {
    throw "ComfyUI Python environment is missing from $PythonExe"
}

Push-Location $ComfyRoot
try {
    & $PythonExe main.py --lowvram --listen 127.0.0.1 --port 8188
} finally {
    Pop-Location
}
