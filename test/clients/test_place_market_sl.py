from nova.clients.clients import clients
from decouple import config


def asserts_place_market_sl(exchange: str, pair: str, side: str, quantity: float):

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

    exit_side = 'SELL' if side == 'BUY' else 'BUY'

    if exit_side == 'SELL':
        sl_price = market_order['executed_price'] * 0.9
    else:
        sl_price = market_order['executed_price'] * 1.1

    sl_data = client.place_market_sl(
        pair=pair,
        side=exit_side,
        quantity=quantity,
        sl_prc=sl_price
    )

    nb_decimals = len(str(sl_data['stop_price']).split(".")[1])

    assert sl_data['type'] == 'STOP_MARKET'
    assert sl_data['status'] == 'NEW'
    assert sl_data['pair'] == pair
    assert sl_data['reduce_only']
    assert sl_data['side'] == exit_side
    assert sl_data['original_quantity'] == quantity
    assert sl_data['executed_quantity'] == 0
    assert sl_data['stop_price'] == round(sl_price, nb_decimals)

    print(sl_data)

    print(f"Test place_market_sl for {exchange.upper()} successful")


def test_place_maket_sl():
    all_tests = [
        {
            'exchange': 'binance',
            'pair': 'BTCUSDT',
            'side': 'BUY',
            'quantity': 0.01
        }
    ]

    for _test in all_tests:
        asserts_place_market_sl(
            exchange=_test['exchange'],
            pair=_test['pair'],
            side=_test['side'],
            quantity=_test['quantity']
        )


test_place_maket_sl()
