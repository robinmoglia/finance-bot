"""
bot.py — The automatic trading bot (paper, Alpaca).

Universe: the S&P 500 (fetched automatically). On each run the bot:
  - downloads all prices in ONE batch call,
  - reads your Alpaca positions in ONE call,
  - computes the MA/RSI signal per stock,
  - SELLS names it holds that turned "flat",
  - BUYS the strongest "buy" names until it holds at most MAX_POSITIONS,
  - checks each trade against instructions.txt (if any) and logs an English
    explanation for real trades.

Run one pass:  python bot.py
Run in a loop: python bot.py --loop

⚠️ Paper money only. Educational project — not investment advice.
"""

import os
import sys
import time
from datetime import datetime

from dotenv import load_dotenv
import pandas as pd
import yfinance as yf
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce


# ===========================================================================
#  CONFIG
# ===========================================================================
SHORT_WINDOW = 20
LONG_WINDOW = 50
QTY = 5                 # shares per new position
MAX_POSITIONS = 15      # never hold more than this many names at once
LOOP_EVERY = 3600
MODEL = "gemini-flash-lite-latest"

SP500_CSV = ("https://raw.githubusercontent.com/datasets/"
             "s-and-p-500-companies/main/data/constituents.csv")
FALLBACK_UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "BRK-B", "JPM", "V",
    "UNH", "XOM", "JNJ", "WMT", "MA", "PG", "HD", "COST", "ORCL", "KO",
]


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


# --- Universe (S&P 500) ----------------------------------------------------
def load_universe() -> list[str]:
    """Return the S&P 500 tickers (Yahoo format, e.g. BRK-B). Falls back to a
    short list if the online source is unreachable."""
    try:
        df = pd.read_csv(SP500_CSV)
        col = "Symbol" if "Symbol" in df.columns else df.columns[0]
        syms = [str(s).strip().replace(".", "-") for s in df[col] if str(s).strip()]
        if len(syms) > 50:
            return syms
    except Exception:
        pass
    return FALLBACK_UNIVERSE


# --- User instructions (instructions.txt) ----------------------------------
def read_instructions() -> str:
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instructions.txt")
    try:
        with open(path, encoding="utf-8") as f:
            lines = [ln.strip() for ln in f
                     if ln.strip() and not ln.strip().startswith("#")]
        return "\n".join(lines)
    except FileNotFoundError:
        return ""


# --- Indicators from the batch-downloaded data -----------------------------
def analyze_ticker(data: pd.DataFrame, sym: str):
    try:
        close = data[sym]["Close"].dropna()
    except Exception:
        return None
    if len(close) < LONG_WINDOW + 2:
        return None
    ma_s = close.rolling(SHORT_WINDOW).mean().iloc[-1]
    ma_l = close.rolling(LONG_WINDOW).mean().iloc[-1]
    if pd.isna(ma_s) or pd.isna(ma_l):
        return None
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    rs = gain.rolling(14).mean() / loss.rolling(14).mean()
    rsi = (100 - 100 / (1 + rs)).iloc[-1]
    return {
        "buy": bool(ma_s > ma_l),
        "ma_s": float(ma_s),
        "ma_l": float(ma_l),
        "rsi": float(rsi) if pd.notna(rsi) else 50.0,
    }


# --- AI helpers (optional) -------------------------------------------------
def explain(action: str, symbol: str, info: dict):
    if _llm is None:
        return None
    prompt = (
        "In ONE short sentence, in English, explain this automated paper-trading "
        "action for a student project. Be concise and educational, no investment "
        f"advice. Action: {action} {symbol}. Strategy: MA{SHORT_WINDOW}/MA{LONG_WINDOW} "
        f"crossover. Values: MA{SHORT_WINDOW}={info['ma_s']:.2f}, "
        f"MA{LONG_WINDOW}={info['ma_l']:.2f}, RSI(14)={info['rsi']:.0f}."
    )
    try:
        return (_llm.models.generate_content(model=MODEL, contents=prompt).text or "").strip()
    except Exception:
        return None


def approves(action: str, symbol: str, info: dict, instructions: str):
    if _llm is None or not instructions:
        return True, ""
    prompt = (
        "You are a risk filter for an automated paper-trading bot (student project, "
        "not investment advice). Decide whether the proposed action RESPECTS the "
        "user's instructions. Reply 'YES' or 'NO' on the first line, then one short "
        f"reason (English).\n\nUser instructions:\n{instructions}\n\n"
        f"Proposed action: {action} {symbol}. MA{SHORT_WINDOW}={info['ma_s']:.2f}, "
        f"MA{LONG_WINDOW}={info['ma_l']:.2f}, RSI(14)={info['rsi']:.0f}."
    )
    try:
        txt = (_llm.models.generate_content(model=MODEL, contents=prompt).text or "").strip()
        ok = txt.upper().startswith("YES")
        reason = txt.split("\n", 1)[1].strip() if "\n" in txt else txt
        return ok, reason
    except Exception:
        return True, ""


