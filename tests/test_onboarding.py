import base64
import copy
from datetime import datetime,timezone
import pytest
from backend import onboarding,ocr,app as module
from backend.domain import DomainError
from backend.fixtures import load_demo
from tests.test_api import client,post


def metadata(): return {'unit':'piece','timezone':'UTC','observed_at':datetime.now(timezone.utc).isoformat(),'source_revision':'customer-1','synthetic':True}
def raw_inventory(): return b'Row,Pool,Qty,Cents,State,Complete,Site,Product\nCUSTOM-1,FG-A,240,4000,available,true,NORTH-01,Decorative housing\n'
def mapping(): return dict(zip(onboarding.FIELDS['inventory'],['Row','Pool','Qty','Cents','State','Complete','Site','Product']))


def test_mapping_errors_and_bad_rows_have_no_authority(client):
    state=post(client,'/api/cases/demo'); route='/api/cases/'+state['id']
    raw=raw_inventory().replace(b',240,',b',not-a-number,')
    proposal=post(client,route+'/intake-preview',{'filename':'customer.csv','content_base64':base64.b64encode(raw).decode(),'kind':'inventory','mapping':mapping(),'metadata':metadata()})
    assert proposal['errors'][0]['row']==2
    assert client.get(route).json()==state
    assert client.post(route+'/intake-review',json={'proposal_id':proposal['id'],'reviewed':True,'note':'Review cannot authorize a malformed numeric row.'}).status_code==422
    assert client.get(route).json()==state


def test_full_mapping_review_profiles_stale_and_original_bytes(client):
    state=post(client,'/api/cases/demo'); route='/api/cases/'+state['id']
    raw=(module.ROOT/'fixtures/demo/inventory.csv').read_bytes()
    full={f:f for f in onboarding.FIELDS['inventory']}
    args={'filename':'customer.csv','content_base64':base64.b64encode(raw).decode(),'kind':'inventory','mapping':full,'metadata':metadata()}
    proposal=post(client,route+'/intake-preview',args)
    assert not proposal['errors']
    result=post(client,route+'/intake-review',{'proposal_id':proposal['id'],'reviewed':True,'note':'Checked units, column mapping and original customer rows.','profile_name':'Customer inventory'})
    assert result['pending_revision'] and result['pending_data']['stocks']
    assert result['plan'] is None and result['stocks']==state['stocks']
    assert client.get('/api/sources/'+proposal['original_hash']).content==raw
    assert client.get('/api/intake/profiles').json()['profiles'][0]['name']=='Customer inventory'
    assert client.post(route+'/intake-review',json={'proposal_id':proposal['id'],'reviewed':True,'note':'Second approval is not allowed for this preview.'}).status_code==422


def test_cycles_unknown_entities_overflow_and_units():
    state=load_demo(); meta=metadata()
    with pytest.raises(DomainError,match='discrete'): onboarding.preview(state,raw_inventory(),'x.csv','inventory',mapping(),{**meta,'unit':'kg'})
    rows=b'row_id,source,target,kind\nX,UNKNOWN,FG-A,confirmed\n'
    result=onboarding.preview(state,rows,'lineage.csv','lineage',{k:k for k in onboarding.FIELDS['lineage']},meta)
    assert 'Unknown' in result['errors'][0]['message']
    rows=b'row_id,source,target,kind\nX,SUP-A,MIX,confirmed\nY,MIX,SUP-A,confirmed\n'
    result=onboarding.preview(state,rows,'lineage.csv','lineage',{k:k for k in onboarding.FIELDS['lineage']},meta)
    assert 'cycle' in result['errors'][0]['message']
    rows=b'row_id,order_id,pool_id,units,due_date,status\nA,O-1,FG-A,241,2026-10-20,open\n'
    result=onboarding.preview(state,rows,'a.csv','allocations',{k:k for k in onboarding.FIELDS['allocations']},meta)
    assert 'exceed' in result['errors'][0]['message']


def test_inspection_metric_duplicates_denominators_and_correction(client):
    state=post(client,'/api/cases/demo');route='/api/cases/'+state['id']
    header=','.join(onboarding.FIELDS['inspections'])+'\n'
    row='OBS-1,2026-10-10T09:00:00Z,NORTH-01,Decorative housing,coating,visual-v1,steady,500,10,cosmetic,FG-A,nonconforming_units\n'
    def preview(text):return post(client,route+'/intake-preview',{'filename':'inspection.csv','content_base64':base64.b64encode(text.encode()).decode(),'kind':'inspections','mapping':{f:f for f in onboarding.FIELDS['inspections']},'metadata':metadata()})
    assert preview(header+row.replace('nonconforming_units','defect_count'))['errors']
    assert preview(header+row+row)['errors']
    assert preview(header+row.replace(',500,10,',',0,10,'))['errors']
    first=preview(header+row)
    post(client,route+'/intake-review',{'proposal_id':first['id'],'reviewed':True,'note':'Reviewed original source and inspection denominator.'})
    second=preview(header+row.replace(',500,10,',',500,12,'))
    post(client,route+'/intake-review',{'proposal_id':second['id'],'reviewed':True,'note':'Source correction replaces the prior observation explicitly.'})
    saved=client.get('/api/inspections').json()
    assert saved['revision']==2 and saved['rows'][0]['nonconforming']==12
    assert saved['history'][0]['prior']['nonconforming']==10 and saved['changed_ids']==['OBS-1']


def test_unconfirmed_ocr_cannot_narrow_and_engine_absence_explicit(monkeypatch):
    doc={'ocr':{'critical_fields_confirmed':False}}
    with pytest.raises(DomainError,match='Visually'): ocr.require_visual_review(doc)
    doc['ocr']['critical_fields_confirmed']=True;ocr.require_visual_review(doc)
    monkeypatch.setattr(ocr.shutil,'which',lambda _:None)
    with pytest.raises(DomainError,match='engine unavailable'):ocr.scan(b'not parsed without engine','scan.pdf')
