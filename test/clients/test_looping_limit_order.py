from nova.clients.clients import clients
from decouple import config


def asserts_looping_limit_order(
    exchange: str,
    pair: str,
    side: str,
    quantity: float,
    reduce_only: bool,
    type_pos: str
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

    while residual == quantity:

        print(f'Current Residual ({residual})')
        residual, all_orders = client._looping_limit_orders(
            pair=pair,
            side=side,
            quantity=quantity,
            reduce_only=reduce_only,
            duration=60
        )

    assert residual >= 0
    assert isinstance(all_orders, list)

    _quantity = 0

    for order in all_orders:
        assert order['type'] == 'LIMIT'
        assert order['time_in_force'] in ['GTX', 'PostOnly']
        _quantity += order['executed_quantity']

    assert 0 < _quantity <= quantity
    client.exit_market_order(pair=pair, quantity=quantity, type_pos=type_pos)

    print(f"Test _looping_limit_order for {exchange.upper()} successful")


def test_looping_limit_order():
    all_tests = [
        # {
        #     'exchange': 'binance',
        #     'pair': 'BTCUSDT',
        #     'side': 'BUY',
        #     'quantity': 0.01,
        #     'reduce_only': False,
        #     'type_pos': 'LONG'
        # },
        {
            'exchange': 'bybit',
            'pair': 'BTCUSDT',
            'side': 'BUY',
            'quantity': 0.5,
            'reduce_only': False,
            'type_pos': 'LONG'
        }
    ]

    for _test in all_tests:
        asserts_looping_limit_order(
            exchange=_test['exchange'],
            pair=_test['pair'],
            side=_test['side'],
            quantity=_test['quantity'],
            reduce_only=_test['reduce_only'],
            type_pos=_test['type_pos']

        )


# test_looping_limit_order()



exchange = 'ftx'

client = clients(
    exchange=exchange,
    key=config(f"{exchange}TestAPIKey"),
    secret=config(f"{exchange}TestAPISecret"),
    testnet=True
)

residual, all_orders = client._looping_limit_orders(
    pair='BTC-PERP',
    side='BUY',
    quantity=0.001,
    reduce_only=False,
    duration=60
)

