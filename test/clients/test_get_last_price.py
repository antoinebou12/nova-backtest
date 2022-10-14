from nova.clients.clients import clients
from decouple import config
import time


def asserts_get_last_price(
    exchange: str,
    pair: str,
):
    start_time = int(time.time() * 1000)

    client = clients(
        exchange=exchange,
        key=config(f"{exchange}TestAPIKey"),
        secret=config(f"{exchange}TestAPISecret"),
        testnet=True
    )

    data = client.get_last_price(
        pair=pair,
    )

    assert isinstance(data, dict)
    assert data['pair'] == pair
    assert data['latest_price'] > 0

    print(f"Test get_last_price for {exchange.upper()} successful")


def test_get_last_price():
    all_tests = [
        {
            'exchange': 'binance',
            'pair': 'BTCUSDT',
        },
        # {
        #     'exchange': 'bybit',
        #     'pair': 'BTCUSDT'
        # }
    ]

    for _test in all_tests:
        asserts_get_last_price(
            exchange=_test['exchange'],
            pair=_test['pair']
        )


test_get_last_price()
