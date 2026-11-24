from base64 import b64encode
from hmac import compare_digest
from pathlib import Path
import re

import streamlit as st
from streamlit.components.v1 import html

ROOT = Path(__file__).parent
PAGES = {
    "แดชบอร์ด": "index.html",
    "รายงานตรวจข้อมูล": "data-quality.html",
    "คู่มือใช้งาน": "quick-guide.html",
}
CSV_FILES = ("monthly-results.csv", "branch-category-daily.csv")

st.set_page_config(page_title="รายงานร้านสหกรณ์", layout="wide")

if not st.session_state.get("judge_logged_in", False):
    with st.container(key="judge_card", border=True):
        st.markdown('''
        <style>
          .st-key-judge_card { max-width: 440px; margin: 4vh auto; }
        </style>
        ''', unsafe_allow_html=True)
        st.subheader("รายงานยอดขายร้านสหกรณ์")
        st.caption("เข้าสู่ระบบสำหรับกรรมการ")

        with st.form("judge_login", border=False):
            user = st.text_input("ชื่อผู้ใช้")
            password = st.text_input("รหัสผ่าน", type="password")
            submitted = st.form_submit_button("เข้าสู่ระบบ", type="primary")

        if submitted:
            try:
                account = st.secrets["judge"]
                user_ok = compare_digest(user.encode(), account["username"].encode())
                password_ok = compare_digest(password.encode(), account["password"].encode())
            except (FileNotFoundError, KeyError):
                st.error("ยังตั้งค่าบัญชีกรรมการไม่ครบ")
            else:
                if user_ok and password_ok:
                    st.session_state["judge_logged_in"] = True
                    st.rerun()
                st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
    st.stop()

menu, actions = st.columns([4, 1], vertical_alignment="bottom")
with menu:
    selected = st.selectbox("เลือกหน้า", list(PAGES))
with actions:
    if st.button("ออกจากระบบ"):
        st.session_state["judge_logged_in"] = False
        st.rerun()

try:
    content = (ROOT / PAGES[selected]).read_text(encoding="utf-8")
    for filename in CSV_FILES:
        link = f'href="{filename}"'
        if link in content:
            payload = b64encode((ROOT / filename).read_bytes()).decode("ascii")
            content = content.replace(
                f'{link} download',
                f'href="data:text/csv;base64,{payload}" download="{filename}"',
            )
except OSError:
    st.error("เปิดไฟล์รายงานไม่ได้ โปรดลองใหม่หรือแจ้งผู้ดูแล")
    st.button("ลองใหม่")
    st.stop()

# ใช้เมนู Streamlit ด้านบนสลับทั้งสามหน้า
page_links = "|".join(re.escape(name) for name in PAGES.values())
content = re.sub(
    rf'<a\b[^>]*\bhref="(?:{page_links})"[^>]*>[^<]*</a>',
    "",
    content,
)

# ปุ่มลัดในหน้าให้เลื่อนไปยังหัวข้อเดิม
anchor_script = '''
<script>
document.addEventListener("click", (event) => {
  const link = event.target.closest('a[href^="#"]');
  if (!link) return;
  const target = document.getElementById(link.getAttribute("href").slice(1));
  if (target) {
    event.preventDefault();
    target.scrollIntoView({block: "start"});
  }
});
</script>
'''
content = content.replace("</body>", anchor_script + "</body>", 1)

st.markdown("""
<style>
.stApp:has(.st-key-provincial_view) { --report-menu-height: 88px; }

[data-testid="stAppViewContainer"]:has(.st-key-provincial_view),
[data-testid="stMain"]:has(.st-key-provincial_view) {
  overflow: hidden !important;
}

.stApp:has(.st-key-provincial_view) [data-testid="stHeader"] {
  display: none;
}

[data-testid="stMain"]:has(.st-key-provincial_view)
[data-testid="stHorizontalBlock"]:has([data-testid="stSelectbox"]) {
  position: fixed;
  inset: 0 0 auto;
  z-index: 100;
  box-sizing: border-box;
  height: var(--report-menu-height);
  padding: 8px clamp(12px, 3vw, 30px);
  background: var(--background-color, #fff);
  border-bottom: 1px solid #dce8e4;
  flex-wrap: nowrap !important;
  gap: 8px;
  align-items: center;
}

[data-testid="stMain"]:has(.st-key-provincial_view) [data-testid="stColumn"] {
  flex: 1 1 0% !important;
  min-width: 0 !important;
  width: auto !important;
}

[data-testid="stMain"]:has(.st-key-provincial_view) [data-testid="stColumn"]:last-child {
  flex: 0 0 auto !important;
}

.st-key-provincial_view iframe {
  position: fixed;
  inset: var(--report-menu-height) 0 auto;
  width: 100% !important;
  height: calc(100dvh - var(--report-menu-height)) !important;
  border: 0;
}
</style>
""", unsafe_allow_html=True)

# แยก Plotly เป็นไฟล์ที่เบราว์เซอร์แคชได้
content = re.sub(
    r'<script[^>]*>\s*/\*\*\s*\*\s*plotly\.js v(\d+\.\d+\.\d+)\b.*?</script>',
    lambda match: f'<script src="https://cdn.plot.ly/plotly-{match[1]}.min.js"></script>',
    content,
    count=1,
    flags=re.S,
)

with st.container(key="provincial_view"):
    html(content, height=760, scrolling=True)
