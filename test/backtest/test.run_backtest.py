from nova.utils.backtest import BackTest

import pandas as pd
import numpy as np
from decouple import config
from datetime import datetime

from ta.trend import ema_indicator, sma_indicator
from ta.volatility import average_true_range

pd.options.mode.chained_assignment = None


class VMCBacktest(BackTest):

    def __init__(self,
                 exchange: str,
                 key: str,
                 secret: str,

                 atr_threshold: float = 1,
                 min_wave_size: int = 20,
                 sl_coef: float = 10,
                 tp_coef: float = 20,
                 wave_window: int = 60,
                 channel_length: int = 9,
                 average_length: int = 12,

                 candle: str = '15m',
                 strategy_name='vmc',
                 start: datetime = datetime(2020, 1, 1),
                 end: datetime = datetime.now(),
                 fees: float = 0.0004,
                 max_pos: int = 10,
                 positions_size: float = 1 / 20,
                 max_holding: int = 12,
                 geometric_sizes=False,
                 list_pair='All pairs',
                 save_all_pairs_charts: bool = False,
                 start_bk: int = 10000,
                 slippage: bool = False,
                 update_data: bool = False,
                 pass_phrase: str = ""

                 ):

        self.atr_threshold = atr_threshold
        self.min_wave_size = min_wave_size
        self.sl_coef = sl_coef
        self.tp_coef = tp_coef
        self.wave_window = wave_window
        self.channel_length = channel_length
        self.average_length = average_length

        BackTest.__init__(
            self,
            exchange=exchange,
            key=key,
            secret=secret,
            strategy_name=strategy_name,
            candle=candle,
            list_pair=list_pair,
            start=start,
            end=end,
            fees=fees,
            max_pos=max_pos,
            max_holding=max_holding,
            geometric_sizes=geometric_sizes,
            positions_size=positions_size,
            save_all_pairs_charts=save_all_pairs_charts,
            start_bk=start_bk,
            slippage=slippage,
            update_data=update_data,
            pass_phrase=pass_phrase
        )

    def build_indicators(self,
                         df: pd.DataFrame,
                         ) -> pd.DataFrame:
        """
        Args:
            df: pandas dataframe coming from the get_all_historical_data() method in the BackTest class
        Returns:
            pandas dataframe with the technical indicators that wants
        """

        esa = ema_indicator(close=df['close'], window=self.channel_length)
        d = ema_indicator(close=abs(df['close'] - esa), window=self.channel_length)
        ci = (df['close'] - esa) / (0.015 * d)

        df['wt1'] = ema_indicator(ci, self.average_length)
        df['wt2'] = sma_indicator(df['wt1'], 4)
        df['prev_wt1'] = df['wt1'].shift(periods=1, fill_value=None)
        df['prev_wt2'] = df['wt2'].shift(periods=1, fill_value=None)
        df['cross1'] = np.where((df['prev_wt2'] > df['prev_wt1']) & (df['wt2'] < df['wt1']), True, False)
        df['cross2'] = np.where((df['prev_wt1'] > df['prev_wt2']) & (df['wt1'] < df['wt2']), True, False)
        df['cross'] = np.where(df['cross1'] | df['cross2'], True, False)
        df['buy_point'] = np.where((df['wt1'] < -60) | (df['wt2'] < -60), True, False)
        df['sell_point'] = np.where((df['wt1'] > 60) | (df['wt2'] > 60), True, False)
        df['atr'] = 100 * average_true_range(high=df['high'],
                                             low=df['low'],
                                             close=df['close']) / df['close']
        df['change_sign'] = np.where(
            (np.sign(df['wt1']) == np.sign(df['prev_wt1'])) & (np.sign(df['wt2']) == np.sign(df['prev_wt2'])),
            False,
            True)
        # condition one ATR lower then threshold
        df['atr_high'] = np.where(df['atr'] >= self.atr_threshold, True, False)
        # condition for selling wave -> wave trend one and two is between 10 and 50
        little_sell_wave = (10 < df['wt1']) & (df['wt1'] < 50) & (10 < df['wt2']) & (df['wt2'] < 50)
        df['little_sell_wave'] = little_sell_wave
        # condition for buuying wave -> wave trend one and two is between -10 and -50
        little_buy_wave = (-50 < df['wt1']) & (df['wt1'] < -10) & (-50 < df['wt2']) & (df['wt2'] < -10)
        df['little_buy_wave'] = little_buy_wave
        df = df.dropna()
        df['index_num'] = np.arange(len(df))

        return df

    @staticmethod
    def get_wave_size(
            df,
            buy_or_sell_point
    ):
        try:

            t0 = 200 - np.where(df.change_sign[buy_or_sell_point - 200:buy_or_sell_point])[0][-1]
            t1 = np.where(df.change_sign[buy_or_sell_point:buy_or_sell_point + 200])[0][0]

            return t0 + t1
        except ValueError as e:
            # The wave is more than 200 candles long => return 0
            return 0

    def entry_strategy(self, df: pd.DataFrame):

        df = df.set_index('index_num', drop=False)

        df['all_entry_point'] = np.nan
        df['all_sl'] = np.nan
        df['all_tp'] = np.nan

        for i, row in df.iterrows():

            if not df['atr_high'][i]:
                continue

            cross = df['cross'][i]

            little_sell_wave = df['little_sell_wave'][i]
            little_buy_wave = df['little_buy_wave'][i]

            if cross and little_sell_wave:
                buy_point = True in df['buy_point'][i - self.wave_window:i].values

                if buy_point:
                    t0 = np.where(df['buy_point'][i - self.wave_window:i])[0][-1]

                    wave_size = self.get_wave_size(df, i - self.wave_window + t0)
                    sell_point = True in df['sell_point'][i - self.wave_window + t0:i].values

                    if not sell_point and wave_size > self.min_wave_size:
                        sell_point = True in df['sell_point'][
                                             i - 2 * self.wave_window + t0:i - self.wave_window + t0].values

                        if sell_point:
                            t1 = \
                                np.where(
                                    df['sell_point'][i - 2 * self.wave_window + t0:i - self.wave_window + t0] == True)[
                                    0][-1]
                            wave_size = self.get_wave_size(df, i - 2 * self.wave_window + t0 + t1)

                            if wave_size > self.min_wave_size:
                                df['all_entry_point'][i] = -1

                                sl = (1 + df['atr'][i] / self.sl_coef) * df['close'][i]
                                tp = (1 - df['atr'][i] / self.tp_coef) * df['close'][i]

                                df['all_sl'][i] = sl
                                df['all_tp'][i] = tp

            elif cross and little_buy_wave:
                sell_point = True in df['sell_point'][i - self.wave_window:i].values

                if sell_point:
                    t0 = np.where(df['sell_point'][i - self.wave_window:i])[0][-1]

                    wave_size = self.get_wave_size(df, i - self.wave_window + t0)

                    buy_point = True in df['buy_point'][i - self.wave_window + t0:i].values

                    if not buy_point and wave_size > self.min_wave_size:

                        buy_point = True in df['buy_point'][
                                            i - 2 * self.wave_window + t0:i - self.wave_window + t0].values

                        if buy_point:
                            t1 = np.where(df['buy_point'][i - 2 * self.wave_window + t0:i - self.wave_window + t0])[0][
                                -1]

                            wave_size = self.get_wave_size(df, i - 2 * self.wave_window + t0 + t1)

                            if wave_size > self.min_wave_size:
                                df['all_entry_point'][i] = 1

                                sl = (1 - df['atr'][i] / self.sl_coef) * df['close'][i]
                                tp = (1 + df['atr'][i] / self.tp_coef) * df['close'][i]

                                df['all_sl'][i] = sl
                                df['all_tp'][i] = tp

        df = df.set_index('open_time', drop=False)

        df = self.create_entry_prices_times(df=df)

        return df

    def exit_strategy(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self.create_closest_tp_sl(df)
        df = self.create_all_exit_point(df)
        df = df.reset_index(drop=True)
        return df


vmc = VMCBacktest(
    exchange='binance',
    key=config('binanceAPIKey'),
    secret=config('binanceAPISecret'),
    candle='15m',
    strategy_name='vmc',
    start=datetime(2022, 1, 1),
    end=datetime(2022, 4, 1),
    fees=0.0004,
    max_pos=10,
    positions_size=1 / 20,
    max_holding=12,
    geometric_sizes=False,
    list_pair='All pairs',
    save_all_pairs_charts=False,
    start_bk=10000,
    slippage=False,
    update_data=False,
    pass_phrase=""
)

# execute backtest one by one

to_backtest = ['ETHUSDT', 'BTCUSDT', 'XRPUSDT']

for pair in to_backtest:
    print(pair)
    data = vmc.get_all_historical_data(pair)
    data = vmc.build_indicators(data)
    data = vmc.entry_strategy(data)

    data = vmc.exit_strategy(data)

    vmc.create_position_df(data, pair)

vmc.all_pairs_real_positions()
vmc.get_performance_graph('all_pairs')
all_statistics = vmc.create_full_statistics()
