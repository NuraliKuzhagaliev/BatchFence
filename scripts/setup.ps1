$ErrorActionPreference='Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
$env:ELECTRON_CACHE=Join-Path (Get-Location) '.cache\electron'
$env:ELECTRON_BUILDER_CACHE=Join-Path (Get-Location) '.cache\electron-builder'
$projectCache=Join-Path (Get-Location) '.cache\npm'
npm ci --cache $projectCache
if ($LASTEXITCODE -ne 0) { throw 'npm ci failed' }
if (!(Test-Path '.venv')) { python -m venv .venv }
& '.\.venv\Scripts\python.exe' -m pip install --cache-dir '.cache\pip' -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Python installation failed' }
npm run build
if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed' }
