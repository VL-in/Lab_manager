"""Exportação de conversas (DOCX), tabelas (CSV) e figuras (PNG)."""

from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd

try:
    from docx import Document
except ImportError:  # pragma: no cover
    Document = None  # type: ignore[misc, assignment]


def conversation_to_docx_bytes(messages: list[dict[str, Any]], title: str = "Exportação") -> bytes:
    if Document is None:
        raise RuntimeError("O pacote python-docx não está instalado.")
    doc = Document()
    doc.add_heading("Lab manager — conversa exportada", level=0)
    doc.add_paragraph(title, style="Intense Quote")
    for m in messages:
        role = m.get("role", "")
        label = "Usuário" if role == "user" else "Assistente"
        doc.add_heading(label, level=2)
        doc.add_paragraph(str(m.get("content", "")))
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    buf = BytesIO()
    # BOM para o Excel abrir acentuação corretamente no Windows
    buf.write("\ufeff".encode("utf-8"))
    buf.write(df.to_csv(index=False).encode("utf-8"))
    return buf.getvalue()


def figure_to_png_bytes(fig) -> bytes:
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)
    return buf.read()
