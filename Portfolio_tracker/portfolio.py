
import argparse
import csv
import re
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_PRICES_FILE = "sample_prices.csv"
DEFAULT_OUTPUT_FILE = "portfolio_summary.csv"
DEFAULT_UNIVERSE_FILE = "constituents.csv"  # S&P 500 list (Symbol, Security columns)
TICKER_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{0,9}$")

CSV_FIELDS = [
    "run_timestamp", "ticker", "shares", "avg_buy_price", "current_price",
    "invested", "market_value", "gain_loss", "gain_loss_pct",
]


# --------------------------------------------------------------------------
# Portfolio data structure
# --------------------------------------------------------------------------
# portfolio = { "AAPL": {"shares": 10.0, "cost": 1500.0}, ... }
# "cost" is total money spent, so the average buy price is cost / shares.
# Buying the same ticker twice merges into one position (weighted average).

def add_position(portfolio, ticker, buy_price, shares):
    """Add a purchase to the portfolio, merging with any existing position."""
    pos = portfolio.setdefault(ticker, {"shares": 0.0, "cost": 0.0})
    pos["shares"] += shares
    pos["cost"] += buy_price * shares


def validate_entry(ticker, buy_price, shares):
    """Return (clean_ticker, price, shares) or raise ValueError."""
    ticker = ticker.strip().upper()
    if not TICKER_PATTERN.match(ticker):
        raise ValueError(f"invalid ticker '{ticker}'")
    try:
        buy_price, shares = float(buy_price), float(shares)
    except ValueError:
        raise ValueError("buy price and shares must be numbers") from None
    if buy_price <= 0:
        raise ValueError("buy price must be greater than 0")
    if shares <= 0:
        raise ValueError("shares must be greater than 0")
    return ticker, buy_price, shares


# --------------------------------------------------------------------------
# Input
# --------------------------------------------------------------------------

def parse_add_arg(text):
    """Parse 'TICKER:PRICE:SHARES' from the command line."""
    parts = text.split(":")
    if len(parts) != 3:
        raise ValueError(f"'{text}' is not in TICKER:PRICE:SHARES format")
    return validate_entry(*parts)


def prompt_for_positions(portfolio):
    """Interactive entry loop. Blank ticker (or 'done') finishes."""
    print("Enter your holdings. Leave the ticker blank when finished.\n")
    while True:
        ticker = input("Ticker symbol: ").strip()
        if ticker == "" or ticker.lower() == "done":
            break
        try:
            price = input("  Buy price per share: ").strip()
            shares = input("  Number of shares:    ").strip()
            add_position(portfolio, *validate_entry(ticker, price, shares))
            print(f"  Added {ticker.upper()}.\n")
        except ValueError as err:
            print(f"  Skipped: {err}\n")


# --------------------------------------------------------------------------
# Price lookup
# --------------------------------------------------------------------------

def load_prices_csv(path):
    """Load {ticker: price} from a CSV with 'Ticker' and 'Price' columns."""
    prices = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        # Case-insensitive column matching.
        cols = {name.strip().lower(): name for name in (reader.fieldnames or [])}
        if "ticker" not in cols or "price" not in cols:
            raise ValueError(f"{path} needs 'Ticker' and 'Price' columns")
        for row in reader:
            try:
                prices[row[cols["ticker"]].strip().upper()] = float(row[cols["price"]])
            except (ValueError, AttributeError):
                continue  # skip malformed rows rather than crash
    return prices


def load_constituents(path):
    """Load {symbol: company name} from the S&P 500 constituents CSV.
    Returns {} if the file is missing, so the dataset stays optional."""
    p = Path(path)
    if not p.exists():
        return {}
    with open(p, newline="", encoding="utf-8-sig") as f:
        return {row["Symbol"].strip().upper(): row.get("Security", "").strip()
                for row in csv.DictReader(f) if row.get("Symbol")}


def fetch_live_prices(tickers):
    """Fetch latest prices with yfinance. Returns {ticker: price} for those found."""
    try:
        import yfinance as yf
    except ImportError:
        sys.exit("yfinance is not installed. Run: pip install yfinance")

    prices = {}
    for t in tickers:
        try:
            hist = yf.Ticker(t.replace(".", "-")).history(period="5d")
            if not hist.empty:
                prices[t] = float(hist["Close"].iloc[-1])
        except Exception as err:  # network errors, delisted symbols, etc.
            print(f"  Warning: could not fetch {t}: {err}")
    return prices


# --------------------------------------------------------------------------
# Calculations
# --------------------------------------------------------------------------

