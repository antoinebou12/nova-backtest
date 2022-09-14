from nova.clients.clients import clients
from decouple import config


def asserts_enter_market_order(exchange: str, pair: str, side: str, quantity: float):

    client = clients(
        exchange=exchange,
        key=config(f"{exchange}TestAPIKey"),
        secret=config(f"{exchange}TestAPISecret"),
        testnet=True
    )

    positions = client.get_actual_positions(
        list_pair=[pair]
    )

    if len(positions) != 0:

        for _pair, _info in positions.items():

            client.exit_market_order(
                pair=_pair,
                side=_info['exit_side'],
                quantity=_info['position_size']
            )

    market_order = client.enter_market_order(
        pair=pair,
        side=side,
        quantity=quantity
    )

    assert market_order['type'] == 'MARKET'
    assert market_order['status'] == 'FILLED'
    assert market_order['pair'] == pair
    assert not market_order['reduce_only']
    assert market_order['side'] == side
    assert market_order['original_quantity'] == quantity
    assert market_order['executed_quantity'] == quantity

    print(f"Test enter_market_order for {exchange.upper()} successful")


def test_enter_market_order():

    all_tests = [
        {
            'exchange': 'binance',
            'pair': 'BTCUSDT',
            'side': 'BUY',
            'quantity': 0.01
        }
    ]

    for _test in all_tests:

        asserts_enter_market_order(
            exchange=_test['exchange'],
            pair=_test['pair'],
            side=_test['side'],
            quantity=_test['quantity']
        )


test_enter_market_order()



