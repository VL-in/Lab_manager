"""Leitura centralizada de configuração sensível.

Credenciais, IDs de chatflow e chaves de API não devem existir em arquivos
versionados: use apenas variáveis de ambiente (por exemplo, `.env` local,
ignorado pelo Git) ou `.streamlit/secrets.toml` (também fora do versionamento).

Este módulo é o único ponto em que `os.environ` e `st.secrets` são combinados
para esses valores. O restante da aplicação recebe strings já resolvidas.
"""

from __future__ import annotations

import os


def _from_env(name: str) -> str | None:
    raw = os.environ.get(name)
    if raw is None:
        return None
    s = str(raw).strip()
    return s or None


def _from_streamlit_secrets(name: str) -> str | None:
    try:
        import streamlit as st

        val = st.secrets[name]
    except (ImportError, KeyError, FileNotFoundError, RuntimeError, TypeError, AttributeError):
        return None
    if val is None:
        return None
    s = str(val).strip()
    return s or None


def get_config(name: str) -> str | None:
    """Resolve uma entrada: ambiente tem prioridade, depois `st.secrets`."""
    return _from_env(name) or _from_streamlit_secrets(name)


def get_flowise_chatflow_id() -> str | None:
    return get_config("FLOWISE_CHATFLOW_ID")


def get_flowise_api_key() -> str | None:
    return get_config("FLOWISE_API_KEY")


def get_flowise_base_url() -> str:
    """URL do serviço Flowise (não é segredo; padrão para o Docker Compose)."""
    return get_config("FLOWISE_BASE_URL") or "http://flowise:3000"


def get_flowise_public_port() -> str:
    """Porta publicada no host (apenas para links na interface)."""
    return get_config("FLOWISE_PUBLIC_PORT") or "3000"
