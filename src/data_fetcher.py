import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import os

def fetch_daily(ticker, period_years=3, data_dir="data"):
    end = datetime.utcnow().date()
    start = end - timedelta(days=period_years * 365)

    df = yf.download(
        ticker,
        start=start.isoformat(),
        end=end.isoformat(),
        progress=False
    )

    if df.empty:
        raise ValueError(f"No data returned for {ticker}")

    # --- FIX: Flatten MultiIndex columns if present ---
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]

    # --- FIX: Ensure Adj Close exists (fallback to Close) ---
    if "Adj Close" not in df.columns:
        df["Adj Close"] = df["Close"]

    df = df[['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']].copy()
    df.index = pd.to_datetime(df.index)

    # Save raw CSV
    os.makedirs(data_dir, exist_ok=True)
    df.to_csv(os.path.join(data_dir, f"{ticker}.csv"))

    return df

def compute_mas(df):
    """
    Compute moving averages (MA20 and MA50) and return cleaned dataframe.
    """
    df = df.copy()
    df['MA20'] = df['Close'].rolling(20).mean()
    df['MA50'] = df['Close'].rolling(50).mean()
    return df.dropna()