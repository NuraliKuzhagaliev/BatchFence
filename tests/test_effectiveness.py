import base64
import copy
from datetime import datetime,timezone
import pytest
from backend import effectiveness,repository as repo,app as module
from backend.domain import DomainError
from tests.test_api import client,post
from tests.test_signals_knowledge import training,row


def test_predeclared_comparison_insufficient_window_missing_and_confounded():
    base=[row('B1',500,20,'2026-09-01T00:00:00+00:00'),row('B2',500,20,'2026-09-02T00:00:00+00:00')]
    group={k:base[0][k] for k in effectiveness.GROUP}
    plan=effectiveness.freeze_plan(base,['B1','B2'],group,'2026-09-04T00:00:00+00:00','2026-09-05T00:00:00+00:00',1000,2,.02,True)
    action={'plan':plan,'implementation':{'evidence':'synthetic reference'}}
    follow=[row('F1',500,5,'2026-09-04T01:00:00+00:00'),row('F2',500,5,'2026-09-04T02:00:00+00:00')]
    result=effectiveness.evaluate(action,base+follow,datetime(2026,9,6,tzinfo=timezone.utc))
    assert result['status']=='criteria_met' and result['baseline']['rate']==.04 and result['followup']['rate']==.01
    assert result['followup']['wilson_95'][0]<.01<result['followup']['wilson_95'][1]
    assert effectiveness.evaluate(action,base+follow,datetime(2026,9,4,tzinfo=timezone.utc))['status']=='inconclusive'
    assert effectiveness.evaluate(action,base+follow[:1])['status']=='inconclusive'
    assert effectiveness.evaluate(action,base+[follow[0],{**follow[1],'regime':'changed'}])['status']=='inconclusive'
    changed=copy.deepcopy(base);changed[0]['nonconforming']=30
    assert effectiveness.evaluate(action,changed+follow)['status']=='inconclusive'
    with pytest.raises(DomainError):effectiveness.freeze_plan(base,['B1','B2'],group,plan['start'],plan['end'],1000,2,.02,False)
    posthoc=effectiveness.freeze_plan(base+follow,['B1','B2'],group,plan['start'],plan['end'],1000,2,.02,True)
    assert effectiveness.evaluate({'plan':posthoc,'implementation':True},base+follow)['status']=='inconclusive'


def test_action_full_lifecycle_insufficient_followup_and_recurrence(client):
    c=client;state=training(c);case_route='/api/cases/'+state['id']
    observations=c.get('/api/inspections').json();group={k:observations['rows'][0][k] for k in effectiveness.GROUP}
    baseline=post(c,'/api/signals/baseline-review',{'observation_ids':[r['observation_id'] for r in observations['rows'] if r['observation_id'].startswith('BASE-')],
        'inspection_revision':observations['revision'],'stable_reviewed':True,'note':'Agent reviewed frozen synthetic baseline for workflow verification.'})
    action=post(c,'/api/actions/create',{'case_id':state['id'],'title':'Improve receipt verification for cosmetic coating material','owner':'Synthetic quality owner','due_date':'2026-10-20','supplier_id':'SUP-A','product':'Decorative housing','process':'coating','defect':'cosmetic'})
    source=next(d for d in state['documents'] if 'supplier_notice' in d['filename'])
    action=post(c,'/api/actions/'+action['id']+'/investigation-review',{'revision':action['revision'],'cause':'Receiving verification may have missed incomplete supplier ancestry.','cause_accepted':False,
        'document_id':source['id'],'quote':source['blocks'][0]['text'],'refuting_evidence':'No independent manufacturing investigation; cause remains a hypothesis.','note':'Agent recorded a synthetic hypothesis with source; no verified root-cause claim.'})
    assert action['cause']['status']=='hypothesis'
    action=post(c,'/api/actions/'+action['id']+'/plan-review',{'revision':action['revision'],'baseline_ids':[r['observation_id'] for r in observations['rows'] if r['observation_id'].startswith('BASE-')],
        'group':group,'start':'2026-09-04T00:00:00+00:00','end':'2026-09-05T23:59:59+00:00','min_inspected':10000,'expected_samples':20,'max_rate':.02,
        'synthetic_historical_replay':True,'reviewed':True,'note':'Predeclared engineering replay criteria before loading withheld synthetic follow-up observations.'})
    route='/api/actions/'+action['id']
    early=c.get(route+'/effectiveness').json();assert early['status']=='inconclusive'
    assert c.post(route+'/outcome-review',json={'revision':action['revision'],'input_hash':early['input_hash'],'reviewed':True,'note':'Trying to close before required implementation and exposure.'}).status_code==422
    proof='Completed the synthetic receiving verification instruction update and reviewer training exercise for this incident.'
    state=post(c,case_route+'/documents',{'filename':'implementation.txt','content_base64':base64.b64encode(proof.encode()).decode(),'synthetic':True})
    action=post(c,route+'/implementation-review',{'revision':action['revision'],'document_id':state['documents'][-1]['id'],'quote':proof,'note':'Agent checked synthetic implementation evidence; not actual plant training.'})
    assert action['status']=='implemented'
    action=post(c,route+'/monitoring-start',{'revision':action['revision'],'reviewed':True,'note':'Begin disclosed historical synthetic follow-up after freezing criteria and recording implementation.'})
    post(c,route+'/synthetic-followup',{'phase':'followup','acknowledge_synthetic_replay':True})
    result=c.get(route+'/effectiveness').json();assert result['status']=='criteria_met'
    assert result['followup']['inspected']==13000 and result['followup']['observations']==20
    action=post(c,route+'/outcome-review',{'revision':action['revision'],'input_hash':result['input_hash'],'reviewed':True,'note':'Synthetic criteria met; this is observed rate change without causal attribution or human productivity evidence.'})
    previous=copy.deepcopy(action['outcomes'])
    post(c,route+'/synthetic-followup',{'phase':'recurrence','acknowledge_synthetic_replay':True})
    assert c.post(route+'/recurrence-review',json={'revision':action['revision'],'baseline_id':baseline['id'],'observation_id':'SHIFT-001'}).status_code==422
    action=post(c,route+'/recurrence-review',{'revision':action['revision'],'baseline_id':baseline['id'],'observation_id':'RECUR-001'})
    assert action['status']=='reviewed_outcome' and action['outcomes']==previous
    action=post(c,route+'/reopen-review',{'revision':action['revision'],'recurrence_id':action['recurrences'][-1]['id'],'reviewed':True,'note':'Reviewed matching supplier genealogy, product, process and cosmetic defect signal; reopen investigation only.'})
    assert action['status']=='investigation' and action['outcomes']==previous
    assert c.get(case_route).json()['receipts']==[]
