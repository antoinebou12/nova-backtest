from nova.clients.clients import clients
from decouple import config
from multiprocessing import set_start_method
set_start_method('fork')


def asserts_integration_orders(exchange: str, orders: list):

    client = clients(
        exchange=exchange,
        key=config(f"{exchange}TestAPIKey"),
        secret=config(f"{exchange}TestAPISecret"),
        testnet=True
    )

    final_orders = []

    for _order in orders:

        upper = client.get_last_price(pair=_order['pair'])['latest_price'] * 1.1
        lower = client.get_last_price(pair=_order['pair'])['latest_price'] * 0.9
        _order['sl_price'] = lower if _order['type_pos'] == 'LONG' else upper
        _order['tp_price'] = upper if _order['type_pos'] == 'LONG' else lower

        final_orders.append(_order)

    entry_orders = client.enter_limit_then_market(final_orders)

    for _order_ in orders:
        assert _order_['pair'] in list(entry_orders.keys())

        del _order_['sl_price']
        del _order_['tp_price']

        tp_order = client.get_order(pair=_order_['pair'], order_id=entry_orders[_order_['pair']]['tp_id'])

        client.cancel_order(pair=_order_['pair'], order_id=entry_orders[_order_['pair']]['tp_id'])
        client.cancel_order(pair=_order_['pair'], order_id=entry_orders[_order_['pair']]['sl_id'])

        _order_['tp_time'] = tp_order["time"]
        _order_['tp_id'] = entry_orders[_order_['pair']]['tp_id']
        _order_['sl_id'] = entry_orders[_order_['pair']]['sl_id']

    exit_orders = client.exit_limit_then_market(orders)

    for _order_ in orders:
        assert _order_['pair'] in list(exit_orders.keys())

    print(f"Test integration_orders for {exchange.upper()} successful")


def test_integration_orders():

    all_tests = [
        # {
        #     'exchange': 'binance',
        #     'orders': [
        #         {'pair': 'BTCUSDT', 'type_pos': 'LONG', 'quantity': 0.01},
        #         {'pair': 'ETHUSDT', 'type_pos': 'SHORT', 'quantity': 0.1}
        #     ]
        # },
        {
            'exchange': 'bybit',
            'orders': [
                {'pair': 'BTCUSDT', 'type_pos': 'LONG', 'quantity': 0.1},
                {'pair': 'ETHUSDT', 'type_pos': 'SHORT', 'quantity': 1}
            ]
        }
    ]

    for _test in all_tests:
        asserts_integration_orders(
            exchange=_test['exchange'],
            orders=_test['orders']
        )


test_integration_orders()


