"""Cliente HTTP para o endpoint de predição do Flowise.

Credenciais e IDs são passados pelo chamador (em geral resolvidos em `env_config`
a partir do ambiente ou de `st.secrets`), não lidos neste módulo.

Streaming: com `streaming: true`, o Flowise envia eventos no formato
`message:\\ndata:` + JSON (`event` / `data`) por bloco SSE (ver `SSEStreamer.ts`).
"""

from __future__ import annotations

import json
from typing import Any, Iterator

import requests


class FlowiseError(Exception):
    pass


def _demo_text(question: str) -> str:
    return (
        "[modo demonstração — chatflow não configurado no ambiente seguro]\n\n"
        "Defina o ID do chatflow apenas em variáveis de ambiente ou no arquivo "
        "`.streamlit/secrets.toml` (nunca no código-fonte). "
        f"Prévia da pergunta: {question[:500]}"
    )


def _extract_text_from_prediction_json(data: dict[str, Any]) -> str:
    text = data.get("text")
    if isinstance(text, str) and text.strip():
        return text
    inner = data.get("data")
    if isinstance(inner, str):
        return inner
    return str(data)


def predict(
    question: str,
    *,
    session_id: str,
    base_url: str,
    chatflow_id: str | None,
    api_key: str | None = None,
    timeout_s: int = 120,
) -> str:
    base = base_url.rstrip("/")
    cid = (chatflow_id or "").strip()
    if not cid:
        return _demo_text(question)

    url = f"{base}/api/v1/prediction/{cid}"
    headers: dict[str, str] = {"Content-Type": "application/json"}
    key = (api_key or "").strip()
    if key:
        headers["Authorization"] = f"Bearer {key}"

    body: dict[str, Any] = {
        "question": question,
        "sessionId": session_id,
    }

    try:
        r = requests.post(url, json=body, headers=headers, timeout=timeout_s)
    except requests.RequestException as e:
        raise FlowiseError(f"Falha de rede ao contatar o Flowise: {e}") from e

    if r.status_code >= 400:
        snippet = (r.text or "")[:200].replace("\n", " ")
        raise FlowiseError(f"Flowise HTTP {r.status_code}: {snippet}")

    try:
        data = r.json()
    except ValueError as e:
        raise FlowiseError("A resposta do Flowise não é um JSON válido.") from e

    return _extract_text_from_prediction_json(data)


def _parse_sse_json_block(block: str) -> tuple[str, Any] | None:
    """Extrai um par (event, data) do bloco SSE do Flowise, ou None."""
    for line in block.split("\n"):
        line = line.strip("\r")
        if not line.startswith("data:"):
            continue
        raw = line[5:].strip()
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            return None
        ev = obj.get("event")
        if not isinstance(ev, str):
            ev = str(ev or "")
        return ev, obj.get("data")
    return None


def _iter_sse_token_events(r: requests.Response) -> Iterator[str]:
    buffer = ""
    for chunk in r.iter_content(chunk_size=4096):
        if not chunk:
            continue
        if isinstance(chunk, bytes):
            chunk = chunk.decode("utf-8", errors="replace")
        buffer += chunk
        while "\n\n" in buffer:
            block, buffer = buffer.split("\n\n", 1)
            block_st = block.strip()
            if not block_st or block_st.startswith(":"):
                continue
            parsed = _parse_sse_json_block(block_st)
            if parsed is None:
                continue
            event, data = parsed
            if event == "token":
                if isinstance(data, str):
                    yield data
                elif data is not None:
                    yield str(data)
            elif event == "error":
                raise FlowiseError(str(data))
            elif event == "end":
                return


def iter_flowise_token_deltas(
    question: str,
    *,
    session_id: str,
    base_url: str,
    chatflow_id: str | None,
    api_key: str | None = None,
    timeout_s: int = 120,
) -> Iterator[str]:
    """Gera fragmentos de texto à medida que o Flowise os envia (SSE).

    Em modo demonstração (sem chatflow), emite o texto em fatias para a UI
    poder mostrar progressão.
    """
    base = base_url.rstrip("/")
    cid = (chatflow_id or "").strip()
    if not cid:
        text = _demo_text(question)
        step = max(16, min(48, len(text) // 30 or 16))
        for i in range(0, len(text), step):
            yield text[i : i + step]
        return

    url = f"{base}/api/v1/prediction/{cid}"
    headers: dict[str, str] = {"Content-Type": "application/json", "Accept": "text/event-stream, application/json"}
    key = (api_key or "").strip()
    if key:
        headers["Authorization"] = f"Bearer {key}"

    body: dict[str, Any] = {
        "question": question,
        "sessionId": session_id,
        "streaming": True,
    }

    try:
        with requests.post(url, json=body, headers=headers, stream=True, timeout=timeout_s) as r:
            if r.status_code >= 400:
                snippet = (r.text or "")[:300].replace("\n", " ")
                raise FlowiseError(f"Flowise HTTP {r.status_code}: {snippet}")

            ct = (r.headers.get("Content-Type") or "").lower()
            if "application/json" in ct:
                try:
                    data = r.json()
                except ValueError as e:
                    raise FlowiseError("A resposta do Flowise não é um JSON válido.") from e
                yield _extract_text_from_prediction_json(data)
                return

            yielded = False
            for delta in _iter_sse_token_events(r):
                yielded = True
                yield delta

        if not yielded:
            # Resposta vazia ou eventos não reconhecidos: uma chamada síncrona evita ecrã em branco.
            yield predict(
                question,
                session_id=session_id,
                base_url=base_url,
                chatflow_id=cid,
                api_key=api_key,
                timeout_s=timeout_s,
            )
    except requests.RequestException as e:
        raise FlowiseError(f"Falha de rede ao contatar o Flowise: {e}") from e
