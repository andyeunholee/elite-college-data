import streamlit as st
import streamlit.components.v1 as components
import os

st.set_page_config(
    page_title="Elite U.S. College Data Sheet",
    page_icon="🎓",
    layout="wide",
)

# Remove Streamlit default padding
st.markdown("""
<style>
    .block-container { padding: 0 !important; }
    iframe { border: none; }
</style>
""", unsafe_allow_html=True)

html_path = os.path.join(os.path.dirname(__file__), "output", "index.html")

if os.path.exists(html_path):
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    components.html(html_content, height=950, scrolling=True)
else:
    st.error("index.html not found. Run `python generate.py` first.")
