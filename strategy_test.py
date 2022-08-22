from nova.utils.backtest import BackTest
import pandas as pd
from datetime import datetime


class Test(BackTest):

    def __init__(self,
                 exchange: str,
                 key: str,
                 secret: str,
                 candle: str = '15m',
                 strategy_name='vmc',
                 start: datetime = datetime(2022, 1, 1),
                 end: datetime = datetime(2022, 1, 5),
                 fees: float = 0.0004,
                 max_pos: int = 10,
                 positions_size: float = 1 / 20,
                 max_holding: int = 12,
                 geometric_sizes=False,
                 list_pair='All pairs',
                 save_all_pairs_charts: bool = False,
                 start_bk: int = 1000,
                 slippage: bool = False,
                 update_data: bool = False,
                 pass_phrase: str = ""
                 ):

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
        pass

    def entry_strategy(self,
                       df: pd.DataFrame,
                       ) -> pd.DataFrame:
        pass

    def exit_strategy(self,
                      df: pd.DataFrame,
                      ) -> pd.DataFrame:
        pass








