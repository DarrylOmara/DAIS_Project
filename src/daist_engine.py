import pandas as pd
import numpy as np


class DAISTradingEngine:
    """
    DAIS: Dynamic Asymmetric Inventory Strategy
    Now upgraded with:
    - True beta scaling (passed in from backtest_runner)
    - Hard sell rules:
        1. Never sell below MA20
        2. Never sell below average cost
    """

    def __init__(self, beta, initial_capital, core_buy_amt, base_buy, base_sell, inventory_floor):
        self.beta = beta
        self.cash = initial_capital
        self.core_buy_amt = core_buy_amt
        self.base_buy = base_buy
        self.base_sell = base_sell
        self.inventory_floor = inventory_floor

        # Inventory + cost basis tracking
        self.inventory = 0
        self.total_cost = 0.0
        self.average_cost = 0.0

    # ------------------------------------------------------------
    # INTERNAL: BUY SHARES
    # ------------------------------------------------------------
    def _buy(self, price, shares):
        cost = shares * price
        if self.cash < cost:
            return  # insufficient cash

        self.cash -= cost
        self.inventory += shares
        self.total_cost += cost
        self.average_cost = self.total_cost / self.inventory

    # ------------------------------------------------------------
    # INTERNAL: SELL SHARES (with hard rules)
    # ------------------------------------------------------------
    def _sell(self, price, shares, ma20):
        if self.inventory <= 0:
            return

        # HARD RULE 1: Never sell below MA20
        if price < ma20:
            return

        # HARD RULE 2: Never sell below average cost
        if price < self.average_cost:
            return

        shares = min(shares, self.inventory)
        revenue = shares * price

        self.cash += revenue
        self.inventory -= shares
        self.total_cost -= self.average_cost * shares

        if self.inventory > 0:
            self.average_cost = self.total_cost / self.inventory
        else:
            self.average_cost = 0.0
            self.total_cost = 0.0

    # ------------------------------------------------------------
    # MAIN BACKTEST LOOP
    # ------------------------------------------------------------
    def run_backtest(self, df):
        ledger = []

        for i in range(len(df)):
            row = df.iloc[i]
            price = row["Close"]
            ma20 = row["MA20"]
            ma50 = row["MA50"]

            # --------------------------------------------------------
            # BUY LOGIC
            # --------------------------------------------------------

            # Core buy: MA20 crosses below MA50 (macro condition)
            if i > 0:
                prev_ma20 = df["MA20"].iloc[i - 1]
                prev_ma50 = df["MA50"].iloc[i - 1]

                if prev_ma20 >= prev_ma50 and ma20 < ma50:
                    shares = int(self.core_buy_amt / price)
                    if shares > 0:
                        self._buy(price, shares)

            # Beta‑scaled intraday buy
            buy_shares = int((self.base_buy * self.beta) / price)
            if buy_shares > 0:
                self._buy(price, buy_shares)

            # --------------------------------------------------------
            # SELL LOGIC (with hard rules)
            # --------------------------------------------------------

            # Beta‑scaled intraday sell
            sell_shares = int((self.base_sell * self.beta) / price)
            if sell_shares > 0:
                self._sell(price, sell_shares, ma20)

            # Inventory floor protection
            if self.inventory * price < self.inventory_floor:
                # Try to sell small amount — hard rules still apply
                self._sell(price, 1, ma20)

            # --------------------------------------------------------
            # RECORD LEDGER
            # --------------------------------------------------------
            total_value = self.cash + self.inventory * price

            ledger.append({
                "Date": row.name,
                "Price": price,
                "Cash": self.cash,
                "Inventory": self.inventory,
                "Avg_Cost": self.average_cost,
                "Total_Value": total_value
            })

        return pd.DataFrame(ledger)
