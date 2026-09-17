"""
common.py — Shared code used by every page of the app.

Contains: the API key loading, the Gemini calls, and ALL the interface texts
in French and English (so the app can switch language in one click).
"""

import os
import time
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai import errors

# Load the API key (local .env, or Streamlit Cloud secrets).
load_dotenv()
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    try:
        API_KEY = st.secrets["GEMINI_API_KEY"]
    except Exception:
        API_KEY = None

MODEL = "gemini-flash-lite-latest"
EMBED_MODEL = "gemini-embedding-2"


# ===========================================================================
#  LANGUAGE / TRANSLATIONS
# ===========================================================================
def get_lang() -> str:
    """Return the current language code ('fr' or 'en'), set by the sidebar."""
    return st.session_state.get("lang", "fr")


def t(key: str, **kwargs) -> str:
    """Return the translated text for `key` in the current language.

    If placeholders are given (e.g. t("no_data", ticker="AAPL")), they are
    filled into the string with .format().
    """
    lang = get_lang()
    text = TR.get(lang, TR["fr"]).get(key) or TR["fr"].get(key, key)
    return text.format(**kwargs) if kwargs else text


TR = {
    # ------------------------------------------------------------------ FR
    "fr": {
        # navigation (sidebar menu)
        "nav_home": "Accueil",
        "nav_assistant": "Assistant",
        "nav_analyse": "Analyse marché",
        "nav_backtest": "Backtesting",
        "nav_documents": "Documents",
        # shared
        "key_missing": "Clé API manquante. Vérifie ton fichier .env (GEMINI_API_KEY).",
        "busy": "⚠️ Le modèle est très demandé en ce moment. Réessaie dans un instant.",
        "disclaimer": "Assistant pédagogique — ne constitue pas un conseil d'investissement.",
        # home
        "home_title": "💰 Bot Financier",
        "home_intro": (
            "Bienvenue 👋 Cette application réunit **quatre outils** :\n\n"
            "- **💬 Assistant** — pose n'importe quelle question de finance, le bot "
            "répond et explique les concepts.\n"
            "- **📈 Analyse marché** — graphique journalier d'une action ou d'un indice, "
            "indicateurs (moyennes mobiles, RSI, volatilité) et analyse rédigée par le bot.\n"
            "- **🧪 Backtesting** — teste une stratégie (croisement de moyennes mobiles) "
            "sur le passé et compare-la à un simple « acheter et garder ».\n"
            "- **📄 Documents** — charge un PDF (rapport annuel...) et pose des questions "
            "dessus, le bot répond en citant le document.\n\n"
            "👈 **Choisis un outil dans le menu à gauche pour commencer.**"
        ),
        "home_disclaimer": (
            "Rappel : cet outil est un projet pédagogique. Il ne remplace pas un conseil "
            "financier professionnel."
        ),
        # assistant
        "assistant_title": "💬 Assistant Financier",
        "assistant_input": "Pose ta question finance...",
        "thinking": "Réflexion...",
        "assistant_system": (
            "Tu es un assistant financier pédagogue pour des étudiants. "
            "Tu expliques clairement les concepts de finance de marché, d'entreprise "
            "et d'économie. Tu réponds en français, de façon concise et structurée. "
            "Tu rappelles quand c'est utile que tu ne donnes pas de conseil "
            "d'investissement personnalisé."
        ),
        # analyse
        "analyse_title": "📈 Analyse Marché",
        "symbol_label": "Symbole (format Yahoo Finance)",
        "period_label": "Période",
        "examples": (
            "Exemples — **Actions** : `AAPL` (Apple), `MSFT`, `TSLA`, `MC.PA` (LVMH), "
            "`GLE.PA` (Société Générale)  ·  **Indices** : `^FCHI` (CAC 40), "
            "`^GSPC` (S&P 500), `^IXIC` (Nasdaq)."
        ),
        "enter_symbol": "Entre un symbole ci-dessus pour lancer l'analyse.",
        "no_data": (
            "Aucune donnée pour « {ticker} ». Vérifie le symbole "
            "(ex. `MC.PA` pour LVMH, `^FCHI` pour le CAC 40)."
        ),
        "m_last": "Dernier cours",
        "m_change": "Variation ({period})",
        "m_rsi": "RSI (14j)",
        "m_vol": "Volatilité annualisée",
        "chart_price_title": "{ticker} — cours journalier",
        "chart_rsi_title": "RSI (14 jours)",
        "trace_price": "Cours",
        "bot_analysis": "🧠 Analyse du bot",
        "generate_btn": "Générer l'analyse",
        "generate_hint": "Clique sur « Générer l'analyse » pour que le bot commente ces chiffres.",
        "analysing": "Analyse en cours...",
        "analyse_system": (
            "Tu es un analyste financier pédagogue. À partir des chiffres fournis, "
            "tu rédiges une analyse courte et claire en français (5-8 phrases), "
            "structurée : tendance, momentum (RSI), volatilité, et un mot de prudence. "
            "Tu ne donnes JAMAIS de conseil d'achat ou de vente personnalisé."
        ),
        "trend_up": "haussière",
        "trend_down": "baissière",
        "analyse_prompt": (
            "Analyse les données suivantes pour {ticker} sur la période {period} :\n"
            "- Dernier cours : {last:.2f}\n"
            "- Variation sur la période : {change:+.1f}%\n"
            "- MA20 vs MA50 : MA20={ma20:.2f}, MA50={ma50:.2f} (tendance {trend})\n"
            "- RSI (14j) : {rsi:.0f}\n"
            "- Volatilité annualisée : {vol:.1f}%\n"
        ),
        # backtest
        "backtest_title": "🧪 Backtesting",
        "backtest_caption": "Test d'une stratégie sur le passé — pédagogique, pas un conseil d'investissement.",
        "fees_label": "Frais par trade (%)",
        "ma_short_label": "Moyenne mobile courte (jours)",
        "ma_long_label": "Moyenne mobile longue (jours)",
        "ma_warn": "La moyenne courte doit être plus petite que la longue.",
        "enter_symbol_bt": "Entre un symbole pour lancer le backtest.",
        "not_enough": "Pas assez de données pour « {ticker} » sur cette période.",
        "m_strat": "Rendement stratégie",
        "m_bh": "Rendement buy & hold",
        "m_maxdd": "Perte max (drawdown)",
        "m_sharpe": "Ratio de Sharpe",
        "delta_vs": "{x:+.1f} pts vs stratégie",
        "bt_caption": (
            "Nombre d'achats : {trades}  ·  Temps investi : {invested:.0f}% du temps  "
            "·  Drawdown buy & hold : {bhdd:.1f}%"
        ),
        "eq_title": "Évolution de 1 € investi",
        "signals_title": "{ticker} — signaux d'achat / vente",
        "trace_buy": "Achat",
        "trace_sell": "Vente",
        "bt_generate_hint": "Clique sur « Générer l'analyse » pour que le bot commente le backtest.",
        "backtest_system": (
            "Tu es un analyste quantitatif pédagogue. À partir des résultats d'un "
            "backtest, tu expliques en français (5-8 phrases) si la stratégie a battu le "
            "buy & hold, à quel prix (drawdown, nombre de trades), ce que dit le ratio de "
            "Sharpe, et tu rappelles les limites d'un backtest (frais réels, sur-optimisation, "
            "le passé ne prédit pas le futur). Jamais de conseil d'investissement."
        ),
        "backtest_prompt": (
            "Backtest d'une stratégie de croisement de moyennes mobiles (MA{short}/MA{long}) "
            "sur {ticker}, période {period}, frais {fee}% par trade :\n"
            "- Rendement stratégie : {strat:+.1f}%\n"
            "- Rendement buy & hold : {bh:+.1f}%\n"
            "- Nombre d'achats : {trades}\n"
            "- Temps investi : {invested:.0f}% du temps\n"
            "- Drawdown max stratégie : {dd:.1f}% (buy & hold : {bhdd:.1f}%)\n"
            "- Ratio de Sharpe stratégie : {sharpe:.2f}\n"
        ),
        # rag
        "rag_title": "📄 Analyse de documents",
        "rag_caption": "Pose des questions sur un PDF — le bot répond en citant le document.",
        "upload_label": "Charge un PDF (rapport annuel, note d'analyse...)",
        "upload_prompt": "Charge un PDF pour commencer.",
        "indexing": "Lecture et indexation du document...",
        "no_text": (
            "Impossible d'extraire du texte de ce PDF. Il est peut-être scanné "
            "(image) plutôt que du vrai texte."
        ),
        "indexed": "{n} passages indexés depuis « {name} ».",
        "question_label": "Ta question sur le document",
        "searching": "Recherche dans le document...",
        "passages_expander": "Voir les passages utilisés",
        "passage_label": "**Passage {n}** — proximité {sim:.2f}",
        "rag_system": (
            "Tu réponds à la question en t'appuyant UNIQUEMENT sur les passages fournis. "
            "Cite les passages utilisés sous la forme [Passage n]. Si la réponse ne se "
            "trouve pas dans les passages, dis-le clairement au lieu d'inventer. "
            "Réponds en français."
        ),
        "rag_prompt": "Passages du document :\n{context}\n\nQuestion : {question}",
    },
    # ------------------------------------------------------------------ EN
    "en": {
        "nav_home": "Home",
        "nav_assistant": "Assistant",
        "nav_analyse": "Market analysis",
        "nav_backtest": "Backtesting",
        "nav_documents": "Documents",
        "key_missing": "API key missing. Check your .env file (GEMINI_API_KEY).",
        "busy": "⚠️ The model is very busy right now. Please try again in a moment.",
        "disclaimer": "Educational assistant — not investment advice.",
        "home_title": "💰 Finance Bot",
        "home_intro": (
            "Welcome 👋 This app brings together **four tools**:\n\n"
            "- **💬 Assistant** — ask any finance question, the bot answers and explains "
            "the concepts.\n"
            "- **📈 Market analysis** — daily chart of a stock or index, indicators "
            "(moving averages, RSI, volatility) and an analysis written by the bot.\n"
            "- **🧪 Backtesting** — test a strategy (moving-average crossover) on the past "
            "and compare it to simply buying and holding.\n"
            "- **📄 Documents** — upload a PDF (annual report...) and ask questions about "
            "it, the bot answers citing the document.\n\n"
            "👈 **Pick a tool from the menu on the left to get started.**"
        ),
        "home_disclaimer": (
            "Reminder: this is an educational project. It does not replace professional "
            "financial advice."
        ),
        "assistant_title": "💬 Financial Assistant",
        "assistant_input": "Ask your finance question...",
        "thinking": "Thinking...",
        "assistant_system": (
            "You are an educational finance assistant for students. "
            "You clearly explain concepts of market finance, corporate finance and "
            "economics. You answer in English, concisely and in a structured way. "
            "You remind the user when relevant that you do not give personalized "
            "investment advice."
        ),
        "analyse_title": "📈 Market Analysis",
        "symbol_label": "Symbol (Yahoo Finance format)",
        "period_label": "Period",
        "examples": (
            "Examples — **Stocks**: `AAPL` (Apple), `MSFT`, `TSLA`, `MC.PA` (LVMH), "
            "`GLE.PA` (Société Générale)  ·  **Indices**: `^FCHI` (CAC 40), "
            "`^GSPC` (S&P 500), `^IXIC` (Nasdaq)."
        ),
        "enter_symbol": "Enter a symbol above to start the analysis.",
        "no_data": (
            "No data for “{ticker}”. Check the symbol "
            "(e.g. `MC.PA` for LVMH, `^FCHI` for the CAC 40)."
        ),
        "m_last": "Last price",
        "m_change": "Change ({period})",
        "m_rsi": "RSI (14d)",
        "m_vol": "Annualized volatility",
        "chart_price_title": "{ticker} — daily price",
        "chart_rsi_title": "RSI (14 days)",
        "trace_price": "Price",
        "bot_analysis": "🧠 Bot analysis",
        "generate_btn": "Generate analysis",
        "generate_hint": "Click “Generate analysis” for the bot to comment on these figures.",
        "analysing": "Analyzing...",
        "analyse_system": (
            "You are an educational financial analyst. From the figures provided, "
            "you write a short, clear analysis in English (5-8 sentences), structured: "
            "trend, momentum (RSI), volatility, and a word of caution. "
            "You NEVER give personalized buy or sell advice."
        ),
        "trend_up": "upward",
        "trend_down": "downward",
        "analyse_prompt": (
            "Analyze the following data for {ticker} over the period {period}:\n"
            "- Last price: {last:.2f}\n"
            "- Change over the period: {change:+.1f}%\n"
            "- MA20 vs MA50: MA20={ma20:.2f}, MA50={ma50:.2f} ({trend} trend)\n"
            "- RSI (14d): {rsi:.0f}\n"
            "- Annualized volatility: {vol:.1f}%\n"
        ),
        "backtest_title": "🧪 Backtesting",
        "backtest_caption": "Testing a strategy on the past — educational, not investment advice.",
        "fees_label": "Fee per trade (%)",
        "ma_short_label": "Short moving average (days)",
        "ma_long_label": "Long moving average (days)",
        "ma_warn": "The short average must be smaller than the long one.",
        "enter_symbol_bt": "Enter a symbol to run the backtest.",
        "not_enough": "Not enough data for “{ticker}” over this period.",
        "m_strat": "Strategy return",
        "m_bh": "Buy & hold return",
        "m_maxdd": "Max drawdown",
        "m_sharpe": "Sharpe ratio",
        "delta_vs": "{x:+.1f} pts vs strategy",
        "bt_caption": (
            "Number of buys: {trades}  ·  Time invested: {invested:.0f}% of the time  "
            "·  Buy & hold drawdown: {bhdd:.1f}%"
        ),
        "eq_title": "Growth of 1 € invested",
        "signals_title": "{ticker} — buy / sell signals",
        "trace_buy": "Buy",
        "trace_sell": "Sell",
        "bt_generate_hint": "Click “Generate analysis” for the bot to comment on the backtest.",
        "backtest_system": (
            "You are an educational quantitative analyst. From the results of a backtest, "
            "you explain in English (5-8 sentences) whether the strategy beat buy & hold, "
            "at what cost (drawdown, number of trades), what the Sharpe ratio says, and you "
            "remind the reader of the limits of a backtest (real fees, over-optimization, "
            "the past does not predict the future). Never any investment advice."
        ),
        "backtest_prompt": (
            "Backtest of a moving-average crossover strategy (MA{short}/MA{long}) "
            "on {ticker}, period {period}, fees {fee}% per trade:\n"
            "- Strategy return: {strat:+.1f}%\n"
            "- Buy & hold return: {bh:+.1f}%\n"
            "- Number of buys: {trades}\n"
            "- Time invested: {invested:.0f}% of the time\n"
            "- Max strategy drawdown: {dd:.1f}% (buy & hold: {bhdd:.1f}%)\n"
            "- Strategy Sharpe ratio: {sharpe:.2f}\n"
        ),
        "rag_title": "📄 Document analysis",
        "rag_caption": "Ask questions about a PDF — the bot answers citing the document.",
        "upload_label": "Upload a PDF (annual report, research note...)",
        "upload_prompt": "Upload a PDF to get started.",
        "indexing": "Reading and indexing the document...",
        "no_text": (
            "Couldn't extract text from this PDF. It may be scanned (an image) rather "
            "than real text."
        ),
        "indexed": "{n} passages indexed from “{name}”.",
        "question_label": "Your question about the document",
        "searching": "Searching the document...",
        "passages_expander": "See the passages used",
        "passage_label": "**Passage {n}** — similarity {sim:.2f}",
        "rag_system": (
            "You answer the question using ONLY the passages provided. "
            "Cite the passages you use in the form [Passage n]. If the answer is not in "
            "the passages, say so clearly instead of inventing. Answer in English."
        ),
        "rag_prompt": "Document passages:\n{context}\n\nQuestion: {question}",
    },
}


# ===========================================================================
#  GEMINI HELPERS
# ===========================================================================
@st.cache_resource
def get_client():
    return genai.Client(api_key=API_KEY)


def check_key():
    if not API_KEY:
        st.error(t("key_missing"))
        st.stop()


def generate(prompt: str, system: str, max_retries: int = 3) -> str:
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
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))
            else:
                return t("busy")


def embed_texts(texts: list[str], batch_size: int = 50) -> list[list[float]]:
    client = get_client()
    vectors: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        result = client.models.embed_content(model=EMBED_MODEL, contents=batch)
        vectors.extend(e.values for e in result.embeddings)
    return vectors
