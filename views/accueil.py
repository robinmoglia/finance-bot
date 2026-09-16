"""views/accueil.py — Landing page: intro + how to use the app."""

import streamlit as st

st.title("💰 Bot Financier")
st.caption("Assistant pédagogique — ne constitue pas un conseil d'investissement.")

st.markdown(
    """
Bienvenue 👋 Cette application réunit deux outils :

- **💬 Assistant** — pose n'importe quelle question de finance, le bot répond
  en français et explique les concepts.
- **📈 Analyse marché** — entre le symbole d'une action ou d'un indice pour voir
  son graphique journalier, ses indicateurs (moyennes mobiles, RSI, volatilité)
  et une analyse rédigée par le bot.

👈 **Choisis un outil dans le menu à gauche pour commencer.**
    """
)

st.info(
    "Rappel : cet outil est un projet pédagogique. Il ne remplace pas un conseil "
    "financier professionnel."
)
