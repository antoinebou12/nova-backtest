from nova.clients.clients import clients
from decouple import config
import time

STD_ORDER_OUTPUT = ['time', 'order_id', 'pair', 'status', 'type', 'time_in_force', 'reduce_only', 'side',
                    'price', 'original_quantity', 'executed_quantity', 'executed_price']


def asserts_get_order(exchange: str, pair: str, type_pos: str, quantity: float):

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

    # Enter Position with Market Order
    market_order = client.enter_market_order(
        pair=pair,
        type_pos=type_pos,
        quantity=quantity
    )

    exit_side = 'SELL' if type_pos == 'LONG' else 'BUY'

    upper = client.get_last_price(pair=pair)['latest_price'] * 1.1
    lower = client.get_last_price(pair=pair)['latest_price'] * 0.9

    sl_price = lower if type_pos == 'LONG' else upper
    tp_price = upper if type_pos == 'LONG' else lower

    # Place TP order
    tp_data = client.place_limit_tp(
        pair=pair,
        side=exit_side,
        quantity=quantity,
        tp_price=tp_price
    )

    # Place SL order
    sl_data = client.place_market_sl(
        pair=pair,
        side=exit_side,
        quantity=quantity,
        sl_price=sl_price
    )

    side = 'BUY' if type_pos == 'LONG' else 'SELL'
    exit_side = 'SELL' if type_pos == 'LONG' else 'BUY'

    # make sure that all outputs have exactly a standardized format
    assert set(STD_ORDER_OUTPUT).issubset(list(market_order.keys()))
    assert set(STD_ORDER_OUTPUT).issubset(list(tp_data.keys()))
    assert set(STD_ORDER_OUTPUT).issubset(list(sl_data.keys()))

    # get price
    latest_price = client.get_last_price(pair)['latest_price']

    p_precision = client.pairs_info[pair]['pricePrecision']
    q_precision = client.pairs_info[pair]['quantityPrecision']
    min_quantity = client.pairs_info[pair]['minQuantity']

    # Verify Market (EXECUTED)
    test_order = client.get_order(pair, market_order['order_id'])

    assert test_order['type'] == 'MARKET'
    assert test_order['status'] == 'FILLED'
    assert test_order['pair'] == pair
    assert not test_order['reduce_only']
    assert test_order['time_in_force'] in ['GTC', 'ImmediateOrCancel']
    assert test_order['side'] == side
    assert test_order['price'] == 0
    assert test_order['stop_price'] == 0
    assert test_order['original_quantity'] == round(quantity, q_precision)
    assert test_order['executed_quantity'] == round(quantity, q_precision)
    assert latest_price * 0.995 < test_order['executed_price'] < latest_price * 1.05

    # Verify TP (NOT EXECUTED)
    test_order = client.get_order(pair, tp_data['order_id'])

    assert test_order['type'] == 'TAKE_PROFIT'
    assert test_order['status'] in ['NEW', 'UNTRIGGERED']
    assert test_order['pair'] == pair
    assert test_order['reduce_only']
    assert test_order['side'] == exit_side
    assert test_order['price'] == 0
    assert round(tp_price*0.9999, p_precision) < test_order['stop_price'] < round(tp_price*1.0001, p_precision)
    assert test_order['original_quantity'] == round(quantity, q_precision)
    assert test_order['executed_quantity'] == 0
    assert test_order['executed_price'] == 0

    # Verify SL (NOT EXECUTED)
    test_order = client.get_order(pair, sl_data['order_id'])

    assert test_order['type'] == 'STOP_MARKET'
    assert test_order['status'] in ['NEW', 'UNTRIGGERED']
    assert test_order['pair'] == pair
    assert test_order['reduce_only']
    assert test_order['side'] == exit_side
    assert test_order['price'] == 0
    assert round(sl_price*0.9999, p_precision) < test_order['stop_price'] < round(sl_price*1.0001, p_precision)
    assert test_order['original_quantity'] == round(quantity, q_precision)
    assert test_order['executed_quantity'] == 0
    assert test_order['executed_price'] == 0

    # Exit position Limit
    residual_size, all_limit_orders = client._looping_limit_orders(
        pair=pair,
        side=exit_side,
        quantity=quantity,
        reduce_only=True,
        duration=3600 # Run until it executes
    )

    assert residual_size < min_quantity
    assert len(all_limit_orders) >= 1

    for order in all_limit_orders:
        assert order['type'] == 'LIMIT'
        assert order['status'] in ['CANCELED', 'CANCELLED', 'FILLED', 'PARTIALLY_FILLED']
        assert order['pair'] == pair
        assert order['reduce_only']
        assert order['side'] == exit_side
        assert latest_price * 0.95 < order['price'] < latest_price * 1.05
        assert order['stop_price'] == 0
        assert order['original_quantity'] == round(quantity, q_precision)
        assert 0 <= order['executed_quantity'] <= round(quantity, q_precision)
        assert order['executed_price'] in [0, order['price']]

    client.cancel_order(pair=pair, order_id=sl_data['order_id'])
    client.cancel_order(pair=pair, order_id=tp_data['order_id'])

    print(f"Test get_order {type_pos} for {exchange.upper()} successful")


def test_get_order():
    all_tests = [
        # {
        #     'exchange': 'binance',
        #     'pair': 'BTCUSDT',
        #     'type_pos': 'LONG',
        #     'quantity': 0.01
        # },
        # {
        #     'exchange': 'binance',
        #     'pair': 'BTCUSDT',
        #     'type_pos': 'SHORT',
        #     'quantity': 0.01
        # },
        {
            'exchange': 'bybit',
            'pair': 'BTCUSDT',
            'type_pos': 'LONG',
            'quantity': 0.1
        },
        {
            'exchange': 'bybit',
            'pair': 'BTCUSDT',
            'type_pos': 'SHORT',
            'quantity': 0.1
        }
    ]

    for _test in all_tests:
        asserts_get_order(
            exchange=_test['exchange'],
            pair=_test['pair'],
            type_pos=_test['type_pos'],
            quantity=_test['quantity']
        )


test_get_order()

