"""views/paper.py — Paper trading dashboard (Alpaca).

Two modes:
  - PUBLIC (default, e.g. online): a READ-ONLY dashboard of the bot's account,
    equity curve, positions and orders. No buttons — nobody can trade.
  - LOCAL: if the env var LOCAL_MODE is set (in your local .env), the manual
    order controls (buy / sell / follow signal) also appear, for you only.
"""

import os
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from common import t, pick_symbol
from data import get_prices


def _cred(name: str):
    val = os.environ.get(name)
    if not val:
        try:
            val = st.secrets.get(name)
        except Exception:
            val = None
    return val


API_KEY = _cred("ALPACA_API_KEY")
SECRET_KEY = _cred("ALPACA_SECRET_KEY")
LOCAL = bool(_cred("LOCAL_MODE"))   # trading controls only appear when this is set

st.title(t("paper_title"))
st.caption(t("paper_caption"))

if not API_KEY or not SECRET_KEY:
    st.info(t("alpaca_missing"))
    st.stop()


@st.cache_resource
def get_client():
    from alpaca.trading.client import TradingClient
    return TradingClient(API_KEY, SECRET_KEY, paper=True)

try:
    client = get_client()
    account = client.get_account()
except Exception as e:
    st.error(t("alpaca_connect_error"))
    st.caption(f"Détail : {type(e).__name__}: {e}")
    st.stop()

# Read-only banner (shown to everyone; the local user also gets controls below).
if not LOCAL:
    st.success(t("readonly_note"))


# --- Live dashboard (auto-refreshes every 30 seconds) ----------------------
# @st.fragment(run_every=30) reruns ONLY this block every 30s, so the account,
# positions, chart and orders update on their own without reloading the page.
@st.fragment(run_every=30)
def dashboard():
    acct = client.get_account()
    positions = client.get_all_positions()

    # Account panel
    st.subheader(t("account_header"))
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(t("m_cash"), f"{float(acct.cash):,.0f} $")
    m2.metric(t("m_portfolio"), f"{float(acct.portfolio_value):,.0f} $")
    m3.metric(t("m_buying_power"), f"{float(acct.buying_power):,.0f} $")
    m4.metric(t("m_positions"), len(positions))

    # Equity curve (portfolio value over time)
    st.subheader(t("equity_header"))
    try:
        from alpaca.trading.requests import GetPortfolioHistoryRequest
        hist = client.get_portfolio_history(
            GetPortfolioHistoryRequest(period="1M", timeframe="1D")
        )
        if hist.timestamp and hist.equity:
            eq = pd.DataFrame(
                {"$": [v for v in hist.equity]},
                index=pd.to_datetime(hist.timestamp, unit="s"),
            )
            st.line_chart(eq)
        else:
            st.caption("—")
    except Exception:
        st.caption("—")

    # Open positions + P/L bar chart
    st.subheader(t("positions_header"))
    if positions:
        rows = [{
            "Symbole": p.symbol,
            "Qté": float(p.qty),
            "Prix moyen": round(float(p.avg_entry_price), 2),
            "Valeur ($)": round(float(p.market_value), 2),
            "P/L latent ($)": round(float(p.unrealized_pl), 2),
            "P/L (%)": round(float(p.unrealized_plpc) * 100, 2),
        } for p in positions]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        st.caption(t("pl_header"))
        pl = pd.DataFrame(
            {"P/L ($)": [float(p.unrealized_pl) for p in positions]},
            index=[p.symbol for p in positions],
        )
        st.bar_chart(pl)
    else:
        st.caption(t("no_positions"))

    # Recent orders
    st.subheader(t("orders_header"))
    try:
        from alpaca.trading.requests import GetOrdersRequest
        from alpaca.trading.enums import QueryOrderStatus
        orders = client.get_orders(GetOrdersRequest(status=QueryOrderStatus.ALL, limit=15))
    except Exception:
        orders = []

    if orders:
        orows = [{
            "Date": str(o.submitted_at)[:16],
            "Symbole": o.symbol,
            "Sens": o.side.value,
            "Qté": float(o.qty) if o.qty else None,
            "Statut": o.status.value,
        } for o in orders]
        st.dataframe(pd.DataFrame(orows), use_container_width=True, hide_index=True)
    else:
        st.caption(t("no_orders"))


dashboard()


# ===========================================================================
#  BOT ENTRY / EXIT POINTS ON A CHART (read-only, visible to everyone)
# ===========================================================================
st.divider()
st.subheader(t("trades_header"))

from alpaca.trading.requests import GetOrdersRequest
from alpaca.trading.enums import QueryOrderStatus

try:
    all_orders = client.get_orders(GetOrdersRequest(status=QueryOrderStatus.ALL, limit=200))
except Exception:
    all_orders = []

# Symbols the bot has touched (from orders + current positions).
traded = sorted({o.symbol for o in all_orders}
                | {p.symbol for p in client.get_all_positions()})

if not traded:
    st.caption(t("no_trades_yet"))
