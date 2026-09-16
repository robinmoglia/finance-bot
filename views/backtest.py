"""views/backtest.py — Backtest a moving-average crossover strategy.

Idea of the strategy:
  - When the SHORT moving average crosses ABOVE the long one  -> we are "invested".
  - When it crosses back BELOW                                -> we are "in cash".
We then replay the past day by day and compare the result to simply buying and
holding the asset the whole time.

Honesty note (important): this is a teaching backtest. A good-looking backtest
often fails in real life. It does not predict the future.
"""

import numpy as np
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from common import generate, check_key

check_key()

st.title("🧪 Backtesting")
st.caption("Test d'une stratégie sur le passé — pédagogique, pas un conseil d'investissement.")


# --- 1. Inputs -------------------------------------------------------------
col_a, col_b, col_c = st.columns([2, 1, 1])
with col_a:
    ticker = st.text_input("Symbole (format Yahoo Finance)", value="AAPL").strip()
with col_b:
    period = st.selectbox("Période", ["1y", "2y", "5y", "10y", "max"], index=2)
with col_c:
    fee_pct = st.number_input("Frais par trade (%)", value=0.10, step=0.05, min_value=0.0)

col_d, col_e = st.columns(2)
with col_d:
    short_win = st.slider("Moyenne mobile courte (jours)", 5, 50, 20)
with col_e:
    long_win = st.slider("Moyenne mobile longue (jours)", 30, 200, 50)

if short_win >= long_win:
    st.warning("La moyenne courte doit être plus petite que la longue.")
    st.stop()


# --- 2. Data ---------------------------------------------------------------
@st.cache_data(ttl=3600)
def load_data(symbol: str, period: str) -> pd.DataFrame:
    return yf.Ticker(symbol).history(period=period)

if not ticker:
    st.info("Entre un symbole pour lancer le backtest.")
    st.stop()

data = load_data(ticker, period)
if data.empty or len(data) < long_win + 5:
    st.error(f"Pas assez de données pour « {ticker} » sur cette période.")
    st.stop()


# --- 3. The backtest (step by step) ----------------------------------------
df = data.copy()
fee = fee_pct / 100.0                                   # 0.10% -> 0.001

# a) the two moving averages
df["short"] = df["Close"].rolling(short_win).mean()
df["long"] = df["Close"].rolling(long_win).mean()

# b) the signal: True the days the short MA is above the long MA
signal = df["short"] > df["long"]

# c) the position: we can only ACT the day AFTER we see the signal (no cheating
#    by using information we wouldn't have had yet). So we shift the signal by 1 day.
position = signal.shift(1).fillna(False)

# d) daily returns of the asset
ret = df["Close"].pct_change().fillna(0)

# e) a "trade" happens each day the position changes (enter OR exit)
trade = position.ne(position.shift(1).fillna(False))

# f) strategy daily return = asset return WHEN invested, minus fees on trade days
strat_ret = position.astype(int) * ret - trade.astype(int) * fee

# g) equity curves: 1 € invested at the start, how does it grow?
df["strategy"] = (1 + strat_ret).cumprod()
df["buy_hold"] = (1 + ret).cumprod()


# --- 4. Performance metrics ------------------------------------------------
def max_drawdown(equity: pd.Series) -> float:
    """Biggest drop from a peak, in %. (How much you'd have suffered.)"""
    running_max = equity.cummax()
    drawdown = equity / running_max - 1
    return drawdown.min() * 100

strat_total = (df["strategy"].iloc[-1] - 1) * 100
bh_total = (df["buy_hold"].iloc[-1] - 1) * 100
n_trades = int(((position) & (~position.shift(1).fillna(False))).sum())   # number of BUYS
strat_dd = max_drawdown(df["strategy"])
bh_dd = max_drawdown(df["buy_hold"])
# Sharpe ratio: return per unit of risk (higher = better). Annualized.
sharpe = (strat_ret.mean() / strat_ret.std() * np.sqrt(252)) if strat_ret.std() > 0 else 0
time_invested = position.mean() * 100                                     # % of days in market


