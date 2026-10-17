"""New local adversarial regressions; no inference or independent human claims."""
import copy
from datetime import datetime,timezone
import pytest
from backend import signals,assisted,knowledge,label_images,repository as repo
from backend.domain import DomainError,digest
from backend.fixtures import document,load_demo
from backend.review_safety import scope_concerns
from backend.scope_proposals import validate_proposals
from tests.test_api import client,post,review,approve,payload
from tests.test_continuation import upload

@pytest.mark.parametrize('caveat',[
 'This is not a complete incident list.',
 'The entire affected scope has not been established.',
 'The incident boundary remains open.',
 'This list is illustrative, not exhaustive.',
])
def test_explicit_incomplete_scope_cannot_support_complete_proposal(caveat):
 d=document('new-notice.txt',('Affected lots: SUP-A. '+caveat).encode())
 assert scope_concerns(d), 'Explicit incompleteness must be visible at source review'
 e={'document_id':d['id'],'block_id':d['blocks'][0]['id'],'quote':d['blocks'][0]['text']}
 with pytest.raises(ValueError):validate_proposals({'facts':[],'qualifiers':[],'scope_status':'complete','scope_evidence':[e]},[d])

def row(key,when,n=1000,bad=100):
 return {'observation_id':key,'event_time':when,'inspected':n,'nonconforming':bad,'site':'s','product':'p','process':'coat','method':'visual','regime':'stable','defect':'cosmetic','metric':'nonconforming_units','source':'synthetic original inspection'}

def test_signal_period_uses_instants_not_timestamp_spelling():
 # Actual order: B=00:00Z, A=01:00Z, F=02:00Z. Lexical order differs.
 rows=[row('A','2026-10-01T03:00:00+02:00'),row('B','2026-10-01T00:00:00Z'),row('F','2026-10-01T01:00:00-01:00',bad=300)]
 b=signals.freeze(rows,['A','B'],{'min_observations':2,'min_inspected':2000,'min_expected':5,'sigma':3})
 assert [r['observation_id'] for r in b['rows']]==['B','A']
 result=signals.chart(b,rows)
 assert result['alerts']==['F']
 assert result['points'][0]['upper']==pytest.approx(.1+3*(.1*.9/1000)**.5)

@pytest.mark.parametrize('statement',[None,1,[],{'fact_id':[],'text':'safe'},{'fact_id':'f','text':None}])
def test_malformed_handover_becomes_domain_rejection(statement):
 with pytest.raises(DomainError):assisted.validate_handover({'facts':[{'id':'f','text':'safe'}],'required_fact_ids':['f']},{'statements':[statement]})

def test_label_prefix_is_not_an_exact_document_identity(tmp_path,monkeypatch):
 monkeypatch.setenv('DEPLOYMENT_PROFILE','local');s=load_demo();d=document('different-lot.txt',b'Supplier lot SUP-0019.')
 s['documents'].append(d);factory=lambda:repo.connect(tmp_path/'label.sqlite',url='')
 with repo.write(factory) as db:
  repo.put_record(db,'test','label','LABEL-1',{'id':'LABEL-1','case_id':s['id'],'reading':{'candidates':['SUP-001'],'unreadable':False,'unresolved_characters':[]}},0)
  with pytest.raises(DomainError):label_images.review_label(db,'test',s,'LABEL-1',d['id'],d['blocks'][0]['text'],'SUP-001',True,True,False,'Agent-operated adversarial association check')

@pytest.mark.parametrize('field,value',[('version',True),('page',True),('page',0)])
def test_procedure_rejects_boolean_versions_and_invalid_pages(field,value):
 d={'id':'Q-1','version':1,'status':'approved','valid_from':'2026-01-01T00:00:00Z','valid_to':None,'products':['p'],'processes':['coat'],'owner':'quality','passages':[{'id':'P1','text':'Keep the original caveat; review before any release.','page':1}],'synthetic':True}
 if field=='version':d[field]=value
 else:d['passages'][0][field]=value
 d['source_hash']=digest(d['passages'])
 with pytest.raises(DomainError):knowledge.validate_document(d)

@pytest.mark.parametrize('raw',[
 b'row_id,source,target,kind,kind\nX,SUP-A,FG-A,possible,confirmed',
 b'row_id,source,target,kind\nX,SUP-A,FG-A,confirmed,unexpected',
 b'row_id,source,target,kind\nX,SUP-A,FG-A',
])
def test_csv_never_silently_overwrites_duplicate_or_missing_fields(raw):
 with pytest.raises(DomainError):document('ambiguous-columns.csv',raw)

def test_whitespace_upload_rejected_without_invalidating_applied_receipt(client):
 import base64
 s=approve(client,review(client,post(client,'/api/cases/demo')));route='/api/cases/'+s['id'];s=post(client,route+'/apply',payload(s,'whitespace-before'))
 before=copy.deepcopy(s)
 assert client.post(route+'/documents',json={'filename':'empty-notice.txt','content_base64':base64.b64encode(b' \r\n\t').decode(),'synthetic':True}).status_code==422
 assert client.get(route).json()==before

def test_review_cannot_override_explicitly_incomplete_receiving_source(client):
 s=approve(client,review(client,post(client,'/api/cases/demo')));route='/api/cases/'+s['id'];s=post(client,route+'/apply',payload(s,'incomplete-before'))
 q=next(q for q in s['plan']['result']['requests'] if q['pool_ids']==['FG-C'])
 text='FG-C may contain SUP-B. Complete ancestry is unconfirmed; other parents remain unknown.'
 s=upload(client,s,text,request_id=q['id']);doc=s['documents'][-1]
 body={'revision':s['revision'],'document_id':doc['id'],'review_path':'structured_record','pool_id':'FG-C','parent_ids':['SUP-B'],'complete':True,'quote':text,'superseded_row_ids':['LIN-3','LIN-4'],'unresolved_contradictions':False,'outcome':'resolved','reviewed':True,'replacement_reviewed':True,'completeness_confirmed':True,'note':'Adversarial agent review cannot manufacture missing receiving evidence.'}
 assert client.post(route+'/receiving-review',json=body).status_code==422
 saved=client.get(route).json();assert saved['receipts']==s['receipts'] and saved['pending_revision']

def test_complete_quote_cannot_omit_later_critical_caveat():
 d=document('late-caveat.txt',b'The complete incident list is SUP-A.\nScope remains unknown pending laboratory results.')
 e={'document_id':d['id'],'block_id':d['blocks'][0]['id'],'quote':d['blocks'][0]['text']}
 with pytest.raises(ValueError):validate_proposals({'facts':[],'qualifiers':[],'scope_status':'complete','scope_evidence':[e]},[d])
