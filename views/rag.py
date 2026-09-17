"""views/rag.py — Ask questions about a PDF (RAG, bilingual)."""

import io
import numpy as np
import streamlit as st
from pypdf import PdfReader

from common import generate, embed_texts, check_key, t

check_key()

st.title(t("rag_title"))
st.caption(t("rag_caption"))


def chunk_text(text: str, size: int = 1500, overlap: int = 200) -> list[str]:
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i:i + size])
        i += size - overlap
    return [c.strip() for c in chunks if c.strip()]


@st.cache_data(ttl=3600, show_spinner=False)
def index_pdf(file_bytes: bytes, name: str):
    reader = PdfReader(io.BytesIO(file_bytes))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    chunks = chunk_text(text)[:200]
    if not chunks:
        return [], np.zeros((0, 0))
    embeddings = embed_texts(chunks)
    return chunks, np.array(embeddings)


uploaded = st.file_uploader(t("upload_label"), type=["pdf"])

if not uploaded:
    st.info(t("upload_prompt"))
    st.stop()

with st.spinner(t("indexing")):
    chunks, matrix = index_pdf(uploaded.getvalue(), uploaded.name)

if len(chunks) == 0:
    st.error(t("no_text"))
    st.stop()

st.success(t("indexed", n=len(chunks), name=uploaded.name))

question = st.text_input(t("question_label"))

if question:
    q_vec = np.array(embed_texts([question])[0])
    sims = matrix @ q_vec / (
        np.linalg.norm(matrix, axis=1) * np.linalg.norm(q_vec) + 1e-9
    )
    top_idx = sims.argsort()[::-1][:4]
    context = "\n\n".join(f"[Passage {i + 1}]\n{chunks[i]}" for i in top_idx)

    prompt = t("rag_prompt", context=context, question=question)

    with st.spinner(t("searching")):
        answer = generate(prompt, t("rag_system"))
    st.markdown(answer)

    with st.expander(t("passages_expander")):
        for i in top_idx:
            st.markdown(t("passage_label", n=i + 1, sim=sims[i]))
            st.text(chunks[i])
