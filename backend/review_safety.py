"""Conservative review checks. Model booleans and quote existence are not certainty.

These bounded English checks catch explicit contradictions; they are not a
semantic classifier. Every candidate still requires a disposition and every
narrowed incident requires a separate, source-backed scope review.
"""
import re

REVIEW_POLICY_VERSION = 3
UNRESOLVED = re.compile(
    r'\b(?:scope|extent|affected (?:lot|batch)(?:s|es)?(?: list| set)?)\b[^.!?\n]{0,65}'
    r'\b(?:unresolved|unknown|undetermined|not (?:yet )?(?:known|final|complete)|pending|under investigation)\b'
    r'|\b(?:cannot|can\x27t|unable to) (?:yet )?(?:determine|establish|confirm|rule out)\b'
    r'|\b(?:may|might|could|possibly|potentially) (?:be |also be |have been )?(?:affected|implicated|involved|contaminated)\b'
    r'|\b(?:awaiting|pending) (?:laboratory|lab|test|investigation|supplier) (?:results|confirmation|findings)\b'
    r'|\b(?:not|no longer) (?:a )?(?:complete|exhaustive|final) (?:list|scope|set)\b'
    r'|\b(?:contradiction|conflict)\b[^.!?\n]{0,45}\b(?:unresolved|not resolved)\b'
    r'|\b(?:unresolved|unreconciled) (?:contradiction|conflict)\b'
    r'|\b(?:critical )?identifier\b[^.!?\n]{0,45}\bnot (?:visually )?confirmed\b',
    re.IGNORECASE,
)


def mentions(lot, text):
    # A terminal period is sentence punctuation; a dot followed by identifier
    # characters still belongs to a longer lot ID and must not match a prefix.
    return re.search(r'(?<![A-Za-z0-9._/-])' + re.escape(lot) + r'(?![A-Za-z0-9_/-]|\.[A-Za-z0-9._/-])', text) is not None


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
