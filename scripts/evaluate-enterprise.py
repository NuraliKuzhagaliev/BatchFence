"""Reproducible synthetic statistical calibration and supported-envelope timings."""
import copy,json,os,platform,random,statistics,time,tracemalloc
from datetime import datetime,timedelta,timezone
from pathlib import Path
from backend import signals,knowledge
from backend.domain import calculate,DomainError,digest
from backend.fixtures import now
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/enterprise'
def observation(key,n,bad,i):return {'observation_id':key,'inspected':n,'nonconforming':bad,'event_time':(datetime(2026,9,1,tzinfo=timezone.utc)+timedelta(hours=i)).isoformat(),'site':'Synthetic','product':'Decorative housing','process':'coating','method':'visual-v1','regime':'steady','defect':'cosmetic','metric':'nonconforming_units','pool_ids':['P-000'],'source':{'document_id':'SYNTHETIC-GENERATOR','block_id':key,'quote':f'{key}: {bad}/{n}; disclosed binomial generator'}}
def series(prefix,count,p,seed,start):
    rng=random.Random(seed);rows=[]
    for i in range(count):
        n=500 if i%2==0 else 800;rows.append(observation(prefix+str(i),n,sum(rng.random()<p for _ in range(n)),start+i))
    return rows
trials=[]
for seed in range(100):
    baseline=series('B',20,.02,1000+seed,0);stable=series('S',100,.02,2000+seed,20);shift=series('H',20,.05,3000+seed,120)
    frozen=signals.freeze(baseline,[r['observation_id'] for r in baseline]);chart=signals.chart(frozen,baseline+stable+shift);assert chart['status']=='ready'
    false=[p['observation_id'] for p in chart['points'] if p['observation_id'].startswith('S') and p['status']=='signal'];detected=[i+1 for i,p in enumerate([p for p in chart['points'] if p['observation_id'].startswith('H')]) if p['status']=='signal']
    trials.append({'seed':seed,'false_alerts':len(false),'stable_observations':100,'first_shift_detection_observation':detected[0] if detected else None})
stats={'at':now(),'provenance':'Synthetic independent binomial draws; fixed reviewed-baseline assumption, not field performance','generation':{'baseline_p':.02,'shift_p':.05,'baseline_count':20,'stable_count':100,'shift_count':20,'sample_sizes':[500,800],'trials':100,'seed_sets':[1000,2000,3000]},'policy':signals.DEFAULT_POLICY,'false_alerts':sum(t['false_alerts'] for t in trials),'stable_denominator':10000,'trials_with_detected_shift':sum(t['first_shift_detection_observation'] is not None for t in trials),'median_detection_delay_observations':statistics.median(t['first_shift_detection_observation'] for t in trials if t['first_shift_detection_observation'] is not None),'per_trial':trials,'limitations':'Synthetic calibration of this one p-chart rule. False alerts within a trial share an estimated baseline and are correlated; no pooled independent-binomial confidence interval is claimed. No supplier causality or acceptance authority.'}
(OUT/'statistical-evaluation.json').write_text(json.dumps(stats,indent=2),encoding='utf-8')
stocks=[];edges=[];allocations=[]
for i in range(500):
    key=f'P-{i:03d}';source='S-'+str(i%5);units=10+i%91
    stocks.append({'id':key,'units':units,'unit_cents':4000,'status':'available','complete':True,'row_id':'I-'+str(i),'site':'Synthetic','product_family':'Decorative housing'})
    edges.append({'row_id':'L-'+str(i),'source':source,'target':key,'kind':'possible' if i%11==0 else 'confirmed','evidence':{'document_id':'D','block_id':'L-'+str(i),'quote':f'{source} to {key}'}})
    allocations.append({'row_id':'A-'+str(i),'order_id':'O-'+str(i),'pool_id':key,'units':units,'due_date':'2026-11-01','status':'open'})
times=[];tracemalloc.start()
for _ in range(15):
    start=time.perf_counter();result=calculate(stocks,edges,['S-0'],allocations,True);times.append((time.perf_counter()-start)*1000)
_,peak=tracemalloc.get_traced_memory();tracemalloc.stop();assert result['hold_units']+result['outside_units']==sum(s['units'] for s in stocks)
rejected=False
try:calculate(stocks+[copy.deepcopy(stocks[0])],edges,['S-0'],allocations,True)
except DomainError:rejected=True
performance={'at':now(),'os':platform.platform(),'architecture':platform.machine(),'logical_cpu_count':os.cpu_count(),'provenance':'Actual local timings of deterministic Python calculations on synthetic 500-pool/500-edge/500-allocation data; tracemalloc enabled','iterations':15,'median_ms':round(statistics.median(times),2),'p95_ms':round(sorted(times)[14],2),'maximum_ms':round(max(times),2),'python_tracked_peak_bytes':peak,'serialized_result_bytes':len(json.dumps(result).encode()),'above_500_records_rejected':rejected,'hold_units':result['hold_units'],'outside_units':result['outside_units'],'limitations':'Single-machine microbenchmark, not browser/network latency, process RSS, a load test or enterprise capacity. Repository serializes committing writers; no scalability claim.'}
assert performance['p95_ms']<2000 and rejected
(OUT/'performance.json').write_text(json.dumps(performance,indent=2),encoding='utf-8')
frozen=(ROOT/'evals/enterprise/frozen-v1.json').read_bytes();manifest=json.loads((ROOT/'evals/enterprise/manifest.json').read_text());assert __import__('hashlib').sha256(frozen).hexdigest()==manifest['sha256'];items=json.loads(frozen)['items'];docs=json.loads((ROOT/'fixtures/enterprise/procedures.json').read_text())
retrieval=[]
for item in items:
    if item['task']!='knowledge':continue
    product={'decorative-housings':'Decorative housing'}.get(item['product'],item['product'])
    result=knowledge.retrieve(docs,item['question'],product,item['process'],True)
    retrieval.append({'id':item['id'],'retrieval_status':result['status'],'retrieved_sources':sorted({p['document_id']+'@'+str(p['version']) for p in result['passages']}),'expected_sources':item['labels']['expected_sources'],'note':'Retrieval candidates are not an answer. Unanswerable adversarial questions may retrieve related text; AMD abstention/semantic quality not measured.'})
quality={'at':now(),'frozen_hash':manifest['sha256'],'full_denominator':24,'fresh_model_requests':0,'model_accuracy':'Not measured; 0/24 fresh model items run','blocker':'Configured MiMo-V2.6-Flash and all current catalog entries report free=false; documented quota endpoint returned 404. Free-only budget requires confirmation of the actual account allowance before new inference. No fallback or model substitution.','preflight':'live/preflight.json','provenance':'Offline deterministic retrieval only, agent-authored synthetic labels; no independent held-out or human validation','product_mapping':{'decorative-housings':'Decorative housing'},'retrieval_only':retrieval,'historical_live_reference':'../release-0.2.0/live/README.md','new_task_live_verification':'incomplete'}
(OUT/'model-evaluation.json').write_text(json.dumps(quality,indent=2),encoding='utf-8')
print(json.dumps({'statistical_false_alerts':stats['false_alerts'],'stable_denominator':10000,'detected_trials':stats['trials_with_detected_shift'],'median_delay':stats['median_detection_delay_observations'],'performance':performance,'fresh_model_requests':0},indent=2))
