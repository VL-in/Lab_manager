import os

import streamlit as st

st.set_page_config(
    page_title="AI_lab_manager",
    page_icon="🧪",
    layout="wide",
)

st.title("AI_lab_manager")
st.caption("Laboratório — protótipo Streamlit + Flowise (Docker).")

flowise_internal = os.environ.get("FLOWISE_BASE_URL", "http://flowise:3000")
flowise_public_port = os.environ.get("FLOWISE_PUBLIC_PORT", "3000")

st.info(
    f"**Flowise** (orquestração): entre os contêineres use `{flowise_internal}`; "
    f"no navegador desta máquina use **http://localhost:{flowise_public_port}**."
)

st.markdown(
    """
- Ajuste os fluxos no **Flowise** e depois integre chamadas HTTP a partir desta UI.
- Variável útil no contêiner: `FLOWISE_BASE_URL` (já definida no `docker-compose`).
"""
)
