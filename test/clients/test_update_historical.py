from nova.clients.clients import clients
from nova.utils.helpers import interval_to_milliseconds

from decouple import config
from datetime import datetime
import time


def asserts_update_historical(exchange: str, pair: str, interval: str, start_ts: int, end_ts: int):

        client = clients(
            exchange=exchange,
            key=config(f"{exchange}TestAPIKey"),
            secret=config(f"{exchange}TestAPISecret"),
        )

        earliest_start = client._get_earliest_timestamp(
            pair=pair,
            interval=interval
        )

        real_start = max(earliest_start, start_ts)

        time_milli = interval_to_milliseconds(interval=interval)

        df = client.get_historical_data(
            pair=pair,
            interval=interval,
            start_ts=real_start,
            end_ts=end_ts
        )

        up_df = client.update_historical(
            pair=pair,
            interval=interval,
            current_df=df
        )

        now_time = int(time.time() * 1000)

        up_df['open_time_difference'] = up_df['open_time'] - up_df['open_time'].shift(1)
        up_df['close_time_difference'] = up_df['close_time'] - up_df['close_time'].shift(1)

        assert up_df['open_time_difference'].min() == up_df['open_time_difference'].max()
        assert up_df['close_time_difference'].min() == up_df['close_time_difference'].max()

        # assert up_df['open_time'].min() < real_start + time_milli
        assert up_df['open_time'].min() >= real_start

        assert up_df['open_time'].max() <= now_time
        # assert up_df['close_time'].max() < now_time + time_milli

        print(f"Test update_historical for {exchange.upper()} successful")


def test_update_historical():

    all_tests = [
        # {'exchange': 'binance',
        #  'interval': '4h',
        #  'pair': 'BTCUSDT',
        #  'start_ts': int(datetime(2018, 1, 1).timestamp() * 1000),
        #  'end_ts': int(datetime(2022, 4, 10).timestamp() * 1000)
        #  },
        # {'exchange': 'bybit',
        #  'interval': '4h',
        #  'pair': 'ETHUSDT',
        #  'start_ts': int(datetime(2021, 1, 1).timestamp() * 1000),
        #  'end_ts': int(datetime(2022, 4, 10).timestamp() * 1000)
        #  },
        # {'exchange': 'ftx',
        #  'interval': '4h',
        #  'pair': 'ETH-PERP',
        #  'start_ts': int(datetime(2021, 1, 1).timestamp() * 1000),
        #  'end_ts': int(datetime(2022, 4, 10).timestamp() * 1000)
        #  },
        # {'exchange': 'okx',
        #  'interval': '1h',
        #  'pair': 'ETH-USDT',
        #  'start_ts': int(datetime(2021, 9, 1).timestamp() * 1000),
        #  'end_ts': int(datetime(2022, 4, 10).timestamp() * 1000)
        #  },
        {'exchange': 'kucoin',
         'interval': '1h',
         'pair': 'ETHUSDTM',
         'start_ts': int(datetime(2021, 9, 1).timestamp() * 1000),
         'end_ts': int(datetime.now().timestamp() * 1000)
         },
    ]

    for _test in all_tests:

        asserts_update_historical(
            exchange=_test['exchange'],
            interval=_test['interval'],
            pair=_test['pair'],
            start_ts=_test['start_ts'],
            end_ts=_test['end_ts'],
        )


test_update_historical()




