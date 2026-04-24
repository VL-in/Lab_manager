"""Lab manager — UI de chat (Flowise) com histórico persistente e exploração de dados."""

from __future__ import annotations

from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from chat_sessions import (
    Conversation,
    Message,
    infer_title_from_messages,
    load_store,
    new_conversation,
    save_store,
    touch,
)
from env_config import (
    get_flowise_api_key,
    get_flowise_base_url,
    get_flowise_chatflow_id,
    get_flowise_public_port,
)
from export_utils import conversation_to_docx_bytes, dataframe_to_csv_bytes, figure_to_png_bytes
from flowise_client import FlowiseError, predict


def _init_session() -> None:
    if st.session_state.get("_lab_init"):
        return
    disk, stored_current = load_store()

    if not disk:
        c = new_conversation()
        st.session_state.conversations = {c.id: c}
        st.session_state.current_id = c.id
        save_store(st.session_state.conversations, st.session_state.current_id)
    else:
        st.session_state.conversations = disk
        if stored_current and stored_current in disk:
            st.session_state.current_id = stored_current
        else:
            st.session_state.current_id = next(iter(disk.keys()))

    st.session_state._lab_init = True


def _current_conv() -> Conversation:
    cid = st.session_state.current_id
    return st.session_state.conversations[cid]


def _persist() -> None:
    save_store(st.session_state.conversations, st.session_state.current_id)


def _demo_dataframe() -> pd.DataFrame:
    if "demo_df" not in st.session_state:
        n = 120
        idx = pd.Series(range(n), dtype=int)
        status_cycle = [
            "rascunho",
            "rascunho",
            "validado",
            "validado",
            "validado",
            "validado",
            "validado",
            "validado",
            "validado",
            "em revisão",
        ]
        st.session_state.demo_df = pd.DataFrame(
            {
                "ensaio_id": [f"ENS-{i:03d}" for i in range(1, n + 1)],
                "lote": (idx % 3).map({0: "A1", 1: "B2", 2: "C3"}),
                "métrica_y": (idx * 7.13 % 40 + 85 + (idx % 5)).round(2),
                "temperatura_C": 18 + (idx % 8),
                "status": [status_cycle[i % 10] for i in range(n)],
            }
        )
    return st.session_state.demo_df


