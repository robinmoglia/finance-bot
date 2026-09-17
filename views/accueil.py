"""views/accueil.py — Landing page (bilingual, lists the four tools)."""

import streamlit as st
from common import t

st.title(t("home_title"))
st.caption(t("disclaimer"))
st.markdown(t("home_intro"))
st.info(t("home_disclaimer"))
