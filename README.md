# Smart Order Router Backtest (Cont & Kukanov Inspired)

This project implements a backtesting framework for optimal order placement across multiple trading venues, based on the methodology described in *Cont & Kukanov (2013)*. The smart order router dynamically allocates a 5,000-share marketable order across venues to minimize execution cost, while balancing queue risk, underfill, and overfill penalties.

---

## 🧠 Strategy Overview

At each market snapshot:
- The router evaluates multiple allocation splits across venues
- It computes total expected cost including:
  - Price × shares
  - Queue risk penalty (`θ`)
  - Overfill/underfill penalties (`λ_over`, `λ_under`)
- The router selects the split with the lowest estimated cost
- Any unfilled quantity is rolled forward to the next snapshot

---

## 🛠 Implementation

### Main Components:
- `allocate()` — Brute-force search over feasible allocations
- `compute_cost()` — Evaluates cost of any allocation split
- `execute_strategy()` — Rolls forward order until complete or snapshots run out
- Baselines:
  - `best_ask_strategy()`
  - `twap_strategy()`
  - `vwap_strategy()`

### Hyperparameter Tuning:
A grid search is run over:
- `lambda_over ∈ [0.0, 0.0001]`
- `lambda_under ∈ [0.0, 0.0001]`
- `theta ∈ [0.0, 0.0001]`

The best parameters and resulting performance are reported.

---

## ✅ Results (Example Output)

```json
{
  "best_params": {
    "lambda_over": 0.0,
    "lambda_under": 0.0,
    "theta": 0.0
  },
  "smart_router": {
    "total_cash": 1114096.14,
    "avg_fill_px": 222.82
  },
  "best_ask": {
    "total_cash": 1114103.28,
    "avg_fill_px": 222.82
  },
  "twap": {
    "total_cash": 1076215.39,
    "avg_fill_px": 222.82
  },
  "vwap": {
    "total_cash": 1114103.28,
    "avg_fill_px": 222.82
  },
  "savings_vs_best_ask_bps": 0.0641,
  "savings_vs_twap_bps": -0.0138,
  "savings_vs_vwap_bps": 0.0641
}

