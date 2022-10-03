from nova.clients.clients import clients
from decouple import config
import time


def asserts_exit_limit_then_market(exchange: str,
                                   pair: str,
                                   type_pos: str,
                                   quantity: float
                                   ):

    client = clients(
        exchange=exchange,
        key=config(f"{exchange}TestAPIKey"),
        secret=config(f"{exchange}TestAPISecret"),
        testnet=True
    )

    positions = client.get_actual_positions(
        pairs=pair
    )

    if len(positions) != 0:

        for _pair, _info in positions.items():

            client.exit_market_order(
                pair=_pair,
                type_pos=_info['type_pos'],
                quantity=_info['position_size']
            )

    # entering in position
    client.enter_market_order(
        pair=pair,
        type_pos=type_pos,
        quantity=quantity,
    )

    time.sleep(1)

    # exiting the position
    exit_orders = client._exit_limit_then_market(
        pair=pair,
        type_pos=type_pos,
        quantity=quantity,
    )

    time.sleep(1)

    keys_expected = ['pair', 'executed_quantity', 'last_exit_time', 'exit_fees', 'exit_price']

    for var in keys_expected:

        assert var in list(exit_orders.keys())

    # assert exit_orders['last_exit_time'] < int(time.time() * 1000)
    assert exit_orders['exit_fees'] > 0
    assert exit_orders['exit_price'] > 0

    print(f"Test exit_limit_then_market for {exchange.upper()} successful")


def test_exit_limit_then_market():

    all_tests = [
        {
            'exchange': 'binance',
            'pair': 'BTCUSDT',
            'type_pos': 'LONG',
            'quantity': 0.01,
        },
        {
            'exchange': 'bybit',
            'pair': 'BTCUSDT',
            'type_pos': 'LONG',
            'quantity': 0.01,
        }
    ]

    for _test in all_tests:

        asserts_exit_limit_then_market(
            exchange=_test['exchange'],
            pair=_test['pair'],
            type_pos=_test['type_pos'],
            quantity=_test['quantity']

        )


test_exit_limit_then_market()
