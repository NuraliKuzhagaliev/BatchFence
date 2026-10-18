"""Conservative review checks. Model booleans and quote existence are not certainty.

These bounded English checks catch explicit contradictions; they are not a
semantic classifier. Every candidate still requires a disposition and every
narrowed incident requires a separate, source-backed scope review.
"""
import re

REVIEW_POLICY_VERSION = 5
UNRESOLVED = re.compile(
    r'\b(?:scope|extent|affected (?:lot|batch)(?:s|es)?(?: list| set)?)\b[^.!?\n]{0,65}'
    r'\b(?:unresolved|unknown|undetermined|not (?:yet )?(?:known|final|complete)|pending|under investigation)\b'
    r'|\b(?:cannot|can\x27t|unable to) (?:yet )?(?:determine|establish|confirm|rule out)\b'
    r'|\b(?:may|might|could|possibly|potentially) (?:be |also be |have been )?(?:affected|implicated|involved|contaminated)\b'
    r'|\b(?:awaiting|pending) (?:laboratory|lab|test|investigation|supplier) (?:results|confirmation|findings)\b'
    r'|\b(?:not|no longer) (?:a )?(?:complete|exhaustive|final) (?:incident |affected )?(?:list|scope|set|boundary)\b'
    r'|\b(?:list|scope|boundary|extent)\b[^.!?\n]{0,65}\b(?:not exhaustive|illustrative|incomplete|remains? open|has not been (?:established|determined|confirmed))\b'
    r'|\b(?:contradiction|conflict)\b[^.!?\n]{0,45}\b(?:unresolved|not resolved)\b'
    r'|\b(?:unresolved|unreconciled) (?:contradiction|conflict)\b'
    r'|\b(?:critical )?identifier\b[^.!?\n]{0,45}\bnot (?:visually )?confirmed\b',
    re.IGNORECASE,
)


def mentions(lot, text):
    # A terminal period is sentence punctuation; a dot followed by identifier
    # characters still belongs to a longer lot ID and must not match a prefix.
    return re.search(r'(?<![\w./-])' + re.escape(lot) + r'(?![\w/-]|\.[\w./-])', text) is not None


def listed_source_lots(state,source):
    """Bounded extra check for explicit English affected-list headers.

    This is not a general source classifier. It prevents a model from dropping
    exact recorded identifiers from the common list form; no fuzzy identity,
    translation, disposition or genealogy is inferred.
    """
    known={str(e[k]) for e in state.get('edges',[]) for k in ('source','target')}
    result=set()
    for block in source['blocks']:
        for match in re.finditer(r'\bAffected\s+(?:supplier\s+)?(?:lots|batches)\s*:\s*',block['text'],re.I):
            span=re.split(r'\.\s+|[!?]|\n',block['text'][match.end():],maxsplit=1)[0]
            result.update(lot for lot in known if mentions(lot,span))
    return result


def scope_concerns(source):
    return [{'document_id': source['id'], 'block_id': b['id'], 'quote': b['text']}
            for b in source['blocks'] if UNRESOLVED.search(b['text'])]


def require_language_review(source):
    if source.get('language_review_required') or source.get('evidence_language','en')!='en':
        review=source.get('language_review')
        if not review or review.get('original_hash')!=source.get('original_hash'):
            from .domain import DomainError
            raise DomainError('Original-language qualification and critical-field review required before consequential interpretation')


def resolution_evidence(source, quote):
    quote = quote.strip()
    if len(quote) < 8:
        return None
    return next(({'document_id': source['id'], 'block_id': b['id'], 'quote': quote}
                 for b in source['blocks'] if quote in b['text']), None)
