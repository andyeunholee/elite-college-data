import streamlit as st
import streamlit.components.v1 as components
import os
import subprocess
import sys

st.set_page_config(
    page_title="Elite U.S. College Data Sheet",
    page_icon="🎓",
    layout="wide",
)

# Set API keys from Streamlit secrets into environment
try:
    os.environ["SCORECARD_API_KEY"] = st.secrets["SCORECARD_API_KEY"]
    os.environ["GEMINI_API_KEY"]    = st.secrets["GEMINI_API_KEY"]
except Exception:
    pass  # 로컬 실행 시 .env 사용

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


def run_generate(force=False):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    cmd = [sys.executable, "generate.py"] + (["--refresh"] if force else [])
    result = subprocess.run(
        cmd, env=env, capture_output=True, text=True,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    return result.returncode == 0, result.stderr


# Sidebar
with st.sidebar:
    st.markdown("### 📊 데이터 관리")
    st.caption("캐시 유효기간: 30일")
    refresh_normal = st.button("🔄 데이터 갱신", use_container_width=True,
                               help="캐시 만료 시만 API 재호출")
    refresh_force  = st.button("⚡ 강제 전체 갱신", use_container_width=True,
                               help="캐시 무시 전체 재호출 (5~10분 소요)")

if refresh_normal or refresh_force:
    with st.spinner("데이터 갱신 중... (약 5~10분 소요)"):
        ok, err = run_generate(force=refresh_force)
    if ok:
        st.session_state.pop("html_content", None)
        st.sidebar.success("✅ 갱신 완료!")
        st.rerun()
    else:
        st.sidebar.error(f"오류: {err}")

# Load HTML
html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "index.html")

if "html_content" not in st.session_state:
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            st.session_state["html_content"] = f.read()

if "html_content" in st.session_state:
    components.html(st.session_state["html_content"], height=980, scrolling=True)
else:
    st.error("index.html not found. Run `python generate.py` first.")
