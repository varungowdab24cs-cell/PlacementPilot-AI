from collections.abc import Callable

import streamlit as st

from frontend.services.api_client import ApiError, SessionExpired


def apply_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            --canvas: #0b0b0c;
            --sidebar: #101011;
            --surface: #151516;
            --surface-raised: #1b1b1d;
            --line: #2b2b2e;
            --ink: #f2f2f0;
            --muted: #97979b;
            --faint: #69696e;
            --brand: #c7f36b;
            --accent: #8db4ff;
            --danger: #ff8e8e;
        }

        html, body, [class*="css"] { font-family: "IBM Plex Mono", "SFMono-Regular", Consolas, monospace; }
        .stApp { background: var(--canvas); color: var(--ink); }
        [data-testid="stHeader"] { background: var(--canvas); }
        [data-testid="stSidebar"] {
            background: var(--sidebar);
            border-right: 1px solid var(--line);
            min-width: 250px;
        }
        [data-testid="stSidebar"] > div:first-child { padding: 1.1rem .85rem; }
        [data-testid="stSidebar"] * { color: var(--ink); }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
            color: var(--muted);
            font-size: .72rem;
            letter-spacing: .08em;
            text-transform: uppercase;
        }
        [data-testid="stSidebar"] button {
            border-radius: 5px;
            border: 1px solid transparent;
            background: transparent;
            color: var(--muted);
            text-align: left;
        }
        [data-testid="stSidebar"] button:hover {
            border-color: var(--line);
            background: var(--surface-raised);
            color: var(--ink);
        }
        [data-testid="stSidebar"] [aria-current="page"] {
            background: #242424;
            border-left: 2px solid var(--brand);
            color: var(--brand);
        }
        [data-testid="stSidebar"] hr { border-color: var(--line); }

        .brand-lockup {
            display: flex;
            align-items: center;
            gap: .65rem;
            margin: .15rem .25rem 1.7rem;
        }
        .brand-mark {
            display: grid;
            width: 30px;
            height: 30px;
            place-items: center;
            border: 1px solid var(--brand);
            color: var(--brand);
            font-weight: 700;
            font-size: .9rem;
        }
        .brand-name { color: var(--ink); font-size: .92rem; font-weight: 700; }
        .brand-caption { color: var(--faint); font-size: .62rem; margin-top: .12rem; }

        .main .block-container {
            max-width: 1320px;
            padding: 3.2rem clamp(1.2rem, 5vw, 5rem) 4rem;
        }
        .hero {
            padding: 0 0 2.2rem;
            margin-bottom: 1.7rem;
            border-bottom: 1px solid var(--line);
            background: transparent;
            color: var(--ink);
        }
        .hero h1 {
            margin: 0;
            max-width: 950px;
            font-size: clamp(2rem, 4vw, 4.2rem);
            font-weight: 400;
            letter-spacing: -.08em;
            line-height: 1.02;
        }
        .hero p {
            max-width: 760px;
            margin: .9rem 0 0;
            color: var(--muted);
            font-size: .9rem;
            line-height: 1.7;
        }
        h1, h2, h3, h4 { letter-spacing: -.04em; font-weight: 500; }
        h2 { margin-top: 2rem; }
        .metric-card {
            min-height: 112px;
            padding: 1.1rem 1.2rem;
            border: 1px solid var(--line);
            border-radius: 3px;
            background: var(--surface);
        }
        .metric-label {
            color: var(--muted);
            font-size: .7rem;
            letter-spacing: .06em;
            text-transform: uppercase;
        }
        .metric-value {
            color: var(--ink);
            font-size: 1.8rem;
            font-weight: 500;
            letter-spacing: -.06em;
            margin-top: .55rem;
        }
        .muted { color: var(--muted); }
        .stCaption, [data-testid="stCaptionContainer"] { color: var(--muted); }
        .stMarkdown, .stText { color: var(--ink); }
        a { color: var(--accent); }
        a:hover { color: var(--brand); }

        [data-testid="stVerticalBlockBorderWrapper"] {
            border-color: var(--line);
            border-radius: 3px;
            background: var(--surface);
        }
        [data-testid="stMetric"] {
            padding: .8rem 1rem;
            border: 1px solid var(--line);
            border-radius: 3px;
            background: var(--surface);
        }
        [data-testid="stMetricLabel"] { color: var(--muted); }
        [data-testid="stMetricValue"] { color: var(--ink); }
        .stButton > button, .stFormSubmitButton > button, .stLinkButton > a {
            min-height: 2.35rem;
            border: 1px solid var(--line);
            border-radius: 3px;
            background: var(--surface-raised);
            color: var(--ink);
            font-family: inherit;
            font-size: .78rem;
        }
        .stButton > button:hover, .stFormSubmitButton > button:hover, .stLinkButton > a:hover {
            border-color: var(--brand);
            color: var(--brand);
        }
        .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
            border-color: var(--brand);
            background: var(--brand);
            color: #111;
        }
        input, textarea, [data-baseweb="select"] > div {
            border-color: var(--line) !important;
            border-radius: 3px !important;
            background: var(--surface) !important;
            color: var(--ink) !important;
        }
        [data-testid="stDataFrame"] { border: 1px solid var(--line); }
        [data-testid="stProgressBar"] > div > div { background: var(--brand); }
        [data-testid="stExpander"] { border-color: var(--line); background: var(--surface); }
        .section-kicker {
            color: var(--brand);
            font-size: .68rem;
            letter-spacing: .12em;
            text-transform: uppercase;
            margin-bottom: .6rem;
        }
        @media (max-width: 760px) {
            [data-testid="stSidebar"] { min-width: 0; }
            .main .block-container { padding: 2rem 1rem 3rem; }
            .hero h1 { font-size: 2.3rem; }
        }
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
