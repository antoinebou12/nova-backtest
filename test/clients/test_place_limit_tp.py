from nova.clients.clients import clients
from decouple import config


def asserts_place_limit_tp(exchange: str, pair: str, side: str, quantity: float):

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

    market_order = client.enter_market_order(
        pair=pair,
        side=side,
        quantity=quantity
    )

    exit_side = 'SELL' if side == 'BUY' else 'BUY'

    if exit_side == 'SELL':
        tp_price = market_order['executed_price'] * 1.1
    else:
        tp_price = market_order['executed_price'] * 0.9

    tp_data = client.place_limit_tp(
        pair=pair,
        side=exit_side,
        quantity=quantity,
        tp_prc=tp_price
    )

    nb_decimals = len(str(tp_data['stop_price']).split(".")[1])

    assert tp_data['type'] == 'TAKE_PROFIT'
    assert tp_data['status'] == 'NEW'
    assert tp_data['pair'] == pair
    assert tp_data['reduce_only']
    assert tp_data['side'] == exit_side
    assert tp_data['original_quantity'] == quantity
    assert tp_data['executed_quantity'] == 0
    assert tp_data['stop_price'] == round(tp_price, nb_decimals)

    print(f"Test place_limit_tp for {exchange.upper()} successful")


def test_place_limit_tp():
    all_tests = [
        {
            'exchange': 'binance',
            'pair': 'BTCUSDT',
            'side': 'BUY',
            'quantity': 0.01
        }
    ]

    for _test in all_tests:
        asserts_place_limit_tp(
            exchange=_test['exchange'],
            pair=_test['pair'],
            side=_test['side'],
            quantity=_test['quantity']
        )


test_place_limit_tp()
