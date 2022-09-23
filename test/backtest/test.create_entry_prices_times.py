from datetime import datetime
from nova.utils.strategy import Test
from decouple import config


def test_create_entry_prices_times() -> None:

    all_tests = [
        {'exchange': 'binance', 'pair': 'BTCUSDT', 'update': False},
        {'exchange': 'binance', 'pair': 'BTCUSDT', 'update': True},
    ]

    for _test in all_tests:

        strategy = Test(
            exchange=_test['exchange'],
            key=config(f'{_test["exchange"]}APIKey'),
            secret=config(f'{_test["exchange"]}APISecret'),
            start=datetime(2022, 1, 1),
            end=datetime(2022, 4, 10),
            candle='4h'
        )

