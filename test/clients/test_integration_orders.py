from nova.clients.clients import clients
from decouple import config
import time
from multiprocessing import set_start_method, get_start_method
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

    print(entry_orders)

    print(f"Test enter_limit_then_market for {exchange.upper()} successful")


def test_integration_orders():

    all_tests = [
        {
            'exchange': 'binance',
            'orders': [
                {'pair': 'BTCUSDT', 'type_pos': 'LONG', 'quantity': 0.01},
                {'pair': 'ETHUSDT', 'type_pos': 'SHORT', 'quantity': 0.1}
            ]
        },
        # {
        #     'exchange': 'bybit',
        #     'orders': [
        #         {'pair': 'BTCUSDT', 'type_pos': 'LONG', 'quantity': 0.01},
        #         {'pair': 'ETHUSDT', 'type_pos': 'SHORT', 'quantity': 0.1}
        #     ]
        # }
    ]

    for _test in all_tests:
        asserts_integration_orders(
            exchange=_test['exchange'],
            orders=_test['orders']
        )


test_integration_orders()

#
# for i in range(5):
#
#     start_bk = self.get_token_balance('USDT')
#
#     entry_0 = {'pair': pair, 'side': side_0, 'qty': qty, 'sl_price': sl_price, 'tp_price': tp_price}
#     # entry_1 = {'pair': 'ETHUSDT', 'side': 'Buy', 'qty': 2, 'sl_price': 1200, 'tp_price': 2000}
#
#     entry_orders = self.enter_limit_then_market([entry_0])
#
#     time.sleep(20)
#
#     position_size = sum([order['cum_exec_qty'] for order in entry_orders[pair]])
#
#     assert position_size * (1 - 0.05) < qty < position_size * (1 + 0.05), 'wrong qty'
#
#     exit_0 = {'pair': pair, 'side': side_1, 'position_size': position_size}
#     # exit_1 = {'pair': 'ETHUSDT', 'side': 'Sell', 'position_size': 2}
#
#     exit_orders = self.exit_limit_then_market([exit_0])
#
#     real_profit = self.get_token_balance('USDT') - start_bk
#
#     entry_price = 0
#     fees = 0
#     pos_size = 0
#
#     for order in entry_orders[pair]:
#         pos_size += order['executedQuantity']
#         entry_price += order['cum_exec_value']
#         fees += order['cum_exec_fee']
#
#     entry_price = entry_price / pos_size
#     pos_size = pos_size * entry_price
#
#     exit_price = 0
#     d_exit = 0
#
#     for order in exit_orders[pair]:
#         d_exit += order['executedQuantity']
#         exit_price += order['cum_exec_value']
#         fees += order['cum_exec_fee']
#
#     exit_price = exit_price / d_exit
#
#     side = 1 if pos_type == 'Long' else -1
#
#     non_realized_pnl = side * (exit_price - entry_price) / entry_price * pos_size
#     expected_profit = non_realized_pnl - fees
#
#     print(f"Real profit = {real_profit}")
#     print(f"Expected profit = {expected_profit}")
#
#     assert abs(expected_profit) * (1 - 0.01) < abs(real_profit) < abs(expected_profit * (1 + 0.01)), 'wrong profit'
#
#     time.sleep(30)

import time
from multiprocessing import Process, Pool, set_start_method
from concurrent.futures import ProcessPoolExecutor, as_completed
from nova.clients.clients import clients
from decouple import config

set_start_method('fork')

start = time.perf_counter()


def do_something(exchange: str, pair: str):
    client = clients(
        exchange=exchange,
        key=config(f"{exchange}TestAPIKey"),
        secret=config(f"{exchange}TestAPISecret"),
        testnet=True
    )
    t_start = time.time()

    while (time.time() - t_start < 5):
        print('waiting')

    return client.get_last_price(pair=pair)

x = []

with Pool() as pool :
    # secs = [5,4,3, 2, 1]
    secs = [('binance', 'BTCUSDT'),('binance', 'ETHUSDT')]

    results = pool.starmap(do_something, secs)

    for result in results:
        x.append(result)


print(x)


finish = time.perf_counter()

print(f'Finished in {finish - start} seconds')

