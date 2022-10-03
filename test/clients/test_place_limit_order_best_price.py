from nova.clients.clients import clients
from decouple import config


def asserts_place_limit_order_best_price(
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

    is_posted, data = client.place_limit_order_best_price(
        pair=pair,
        side=side,
        quantity=quantity,
        reduce_only=reduce_only
    )

    assert is_posted
    assert data is not None

    print(f"Test place_limit_order_best_price for {exchange.upper()} successful")


def test_place_limit_order_best_price():
    all_tests = [
        {
            'exchange': 'binance',
            'pair': 'BTCUSDT',
            'side': 'BUY',
            'quantity': 0.01,
            'reduce_only': False
        },
        {
            'exchange': 'bybit',
            'pair': 'BTCUSDT',
            'side': 'BUY',
            'quantity': 0.01,
            'reduce_only': False
        }
    ]

    for _test in all_tests:
        asserts_place_limit_order_best_price(
            exchange=_test['exchange'],
            pair=_test['pair'],
            side=_test['side'],
            quantity=_test['quantity'],
            reduce_only=_test['reduce_only'],
        )


test_place_limit_order_best_price()
