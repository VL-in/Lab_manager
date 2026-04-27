"""Lab manager — UI de chat (Flowise) com histórico persistente e exportação de conversa."""

from __future__ import annotations

import streamlit as st

from chat_sessions import (
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
from elisa_ui import render_elisa_query_tab
from export_utils import conversation_to_docx_bytes
from flowise_client import FlowiseError, iter_flowise_token_deltas
from theme import inject_theme


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


def _current_conv():
    cid = st.session_state.current_id
    return st.session_state.conversations[cid]


def _persist() -> None:
    save_store(st.session_state.conversations, st.session_state.current_id)


def _consume_pending_chat_user(conv) -> bool:
    """Se o usuário enviou na rodada anterior, grava a mensagem e sinaliza streaming na próxima parte do layout."""
    raw = st.session_state.pop("_lab_pending_user", None)
    if raw is None:
        return False
    if isinstance(raw, tuple) and len(raw) == 2:
        cid, pending = raw
        if cid != conv.id:
            st.session_state["_lab_pending_user"] = raw
            return False
    else:
        pending = raw
    pending = str(pending).strip()
    if not pending:
        return False
    conv.messages.append(Message(role="user", content=pending))
    touch(conv)
    infer_title_from_messages(conv)
    _persist()
    st.session_state["_lab_stream_assistant_cid"] = conv.id
    return True


def main() -> None:
    st.set_page_config(
        page_title="Assistente de laboratório",
        page_icon="🧪",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_theme()
    _init_session()

    flowise_base = get_flowise_base_url()
    flowise_public = get_flowise_public_port()
    flow_id = get_flowise_chatflow_id()
    api_key = get_flowise_api_key()
    has_flow = bool(flow_id)

    conv = _current_conv()

    with st.sidebar:
        st.markdown('<p class="lab-sidebar-brand">Assistente de laboratório</p>', unsafe_allow_html=True)
        st.markdown('<p class="lab-sidebar-tag">P&D · assistente</p>', unsafe_allow_html=True)

        if st.button("Nova conversa", use_container_width=True, type="primary"):
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
        st.markdown("**Exportar**")
        msgs = [msg.to_dict() for msg in conv.messages]
        try:
            docx_bytes = conversation_to_docx_bytes(msgs, title=conv.title)
        except RuntimeError as e:
            st.caption(str(e))
            docx_bytes = b""
        if docx_bytes:
            st.download_button(
                label="Conversa (.docx)",
                data=docx_bytes,
                file_name=f"conversa_{conv.id[:8]}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )

        st.divider()
        st.markdown("**Flowise**")
        st.caption(f"API: `{flowise_base}` · [local:{flowise_public}](http://localhost:{flowise_public})")
        if has_flow:
            st.success("ID do fluxo configurado (Chatflow/AgentFlow).")
        else:
            st.warning(
                "Defina o ID do Flowise (Chatflow ou AgentFlow) em variáveis de ambiente "
                "ou em `.streamlit/secrets.toml` "
                "(nunca no código versionado). Ver README."
            )

        if len(st.session_state.conversations) > 1:
            if st.button("Excluir conversa atual", use_container_width=True):
                cid = st.session_state.current_id
                del st.session_state.conversations[cid]
                st.session_state.current_id = next(iter(st.session_state.conversations.keys()))
                _persist()
                st.rerun()

    tab_chat, tab_elisa = st.tabs(["Assistente", "Dados ELISA (DuckDB)"])

    with tab_chat:
        st.markdown('<p class="lab-hero">Assistente do laboratório</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="lab-sub">Diálogo com o fluxo configurado no Flowise. O histórico fica guardado entre sessões.</p>',
            unsafe_allow_html=True,
        )

        _consume_pending_chat_user(conv)

        # Área com scroll: conversa acima; o campo de texto fica abaixo (fora deste bloco).
        chat_height = 440
        with st.container(height=chat_height, border=True):
            if not conv.messages:
                st.markdown(
                    '<p class="lab-chat-empty">Envie uma pergunta sobre protocolos, resultados ou documentação do laboratório.</p>',
                    unsafe_allow_html=True,
                )
            for m in conv.messages:
                with st.chat_message(m.role):
                    st.markdown(m.content)
            if st.session_state.get("_lab_stream_assistant_cid") == conv.id:
                del st.session_state["_lab_stream_assistant_cid"]
                question = conv.messages[-1].content if conv.messages else ""
                with st.chat_message("assistant"):
                    chunks: list[str] = []

                    def _token_stream():
                        try:
                            for delta in iter_flowise_token_deltas(
                                question,
                                session_id=conv.id,
                                base_url=flowise_base,
                                chatflow_id=flow_id,
                                api_key=api_key,
                            ):
                                chunks.append(delta)
                                yield delta
                        except FlowiseError as e:
                            err = f"**Erro ao contatar o Flowise:**\n\n`{e}`"
                            chunks.append(err)
                            yield err

                    st.write_stream(_token_stream)
                    reply = "".join(chunks)
                conv.messages.append(Message(role="assistant", content=reply))
                touch(conv)
                infer_title_from_messages(conv)
                _persist()
                st.rerun()

        prompt = st.chat_input("Escreva a sua mensagem…", key=f"lab_chat_input_{conv.id}")
        if prompt and str(prompt).strip():
            st.session_state["_lab_pending_user"] = (conv.id, str(prompt).strip())
            st.rerun()

    with tab_elisa:
        render_elisa_query_tab()


if __name__ == "__main__":
    main()
