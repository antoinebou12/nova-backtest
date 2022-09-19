from nova.clients.clients import clients
from decouple import config
import time


def assert_get_tp_sl_state(exchange: str,
                           pair: str,
                           side: str,
                           quantity: float):

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
                side=_info['exit_side'],
                quantity=_info['position_size']
            )

    exit_side = 'SELL' if side == "BUY" else "BUY"

    market_order = client.enter_market_order(
        pair=pair,
        side=side,
        quantity=quantity
    )

    upper = client.get_last_price(pair=pair)['latest_price'] * 1.01
    lower = client.get_last_price(pair=pair)['latest_price'] * 0.99

    sl_price = lower if side == 'BUY' else upper
    tp_price = upper if side == 'BUY' else lower

    tp_order = client.place_limit_tp(
        pair=pair,
        side=exit_side,
        quantity=quantity,
        tp_price=tp_price
    )

    sl_order = client.place_market_sl(
        pair=pair,
        side=exit_side,
        quantity=quantity,
        sl_prc=sl_price
    )

    time.sleep(20)

    _update = client.get_tp_sl_state(
        pair=pair,
        tp_id=tp_order['order_id'],
        sl_id=sl_order['order_id']
    )

    print(_update)


def test_get_tp_sl_state():

    all_tests = [
        {
            'exchange': 'binance',
            'pair': 'BTCUSDT',
            'side': 'BUY',
            'quantity': 0.01
        }
    ]

    for _test in all_tests:

        assert_get_tp_sl_state(
            exchange=_test['exchange'],
            pair=_test['pair'],
            side=_test['side'],
            quantity=_test['quantity'],
        )
