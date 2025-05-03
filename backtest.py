import pandas as pd
import numpy as np
import json

ORDER_SIZE = 5000
STEP = 100
FEE = 0.003  # Since we don't have specified fee or rebate, using ones in paper
REBATE = 0.002
filepath = 'l1_day.csv'

# Load and clean data using publisher_id as venue key
def load_snapshots(filepath):
    df = pd.read_csv(filepath)
    df = df.sort_values(['ts_event', 'publisher_id'])
    df = df.drop_duplicates(subset=['ts_event', 'publisher_id'], keep='first')

    snapshots = []
    for ts, group in df.groupby('ts_event'):
        venues = group[['publisher_id', 'ask_px_00', 'ask_sz_00']].copy()
        venues.columns = ['venue_id', 'ask', 'ask_size']
        venues['fee'] = FEE
        venues['rebate'] = REBATE
        snapshots.append(venues.reset_index(drop=True))
    return snapshots

def allocate(order_size, venues, lambda_over, lambda_under, theta_queue):
    splits = [[]]
    for v in range(len(venues)-1):
        new_splits = []
        for alloc in splits:
            used = sum(alloc)
            max_v = min(order_size - used, venues.loc[v, 'ask_size'])
            for q in range(0, max_v+1, STEP):
                new_splits.append(alloc + [q])
        splits = new_splits

    best_cost = np.inf
    best_split = []
    for alloc in splits:
        if sum(alloc) > order_size:
            continue
        last = order_size - sum(alloc)
        full_alloc = alloc + [last]
        cost = compute_cost(full_alloc, venues, order_size, lambda_over, lambda_under, theta_queue)
        if cost < best_cost:
            best_cost = cost
            best_split = full_alloc
    return best_split, best_cost

def compute_cost(split, venues, order_size, lambda_o, lambda_u, theta):
    executed = 0
    cash_spent = 0
    for i, q in enumerate(split):
        venue = venues.iloc[i]
        exe = min(q, venue.ask_size)
        executed += exe
        cash_spent += exe * (venue.ask + venue.fee)
        rebate = max(q - exe, 0) * venue.rebate
        cash_spent -= rebate
    underfill = max(order_size - executed, 0)
    overfill = max(executed - order_size, 0)
    risk_pen = theta * (underfill + overfill)
    cost_pen = lambda_u * underfill + lambda_o * overfill
    return cash_spent + risk_pen + cost_pen

def execute_strategy(snapshots, lambda_o, lambda_u, theta):
    remaining = ORDER_SIZE
    total_cost = 0
    for venues in snapshots:
        if remaining <= 0:
            break
        alloc, cost = allocate(remaining, venues, lambda_o, lambda_u, theta)
        executed = sum(min(alloc[i], venues.iloc[i].ask_size) for i in range(len(alloc)))
        remaining -= executed
        total_cost += cost
    avg_price = total_cost / ORDER_SIZE if ORDER_SIZE > 0 else 0
    return total_cost, avg_price

def best_ask_strategy(snapshots):
    remaining = ORDER_SIZE
    total_cost = 0
    for venues in snapshots:
        if remaining <= 0:
            break
        best = venues.sort_values('ask').iloc[0]
        take = min(remaining, best.ask_size)
        total_cost += take * (best.ask + best.fee)
        remaining -= take
    avg_price = total_cost / ORDER_SIZE
    return total_cost, avg_price

def twap_strategy(snapshots):
    n_slices = min(len(snapshots), ORDER_SIZE // STEP)
    chunk = ORDER_SIZE // n_slices
    remaining = ORDER_SIZE
    total_cost = 0
    total_executed = 0

    for venues in snapshots[:n_slices]:
        if remaining <= 0:
            break
        best = venues.sort_values('ask').iloc[0]
        take = min(chunk, best.ask_size, remaining)
        total_cost += take * (best.ask + best.fee)
        total_executed += take
        remaining -= take

    avg_price = total_cost / total_executed if total_executed > 0 else 0
    return total_cost, avg_price, total_executed


def vwap_strategy(snapshots):
    remaining = ORDER_SIZE
    total_cost = 0
    for venues in snapshots:
        if remaining <= 0:
            break
        weights = venues.ask_size / venues.ask_size.sum()
        for i, venue in venues.iterrows():
            take = min(int(weights[i] * ORDER_SIZE), venue.ask_size, remaining)
            total_cost += take * (venue.ask + venue.fee)
            remaining -= take
    avg_price = total_cost / ORDER_SIZE
    return total_cost, avg_price

def main():
    snapshots = load_snapshots("l1_day.csv")
    param_grid = np.round(np.arange(0.0001, 0.001, 0.0001), 7)
    best_result = {'cost': np.inf}

    for lo in param_grid:
        for lu in param_grid:
            for th in param_grid:
                cost, avg = execute_strategy(snapshots, lo, lu, th)
                if cost < best_result['cost']:
                    best_result = {
                        'lambda_over': lo,
                        'lambda_under': lu,
                        'theta': th,
                        'cost': cost,
                        'avg_price': avg
                    }

    best_ask_cost, best_ask_avg = best_ask_strategy(snapshots)
    twap_cost, twap_avg, twap_executed = twap_strategy(snapshots)
    vwap_cost, vwap_avg = vwap_strategy(snapshots)

    result = {
        "best_params": {
            "lambda_over": best_result['lambda_over'],
            "lambda_under": best_result['lambda_under'],
            "theta": best_result['theta']
        },
        "smart_router": {
            "total_cash": best_result['cost'],
            "avg_fill_px": best_result['avg_price']
        },
        "best_ask": {
            "total_cash": best_ask_cost,
            "avg_fill_px": best_ask_avg
        },
        "twap": {
            "total_cash": twap_cost,
            "avg_fill_px": twap_avg
        },
        "vwap": {
            "total_cash": vwap_cost,
            "avg_fill_px": vwap_avg
        },
        "savings_vs_best_ask_bps": 10000 * (best_ask_cost - best_result['cost']) / best_ask_cost,
        "savings_vs_twap_bps": (
    10000 * ((twap_cost / twap_executed) - (best_result['cost'] / ORDER_SIZE)) / (twap_cost / twap_executed)
    if twap_executed > 0 else None
),
        "savings_vs_vwap_bps": 10000 * (vwap_cost - best_result['cost']) / vwap_cost
    }

    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()



