from nova.clients.clients import clients
from decouple import config


def asserts_place_market_sl(exchange: str, pair: str, type_pos: str, quantity: float):

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

    market_order = client.enter_market_order(
        pair=pair,
        type_pos=type_pos,
        quantity=quantity
    )

    exit_side = 'SELL' if type_pos == 'LONG' else 'BUY'

    if exit_side == 'SELL':
        sl_price = market_order['executed_price'] * 0.9
    else:
        sl_price = market_order['executed_price'] * 1.1

    sl_data = client.place_market_sl(
        pair=pair,
        side=exit_side,
        quantity=quantity,
        sl_price=sl_price
    )

    assert sl_data['type'] == 'STOP_MARKET'
    assert sl_data['status'] in ['NEW', 'UNTRIGGERED']
    assert sl_data['pair'] == pair
    assert sl_data['reduce_only']
    assert sl_data['side'] == exit_side
    assert sl_data['original_quantity'] == quantity
    assert sl_data['executed_quantity'] == 0
    assert sl_data['stop_price'] > 0

    client.exit_market_order(
        pair=pair,
        type_pos=type_pos,
        quantity=quantity
    )

    client.cancel_order(pair=pair, order_id=sl_data['order_id'])

    print(f"Test place_market_sl for {exchange.upper()} successful")


def test_place_market_sl():
    all_tests = [
        # {
        #     'exchange': 'binance',
        #     'pair': 'BTCUSDT',
        #     'type_pos': 'LONG',
        #     'quantity': 0.01
        # },
        {
            'exchange': 'bybit',
            'pair': 'BTCUSDT',
            'type_pos': 'LONG',
            'quantity': 0.01
        }
    ]

    for _test in all_tests:
        asserts_place_market_sl(
            exchange=_test['exchange'],
            pair=_test['pair'],
            type_pos=_test['type_pos'],
            quantity=_test['quantity']
        )


test_place_market_sl()