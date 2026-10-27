"""UDFs for the equipment-manual chat API (pure Python, no table imports)."""

from __future__ import annotations

import re

import pixeltable as pxt

ANSWER_MODEL = 'gpt-4o-mini'
EMBED_MODEL = 'text-embedding-3-small'

SYSTEM_PROMPT = (
    'You answer questions from maintenance technicians using only the manual excerpts provided. '
    'Quote exact numbers, part numbers and fault codes from the excerpts. Cite the excerpts you used as [1], [2], ... '
    'If the excerpts do not contain the answer, say "Not in the manuals." and nothing else.'
)


@pxt.udf
def build_prompt(question: str, equipment: str | None, hits: list[dict] | None) -> str:
    """Number the retrieved excerpts and put the question last."""
    lines = []
    for i, h in enumerate(hits or [], start=1):
        where = h.get('equipment') or h.get('manual_id')
        page = h.get('page')
        loc = f'{where}, page {page + 1}' if isinstance(page, int) else f'{where}'
        text = ' '.join(str(h.get('text') or '').split())
        lines.append(f'[{i}] ({loc}) {text}')
    scope = f'Equipment: {equipment}\n' if equipment else ''
    return 'Manual excerpts:\n' + '\n'.join(lines) + f'\n\n{scope}Question: {question}'


@pxt.udf
def sources(hits: list[dict] | None) -> list[dict]:
    """The citations returned with an answer: manual, page and similarity score per excerpt."""
    out = []
    for i, h in enumerate(hits or [], start=1):
        page = h.get('page')
        out.append({
            'ref': i,
            'manual_id': h.get('manual_id'),
            'page': page + 1 if isinstance(page, int) else None,
            'score': round(float(h.get('score') or 0.0), 3),
        })
    return out


@pxt.udf
def cited_refs(answer: str) -> list[int]:
    """Which [n] markers the model actually cited."""
    return sorted({int(n) for n in re.findall(r'\[(\d+)\]', answer or '')})


@pxt.udf
def fault_codes(text: str) -> list[str]:
    """Fault / alarm codes mentioned in a chunk (E07, ALM-14, F5, A3, ...), for exact-code lookups."""
    codes = re.findall(r'\b(?:E\d{2}|ALM-\d{1,2}|F\d|A\d)\b', text or '')
    return sorted(set(codes))
