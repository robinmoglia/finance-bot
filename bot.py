"""
bot.py — The automatic trading bot (paper, Alpaca).

Standalone script (no Streamlit). Each run does ONE pass over the watchlist:
computes the MA/RSI signal, compares to your Alpaca position, buys/sells, and
logs the decision with the numbers behind it.

Two AI touches (Gemini, English), both optional:
  - On a real trade, a one-sentence explanation is logged.
  - If instructions.txt contains guidelines, each trade is checked against them
    first; a trade that goes against your instructions is skipped.
    (Empty instructions.txt -> no filter, the bot just follows its strategy.)

Run one pass:  python bot.py
Run in a loop: python bot.py --loop

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
#  CONFIG
# ===========================================================================
WATCHLIST = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "TSLA"]
SHORT_WINDOW = 20
LONG_WINDOW = 50
QTY = 5
LOOP_EVERY = 3600
MODEL = "gemini-flash-lite-latest"


# --- Setup -----------------------------------------------------------------
load_dotenv()
API_KEY = os.environ.get("ALPACA_API_KEY")
SECRET_KEY = os.environ.get("ALPACA_SECRET_KEY")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

if not API_KEY or not SECRET_KEY:
    raise SystemExit(
        "Clés Alpaca manquantes. Ajoute ALPACA_API_KEY et ALPACA_SECRET_KEY dans .env."
    )

client = TradingClient(API_KEY, SECRET_KEY, paper=True)

_llm = None
if GEMINI_KEY:
    try:
        from google import genai
        _llm = genai.Client(api_key=GEMINI_KEY)
    except Exception:
        _llm = None


# --- User instructions (read from instructions.txt) ------------------------
def read_instructions() -> str:
    """Return the user's guidelines (English), ignoring comments/blank lines.
    Empty string means: no filter, follow the strategy."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instructions.txt")
    try:
        with open(path, encoding="utf-8") as f:
            lines = [ln.strip() for ln in f
                     if ln.strip() and not ln.strip().startswith("#")]
        return "\n".join(lines)
    except FileNotFoundError:
        return ""


# --- Strategy: signal + the numbers behind it ------------------------------
def analyze(symbol: str):
    df = yf.Ticker(symbol).history(period="1y")
    if df.empty or len(df) < LONG_WINDOW + 2:
        return None
    close = df["Close"]
    ma_s = close.rolling(SHORT_WINDOW).mean().iloc[-1]
    ma_l = close.rolling(LONG_WINDOW).mean().iloc[-1]
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    rs = gain.rolling(14).mean() / loss.rolling(14).mean()
    rsi = (100 - 100 / (1 + rs)).iloc[-1]
    return {"buy": bool(ma_s > ma_l), "ma_s": ma_s, "ma_l": ma_l, "rsi": rsi}


def explain(action: str, symbol: str, info: dict) -> str | None:
    """One-sentence English explanation of a real trade (via Gemini)."""
    if _llm is None:
        return None
    prompt = (
        "In ONE short sentence, in English, explain this automated paper-trading "
        "action for a student project. Be concise and educational, and do not give "
        f"investment advice. Action: {action} {symbol}. Strategy: MA{SHORT_WINDOW}/"
        f"MA{LONG_WINDOW} crossover. Values: MA{SHORT_WINDOW}={info['ma_s']:.2f}, "
        f"MA{LONG_WINDOW}={info['ma_l']:.2f}, RSI(14)={info['rsi']:.0f}."
    )
    try:
        r = _llm.models.generate_content(model=MODEL, contents=prompt)
        return (r.text or "").strip()
    except Exception:
        return None


def approves(action: str, symbol: str, info: dict, instructions: str):
    """Check a trade against the user's instructions. Returns (ok, reason).
    If there are no instructions (or no AI), always returns (True, "")."""
    if _llm is None or not instructions:
        return True, ""
    prompt = (
        "You are a risk filter for an automated paper-trading bot (student project, "
        "not investment advice). Decide whether the proposed action RESPECTS the "
        "user's instructions. Reply with 'YES' or 'NO' on the first line, then one "
        "short sentence of reason (English).\n\n"
        f"User instructions:\n{instructions}\n\n"
        f"Proposed action: {action} {symbol}. "
        f"MA{SHORT_WINDOW}={info['ma_s']:.2f}, MA{LONG_WINDOW}={info['ma_l']:.2f}, "
        f"RSI(14)={info['rsi']:.0f}."
    )
    try:
        r = _llm.models.generate_content(model=MODEL, contents=prompt)
        txt = (r.text or "").strip()
        ok = txt.upper().startswith("YES")
        reason = txt.split("\n", 1)[1].strip() if "\n" in txt else txt
        return ok, reason
    except Exception:
        return True, ""   # if the check fails, don't block the strategy


def held_qty(symbol: str) -> float:
    try:
        return float(client.get_open_position(symbol).qty)
    except Exception:
        return 0.0


def order(symbol: str, qty: float, side: OrderSide):
    client.submit_order(MarketOrderRequest(
        symbol=symbol, qty=qty, side=side, time_in_force=TimeInForce.DAY,
    ))


# --- One pass over the watchlist -------------------------------------------
def run_once():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    instructions = read_instructions()
    account = client.get_account()
    try:
        is_open = client.get_clock().is_open
    except Exception:
        is_open = None
    market = "ouvert" if is_open else "fermé (ordres exécutés à l'ouverture)"
    note = " | consignes actives" if instructions else ""
    print(f"\n=== Bot — {now} | portefeuille {float(account.portfolio_value):,.0f} $ | marché {market}{note} ===")

    for symbol in WATCHLIST:
        info = analyze(symbol)
        if info is None:
            print(f"  {symbol:6} : pas assez de données, ignoré")
            continue

        pos = held_qty(symbol)
        sign = ">" if info["buy"] else "<"
        nums = (f"(MA{SHORT_WINDOW}={info['ma_s']:.2f} {sign} MA{LONG_WINDOW}="
                f"{info['ma_l']:.2f}, RSI {info['rsi']:.0f})")

        try:
            if info["buy"] and pos <= 0:                      # buy signal, not invested
                ok, reason = approves("BUY", symbol, info, instructions)
                if not ok:
                    print(f"  {symbol:6} : ACHAT  {nums} -> ignoré (consignes)")
                    if reason:
                        print(f"           🚫 {reason}")
                    continue
                order(symbol, QTY, OrderSide.BUY)
                print(f"  {symbol:6} : ACHAT  {nums} -> achat de {QTY}")
                why = explain("BUY", symbol, info)
                if why:
                    print(f"           💡 {why}")

            elif not info["buy"] and pos > 0:                 # flat signal, holding -> close
                ok, reason = approves("SELL", symbol, info, instructions)
                if not ok:
                    print(f"  {symbol:6} : SORTIE {nums} -> ignoré (consignes)")
                    if reason:
                        print(f"           🚫 {reason}")
                    continue
                order(symbol, pos, OrderSide.SELL)
                print(f"  {symbol:6} : SORTIE {nums} -> vente de {pos:g}")
                why = explain("SELL", symbol, info)
                if why:
                    print(f"           💡 {why}")

            else:
                state = "achat" if info["buy"] else "hors marché"
                print(f"  {symbol:6} : rien à faire {nums} (signal {state}, position {pos:g})")
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
