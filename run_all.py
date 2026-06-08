import matplotlib
matplotlib.use("Agg")  # Force non-GUI backend globally before any pyplot import

import os
import time
import logging
import yaml
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from src.data_fetcher import fetch_daily, compute_mas
from src.daist_engine import DAISTradingEngine
from src.metrics import compute_true_beta, performance_metrics_from_ledger
from src.charts import make_all_charts
from src.report_generator import build_pdf_report
from src.pptx_builder import build_presentation
from src.dashboard_export import build_dashboard_html
from src.docx_guide import build_docx_guide


# ------------------------------------------------------------
# LOGGING SETUP
# ------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("DAIS")


# ------------------------------------------------------------
# LOAD CONFIG
# ------------------------------------------------------------
def load_config(config_path: str = "config.yaml"):
    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)
    return cfg


# ------------------------------------------------------------
# SINGLE-TICKER PIPELINE (exception-safe)
# ------------------------------------------------------------
def run_for_ticker(ticker: str, cfg: dict, benchmark_close: pd.Series, outdir: str):
    start = time.time()
    logger.info(f"Starting pipeline for {ticker}")

    try:
        data_dir = cfg.get("data_dir", "data")
        df_path = os.path.join(data_dir, f"{ticker}.csv")
        df = pd.read_csv(df_path, parse_dates=["Date"]).set_index("Date").sort_index()

        # Compute moving averages if not present
        df = compute_mas(df)

        # True beta
        beta_true = compute_true_beta(df["Close"], benchmark_close)
        if pd.isna(beta_true):
            beta_use = cfg["beta_default"]
        else:
            beta_use = beta_true

        # Engine
        engine = DAISTradingEngine(
            beta=beta_use,
            initial_capital=cfg["initial_capital"],
            core_buy_amt=cfg["core_buy_amt"],
            base_buy=cfg["base_buy"],
            base_sell=cfg["base_sell"],
            inventory_floor=cfg["inventory_floor"],
        )

        ledger = engine.run_backtest(df)

        ticker_outdir = os.path.join(outdir, ticker)
        os.makedirs(ticker_outdir, exist_ok=True)

        # Save ledger
        ledger_csv = os.path.join(ticker_outdir, f"{ticker}_ledger.csv")
        ledger.to_csv(ledger_csv, index=False)

        # Metrics
        metrics = performance_metrics_from_ledger(ledger, df["Close"])
        metrics_csv = os.path.join(ticker_outdir, f"{ticker}_metrics.csv")
        pd.DataFrame([metrics]).to_csv(metrics_csv, index=False)

        # Charts
        charts = make_all_charts(ticker, df, ledger, ticker_outdir)

        # Collect engine stats for reporting
        result = {
            "ticker": ticker,
            "metrics": metrics,
            "beta_true": beta_true,
            "sell_rule_stats": getattr(engine, "sell_rule_stats", {}),
            "trade_stats": getattr(engine, "trade_stats", {}),
            "ledger_csv": ledger_csv,
            "charts": charts,
        }

        elapsed = time.time() - start
        logger.info(f"Completed pipeline for {ticker} in {elapsed:.2f}s")

        return result

    except Exception as e:
        logger.error(f"Error processing {ticker}: {e}", exc_info=True)
        return {
            "ticker": ticker,
            "metrics": {},
            "beta_true": float("nan"),
            "sell_rule_stats": {},
            "trade_stats": {},
            "ledger_csv": "",
            "charts": {},
            "error": str(e),
        }


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------
def main():
    cfg = load_config()
    outdir = cfg.get("outdir", "output")
    os.makedirs(outdir, exist_ok=True)

    tickers = cfg.get("tickers", [])
    benchmark = cfg.get("benchmark", "SPY")

    logger.info(f"Fetching benchmark data: {benchmark}")
    benchmark_df = fetch_daily(
        benchmark,
        cfg["period_years"],
        data_dir=cfg.get("data_dir", "data")
    )

    # PATCH APPLIED HERE
    benchmark_df = benchmark_df.sort_index()

    benchmark_close = benchmark_df["Close"]

    summary = []

    # Parallel processing with progress bar
    logger.info("Starting parallel ticker processing...")
    with ThreadPoolExecutor(max_workers=cfg.get("max_workers", 4)) as executor:
        futures = {
            executor.submit(run_for_ticker, ticker, cfg, benchmark_close, outdir): ticker
            for ticker in tickers
        }

        for future in tqdm(as_completed(futures), total=len(futures), desc="Tickers"):
            ticker = futures[future]
            result = future.result()
            summary.append(result)

    logger.info("All tickers processed. Building reports...")

    # Reporting modules (exception-safe)
    try:
        pdf_path = build_pdf_report(summary, cfg, outdir)
        logger.info(f"PDF report built: {pdf_path}")
    except Exception as e:
        logger.error(f"Error building PDF report: {e}", exc_info=True)

    try:
        pptx_path = build_presentation(summary, cfg, outdir)
        logger.info(f"PPTX deck built: {pptx_path}")
    except Exception as e:
        logger.error(f"Error building PPTX deck: {e}", exc_info=True)

    try:
        dashboard_path = build_dashboard_html(summary, cfg, outdir)
        logger.info(f"Dashboard HTML built: {dashboard_path}")
    except Exception as e:
        logger.error(f"Error building dashboard HTML: {e}", exc_info=True)

    try:
        docx_path = build_docx_guide(cfg, outdir)
        logger.info(f"DOCX guide built: {docx_path}")
    except Exception as e:
        logger.error(f"Error building DOCX guide: {e}", exc_info=True)

    logger.info("DAIS pipeline complete.")


if __name__ == "__main__":
    main()
