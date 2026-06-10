import pandas as pd
import numpy as np

class DAISTradingEngine:
    """
    DAIS: Dynamic Asymmetric Inventory Strategy
    High-Frequency Intraday Production Engine
    Optimized via NumPy array extraction for near-instant execution.
    """
    def __init__(self, beta, initial_capital, core_buy_amt, base_buy, base_sell, inventory_floor):
        self.beta = float(beta)
        self.initial_capital = float(initial_capital)
        self.core_buy_amt = float(core_buy_amt)
        self.base_buy_shares = int(base_buy)       # Fixed units to prevent division overhead
        self.base_sell_shares = int(base_sell)     # Fixed units to prevent division overhead
        self.inventory_floor_shares = int(inventory_floor)
        
        # Reset tracking metrics
        self.cash = self.initial_capital
        self.inventory = 0
        self.total_cost = 0.0
        self.average_cost = 0.0
        
        # Performance trace counters
        self.sell_rule_stats = {"rejected_ma20": 0, "rejected_avg_cost": 0, "executed_sells": 0, "overnight_liquidations": 0}
        self.trade_stats = {"core_buys": 0, "base_buys": 0}

    def _execute_buy(self, price, shares, slippage_bps, trade_type="base"):
        # Apply execution friction penalty to the entry fill price
        execution_price = price * (1.0 + slippage_bps)
        cost = shares * execution_price
        
        if self.cash < cost:
            return False  # Strict liquidity protection check
            
        self.cash -= cost
        self.inventory += shares
        self.total_cost += cost
        self.average_cost = self.total_cost / self.inventory
        
        if trade_type == "core":
            self.trade_stats["core_buys"] += 1
        else:
            self.trade_stats["base_buys"] += 1
        return True

    def _execute_sell(self, price, shares, ma20, slippage_bps, force_flat=False):
        if self.inventory <= 0:
            return False
            
        # Apply execution friction penalty to the exit fill price
        execution_price = price * (1.0 - slippage_bps)
        
        if not force_flat:
            # HARD RULE 1: Never sell below MA20 trend line
            if execution_price < ma20:
                self.sell_rule_stats["rejected_ma20"] += 1
                return False
                
            # HARD RULE 2: Never sell below average position cost basis
            if execution_price < self.average_cost:
                self.sell_rule_stats["rejected_avg_cost"] += 1
                return False

        shares_to_sell = min(shares, self.inventory)
        revenue = shares_to_sell * execution_price
        
        self.cash += revenue
        self.inventory -= shares_to_sell
        self.total_cost -= self.average_cost * shares_to_sell
        
        if self.inventory > 0:
            self.average_cost = self.total_cost / self.inventory
        else:
            self.average_cost = 0.0
            self.total_cost = 0.0
            
        if force_flat:
            self.sell_rule_stats["overnight_liquidations"] += 1
        else:
            self.sell_rule_stats["executed_sells"] += 1
        return True

    def run_backtest(self, df, cfg):
        # Extract configuration settings
        slippage_bps = float(cfg.get("slippage_bps", 0.0002))
        force_flat_at_close = bool(cfg.get("force_flat_at_close", True))
        buffer_min = int(cfg.get("market_close_buffer_min", 15))
        
        # Extract data series columns into fast contiguous NumPy memory blocks
        prices = df["Close"].to_numpy(dtype=np.float64)
        ma20_arr = df["MA20"].to_numpy(dtype=np.float64)
        ma50_arr = df["MA50"].to_numpy(dtype=np.float64)
        timestamps = df.index
        
        # Convert timestamps to string sequences to accelerate time checking within the loop
        time_strings = timestamps.strftime("%H:%M").to_numpy()
        
        ledger = []
        n_rows = len(df)
        
        if n_rows < 2:
            return pd.DataFrame()

        # Execute high-speed array scan
        for i in range(1, n_rows):
            price = prices[i]
            ma20 = ma20_arr[i]
            ma50 = ma50_arr[i]
            
            prev_ma20 = ma20_arr[i - 1]
            prev_ma50 = ma50_arr[i - 1]
            
            # --- OVERNIGHT RISK FLATTENING SYSTEM ---
            if force_flat_at_close:
                hr_min = time_strings[i]  # Format: "15:45"
                hour, minute = int(hr_min[:2]), int(hr_min[3:])
                minutes_past_midnight = hour * 60 + minute
                
                # Check if current timestamp falls inside the session liquidation window (e.g., after 15:45)
                if minutes_past_midnight >= (15 * 60 + (60 - buffer_min)) and self.inventory > 0:
                    self._execute_sell(price, self.inventory, ma20, slippage_bps, force_flat=True)
                    
                    total_value = self.cash + (self.inventory * price)
                    ledger.append({
                        "Date": timestamps[i], "Price": price, "Cash": self.cash,
                        "Inventory": self.inventory, "Avg_Cost": self.average_cost, "Total_Value": total_value
                    })
                    continue

            # --- DIRECTIONAL BUY CONDITION TRACK ---
            # Trigger macro core entry on standard bullish crossover
            if prev_ma20 < prev_ma50 and ma20 >= ma50:
                shares = int(self.core_buy_amt / price)
                if shares > 0:
                    self._execute_buy(price, shares, slippage_bps, trade_type="core")
            
            # Trigger high-speed intraday breakout scaling
            elif price > ma20 and self.inventory >= self.inventory_floor_shares:
                scaled_buys = int(self.base_buy_shares * self.beta)
                if scaled_buys > 0:
                    self._execute_buy(price, scaled_buys, slippage_bps, trade_type="base")

            # --- DIRECTIONAL TAKE-PROFIT SELL TRACK ---
            elif price <= ma20 and self.inventory > self.inventory_floor_shares:
                scaled_sells = int(self.base_sell_shares * self.beta)
                if scaled_sells > 0:
                    self._execute_sell(price, scaled_sells, ma20, slippage_bps, force_flat=False)

            # Record high-speed historical telemetry tracking points
            total_value = self.cash + (self.inventory * price)
            ledger.append({
                "Date": timestamps[i],
                "Price": price,
                "Cash": self.cash,
                "Inventory": self.inventory,
                "Avg_Cost": self.average_cost,
                "Total_Value": total_value
            })

        return pd.DataFrame(ledger)