def _lab_css() -> None:
    st.markdown(
        """
        <style>
          :root {
            --lab-bg: #f6f7f9;
            --lab-panel: #ffffff;
            --lab-border: #e2e5eb;
            --lab-text: #1a1d24;
            --lab-muted: #5c6370;
            --lab-accent: #2563eb;
            --lab-accent-soft: #dbeafe;
          }
          .stApp { background: var(--lab-bg); color: var(--lab-text); }
          [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f172a 0%, #111827 100%);
            border-right: 1px solid #1f2937;
          }
          [data-testid="stSidebar"] .stMarkdown { color: #e5e7eb; }
          [data-testid="stSidebar"] label { color: #cbd5e1 !important; }
          [data-testid="stSidebar"] hr { border-color: #334155; }
          div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stChatMessage"]) {
            max-height: none;
          }
          [data-testid="stChatMessage"] {
            background: var(--lab-panel) !important;
            border: 1px solid var(--lab-border);
            border-radius: 12px;
          }
          .lab-hero {
            font-size: 1.35rem;
            font-weight: 600;
            letter-spacing: -0.02em;
            margin-bottom: 0.15rem;
          }
          .lab-sub {
            color: var(--lab-muted);
            font-size: 0.9rem;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(
        page_title="Lab manager",
        page_icon="🧪",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _lab_css()
    _init_session()

    flowise_base = get_flowise_base_url()
    flowise_public = get_flowise_public_port()
    chatflow_id = get_flowise_chatflow_id()
    api_key = get_flowise_api_key()
    has_flow = bool(chatflow_id)

    with st.sidebar:
        st.markdown('<p class="lab-hero" style="color:#f8fafc;">Lab manager</p>', unsafe_allow_html=True)
        st.caption("P&D · dados · relatórios")

        if st.button("➕ Nova conversa", use_container_width=True):
            c = new_conversation()
            st.session_state.conversations[c.id] = c
            st.session_state.current_id = c.id
            _persist()
            st.rerun()

        st.divider()
        st.markdown("**Histórico**")

        convs = sorted(st.session_state.conversations.values(), key=lambda x: x.updated_at, reverse=True)
        ids = [c.id for c in convs]

        def _conv_label(cid: str) -> str:
            c = st.session_state.conversations[cid]
            ts = c.updated_at[:16].replace("T", " ") if len(c.updated_at) >= 16 else c.updated_at
            return f"{c.title} · {ts}"

        try:
            idx = ids.index(st.session_state.current_id)
        except ValueError:
            idx = 0
        sel = st.selectbox(
            "Conversas",
            options=ids,
            index=idx,
            format_func=_conv_label,
            label_visibility="collapsed",
        )
        if sel != st.session_state.current_id:
            st.session_state.current_id = sel
            _persist()
            st.rerun()

        st.divider()
        st.markdown("**Flowise**")
        st.caption(f"Orquestração: `{flowise_base}`")
        st.caption(f"Na máquina local: [localhost:{flowise_public}](http://localhost:{flowise_public})")
        if has_flow:
            st.success("Chatflow configurado (variáveis de ambiente ou secrets).")
        else:
            st.warning(
                "Para respostas reais, defina o ID do chatflow apenas em variáveis de ambiente "
                "ou no arquivo `.streamlit/secrets.toml` — nunca no código versionado. "
                "Consulte o README."
            )

        if len(st.session_state.conversations) > 1:
            if st.button("Excluir conversa atual", use_container_width=True):
                cid = st.session_state.current_id
                del st.session_state.conversations[cid]
                st.session_state.current_id = next(iter(st.session_state.conversations.keys()))
                _persist()
                st.rerun()

    conv = _current_conv()
    col_main, col_meta = st.columns([2.1, 1], gap="large")

    with col_main:
        st.markdown('<p class="lab-hero">Assistente do laboratório</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="lab-sub">Converse com o fluxo no Flowise; à direita, explore dados tabulares e exporte artefatos.</p>',
            unsafe_allow_html=True,
        )

        prompt = st.chat_input("Mensagem para o assistente...")
        if prompt:
            conv.messages.append(Message(role="user", content=prompt))
            touch(conv)
            infer_title_from_messages(conv)
            _persist()

        for m in conv.messages:
            with st.chat_message(m.role):
                st.markdown(m.content)

        if prompt:
            with st.chat_message("assistant"):
                with st.spinner("Processando..."):
                    try:
                        reply = predict(
                            prompt,
                            session_id=conv.id,
                            base_url=flowise_base,
                            chatflow_id=chatflow_id,
                            api_key=api_key,
                        )
                    except FlowiseError as e:
                        reply = f"**Erro ao contatar o Flowise:**\n\n`{e}`"
                st.markdown(reply)
            conv.messages.append(Message(role="assistant", content=reply))
            touch(conv)
            infer_title_from_messages(conv)
            _persist()
            st.rerun()

    with col_meta:
        st.markdown("**Exportações rápidas**")
        msgs = [msg.to_dict() for msg in conv.messages]
        docx_bytes = conversation_to_docx_bytes(msgs, title=conv.title)
        st.download_button(
            label="Baixar conversa (.docx)",
            data=docx_bytes,
            file_name=f"conversa_{conv.id[:8]}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )

        tab_data, tab_viz = st.tabs(["Dados tabulares", "Figura / imagem"])

        with tab_data:
            st.caption("Dados fictícios para navegação (substituídos após integração).")
            df = _demo_dataframe()
            lotes = ["(todos)"] + sorted(df["lote"].unique().tolist())
            lot = st.selectbox("Filtrar por lote", lotes)
            status_opts = ["(todos)"] + sorted(df["status"].unique().tolist())
            st_f = st.selectbox("Filtrar por situação", status_opts)
            view = df
            if lot != "(todos)":
                view = view[view["lote"] == lot]
            if st_f != "(todos)":
                view = view[view["status"] == st_f]
            st.dataframe(view, use_container_width=True, height=280)
            csv_b = dataframe_to_csv_bytes(view)
            st.download_button(
                "Exportar tabela atual (.csv)",
                data=csv_b,
                file_name=f"tabela_filtrada_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True,
            )

        with tab_viz:
            st.caption("Gráfico de exemplo para testar exportação em PNG.")
            fig, ax = plt.subplots(figsize=(4.2, 2.8))
            sample = _demo_dataframe().groupby("lote", observed=True)["métrica_y"].mean()
            sample.plot(kind="bar", ax=ax, color="#2563eb", edgecolor="white")
            ax.set_xlabel("Lote")
            ax.set_ylabel("Média da métrica_y")
            ax.grid(axis="y", alpha=0.25)
            plt.tight_layout()
            st.session_state["_last_fig"] = fig
            st.pyplot(fig)
            png_b = figure_to_png_bytes(fig)
            plt.close(fig)
            st.download_button(
                "Exportar gráfico (.png)",
                data=png_b,
                file_name=f"grafico_{datetime.now().strftime('%Y%m%d_%H%M')}.png",
                mime="image/png",
                use_container_width=True,
            )


if __name__ == "__main__":
    main()
