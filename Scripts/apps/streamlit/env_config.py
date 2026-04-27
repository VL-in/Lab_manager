"""Leitura centralizada de configuração sensível.

Credenciais, IDs de chatflow e chaves de API não devem existir em arquivos
versionados: use apenas variáveis de ambiente (por exemplo, `.env` local,
ignorado pelo Git) ou `.streamlit/secrets.toml` (também fora do versionamento).

Este módulo é o único ponto em que `os.environ` e `st.secrets` são combinados
para esses valores. O restante da aplicação recebe strings já resolvidas.
"""

from __future__ import annotations

import os
from pathlib import Path

from elisa_duckdb import resolve_elisa_dir


def _strip_surrounding_quotes(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1].strip()
    return s


def _from_env(name: str) -> str | None:
    raw = os.environ.get(name)
    if raw is None:
        return None
    s = _strip_surrounding_quotes(str(raw))
    return s or None


def _from_streamlit_secrets(name: str) -> str | None:
    try:
        import streamlit as st

        val = st.secrets[name]
    except (ImportError, KeyError, FileNotFoundError, RuntimeError, TypeError, AttributeError):
        return None
    if val is None:
        return None
    s = _strip_surrounding_quotes(str(val).strip())
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


def get_elisa_xlsx_dir() -> str | None:
    """Pasta com arquivos `.xlsx` do ELISA (ambiente ou secrets; opcional)."""
    raw = get_config("ELISA_XLSX_DIR")
    if raw is None:
        return None
    return _strip_surrounding_quotes(raw)


def _running_in_docker() -> bool:
    return Path("/.dockerenv").is_file()


def _looks_like_windows_drive_path(s: str) -> bool:
    s = s.strip()
    return len(s) >= 2 and s[0].isalpha() and s[1] == ":"


def explain_missing_elisa_dir(configured: str | None, resolved: Path | None) -> str | None:
    """Texto de ajuda quando ELISA_XLSX_DIR está definido mas a pasta não é válida."""
    if not configured or resolved is not None:
        return None
    parts: list[str] = []
    if _running_in_docker() and _looks_like_windows_drive_path(configured):
        parts.append(
            "O valor parece um caminho do Windows (`D:\\...`), mas a aplicação corre em Linux "
            "dentro do Docker — esse caminho não existe no contêiner. "
            "No `docker-compose.yml` a pasta do host é montada em `/data/elisa` e "
            "`ELISA_XLSX_DIR` deve ser `/data/elisa` (já definido no Compose). "
            "Defina `ELISA_HOST_XLSX_DIR` no `.env` com a pasta **no Windows** onde estão os `.xlsx` "
            "(ex.: `ELISA_HOST_XLSX_DIR=D:/Laboratorio/ELISA`)."
        )
    else:
        p = Path(configured).expanduser()
        if not p.exists():
            parts.append(f"A pasta `{configured}` não existe neste sistema.")
        elif not p.is_dir():
            parts.append(f"`{configured}` existe mas não é uma pasta.")
        else:
            parts.append(f"A pasta `{configured}` não pôde ser usada (verifique permissões de leitura).")
        parts.append(
            "Remova aspas extra no `.env` se tiver colocado o caminho entre `\"...\"`. "
            "Use caminho absoluto. Em Docker, prefira `ELISA_HOST_XLSX_DIR` + `/data/elisa` no contêiner."
        )
    return " ".join(parts)


def resolve_elisa_dir_path() -> Path | None:
    """Caminho absoluto da pasta ELISA, ou None se não existir."""
    return resolve_elisa_dir(get_elisa_xlsx_dir())
