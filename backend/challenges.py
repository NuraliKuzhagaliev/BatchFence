"""Executable bounded challenges over disposable copies; no persisted visitor state."""
import copy
from .domain import make_plan
from .fixtures import load_demo
from .provider import validate_output
from .review_safety import REVIEW_POLICY_VERSION
from .scenarios import simulate


def run_challenges(approval_current,actions_exact):
    checks=[]
    def check(name,passed,actual):
        checks.append({'name':name,'passed':bool(passed),'actual':actual})
    s=load_demo()
    s['scope'].update(lot_ids=['SUP-A'],incident_scope_status='unresolved',review_policy_version=REVIEW_POLICY_VERSION)
    r=make_plan(s)['result']
    check('Ambiguous boundary cannot exclude stock',r['outside_units']==0,{'hold_units':r['hold_units'],'outside_units':r['outside_units']})
    s['scope']['incident_scope_status']='resolved'
    s['plan']=make_plan(s)
    p=copy.deepcopy(s['plan'])
    s['revision']+=1
    check('Changed evidence invalidates approval',not approval_current(s,p['id'],p['digest']),{'approval_current':approval_current(s,p['id'],p['digest'])})
    s['revision']-=1
    changed=[a for a in p['actions'] if a['pool_id']!='FG-C']
    check('Uncertain stock cannot be removed from actions',not actions_exact(changed,p),{'accepted':actions_exact(changed,p),'removed':'FG-C'})
    d=s['documents'][0]
    rejected=False
    try:
        validate_output({'facts':[{'lot_id':'FAKE','affected':True,'evidence':[{'document_id':d['id'],'block_id':d['blocks'][0]['id'],'quote':'Fabricated FAKE citation'}]}],'qualifiers':[]},[d])
    except ValueError:
        rejected=True
    check('Fabricated citation is rejected',rejected,{'citation_rejected':rejected})
    s['edges'].append(copy.deepcopy(s['edges'][0]))
    r=make_plan(s)['result']
    check('Overlapping ancestry counts unique stock once',r['hold_units']==500,{'hold_units':r['hold_units'],'unique_pools':len(r['rows'])})
    result=simulate(s,[{'kind':'inconclusive'}])
    check('Inconclusive answer cannot narrow',result['before']['hold_units']==result['after']['hold_units']==500,{'before':result['before']['hold_units'],'after':result['after']['hold_units']})
    return checks
