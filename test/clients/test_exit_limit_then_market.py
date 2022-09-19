from nova.clients.clients import clients
from decouple import config
import time


def asserts_exit_limit_then_market(exchange: str, entry_args: list):

    client = clients(
        exchange=exchange,
        key=config(f"{exchange}TestAPIKey"),
        secret=config(f"{exchange}TestAPISecret"),
        testnet=True
    )

    client.change_position_mode(
        dual_position="false"
    )

    for args in entry_args:

        args['pos_type'] = 'LONG' if args['side'] == 'BUY' else 'SHORT'

        order = client.enter_market_order(
            pair=args['pair'],
            side=args['side'],
            quantity=args['quantity'],
        )

        time.sleep(1)

        exit_orders = client._exit_limit_then_market(
            pair=args['pair'],
            type_pos=args['pos_type'],
            quantity=args['quantity'],
            return_dict={}
        )

        print(exit_orders)


def test_exit_limit_then_market():

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

        asserts_exit_limit_then_market(
            exchange=_test['exchange'],
            entry_args=_test['entry_args']
        )


test_exit_limit_then_market()
