"""Create disclosed raster-only test pages; requires Pillow and ReportLab."""
from pathlib import Path
import hashlib,json
from PIL import Image,ImageDraw,ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
root=Path(__file__).resolve().parents[1]
out=root/'fixtures/enterprise/ocr';out.mkdir(parents=True,exist_ok=True)
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',42)
pages=[['SYNTHETIC ENGINEERING TEST — NOT SUPPLIER EVIDENCE','Supplier notice revision 1','Affected lots: SUP-A.','Complete supplier scope: SUP-A only.','Warehouse ancestry remains a separate question.'],
       ['SYNTHETIC ENGINEERING TEST — NOT INSPECTION PROOF','Inspection record INS-100','FG-C: 100 pieces inspected; 0 nonconforming.','Method: visual-v1. Result: passed.','Receiving record REC-812 identifies supplier lot SUP-B.']]
pdf=canvas.Canvas(str(out/'raster-only-notice.pdf'),pagesize=(900,700))
for n,lines in enumerate(pages,1):
    image=Image.new('RGB',(1800,1400),'white');draw=ImageDraw.Draw(image)
    for i,line in enumerate(lines):draw.text((75,100+i*155),line,fill='black',font=font)
    image.save(out/f'input-page-{n}.png')
    pdf.drawImage(ImageReader(image),0,0,width=900,height=700);pdf.showPage()
pdf.save()
(out/'provenance.json').write_text(json.dumps({'provenance':'Programmatically generated raster-only synthetic engineering fixture; no real supplier or inspection claim','expected_pages':pages,'pdf_sha256':hashlib.sha256((out/'raster-only-notice.pdf').read_bytes()).hexdigest()},indent=2),encoding='utf-8')
print('Created two raster-only synthetic pages on D:')
