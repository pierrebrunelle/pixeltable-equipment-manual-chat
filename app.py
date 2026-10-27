"""Equipment-manual chat API built with Pixeltable.

Upload equipment manuals (PDF or Markdown). Pixeltable splits each one into page-aware chunks
(`document_splitter`), embeds the chunks into an embedding index, and every question inserted into
`questions` retrieves the closest excerpts, asks a small model for a cited answer, and stores the
answer with its sources. One FastAPIRouter serves uploads, questions and search.

Layout: UDFs live in udfs.py; this file holds table models, @pxt.query functions and routes.

    pxt schema update app.py manuals
    python seed.py
    pxt service run app.py manuals --port 8000
"""

from __future__ import annotations

import pixeltable as pxt
import pixeltable.functions as pxtf
from pixeltable.functions import openai
from pixeltable.serving import FastAPIRouter

from udfs import ANSWER_MODEL, EMBED_MODEL, SYSTEM_PROMPT, build_prompt, cited_refs, fault_codes, sources

TableModel = pxt.model_base()


class Manuals(TableModel, name='manuals'):
    """One equipment manual (PDF or Markdown)."""

    manual_id = pxt.Column(type=pxt.String, primary_key=True)
    equipment: pxt.String
    vendor: pxt.String | None
    doc: pxt.Document

    __indexes__ = [pxt.BtreeIndex(equipment)]


class Chunks(
    TableModel,
    name='chunks',
    base=Manuals,
    # one chunk per page, split further at 200 tokens; `page` is 0-based (PDF only), `heading` is Markdown only
    iterator=pxtf.document.document_splitter(Manuals.doc, separators='page,token_limit', limit=200, metadata='heading,page'),
):
    """Component view: page-aware chunks of every manual, embedded for retrieval."""

    codes = fault_codes(text)  # type: ignore[name-defined]  # noqa: F821

    __indexes__ = [
        pxt.EmbeddingIndex(text, string_embed=openai.embeddings.using(model=EMBED_MODEL), name='chunk_embed')  # type: ignore[name-defined]  # noqa: F821
    ]


@pxt.query
def search_chunks(q: str, k: int = 4):
    """Top-k manual excerpts closest in meaning to the question."""
    sim = Chunks.text.similarity(string=q, idx='chunk_embed')
    return (
        Chunks.order_by(sim, asc=False)
        .limit(k)
        .select(Chunks.manual_id, Chunks.equipment, Chunks.page, Chunks.text, score=sim)
    )


@pxt.query
def code_lookup(code: str):
    """Exact fault-code lookup (no embeddings): every chunk that mentions the code."""
    return Chunks.where(Chunks.codes.contains(code)).select(Chunks.manual_id, Chunks.equipment, Chunks.page, Chunks.text)


@pxt.query
def manual_list():
    """Every manual with its equipment name."""
    return Manuals.order_by(Manuals.equipment).select(Manuals.manual_id, Manuals.equipment, Manuals.vendor)


class Questions(TableModel, name='questions'):
    """A technician's question; retrieval, the cited answer and its sources are computed on insert."""

    question: pxt.String
    equipment: pxt.String | None
    asked_by: pxt.String | None
    qid = pxt.Column(value=pxtf.uuid.uuid7(), primary_key=True)

    hits = search_chunks(question)
    prompt = build_prompt(question, equipment, hits)
    response = openai.chat_completions(
        [{'role': 'system', 'content': SYSTEM_PROMPT}, {'role': 'user', 'content': prompt}],
        model=ANSWER_MODEL,
        model_kwargs={'max_tokens': 250, 'temperature': 0},
    )
    answer = response.choices[0].message.content.astype(pxt.String)
    cited = cited_refs(answer)
    refs = sources(hits)


@pxt.query
def recent_questions(n: int = 10):
    """The latest answered questions."""
    return Questions.order_by(Questions.qid, asc=False).limit(n).select(Questions.question, Questions.answer, Questions.refs)


manuals_api = FastAPIRouter(name='manuals_api')

manuals_api.add_insert_route(
    Manuals,
    path='/manuals',
    inputs=[Manuals.manual_id, Manuals.equipment, Manuals.vendor],
    uploadfile_inputs=[Manuals.doc],
    outputs=[Manuals.manual_id, Manuals.equipment],
)
manuals_api.add_insert_route(
    Questions,
    path='/ask',
    inputs=[Questions.question, Questions.equipment, Questions.asked_by],
    outputs=[Questions.qid, Questions.answer, Questions.refs, Questions.cited],
)
manuals_api.add_compute_route(
    Questions,
    path='/ask/preview',
    inputs=[Questions.question, Questions.equipment],
    outputs=[Questions.answer, Questions.refs],
)
manuals_api.add_delete_route(Manuals, path='/manuals/delete')
manuals_api.add_query_route(path='/search', query=search_chunks, method='get')
manuals_api.add_query_route(path='/codes', query=code_lookup, method='get')
manuals_api.add_query_route(path='/manuals/list', query=manual_list, method='get')
manuals_api.add_query_route(path='/questions/recent', query=recent_questions, method='get')
