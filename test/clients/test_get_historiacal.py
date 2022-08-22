from nova.clients.clients import clients
from decouple import config
from datetime import datetime


def test_get_historical_correct_date():

    all_tests = [
        {'exchange': 'binance', 'interval': '1d', 'pair': 'ETHUSDT'},
    ]

    for _test in all_tests:

        client = clients(
            exchange=_test["exchange"],
            key=config(f"{_test['exchange']}APIKey"),
            secret=config(f"{_test['exchange']}APISecret"),
        )

        start = int(datetime(2022, 1, 1).timestamp() * 1000)
        end = int(datetime(2022, 4, 10).timestamp() * 1000)

        df = client.get_historical(
            pair=_test['pair'],
            interval=_test['interval'],
            start_time=start,
            end_time=end
        )

        candle = client._get_candles(
            pair=_test['pair'],
            interval=_test['interval'],
            start_time=start,
            end_time=end
        )

        return df, candle


_df, _candle = test_get_historical_correct_date()










