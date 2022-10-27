from nova.clients.clients import clients
from decouple import config
import time


def assert_get_tp_sl_state(exchange: str,
                           pair: str,
                           type_pos: str,
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
                type_pos=_info['type_pos'],
                quantity=_info['position_size']
            )

    exit_side = 'SELL' if type_pos == "LONG" else "BUY"

    client.enter_market_order(
        pair=pair,
        type_pos=type_pos,
        quantity=quantity
    )

    upper = client.get_last_price(pair=pair)['latest_price'] * 1.01
    lower = client.get_last_price(pair=pair)['latest_price'] * 0.99

    sl_price = lower if type_pos == 'LONG' else upper
    tp_price = upper if type_pos == 'LONG' else lower

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
        sl_price=sl_price
    )

    time.sleep(2)

    _update = client.get_tp_sl_state(
        pair=pair,
        tp_id=tp_order['order_id'],
        sl_id=sl_order['order_id']
    )

    for var in ['tp', 'sl']:
        assert var in list(_update.keys())

    assert _update['tp']['order_id'] == tp_order['order_id']
    assert _update['sl']['order_id'] == sl_order['order_id']

    client.exit_market_order(
        pair=pair,
        type_pos=type_pos,
        quantity=quantity
    )

    client.cancel_order(
        pair=pair,
        order_id=tp_order['order_id'],
    )

    client.cancel_order(
        pair=pair,
        order_id=sl_order['order_id'],
    )

    print(f"Test get_tp_sl_state for {exchange.upper()} successful")


def test_get_tp_sl_state():

    all_tests = [
        {
            'exchange': 'binance',
            'pair': 'BTCUSDT',
            'type_pos': 'LONG',
            'quantity': 0.01
        },
        # {
        #     'exchange': 'bybit',
        #     'pair': 'BTCUSDT',
        #     'type_pos': 'LONG',
        #     'quantity': 0.01
        # }
    ]

    for _test in all_tests:

        assert_get_tp_sl_state(
            exchange=_test['exchange'],
            pair=_test['pair'],
            type_pos=_test['type_pos'],
            quantity=_test['quantity'],
        )


# test_get_tp_sl_state()

exchange = 'ftx'

client = clients(
    exchange=exchange,
    key=config(f"{exchange}TestAPIKey"),
    secret=config(f"{exchange}TestAPISecret"),
    testnet=True
)


tp_data = client.place_limit_tp(
    pair="ETH-PERP",
    side="SELL",
    quantity=0.01,
    tp_price=1650
)


sl_data = client.place_market_sl(
    pair="ETH-PERP",
    side="SELL",
    quantity=0.01,
    sl_price=1400
)

tp_sl_state = client.get_tp_sl_state(
    pair="ETH-PERP",
    tp_id=tp_data['order_id'],
    sl_id=sl_data['order_id']
)

