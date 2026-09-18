"""
data.py — One place to get market prices, whatever the source.

Order of attempts:
  1. Refinitiv/LSEG  — only if DATA_SOURCE=refinitiv and Workspace is running.
  2. Yahoo Finance   — the default (with automatic retries for rate-limits).
  3. Stooq           — a free backup if Yahoo fails entirely.

All sources return the SAME columns: Open, High, Low, Close (+ Volume),
with a datetime index — so the rest of the app doesn't care which one is used.
"""

import os
import time
from datetime import date, timedelta

import pandas as pd
import streamlit as st


def _source() -> str:
    src = os.environ.get("DATA_SOURCE")
    if not src:
        try:
            src = st.secrets.get("DATA_SOURCE")
        except Exception:
            src = None
    return (src or "yahoo").lower()


_PERIOD_DAYS = {
    "3mo": 90, "6mo": 180, "1y": 365, "2y": 730,
    "5y": 1825, "10y": 3650, "max": 3650 * 3,
}


@st.cache_data(ttl=3600, show_spinner=False)
def get_prices(ticker: str, period: str) -> pd.DataFrame:
    """Return daily OHLC prices for `ticker` over `period`, trying several sources."""
    # 1. Refinitiv (local only)
    if _source() == "refinitiv":
        try:
            df = _from_refinitiv(ticker, period)
            if df is not None and not df.empty:
                return df
        except Exception:
            pass

    # 2. Yahoo Finance (with retries for transient rate-limits / HTTP 429)
    df = _from_yahoo(ticker, period)
    if df is not None and not df.empty:
        return df

    # 3. Stooq — free backup when Yahoo returns nothing
    try:
        df2 = _from_stooq(ticker, period)
        if df2 is not None and not df2.empty:
            return df2
    except Exception:
        pass

    return df if df is not None else pd.DataFrame()


# --- Yahoo Finance (default, with retries) ---------------------------------
def _from_yahoo(ticker: str, period: str, retries: int = 3) -> pd.DataFrame:
    import yfinance as yf
    df = pd.DataFrame()
    for attempt in range(retries):
        try:
            df = yf.Ticker(ticker).history(period=period)
        except Exception:
            df = pd.DataFrame()
        if not df.empty:
            return df
        time.sleep(1.5 * (attempt + 1))   # wait a bit longer each time
    return df


# --- Stooq (free backup, no account needed) --------------------------------
def _from_stooq(ticker: str, period: str) -> pd.DataFrame:
    """Fetch daily OHLC from Stooq (CSV). Best-effort backup for when Yahoo fails.

    Stooq uses its own suffixes (e.g. US stocks end in .us). We add .us when the
    symbol has no suffix; other symbols are passed through as-is.
    """
    sym = ticker.strip().lower()
    if "." not in sym and not sym.startswith("^"):
        sym = sym + ".us"

    url = f"https://stooq.com/q/d/l/?s={sym}&i=d"
    df = pd.read_csv(url)
    if df.empty or "Date" not in df.columns:
        return pd.DataFrame()

    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()

    # Keep only the requested period.
    days = _PERIOD_DAYS.get(period, 365)
    cutoff = pd.Timestamp(date.today() - timedelta(days=days))
    df = df[df.index >= cutoff]
    return df  # columns are already Open, High, Low, Close, Volume


# --- Refinitiv / LSEG (local only, needs Workspace running) -----------------
def _from_refinitiv(ticker: str, period: str) -> pd.DataFrame:
    """Fetch daily OHLC from Refinitiv and normalize it to Yahoo-style columns.

    Requirements (all on YOUR machine): Workspace running, `pip install lseg-data`,
    an App Key configured, and RIC codes as symbols (AAPL.O, MC.PA, .FCHI...).
    """
    import lseg.data as ld

    ld.open_session()
    try:
        days = _PERIOD_DAYS.get(period, 365)
        start = (date.today() - timedelta(days=days)).isoformat()
        end = date.today().isoformat()

        raw = ld.get_history(universe=ticker, interval="daily", start=start, end=end)

        rename = {}
        for col in raw.columns:
            low = str(col).lower()
            if "open" in low:
                rename[col] = "Open"
            elif "high" in low:
                rename[col] = "High"
            elif "low" in low:
                rename[col] = "Low"
            elif "close" in low or "trdprc" in low or "price" in low:
                rename[col] = "Close"
            elif "volume" in low or "acvol" in low:
                rename[col] = "Volume"
        df = raw.rename(columns=rename)

        if "Close" in df.columns:
            for c in ("Open", "High", "Low"):
                if c not in df.columns:
                    df[c] = df["Close"]

        df.index = pd.to_datetime(df.index)
        return df
    finally:
        ld.close_session()
