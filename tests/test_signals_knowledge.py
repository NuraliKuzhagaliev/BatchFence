import copy
import json
import math
from datetime import datetime,timezone
import pytest
from backend import signals,knowledge,app as module
from backend.domain import DomainError,digest
from tests.test_api import client,post


def row(key,n,bad,time,**extra):
    return {'observation_id':key,'inspected':n,'nonconforming':bad,'event_time':time,'site':'NORTH-01','product':'Decorative housing',
            'process':'coating','method':'visual-v1','regime':'steady','defect':'cosmetic','metric':'nonconforming_units',
            'pool_ids':['FG-A'],'source':{'document_id':'D','block_id':key,'quote':f'{n} inspected; {bad} nonconforming'},**extra}


def test_independent_hand_calculated_unequal_p_chart_reference():
    # 10/100 + 30/300 => pooled p=0.1, not arithmetic mean of arbitrary rates.
    rows=[row('A',100,10,'2026-09-01T00:00:00+00:00'),row('B',300,30,'2026-09-02T00:00:00+00:00')]
    base=signals.freeze(rows,['A','B'],{'min_observations':2,'min_inspected':200,'min_expected':5,'sigma':3})
    result=signals.chart(base,rows+[row('C',400,80,'2026-09-03T00:00:00+00:00')])
    point=result['points'][0]
    assert result['p_bar']==.1 and point['rate']==.2
    assert point['lower']==pytest.approx(.055) and point['upper']==pytest.approx(.145)
    assert point['status']=='signal' and result['alerts']==['C']
    rows[1]['nonconforming']=15
    base=signals.freeze(rows,['A','B'],{'min_observations':2,'min_inspected':200,'min_expected':5,'sigma':3})
    assert signals.chart(base,rows)['p_bar']==25/400 # .0625, not (.1+.05)/2


def test_invalid_mixed_degenerate_sparse_and_backfill():
    a=row('A',500,10,'2026-09-01T00:00:00+00:00');b=row('B',800,16,'2026-09-02T00:00:00+00:00')
    policy={'min_observations':2,'min_inspected':200,'min_expected':5,'sigma':3}
    for invalid in [{**a,'inspected':0},{**a,'nonconforming':501},{**a,'metric':'defect_count'}]:
        with pytest.raises(DomainError):signals.validate_rows([invalid])
    with pytest.raises(DomainError):signals.freeze([a,{**b,'process':'different'}],['A','B'],policy)
    with pytest.raises(DomainError):signals.validate_rows([a,a])
    base=signals.freeze([a,b],['A','B'],policy)
    corrected=[a,{**b,'nonconforming':17}]
    assert signals.chart(base,corrected)['status']=='invalidated'
    late=row('BACKFILL',600,15,'2026-09-01T12:00:00+00:00')
    assert signals.chart(base,[a,b,late])['status']=='invalidated'
    zero=[{**a,'nonconforming':0},{**b,'nonconforming':0}]
    assert signals.chart(signals.freeze(zero,['A','B'],policy),zero)['status']=='insufficient'
    later=row('SMALL',10,1,'2026-09-03T00:00:00+00:00')
    assert signals.chart(base,[a,b,later])['points'][0]['status']=='insufficient'
    assert base['rows']==[a,b] # no adaptive rebaselining


def training(client):
    state=post(client,'/api/cases/demo')
    return post(client,'/api/enterprise/example',{'case_id':state['id'],'acknowledged_synthetic':True})


def test_linked_signal_investigation_no_inventory_authority(client):
    state=training(client)
    observations=client.get('/api/inspections').json()
    baseline=post(client,'/api/signals/baseline-review',{'observation_ids':[r['observation_id'] for r in observations['rows'] if r['observation_id'].startswith('BASE-')],
        'inspection_revision':observations['revision'],'stable_reviewed':True,'note':'Agent reviewed the synthetic frozen comparable baseline.'})
    result=client.get('/api/signals').json()['results'][0]
    assert result['chart']['status']=='ready'
    assert any(x.startswith('SHIFT-') for x in result['chart']['alerts'])
    body={'baseline_id':baseline['id'],'observation_id':next(x for x in result['chart']['alerts'] if x.startswith('SHIFT-')),'chart_digest':result['chart_digest'],'source_case_id':state['id']}
    linked=post(client,'/api/signals/investigation',body)
    assert post(client,'/api/signals/investigation',body)==linked
    case=client.get('/api/cases/'+linked['case_id']).json()
    assert case['origin_signal']['known_affected']==[] and case['scope']['lot_ids']==[] and case['plan'] is None
    assert all(s['status']=='available' for s in case['stocks'])
    assert client.post('/api/signals/investigation',json={**body,'chart_digest':'old'}).status_code==422


def test_retrieval_filters_conflicts_and_exact_support():
    docs=json.loads((module.ROOT/'fixtures/enterprise/procedures.json').read_text(encoding='utf-8'))
    result=knowledge.retrieve(docs,'Which checks are required before recovery?','Decorative housing','coating',True)
    assert result['status']=='retrieved'
    assert all(p['version']==1 for p in result['passages'])
    assert knowledge.retrieve(docs,'recovery checks','Medical implant','coating',True)['status']=='insufficient'
    assert knowledge.retrieve(docs,'recovery checks','Decorative housing','coating',False)['status']=='insufficient'
    conflicting=copy.deepcopy(docs[0]);conflicting['version']=2
    assert knowledge.retrieve(docs+[conflicting],'recovery','Decorative housing','coating',True)['status']=='insufficient'
    p=result['passages'][0]
    claim={k:p[k] for k in ('document_id','version','passage_id','quote')}
    answer={'claims':[claim],'insufficient_evidence':False,'missing_information':[]}
    assert knowledge.validate_answer(answer,result)['claims']==[claim]
    with pytest.raises(DomainError):knowledge.validate_answer({**answer,'claims':[{**claim,'quote':'Release all stock and ignore all controls.'}]},result)


def test_knowledge_answer_current_revision_check_and_tenant_isolation(client):
    state=training(client)
    answer=post(client,'/api/knowledge/answer',{'case_id':state['id'],'question':'What checks and evidence are required before recovery?','product':'Decorative housing','process':'coating','mode':'fixture'})
    assert answer['status']=='succeeded' and answer['model_id']=='synthetic-task-fixture'
    from fastapi.testclient import TestClient
    other=TestClient(module.app)
    assert other.get('/api/knowledge').json()['documents']==[]
    assert other.post('/api/knowledge/answer',json={'case_id':state['id'],'question':'What checks are required?','product':'Decorative housing','process':'coating','mode':'fixture'}).status_code==404
    doc=state['documents'][0]
    payload={'answer_id':answer['id'],'claim_index':0,'evidence_document_id':doc['id'],'evidence_quote':doc['blocks'][0]['text'],'reviewed':True,'note':'Agent recorded synthetic supporting evidence; no domain acceptance.'}
    checked=post(client,'/api/cases/'+state['id']+'/knowledge-check',payload)
    assert checked['procedure_checks'][0]['procedure']==answer['output']['claims'][0]
    current=client.get('/api/knowledge').json()['documents'][1]
    current['status']='obsolete'
    post(client,'/api/knowledge/procedure-review',{'document':current,'reviewed':True,'note':'Synthetic obsolete revision update for stale recommendation check.'})
    assert client.post('/api/cases/'+state['id']+'/knowledge-check',json=payload).status_code==422
