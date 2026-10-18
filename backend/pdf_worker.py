"""Parse bounded PDF text in a credential-free subprocess, not the web worker."""
import os
import sys
import json
from pathlib import Path
if os.name!='nt':
    import resource
    resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))
    resource.setrlimit(resource.RLIMIT_CPU,(20,20))
    resource.setrlimit(resource.RLIMIT_FSIZE,(2*1024*1024,2*1024*1024))
from pypdf import PdfReader
source=Path(sys.argv[1]).read_bytes()
if not source.startswith(b'%PDF-'):raise ValueError('PDF signature does not match filename')
reader=PdfReader(sys.argv[1])
if reader.is_encrypted:raise ValueError('Encrypted PDF is not supported')
if not 1<=len(reader.pages)<=8:raise ValueError('PDF page limit: 8; no pages silently omitted')
pages=[]
for page in reader.pages:
    if float(page.mediabox.width)>2000 or float(page.mediabox.height)>2000:raise ValueError('PDF page dimensions')
    text=page.extract_text() or ''
    pages.append(text)
    if sum(len(p) for p in pages)>80000:raise ValueError('PDF text limit')
Path(sys.argv[2]).write_text(json.dumps({'pages':pages}),encoding='utf-8')
