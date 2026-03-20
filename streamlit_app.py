import streamlit as st
import streamlit.components.v1 as components
import os

st.set_page_config(
    page_title="Elite U.S. College Data Sheet",
    page_icon="🎓",
    layout="wide",
)

# Remove all Streamlit padding and header
st.markdown("""
<style>
    header[data-testid="stHeader"] { display: none !important; }
    .block-container {
        padding: 0 !important;
        max-width: 100% !important;
    }
    section[data-testid="stMain"] > div {
        padding: 0 !important;
    }
    iframe {
        border: none !important;
        width: 100% !important;
        display: block !important;
    }
</style>
""", unsafe_allow_html=True)

html_path = os.path.join(os.path.dirname(__file__), "output", "index.html")

if os.path.exists(html_path):
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    components.html(html_content, height=980, scrolling=True)
else:
    st.error("index.html not found. Run `python generate.py` first.")
