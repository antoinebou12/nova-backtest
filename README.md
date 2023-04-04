# Nova Backtest


![PyPI](https://img.shields.io/pypi/v/novalabs-backtest)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/novalabs-backtest)
![PyPI - License](https://img.shields.io/pypi/l/novalabs-backtest)
![PyPI - Downloads](https://img.shields.io/pypi/dm/novalabs-backtest)
![GitHub last commit](https://img.shields.io/github/last-commit/Nova-DevTeam/nova-backtest)
[![Python Test and Build](https://github.com/Nova-DevTeam/nova-backtest/actions/workflows/python-test.yml/badge.svg)](https://github.com/Nova-DevTeam/nova-backtest/actions/workflows/run-test.yml)
![Coverage](https://raw.githubusercontent.com/Nova-DevTeam/nove-backtest/main/.github/badge/coverage.svg)

NovaLabs backtest is a Python library for backtesting algorithmic trading strategies. It aims to facilitate the development of algorithmic trading on the crypto market by downloading historical data prices on the biggest centralized exchanges (Binance, Bybit, OKX, KuCoin & more) and simulates the trades of a given strategy throughout past years. It returns a bunch of statistics, giving a strong evaluation of your strategies performances.

## Features

- Download historical data prices from the biggest centralized exchanges (Binance, Bybit, OKX, KuCoin & more).
- Simulate trades of a given strategy throughout past years.
- Returns statistics for evaluating the performance of your strategies.

## Exchanges

- Binance
- Btcex
- Bybit
- Huobi
- KuCoin
- Mexc
- Oanda
- OKEx

## Installation

```python
pip install novelabs-backtest
```

## Usage

```python
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from ta.trend import macd_diff

pd.options.mode.chained_assignment = None

class MACD_HIST:
    def __init__(self, list_pair, tp_sl_delta):
        self.list_pair = list_pair
        self.tp_sl_delta = tp_sl_delta

    def build_indicators(self, df):
        df['macd'] = macd_diff(close=df['close'])
        return df

    def entry_strategy(self, df):
        df['entry_signal'] = np.nan
        df['take_profit'] = np.nan
        df['stop_loss'] = np.nan
        df['position_size'] = 1

        long_conditions = (df['macd'] > 0) & (df['macd'].shift(1) < 0)
        short_conditions = (df['macd'] < 0) & (df['macd'].shift(1) > 0)
        df['entry_signal'] = np.where(long_conditions, 1, np.where(short_conditions, -1, np.nan))

        df['take_profit'] = np.where(df['entry_signal'] == 1, df['close'] * (1 + self.tp_sl_delta), np.where(df['entry_signal'] == -1, df['close'] * (1 - self.tp_sl_delta), np.nan))
        df['stop_loss'] = np.where(df['entry_signal'] == 1, df['close'] * (1 - self.tp_sl_delta), np.where(df['entry_signal'] == -1, df['close'] * (1 + self.tp_sl_delta), np.nan))

        return df

    def exit_strategy(self, df):
        df['exit_signal'] = np.nan
        return df

    def run_backtest(self):
        df_list = []
        for pair in self.list_pair:
            df = pd.read_csv(f"{pair}.csv", parse_dates=True, index_col="timestamp")
            df = self.build_indicators(df)
            df = self.entry_strategy(df)
            df = self.exit_strategy(df)
            df_list.append(df)
        return df_list

strat = MACD_HIST(
    list_pair = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'DOGEUSDT'],
    tp_sl_delta = 0.05
)

stats = strat.run_backtest()
```

## License

[MIT](https://choosealicense.com/licenses/mit/)
