import os
import pandas as pd


def build_dashboard_html(summary, cfg, outdir):
    html_path = os.path.join(outdir, "DAIS_Dashboard.html")

    rows = []
    for s in summary:
        m = s["metrics"]
        sell = s.get("sell_rule_stats", {})
        trade = s.get("trade_stats", {})
        rows.append({
            "ticker": s["ticker"],
            "total_return": m.get("total_return", 0),
            "annualized_return": m.get("annualized_return", 0),
            "annualized_vol": m.get("annualized_vol", 0),
            "sharpe": m.get("sharpe", 0),
            "max_drawdown": m.get("max_drawdown", 0),
            "beta_true": s["beta_true"],
            "sell_attempts": sell.get("total_sell_attempts", 0),
            "blocked_ma20": sell.get("blocked_by_ma20", 0),
            "blocked_avg_cost": sell.get("blocked_by_avg_cost", 0),
            "buys": trade.get("buys", 0),
            "sells": trade.get("sells", 0),
        })

    df = pd.DataFrame(rows)

    html = """
    <html>
    <head>
        <title>DAIS Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ccc; padding: 8px; text-align: right; }
            th { background-color: #f2f2f2; }
            td.ticker { text-align: left; }
        </style>
    </head>
    <body>
        <h1>DAIS Dashboard</h1>
        <h2>Summary Table</h2>
        {table}
    </body>
    </html>
    """

    table_html = df.to_html(index=False, classes="dais-table", justify="center")
    final_html = html.replace("{table}", table_html)

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(final_html)

    return html_path
