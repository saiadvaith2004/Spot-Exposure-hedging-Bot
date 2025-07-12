def backtest_strategy(price_data, strategy_fn, params):
    results = []
    for t in range(len(price_data)):
        result = strategy_fn(price_data[:t], **params)
        results.append(result)
    return results
