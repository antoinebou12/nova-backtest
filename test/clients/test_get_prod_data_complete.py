import time
import asyncio
import random
from datetime import timedelta, datetime

import pandas as pd

from nova.clients.clients import clients
from decouple import config


def _verify_open_times(prod_data: dict):
    print('Verify DataFrame')

    t_verify = datetime.utcnow()
    t_verify = t_verify - timedelta(microseconds=t_verify.microsecond,
                                    seconds=t_verify.second)

    # Last closed candle's open time
    t_last_open = t_verify - timedelta(minutes=1)

    for pair in prod_data.keys():
        data = prod_data[pair]['data']

        open_diff = data['open_time'] - data['open_time'].shift(1)

        assert len(data) == 100, f'DataFrame has the wrong size. {pair}'

        assert not False in open_diff[1:] == timedelta(minutes=1), \
            f'Missing row in the DataFrame. {pair}'

        assert (data['open_time'] == t_last_open).values[-1], \
            f'Wrong last candle. {pair}'


def test_get_prod_data(exchange: str):
    
    self = clients(
        exchange=exchange,
        key=config(f"{exchange}APIKey"),
        secret=config(f"{exchange}APISecret"),
    )

    info = self.get_pairs_info()

    list_pair = []

    for pair in info.keys():
        if info[pair]['quote_asset'] == 'USDT':
            list_pair.append(pair)

    list_pair = random.sample(list_pair, 100)

    print(f'Fetching historical data')
    self.prod_data = asyncio.run(self.get_prod_data(
        list_pair=list_pair,
        interval='1m',
        nb_candles=100,
        current_state=None
    ))

    _verify_open_times(self.prod_data)

    idx = 0
    while idx < 10:

        if datetime.now().second == 0:
            print('Update all data')
            t0 = time.time()
            self.prod_data = asyncio.run(self.get_prod_data(
                list_pair=list_pair,
                interval='1m',
                nb_candles=100,
                current_state=self.prod_data.copy()
            ))
            print(f'Updated data in {round(time.time() - t0, 2)}s')

            _verify_open_times(self.prod_data)

            idx += 1

