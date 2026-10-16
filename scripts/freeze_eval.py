"""Author ground truth as literal stock sets, independently of the domain engine."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]


def edges(*pairs):
    return [{'source': a, 'target': b, 'kind': k} for a, b, k in pairs]


def c(bucket, name, relations, documented, uncertain, outside, *, incomplete=(), seeds=('SUP-A',),
      invalid=False, second=None, shipped=()):
    return {'id': bucket + '-' + name, 'bucket': bucket, 'synthetic': True,
            'notice': 'Synthetic supplier notice. Affected lots: ' + ', '.join(seeds),
            'seeds': list(seeds), 'bounded': True,
            'stocks': [{'id': p, 'units': q, 'unit_cents': cents, 'complete': p not in incomplete,
                        'status': 'shipped' if p in shipped else 'available'}
                       for p, q, cents in [('P1', 7, 1000), ('P2', 11, 2000), ('P3', 13, 3000)]],
            'edges': relations, 'allocations': [], 'expected_error': invalid,
            'truth': {'documented': documented.split(), 'uncertain': uncertain.split(),
                      'outside': outside.split()}, 'second_scope': second}


base = edges(('SUP-A', 'P1', 'confirmed'), ('SUP-B', 'P2', 'confirmed'), ('SUP-C', 'P3', 'confirmed'))
cases = [
 c('clean','one',base,'P1','','P2 P3'),
 c('clean','two',base,'P2','','P1 P3',seeds=('SUP-B',)),
 c('clean','three',base,'P3','','P1 P2',seeds=('SUP-C',)),
 c('clean','shipped',base,'P1','','P2 P3',shipped=('P1',)),
 c('clean','all',base,'P1 P2 P3','','',seeds=('SUP-A','SUP-B','SUP-C')),
 c('merge','whole',base+edges(('SUP-A','P2','confirmed')),'P1 P2','','P3'),
 c('merge','two-seeds',base,'P1 P3','','P2',seeds=('SUP-A','SUP-C')),
 c('merge','possible',base+edges(('SUP-A','P3','possible')),'P1','P3','P2'),
 c('merge','duplicate',base+base,'P1','','P2 P3'),
 c('merge','precedence',base+edges(('SUP-A','P2','possible'),('SUP-A','P2','confirmed')),'P1 P2','','P3'),
 c('rework','split',edges(('SUP-A','EV1','confirmed'),('EV1','P1','confirmed'),('EV1','P2','confirmed'),('SUP-C','P3','confirmed')),'P1 P2','','P3'),
 c('rework','uncertain-event',edges(('SUP-A','EV1','possible'),('EV1','P1','confirmed'),('EV1','P2','confirmed'),('SUP-C','P3','confirmed')),'','P1 P2','P3'),
 c('rework','versioned',edges(('SUP-A','EV1-v1','confirmed'),('EV1-v1','EV1-v2','confirmed'),('EV1-v2','P1','confirmed'),('SUP-B','P2','confirmed'),('SUP-C','P3','confirmed')),'P1','','P2 P3'),
 c('rework','diamond',edges(('SUP-A','E1','confirmed'),('SUP-A','E2','confirmed'),('E1','E3','confirmed'),('E2','E3','confirmed'),('E3','P1','confirmed'),('SUP-B','P2','confirmed'),('SUP-C','P3','confirmed')),'P1','','P2 P3'),
 c('rework','mixed',edges(('SUP-A','E1','confirmed'),('E1','P1','confirmed'),('E1','E2','possible'),('E2','P2','confirmed'),('SUP-C','P3','confirmed')),'P1','P2','P3'),
 c('missing','no-receipt',base,'P1','P2','P3',incomplete=('P2',)),
 c('missing','no-edges',edges(('SUP-A','P1','confirmed')),'P1','P2 P3','',incomplete=('P2','P3')),
 c('missing','conflicting',base+edges(('SUP-A','P2','possible')),'P1','P2','P3'),
 c('missing','disconnected-unknown',base,'','P1 P2 P3','',seeds=('SUP-Z',)),
 c('missing','combined',base+edges(('SUP-A','P3','possible')),'P1','P2 P3','',incomplete=('P2',)),
 c('adversarial','cycle',base+edges(('E1','E2','confirmed'),('E2','E1','confirmed')),'','','',invalid=True),
 c('adversarial','dangling',base+edges(('SUP-A','MISSING','confirmed')),'','','',invalid=True),
 c('adversarial','invalid-kind',base+edges(('SUP-A','P2','release')),'','','',invalid=True),
 c('adversarial','terminal-reused',base+edges(('P1','P2','confirmed')),'','','',invalid=True),
 c('adversarial','negative',base,'','','',invalid=True),
 c('revision','expand',base,'P1','','P2 P3',second={'seeds':['SUP-A','SUP-B'],'truth':{'documented':['P1','P2'],'uncertain':[],'outside':['P3']}}),
 c('revision','possible',base+edges(('SUP-A','P2','possible')),'P1','P2','P3',second={'seeds':['SUP-A','SUP-C'],'truth':{'documented':['P1','P3'],'uncertain':['P2'],'outside':[]}}),
 c('revision','supersede',base,'P1','','P2 P3',second={'seeds':['SUP-C'],'truth':{'documented':['P3'],'uncertain':[],'outside':['P1','P2']}}),
 c('revision','merge-expand',base+edges(('SUP-C','P2','confirmed')),'P1','','P2 P3',second={'seeds':['SUP-A','SUP-C'],'truth':{'documented':['P1','P2','P3'],'uncertain':[],'outside':[]}}),
 c('revision','split-expand',edges(('SUP-A','E1','confirmed'),('E1','P1','confirmed'),('E1','P2','possible'),('SUP-C','P3','confirmed')),'P1','P2','P3',second={'seeds':['SUP-A','SUP-C'],'truth':{'documented':['P1','P3'],'uncertain':['P2'],'outside':[]}}),
]
cases[24]['stocks'][0]['units'] = -7
manifest = []
for i, case in enumerate(cases):
    split = 'dev' if i % 5 < 3 else 'test'
    dest = ROOT / 'evals' / split / (case['id'] + '.json')
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        raise SystemExit('Evaluation pack already frozen; do not overwrite or silently retune.')
    content = json.dumps(case, indent=2).encode()
    dest.write_bytes(content)
    manifest.append({'id': case['id'], 'split': split, 'sha256': hashlib.sha256(content).hexdigest()})
(ROOT / 'evals/manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print('Frozen 18 development / 12 held-out domain cases. No inference claims.')