def analyse(portfolio, prices):
    """Return (rows, totals, missing). Unpriced tickers are excluded from totals."""
    rows, missing = [], []
    total_invested = total_value = 0.0

    for ticker in sorted(portfolio):
        pos = portfolio[ticker]
        if ticker not in prices:
            missing.append(ticker)
            continue
        invested = pos["cost"]
        value = pos["shares"] * prices[ticker]
        gain = value - invested
        rows.append({
            "ticker": ticker,
            "shares": pos["shares"],
            "avg_buy_price": invested / pos["shares"],
            "current_price": prices[ticker],
            "invested": invested,
            "market_value": value,
            "gain_loss": gain,
            "gain_loss_pct": gain / invested * 100,  # invested > 0 is guaranteed by validation
        })
        total_invested += invested
        total_value += value

    gain = total_value - total_invested
    totals = {
        "invested": total_invested,
        "market_value": total_value,
        "gain_loss": gain,
        "gain_loss_pct": (gain / total_invested * 100) if total_invested else 0.0,
    }
    return rows, totals, missing


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------

def print_report(rows, totals, missing, names=None):
    names = names or {}
    header = (f"{'Ticker':<8}{'Company':<24}{'Shares':>10}{'Avg Buy':>12}{'Current':>12}"
              f"{'Invested':>15}{'Value':>15}{'Gain/Loss':>15}{'%':>10}")
    line = "-" * len(header)
    print("\n" + line)
    print(header)
    print(line)
    for r in rows:
        print(f"{r['ticker']:<8}{names.get(r['ticker'], '')[:22]:<24}{r['shares']:>10,.4g}{r['avg_buy_price']:>12,.2f}"
              f"{r['current_price']:>12,.2f}{r['invested']:>15,.2f}"
              f"{r['market_value']:>15,.2f}{r['gain_loss']:>+15,.2f}"
              f"{r['gain_loss_pct']:>+9.2f}%")
    print(line)
    print(f"{'TOTAL':<8}{'':<24}{'':>10}{'':>12}{'':>12}{totals['invested']:>15,.2f}"
          f"{totals['market_value']:>15,.2f}{totals['gain_loss']:>+15,.2f}"
          f"{totals['gain_loss_pct']:>+9.2f}%")
    print(line)
    if missing:
        print(f"\nWARNING: no price found for {', '.join(missing)}. "
              "These are excluded from the totals above.")


def log_summary(path, rows, totals):
    """Append this run to the CSV log (header written only if the file is new)."""
    path = Path(path)
    is_new = not path.exists() or path.stat().st_size == 0
    stamp = datetime.now().isoformat(timespec="seconds")

    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if is_new:
            writer.writeheader()
        for r in rows:
            writer.writerow({"run_timestamp": stamp, **_rounded(r)})
        writer.writerow({
            "run_timestamp": stamp, "ticker": "TOTAL",
            **{k: round(v, 2) for k, v in totals.items()},
        })


def _rounded(row):
    return {k: (round(v, 4) if k == "shares" else round(v, 2) if isinstance(v, float) else v)
            for k, v in row.items()}


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Simple investment portfolio tracker.")
    ap.add_argument("--add", action="append", default=[], metavar="TICKER:PRICE:SHARES",
                    help="add a position non-interactively (repeatable)")
    ap.add_argument("--prices", default=DEFAULT_PRICES_FILE,
                    help=f"prices CSV (default: {DEFAULT_PRICES_FILE})")
    ap.add_argument("--live", action="store_true", help="fetch live prices via yfinance")
    ap.add_argument("--output", default=DEFAULT_OUTPUT_FILE,
                    help=f"summary CSV to append to (default: {DEFAULT_OUTPUT_FILE})")
    ap.add_argument("--universe", default=DEFAULT_UNIVERSE_FILE,
                    help=f"S&P 500 constituents CSV, used for company names and "
                         f"a non-S&P warning (default: {DEFAULT_UNIVERSE_FILE}, optional)")
    args = ap.parse_args()

    portfolio = {}
    try:
        for item in args.add:
            add_position(portfolio, *parse_add_arg(item))
    except ValueError as err:
        sys.exit(f"Error: {err}")

    if not args.add:
        try:
            prompt_for_positions(portfolio)
        except (EOFError, KeyboardInterrupt):
            print()
    if not portfolio:
        sys.exit("No positions entered. Nothing to do.")

    if args.live:
        print("Fetching live prices...")
        prices = fetch_live_prices(list(portfolio))
    else:
        try:
            prices = load_prices_csv(args.prices)
        except (OSError, ValueError) as err:
            sys.exit(f"Error loading prices: {err}")

    names = load_constituents(args.universe)
    rows, totals, missing = analyse(portfolio, prices)
    print_report(rows, totals, missing, names)
    if names:
        outside = [t for t in portfolio if t not in names]
        if outside:
            print(f"\nNote: {', '.join(outside)} not in the S&P 500 list "
                  f"(fine if intentional; check for typos).")

    if rows:
        log_summary(args.output, rows, totals)
        print(f"\nSummary appended to {args.output}")
    else:
        print("\nNo priced holdings; nothing logged.")


if __name__ == "__main__":
    main()