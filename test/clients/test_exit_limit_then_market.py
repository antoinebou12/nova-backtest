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

    upper = client.get_last_price(pair=pair)['latest_price'] * 1.1
    lower = client.get_last_price(pair=pair)['latest_price'] * 0.9

    sl_price = lower if type_pos == 'LONG' else upper
    tp_price = upper if type_pos == 'LONG' else lower

    entry_orders = client._enter_limit_then_market(
        pair=pair,
        type_pos=type_pos,
        quantity=quantity,
        sl_price=sl_price,
        tp_price=tp_price,
    )

    time.sleep(1)

    state_tp = client.get_order_trades(pair=pair, order_id=entry_orders['tp_id'])

    # exiting the position
    exit_orders = client._exit_limit_then_market(
        pair=pair,
        type_pos=type_pos,
        quantity=quantity,
        tp_time=state_tp['time'],
        tp_id=entry_orders['tp_id'],
        sl_id=entry_orders['sl_id']
    )

    time.sleep(1)

    keys_expected = ['pair', 'executed_quantity', 'time', 'exit_fees', 'trade_status', 'exit_price']

    for var in keys_expected:

        assert var in list(exit_orders.keys())

    # assert exit_orders['last_exit_time'] < int(time.time() * 1000)
    assert exit_orders['exit_fees'] > 0
    assert exit_orders['exit_price'] > 0

    for var in ['tp_id', 'sl_id']:
        client.cancel_order(
            pair=pair,
            order_id=entry_orders[var]
        )

    print(f"Test exit_limit_then_market for {exchange.upper()} successful")


def test_exit_limit_then_market():

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
            'quantity': 0.01,
        }
    ]

    for _test in all_tests:

        asserts_exit_limit_then_market(
            exchange=_test['exchange'],
            pair=_test['pair'],
            type_pos=_test['type_pos'],
            quantity=_test['quantity'],

        )


# test_exit_limit_then_market()



exchange = 'ftx'

client = clients(
    exchange=exchange,
    key=config(f"{exchange}TestAPIKey"),
    secret=config(f"{exchange}TestAPISecret"),
    testnet=True
)

pair = 'ETH-PERP'
type_pos = "LONG"
quantity = 0.01

upper = client.get_last_price(pair=pair)['latest_price'] * 1.1
lower = client.get_last_price(pair=pair)['latest_price'] * 0.9

sl_price = lower if type_pos == 'LONG' else upper
tp_price = upper if type_pos == 'LONG' else lower

entry_orders = client._enter_limit_then_market(
    pair=pair,
    type_pos=type_pos,
    quantity=quantity,
    sl_price=sl_price,
    tp_price=tp_price,
)

state_tp = client.get_order_trades(pair=pair, order_id=entry_orders['tp_id'])

# exiting the position
exit_orders = client._exit_limit_then_market(
    pair=pair,
    type_pos=type_pos,
    quantity=quantity,
    tp_time=state_tp['time'],
    tp_id=entry_orders['tp_id'],
    sl_id=entry_orders['sl_id']
)



