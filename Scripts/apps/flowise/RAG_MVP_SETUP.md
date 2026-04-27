# Flowise RAG MVP (LM Studio embeddings + Chroma)

Este guia configura o MVP de RAG no Flowise usando:
- LLM local no LM Studio para chat (`qwen/qwen3.5-9b`)
- modelo de embeddings no LM Studio via API OpenAI-compatible
- Chroma rodando no Docker Compose (`http://chroma:8000` dentro da rede)

## 1) Pré-requisitos
- Stack iniciada com `docker compose up --build -d`
- Variáveis no `.env`:
  - `FLOWISE_CHATFLOW_ID` (ID do endpoint `/api/v1/prediction/{id}`)
  - `CHROMA_PORT`, `CHROMA_COLLECTION`
  - `LMSTUDIO_BASE_URL`, `LMSTUDIO_EMBEDDING_MODEL`

## 2) Credenciais no Flowise
Na UI do Flowise:
1. Crie credencial OpenAI-compatible para LM Studio:
   - Base URL: `http://host.docker.internal:1234/v1`
   - API Key: `lm-studio` (ou a definida localmente)
2. Crie credencial Chroma:
   - Host: `chroma`
   - Port: `8000`
   - Collection: usar `CHROMA_COLLECTION`

## 3) Nós recomendados no Chatflow/AgentFlow
1. **Chat Model**: OpenAI-compatible apontando para LM Studio + `qwen/qwen3.5-9b`
2. **Embeddings**: OpenAI-compatible apontando para LM Studio + `LMSTUDIO_EMBEDDING_MODEL`
3. **Vector Store**: Chroma (collection do laboratório)
4. **Retriever**: top-k inicial de 4
5. **Prompt**:
   - responder em pt-BR
   - citar fontes (source_uri/chunk_id)
   - sinalizar quando não encontrar contexto suficiente

## 4) Contrato de metadados por chunk
Garanta que cada chunk em Chroma tenha:
- `chunk_id`
- `doc_id`
- `source_uri`
- `lang`
- `content_hash`
- `ingested_at`

## 5) Validação rápida
1. Ingerir documentos de teste em `packages/ingest/chroma_ingest.py`
2. Fazer 5-10 perguntas reais no Streamlit
3. Verificar:
   - se a resposta usa conteúdo recuperado
   - se cita fonte (`source_uri`/`chunk_id`)
   - se mantém resposta em pt-BR
