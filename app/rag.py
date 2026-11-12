import asyncio
import json
from functools import lru_cache

import chromadb
from chromadb.utils import embedding_functions
from opentelemetry import trace
from rank_bm25 import BM25Okapi

from app.config import CHROMA_COLLECTION, CHROMA_PATH

DOCS = (
    {
        "id": "cliente-7",
        "texto": "Cliente 7. Pedidos: 2. Total: 800. Último pedido: P-7-2 mouse, 2026-01-04.",
        "meta": {
            "tipo": "cliente",
            "cliente_id": 7,
            "pedidos": 2,
            "total": 800,
            "ultimo": "P-7-2 mouse, 2026-01-04",
        },
    },
    {
        "id": "cliente-102",
        "texto": "Cliente 102. Pedidos: 3. Total: 14500. Último pedido: P-102-3 teclado, 2026-03-18.",
        "meta": {
            "tipo": "cliente",
            "cliente_id": 102,
            "pedidos": 3,
            "total": 14500,
            "ultimo": "P-102-3 teclado, 2026-03-18",
        },
    },
    {
        "id": "cliente-318",
        "texto": "Cliente 318. Pedidos: 5. Total: 22000. Último pedido: P-318-5 monitor, 2026-04-09.",
        "meta": {
            "tipo": "cliente",
            "cliente_id": 318,
            "pedidos": 5,
            "total": 22000,
            "ultimo": "P-318-5 monitor, 2026-04-09",
        },
    },
    {
        "id": "cliente-441",
        "texto": "Cliente 441. Pedidos: 1. Total: 3500. Último pedido: P-441-1 cable, 2026-01-15.",
        "meta": {
            "tipo": "cliente",
            "cliente_id": 441,
            "pedidos": 1,
            "total": 3500,
            "ultimo": "P-441-1 cable, 2026-01-15",
        },
    },
    {
        "id": "politica-reembolso",
        "texto": "La política de reembolso permite devolver dentro de 30 días si el pedido ya fue pagado.",
        "meta": {"tipo": "politica", "tema": "reembolso"},
    },
    {
        "id": "politica-envio",
        "texto": "El envío estándar tarda 5 días hábiles. El envío express tarda 48 horas.",
        "meta": {"tipo": "politica", "tema": "envio"},
    },
)

BY_ID = {doc["id"]: doc for doc in DOCS}


@lru_cache(maxsize=1)
def _collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(
        name=CHROMA_COLLECTION,
        embedding_function=embedding_functions.DefaultEmbeddingFunction(),
    )
    if collection.count() < len(DOCS):
        collection.upsert(
            ids=[doc["id"] for doc in DOCS],
            documents=[doc["texto"] for doc in DOCS],
            metadatas=[doc["meta"] for doc in DOCS],
        )
    return collection


def _bm25(docs: list[dict], consulta: str) -> list[str]:
    if not docs:
        return []
    tokenized = [doc["texto"].lower().split() for doc in docs]
    scores = BM25Okapi(tokenized).get_scores(consulta.lower().split())
    ranked = sorted(zip(docs, scores), key=lambda item: item[1], reverse=True)
    return [doc["id"] for doc, score in ranked if score > 0]


def _chroma(consulta: str, where: dict) -> list[str]:
    found = _collection().query(query_texts=[consulta], n_results=4, where=where)
    return (found.get("ids") or [[]])[0]


def _fusion(vector_ids: list[str], lexical_ids: list[str]) -> list[str]:
    scores: dict[str, float] = {}
    for ranking in (vector_ids, lexical_ids):
        for rank, doc_id in enumerate(ranking):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (60 + rank + 1)
    return sorted(scores, key=scores.get, reverse=True)


def _payload(consulta: str, ids: list[str]) -> str:
    docs = []
    for doc_id in ids[:5]:
        doc = BY_ID[doc_id]
        docs.append({"id": doc["id"], "texto": doc["texto"], "metadata": doc["meta"]})
    body: dict = {"consulta": consulta, "documentos": docs}
    if docs and docs[0]["metadata"].get("tipo") == "cliente":
        meta = docs[0]["metadata"]
        body.update(
            {
                "cliente_id": meta["cliente_id"],
                "pedidos": meta["pedidos"],
                "total": meta["total"],
                "ultimo": meta["ultimo"],
                "fuente": docs[0]["texto"],
            }
        )
    return json.dumps(body, ensure_ascii=False)


def _cliente(cliente_id: int) -> str:
    consulta = f"cliente {cliente_id} pedidos total"
    propios = [doc for doc in DOCS if doc["meta"].get("cliente_id") == cliente_id]
    if not propios:
        return json.dumps(
            {
                "error": "Cliente no encontrado",
                "cliente_id": cliente_id,
                "sugerencia": "Pedí que confirmen el id. No inventes el número.",
            },
            ensure_ascii=False,
        )
    ids = _fusion(
        _chroma(consulta, {"cliente_id": cliente_id}),
        _bm25(propios, consulta),
    )
    if not ids:
        ids = [propios[0]["id"]]
    return _payload(consulta, ids)


def _politica(consulta: str) -> str:
    politicas = [doc for doc in DOCS if doc["meta"].get("tipo") == "politica"]
    ids = _fusion(_chroma(consulta, {"tipo": "politica"}), _bm25(politicas, consulta))
    if not ids:
        return json.dumps(
            {"error": "Sin política en la base", "consulta": consulta},
            ensure_ascii=False,
        )
    return _payload(consulta, ids)


async def buscar_cliente(cliente_id: int) -> str:
    return await _trazar("rag.cliente", f"cliente {cliente_id}", _cliente, cliente_id)


async def buscar_politica(consulta: str) -> str:
    return await _trazar("rag.politica", consulta, _politica, consulta)


async def _trazar(name: str, consulta: str, fn, arg) -> str:
    tracer = trace.get_tracer("sistema.rag")
    with tracer.start_as_current_span(name) as span:
        span.set_attribute("openinference.span.kind", "RETRIEVER")
        span.set_attribute("input.value", consulta)
        payload = await asyncio.to_thread(fn, arg)
        span.set_attribute("output.value", payload[:2000])
        return payload
