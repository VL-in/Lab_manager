"""Interface Streamlit para consultar dados ELISA via DuckDB."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from elisa_duckdb import list_xlsx_files, load_xlsx_into_duckdb, run_sql
from env_config import get_elisa_xlsx_dir, resolve_elisa_dir_path


def _fingerprint(directory: Path) -> tuple[tuple[str, int], ...]:
    files = list_xlsx_files(directory)
    return tuple((f.name, int(f.stat().st_mtime_ns)) for f in files)


def _ensure_db(directory: Path) -> None:
    fp = _fingerprint(directory)
    if st.session_state.get("_elisa_fp") == fp and st.session_state.get("_elisa_con") is not None:
        return
    con, tables, warns = load_xlsx_into_duckdb(directory)
    st.session_state._elisa_fp = fp
    st.session_state._elisa_con = con
    st.session_state._elisa_tables = tables
    st.session_state._elisa_warns = warns


def _clear_elisa_cache() -> None:
    for k in ("_elisa_fp", "_elisa_con", "_elisa_tables", "_elisa_warns"):
        st.session_state.pop(k, None)


def render_elisa_query_tab() -> None:
    st.markdown(
        '<p class="lab-sub">Consulta interativa aos resultados em Excel (DuckDB em memória).</p>',
        unsafe_allow_html=True,
    )

    configured = get_elisa_xlsx_dir()
    resolved = resolve_elisa_dir_path()

    st.caption(
        "Pasta ativa: "
        + (f"`{resolved}`" if resolved else "— (defina `ELISA_XLSX_DIR` ou coloque os `.xlsx` em `Example/results/ELISA` ao lado de `Scripts`)")
    )
    if configured:
        st.caption(f"Variável / secrets: `ELISA_XLSX_DIR` = `{configured}`")

    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("Recarregar Excel", use_container_width=True):
            _clear_elisa_cache()
            st.rerun()

    if resolved is None:
        st.warning(
            "Não foi encontrada uma pasta válida. Defina a variável de ambiente ou "
            "`ELISA_XLSX_DIR` em `.streamlit/secrets.toml` com o caminho absoluto da pasta "
            "que contém os `.xlsx` (por exemplo o caminho no Windows que indicou)."
        )
        return

    files = list_xlsx_files(resolved)
    if not files:
        st.info(f"Nenhum ficheiro `.xlsx` em `{resolved}`.")
        return

    st.caption("Ficheiros: " + ", ".join(f"`{f.name}`" for f in files))

    _ensure_db(resolved)
    warns: list[str] = st.session_state.get("_elisa_warns") or []
    for w in warns:
        st.warning(w)

    con = st.session_state._elisa_con
    tables: list[str] = st.session_state._elisa_tables

    if not tables:
        st.error("Não foi possível criar tabelas a partir dos Excel.")
        return

    default_tbl = tables[0]
    pick = st.selectbox("Tabela (pré-visualização)", options=tables, index=0)
    try:
        preview = run_sql(con, f'SELECT * FROM "{pick}" LIMIT 200')
        st.dataframe(preview, use_container_width=True, hide_index=True)
    except Exception as e:  # noqa: BLE001
        st.error(f"Erro na pré-visualização: {e}")

    st.divider()
    st.markdown("**SQL**")
    hint = f'SELECT * FROM "{default_tbl}" LIMIT 50'
    sql = st.text_area(
        "Consulta DuckDB",
        value=st.session_state.get("_elisa_sql_draft", hint),
        height=160,
        label_visibility="collapsed",
        placeholder=hint,
    )
    st.session_state["_elisa_sql_draft"] = sql

    if st.button("Executar SQL", type="primary"):
        if not sql.strip():
            st.warning("Escreva uma consulta SQL.")
        else:
            try:
                out = run_sql(con, sql)
                st.success(f"{len(out)} linhas × {len(out.columns)} colunas")
                st.dataframe(out, use_container_width=True, hide_index=True)
            except Exception as e:  # noqa: BLE001
                st.error(f"Erro SQL: {e}")

    with st.expander("Ajuda rápida"):
        st.markdown(
            f"""
- Tabelas disponíveis: {", ".join(f"`{t}`" for t in tables)}.
- Use aspas duplas nos identificadores se tiver caracteres especiais: `SELECT * FROM "{default_tbl}" LIMIT 10`.
- Sintaxe [DuckDB SQL](https://duckdb.org/docs/sql/introduction).
"""
        )
