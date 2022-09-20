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
            type_pos=_test['side'],
            quantity=_test['quantity'],

        )


test_enter_limit_then_market()