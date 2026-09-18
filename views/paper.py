"""views/paper.py — Paper trading dashboard (Alpaca).

Two modes:
  - PUBLIC (default, e.g. online): a READ-ONLY dashboard of the bot's account,
    equity curve, positions and orders. No buttons — nobody can trade.
  - LOCAL: if the env var LOCAL_MODE is set (in your local .env), the manual
    order controls (buy / sell / follow signal) also appear, for you only.
"""

import os
import pandas as pd
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


# --- Account panel ----------------------------------------------------------
st.subheader(t("account_header"))
positions = client.get_all_positions()

m1, m2, m3, m4 = st.columns(4)
m1.metric(t("m_cash"), f"{float(account.cash):,.0f} $")
m2.metric(t("m_portfolio"), f"{float(account.portfolio_value):,.0f} $")
m3.metric(t("m_buying_power"), f"{float(account.buying_power):,.0f} $")
m4.metric(t("m_positions"), len(positions))


# --- Equity curve (portfolio value over time) ------------------------------
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


# --- Open positions + P/L bar chart ----------------------------------------
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


# --- Recent orders ----------------------------------------------------------
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
