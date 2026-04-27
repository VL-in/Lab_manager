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
          /* O thread usa scroll da página (chat_input tem de ficar por último no script). */
          div[data-testid="stVerticalBlockBorderWrapper"]:has([data-testid="stChatMessage"]) {
            background: var(--lab-surface);
            border-radius: 12px;
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
          section[data-testid="stMain"] .block-container {
            padding-top: 1rem;
            padding-bottom: 0.5rem;
            max-width: 920px;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )
