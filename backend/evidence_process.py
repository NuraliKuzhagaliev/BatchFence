"""Local source suitability diagnostics, never completeness or action authority."""
from .assist_contracts import source_context


def suitability(document):
    blocks=document.get('blocks') or []
    pages=sorted({b.get('page') for b in blocks if b.get('page')})
    count=sum(len(b.get('text','')) for b in blocks)
    gaps=[]
    if not blocks:gaps.append('No readable retained passages; supply a supported nonempty original.')
    if count>16000:gaps.append('This source exceeds the bounded interpretation envelope; submit a complete smaller notice. No pages are silently truncated.')
    if document.get('ocr') and not document['ocr'].get('critical_fields_confirmed'):gaps.append('Derived local OCR is unverified: inspect every original page and confirm critical fields before a narrowed plan.')
    if document.get('language_review_required') and not document.get('language_review'):gaps.append('Qualified original-language review is still required; a translation is only derived evidence.')
    if document.get('media_type')=='text/csv':gaps.append('Structured records require the existing mapped intake review; a supplier narrative cannot manufacture absent required columns.')
    return {'document_id':document['id'],'original_hash':document['original_hash'],'document_revision':document['revision'],
        'filename':document['filename'],'media_type':document.get('media_type'),'readable_blocks':len(blocks),'pages':pages,'characters':count,
        'status':'needs source review' if gaps else 'readable / suitability review still required','gaps':gaps,
        'next_action':'Inspect original and resolve the named gap' if gaps else 'Interpret the selected original, then review supported facts and explicit scope',
        'boundary':'Readability is not supplier relevance, authenticity, complete ancestry or complete incident scope. No stock or approval authority.'}
