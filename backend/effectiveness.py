"""Predeclared effectiveness mechanics, never proof of causal improvement."""
import copy
from datetime import datetime,timezone
from .domain import DomainError,digest
from .signals import validate_rows,same_group,GROUP,wilson


def freeze_plan(rows,baseline_ids,group,start,end,min_inspected,expected_samples,max_rate,synthetic_replay=False):
    validate_rows(rows)
    try:begin=datetime.fromisoformat(start.replace('Z','+00:00'));finish=datetime.fromisoformat(end.replace('Z','+00:00'))
    except ValueError:raise DomainError('Use valid ISO follow-up timestamps with timezone')
    if not begin.tzinfo or not finish.tzinfo or finish<=begin:raise DomainError('Use a valid timezone-aware follow-up window')
    start=begin.astimezone(timezone.utc).isoformat();end=finish.astimezone(timezone.utc).isoformat()
    if not synthetic_replay and begin<datetime.now(timezone.utc):raise DomainError('Predeclare a future follow-up window; historical data cannot become a prospective trial')
    if not 1<=min_inspected<=1_000_000 or not 2<=expected_samples<=500 or not 0<=max_rate<=1:raise DomainError('Invalid predefined exposure or success criterion')
    baseline=[r for r in rows if r['observation_id'] in baseline_ids]
    if not baseline or len(baseline)!=len(set(baseline_ids)) or any(not same_group(r,group) for r in baseline):raise DomainError('Comparable existing baseline rows required')
    if any(datetime.fromisoformat(r['event_time'].replace('Z','+00:00'))>=begin for r in baseline):raise DomainError('Baseline cannot include future follow-up observations')
    return {'baseline':copy.deepcopy(baseline),'baseline_hash':digest(baseline),'group':group,'start':start,'end':end,
            'min_inspected':min_inspected,'expected_samples':expected_samples,'max_rate':max_rate,'missing_data_policy':'inconclusive',
            'known_observation_ids':[r['observation_id'] for r in rows],'synthetic_historical_replay':synthetic_replay,
            'criterion':'Follow-up nonconforming-unit rate at or below the predeclared maximum, after complete window/exposure and evidence checks',
            'interpretation':'Observed improvement is not causal attribution. Intervals describe binomial sampling uncertainty under comparability/independence assumptions.'}


def evaluate(action,rows,as_of=None):
    plan=action['plan'];as_of=as_of or datetime.now(timezone.utc)
    validate_rows(rows)
    baseline=[next((r for r in rows if r['observation_id']==b['observation_id']),{}) for b in plan['baseline']]
    reasons=[]
    if digest(baseline)!=plan['baseline_hash']:reasons.append('Baseline was corrected or removed after plan approval')
    begin=datetime.fromisoformat(plan['start'].replace('Z','+00:00'));end=datetime.fromisoformat(plan['end'].replace('Z','+00:00'))
    if as_of<end:reasons.append('Predeclared follow-up window is not complete')
    window=[r for r in rows if begin<=datetime.fromisoformat(r['event_time'].replace('Z','+00:00'))<=end]
    follow=[r for r in window if same_group(r,plan['group'])]
    if any(r['observation_id'] in plan['known_observation_ids'] for r in follow):reasons.append('Follow-up rows were already available at plan approval; post-hoc comparison is not accepted')
    if len(follow)<plan['expected_samples']:reasons.append('Missing planned inspection observations; missing results are not zero defects')
    if any(r['site']==plan['group']['site'] and r['product']==plan['group']['product'] and r['process']==plan['group']['process'] and not same_group(r,plan['group']) for r in window):reasons.append('Method/regime/defect population changed; comparison is confounded')
    total=sum(r['inspected'] for r in follow);bad=sum(r['nonconforming'] for r in follow)
    if total<plan['min_inspected']:reasons.append('Minimum inspected exposure not met')
    if not action.get('implementation'):reasons.append('Implementation evidence is absent')
    before_total=sum(r['inspected'] for r in plan['baseline']);before_bad=sum(r['nonconforming'] for r in plan['baseline'])
    rate=bad/total if total else None
    status='inconclusive' if reasons else 'criteria_met' if rate<=plan['max_rate'] else 'criteria_not_met'
    return {'status':status,'reasons':reasons,'baseline':{'inspected':before_total,'nonconforming':before_bad,'rate':before_bad/before_total,'wilson_95':wilson(before_bad,before_total)},
            'followup':{'inspected':total,'nonconforming':bad,'rate':rate,'wilson_95':wilson(bad,total),'observations':len(follow)},
            'followup_rows':follow,'plan_hash':digest(plan),'input_hash':digest({'baseline':baseline,'followup':follow,'window':window}),
            'criterion':plan['criterion'],'max_rate':plan['max_rate'],'interpretation':plan['interpretation'],
            'synthetic_historical_replay':plan['synthetic_historical_replay']}
