"""Carrega folhas de Excel (ELISA) numa base DuckDB em memória para consulta SQL."""

from __future__ import annotations

import re
from pathlib import Path

import duckdb
import pandas as pd


def _sanitize_sql_id(raw: str) -> str:
    s = re.sub(r"[^0-9a-zA-Z_]+", "_", raw.strip()).strip("_").lower()
    if not s:
        s = "t"
    if s[0].isdigit():
        s = "t_" + s
    return s[:63]


def default_elisa_dir_from_repo() -> Path | None:
    """Procura `Example/results/ELISA` a partir da pasta deste módulo (repo local ou layout em /app)."""
    start = Path(__file__).resolve().parent
    for base in [start, *start.parents]:
        candidate = base / "Example" / "results" / "ELISA"
        if candidate.is_dir():
            return candidate
    return None


def resolve_elisa_dir(explicit: str | None) -> Path | None:
    if explicit:
        p = Path(explicit).expanduser()
        return p if p.is_dir() else None
    d = default_elisa_dir_from_repo()
    if d is not None:
        return d
    return None


def list_xlsx_files(directory: Path) -> list[Path]:
    return sorted(directory.glob("*.xlsx"), key=lambda p: p.name.lower())


def load_xlsx_into_duckdb(directory: Path) -> tuple[duckdb.DuckDBPyConnection, list[str], list[str]]:
    """Devolve (conexão, nomes de tabelas, avisos)."""
    warnings: list[str] = []
    files = list_xlsx_files(directory)
    if not files:
        con = duckdb.connect(":memory:")
        return con, [], warnings

    con = duckdb.connect(":memory:")
    table_names: list[str] = []
    used: set[str] = set()

    for path in files:
        stem = _sanitize_sql_id(path.stem)
        try:
            xl = pd.ExcelFile(path, engine="openpyxl")
        except Exception as e:  # noqa: BLE001 — UI de laboratório
            warnings.append(f"{path.name}: não foi possível abrir ({e})")
            continue

        sheets = xl.sheet_names
        if not sheets:
            warnings.append(f"{path.name}: sem folhas.")
            continue

        for sheet in sheets:
            try:
                df = pd.read_excel(path, sheet_name=sheet, engine="openpyxl")
            except Exception as e:  # noqa: BLE001
                warnings.append(f"{path.name} / {sheet}: erro ao ler ({e})")
                continue

            if len(sheets) == 1:
                base = stem
            else:
                base = f"{stem}_{_sanitize_sql_id(sheet)}"

            tname = base
            n = 2
            while tname in used:
                tname = f"{base}_{n}"
                n += 1
            used.add(tname)

            tmp = f"_tmp_{tname}"
            con.register(tmp, df)
            con.execute(f'CREATE TABLE "{tname}" AS SELECT * FROM "{tmp}"')
            con.unregister(tmp)
            table_names.append(tname)

    return con, sorted(table_names), warnings


def run_sql(con: duckdb.DuckDBPyConnection, sql: str) -> pd.DataFrame:
    return con.sql(sql).df()
