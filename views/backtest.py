"""views/backtest.py — Backtest a moving-average crossover strategy (bilingual)."""

import numpy as np
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import streamlit as st

from common import generate, check_key, t

check_key()

st.title(t("backtest_title"))
st.caption(t("backtest_caption"))


# --- Inputs ----------------------------------------------------------------
col_a, col_b, col_c = st.columns([2, 1, 1])
with col_a:
    ticker = st.text_input(t("symbol_label"), value="AAPL").strip()
with col_b:
    period = st.selectbox(t("period_label"), ["1y", "2y", "5y", "10y", "max"], index=2)
with col_c:
    fee_pct = st.number_input(t("fees_label"), value=0.10, step=0.05, min_value=0.0)

col_d, col_e = st.columns(2)
with col_d:
    short_win = st.slider(t("ma_short_label"), 5, 50, 20)
with col_e:
    long_win = st.slider(t("ma_long_label"), 30, 200, 50)

if short_win >= long_win:
    st.warning(t("ma_warn"))
    st.stop()


# --- Data ------------------------------------------------------------------
@st.cache_data(ttl=3600)
def load_data(symbol: str, period: str) -> pd.DataFrame:
    return yf.Ticker(symbol).history(period=period)

if not ticker:
    st.info(t("enter_symbol_bt"))
    st.stop()

data = load_data(ticker, period)
if data.empty or len(data) < long_win + 5:
    st.error(t("not_enough", ticker=ticker))
    st.stop()


# --- Backtest --------------------------------------------------------------
df = data.copy()
fee = fee_pct / 100.0

df["short"] = df["Close"].rolling(short_win).mean()
df["long"] = df["Close"].rolling(long_win).mean()

signal = df["short"] > df["long"]
position = signal.shift(1).fillna(False)          # act the day AFTER the signal (no cheating)
ret = df["Close"].pct_change().fillna(0)
trade = position.ne(position.shift(1).fillna(False))
strat_ret = position.astype(int) * ret - trade.astype(int) * fee

df["strategy"] = (1 + strat_ret).cumprod()
df["buy_hold"] = (1 + ret).cumprod()


def max_drawdown(equity: pd.Series) -> float:
    running_max = equity.cummax()
    return (equity / running_max - 1).min() * 100

strat_total = (df["strategy"].iloc[-1] - 1) * 100
bh_total = (df["buy_hold"].iloc[-1] - 1) * 100
n_trades = int(((position) & (~position.shift(1).fillna(False))).sum())
strat_dd = max_drawdown(df["strategy"])
bh_dd = max_drawdown(df["buy_hold"])
sharpe = (strat_ret.mean() / strat_ret.std() * np.sqrt(252)) if strat_ret.std() > 0 else 0
time_invested = position.mean() * 100


# --- Metric row ------------------------------------------------------------
m1, m2, m3, m4 = st.columns(4)
m1.metric(t("m_strat"), f"{strat_total:+.1f}%")
m2.metric(t("m_bh"), f"{bh_total:+.1f}%",
          delta=t("delta_vs", x=strat_total - bh_total), delta_color="off")
m3.metric(t("m_maxdd"), f"{strat_dd:.1f}%")
m4.metric(t("m_sharpe"), f"{sharpe:.2f}")

st.caption(t("bt_caption", trades=n_trades, invested=time_invested, bhdd=bh_dd))


# --- Charts ----------------------------------------------------------------
eq = go.Figure()
eq.add_trace(go.Scatter(x=df.index, y=df["strategy"], name=t("m_strat")))
eq.add_trace(go.Scatter(x=df.index, y=df["buy_hold"], name="Buy & Hold"))
eq.update_layout(
    title=t("eq_title"),
    height=380, legend=dict(orientation="h", y=1.02, yanchor="bottom"),
    margin=dict(l=10, r=10, t=40, b=10),
)
st.plotly_chart(eq, use_container_width=True)

buys = df.index[(position) & (~position.shift(1).fillna(False))]
sells = df.index[(~position) & (position.shift(1).fillna(False))]

pr = go.Figure()
pr.add_trace(go.Scatter(x=df.index, y=df["Close"], name=t("trace_price"), line=dict(width=1)))
pr.add_trace(go.Scatter(x=df.index, y=df["short"], name=f"MA{short_win}", line=dict(width=1)))
pr.add_trace(go.Scatter(x=df.index, y=df["long"], name=f"MA{long_win}", line=dict(width=1)))
pr.add_trace(go.Scatter(x=buys, y=df.loc[buys, "Close"], name=t("trace_buy"),
                        mode="markers", marker=dict(symbol="triangle-up", size=10, color="green")))
pr.add_trace(go.Scatter(x=sells, y=df.loc[sells, "Close"], name=t("trace_sell"),
                        mode="markers", marker=dict(symbol="triangle-down", size=10, color="red")))
pr.update_layout(
    title=t("signals_title", ticker=ticker),
    height=420, legend=dict(orientation="h", y=1.02, yanchor="bottom"),
    margin=dict(l=10, r=10, t=40, b=10),
)
st.plotly_chart(pr, use_container_width=True)


# --- AI commentary ---------------------------------------------------------
st.subheader(t("bot_analysis"))
prompt = t(
    "backtest_prompt",
    short=short_win, long=long_win, ticker=ticker, period=period, fee=fee_pct,
    strat=strat_total, bh=bh_total, trades=n_trades, invested=time_invested,
    dd=strat_dd, bhdd=bh_dd, sharpe=sharpe,
)
if st.button(t("generate_btn")):
    with st.spinner(t("analysing")):
        st.markdown(generate(prompt, t("backtest_system")))
else:
    st.info(t("bt_generate_hint"))
