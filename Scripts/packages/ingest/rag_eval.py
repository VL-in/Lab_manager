"""Validacao basica de retrieval para RAG em pt-BR.

Espera um arquivo JSON com lista de casos:
[
  {"query": "...", "expected_chunk_id": "abc"},
  {"query": "...", "must_contain": "trecho esperado"}
]
"""

from __future__ import annotations

import argparse
import json
import os

import chromadb
from openai import OpenAI


def _embed_query(client: OpenAI, model: str, text: str) -> list[float]:
    r = client.embeddings.create(model=model, input=[text])
    return r.data[0].embedding


def main() -> None:
    parser = argparse.ArgumentParser(description="Avalia retrieval no Chroma.")
    parser.add_argument("--golden-set", required=True, help="Arquivo JSON com casos de teste")
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument("--chroma-host", default=os.getenv("CHROMA_HOST", "localhost"))
    parser.add_argument("--chroma-port", type=int, default=int(os.getenv("CHROMA_PORT", "8000")))
    parser.add_argument("--collection", default=os.getenv("CHROMA_COLLECTION", "lab_docs"))
    parser.add_argument("--lmstudio-base-url", default=os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1"))
    parser.add_argument("--embedding-model", default=os.getenv("LMSTUDIO_EMBEDDING_MODEL", "text-embedding-nomic-embed-text-v1.5"))
    parser.add_argument("--embedding-api-key", default=os.getenv("LMSTUDIO_API_KEY", "lm-studio"))
    args = parser.parse_args()

    with open(args.golden_set, "r", encoding="utf-8") as f:
        cases = json.load(f)

    openai_client = OpenAI(base_url=args.lmstudio_base_url.rstrip("/"), api_key=args.embedding_api_key)
    chroma = chromadb.HttpClient(host=args.chroma_host, port=args.chroma_port)
    collection = chroma.get_collection(args.collection)

    hits = 0
    for case in cases:
        query = case["query"]
        query_vector = _embed_query(openai_client, args.embedding_model, query)
        result = collection.query(query_embeddings=[query_vector], n_results=args.top_k)
        ids = result.get("ids", [[]])[0]
        docs = result.get("documents", [[]])[0]
        expected_chunk_id = case.get("expected_chunk_id")
        must_contain = case.get("must_contain")

        ok = False
        if expected_chunk_id and expected_chunk_id in ids:
            ok = True
        if must_contain and any(must_contain.lower() in (doc or "").lower() for doc in docs):
            ok = True
        if ok:
            hits += 1

    total = len(cases)
    recall_at_k = (hits / total) if total else 0.0
    print(json.dumps({"total": total, "hits": hits, "recall_at_k": recall_at_k}, ensure_ascii=True))


if __name__ == "__main__":
    main()
