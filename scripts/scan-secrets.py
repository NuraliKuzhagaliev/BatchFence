from pathlib import Path
import json
import re
import subprocess
ROOT=Path(__file__).resolve().parents[1]
tracked=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')
patterns=[re.compile(r'sk-(?:proj-)?[A-Za-z0-9_-]{24,}'),re.compile(r'hf_[A-Za-z0-9]{24,}'),re.compile(r'Bearer\s+[A-Za-z0-9_=/+-]{24,}')]
findings=[]
checked=0
files=[ROOT/f for f in tracked if f]+list((ROOT/'dist').rglob('*'))
for f in files:
 if not f.is_file():continue
 if f.name=='.env' or (f.name.startswith('.env.') and f.name!='.env.example'):
  findings.append({'file':str(f.relative_to(ROOT)),'reason':'Private environment file in delivery list'});continue
 try:text=f.read_text(encoding='utf-8-sig')
 except (UnicodeError,OSError):continue
 checked+=1
 for i,pattern in enumerate(patterns):
  if pattern.search(text):findings.append({'file':str(f.relative_to(ROOT)),'reason':'Credential-like token pattern '+str(i+1)})
for f in [ROOT/'docs/verified-decision-packet.json',ROOT/'docs/desktop-decision-packet.json',ROOT/'submission/demo-decision-packet.json']:
 if f.exists() and any(k in f.read_text() for k in ['bf_session','x-bf-session','AMD_API_KEY']):
  findings.append({'file':str(f.relative_to(ROOT)),'reason':'Forbidden session/credential field in packet'})
result={'checked_text_files':checked,'findings':findings,'scope':'Tracked source and built frontend plus delivered packets. Pattern scan does not prove absence of every possible secret.'}
(ROOT/'docs/secret-scan.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
if findings:raise SystemExit(1)
