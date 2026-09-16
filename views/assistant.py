"""views/assistant.py — The chat assistant page."""

import streamlit as st
from common import generate, check_key   # shared helpers (see common.py)

check_key()

st.title("💬 Assistant Financier")
st.caption("Assistant pédagogique — ne donne pas de conseil d'investissement.")

# The bot's role/personality, sent with every question.
SYSTEM = (
    "Tu es un assistant financier pédagogue pour des étudiants. "
    "Tu expliques clairement les concepts de finance de marché, d'entreprise "
    "et d'économie. Tu réponds en français, de façon concise et structurée. "
    "Tu rappelles quand c'est utile que tu ne donnes pas de conseil "
    "d'investissement personnalisé."
)

# Conversation memory: survives Streamlit's re-runs within this session.
if "history" not in st.session_state:
    st.session_state.history = []

# Redraw the whole conversation each time.
for message in st.session_state.history:
    with st.chat_message(message["role"]):
        st.markdown(message["text"])

# The input box at the bottom.
question = st.chat_input("Pose ta question finance...")

if question:
    st.session_state.history.append({"role": "user", "text": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Réflexion..."):
            answer = generate(question, SYSTEM)
        st.markdown(answer)

    st.session_state.history.append({"role": "assistant", "text": answer})
