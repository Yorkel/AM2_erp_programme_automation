"""
Custom CSS for ESRC brand styling.
"""

from .config import NAVY, TEAL, MID_BLUE


def get_css():
    return f"""
<style>
    /* Sidebar */
    [data-testid="stSidebar"] {{
        background-color: {NAVY};
    }}
    [data-testid="stSidebar"] * {{
        color: white !important;
    }}
    [data-testid="stSidebar"] .stRadio label {{
        color: #c8d8ec !important;
    }}
    [data-testid="stSidebar"] .stRadio label:hover {{
        color: {TEAL} !important;
    }}

    /* Headers */
    h1 {{
        color: {NAVY} !important;
    }}
    h2, h3 {{
        color: {MID_BLUE} !important;
    }}

    /* Primary buttons */
    .stButton > button[kind="primary"] {{
        background-color: {TEAL};
        border-color: {TEAL};
    }}
    .stButton > button[kind="primary"]:hover {{
        background-color: #389e93;
        border-color: #389e93;
    }}

    /* Info boxes */
    .stAlert {{
        background-color: #e8f4f8;
        border-left-color: {TEAL};
    }}

    /* Progress bar */
    .stProgress > div > div > div {{
        background-color: {TEAL};
    }}

    /* Dividers */
    hr {{
        border-color: #dde3ed;
    }}

    /* Hide anchor link icons on headers */
    h1 a, h2 a, h3 a {{
        display: none !important;
    }}

    /* Card containers — light background */
    [data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: #f8f9fb !important;
        border-radius: 8px !important;
    }}

    /* Download button — light orange */
    [data-testid="stDownloadButton"] button {{
        background-color: #ffecd2 !important;
        color: #856404 !important;
        border: 1px solid #f0c36d !important;
    }}
    [data-testid="stDownloadButton"] button:hover {{
        background-color: #ffe0b2 !important;
    }}

    /* All buttons — same height, larger text */
    [data-testid="stButton"] button {{
        min-height: 50px !important;
        font-size: 16px !important;
    }}

    /* Primary buttons — light blue (Category 1 + Manual) */
    [data-testid="stButton"] button[kind="primary"] {{
        background-color: #d6e4f0 !important;
        border: 1px solid #4472c4 !important;
        color: #2c5aa0 !important;
    }}
    [data-testid="stButton"] button[kind="primary"]:hover {{
        background-color: #b8cfe2 !important;
    }}

    /* Tertiary buttons — light orange (Category 2) */
    [data-testid="stButton"] button[kind="tertiary"] {{
        background-color: #fde8d0 !important;
        border: 1px solid #ed7d31 !important;
        color: #c46516 !important;
    }}
    [data-testid="stButton"] button[kind="tertiary"]:hover {{
        background-color: #f9d4ae !important;
    }}

    /* Secondary buttons — light red (Reject) */
    [data-testid="stButton"] button[kind="secondary"] {{
        background-color: #fadbd8 !important;
        border: 1px solid #e74c3c !important;
        color: #c0392b !important;
    }}
    [data-testid="stButton"] button[kind="secondary"]:hover {{
        background-color: #f1948a !important;
        color: white !important;
    }}
</style>
"""
