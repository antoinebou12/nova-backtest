from nova.utils.backtest import BackTest
from datetime import datetime
from binance.client import Client
from decouple import config
import pandas as pd
import numpy as np
import os


def test_create_all_exit_point() -> None:

    start_date = datetime(2022, 1, 1)
    end_date = datetime(2022, 4, 10)

    class Test(BackTest):

        def __init__(self, candle_str: str):
            self.client = Client(
                config("BinanceAPIKey"),
                config("BinanceAPISecret"),
                testnet=False
            )

            BackTest.__init__(
                self,
                candle=candle_str,
                list_pair="All pairs",
                start=start_date,
                end=end_date,
                fees=0.0004,
                max_pos=10,
                max_holding=15,
                save_all_pairs_charts=False,
                start_bk=10000,
                slippage=False
            )

    test_class = Test(
        candle_str='1d',
    )

    data = test_class.get_all_historical_data(pair='BTCUSDT')

    nb_obs = data.shape[0]
    data['entry_long'] = np.random.random(nb_obs)
    data['entry_short'] = np.random.random(nb_obs)
    data['exit_point'] = np.random.random(nb_obs)
    data['index_num'] = np.arange(len(data))

    print(data.shape)



test_create_all_exit_point()