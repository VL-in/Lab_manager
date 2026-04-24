"""Cliente HTTP para o endpoint de predição do Flowise.

Credenciais e IDs são passados pelo chamador (em geral resolvidos em `env_config`
a partir do ambiente ou de `st.secrets`), não lidos neste módulo.
"""

from __future__ import annotations

from typing import Any

import requests


class FlowiseError(Exception):
    pass


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
        return (
            "[modo demonstração — chatflow não configurado no ambiente seguro]\n\n"
            "Defina o ID do chatflow apenas em variáveis de ambiente ou no arquivo "
            "`.streamlit/secrets.toml` (nunca no código-fonte). "
            f"Prévia da pergunta: {question[:500]}"
        )

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

    text = data.get("text")
    if isinstance(text, str) and text.strip():
        return text
    if isinstance(data, dict) and "data" in data:
        inner = data["data"]
        if isinstance(inner, str):
            return inner
    return str(data)
