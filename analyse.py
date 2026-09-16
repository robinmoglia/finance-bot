"""
analyse.py — Market analysis module (with daily chart + AI commentary).

What it does:
  1. Downloads daily prices for a stock or index (free, via yfinance).
  2. Computes indicators with pandas: moving averages, RSI, volatility.
  3. Draws a candlestick chart + an RSI chart (interactive, via plotly).
  4. Asks Gemini to write a short analysis in French below the chart.

Run it with:  python -m streamlit run analyse.py

New libraries needed (install once):  pip install yfinance plotly
"""

import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai import errors
import streamlit as st
import yfinance as yf                       # free market data
import pandas as pd                         # data handling (your AIDAMS toolbox)
import numpy as np                          # for the annualized volatility math
import plotly.graph_objects as go           # interactive charts
from plotly.subplots import make_subplots   # to stack price + RSI


# --- 1. Gemini setup (same pattern as your other files) --------------------
load_dotenv()
API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL = "gemini-flash-lite-latest"

if not API_KEY:
    st.error("Clé API manquante. Vérifie ton fichier .env (GEMINI_API_KEY).")
    st.stop()

@st.cache_resource
def get_client():
    return genai.Client(api_key=API_KEY)

client = get_client()


def ai_comment(prompt: str, max_retries: int = 3) -> str:
    """Ask Gemini for a French analysis, retrying if the model is busy (503)."""
    system = (
        "Tu es un analyste financier pédagogue. À partir des chiffres fournis, "
        "tu rédiges une analyse courte et claire en français (5-8 phrases), "
        "structurée : tendance, momentum (RSI), volatilité, et un mot de prudence. "
        "Tu ne donnes JAMAIS de conseil d'achat ou de vente personnalisé."
    )
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
                return "⚠️ Le modèle est très demandé, réessaie dans un instant."


# --- 2. Page + inputs -------------------------------------------------------
st.set_page_config(page_title="Analyse Marché", page_icon="📈", layout="wide")
st.title("📈 Analyse Marché")
st.caption("Analyse pédagogique — ne constitue pas un conseil d'investissement.")

# The symbol uses Yahoo Finance format. We give examples for stocks and indices.
col_a, col_b = st.columns([2, 1])
with col_a:
    ticker = st.text_input("Symbole (format Yahoo Finance)", value="AAPL").strip()
with col_b:
    period = st.selectbox("Période", ["3mo", "6mo", "1y", "2y", "5y"], index=2)

st.caption(
    "Exemples — **Actions** : `AAPL` (Apple), `MSFT`, `TSLA`, `MC.PA` (LVMH), "
    "`AIR.PA` (Airbus)  ·  **Indices** : `^FCHI` (CAC 40), `^GSPC` (S&P 500), "
    "`^IXIC` (Nasdaq)."
)


# --- 3. Download data -------------------------------------------------------
# .history() returns clean columns: Open, High, Low, Close, Volume.
# @st.cache_data avoids re-downloading the same request on every interaction.
@st.cache_data(ttl=3600)
def load_data(symbol: str, period: str) -> pd.DataFrame:
    return yf.Ticker(symbol).history(period=period)

if not ticker:
    st.info("Entre un symbole ci-dessus pour lancer l'analyse.")
    st.stop()

data = load_data(ticker, period)

# If the symbol is wrong or has no data, yfinance returns an empty table.
if data.empty:
    st.error(
        f"Aucune donnée pour « {ticker} ». Vérifie le symbole "
        "(ex. `MC.PA` pour LVMH, `^FCHI` pour le CAC 40)."
    )
    st.stop()


# --- 4. Compute indicators (pandas) ----------------------------------------
# Moving averages: the average closing price over the last N days. They smooth
# the noise and show the trend. MA20 = short term, MA50 = medium term.
data["MA20"] = data["Close"].rolling(window=20).mean()
data["MA50"] = data["Close"].rolling(window=50).mean()

