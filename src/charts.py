import os
import matplotlib
matplotlib.use("Agg")  # Force non-GUI backend for headless runs

import matplotlib.pyplot as plt
import pandas as pd


# ------------------------------------------------------------
# INTERNAL: Detect buys and sells from inventory changes
# ------------------------------------------------------------
def detect_trades(ledger: pd.DataFrame):
    ledger = ledger.sort_values("Date").copy()
    ledger["Inv_Change"] = ledger["Inventory"].diff()

    buys = ledger[ledger["Inv_Change"] > 0]
    sells = ledger[ledger["Inv_Change"] < 0]

    return buys, sells


# ------------------------------------------------------------
# PRICE + MA20 + MA50 + BUY/SELL MARKERS
# ------------------------------------------------------------
def plot_price_with_mas(df: pd.DataFrame, ledger: pd.DataFrame, ticker: str, outdir: str):
    # Ensure MAs exist
    if "MA20" not in df.columns:
        df["MA20"] = df["Close"].rolling(20).mean()
    if "MA50" not in df.columns:
        df["MA50"] = df["Close"].rolling(50).mean()

    df = df.dropna()

    buys, sells = detect_trades(ledger)

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(df.index, df["Close"], label="Close", color="black")
    ax.plot(df.index, df["MA20"], label="MA20", color="blue")
    ax.plot(df.index, df["MA50"], label="MA50", color="orange")

    # Plot buys
    if not buys.empty:
        ax.scatter(
            buys["Date"],
            buys["Price"],
            marker="^",
            color="green",
            s=80,
            label="Buy",
        )

    # Plot sells
    if not sells.empty:
        ax.scatter(
            sells["Date"],
            sells["Price"],
            marker="v",
            color="red",
            s=80,
            label="Sell",
        )

    ax.set_title(f"{ticker} — Price with MA20/MA50 and Trades")
    ax.set_xlabel("Date")
    ax.set_ylabel("Price")
    ax.legend()

    os.makedirs(outdir, exist_ok=True)
    outpath = os.path.join(outdir, f"{ticker}_price_ma_trades.png")
    fig.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close(fig)

    return outpath


# ------------------------------------------------------------
# EQUITY CURVE (Total Value Over Time)
# ------------------------------------------------------------
def plot_equity_curve(ledger: pd.DataFrame, ticker: str, outdir: str):
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(ledger["Date"], ledger["Total_Value"], color="purple", label="Total Value")

    ax.set_title(f"{ticker} — Equity Curve")
    ax.set_xlabel("Date")
    ax.set_ylabel("Portfolio Value")
    ax.legend()

    os.makedirs(outdir, exist_ok=True)
    outpath = os.path.join(outdir, f"{ticker}_equity_curve.png")
    fig.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close(fig)

    return outpath


# ------------------------------------------------------------
# INVENTORY OVER TIME
# ------------------------------------------------------------
def plot_inventory(ledger: pd.DataFrame, ticker: str, outdir: str):
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(ledger["Date"], ledger["Inventory"], color="brown", label="Inventory")

    ax.set_title(f"{ticker} — Inventory Over Time")
    ax.set_xlabel("Date")
    ax.set_ylabel("Shares Held")
    ax.legend()

    os.makedirs(outdir, exist_ok=True)
    outpath = os.path.join(outdir, f"{ticker}_inventory.png")
    fig.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close(fig)

    return outpath


# ------------------------------------------------------------
# MASTER FUNCTION: Generate All Charts
# ------------------------------------------------------------
def make_all_charts(ticker: str, df: pd.DataFrame, ledger: pd.DataFrame, outdir: str):
    os.makedirs(outdir, exist_ok=True)

    charts = {}
    charts["price_ma_trades"] = plot_price_with_mas(df, ledger, ticker, outdir)
    charts["equity_curve"] = plot_equity_curve(ledger, ticker, outdir)
    charts["inventory"] = plot_inventory(ledger, ticker, outdir)

    return charts
