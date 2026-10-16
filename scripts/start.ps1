$ErrorActionPreference='Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
if (!(Test-Path '.venv\Scripts\python.exe')) { throw 'Run scripts\setup.ps1 first.' }
if (!(Test-Path 'dist\index.html')) { npm run build }
& '.\.venv\Scripts\python.exe' -m uvicorn backend.app:app --host 127.0.0.1 --port 8787
