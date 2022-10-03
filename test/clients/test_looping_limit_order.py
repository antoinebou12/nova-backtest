from nova.clients.clients import clients
from decouple import config


def asserts_looping_limit_order(
    exchange: str,
    pair: str,
    side: str,
    quantity: float,
    reduce_only: bool
):

    client = clients(
        exchange=exchange,
        key=config(f"{exchange}TestAPIKey"),
        secret=config(f"{exchange}TestAPISecret"),
        testnet=True
    )

    residual, all_orders = client._looping_limit_orders(
        pair=pair,
        side=side,
        quantity=quantity,
        reduce_only=reduce_only,
        duration=60
    )

    assert residual >= 0
    assert isinstance(all_orders, list)

    print(f"Test _looping_limit_order for {exchange.upper()} successful")


def test_looping_limit_order():
    all_tests = [
        # {
        #     'exchange': 'binance',
        #     'pair': 'BTCUSDT',
        #     'side': 'BUY',
        #     'quantity': 0.01,
        #     'reduce_only': False
        # },
        {
            'exchange': 'bybit',
            'pair': 'BTCUSDT',
            'side': 'BUY',
            'quantity': 0.01,
            'reduce_only': False
        }
    ]

    for _test in all_tests:
        asserts_looping_limit_order(
            exchange=_test['exchange'],
            pair=_test['pair'],
            side=_test['side'],
            quantity=_test['quantity'],
            reduce_only=_test['reduce_only'],
        )


test_looping_limit_order()
