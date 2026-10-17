"""Versioned p-chart calculations; never a product acceptance specification."""
import math
from datetime import datetime
from .domain import DomainError,digest

GROUP=('site','product','process','method','regime','defect','metric')
DEFAULT_POLICY={'min_observations':20,'min_inspected':5000,'min_expected':5,'sigma':3}


def event_instant(value):
    """Compare actual instants while retaining original source timestamps."""
    try:
        stamp=datetime.fromisoformat(value.replace('Z','+00:00'))
        if stamp.tzinfo is None:raise ValueError()
        return stamp
    except (ValueError,TypeError,AttributeError):raise DomainError('Valid timezone-aware observation required')


def event_order(row):return (event_instant(row['event_time']),row['observation_id'])


def validate_rows(rows):
    seen=set()
    for r in rows:
        if r['observation_id'] in seen: raise DomainError('Duplicate observation ID')
        seen.add(r['observation_id'])
        if any(not r.get(k) for k in GROUP) or r['metric']!='nonconforming_units': raise DomainError('Comparable nonconforming-unit records required')
        if type(r['inspected']) is not int or type(r['nonconforming']) is not int or r['inspected']<=0 or not 0<=r['nonconforming']<=r['inspected']:
            raise DomainError('Invalid inspection denominator or nonconforming count')
        event_instant(r['event_time'])
    return rows


def freeze(rows,ids,policy=None):
    validate_rows(rows)
    chosen=sorted([r for r in rows if r['observation_id'] in ids],key=event_order)
    if not chosen or len(chosen)!=len(set(ids)): raise DomainError('Choose existing unique baseline rows')
    groups={tuple(r[k] for k in GROUP) for r in chosen}
    if len(groups)!=1: raise DomainError('Do not pool products, methods, regimes or processes')
    policy=policy or DEFAULT_POLICY
    if not 2<=policy['min_observations']<=100 or not 1<=policy['min_inspected']<=1_000_000 or not 1<=policy['min_expected']<=20 or policy['sigma']!=3:
        raise DomainError('Unsupported baseline policy')
    result={'rows':chosen,'row_hash':digest(chosen),'group':{k:chosen[0][k] for k in GROUP},'start':chosen[0]['event_time'],'end':chosen[-1]['event_time'],
            'policy':policy,'assumptions':['Independent inspections','Comparable product/process/method/regime','Reviewer-accepted stable baseline'],
            'rule':'One observation strictly outside clipped three-sigma limits; limits are not acceptance specifications.'}
    # Prevent hidden omission of comparable observations inside the baseline period.
    all_period=[r for r in rows if same_group(r,result['group']) and event_instant(result['start'])<=event_instant(r['event_time'])<=event_instant(result['end'])]
    if {r['observation_id'] for r in all_period}!=set(ids): raise DomainError('Baseline interval contains omitted comparable observations')
    return result


def same_group(row,group): return all(row.get(k)==v for k,v in group.items())


def chart(baseline,rows):
    validate_rows(rows)
    current=sorted([r for r in rows if same_group(r,baseline['group']) and event_instant(baseline['start'])<=event_instant(r['event_time'])<=event_instant(baseline['end'])],key=event_order)
    if digest(current)!=baseline['row_hash']:
        return {'status':'invalidated','reason':'Baseline observations changed or were backfilled; review a new baseline revision','points':[]}
    selected=baseline['rows']; total=sum(r['inspected'] for r in selected); bad=sum(r['nonconforming'] for r in selected)
    p=bad/total;policy=baseline['policy']
    reasons=[]
    if len(selected)<policy['min_observations'] or total<policy['min_inspected']: reasons.append('Baseline is below the configured minimum exposure/observations')
    if p in (0,1): reasons.append('Degenerate baseline at zero or one; normal approximation is unsuitable')
    if any(r['inspected']*p<policy['min_expected'] or r['inspected']*(1-p)<policy['min_expected'] for r in selected): reasons.append('Sparse expected baseline counts; normal approximation is unsuitable')
    base={'p_bar':p,'baseline_inspected':total,'baseline_nonconforming':bad,'baseline_count':len(selected),'baseline_hash':baseline['row_hash'],
          'rule':baseline['rule'],'group':baseline['group'],'assumptions':baseline['assumptions'],'policy':policy}
    if reasons:return {**base,'status':'insufficient','reason':'; '.join(reasons),'points':[]}
    points=[];excluded=[]
    for r in sorted(rows,key=event_order):
        if event_instant(r['event_time'])<=event_instant(baseline['end']):continue
        if not same_group(r,baseline['group']): excluded.append({'id':r['observation_id'],'reason':'Different product/process/method/regime/defect population'});continue
        n=r['inspected'];rate=r['nonconforming']/n
        if n*p<policy['min_expected'] or n*(1-p)<policy['min_expected']:
            points.append({'observation_id':r['observation_id'],'status':'insufficient','reason':'Sparse expected counts','inspected':n,'rate':rate,'source':r['source']});continue
        delta=3*math.sqrt(p*(1-p)/n);lower=max(0,p-delta);upper=min(1,p+delta)
        points.append({**r,'rate':rate,'lower':lower,'upper':upper,'status':'signal' if rate<lower or rate>upper else 'within_limits',
                       'direction':'higher' if rate>upper else 'lower' if rate<lower else None})
    return {**base,'status':'ready','points':points,'excluded':excluded,'alerts':[r['observation_id'] for r in points if r['status']=='signal'],
            'boundary':'A signal is evidence of process variation, not supplier causation, defect certainty, hold authority or release authority.'}


def wilson(bad,total,z=1.96):
    if not total:return None
    p=bad/total;den=1+z*z/total;center=(p+z*z/(2*total))/den
    half=z*math.sqrt(p*(1-p)/total+z*z/(4*total*total))/den
    return [max(0,center-half),min(1,center+half)]


def explanation_context(baseline,result):
    """Bound narrative work while keeping the full deterministic chart in storage/UI."""
    signal_points=[p for p in result['points'] if p['status']=='signal']
    selected=(signal_points or result['points'])[:5]
    keys=('observation_id','event_time','inspected','nonconforming','rate','lower','upper','status','direction','source')
    return {'baseline_observation_ids':[r['observation_id'] for r in baseline['rows']],
        'baseline_period':{'start':baseline['start'],'end':baseline['end']},
        'baseline':{k:result[k] for k in ('baseline_count','baseline_inspected','baseline_nonconforming','p_bar','baseline_hash','group','assumptions','rule')},
        'followup_count':len(result['points']),'signal_count':len(signal_points),
        'omitted_followup_count':len(result['points'])-len(selected),
        'selection':'First five statistical signals, or first five follow-up observations when there are no signals. Other observations remain in the full chart.',
        'observations':[{k:p[k] for k in keys if k in p} for p in selected],
        'boundary':result['boundary']}
