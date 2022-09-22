from nova.clients.clients import clients
from decouple import config
import time


def asserts_cancel_order(exchange: str, pair: str, type_pos: str, quantity: float):

    client = clients(
        exchange=exchange,
        key=config(f"{exchange}TestAPIKey"),
        secret=config(f"{exchange}TestAPISecret"),
        testnet=True
    )

    client.enter_market_order(
        pair=pair,
        type_pos=type_pos,
        quantity=quantity
    )

    exit_side = 'SELL' if type_pos == 'LONG' else 'BUY'

    upper = client.get_last_price(pair=pair)['latest_price'] * 1.1
    lower = client.get_last_price(pair=pair)['latest_price'] * 0.9

    tp_price = upper if type_pos == 'LONG' else lower

    tp_order = client.place_limit_tp(
        pair=pair,
        side=exit_side,
        quantity=quantity,
        tp_price=tp_price
    )

    time.sleep(1)

    tp = client.get_order(pair=pair, order_id=tp_order['order_id'])

    assert tp['status'] == 'NEW'

    cancel = client.cancel_order(
        pair=pair,
        order_id=tp_order['order_id']
    )

    assert isinstance(cancel, dict)
    assert cancel['status'] == 'CANCELED'

    print(f"Test cancel_order for {exchange.upper()} successful")


def test_cancel_order():

    all_tests = [
        {
            'exchange': 'binance',
            'pair': 'BTCUSDT',
            'type_pos': 'LONG',
            'quantity': 0.01
        }
    ]

    for _test in all_tests:
        asserts_cancel_order(
            exchange=_test['exchange'],
            pair=_test['pair'],
            type_pos=_test['type_pos'],
            quantity=_test['quantity']
        )


test_cancel_order()
