"""Verify a real backend process restart preserves a case and committed receipt."""
from pathlib import Path
import json
import subprocess
import time
import httpx

ROOT=Path(__file__).resolve().parents[1]
client=httpx.Client(base_url='http://127.0.0.1:8787',timeout=10)
assert client.get('/api/health').json()['version']=='0.1.0'
def post(route,data=None):
    r=client.post(route,json=data or {})
    r.raise_for_status()
    return r.json()
s=post('/api/cases/demo')
doc=next(d for d in s['documents'] if d['filename']=='supplier_notice_v1.txt')
s=post(f"/api/cases/{s['id']}/analyze",{'document_id':doc['id'],'mode':'fixture'})
run=s['runs'][-1]
s=post(f"/api/cases/{s['id']}/reviews",{'run_id':run['id'],'revision':1,'lot_ids':['SUP-A'],'accept_scope':True,'bounded_scope_reviewed':True})
s=post(f"/api/cases/{s['id']}/approve",{'plan_id':s['plan']['id'],'digest':s['plan']['digest']})
s=post(f"/api/cases/{s['id']}/apply",{'plan_id':s['plan']['id'],'digest':s['plan']['digest'],'actions':s['plan']['actions'],'idempotency_key':'restart-proof-request'})
receipt=s['receipts'][0]
# The app identity is checked above; only this project's loopback listener is stopped.
ps=r"""
$listener=Get-NetTCPConnection -LocalPort 8787 -State Listen -ErrorAction Stop
$ownedServer=Get-Process -Id $listener.OwningProcess -ErrorAction Stop
if ($ownedServer.ProcessName -ne 'python') { throw 'Unexpected listener; refusing restart' }
Stop-Process -Id $ownedServer.Id -ErrorAction Stop
$newBackend=Start-Process -FilePath 'D:\projects\BatchFence\.venv\Scripts\python.exe' -ArgumentList @('-m','uvicorn','backend.app:app','--host','127.0.0.1','--port','8787') -WorkingDirectory 'D:\projects\BatchFence' -RedirectStandardOutput 'D:\projects\BatchFence\work\server.stdout.log' -RedirectStandardError 'D:\projects\BatchFence\work\server.stderr.log' -WindowStyle Hidden -PassThru
$newBackend.Id | Set-Content -LiteralPath 'D:\projects\BatchFence\work\server-launcher.pid'
"""
subprocess.run(['powershell.exe','-NoProfile','-Command',ps],check=True,cwd=ROOT)
for _ in range(30):
    try:
        if client.get('/api/health').status_code==200:break
    except httpx.HTTPError:
        pass
    time.sleep(.2)
after=client.get('/api/cases/'+s['id'])
after.raise_for_status()
current=after.json()
assert current['receipts'][0]==receipt
assert current['plan']['status']=='applied'
assert sum(p['units'] for p in current['stocks'] if p['status']=='held')==500
report={'passed':True,'case_id':s['id'],'receipt_transaction_id':receipt['transaction_id'],
        'held_units':500,'mechanism':'Actual owned uvicorn listener stopped and relaunched; same HTTP client session recovered exact case and receipt from SQLite.'}
(ROOT/'docs/restart-results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
