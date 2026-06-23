"""Telnek Streamlit branding — theme tokens and global CSS."""

BRAND_PRIMARY = "#1B6BB5"
BRAND_PRIMARY_DARK = "#145A96"
BRAND_ACCENT = "#3BA4D9"
BRAND_BG = "#F5FAFD"
BRAND_TEXT = "#1A1A2E"
BRAND_MUTED = "#64748B"


def inject_brand_css() -> None:
    """Inject global CSS for a cleaner, Telnek-branded Streamlit shell."""
    import streamlit as st

    st.markdown(
        f"""
        <style>
            :root {{
                --telnek-primary: {BRAND_PRIMARY};
                --telnek-primary-dark: {BRAND_PRIMARY_DARK};
                --telnek-accent: {BRAND_ACCENT};
                --telnek-bg: {BRAND_BG};
                --telnek-text: {BRAND_TEXT};
                --telnek-muted: {BRAND_MUTED};
            }}

            #MainMenu {{visibility: hidden;}}
            footer {{visibility: hidden;}}
            header[data-testid="stHeader"] {{
                background: transparent;
            }}

            .block-container {{
                padding-top: 1.5rem;
                padding-bottom: 2rem;
                max-width: 1180px;
            }}

            [data-testid="stMetric"] {{
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
                padding: 0.65rem 0.85rem;
                box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
            }}

            [data-testid="stMetricLabel"] {{
                color: var(--telnek-muted);
                font-size: 0.8rem;
            }}

            [data-testid="stSidebar"] {{
                background-color: #FFFFFF;
                border-right: 1px solid #E2E8F0;
            }}

            [data-testid="stSidebar"] [data-testid="stMarkdown"] h3 {{
                font-size: 0.82rem;
                color: var(--telnek-muted);
                font-weight: 600;
                letter-spacing: 0.06em;
                text-transform: uppercase;
                margin-bottom: 0.35rem;
            }}

            [data-testid="stSidebar"] [role="radiogroup"] {{
                gap: 0.2rem;
            }}

            [data-testid="stSidebar"] [role="radiogroup"] label {{
                width: 100%;
                padding: 0.5rem 0.65rem;
                border-radius: 8px;
                border: 1px solid transparent;
                margin: 0;
            }}

            [data-testid="stSidebar"] [role="radiogroup"] label:hover {{
                background: #F1F5F9;
            }}

            [data-testid="stSidebar"] [role="radiogroup"] label[data-checked="true"],
            [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {{
                background: #E8F2FA;
                border-color: #C7DDF2;
                font-weight: 600;
            }}

            div[data-testid="stForm"] {{
                border: 1px solid #E2E8F0;
                border-radius: 12px;
                padding: 1.25rem 1.5rem 1.5rem;
                background: #FFFFFF;
                box-shadow: 0 4px 14px rgba(27, 107, 181, 0.08);
            }}

            .telnek-app-header-rule {{
                border-bottom: 1px solid #E2E8F0;
                margin: 0.25rem 0 0.75rem;
            }}

            [data-testid="stMarkdown"] .telnek-brand-subtitle,
            .telnek-brand-subtitle {{
                margin: 0 !important;
                padding: 0 !important;
                font-size: 4.75rem !important;
                font-weight: 800 !important;
                color: var(--telnek-text) !important;
                line-height: 1.02 !important;
                letter-spacing: -0.04em !important;
                white-space: nowrap;
            }}

            @media (max-width: 900px) {{
                [data-testid="stMarkdown"] .telnek-brand-subtitle,
                .telnek-brand-subtitle {{
                    font-size: 3.25rem !important;
                    white-space: normal;
                }}
            }}

            .telnek-login-title {{
                margin: 1.1rem 0 0.35rem;
                font-size: 1.2rem;
                font-weight: 600;
                color: var(--telnek-primary);
                text-align: center;
            }}

            .telnek-login-caption {{
                display: block;
                text-align: center;
                color: var(--telnek-muted);
                font-size: 0.92rem;
                margin-bottom: 1rem;
            }}

            .telnek-login-hint {{
                text-align: center;
                color: var(--telnek-muted);
                font-size: 0.82rem;
                margin-top: 0.75rem;
                line-height: 1.45;
            }}

            .telnek-footer {{
                text-align: center;
                color: var(--telnek-muted);
                font-size: 0.85rem;
                margin: 1rem 0 0.5rem;
            }}

            button[kind="primary"] {{
                background-color: var(--telnek-primary);
                border-color: var(--telnek-primary);
            }}

            button[kind="primary"]:hover {{
                background-color: var(--telnek-primary-dark);
                border-color: var(--telnek-primary-dark);
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )