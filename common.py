"""
common.py — Shared code used by every page of the app.

Instead of repeating the API key, the model name and the Gemini call in each
file (which is how we ended up with a busy model in one file and not the other),
we put them ONCE here and import them everywhere. Change the model in one place
and the whole app follows.
"""

import os
import time
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai import errors

# Load the API key. Two sources are supported:
#   - Locally: from the .env file (via python-dotenv).
#   - Deployed on Streamlit Cloud: from st.secrets (set in the app's settings).
load_dotenv()
API_KEY = os.environ.get("GEMINI_API_KEY")

# On Streamlit Cloud there is no .env; the key lives in st.secrets instead.
# Reading st.secrets raises if no secrets exist, so we guard it with try/except.
if not API_KEY:
    try:
        API_KEY = st.secrets["GEMINI_API_KEY"]
    except Exception:
        API_KEY = None

# The one and only place the model is set for the whole app.
MODEL = "gemini-flash-lite-latest"

# The embedding model, used by the RAG page to turn text into vectors.
EMBED_MODEL = "gemini-embedding-2"


@st.cache_resource
def get_client():
    """Create the Gemini client once and reuse it (cached by Streamlit)."""
    return genai.Client(api_key=API_KEY)


def check_key():
    """Stop the page with a clear message if the API key is missing."""
    if not API_KEY:
        st.error("Clé API manquante. Vérifie ton fichier .env (GEMINI_API_KEY).")
        st.stop()


def generate(prompt: str, system: str, max_retries: int = 3) -> str:
    """Send `prompt` to Gemini with a given `system` role, retrying on a busy server."""
    client = get_client()
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(system_instruction=system),
            )
            return response.text
        except errors.ServerError:
            # 503 = model temporarily overloaded. Wait a bit and try again.
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))
            else:
                return "⚠️ Le modèle est très demandé en ce moment. Réessaie dans un instant."


def embed_texts(texts: list[str], batch_size: int = 50) -> list[list[float]]:
    """Turn a list of texts into a list of vectors (embeddings), in batches.

    Each vector is a list of numbers that captures the MEANING of the text, so
    that two texts about the same thing end up with close vectors. Used by the
    RAG page to find the passages most relevant to a question.
    """
    client = get_client()
    vectors: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        result = client.models.embed_content(model=EMBED_MODEL, contents=batch)
        vectors.extend(e.values for e in result.embeddings)
    return vectors
