"""views/assistant.py — Chat assistant page (bilingual)."""

import streamlit as st
from common import generate, check_key, t

check_key()

st.title(t("assistant_title"))
st.caption(t("disclaimer"))

SYSTEM = t("assistant_system")

if "history" not in st.session_state:
    st.session_state.history = []

for message in st.session_state.history:
    with st.chat_message(message["role"]):
        st.markdown(message["text"])

question = st.chat_input(t("assistant_input"))

if question:
    st.session_state.history.append({"role": "user", "text": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner(t("thinking")):
            answer = generate(question, SYSTEM)
        st.markdown(answer)

    st.session_state.history.append({"role": "assistant", "text": answer})