# --- 5. Metric row ---------------------------------------------------------
m1, m2, m3, m4 = st.columns(4)
m1.metric("Rendement stratégie", f"{strat_total:+.1f}%")
m2.metric("Rendement buy & hold", f"{bh_total:+.1f}%",
          delta=f"{strat_total - bh_total:+.1f} pts vs stratégie", delta_color="off")
m3.metric("Perte max (drawdown)", f"{strat_dd:.1f}%")
m4.metric("Ratio de Sharpe", f"{sharpe:.2f}")

st.caption(
    f"Nombre d'achats : {n_trades}  ·  Temps investi : {time_invested:.0f}% du temps  "
    f"·  Drawdown buy & hold : {bh_dd:.1f}%"
)


# --- 6. Charts -------------------------------------------------------------
# a) equity curves: strategy vs buy & hold
eq = go.Figure()
eq.add_trace(go.Scatter(x=df.index, y=df["strategy"], name="Stratégie"))
eq.add_trace(go.Scatter(x=df.index, y=df["buy_hold"], name="Buy & Hold"))
eq.update_layout(
    title="Évolution de 1 € investi",
    height=380, legend=dict(orientation="h", y=1.02, yanchor="bottom"),
    margin=dict(l=10, r=10, t=40, b=10),
)
st.plotly_chart(eq, use_container_width=True)

# b) price + MAs + buy/sell markers
buys = df.index[(position) & (~position.shift(1).fillna(False))]
sells = df.index[(~position) & (position.shift(1).fillna(False))]

pr = go.Figure()
pr.add_trace(go.Scatter(x=df.index, y=df["Close"], name="Cours", line=dict(width=1)))
pr.add_trace(go.Scatter(x=df.index, y=df["short"], name=f"MA{short_win}", line=dict(width=1)))
pr.add_trace(go.Scatter(x=df.index, y=df["long"], name=f"MA{long_win}", line=dict(width=1)))
pr.add_trace(go.Scatter(x=buys, y=df.loc[buys, "Close"], name="Achat",
                        mode="markers", marker=dict(symbol="triangle-up", size=10, color="green")))
pr.add_trace(go.Scatter(x=sells, y=df.loc[sells, "Close"], name="Vente",
                        mode="markers", marker=dict(symbol="triangle-down", size=10, color="red")))
pr.update_layout(
    title=f"{ticker} — signaux d'achat / vente",
    height=420, legend=dict(orientation="h", y=1.02, yanchor="bottom"),
    margin=dict(l=10, r=10, t=40, b=10),
)
st.plotly_chart(pr, use_container_width=True)


# --- 7. AI commentary ------------------------------------------------------
st.subheader("🧠 Analyse du bot")
SYSTEM = (
    "Tu es un analyste quantitatif pédagogue. À partir des résultats d'un "
    "backtest, tu expliques en français (5-8 phrases) si la stratégie a battu le "
    "buy & hold, à quel prix (drawdown, nombre de trades), ce que dit le ratio de "
    "Sharpe, et tu rappelles les limites d'un backtest (frais réels, sur-optimisation, "
    "le passé ne prédit pas le futur). Jamais de conseil d'investissement."
)
prompt = (
    f"Backtest d'une stratégie de croisement de moyennes mobiles (MA{short_win}/MA{long_win}) "
    f"sur {ticker}, période {period}, frais {fee_pct}% par trade :\n"
    f"- Rendement stratégie : {strat_total:+.1f}%\n"
    f"- Rendement buy & hold : {bh_total:+.1f}%\n"
    f"- Nombre d'achats : {n_trades}\n"
    f"- Temps investi : {time_invested:.0f}% du temps\n"
    f"- Drawdown max stratégie : {strat_dd:.1f}% (buy & hold : {bh_dd:.1f}%)\n"
    f"- Ratio de Sharpe stratégie : {sharpe:.2f}\n"
)
if st.button("Générer l'analyse"):
    with st.spinner("Analyse en cours..."):
        st.markdown(generate(prompt, SYSTEM))
else:
    st.info("Clique sur « Générer l'analyse » pour que le bot commente le backtest.")
