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

    assert df['open_time_difference'].max() == df['open_time_difference'].min()
    assert df['close_time_difference'].min() == df['close_time_difference'].max()

    # assert df['open_time'].min() < real_start + time_milli
    assert df['open_time'].min() >= real_start

    assert df['open_time'].max() <= end_ts
    # assert df['close_time'].max() < end_ts + time_milli

    print(f"Test _get_historical_data for {exchange.upper()} successful")


def test_get_historical_data():

    all_tests = [
        # {'exchange': 'binance',
        #  'interval': '4h',
        #  'pair': 'ETHUSDT',
        #  'start_ts': int(datetime(2018, 1, 1).timestamp() * 1000),
        #  'end_ts': int(datetime(2022, 4, 10).timestamp() * 1000)
        #  },
        # {'exchange': 'bybit',
        #  'interval': '4h',
        #  'pair': 'BTCUSDT',
        #  'start_ts': int(datetime(2018, 1, 1).timestamp() * 1000),
        #  'end_ts': int(datetime(2022, 4, 10).timestamp() * 1000)
        #  },
        # {'exchange': 'ftx',
        #  'interval': '4h',
        #  'pair': 'BTC-PERP',
        #  'start_ts': int(datetime(2020, 3, 20).timestamp() * 1000),
        #  'end_ts': int(datetime(2022, 4, 10).timestamp() * 1000)
        #  },
        # {'exchange': 'coinbase',
        #  'interval': '1h',
        #  'pair': 'BTC-USD',
        #  'start_ts': int(datetime(2022, 1, 1).timestamp() * 1000),
        #  'end_ts': int(datetime.today().timestamp() * 1000)
        #  },
        # {'exchange': 'okx',
        #  'interval': '1h',
        #  'pair': 'BTC-USDT',
        #  'start_ts': int(datetime(2022, 1, 1).timestamp() * 1000),
        #  'end_ts': int(datetime.today().timestamp() * 1000)
        #  },
        {'exchange': 'kucoin',
         'interval': '1h',
         'pair': 'XBTUSDTM',
         'start_ts': int(datetime(2022, 1, 1).timestamp() * 1000),
         'end_ts': int(datetime.today().timestamp() * 1000)
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


# exchange = 'kucoin'
#
# client = clients(
#     exchange=exchange,
#     key=config(f"{exchange}TestAPIKey"),
#     secret=config(f"{exchange}TestAPISecret"),
# )
#
# df = client.get_historical_data(
#     pair='XBTUSDTM',
#     interval='1h',
#     start_ts=int(datetime(2022, 1, 1).timestamp() * 1000),
#     end_ts=int(datetime.today().timestamp() * 1000)
# )
#
# df['open_time_difference'] = df['open_time'] - df['open_time'].shift(1)
#
# df['open_time_difference'].max()
# df['open_time_difference'].min()
#
# df[df['open_time_difference'] == 10800000]