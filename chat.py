"""
chat.py — Your very first finance bot (terminal version).

Goal: understand the CORE of the bot before adding a nice interface.
This script sends a question to the Gemini model and prints its answer.
Run it from the terminal with:  python chat.py

Read every comment: each line is explained so you learn what it does.
"""

# --- 1. Imports -------------------------------------------------------------
import os                          # lets us read "environment variables" (our secret key)
from dotenv import load_dotenv     # reads the .env file and loads the key into the environment
from google import genai           # the official Gemini SDK
from google.genai import types     # extra options (used here for the system instruction)


# --- 2. Load the secret API key --------------------------------------------
# load_dotenv() opens the .env file and makes GEMINI_API_KEY available via os.environ.
# We keep the key in a separate file so it never ends up hard-coded in the code.
load_dotenv()
API_KEY = os.environ.get("GEMINI_API_KEY")

# A friendly check: if the key is missing, stop early with a clear message
# instead of crashing later with a confusing error.
if not API_KEY:
    raise SystemExit(
        "No API key found. Create a .env file with GEMINI_API_KEY=your_key "
        "(see .env.example)."
    )


# --- 3. Configuration -------------------------------------------------------
# The model name. Model IDs change over time, so if you get a "model not found"
# error, run  list_models.py  to see what is currently available and update this.
MODEL = "gemini-flash-lite-latest"

# The "system instruction" is the bot's personality/role. It is sent with every
# request and shapes HOW the bot answers. Here we make it a finance assistant
# that answers in French and stays honest about not giving investment advice.
SYSTEM_INSTRUCTION = (
    "Tu es un assistant financier pédagogue pour des étudiants. "
    "Tu expliques clairement les concepts de finance de marché, d'entreprise "
    "et d'économie. Tu réponds en français, de façon concise et structurée. "
    "Tu rappelles quand c'est utile que tu ne donnes pas de conseil "
    "d'investissement personnalisé."
)


# --- 4. Create the client ---------------------------------------------------
# The "client" is our connection to Gemini. We pass it the API key once here.
client = genai.Client(api_key=API_KEY)


# --- 5. A function that asks the bot one question ---------------------------
def ask(question: str) -> str:
    """Send `question` to Gemini and return the text answer."""
    response = client.models.generate_content(
        model=MODEL,
        contents=question,                       # what the user asks
        config=types.GenerateContentConfig(      # extra settings for this request
            system_instruction=SYSTEM_INSTRUCTION,
        ),
    )
    return response.text


# --- 6. Run it -------------------------------------------------------------
# This block only runs when you launch "python chat.py" directly.
if __name__ == "__main__":
    print("Bot financier (tape 'quit' pour arrêter)\n")

    # A simple loop: keep asking until the user types "quit".
    while True:
        user_question = input("Toi > ")          # read what the user types
        if user_question.strip().lower() in {"quit", "exit", "q"}:
            print("À bientôt !")
            break
        answer = ask(user_question)              # call the bot
        print(f"\nBot > {answer}\n")             # show the answer
