"""One real isolated Blob-library retrieval and one fresh Gemma answer.

Synthetic approved procedure, explicit agent review, no embeddings or messages.
"""
import json,os
from fastapi.testclient import TestClient
from scripts.continuation_live import PRIVATE,OUT,refresh_quota,safe_save
from scripts.continuation_evolus_flow import setup_allowance
from backend import app as module
from backend.domain import digest

def main():
 statefile=PRIVATE/'library-session.json'
 if statefile.exists():raise RuntimeError('Prior library attempt retained; inspect before another request')
 setup_allowance();c=TestClient(module.app);phase='created'
 def post(p,b=None):
  r=c.post(p,json=b or {})
  if r.status_code!=200:raise RuntimeError('Application HTTP '+str(r.status_code)+': '+str(r.json())[:700])
  return r.json()
 s=post('/api/cases/demo');route='/api/cases/'+s['id'];product=s['stocks'][0]['product_family']
 statefile.write_text(json.dumps({'case_id':s['id'],'cookies':dict(c.cookies)}),encoding='utf-8')
 try:
  passages=[{'id':'P1','page':1,'text':'Before cosmetic recovery, verify the exact lot identity, complete parent list, passed whole-pool inspection and current approved scope. Obtain separate release approval. This fictional training procedure grants no real inventory authority.'}]
  proc={'id':'TRAIN-COSMETIC','version':1,'owner':'Synthetic engineering author','products':[product],'processes':['coating'],'status':'approved',
   'valid_from':'2026-01-01T00:00:00Z','valid_to':None,'synthetic':True,'passages':passages,'source_hash':digest(passages)}
  post('/api/knowledge/procedure-review',{'document':proc,'reviewed':True,'note':'Agent-operated synthetic source and applicability review; no independent professional approval.'})
  phase='indexing';binding=post('/api/assist/knowledge-index',{'library_id':os.environ['EVOLUS_LIBRARY_ID'],'product':product,'process':'coating','synthetic':True,'reviewed':True,
    'note':'Agent-operated review of dedicated empty read-only Blob library and exact synthetic source set; no embeddings.'})
  safe_save(OUT/'evolus-library-binding.json',binding)
  phase='retrieval-and-answer';record=post(route+'/assist-generate',{'kind':'knowledge','revision':s['revision'],'question':'What evidence is required before cosmetic recovery?',
    'product':product,'process':'coating','idempotency_key':'actual-isolated-evolus-library-answer'})
  safe_save(OUT/'evolus-library-answer.json',record)
  if record['status']!='unreviewed proposal':raise RuntimeError('Fresh library answer '+record['status']+': '+record.get('error',''))
  assert record['draft']['claims'] and not record['draft']['insufficient_evidence']
  assert len(record['library_provenance'])>=2 and record['linked_answer']['output']==record['draft']
  # Wrong applicability abstains before any provider request, even with a library.
  wrong=post(route+'/assist-generate',{'kind':'knowledge','revision':s['revision'],'question':'What evidence is required before cosmetic recovery?',
    'product':'WRONG-PRODUCT','process':'coating','idempotency_key':'wrong-product-must-abstain'})
  assert wrong['provider_calls']==0
  safe_save(OUT/'evolus-library-result.json',{'status':'verified real Blob upload/membership/download + fresh exact-passage Gemma selection',
    'fresh_model_calls':1,'wrong_product_provider_calls':0,'binding_scope':binding['scope'],'claims':record['draft']['claims'],
    'model_id':record['provenance']['model_id'],'request_id':record['provenance']['request_id'],
    'retrieval':'Local applicability and lexical rank first; actual Evolus retained source membership/download; exact hash and passage check before Gemma. No semantic/RAG performance claim.',
    'cost':'Catalog own-model byok-free; documented read-only Blob has no vector/embedding pipeline. API does not return library operation credit consumption.',
    'independent_human_validation':False})
  print('Actual Evolus isolated Blob retrieval + fresh Gemma exact passage accepted; wrong product made zero provider calls.')
 except Exception as e:
  safe_save(OUT/'evolus-library-blocked.json',{'phase':phase,'error':str(e)[:900],'no_automatic_retry':True});print('Library blocked:',str(e)[:900]);raise
 finally:refresh_quota('after-evolus-library')

if __name__=='__main__':main()
