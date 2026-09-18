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
        "market_label": "Marché",
        "company_label": "Entreprise",
        "custom_group": "✏️ Autre (saisir un symbole)",
        "period_label": "Période",
        "examples": (
            "Exemples — **Actions** : `AAPL` (Apple), `MSFT`, `TSLA`, `MC.PA` (LVMH), "
            "`GLE.PA` (Société Générale)  ·  **Indices** : `^FCHI` (CAC 40), "
            "`^GSPC` (S&P 500), `^IXIC` (Nasdaq)."
        ),
        "enter_symbol": "Entre un symbole ci-dessus pour lancer l'analyse.",
        "no_data": (
            "Aucune donnée pour « {ticker} ». Cherche le symbole exact sur "
            "finance.yahoo.com. Pour les valeurs européennes, ajoute le suffixe de "
            "place : `MC.PA` (LVMH, Paris), `SIE.DE` (Francfort), `ASML.AS` (Amsterdam), "
            "`^FCHI` (CAC 40)."
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
        # paper trading
        "nav_paper": "Paper Trading",
        "paper_title": "🤖 Paper Trading",
        "paper_caption": "Trading en argent fictif via Alpaca — expérimentation, pas un conseil d'investissement.",
        "alpaca_missing": (
            "Clés Alpaca manquantes. En local, ajoute ALPACA_API_KEY et "
            "ALPACA_SECRET_KEY dans ton fichier .env (compte paper sur alpaca.markets). "
            "Le paper trading fonctionne en local, pas sur la version en ligne publique."
        ),
        "alpaca_connect_error": "Connexion à Alpaca impossible. Vérifie tes clés (mode paper).",
        "account_header": "💼 Ton compte (paper)",
        "m_cash": "Liquidités",
        "m_portfolio": "Valeur du portefeuille",
        "m_buying_power": "Pouvoir d'achat",
        "m_positions": "Positions",
        "positions_header": "📊 Positions ouvertes",
        "no_positions": "Aucune position ouverte.",
        "orders_header": "🧾 Derniers ordres",
        "no_orders": "Aucun ordre pour l'instant.",
        "equity_header": "📈 Valeur du portefeuille dans le temps",
        "pl_header": "Résultat latent par position ($)",
        "readonly_note": "👀 Vue en lecture seule — le bot trade automatiquement. Personne ne peut passer d'ordre ici.",
        "trades_header": "📉 Points d'entrée / sortie du bot",
        "no_trades_yet": "Aucun trade pour l'instant.",
        "stock_label": "Action",
        "trades_caption": "Triangles verts = achats du bot, rouges = ventes (aux prix réellement exécutés).",
        "strategy_header": "🎯 Passer un ordre",
        "us_only": "⚠️ Alpaca ne trade que des actions américaines (AAPL, TSLA...).",
        "qty_label": "Quantité (nb d'actions)",
        "signal_invested": "Signal MA{short}/MA{long} : **ACHAT** (MA courte au-dessus de la longue).",
        "signal_flat": "Signal MA{short}/MA{long} : **HORS MARCHÉ** (MA courte sous la longue).",
        "btn_follow": "Suivre le signal",
        "btn_buy": "Acheter",
        "btn_sell": "Vendre / clôturer",
        "order_ok": "✅ Ordre envoyé : {side} {qty} {symbol}.",
        "order_err": "❌ Échec de l'ordre : {err}",
        "nothing_to_do": "Rien à faire : le signal correspond déjà à ta position actuelle.",
        "no_position_to_sell": "Tu n'as pas de position sur {symbol} à vendre.",
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
        "market_label": "Market",
        "company_label": "Company",
        "custom_group": "✏️ Other (enter a symbol)",
        "period_label": "Period",
        "examples": (
            "Examples — **Stocks**: `AAPL` (Apple), `MSFT`, `TSLA`, `MC.PA` (LVMH), "
            "`GLE.PA` (Société Générale)  ·  **Indices**: `^FCHI` (CAC 40), "
            "`^GSPC` (S&P 500), `^IXIC` (Nasdaq)."
        ),
        "enter_symbol": "Enter a symbol above to start the analysis.",
        "no_data": (
            "No data for “{ticker}”. Look up the exact symbol on finance.yahoo.com. "
            "For European stocks, add the exchange suffix: `MC.PA` (LVMH, Paris), "
            "`SIE.DE` (Frankfurt), `ASML.AS` (Amsterdam), `^FCHI` (CAC 40)."
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
        # paper trading
        "nav_paper": "Paper Trading",
        "paper_title": "🤖 Paper Trading",
        "paper_caption": "Paper (fake-money) trading via Alpaca — experimentation, not investment advice.",
        "alpaca_missing": (
            "Alpaca keys missing. Locally, add ALPACA_API_KEY and ALPACA_SECRET_KEY "
            "to your .env file (paper account on alpaca.markets). Paper trading works "
            "locally, not on the public online version."
        ),
        "alpaca_connect_error": "Couldn't connect to Alpaca. Check your keys (paper mode).",
        "account_header": "💼 Your account (paper)",
        "m_cash": "Cash",
        "m_portfolio": "Portfolio value",
        "m_buying_power": "Buying power",
        "m_positions": "Positions",
        "positions_header": "📊 Open positions",
        "no_positions": "No open positions.",
        "orders_header": "🧾 Recent orders",
        "no_orders": "No orders yet.",
        "equity_header": "📈 Portfolio value over time",
        "pl_header": "Unrealized P/L by position ($)",
        "readonly_note": "👀 Read-only view — the bot trades automatically. Nobody can place orders here.",
        "trades_header": "📉 Bot entry / exit points",
        "no_trades_yet": "No trades yet.",
        "stock_label": "Stock",
        "trades_caption": "Green triangles = bot buys, red = sells (at the actually executed prices).",
        "strategy_header": "🎯 Place an order",
        "us_only": "⚠️ Alpaca only trades US stocks (AAPL, TSLA...).",
        "qty_label": "Quantity (shares)",
        "signal_invested": "MA{short}/MA{long} signal: **BUY** (short MA above long MA).",
        "signal_flat": "MA{short}/MA{long} signal: **FLAT** (short MA below long MA).",
        "btn_follow": "Follow the signal",
        "btn_buy": "Buy",
        "btn_sell": "Sell / close",
        "order_ok": "✅ Order sent: {side} {qty} {symbol}.",
        "order_err": "❌ Order failed: {err}",
        "nothing_to_do": "Nothing to do: the signal already matches your current position.",
        "no_position_to_sell": "You have no position in {symbol} to sell.",
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


# ===========================================================================
#  READY-MADE SYMBOL LISTS + PICKER
# ===========================================================================
# Ready-made lists of Yahoo Finance tickers, so the user can pick from a menu
# instead of typing symbols. "name shown to the user": "yahoo ticker".
PRESETS = {
    "CAC 40": {
        "Accor": "AC.PA", "Air Liquide": "AI.PA", "Airbus": "AIR.PA",
        "Alstom": "ALO.PA", "AXA": "CS.PA", "BNP Paribas": "BNP.PA",
        "Bouygues": "EN.PA", "Capgemini": "CAP.PA", "Carrefour": "CA.PA",
        "Crédit Agricole": "ACA.PA", "Danone": "BN.PA", "Dassault Systèmes": "DSY.PA",
        "Edenred": "EDEN.PA", "Engie": "ENGI.PA", "EssilorLuxottica": "EL.PA",
        "Hermès": "RMS.PA", "Kering": "KER.PA", "Legrand": "LR.PA",
        "L'Oréal": "OR.PA", "LVMH": "MC.PA", "Michelin": "ML.PA",
        "Orange": "ORA.PA", "Pernod Ricard": "RI.PA", "Publicis": "PUB.PA",
        "Renault": "RNO.PA", "Safran": "SAF.PA", "Saint-Gobain": "SGO.PA",
        "Sanofi": "SAN.PA", "Schneider Electric": "SU.PA", "Société Générale": "GLE.PA",
        "Stellantis": "STLAP.PA", "STMicroelectronics": "STMPA.PA", "Teleperformance": "TEP.PA",
        "Thales": "HO.PA", "TotalEnergies": "TTE.PA", "Veolia": "VIE.PA",
        "Vinci": "DG.PA",
    },
    "S&P 500 (grandes valeurs)": {
        "Apple": "AAPL", "Microsoft": "MSFT", "Nvidia": "NVDA", "Amazon": "AMZN",
        "Alphabet (Google)": "GOOGL", "Meta": "META", "Tesla": "TSLA",
        "Berkshire Hathaway": "BRK-B", "JPMorgan": "JPM", "Visa": "V",
        "Mastercard": "MA", "UnitedHealth": "UNH", "Johnson & Johnson": "JNJ",
        "Walmart": "WMT", "Procter & Gamble": "PG", "ExxonMobil": "XOM",
        "Home Depot": "HD", "Coca-Cola": "KO", "PepsiCo": "PEP", "Netflix": "NFLX",
        "Disney": "DIS", "McDonald's": "MCD", "Nike": "NKE", "Intel": "INTC",
        "AMD": "AMD", "Boeing": "BA", "Salesforce": "CRM", "Adobe": "ADBE",
        "Oracle": "ORCL", "Pfizer": "PFE", "Bank of America": "BAC", "Chevron": "CVX",
        "Costco": "COST", "Starbucks": "SBUX", "Goldman Sachs": "GS", "IBM": "IBM",
        "Qualcomm": "QCOM", "Uber": "UBER", "Ford": "F",
    },
    "Indices": {
        "CAC 40 (indice)": "^FCHI", "S&P 500 (indice)": "^GSPC",
        "Nasdaq (indice)": "^IXIC", "Dow Jones (indice)": "^DJI",
    },
}


def pick_symbol(key: str, markets=None) -> str:
    """Show a market menu + company menu (with an 'Other' free-text option) and
    return the chosen Yahoo Finance ticker.

    `markets` optionally restricts which preset groups are shown (e.g. US only).
    """
    groups = markets if markets is not None else list(PRESETS.keys())
    options = groups + ["__custom__"]
    market = st.selectbox(
        t("market_label"), options,
        format_func=lambda o: t("custom_group") if o == "__custom__" else o,
        key=key + "_mkt",
    )
    if market == "__custom__":
        sym = st.text_input(t("symbol_label"), value="AAPL", key=key + "_txt").strip()
        st.caption(t("examples"))
        return sym
    mapping = PRESETS[market]
    name = st.selectbox(t("company_label"), list(mapping.keys()), key=key + "_co")
    return mapping[name]
