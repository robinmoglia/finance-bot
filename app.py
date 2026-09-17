"""
app.py — Entry point (navigation + language selector).

Run it with:  python -m streamlit run app.py
"""

import streamlit as st
from common import TR

st.set_page_config(page_title="Finance Bot", page_icon="💰", layout="wide")

# Language selector, shown in the sidebar on every page. The choice is stored
# in st.session_state["lang"] (via key="lang") and read by every page.
st.sidebar.radio(
    "🌐 Langue / Language",
    options=["fr", "en"],
    format_func=lambda c: "Français" if c == "fr" else "English",
    key="lang",
)

# Translate the menu labels to the chosen language.
tr = TR[st.session_state.get("lang", "fr")]

accueil = st.Page("views/accueil.py", title=tr["nav_home"], icon="💰", default=True)
assistant = st.Page("views/assistant.py", title=tr["nav_assistant"], icon="💬")
analyse = st.Page("views/analyse.py", title=tr["nav_analyse"], icon="📈")
backtest = st.Page("views/backtest.py", title=tr["nav_backtest"], icon="🧪")
documents = st.Page("views/rag.py", title=tr["nav_documents"], icon="📄")

pg = st.navigation([accueil, assistant, analyse, backtest, documents])
pg.run()
