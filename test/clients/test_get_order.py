from nova.clients.clients import clients
from decouple import config
import time


def asserts_get_order(exchange: str, pair: str, side: str, quantity: float):

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

    time.sleep(2)

    order_data = client.get_order(
        pair=pair,
        order_id=market_order['order_id']
    )

    std_output = ['time', 'order_id', 'pair', 'status', 'type', 'time_in_force', 'reduce_only', 'side',
                  'price', 'original_quantity', 'executed_quantity', 'executed_price']

    assert set(std_output).issubset(list(order_data.keys()))
    assert order_data['type'] == 'MARKET'
    assert order_data['status'] == 'FILLED'
    assert order_data['pair'] == pair
    assert not order_data['reduce_only']
    assert order_data['side'] == side
    assert order_data['original_quantity'] == quantity
    assert order_data['executed_quantity'] == quantity

    print(f"Test get_order for {exchange.upper()} successful")


def test_get_order():
    all_tests = [
        {
            'exchange': 'binance',
            'pair': 'BTCUSDT',
            'side': 'BUY',
            'quantity': 0.01
        }
    ]

    for _test in all_tests:
        asserts_get_order(
            exchange=_test['exchange'],
            pair=_test['pair'],
            side=_test['side'],
            quantity=_test['quantity']
        )


test_get_order()

