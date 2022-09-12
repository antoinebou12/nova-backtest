from nova.clients.clients import clients
from nova.utils.helpers import interval_to_milliseconds

from decouple import config
from datetime import datetime
import time


def assert_update_historical(all_tests: list):

    for _test in all_tests:

        client = clients(
            exchange=_test["exchange"],
            key=config(f"{_test['exchange']}APIKey"),
            secret=config(f"{_test['exchange']}APISecret"),
        )

        earliest_start = client._get_earliest_timestamp(
            pair=_test["pair"],
            interval=_test['interval']
        )

        real_start = max(earliest_start, _test['start_ts'])

        time_milli = interval_to_milliseconds(interval=_test['interval'])

        df = client.get_historical_data(
            pair=_test['pair'],
            interval=_test['interval'],
            start_ts=real_start,
            end_ts=_test['end_ts']
        )

        up_df = client.update_historical(
            pair=_test['pair'],
            interval=_test['interval'],
            current_df=df
        )

        now_time = int(time.time() * 1000)

        up_df['open_time_difference'] = up_df['open_time'] - up_df['open_time'].shift(1)
        up_df['close_time_difference'] = up_df['close_time'] - up_df['close_time'].shift(1)

        assert up_df['open_time_difference'].min() == up_df['open_time_difference'].max()
        assert up_df['close_time_difference'].min() == up_df['close_time_difference'].max()

        assert up_df['open_time'].min() < real_start + time_milli
        assert up_df['open_time'].min() >= real_start

        assert up_df['open_time'].max() <= now_time
        assert up_df['close_time'].max() < now_time + time_milli

        print(f"Test update_historical for {_test['exchange'].upper()} successful")


def test_update_historical():

    all_tests = [
        {'exchange': 'binance',
         'interval': '4h',
         'pair': 'ETHUSDT',
         'start_ts': int(datetime(2021, 1, 1).timestamp() * 1000),
         'end_ts': int(datetime(2022, 4, 10).timestamp() * 1000)
         },
        {'exchange': 'binance',
         'interval': '4h',
         'pair': 'BTCUSDT',
         'start_ts': int(datetime(2018, 1, 1).timestamp() * 1000),
         'end_ts': int(datetime(2022, 4, 10).timestamp() * 1000)
         },
    ]

    assert_update_historical(all_tests)


test_update_historical()




