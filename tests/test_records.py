import base64
import json
from pypdf import PdfWriter
from backend.domain import calculate
from backend.fixtures import load_demo
from .test_api import prepare, approve, payload, post, review, client


def encode(text):
    return base64.b64encode(text.encode()).decode()


def test_unsupported_inputs_keep_case_unchanged(client):
    s = prepare(client)
    route = f"/api/cases/{s['id']}/documents"
    for data in [
        {'filename':'input.exe','content_base64':encode('x')},
        {'filename':'input.csv','content_base64':encode('wrong,columns\nx,y')},
        {'filename':'input.txt','content_base64':'%%%'},
        {'filename':'input.pdf','content_base64':encode('not a pdf')},
    ]:
        assert client.post(route,json=data).status_code == 422
    current = client.get(f"/api/cases/{s['id']}").json()
    assert current['revision'] == 1 and current['plan']['digest'] == s['plan']['digest']


def test_image_pdf_has_clear_unsupported_result(client):
    import io
    writer = PdfWriter()
    writer.add_blank_page(width=300,height=200)
    raw = io.BytesIO()
    writer.write(raw)
    s = post(client,'/api/cases/demo')
    r = client.post(f"/api/cases/{s['id']}/documents",json={'filename':'scan.pdf','content_base64':base64.b64encode(raw.getvalue()).decode()})
    assert r.status_code == 422 and r.json()['detail']['code'] == 'OCR_UNSUPPORTED'


def test_narrower_review_never_releases_existing_hold(client):
    s = approve(client,prepare(client))
    s = post(client,f"/api/cases/{s['id']}/apply",payload(s))
    header = 'row_id,source,target,kind,revision,timestamp\n'
    lines = [
        'L1,SUP-A,FG-A,confirmed,2,2026-10-16T01:00:00Z',
        'L2,SUP-A,FG-B,confirmed,2,2026-10-16T01:00:00Z',
        'L3,SUP-B,FG-C,confirmed,2,2026-10-16T01:00:00Z',
        'L4,SUP-C,FG-D,confirmed,2,2026-10-16T01:00:00Z',
        'L5,SUP-D,FG-E,confirmed,2,2026-10-16T01:00:00Z',
        'L6,SUP-E,FG-F,confirmed,2,2026-10-16T01:00:00Z'
    ]
    s = post(client,f"/api/cases/{s['id']}/documents",{'filename':'resolved-lineage.csv','content_base64':encode(header+'\n'.join(lines)),'synthetic':True})
    # Current inventory is explicitly reviewed complete after receiving identity resolution.
    stock_header = 'row_id,pool_id,units,unit_cents,status,ancestry_complete,site,product_family\n'
    stock_rows = '\n'.join(f"{p['row_id']},{p['id']},{p['units']},{p['unit_cents']},available,true,{p['site']},Decorative housing" for p in s['stocks'])
    s = post(client,f"/api/cases/{s['id']}/documents",{'filename':'resolved-inventory.csv','content_base64':encode(stock_header+stock_rows),'synthetic':True})
    s = review(client,s)
    assert s['plan']['result']['hold_units'] == 400
    assert next(p for p in s['stocks'] if p['id']=='FG-C')['status'] == 'held'
    s = approve(client,s)
    s = post(client,f"/api/cases/{s['id']}/apply",payload(s,'new-narrower-request'))
    assert next(p for p in s['stocks'] if p['id']=='FG-C')['status'] == 'held'


def test_completeness_flag_cannot_replace_missing_relation():
    s = load_demo()
    s['edges'] = [e for e in s['edges'] if e['target']!='FG-D']
    result = calculate(s['stocks'],s['edges'],['SUP-A'],s['allocations'])
    assert next(r for r in result['rows'] if r['id']=='FG-D')['classification']=='uncertain'


def test_malformed_packet_records_fail_before_promotion(client):
    from backend.domain import digest
    s = prepare(client)
    packet = client.get(f"/api/cases/{s['id']}/export").json()
    packet['case']['stocks'][0]['complete'] = 'false'
    packet['integrity_hash'] = digest(packet['case'])
    r = client.post('/api/cases/import',json=packet)
    assert r.status_code == 422 and r.json()['detail']['code'] == 'PACKET_INVALID'


def test_multiline_csv_evidence_cites_entire_record(client):
    s = prepare(client)
    raw = 'row_id,source,target,kind,note\nL1,SUP-A,FG-A,confirmed,"Reviewed first line\nand second line"\nL2,SUP-A,FG-B,confirmed,reviewed\nL3,SUP-A,FG-C,possible,unresolved\nL4,SUP-B,FG-C,possible,unresolved\nL5,SUP-C,FG-D,confirmed,reviewed\nL6,SUP-D,FG-E,confirmed,reviewed\nL7,SUP-E,FG-F,confirmed,reviewed'
    s = post(client,f"/api/cases/{s['id']}/documents",{'filename':'multiline.csv','content_base64':encode(raw),'synthetic':True})
    d = s['documents'][-1]
    assert len(d['blocks']) == 8 and '\nand second line"' in d['blocks'][1]['text']
    s = review(client,s)
    edge = next(e for e in s['edges'] if e['target']=='FG-A')
    assert edge['evidence']['quote'] == d['blocks'][1]['text']
    assert s['plan']['result']['hold_units'] == 500


def test_text_pdf_intake_preserves_extractable_notice(client):
    # Small independently authored text PDF, without a PDF-generation dependency.
    stream=b'BT /F1 12 Tf 30 100 Td (Affected lots: SUP-Q) Tj ET'
    objects=[
      b'<< /Type /Catalog /Pages 2 0 R >>',
      b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
      b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
      b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
      b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream'
    ]
    raw=b'%PDF-1.4\n';offsets=[0]
    for i,obj in enumerate(objects,1):
        offsets.append(len(raw));raw+=str(i).encode()+b' 0 obj\n'+obj+b'\nendobj\n'
    xref=len(raw);raw+=b'xref\n0 6\n0000000000 65535 f \n'
    raw+=b''.join(f'{n:010d} 00000 n \n'.encode() for n in offsets[1:])
    raw+=b'trailer\n<< /Root 1 0 R /Size 6 >>\nstartxref\n'+str(xref).encode()+b'\n%%EOF'
    s=post(client,'/api/cases/demo')
    s=post(client,f"/api/cases/{s['id']}/documents",{'filename':'fresh.pdf','content_base64':base64.b64encode(raw).decode(),'synthetic':True})
    d=s['documents'][-1]
    assert d['media_type']=='application/pdf'
    assert any('Affected lots: SUP-Q' in b['text'] for b in d['blocks'])
