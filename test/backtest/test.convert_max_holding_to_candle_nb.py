from nova.utils.strategy import Test
from decouple import config


def test_convert_max_holding_to_candle() -> None:

    all_tests = [
        {'candle': '15m', 'max_holding': 15, 'result': 60},
        {'candle': '30m', 'max_holding': 10, 'result': 20},
        {'candle': '1h', 'max_holding': 10, 'result': 10},
        {'candle': '3h', 'max_holding': 10, 'result': 3},
    ]

    for _test in all_tests:

        strategy = Test(
            exchange='binance',
            key=config('binanceAPIKey'),
            secret=config('binanceAPISecret'),
            candle=_test['candle'],
            max_holding=_test['max_holding']
        )

        nb_candle = strategy._convert_max_holding_to_candle_nb()

        assert nb_candle == _test['result']

        print('Success')

