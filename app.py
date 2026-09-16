"""
app.py — Entry point of the whole app (navigation between pages).

Run it with:  python -m streamlit run app.py

This uses Streamlit's multipage navigation: each "page" is a separate file in
the views/ folder, and the menu on the left lets you switch between them.
"""

import streamlit as st

# set_page_config must be called once, here, before anything else is drawn.
st.set_page_config(page_title="Bot Financier", page_icon="💰", layout="wide")

# Declare the pages. `icon` and `title` are what show up in the left menu.
accueil = st.Page("views/accueil.py", title="Accueil", icon="💰", default=True)
assistant = st.Page("views/assistant.py", title="Assistant", icon="💬")
analyse = st.Page("views/analyse.py", title="Analyse marché", icon="📈")
backtest = st.Page("views/backtest.py", title="Backtesting", icon="🧪")
documents = st.Page("views/rag.py", title="Documents", icon="📄")

# Build the navigation menu and run whichever page is selected.
pg = st.navigation([accueil, assistant, analyse, backtest, documents])
pg.run()
