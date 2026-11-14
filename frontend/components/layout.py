from collections.abc import Callable

import streamlit as st

from frontend.services.api_client import ApiError, SessionExpired


def apply_theme() -> None:
    st.markdown(
        """
        <style>
        :root { --ink: #172033; --muted: #64748b; --brand: #3157d5; --surface: #ffffff; }
        .stApp { background: #f5f7fb; color: var(--ink); }
        [data-testid="stSidebar"] { background: #101827; }
        [data-testid="stSidebar"] * { color: #e8edf7; }
        .hero { padding: 1.5rem 1.6rem; border-radius: 18px; background: linear-gradient(135deg,#203b91,#4f6fe8); color: white; margin-bottom: 1rem; }
        .hero h1 { margin: 0; font-size: 2rem; }
        .hero p { margin: .45rem 0 0; opacity: .84; }
        .metric-card { background: var(--surface); padding: 1rem; border-radius: 14px; border: 1px solid #e6eaf2; min-height: 100px; }
        .metric-label { color: var(--muted); font-size: .82rem; }
        .metric-value { color: var(--ink); font-size: 1.7rem; font-weight: 700; margin-top: .25rem; }
        .muted { color: var(--muted); }
        a { color: var(--brand); }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str = "") -> None:
    st.markdown(f'<div class="hero"><h1>{title}</h1><p>{subtitle}</p></div>', unsafe_allow_html=True)


def metric_card(label: str, value: str, help_text: str = "") -> None:
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div><div class="muted">{help_text}</div></div>',
        unsafe_allow_html=True,
    )


def run_page(render: Callable[[], None]) -> None:
    try:
        render()
    except SessionExpired as exc:
        st.session_state.clear()
        st.warning(exc.detail)
        st.rerun()
    except ApiError as exc:
        st.error(exc.detail)
