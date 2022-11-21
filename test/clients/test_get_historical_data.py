from nova.clients.clients import clients
from nova.utils.helpers import interval_to_milliseconds

from decouple import config
from datetime import datetime


def assert_get_historical_data(exchange: str, pair: str, interval: str, start_ts: int, end_ts: int):

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

    df['open_time_difference'] = df['open_time'] - df['open_time'].shift(1)
    df['close_time_difference'] = df['close_time'] - df['close_time'].shift(1)

    assert df['open_time_difference'].max() == time_milli, 'Candle interval is wrong for open_time'
    assert df['close_time_difference'].max() == time_milli, 'Candle interval is wrong for close_time'

    assert df['open_time_difference'].max() == df['open_time_difference'].min(), 'Time series not respected'
    assert df['close_time_difference'].min() == df['close_time_difference'].max(), 'Time series not respected'

    assert df['open_time'].min() >= real_start
    assert df['open_time'].max() <= end_ts

    print(f"Test _get_historical_data for {exchange.upper()} successful")


def test_get_historical_data():

    all_tests = [
        {'exchange': 'binance',
         'interval': '4h',
         'pair': 'ETHUSDT',
         'start_ts': int(datetime(2018, 1, 1).timestamp() * 1000),
         'end_ts': int(datetime(2022, 4, 10).timestamp() * 1000),
         'can_historical': True
         },
        {'exchange': 'bybit',
         'interval': '4h',
         'pair': 'BTCUSDT',
         'start_ts': int(datetime(2018, 1, 1).timestamp() * 1000),
         'end_ts': int(datetime(2022, 4, 10).timestamp() * 1000),
         'can_historical': True
         },
        {'exchange': 'ftx',
         'interval': '4h',
         'pair': 'BTC-PERP',
         'start_ts': int(datetime(2020, 3, 20).timestamp() * 1000),
         'end_ts': int(datetime(2022, 4, 10).timestamp() * 1000),
         'can_historical': True
         },
        {'exchange': 'okx',
         'interval': '1h',
         'pair': 'BTC-USDT',
         'start_ts': int(datetime(2022, 1, 1).timestamp() * 1000),
         'end_ts': int(datetime.today().timestamp() * 1000),
         'can_historical': True
         },
        {'exchange': 'kucoin',
         'interval': '1h',
         'pair': 'XBTUSDTM',
         'start_ts': int(datetime(2022, 1, 1).timestamp() * 1000),
         'end_ts': int(datetime.today().timestamp() * 1000),
         'can_historical': False
         },
    ]

    for _test in all_tests:

        assert_get_historical_data(
            exchange=_test['exchange'],
            interval=_test['interval'],
            pair=_test['pair'],
            start_ts=_test['start_ts'],
            end_ts=_test['end_ts'],
        )


test_get_historical_data()
