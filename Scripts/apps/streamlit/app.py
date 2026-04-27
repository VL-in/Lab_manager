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
from export_utils import conversation_to_docx_bytes
from flowise_client import FlowiseError, predict
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


def main() -> None:
    st.set_page_config(
        page_title="Lab manager",
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
        st.markdown('<p class="lab-sidebar-brand">Lab manager</p>', unsafe_allow_html=True)
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
            st.success("Flow ID configurado (Chatflow/AgentFlow).")
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

    st.markdown('<p class="lab-hero">Assistente do laboratório</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="lab-sub">Diálogo com o fluxo configurado no Flowise. O histórico fica guardado entre sessões.</p>',
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        for m in conv.messages:
            with st.chat_message(m.role):
                st.markdown(m.content)

    prompt = st.chat_input("Escreva a sua mensagem…")

    if prompt:
        conv.messages.append(Message(role="user", content=prompt))
        touch(conv)
        infer_title_from_messages(conv)
        _persist()
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("A processar…"):
                try:
                    reply = predict(
                        prompt,
                        session_id=conv.id,
                        base_url=flowise_base,
                        chatflow_id=flow_id,
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


if __name__ == "__main__":
    main()
