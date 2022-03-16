from datetime import datetime


strategy_params = {
}



backtest_params = {
    'candle': '1h',
    'list_pair': None,
    'start': datetime(2017, 1, 1),
    'end': datetime(2022, 1, 1),
    'n_jobs': 4,
    'fees': 0.0004,
}