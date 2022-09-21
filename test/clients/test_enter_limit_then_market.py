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
        return_dict={}
    )

    keys_expected = ['pair', 'position_type', 'original_position_size', 'current_position_size', 'entry_time', 'tp_id',
                     'tp_price', 'sl_id', 'sl_price', 'trade_status', 'quantity_exited', 'exit_fees',
                     'last_exit_time', 'exit_price', 'entry_fees']

    time.sleep(1)

    for var in keys_expected:
        assert var in list(entry_orders.keys())

    nb_decimals = len(str(entry_orders['tp_price']).split(".")[1])

    assert entry_orders['entry_time'] < int(time.time() * 1000)
    assert entry_orders['original_position_size'] == quantity
    assert entry_orders['tp_price'] == round(tp_price, nb_decimals)
    assert entry_orders['sl_price'] == round(sl_price, nb_decimals)
    assert entry_orders['trade_status'] == 'ACTIVE'
    assert entry_orders['quantity_exited'] == 0
    assert entry_orders['exit_fees'] == 0
    assert entry_orders['last_exit_time'] == 0
    assert entry_orders['exit_price'] == 0
    assert entry_orders['entry_fees'] > 0
    assert entry_orders['entry_price'] > 0


def test_enter_limit_then_market():

    all_tests = [
        {
            'exchange': 'binance',
            'pair': 'BTCUSDT',
            'type_pos': 'LONG',
            'quantity': 0.01,
        }
    ]

    for _test in all_tests:

        asserts_enter_limit_then_market(
            exchange=_test['exchange'],
            pair=_test['pair'],
            type_pos=_test['type_pos'],
            quantity=_test['quantity'],

        )


test_enter_limit_then_market()
