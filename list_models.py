"""
list_models.py — Utility: print the Gemini models your API key can use.

Model names change over time. If chat.py or app.py says a model was not found,
run  python list_models.py  and copy a "flash" model name into the MODEL
constant of those files.
"""

import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# Ask the API for every model available to your key, and print the ones
# that can generate text (i.e. answer questions).
for model in client.models.list():
    actions = getattr(model, "supported_actions", None) or []
    if "generateContent" in actions:
        print(model.name)
