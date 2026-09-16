"""views/rag.py — Ask questions about a PDF (RAG = Retrieval-Augmented Generation).

How it works:
  1. Read the PDF and cut it into small passages ("chunks").
  2. Turn each passage into a vector (embedding) that captures its meaning.
  3. When you ask a question, turn IT into a vector too, and find the passages
     whose vectors are closest (cosine similarity).
  4. Give ONLY those passages to the bot, which answers using them and cites them.
"""

import io
import numpy as np
import streamlit as st
from pypdf import PdfReader

from common import generate, embed_texts, check_key

check_key()

st.title("📄 Analyse de documents")
st.caption("Pose des questions sur un PDF — le bot répond en citant le document.")


# --- 1. Cut the text into overlapping passages -----------------------------
def chunk_text(text: str, size: int = 1500, overlap: int = 200) -> list[str]:
    """Split text into ~1500-char pieces that overlap a bit (so we don't cut an
    idea in half at a boundary)."""
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i:i + size])
        i += size - overlap
    return [c.strip() for c in chunks if c.strip()]


# --- 2. Read + index the PDF (cached, so we only do it once per file) -------
@st.cache_data(ttl=3600, show_spinner=False)
def index_pdf(file_bytes: bytes, name: str):
    reader = PdfReader(io.BytesIO(file_bytes))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    chunks = chunk_text(text)[:200]           # cap to keep it fast / cheap
    if not chunks:
        return [], np.zeros((0, 0))
    embeddings = embed_texts(chunks)
    return chunks, np.array(embeddings)


uploaded = st.file_uploader("Charge un PDF (rapport annuel, note d'analyse...)", type=["pdf"])

if not uploaded:
    st.info("Charge un PDF pour commencer.")
    st.stop()

with st.spinner("Lecture et indexation du document..."):
    chunks, matrix = index_pdf(uploaded.getvalue(), uploaded.name)

if len(chunks) == 0:
    st.error(
        "Impossible d'extraire du texte de ce PDF. Il est peut-être scanné "
        "(image) plutôt que du vrai texte."
    )
    st.stop()

st.success(f"{len(chunks)} passages indexés depuis « {uploaded.name} ».")


# --- 3. Answer a question --------------------------------------------------
question = st.text_input("Ta question sur le document")

if question:
    # a) embed the question, then measure closeness to every passage.
    q_vec = np.array(embed_texts([question])[0])
    sims = matrix @ q_vec / (
        np.linalg.norm(matrix, axis=1) * np.linalg.norm(q_vec) + 1e-9
    )

    # b) keep the 4 most relevant passages.
    top_idx = sims.argsort()[::-1][:4]
    context = "\n\n".join(f"[Passage {i + 1}]\n{chunks[i]}" for i in top_idx)

    # c) the bot must answer ONLY from these passages, and say so if the answer
    #    isn't there (this is what stops it from inventing).
    SYSTEM = (
        "Tu réponds à la question en t'appuyant UNIQUEMENT sur les passages fournis. "
        "Cite les passages utilisés sous la forme [Passage n]. Si la réponse ne se "
        "trouve pas dans les passages, dis-le clairement au lieu d'inventer. "
        "Réponds en français."
    )
    prompt = f"Passages du document :\n{context}\n\nQuestion : {question}"

    with st.spinner("Recherche dans le document..."):
        answer = generate(prompt, SYSTEM)
    st.markdown(answer)

    # d) show the raw passages that were used, for transparency.
    with st.expander("Voir les passages utilisés"):
        for i in top_idx:
            st.markdown(f"**Passage {i + 1}** — proximité {sims[i]:.2f}")
            st.text(chunks[i])
