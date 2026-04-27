"""Interface Streamlit para consultar dados ELISA via DuckDB."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from elisa_duckdb import list_xlsx_files, load_xlsx_into_duckdb, run_sql
from env_config import explain_missing_elisa_dir, get_elisa_xlsx_dir, resolve_elisa_dir_path


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


def _column_config_for_df(df: pd.DataFrame) -> dict:
    """Configuração de colunas para leitura em browser (números, datas, texto)."""
    cfg: dict = {}
    for col in df.columns:
        s = df[col]
        if pd.api.types.is_numeric_dtype(s):
            cfg[col] = st.column_config.NumberColumn(col, format="%.4g", width="small")
        elif pd.api.types.is_datetime64_any_dtype(s):
            cfg[col] = st.column_config.DatetimeColumn(col, width="medium")
        else:
            cfg[col] = st.column_config.TextColumn(col, width="medium")
    return cfg


def _first_numeric_series(df: pd.DataFrame) -> tuple[str, pd.Series] | None:
    for col in df.columns:
        s = df[col]
        if pd.api.types.is_numeric_dtype(s) and s.notna().any():
            return col, s
    return None


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
   
    hint = explain_missing_elisa_dir(configured, resolved)
    if hint:
        st.warning(hint)

    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("Recarregar Excel", use_container_width=True):
            _clear_elisa_cache()
            st.session_state.pop("_elisa_query_ok", None)
            st.session_state.pop("_elisa_query_err", None)
            st.rerun()

    if resolved is None:
        if not hint:
            if Path("/.dockerenv").is_file():
                st.warning(
                    "Não foi encontrada a pasta de dados ELISA. No Docker o caminho no contêiner "
                    "é `/data/elisa` (definido no `docker-compose.yml`). Confirme o volume que monta "
                    "os Excel do host (por padrão `./Example/results/ELISA` ao lado do `docker-compose.yml`) "
                    "ou defina `ELISA_HOST_XLSX_DIR` no `.env` com a pasta absoluta no Windows, "
                    "ex.: `ELISA_HOST_XLSX_DIR=D:/Laboratorio/ELISA`, e execute `docker compose up -d`."
                )
            else:
                st.warning(
                    "Não foi encontrada uma pasta válida. Defina `ELISA_XLSX_DIR` no ambiente ou em "
                    "`.streamlit/secrets.toml` com o caminho absoluto da pasta que contém os `.xlsx` "
                    "(caminho Linux/macOS ou Windows, conforme onde corre o Streamlit)."
                )
        return

    files = list_xlsx_files(resolved)
    if not files:
        msg = f"Nenhum arquivo `.xlsx` em `{resolved}`."
        if Path("/.dockerenv").is_file():
            msg += (
                " Coloque arquivos `.xlsx` nessa pasta no **host** (é uma montagem somente leitura) "
                "ou ajuste `ELISA_HOST_XLSX_DIR` no `.env` e recrie o serviço: `docker compose up -d`."
            )
        st.info(msg)
        return

    st.caption("Arquivos carregados: " + ", ".join(f"`{f.name}`" for f in files))

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
    preview_height = 320
    try:
        preview = run_sql(con, f'SELECT * FROM "{pick}" LIMIT 200')
        st.caption(f"Pré-visualização: até 200 linhas · {len(preview.columns)} colunas")
        st.dataframe(
            preview,
            use_container_width=True,
            hide_index=True,
            height=preview_height,
            column_config=_column_config_for_df(preview),
        )
        num = _first_numeric_series(preview)
        if num is not None and len(preview) > 1:
            col_name, series = num
            with st.expander("Gráfico rápido (primeira coluna numérica)", expanded=False):
                chart_df = preview[[col_name]].copy()
                chart_df.index = preview.index
                st.caption(f"Coluna: `{col_name}` (índice = ordem das linhas na pré-visualização)")
                st.bar_chart(chart_df, height=260, use_container_width=True)
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

    run = st.button("Executar SQL", type="primary")
    if run:
        st.session_state.pop("_elisa_query_ok", None)
        st.session_state.pop("_elisa_query_err", None)
        if not sql.strip():
            st.session_state["_elisa_query_err"] = "Escreva uma consulta SQL."
        else:
            try:
                out = run_sql(con, sql)
                st.session_state["_elisa_query_ok"] = {"df": out, "sql": sql.strip()}
            except Exception as e:  # noqa: BLE001
                st.session_state["_elisa_query_err"] = str(e)

    err = st.session_state.get("_elisa_query_err")
    ok = st.session_state.get("_elisa_query_ok")
    if err:
        if str(err).startswith("Escreva"):
            st.warning(err)
        else:
            st.error(f"Erro SQL: {err}")
    if ok:
        out: pd.DataFrame = ok["df"]
        st.success(f"{len(out)} linhas × {len(out.columns)} colunas")
        result_height = min(520, max(220, 14 * min(len(out), 36) + 40))
        st.dataframe(
            out,
            use_container_width=True,
            hide_index=True,
            height=result_height,
            column_config=_column_config_for_df(out),
        )
        csv_bytes = out.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="Baixar resultado (.csv)",
            data=csv_bytes,
            file_name="elisa_consulta.csv",
            mime="text/csv",
            use_container_width=False,
        )
        num = _first_numeric_series(out)
        if num is not None and len(out) > 1:
            cname, _ = num
            with st.expander("Gráfico do resultado (coluna numérica)", expanded=False):
                st.bar_chart(out[[cname]], height=280, use_container_width=True)

    with st.expander("Ajuda rápida"):
        st.markdown(
            f"""
- Tabelas disponíveis: {", ".join(f"`{t}`" for t in tables)}.
- Use aspas duplas nos identificadores se tiver caracteres especiais: `SELECT * FROM "{default_tbl}" LIMIT 10`.
- Sintaxe [DuckDB SQL](https://duckdb.org/docs/sql/introduction).
"""
        )
