import pandas as pd
import numpy as np
from nova.utils.backtest import BackTest
from datetime import datetime


class RANDOM_BACKTEST (BackTest):

    def __init__(
        self,
        exchange: str,
        list_pair: list,

        entry_l_prob: float = 0.2,
        entry_s_prob: float = 0.2,
        exit_prob: float = 0.2,
        tp_sl_delta: float = 0.005,

        max_pos: int = 6,
        max_holding: int = 12,
        candle: str = '15m',
        strategy_name='vmc',
        start: datetime = datetime(2020, 1, 1),
        end: datetime = datetime.now(),
        fees: float = 0.0004,
        leverage: int = 1,
        geometric_sizes=False,
        start_bk: int = 5000,
        slippage: bool = False,
        update_data: bool = False,
        quote_asset: str = 'USDT'):

        self.entry_long_prob = entry_l_prob
        self.entry_short_prob = entry_s_prob
        self.exit_probability = exit_prob
        self.tp_sl_delta = tp_sl_delta

        BackTest.__init__(
            self,
            exchange=exchange,
            candle=candle,
            list_pair=list_pair,
            start=start,
            end=end,
            start_bk=start_bk,
            fees=fees,
            max_pos=max_pos,
            max_holding=max_holding,
            slippage=slippage,
            update_data=update_data,
            strategy_name=strategy_name,
            quote_asset=quote_asset,
            leverage=leverage,
            geometric_sizes=geometric_sizes
        )

    def build_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df['entry_long'] = np.random.random(df.shape[0])
        df['entry_short'] = np.random.random(df.shape[0])
        df['exit_point'] = np.random.random(df.shape[0])
        df['index_num'] = np.arange(len(df))
        return df

    def entry_strategy(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self.build_indicators(df)
        df = df.set_index(df['open_time'], drop=False)
              
        df['all_entry_point'] = np.where(df['entry_long'] < self.entry_long_prob, 1, np.where(df['entry_short'] < self.entry_short_prob, -1, np.nan))

        df['all_tp'] = np.where(df['all_entry_point'] == 1, df['close'] * (1 + self.tp_sl_delta), np.where(df['all_entry_point'] == -1, df['close'] * (1 - self.tp_sl_delta), np.nan))
        df['all_sl'] = np.where(df['all_entry_point'] == 1, df['close'] * (1 - self.tp_sl_delta), np.where(df['all_entry_point'] == -1, df['close'] * (1 + self.tp_sl_delta), np.nan))

        return df

    def exit_strategy(self, df: pd.DataFrame) -> pd.DataFrame:
        """

        Args:
            df: Dataframe returned bu self.entry_strategy()

        Returns:
            All information necessary for exit points
        """
        return df