"""Restart only the verified project server; compare existing live evidence exactly.

No inference calls. Private cookies are read locally and never emitted.
"""
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'docs/ambiguity-fix'
ambiguous = json.loads((DEST / 'live-ambiguity.json').read_text())
clear = json.loads((DEST / 'clear-live/browser-results.json').read_text())
targets = [(x['case_id'], ROOT / 'work/ambiguity-live-session.json') for x in ambiguous['cases']]
# The exported packet carries the case ID, never a session capability.
packet = json.loads((DEST / 'clear-live/packet-2.json').read_text())
targets.append((packet['case']['id'], ROOT / 'work/live-verification/ambiguity-fix-live/private-browser-session.json'))
sessions = []
for case_id, file in targets:
    c = httpx.Client(base_url='http://127.0.0.1:8787', timeout=10)
    private = json.loads(file.read_text())
    if isinstance(private, list):
        c.cookies.update({v['name']: v['value'] for v in private})
    elif 'cookies' in private:
        c.cookies.update({v['name']: v['value'] for v in private['cookies']})
    else:
        c.cookies.update(private)
    response = c.get('/api/cases/' + case_id)
    response.raise_for_status()
    sessions.append((c, case_id, response.json()))
assert sessions[0][0].get('/api/health').json()['version'] == '0.1.1'
ps = r'''
$listener=Get-NetTCPConnection -LocalPort 8787 -State Listen -ErrorAction Stop
if (@($listener).Count -ne 1) { throw 'Unexpected listener count' }
$ownedServer=Get-CimInstance Win32_Process -Filter ("ProcessId="+$listener.OwningProcess)
if ($ownedServer.Name -ne 'python.exe' -or $ownedServer.CommandLine -notmatch 'uvicorn backend.app:app' -or $ownedServer.CommandLine -notmatch 'BatchFence') { throw 'Unexpected process; refusing restart' }
$previous=$ownedServer.ProcessId
Stop-Process -Id $previous -ErrorAction Stop
$newBackend=Start-Process -FilePath 'D:\projects\BatchFence\.venv\Scripts\python.exe' -ArgumentList @('-m','uvicorn','backend.app:app','--host','127.0.0.1','--port','8787') -WorkingDirectory 'D:\projects\BatchFence' -RedirectStandardOutput 'D:\projects\BatchFence\work\server-0.1.1.stdout.log' -RedirectStandardError 'D:\projects\BatchFence\work\server-0.1.1.stderr.log' -WindowStyle Hidden -PassThru
@{stopped_pid=$previous;launcher_pid=$newBackend.Id}|ConvertTo-Json -Compress
'''
# Detached Windows descendants can inherit capture pipes and keep communicate()
# waiting after PowerShell exits. A file avoids that pipe-lifetime deadlock.
with (ROOT / 'work/restart-processes.json').open('w', encoding='utf-8') as output:
    subprocess.run(['powershell.exe', '-NoProfile', '-Command', ps], check=True, stdout=output, timeout=30)
processes = json.loads((ROOT / 'work/restart-processes.json').read_text(encoding='utf-8-sig'))
for _ in range(60):
    try:
        if sessions[0][0].get('/api/health').status_code == 200:
            break
    except httpx.HTTPError:
        pass
    time.sleep(.25)
results = []
for c, case_id, before in sessions:
    response = c.get('/api/cases/' + case_id)
    response.raise_for_status()
    after = response.json()
    for field in ['runs', 'scope', 'plan', 'receipts', 'stocks', 'history']:
        assert after.get(field) == before.get(field), (case_id, field)
    results.append({'case_id': case_id, 'equal_fields': ['runs','scope','plan','receipts','stocks','history'],
                    'receipts': len(after['receipts']), 'held_units': sum(x['units'] for x in after['stocks'] if x['status']=='held'),
                    'plan_status': after['plan']['status'] if after['plan'] else None})
    c.close()
report = {'passed': True, 'at': datetime.now(timezone.utc).isoformat(), 'mechanism': 'Actual verified project uvicorn process stopped and relaunched',
          'processes': processes, 'new_inference_calls': 0, 'cases': results}
(DEST / 'restart-results.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