else:
    col_s, col_p = st.columns([2, 1])
    with col_s:
        sym = st.selectbox(t("stock_label"), traded, key="trade_sym")
    with col_p:
        tperiod = st.selectbox(t("period_label"), ["3mo", "6mo", "1y"], index=1, key="trade_period")

    df = get_prices(sym.replace(".", "-"), tperiod)   # Yahoo format for prices
    if df.empty:
        st.caption(t("no_data", ticker=sym))
    else:
        df = df.copy()
        df["MA20"] = df["Close"].rolling(20).mean()
        df["MA50"] = df["Close"].rolling(50).mean()

        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df.index, open=df["Open"], high=df["High"],
            low=df["Low"], close=df["Close"], name=t("trace_price"),
        ))
        fig.add_trace(go.Scatter(x=df.index, y=df["MA20"], name="MA20", line=dict(width=1)))
        fig.add_trace(go.Scatter(x=df.index, y=df["MA50"], name="MA50", line=dict(width=1)))

        # Real filled orders on this symbol -> markers at fill date & price.
        fills = [o for o in all_orders if o.symbol == sym
                 and getattr(o, "filled_at", None) and getattr(o, "filled_avg_price", None)]
        bx = [o.filled_at for o in fills if o.side.value == "buy"]
        by = [float(o.filled_avg_price) for o in fills if o.side.value == "buy"]
        sx = [o.filled_at for o in fills if o.side.value == "sell"]
        sy = [float(o.filled_avg_price) for o in fills if o.side.value == "sell"]
        fig.add_trace(go.Scatter(x=bx, y=by, mode="markers", name=t("trace_buy"),
                                 marker=dict(symbol="triangle-up", size=13, color="green")))
        fig.add_trace(go.Scatter(x=sx, y=sy, mode="markers", name=t("trace_sell"),
                                 marker=dict(symbol="triangle-down", size=13, color="red")))
        fig.update_layout(
            height=460, xaxis_rangeslider_visible=False,
            legend=dict(orientation="h", y=1.02, yanchor="bottom"),
            margin=dict(l=10, r=10, t=30, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(t("trades_caption"))


# ===========================================================================
#  MANUAL TRADING CONTROLS — LOCAL ONLY (hidden on the public site)
# ===========================================================================
if not LOCAL:
    st.stop()   # public visitors stop here: dashboard only, no controls

st.divider()
st.subheader(t("strategy_header"))
st.caption(t("us_only"))

col1, col2 = st.columns([2, 1])
with col1:
    symbol = pick_symbol("paper", markets=["S&P 500 (grandes valeurs)"])
with col2:
    qty = st.number_input(t("qty_label"), min_value=1, value=1, step=1)

c1, c2 = st.columns(2)
with c1:
    short_win = st.slider(t("ma_short_label"), 5, 50, 20, key="paper_short")
with c2:
    long_win = st.slider(t("ma_long_label"), 30, 200, 50, key="paper_long")


def current_signal(sym: str):
    data = get_prices(sym, "1y")
    if data.empty or len(data) < long_win + 2:
        return None
    short = data["Close"].rolling(short_win).mean().iloc[-1]
    long = data["Close"].rolling(long_win).mean().iloc[-1]
    return bool(short > long)


def _alpaca_sym(sym: str) -> str:
    """Alpaca uses a dot for share classes (BRK.B) where Yahoo uses a dash (BRK-B)."""
    return sym.replace("-", ".")


def held_qty(sym: str) -> float:
    try:
        return float(client.get_open_position(_alpaca_sym(sym)).qty)
    except Exception:
        return 0.0


def place(side: str, sym: str, quantity: float):
    from alpaca.trading.requests import MarketOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce
    req = MarketOrderRequest(
        symbol=_alpaca_sym(sym), qty=quantity,
        side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
        time_in_force=TimeInForce.DAY,
    )
    client.submit_order(req)


sig = current_signal(symbol)
if sig is True:
    st.markdown(t("signal_invested", short=short_win, long=long_win))
elif sig is False:
    st.markdown(t("signal_flat", short=short_win, long=long_win))

b1, b2, b3 = st.columns(3)
with b1:
    if st.button(t("btn_buy"), use_container_width=True):
        try:
            place("buy", symbol, qty)
            st.success(t("order_ok", side="BUY", qty=qty, symbol=symbol))
        except Exception as e:
            st.error(t("order_err", err=str(e)))
with b2:
    if st.button(t("btn_sell"), use_container_width=True):
        owned = held_qty(symbol)
        if owned <= 0:
            st.warning(t("no_position_to_sell", symbol=symbol))
        else:
            try:
                place("sell", symbol, owned)
                st.success(t("order_ok", side="SELL", qty=owned, symbol=symbol))
            except Exception as e:
                st.error(t("order_err", err=str(e)))
with b3:
    if st.button(t("btn_follow"), use_container_width=True, type="primary"):
        owned = held_qty(symbol)
        if sig is True and owned <= 0:
            try:
                place("buy", symbol, qty)
                st.success(t("order_ok", side="BUY", qty=qty, symbol=symbol))
            except Exception as e:
                st.error(t("order_err", err=str(e)))
        elif sig is False and owned > 0:
            try:
                place("sell", symbol, owned)
                st.success(t("order_ok", side="SELL", qty=owned, symbol=symbol))
            except Exception as e:
                st.error(t("order_err", err=str(e)))
        else:
            st.info(t("nothing_to_do"))
