from nova.clients.clients import clients
from decouple import config
import time


def asserts_enter_limit_then_market(exchange: str,
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

    keys_expected = ['pair', 'position_type', 'original_position_size', 'current_position_size', 'entry_time', 'tp_id',
                     'tp_price', 'sl_id', 'sl_price', 'trade_status', 'entry_fees', 'last_tp_executed', 'exit_time',
                     'exit_fees', 'exit_price', 'quantity_exited', 'total_fees', 'realized_pnl']

    time.sleep(1)

    for var in keys_expected:
        assert var in list(entry_orders.keys())

    assert entry_orders['original_position_size'] == quantity
    assert entry_orders['trade_status'] == 'ACTIVE'
    assert entry_orders['quantity_exited'] == 0
    assert entry_orders['exit_fees'] == 0
    assert entry_orders['exit_time'] == 0
    assert entry_orders['exit_price'] == 0
    assert entry_orders['entry_fees'] > 0
    assert entry_orders['entry_price'] > 0
    assert entry_orders['position_type'] == type_pos

    for var in ['tp_id', 'sl_id']:
        client.cancel_order(
            pair=pair,
            order_id=entry_orders[var]
        )

    client.exit_market_order(
        pair=pair,
        type_pos=type_pos,
        quantity=quantity
    )

    print(f"Test enter_limit_then_market for {exchange.upper()} successful")


def test_enter_limit_then_market():

    all_tests = [
        # {
        #     'exchange': 'binance',
        #     'pair': 'XRPUSDT',
        #     'type_pos': 'LONG',
        #     'quantity': 200,
        # },
        {
            'exchange': 'bybit',
            'pair': 'ETHUSDT',
            'type_pos': 'LONG',
            'quantity': 1,
        }
    ]

    for _test in all_tests:

        asserts_enter_limit_then_market(
            exchange=_test['exchange'],
            pair=_test['pair'],
            type_pos=_test['type_pos'],
            quantity=_test['quantity'],

        )


# test_enter_limit_then_market()



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



