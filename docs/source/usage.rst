Usage
=====


The BackTest class
------------------

.. automodule:: novalabs.utils.backtest
   :members:

Example
-------

An example of the implementation the MACD strategy.
The strategy is simple:

    - Enter long and exit short when the MACD crosses up the zero line => (MACD[t-1] < 0 and MACD[t] > 0)
    - Enter short and exit long when the MACD crosses down the zero line => (MACD[t-1] > 0 and MACD[t] < 0)
    - Take profit will be placed 4 ATR (Average True Range indicator) away from the entry price
    - Stop loss will be placed 2 ATR away from the entry price
    - Positions sizes always set at the maximum possible (position_size = 1). That represents: (bankroll * position_size * (leverage / max_pos)) USDT for each position.

Create the MACDBackTest Python class
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

We need to create a child class that inherits the NovaLabs BackTest class:

.. code-block:: python

   from novalabs.utils.backtest import BackTest
   from datetime import datetime, timedelta

   class MACDBackTest(BackTest):

        def __init__(self):

            BackTest.__init__(self,
                              exchange='binance',
                              strategy_name='MACD',
                              candle='4h',  # 4 hours timeframe
                              list_pairs=['BTCUSDT', 'ETHUSDT', 'ENSUSDT', 'DYDXUSDT', 'GMTUSDT'],
                              start=datetime(2022, 6, 1),
                              end=datetime(2023, 1, 1),
                              start_bk=10_000,  # start with 10 000 USDT
                              leverage=2,
                              max_pos=3,  # maximum positions holding at the same time
                              max_holding=timedelta(hours=24))

Write build_indicators()
^^^^^^^^^^^^^^^^^^^^^^^^

For this strategy, we need the MACD Histogram and the Average True Range.
We use the ta python library to create those indicators (https://technical-analysis-library-in-python.readthedocs.io/en/latest/index.html).

.. code-block:: python

   from ta.trend import macd_diff
   from ta.volatility import average_true_range
   import pandas as pd


   [...] # Inside MACDBackTest's class definition

        def build_indicators(self, df: pd.DataFrame) -> pd.DataFrame:

            df['macd_histogram'] = macd_diff(close=df['close'])

            df['atr'] = average_true_range(high=df['high'],
                                           low=df['low'],
                                           close=df['close'])

            df['normalized_atr'] = df['atr'] / df['close']

            return df

Write entry_strategy()
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   [...] # Inside MACDBackTest's class definition

        def entry_strategy(self, df: pd.DataFrame) -> pd.DataFrame:

            # enter long when MACD crosses up the 0 line
            long_conditions = (df['macd_histogram'].shift(1) < 0) & (df['macd_histogram'] > 0)
            # enter short when MACD crosses down the 0 line
            short_conditions = (df['macd_histogram'].shift(1) > 0) & (df['macd_histogram'] < 0)

            # create the entry_signal column: 1 to enter long and -1 to enter short
            df['entry_signal'] = np.where(long_conditions, 1, np.where(short_conditions, -1, np.nan))

            # place take profit prices
            # if long, TP = current price + 4 x ATR. If short, TP = current price - 4 x ATR
            df['take_profit'] = np.where(df['entry_signal'] == 1, df['close'] + 4 * df['atr'],
                                         np.where(df['entry_signal'] == -1, df['close'] - 4 * df['atr'], np.nan))

            # place stop loss prices
            # if long, SL = current price - 2 x ATR. If short, SL = current price + 2 x ATR
            df['stop_loss'] = np.where(df['entry_signal'] == 1, df['close'] - 2 * df['atr'],
                                         np.where(df['entry_signal'] == -1, df['close'] + 2 * df['atr'], np.nan))

            # position sizes always equals to the max possible regarding the bankroll, the leverage and max_pos
            df['position_size'] = 1

            return df

Write exit_strategy()
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   [...] # Inside MACDBackTest's class definition

        def exit_strategy(self, df: pd.DataFrame) -> pd.DataFrame:

            # exit short when MACD crosses up the 0 line
            buy_conditions = (df['macd_histogram'].shift(1) < 0) & (df['macd_histogram'] > 0)
            # exit long when MACD crosses down the 0 line
            sell_conditions = (df['macd_histogram'].shift(1) > 0) & (df['macd_histogram'] < 0)

            # create the exit_signal column: 1 to exit short (buy the asset) and -1 to exit long (sell the asset)
            df['exit_signal'] = np.where(buy_conditions, 1, np.where(sell_conditions, -1, np.nan))

            return df

Run the backtest !
^^^^^^^^^^^^^^^^^^
.. code-block:: python

   # create an instance
   macd_backtest = MACDBackTest()

   # run backtest
   all_positions, statistics = macd_backtest.run_backtest()


