"""Create private local pilot config once, without printing credentials."""
import os
import secrets
from pathlib import Path
from backend.fixtures import ROOT

root=ROOT/'work/pilot-config'
if root.exists(): raise SystemExit('Private pilot configuration already exists; preserving it.')
root.mkdir(mode=0o700)
admin=secrets.token_urlsafe(40); runtime=secrets.token_urlsafe(40); signing=secrets.token_urlsafe(48)
files={
    'postgres.env':f'POSTGRES_USER=batchfence_migration\nPOSTGRES_DB=batchfence\nPOSTGRES_PASSWORD={admin}\n',
    'migration.env':f'PILOT_DATABASE_URL=postgresql://batchfence_migration:{admin}@postgres:5432/batchfence\nPILOT_RUNTIME_PASSWORD={runtime}\n',
    'app.env':f'PILOT_DATABASE_URL=postgresql://batchfence_runtime:{runtime}@postgres:5432/batchfence\nPILOT_SESSION_SECRET={signing}\nDEPLOYMENT_PROFILE=pilot\nSOURCE_STORAGE_PATH=/var/data/sources\nAPP_ORIGIN=http://127.0.0.1:8788\nPUBLIC_DEMO=false\nINFERENCE_MODE=fixture\nMAX_ORG_LIVE_JOBS=20\nMAX_USER_LIVE_JOBS=8\n',
}
for name,content in files.items():
    path=root/name
    with path.open('x',encoding='utf-8') as f: f.write(content)
    os.chmod(path,0o600)
for name in ('postgres','sources','backups'): (ROOT/'work/pilot-data'/name).mkdir(parents=True,exist_ok=True)
print('Created private configuration under work/pilot-config. No default user/password, model key, or public exposure configured.')
