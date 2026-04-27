"""Tema claro P&D — tokens CSS e injeção global para a UI Streamlit."""

from __future__ import annotations

import streamlit as st


def inject_theme() -> None:
    st.markdown(
        """
        <style>
          :root {
            --lab-bg: #eef1f6;
            --lab-surface: #ffffff;
            --lab-border: #d8dee8;
            --lab-text: #1c2430;
            --lab-muted: #5a6578;
            --lab-accent: #1e5a8a;
            --lab-accent-soft: #e4eef6;
            --lab-sidebar-bg: #f4f6fa;
          }
          .stApp {
            background: var(--lab-bg);
            color: var(--lab-text);
          }
          /* Melhor leitura em telas estreitas (celular / janela estreita). */
          @media (max-width: 768px) {
            section[data-testid="stMain"] .block-container {
              padding-left: 0.75rem;
              padding-right: 0.75rem;
            }
            [data-testid="stSidebar"] {
              box-shadow: 0 0 12px rgba(28, 36, 48, 0.12);
            }
          }
          [data-testid="stSidebar"] {
            background: var(--lab-sidebar-bg) !important;
            border-right: 1px solid var(--lab-border);
          }
          [data-testid="stSidebar"] .stMarkdown,
          [data-testid="stSidebar"] p,
          [data-testid="stSidebar"] span {
            color: var(--lab-text);
          }
          [data-testid="stSidebar"] .stCaption,
          [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
            color: var(--lab-muted) !important;
          }
          [data-testid="stSidebar"] label {
            color: var(--lab-text) !important;
          }
          [data-testid="stSidebar"] hr {
            border-color: var(--lab-border);
          }
          [data-testid="stSidebar"] a {
            color: var(--lab-accent);
          }
          [data-testid="stChatMessage"] {
            background: var(--lab-surface) !important;
            border: 1px solid var(--lab-border);
            border-radius: 10px;
            box-shadow: 0 1px 2px rgba(28, 36, 48, 0.04);
          }
          [data-testid="stChatMessage"] [data-testid="stVerticalBlock"] {
            gap: 0.35rem;
          }
          /* Área do thread de mensagens dentro do contêiner com borda. */
          div[data-testid="stVerticalBlockBorderWrapper"]:has([data-testid="stChatMessage"]) {
            background: var(--lab-surface);
            border-radius: 12px;
          }
          .lab-chat-empty {
            color: var(--lab-muted);
            font-size: 0.9rem;
            text-align: center;
            padding: 2rem 1rem;
            margin: 0;
          }
          .lab-hero {
            font-size: 1.25rem;
            font-weight: 600;
            letter-spacing: -0.02em;
            margin-bottom: 0.1rem;
            color: var(--lab-text);
          }
          .lab-sub {
            color: var(--lab-muted);
            font-size: 0.875rem;
            line-height: 1.45;
            margin-bottom: 0.75rem;
          }
          .lab-sidebar-brand {
            font-size: 1.05rem;
            font-weight: 600;
            letter-spacing: -0.01em;
            color: var(--lab-text);
            margin-bottom: 0.05rem;
          }
          .lab-sidebar-tag {
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: var(--lab-muted);
            margin-bottom: 0.75rem;
          }
          /*
           * Espaço para o cabeçalho nativo do Streamlit (menu, tema, “Deploy”).
           * padding-top muito baixo faz as abas e o primeiro conteúdo ficarem
           * atrás do cabeçalho e deixam de ser clicáveis.
           */
          section[data-testid="stMain"] .block-container {
            padding-top: max(5.5rem, calc(1rem + 3.75rem));
            padding-bottom: 0.5rem;
            max-width: min(1100px, 100%);
          }
          /* Tabelas e área de dados: cantos alinhados ao resto da UI. */
          [data-testid="stDataFrame"] {
            border-radius: 8px;
          }
          /* Campo de mensagem abaixo da área de conversa: respiro e leitura em fundo claro. */
          [data-testid="stChatInput"] {
            margin-top: 0.75rem;
            background: var(--lab-surface);
            border-radius: 12px;
            border: 1px solid var(--lab-border);
          }
        </style>
        """,
        unsafe_allow_html=True,
    )
