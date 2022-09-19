from nova.clients.clients import clients
from decouple import config
import time


def asserts_enter_limit_then_market(exchange: str, entry_args: list):

    client = clients(
        exchange=exchange,
        key=config(f"{exchange}TestAPIKey"),
        secret=config(f"{exchange}TestAPISecret"),
        testnet=True
    )

    for args in entry_args:

        upper = client.get_last_price(pair=args['pair'])['latest_price'] * 1.1
        lower = client.get_last_price(pair=args['pair'])['latest_price'] * 0.9

        args['sl_price'] = lower if args['side'] == 'BUY' else upper
        args['tp_price'] = upper if args['side'] == 'BUY' else lower
        args['pos_type'] = 'LONG' if args['side'] == 'BUY' else 'SHORT'

        entry_orders = client._enter_limit_then_market(
            pair=args['pair'],
            type_pos=args['pos_type'],
            quantity=args['quantity'],
            sl_price=args['sl_price'],
            tp_price=args['tp_price'],
            return_dict={}
        )

        time.sleep(20)


def test_enter_limit_then_market():

    all_tests = [
        {
            'exchange': 'binance',
            'entry_args': [
                {
                    'pair': 'BTCUSDT',
                    'side': 'BUY',
                    'quantity': 0.01,
                },
                # {
                #     'pair': 'ETHUSDT',
                #     'side': 'SELL',
                #     'quantity': 0.1,
                # }
            ]
        }
    ]

    for _test in all_tests:

        asserts_enter_limit_then_market(
            exchange=_test['exchange'],
            entry_args=_test['entry_args']
        )


test_enter_limit_then_market()