from nova.clients.clients import clients
from decouple import config


def asserts_exit_market_order(exchange: str, pair: str, exit_side: str, quantity: float):

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

    entry_side = 'SELL' if exit_side == 'BUY' else 'BUY'

    market_enter = client.enter_market_order(
        pair=pair,
        side=entry_side,
        quantity=quantity
    )

    assert market_enter['type'] == 'MARKET'
    assert market_enter['status'] == 'FILLED'
    assert market_enter['original_quantity'] == quantity
    assert market_enter['executed_quantity'] == quantity
    assert market_enter['side'] == entry_side

    market_exit = client.exit_market_order(
        pair=pair,
        side=exit_side,
        quantity=quantity
    )

    assert market_exit['type'] == 'MARKET'
    assert market_exit['status'] == 'FILLED'
    assert market_exit['pair'] == pair
    assert market_exit['reduce_only']
    assert market_exit['side'] == exit_side
    assert market_exit['original_quantity'] == quantity
    assert market_exit['executed_quantity'] == quantity

    print(f"Test exit_market_order for {exchange.upper()} successful")


def test_exit_market_order():

    all_tests = [
        {
            'exchange': 'binance',
            'pair': 'BTCUSDT',
            'exit_side': 'BUY',
            'quantity': 0.01
        }
    ]

    for _test in all_tests:

        asserts_exit_market_order(
            exchange=_test['exchange'],
            pair=_test['pair'],
            exit_side=_test['exit_side'],
            quantity=_test['quantity']
        )


test_exit_market_order()

