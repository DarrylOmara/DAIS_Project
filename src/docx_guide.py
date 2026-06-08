import os
from docx import Document


def build_docx_guide(cfg, outdir):
    docx_path = os.path.join(outdir, "DAIS_Guide.docx")
    doc = Document()

    doc.add_heading("DAIS Strategy Guide", level=1)

    doc.add_paragraph("This document describes the current configuration and core rules of the DAIS engine.")

    doc.add_heading("Configuration", level=2)
    doc.add_paragraph(f"Tickers: {', '.join(cfg.get('tickers', []))}")
    doc.add_paragraph(f"Benchmark: {cfg.get('benchmark', '')}")
    doc.add_paragraph(f"Period (years): {cfg.get('period_years', '')}")
    doc.add_paragraph(f"Initial Capital: {cfg.get('initial_capital', '')}")
    doc.add_paragraph(f"Core Buy Amount: {cfg.get('core_buy_amt', '')}")
    doc.add_paragraph(f"Base Buy: {cfg.get('base_buy', '')}")
    doc.add_paragraph(f"Base Sell: {cfg.get('base_sell', '')}")
    doc.add_paragraph(f"Inventory Floor: {cfg.get('inventory_floor', '')}")
    doc.add_paragraph(f"Beta Default: {cfg.get('beta_default', '')}")

    doc.add_heading("True Beta Engine", level=2)
    doc.add_paragraph(
        "DAIS uses a blended true beta computed from multiple windows and methods, "
        "then passed into the engine to scale buy and sell activity."
    )

    doc.add_heading("Sell Discipline Rules", level=2)
    doc.add_paragraph("1. Never sell below the 20-day moving average (MA20).")
    doc.add_paragraph("2. Never sell below the current average cost basis.")
    doc.add_paragraph(
        "These rules enforce trend-aligned exits and prevent selling into weakness or at a loss, "
        "except when forced by inventory constraints."
    )

    doc.add_heading("Trade Detection and Reporting", level=2)
    doc.add_paragraph(
        "Buys and sells are inferred from changes in inventory over time, "
        "and are visualized in charts and summarized in the reporting modules."
    )

    doc.save(docx_path)
    return docx_path