def _alpaca_sym(sym: str) -> str:
    return sym.replace("-", ".")


def order(sym: str, qty: float, side: OrderSide):
    client.submit_order(MarketOrderRequest(
        symbol=_alpaca_sym(sym), qty=qty, side=side, time_in_force=TimeInForce.DAY,
    ))


# --- One pass over the S&P 500 ---------------------------------------------
def run_once():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    instructions = read_instructions()
    universe = load_universe()
    account = client.get_account()

    # positions as {yahoo_symbol: qty}
    pos_map = {p.symbol.replace(".", "-"): float(p.qty) for p in client.get_all_positions()}
    held = sum(1 for q in pos_map.values() if q > 0)

    try:
        is_open = client.get_clock().is_open
    except Exception:
        is_open = None
    market = "ouvert" if is_open else "fermé (ordres à l'ouverture)"
    note = " | consignes actives" if instructions else ""
    print(f"\n=== Bot — {now} | portefeuille {float(account.portfolio_value):,.0f} $ | "
          f"{len(universe)} actions | positions {held}/{MAX_POSITIONS} | marché {market}{note} ===")

    # One batched price download for the whole universe.
    data = yf.download(universe, period="6mo", group_by="ticker",
                       threads=True, progress=False)
    if data is None or data.empty:
        print("  Impossible de télécharger les prix, réessai à la prochaine passe.")
        return

    buys, sells, skipped = 0, 0, 0
    buy_candidates = []

    # First pass: handle sells now, collect buy candidates.
    for sym in universe:
        info = analyze_ticker(data, sym)
        if info is None:
            continue
        pos = pos_map.get(sym, 0.0)
        nums = (f"(MA{SHORT_WINDOW}={info['ma_s']:.2f} "
                f"{'>' if info['buy'] else '<'} MA{LONG_WINDOW}={info['ma_l']:.2f}, "
                f"RSI {info['rsi']:.0f})")

        if not info["buy"] and pos > 0:                       # exit signal -> sell
            ok, reason = approves("SELL", sym, info, instructions)
            if not ok:
                print(f"  {sym:6} : SORTIE {nums} -> ignoré (consignes)")
                if reason:
                    print(f"           🚫 {reason}")
                skipped += 1
                continue
            try:
                order(sym, pos, OrderSide.SELL)
                sells += 1
                held -= 1
                print(f"  {sym:6} : SORTIE {nums} -> vente de {pos:g}")
                why = explain("SELL", sym, info)
                if why:
                    print(f"           💡 {why}")
            except Exception as e:
                print(f"  {sym:6} : ERREUR vente -> {e}")

        elif info["buy"] and pos <= 0:                        # buy signal, not held yet
            strength = info["ma_s"] / info["ma_l"] - 1        # how far short MA is above long MA
            buy_candidates.append((strength, sym, info, nums))

    # Second pass: buy the STRONGEST candidates until we reach the cap.
    buy_candidates.sort(reverse=True)
    for strength, sym, info, nums in buy_candidates:
        if held >= MAX_POSITIONS:
            break
        ok, reason = approves("BUY", sym, info, instructions)
        if not ok:
            print(f"  {sym:6} : ACHAT  {nums} -> ignoré (consignes)")
            if reason:
                print(f"           🚫 {reason}")
            skipped += 1
            continue
        try:
            order(sym, QTY, OrderSide.BUY)
            buys += 1
            held += 1
            print(f"  {sym:6} : ACHAT  {nums} -> achat de {QTY}")
            why = explain("BUY", sym, info)
            if why:
                print(f"           💡 {why}")
        except Exception as e:
            print(f"  {sym:6} : ERREUR achat -> {e}")

    print(f"  → Résumé : {buys} achats, {sells} ventes, {skipped} ignorés | "
          f"positions détenues : {held}/{MAX_POSITIONS}")


# --- Entry point -----------------------------------------------------------
if __name__ == "__main__":
    if "--loop" in sys.argv:
        print("Mode boucle : Ctrl+C pour arrêter.")
        while True:
            run_once()
            time.sleep(LOOP_EVERY)
    else:
        run_once()
