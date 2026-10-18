import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import uuid
from pathlib import Path
from . import repository as repo,jobs
from .domain import DomainError,digest
from .fixtures import document

document_slot=threading.BoundedSemaphore(1)


def render_page(raw,number):
    import shutil
    renderer=shutil.which(os.getenv('PDFTOPPM_PATH') or 'pdftoppm')
    if not renderer:raise DomainError('PDF renderer unavailable; inspect the retained original externally')
    if not 1<=number<=8 or not raw.startswith(b'%PDF-'):raise DomainError('Unsupported original PDF page')
    if not document_slot.acquire(timeout=2):raise DomainError('Another document operation is running; try the page preview after it finishes')
    try:
        folder=repo.source_root().parent/'ocr-tmp';folder.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='preview-',dir=folder) as tmp:
            source=Path(tmp)/'source.pdf';output=Path(tmp)/'page';source.write_bytes(raw)
            subprocess.run([sys.executable,'-m','backend.native_worker',renderer,'-f',str(number),'-l',str(number),'-singlefile','-scale-to','1200','-png',str(source),str(output)],capture_output=True,timeout=20,check=True,env=clean_environment())
            image=output.with_suffix('.png').read_bytes()
            if len(image)>4_000_000:raise DomainError('Page preview exceeds supported bound')
            return image
    except (OSError,subprocess.SubprocessError):raise DomainError('Original PDF could not be rendered within its time limit; no source changed')
    finally:document_slot.release()


def clean_environment():
    allowed=('PATH','SYSTEMROOT','WINDIR','TEMP','TMP','TESSDATA_PREFIX')
    return {k:v for k,v in os.environ.items() if k.upper() in allowed}|{'PYTHONUTF8':'1','LANG':'C.UTF-8'}


def process_pdf(raw,filename,synthetic,owner,case_id,factory):
    if not document_slot.acquire(blocking=False):raise DomainError('Another document parser is running; retry after it finishes')
    key='DOCUMENT-'+uuid.uuid4().hex;started=False
    try:
        with repo.write(factory) as db:
            jobs.start(db,owner,key,'document_processing',{'case_id':case_id,'source_hash':hashlib.sha256(raw).hexdigest()},'local-parser')
            started=True
        folder=repo.source_root().parent/'ocr-tmp';folder.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='pdf-',dir=folder) as tmp:
            source=Path(tmp)/'source.pdf';output=Path(tmp)/'text.json';source.write_bytes(raw)
            subprocess.run([sys.executable,'-m','backend.pdf_worker',str(source),str(output)],capture_output=True,timeout=25,check=True,env=clean_environment())
            pages=json.loads(output.read_text(encoding='utf-8'))['pages']
        if any(not p.strip() for p in pages):
            from .ocr import scan
            doc,images=scan(raw,filename,synthetic,page_count=len(pages))
        else:
            doc=document(filename,'\n'.join(pages).encode(),synthetic=synthetic);images=[]
            doc['blocks']=[{'id':f'page-{i+1}-line-{j+1}','page':i+1,'text':line} for i,p in enumerate(pages) for j,line in enumerate(p.splitlines()) if line.strip()]
            doc.update(media_type='application/pdf',original_hash=hashlib.sha256(raw).hexdigest(),page_count=len(pages))
        with repo.write(factory) as db:
            if not jobs.finish(db,owner,key,'succeeded',digest(doc)):raise DomainError('Document processing cancelled or interrupted; result not accepted')
        return doc,images
    except Exception as exc:
        if started:
            with repo.write(factory) as db:jobs.finish(db,owner,key,'failed',digest({'failure':type(exc).__name__}))
        if isinstance(exc,DomainError):raise
        raise DomainError('PDF parser exceeded limits or could not read the document; no partial source accepted')
    finally:document_slot.release()
