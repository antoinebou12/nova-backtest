from datetime import datetime
from nova.utils.strategy import Test
from decouple import config
import os
import pandas as pd


def test_data_already_saved_locally() -> None:

    start_date = datetime(2022, 1, 1)
    end_date = datetime(2022, 4, 10)

    _candle = '1d'

    all_tests = [
        {'exchange': 'binance', 'pair': 'BTCUSDT', 'update': False},
        {'exchange': 'binance', 'pair': 'BTCUSDT', 'update': True},
    ]

    for _test in all_tests:

        if f'hist_{_test["pair"]}_{_candle}.csv' in os.listdir(f'{os.getcwd()}/database/{_test["exchange"]}'):
            print(f'Removing hist_{_test["pair"]}_{_candle}.csv from {_test["exchange"]}')
            os.remove(f'{os.getcwd()}/database/{_test["exchange"]}/hist_{_test["pair"]}_{_candle}.csv')

        strategy = Test(
            exchange=_test['exchange'],
            key=config(f'{_test["exchange"]}APIKey'),
            secret=config(f'{_test["exchange"]}APISecret'),
            start=start_date,
            end=end_date,
            candle=_candle,
            update_data=_test['update']
        )

        strategy.get_all_historical_data(
            pair=_test['pair']
        )

        data = strategy.get_all_historical_data(
            pair=_test['pair']
        )

        assert data['open_time'].min() >= strategy.start & data['open_time'].min() <= strategy.start + (3600000 * 24)
        assert list(data.columns) == ['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'next_open']

        data['time_dif'] = data['open_time'] - data['open_time'].shift(1)
        assert data['time_dif'].mean() == 24 * 3600 * 1000

        if _test['update']:
            print('Testing Update')
            nb_days = (datetime.now() - start_date).days - 2
            assert data['close_time'].max() >= int(datetime.now().timestamp() * 1000) - 2 * (3600000 * 24)
            assert nb_days == len(data)

        else:
            print('Testing No Update')
            nb_days = (end_date - start_date).days - 1
            assert data['close_time'].max() <= strategy.end
            assert data['open_time'].max() >= strategy.end - 2 * (3600000 * 24)

            assert nb_days == len(data)


def test_data_not_saved_yet() -> None:

    start_date = datetime(2021, 1, 1)
    end_date = datetime(2022, 4, 10)

    _candle = '1d'

    all_tests = [
        {'exchange': 'binance', 'pair': 'BTCUSDT', 'result': 'minus'},
        {'exchange': 'binance', 'pair': 'APEUSDT', 'result': 'plus'},
    ]

    for _test in all_tests:

        strategy = Test(
            exchange=_test['exchange'],
            key=config(f'{_test["exchange"]}APIKey'),
            secret=config(f'{_test["exchange"]}APISecret'),
            start=start_date,
            end=end_date,
            candle=_candle,
        )

        if f'hist_{_test["pair"]}_{_candle}.csv' in os.listdir(f'{os.getcwd()}/database/{_test["exchange"]}'):
            print(f'Removing hist_{_test["pair"]}_{_candle}.csv from {_test["exchange"]}')
            os.remove(f'{os.getcwd()}/database/{_test["exchange"]}/hist_{_test["pair"]}_{_candle}.csv')

        strategy.get_all_historical_data(
            pair=_test['pair']
        )

        assert f'hist_{_test["pair"]}_{_candle}.csv' in os.listdir(f'{os.getcwd()}/database/{_test["exchange"]}')

        df = pd.read_csv(f'database/{_test["exchange"]}/hist_{_test["pair"]}_{_candle}.csv')

        if _test['result'] == 'minus':
            assert df['open_time'].min() <= strategy.start

        if _test['result'] == 'plus':
            assert df['open_time'].min() >= strategy.start


test_data_not_saved_yet()
