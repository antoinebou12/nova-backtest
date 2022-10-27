from nova.clients.clients import clients
from decouple import config
import time


def asserts_place_limit_tp(exchange: str, pair: str, type_pos: str, quantity: float):

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
        tp_price = market_order['executed_price'] * 1.1
    else:
        tp_price = market_order['executed_price'] * 0.9

    tp_data = client.place_limit_tp(
        pair=pair,
        side=exit_side,
        quantity=quantity,
        tp_price=tp_price
    )

    p_precision = client.pairs_info[pair]['pricePrecision']
    q_precision = client.pairs_info[pair]['quantityPrecision']

    assert tp_data['type'] == 'TAKE_PROFIT'
    assert tp_data['status'] in ['NEW', 'UNTRIGGERED']
    assert tp_data['pair'] == pair
    assert tp_data['reduce_only']
    assert tp_data['side'] == exit_side
    assert tp_data['price'] == 0
    assert round(tp_price * 0.9999, p_precision) < tp_data['stop_price'] < round(tp_price * 1.0001, p_precision)
    assert tp_data['original_quantity'] == round(quantity, q_precision)
    assert tp_data['executed_quantity'] == 0
    assert tp_data['executed_price'] == 0

    time.sleep(1)

    client.cancel_order(pair=pair, order_id=tp_data['order_id'])

    client.exit_market_order(
        pair=pair,
        type_pos=type_pos,
        quantity=quantity
    )

    print(f"Test place_limit_tp for {exchange.upper()} successful")


def test_place_limit_tp():
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
            'quantity': 0.1
        }
    ]

    for _test in all_tests:
        asserts_place_limit_tp(
            exchange=_test['exchange'],
            pair=_test['pair'],
            type_pos=_test['type_pos'],
            quantity=_test['quantity']
        )


# test_place_limit_tp()


exchange = 'ftx'

client = clients(
    exchange=exchange,
    key=config(f"{exchange}TestAPIKey"),
    secret=config(f"{exchange}TestAPISecret"),
    testnet=True
)

# market_data = client.enter_market_order(
#     pair="ETH-PERP",
#     type_pos="LONG",
#     quantity=0.01
# )


tp_data = client.place_limit_tp(
    pair="ETH-PERP",
    side="SELL",
    quantity=0.01,
    tp_price=1650
)

# tp_data_executed = client.place_limit_tp(
#     pair="ETH-PERP",
#     side="SELL",
#     quantity=0.01,
#     tp_price=1571
# )


order_tp_ex = client.get_order(pair="ETH-PERP", order_id=323380952)