# RSI (Relative Strength Index): momentum indicator between 0 and 100.
# >70 = often "overbought", <30 = often "oversold". Classic 14-day version.
delta = data["Close"].diff()                     # daily price change
gain = delta.clip(lower=0)                        # keep only the up moves
loss = -delta.clip(upper=0)                       # keep only the down moves (as positive)
avg_gain = gain.rolling(window=14).mean()
avg_loss = loss.rolling(window=14).mean()
rs = avg_gain / avg_loss                          # relative strength
data["RSI"] = 100 - (100 / (1 + rs))

# Volatility: how much the price moves. We take the standard deviation of the
# daily returns and annualize it (x sqrt(252), the ~number of trading days/year).
daily_returns = data["Close"].pct_change()
annual_vol = daily_returns.std() * np.sqrt(252)

# A few summary numbers for the metric row and the AI prompt.
last_close = data["Close"].iloc[-1]
first_close = data["Close"].iloc[0]
period_change = (last_close / first_close - 1) * 100      # % change over the period
last_rsi = data["RSI"].iloc[-1]
last_ma20 = data["MA20"].iloc[-1]
last_ma50 = data["MA50"].iloc[-1]


# --- 5. Metric row ----------------------------------------------------------
m1, m2, m3, m4 = st.columns(4)
m1.metric("Dernier cours", f"{last_close:,.2f}")
m2.metric(f"Variation ({period})", f"{period_change:+.1f}%")
m3.metric("RSI (14j)", f"{last_rsi:.0f}" if pd.notna(last_rsi) else "—")
m4.metric("Volatilité annualisée", f"{annual_vol*100:.1f}%")


# --- 6. Charts (candlestick + moving averages, then RSI below) -------------
fig = make_subplots(
    rows=2, cols=1, shared_xaxes=True,
    row_heights=[0.72, 0.28], vertical_spacing=0.05,
    subplot_titles=(f"{ticker} — cours journalier", "RSI (14 jours)"),
)

# Candlesticks: each "candle" shows open/high/low/close for one day.
fig.add_trace(
    go.Candlestick(
        x=data.index, open=data["Open"], high=data["High"],
        low=data["Low"], close=data["Close"], name="Cours",
    ),
    row=1, col=1,
)
# Moving averages on top of the candles.
fig.add_trace(go.Scatter(x=data.index, y=data["MA20"], name="MA20",
                         line=dict(width=1.2)), row=1, col=1)
fig.add_trace(go.Scatter(x=data.index, y=data["MA50"], name="MA50",
                         line=dict(width=1.2)), row=1, col=1)

# RSI on the second row, with the 70 / 30 reference lines.
fig.add_trace(go.Scatter(x=data.index, y=data["RSI"], name="RSI",
                         line=dict(width=1.2)), row=2, col=1)
fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.4, row=2, col=1)
fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.4, row=2, col=1)

fig.update_layout(
    height=650, xaxis_rangeslider_visible=False,
    legend=dict(orientation="h", y=1.02, yanchor="bottom"),
    margin=dict(l=10, r=10, t=40, b=10),
)
st.plotly_chart(fig, use_container_width=True)


# --- 7. AI commentary -------------------------------------------------------
st.subheader("🧠 Analyse du bot")

# We turn the numbers into a short text prompt for the model.
trend = "haussière" if last_ma20 > last_ma50 else "baissière"
prompt = (
    f"Analyse les données suivantes pour {ticker} sur la période {period} :\n"
    f"- Dernier cours : {last_close:.2f}\n"
    f"- Variation sur la période : {period_change:+.1f}%\n"
    f"- MA20 vs MA50 : MA20={last_ma20:.2f}, MA50={last_ma50:.2f} "
    f"(croisement de tendance {trend})\n"
    f"- RSI (14j) : {last_rsi:.0f}\n"
    f"- Volatilité annualisée : {annual_vol*100:.1f}%\n"
)

# We only call the (paid-quota) model when the user asks, to save requests.
if st.button("Générer l'analyse"):
    with st.spinner("Analyse en cours..."):
        st.markdown(ai_comment(prompt))
else:
    st.info("Clique sur « Générer l'analyse » pour que le bot commente ces chiffres.")
