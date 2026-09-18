"""
bot.py — The automatic trading bot (paper, Alpaca).

This is a STANDALONE script (it does NOT use Streamlit). Each time you run it,
it does ONE pass over the watchlist:
  - computes the MA20/MA50 signal for each stock,
  - looks at your current Alpaca position,
  - buys if the signal turned to "buy" and you're not invested,
  - sells (closes) if the signal turned to "flat" and you hold the stock,
  - does nothing otherwise.

Run one pass:      python bot.py
Run in a loop:     python bot.py --loop        (checks every hour, Ctrl+C to stop)

To make it fully automatic, schedule "python bot.py" once a day (see README /
the cron example your assistant gave you). The bot only runs when your Mac is on.

⚠️ Paper money only. Educational project — not investment advice.
"""

import os
import sys
import time
from datetime import datetime

from dotenv import load_dotenv
import yfinance as yf
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce


# ===========================================================================
#  CONFIG — edit these to change the bot's behavior
# ===========================================================================
WATCHLIST = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "TSLA"]  # US stocks only
SHORT_WINDOW = 20      # short moving average (days)
LONG_WINDOW = 50       # long moving average (days)
QTY = 5                # number of shares to buy per position
LOOP_EVERY = 3600      # seconds between checks in --loop mode (3600 = 1 hour)


# --- Setup -----------------------------------------------------------------
load_dotenv()
API_KEY = os.environ.get("ALPACA_API_KEY")
SECRET_KEY = os.environ.get("ALPACA_SECRET_KEY")

if not API_KEY or not SECRET_KEY:
    raise SystemExit(
        "Clés Alpaca manquantes. Ajoute ALPACA_API_KEY et ALPACA_SECRET_KEY "
        "dans ton fichier .env."
    )

client = TradingClient(API_KEY, SECRET_KEY, paper=True)


# --- Strategy helpers ------------------------------------------------------
def signal(symbol: str):
    """True = buy signal (short MA > long MA), False = flat, None = no data."""
    df = yf.Ticker(symbol).history(period="1y")
    if df.empty or len(df) < LONG_WINDOW + 2:
        return None
    short = df["Close"].rolling(SHORT_WINDOW).mean().iloc[-1]
    long = df["Close"].rolling(LONG_WINDOW).mean().iloc[-1]
    return bool(short > long)


def held_qty(symbol: str) -> float:
    """How many shares of `symbol` we currently hold (0 if none)."""
    try:
        return float(client.get_open_position(symbol).qty)
    except Exception:
        return 0.0


def order(symbol: str, qty: float, side: OrderSide):
    client.submit_order(MarketOrderRequest(
        symbol=symbol, qty=qty, side=side, time_in_force=TimeInForce.DAY,
    ))


# --- One pass over the whole watchlist -------------------------------------
def run_once():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    account = client.get_account()
    try:
        is_open = client.get_clock().is_open
    except Exception:
        is_open = None
    market = "ouvert" if is_open else "fermé (les ordres seront exécutés à l'ouverture)"
    print(f"\n=== Bot — {now} | portefeuille {float(account.portfolio_value):,.0f} $ | marché {market} ===")

    for symbol in WATCHLIST:
        sig = signal(symbol)
        if sig is None:
            print(f"  {symbol:6} : pas assez de données, ignoré")
            continue

        pos = held_qty(symbol)
        try:
            if sig and pos <= 0:                       # buy signal, not invested
                order(symbol, QTY, OrderSide.BUY)
                print(f"  {symbol:6} : signal ACHAT  -> achat de {QTY}")
            elif not sig and pos > 0:                  # flat signal, holding -> close
                order(symbol, pos, OrderSide.SELL)
                print(f"  {symbol:6} : signal SORTIE -> vente de {pos:g}")
            else:
                state = "achat" if sig else "hors marché"
                print(f"  {symbol:6} : rien à faire (signal {state}, position {pos:g})")
        except Exception as e:
            print(f"  {symbol:6} : ERREUR ordre -> {e}")


# --- Entry point -----------------------------------------------------------
if __name__ == "__main__":
    if "--loop" in sys.argv:
        print("Mode boucle : Ctrl+C pour arrêter.")
        while True:
            run_once()
            time.sleep(LOOP_EVERY)
    else:
        run_once()
