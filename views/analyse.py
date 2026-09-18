"""views/analyse.py — Market analysis page (bilingual)."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from common import generate, check_key, t, pick_symbol
from data import get_prices

check_key()

st.title(t("analyse_title"))
st.caption(t("disclaimer"))

# --- Inputs ----------------------------------------------------------------
col_a, col_b = st.columns([2, 1])
with col_a:
    ticker = pick_symbol("analyse")
with col_b:
    period = st.selectbox(t("period_label"), ["3mo", "6mo", "1y", "2y", "5y"], index=2)


# --- Download (via the shared data layer: Yahoo or Refinitiv) --------------
if not ticker:
    st.info(t("enter_symbol"))
    st.stop()

data = get_prices(ticker, period)
if data.empty:
    st.error(t("no_data", ticker=ticker))
    st.stop()


# --- Indicators ------------------------------------------------------------
data["MA20"] = data["Close"].rolling(window=20).mean()
data["MA50"] = data["Close"].rolling(window=50).mean()

delta = data["Close"].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.rolling(window=14).mean()
avg_loss = loss.rolling(window=14).mean()
rs = avg_gain / avg_loss
data["RSI"] = 100 - (100 / (1 + rs))

daily_returns = data["Close"].pct_change()
annual_vol = daily_returns.std() * np.sqrt(252)

last_close = data["Close"].iloc[-1]
first_close = data["Close"].iloc[0]
period_change = (last_close / first_close - 1) * 100
last_rsi = data["RSI"].iloc[-1]
last_ma20 = data["MA20"].iloc[-1]
last_ma50 = data["MA50"].iloc[-1]


# --- Metric row ------------------------------------------------------------
m1, m2, m3, m4 = st.columns(4)
m1.metric(t("m_last"), f"{last_close:,.2f}")
m2.metric(t("m_change", period=period), f"{period_change:+.1f}%")
m3.metric(t("m_rsi"), f"{last_rsi:.0f}" if pd.notna(last_rsi) else "—")
m4.metric(t("m_vol"), f"{annual_vol*100:.1f}%")


# --- Charts ----------------------------------------------------------------
fig = make_subplots(
    rows=2, cols=1, shared_xaxes=True,
    row_heights=[0.72, 0.28], vertical_spacing=0.05,
    subplot_titles=(t("chart_price_title", ticker=ticker), t("chart_rsi_title")),
)
fig.add_trace(
    go.Candlestick(
        x=data.index, open=data["Open"], high=data["High"],
        low=data["Low"], close=data["Close"], name=t("trace_price"),
    ),
    row=1, col=1,
)
fig.add_trace(go.Scatter(x=data.index, y=data["MA20"], name="MA20",
                         line=dict(width=1.2)), row=1, col=1)
fig.add_trace(go.Scatter(x=data.index, y=data["MA50"], name="MA50",
                         line=dict(width=1.2)), row=1, col=1)
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


# --- AI commentary ---------------------------------------------------------
st.subheader(t("bot_analysis"))

trend = t("trend_up") if last_ma20 > last_ma50 else t("trend_down")
prompt = t(
    "analyse_prompt",
    ticker=ticker, period=period, last=last_close, change=period_change,
    ma20=last_ma20, ma50=last_ma50, trend=trend, rsi=last_rsi, vol=annual_vol * 100,
)

if st.button(t("generate_btn")):
    with st.spinner(t("analysing")):
        st.markdown(generate(prompt, t("analyse_system")))
else:
    st.info(t("generate_hint"))
