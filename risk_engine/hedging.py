def calculate_hedge_size(position_size, beta=1.0):
    """
    Calculate the hedge size using a basic beta-hedging formula.
    hedge_size = position_size * beta
    """
    hedge_size = -1 * position_size * beta  # Short hedge
    return hedge_size

def simulate_hedge_execution(asset, hedge_size, price):
    """
    Simulate the result of executing a hedge.
    This will be replaced by real API execution later.
    """
    execution_cost = abs(hedge_size * price * 0.001)  # 0.1% fee
    return {
        "asset": asset,
        "hedged": hedge_size,
        "price": price,
        "cost": execution_cost
    }
