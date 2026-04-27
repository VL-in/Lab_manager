"""Ingestão textual idempotente para Chroma com embeddings compatíveis com OpenAI.

Uso rápido:
  python packages/ingest/chroma_ingest.py --input-dir ./data/docs
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import chromadb
from openai import OpenAI


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _detect_lang(text: str) -> str:
    sample = text.lower()
    pt_hints = [" não ", " para ", " com ", " laboratório ", " ensaio "]
    return "pt-BR" if any(t in f" {sample} " for t in pt_hints) else "unknown"


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []
    chunks: list[str] = []
    step = max(1, chunk_size - overlap)
    for idx in range(0, len(cleaned), step):
        chunk = cleaned[idx : idx + chunk_size]
        if chunk:
            chunks.append(chunk)
        if idx + chunk_size >= len(cleaned):
            break
    return chunks


@dataclass(frozen=True)
class ChunkRecord:
    chunk_id: str
    text: str
    metadata: dict[str, str]


class EmbeddingClient:
    def __init__(self, base_url: str, model: str, api_key: str) -> None:
        self.model = model
        self.client = OpenAI(base_url=base_url.rstrip("/"), api_key=api_key)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self.client.embeddings.create(model=self.model, input=texts)
        return [item.embedding for item in response.data]


def _build_chunk_records(
    source_file: Path, text: str, *, chunk_size: int, overlap: int, default_project: str
) -> list[ChunkRecord]:
    source_uri = source_file.as_posix()
    doc_id = _sha256(source_uri)[:16]
    lang = _detect_lang(text)
    timestamp = _utc_now()
    chunks = _chunk_text(text, chunk_size=chunk_size, overlap=overlap)
    records: list[ChunkRecord] = []
    for idx, chunk in enumerate(chunks):
        content_hash = _sha256(chunk)
        chunk_id = f"{doc_id}:{idx}:{content_hash[:12]}"
        metadata = {
            "chunk_id": chunk_id,
            "doc_id": doc_id,
            "source_uri": source_uri,
            "lang": lang,
            "content_hash": content_hash,
            "ingested_at": timestamp,
            "project": default_project,
        }
        records.append(ChunkRecord(chunk_id=chunk_id, text=chunk, metadata=metadata))
    return records


def _iter_text_files(input_dir: Path) -> Iterable[Path]:
    for path in input_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".txt", ".md"}:
            yield path


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingere documentos textuais no Chroma.")
    parser.add_argument("--input-dir", required=True, help="Diretório com .txt/.md")
    parser.add_argument("--chroma-host", default=os.getenv("CHROMA_HOST", "localhost"))
    parser.add_argument("--chroma-port", type=int, default=int(os.getenv("CHROMA_PORT", "8000")))
    parser.add_argument("--collection", default=os.getenv("CHROMA_COLLECTION", "lab_docs"))
    parser.add_argument("--lmstudio-base-url", default=os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1"))
    parser.add_argument("--embedding-model", default=os.getenv("LMSTUDIO_EMBEDDING_MODEL", "text-embedding-nomic-embed-text-v1.5"))
    parser.add_argument("--embedding-api-key", default=os.getenv("LMSTUDIO_API_KEY", "lm-studio"))
    parser.add_argument("--chunk-size", type=int, default=900)
    parser.add_argument("--chunk-overlap", type=int, default=150)
    parser.add_argument("--project", default=os.getenv("LAB_PROJECT", "default"))
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        raise SystemExit(f"Diretório não encontrado: {input_dir}")

    chroma_client = chromadb.HttpClient(host=args.chroma_host, port=args.chroma_port)
    collection = chroma_client.get_or_create_collection(name=args.collection)
    embedder = EmbeddingClient(
        base_url=args.lmstudio_base_url,
        model=args.embedding_model,
        api_key=args.embedding_api_key,
    )

    total_chunks = 0
    for file_path in _iter_text_files(input_dir):
        raw_text = file_path.read_text(encoding="utf-8", errors="ignore")
        records = _build_chunk_records(
            file_path,
            raw_text,
            chunk_size=args.chunk_size,
            overlap=args.chunk_overlap,
            default_project=args.project,
        )
        if not records:
            continue

        ids = [r.chunk_id for r in records]
        docs = [r.text for r in records]
        metadatas = [r.metadata for r in records]
        vectors = embedder.embed(docs)

        # Idempotência: mesmo chunk_id + content_hash resulta em update determinístico.
        collection.upsert(ids=ids, documents=docs, metadatas=metadatas, embeddings=vectors)
        total_chunks += len(records)

    print(
        json.dumps(
            {
                "status": "ok",
                "collection": args.collection,
                "input_dir": str(input_dir),
                "total_chunks": total_chunks,
            },
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
