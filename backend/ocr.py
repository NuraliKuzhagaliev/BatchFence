"""Bounded local OCR. Output is untrusted and requires visual critical-field review."""
import csv
import hashlib
import io
import os
import shutil
import subprocess
import tempfile
import time
import sys
from pathlib import Path
from pypdf import PdfReader
from .domain import DomainError
from .fixtures import ROOT,document


def scan(raw,filename,synthetic=False,page_count=None):
    from .documents import clean_environment
    engine=shutil.which(os.getenv('TESSERACT_PATH') or 'tesseract')
    renderer=shutil.which(os.getenv('PDFTOPPM_PATH') or 'pdftoppm')
    if not engine or not renderer: raise DomainError('OCR engine unavailable: configure TESSERACT_PATH and PDFTOPPM_PATH on the backend; scanned-source acceptance remains blocked')
    if page_count is None:
        reader=PdfReader(io.BytesIO(raw));page_count=len(reader.pages)
        if any(float(p.mediabox.width)>2000 or float(p.mediabox.height)>2000 for p in reader.pages): raise DomainError('PDF page dimensions exceed supported envelope')
    if not 1<=page_count<=8: raise DomainError('Scanned PDF limit: 8 pages')
    version=subprocess.run([engine,'--version'],capture_output=True,text=True,timeout=5,check=True,env=clean_environment()).stdout.splitlines()[0]
    from .repository import source_root
    folder=Path(os.getenv('OCR_TEMP_PATH') or source_root().parent/'ocr-tmp');folder.mkdir(parents=True,exist_ok=True)
    started=time.monotonic(); blocks=[]; images=[]; words=[]
    # Unique owned temporary directory, removed by the context manager only.
    with tempfile.TemporaryDirectory(prefix='scan-',dir=folder) as tmp:
        source=Path(tmp)/'source.pdf';source.write_bytes(raw)
        for n in range(1,page_count+1):
            remaining=110-(time.monotonic()-started)
            if remaining<=0: raise DomainError('OCR time limit reached; no authoritative records changed')
            output=Path(tmp)/f'page-{n}'
            subprocess.run([sys.executable,'-m','backend.native_worker',renderer,'-f',str(n),'-l',str(n),'-singlefile','-scale-to','1600','-png',str(source),str(output)],capture_output=True,timeout=min(remaining,30),check=True,env=clean_environment())
            png=output.with_suffix('.png').read_bytes()
            if len(png)>4_000_000: raise DomainError('Rendered page exceeds 4 MB')
            subprocess.run([sys.executable,'-m','backend.native_worker',engine,str(output.with_suffix('.png')),str(output),'-l','eng','--psm','6','tsv'],capture_output=True,timeout=min(110-(time.monotonic()-started),30),check=True,env=clean_environment())
            tsv=output.with_suffix('.tsv').read_text(encoding='utf-8')
            if len(tsv)>1_000_000: raise DomainError('OCR coordinate output exceeds supported bound')
            lines={}
            for word in csv.DictReader(io.StringIO(tsv),delimiter='\t'):
                if not word.get('text','').strip(): continue
                key=(word['block_num'],word['par_num'],word['line_num'])
                lines.setdefault(key,[]).append(word['text'])
                words.append({'page':n,'text':word['text'],'box':[int(word[k]) for k in ('left','top','width','height')], 'confidence':float(word['conf'])})
            for i,text in enumerate(lines.values()): blocks.append({'id':f'page-{n}-line-{i+1}','page':n,'text':' '.join(text)})
            images.append({'page':n,'raw':png,'hash':hashlib.sha256(png).hexdigest()})
    text='\n'.join(b['text'] for b in blocks)
    if not text.strip() or len(text)>80_000: raise DomainError('OCR returned empty or excessive text; original page review required')
    doc=document(filename,text.encode(),synthetic=synthetic)
    doc.update(media_type='application/pdf',original_hash=hashlib.sha256(raw).hexdigest(),blocks=blocks,
               ocr={'engine':version,'language':'eng','elapsed_ms':round((time.monotonic()-started)*1000),
                    'critical_fields_confirmed':False,'pages':[{'page':p['page'],'image_hash':p['hash']} for p in images],
                    'words':words,'coordinates':'pixels in retained page PNG; top-left origin','fallible':True})
    return doc,images


def require_visual_review(doc):
    if doc.get('ocr') and not doc['ocr'].get('critical_fields_confirmed'):
        raise DomainError('Visually confirm critical identifiers, quantities and completeness against every scanned page before narrowing or recovery')
