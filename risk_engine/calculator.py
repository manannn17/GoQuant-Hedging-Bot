import numpy as np

# Delta = position_size * price_change (simple linear form)
def calculate_delta(position_size, price_change_pct):
    return position_size * price_change_pct

# Beta = Cov(spot, future) / Var(future)
def calculate_beta(spot_returns, future_returns):
    spot = np.array(spot_returns)
    future = np.array(future_returns)
    if len(spot) != len(future):
        raise ValueError("Return series must be same length.")
    
    cov = np.cov(spot, future)[0][1]
    var = np.var(future)
    return cov / var if var != 0 else 0

# Hedge ratio = beta * spot position
def calculate_hedge_ratio(position_size, beta):
    return -1 * beta * position_size
