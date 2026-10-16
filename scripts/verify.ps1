$ErrorActionPreference='Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
npm run build
if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed' }
& '.\.venv\Scripts\python.exe' -m pytest -q --basetemp work\pytest-verify
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
& '.\.venv\Scripts\python.exe' -m scripts.evaluate
if ($LASTEXITCODE -ne 0) { throw 'Domain evaluation failed' }
node scripts\browser-smoke.cjs
if ($LASTEXITCODE -ne 0) { throw 'Browser flow failed' }
