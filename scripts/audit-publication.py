"""Audit publishable Git history and working files without emitting secret values."""
from pathlib import Path
from datetime import datetime, timezone
import io, json, re, subprocess, zipfile, os
from dotenv import dotenv_values
from urllib.parse import urlsplit
ROOT = Path(__file__).resolve().parents[1]
def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)
needles = {v.encode() for private_file in (ROOT/'.env', ROOT/'work/cloud-demo.env')
           for k,v in dotenv_values(private_file).items()
           if v and k!='EVOLUS_GEMMA_MODEL_KEY' and any(x in k.upper() for x in ('KEY', 'TOKEN', 'SECRET', 'PASSWORD'))}
for private_file in (ROOT/'work/pilot-config').glob('*.env'):
    for k,v in dotenv_values(private_file).items():
        if not v: continue
        if any(x in k.upper() for x in ('KEY','TOKEN','SECRET','PASSWORD')): needles.add(v.encode())
        if 'DATABASE_URL' in k and urlsplit(v).password: needles.add(urlsplit(v).password.encode())
for private_file in [*(ROOT/'work/pilot-data/backups').glob('*private.json'),*(ROOT/'work').glob('enterprise-live*/private.json')]:
    values=json.loads(private_file.read_text(encoding='utf-8-sig'))
    for k,v in values.items():
        if isinstance(v,str) and any(x in k.upper() for x in ('KEY','TOKEN','SECRET','PASSWORD')): needles.add(v.encode())
def sessions(x):
    if isinstance(x, dict):
        if x.get('name') == 'bf_session' and isinstance(x.get('value'), str): needles.add(x['value'].encode())
        if isinstance(x.get('bf_session'), str): needles.add(x['bf_session'].encode())
        for v in x.values(): sessions(v)
    elif isinstance(x, list):
        for v in x: sessions(v)
for f in (ROOT/'work').rglob('*session*.json'):
    try: sessions(json.loads(f.read_text(encoding='utf-8-sig')))
    except (ValueError, OSError): pass
patterns = [rb'sk-(?:proj-)?[A-Za-z0-9_-]{24,}', rb'hf_[A-Za-z0-9]{24,}',
            rb'rc-[A-Za-z0-9]{40,}',
            rb'Bearer[ \t]+[A-Za-z0-9_=/+-]{24,}', rb'gh[pousr]_[A-Za-z0-9]{30,}']
findings=[]; checked=0; largest=[]
def inspect(name, raw):
    global checked
    checked += 1
    if any(v in raw for v in needles): findings.append({'file':name,'reason':'Known private value'})
    if any(re.search(p,raw) for p in patterns): findings.append({'file':name,'reason':'Credential-like literal'})
    if name.endswith(('.zip','.pptx')):
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            for member in z.namelist():
                if not member.endswith('/'): inspect(name+'!'+member,z.read(member))
    # Shipped runtime dependencies are expected in an installed ASAR, but never in source history.
    source_only=not name.startswith('candidate-assets/node_modules/')
    prohibited=r'(^|/)(?:\.env(?:$|\.(?!example$))|work/|releases/|node_modules/|\.venv/)'
    if (source_only and re.search(prohibited,name)) or re.search(r'(^|/)\.env(?:$|\.(?!example$))|\.(?:sqlite3?|db|exe|msi)$',name):
        findings.append({'file':name,'reason':'Private/runtime/release path'})
objects=git('rev-list','--objects','HEAD').decode().splitlines()
blobs=0
batch=subprocess.run(['git','cat-file','--batch'],input=('\n'.join(line.split(' ',1)[0] for line in objects)+'\n').encode(),stdout=subprocess.PIPE,check=True,cwd=ROOT).stdout
pos=0
for line in objects:
    oid,_,name=line.partition(' ')
    eol=batch.index(b'\n',pos); header=batch[pos:eol].split(); size=int(header[2])
    raw=batch[eol+1:eol+1+size]; pos=eol+size+2
    if header[1]==b'commit': inspect('commit/'+oid,raw)
    if header[1]!=b'blob': continue
    blobs+=1; inspect(name,raw); largest.append({'file':name,'bytes':len(raw)})
for name in git('ls-files','-co','--exclude-standard','-z').decode().split('\0'):
    if name and (ROOT/name).is_file(): inspect(name,(ROOT/name).read_bytes())
for f in (ROOT/'dist').rglob('*'):
    if f.is_file(): inspect(str(f.relative_to(ROOT)).replace('\\','/'),f.read_bytes())
asset_root=os.getenv('BATCHFENCE_AUDIT_ASSETS')
if asset_root:
    for f in Path(asset_root).rglob('*'):
        if f.is_file(): inspect('candidate-assets/'+f.relative_to(asset_root).as_posix(),f.read_bytes())
report={'at':datetime.now(timezone.utc).isoformat(),'head':git('rev-parse','HEAD').decode().strip(),
        'commits':int(git('rev-list','--count','HEAD')),'history_blobs':blobs,'files_and_archive_members':checked,
        'known_private_values_checked':len(needles),'findings':findings,
        'largest_history_files':sorted(largest,key=lambda x:x['bytes'],reverse=True)[:5],
        'limitations':'Known-value and credential-pattern scan, archive contents and prohibited-path checks; not a general security audit. Evidence records are synthetic. Image pixels are not OCR-scanned.'}
out=Path(os.getenv('BATCHFENCE_AUDIT_REPORT_DIR',str(ROOT/'docs/cloud'))); out.mkdir(parents=True,exist_ok=True)
(out/'publication-audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
raise SystemExit(bool(findings))
