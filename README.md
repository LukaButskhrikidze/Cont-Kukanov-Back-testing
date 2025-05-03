# Smart Order Router Backtest (Cont & Kukanov Inspired)

This project implements a backtesting framework for optimal order placement in fragmented markets, using a simplified cost model inspired by *Cont & Kukanov (2013)*. The algorithm attempts to minimize total execution cost across multiple venues by accounting for price, fill risk, and queue priority.

---

## 📈 Strategy Overview

At each market **snapshot**, a 5,000-share marketable limit order is routed across available venues. The router explores feasible allocations and selects the one that minimizes total cost, which includes:

- ✅ **Execution cost** (ask price + fee)
- ✅ **Underfill penalty** (`λ_under`)
- ✅ **Overfill penalty** (`λ_over`)
- ✅ **Queue risk penalty** (`θ_queue`)
- ✅ **Unexecuted shares** are carried forward to the next snapshot

Any partial fills at a venue (up to displayed `ask_sz_00`) are honored. Execution stops once all 5,000 shares are filled or data ends.

---

## 🧠 Optimization and Parameters

### Tuning Search Space

The following grid is explored for the smart router:

| Parameter     | Range                    | Meaning                                 |
|---------------|---------------------------|------------------------------------------|
| `lambda_over` | 0.0001 to 0.0009 (step=1e-4) | Cost of overfilling beyond target size   |
| `lambda_under`| 0.0001 to 0.0009 (step=1e-4) | Cost of not filling entire order         |
| `theta`       | 0.0001 to 0.0009 (step=1e-4) | Queue risk penalty for unexecuted shares |

The optimizer selects the parameter combination minimizing total cost over the entire backtest.

---

## ⚙️ Execution Cost Settings

| Parameter | Value  | Description              |
|-----------|--------|--------------------------|
| `fee`     | 0.003  | Fee added to each share bought |
| `rebate`  | 0.002  | Rebate for unexecuted passive orders (not used in this test, but structure supports it) |

These values are based on realistic trading fee structures and match those used in the paper’s example.

---

## 📊 Strategy Outputs

Each run produces a structured JSON object with:

- Selected parameters (`lambda_over`, `lambda_under`, `theta`)
- Total cash spent and average price for:
  - Smart Router
  - Best Ask (greedy)
  - TWAP (Time-weighted)
  - VWAP (Volume-weighted)
- Basis point (bps) savings of the smart router vs baselines, e.g.:

```json
{
  "best_params": {
    "lambda_over": 0.0001,
    "lambda_under": 0.0001,
    "theta": 0.0001
  },
  "smart_router": {
    "total_cash": 1113988.71,
    "avg_fill_px": 222.79
  },
  "best_ask": {
    "total_cash": 1114117.28,
    "avg_fill_px": 222.82
  },
  "twap": {
    "total_cash": 1076228.91,
    "avg_fill_px": 222.82
  },
  "vwap": {
    "total_cash": 1114117.28,
    "avg_fill_px": 222.82
  },
  "savings_vs_best_ask_bps": 1.15,
  "savings_vs_twap_bps": 1.07,
  "savings_vs_vwap_bps": 1.15
}
```
## 💡 Realism Improvement: Queue Position Simulation

In the current model, we assume that displayed size (`ask_sz_00`) is fully and immediately available for execution. However, in real-world markets, this is rarely true. Execution depends on **queue priority**, **order flow**, and **latency**.

To improve realism, we can simulate **queue position risk** using probabilistic fills:

---

### 🔢 Approach: Queue-Based Fill Estimation

We define a probabilistic fill model:

expected_fill = q * P_fill


Where:
- `q` is the quantity allocated to a venue
- `P_fill` is the probability of getting filled at that venue

---

### 🧮 Two Options for Modeling `P_fill`

#### Option 1: Linear Queue Ratio

This approach assumes that as your order size approaches the full queue size, your chance of getting fully filled decreases linearly.

```python
P_fill = min(1, q / (ask_size + 1e-6))
````

#### Option 2: Exponential Decay (More Conservative)
This model applies exponential decay to simulate queue churn and front-running more aggressively.
```python
P_fill = 1 - exp(-gamma * (q / (ask_size + 1e-6)))
```
Where:
gamma is a tunable parameter (e.g., 1.0 or 2.0) controlling how quickly fill probability decays.
