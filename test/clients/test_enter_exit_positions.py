import time

from nova.clients.bybit import Bybit
from decouple import config

self = Bybit(key=config('BYBIT_KEY_TEST'),
             secret=config('BYBIT_SECRET_TEST'),
             testnet=True)

# self.setup_account(quote_asset='USDT', leverage=10, list_pairs=['AVAXUSDT'], bankroll=1000, max_down=0.5)


pair = 'AVAXUSDT'
qty = 230
pos_type = 'Long'

if pos_type == 'Long':
    side_0 = 'Buy'
    side_1 = 'Sell'

    sl_price = self.get_last_price(pair=pair) * 0.9
    tp_price = self.get_last_price(pair=pair) * 1.1
else:
    side_1 = 'Buy'
    side_0 = 'Sell'

    sl_price = self.get_last_price(pair=pair) * 1.1
    tp_price = self.get_last_price(pair=pair) * 0.9

for i in range(5):

    start_bk = self.get_token_balance('USDT')

    entry_0 = {'pair': pair, 'side': side_0, 'qty': qty, 'sl_price': sl_price, 'tp_price': tp_price}
    # entry_1 = {'pair': 'ETHUSDT', 'side': 'Buy', 'qty': 2, 'sl_price': 1200, 'tp_price': 2000}

    entry_orders = self.enter_limit_then_market([entry_0])

    time.sleep(20)

    position_size = sum([order['cum_exec_qty'] for order in entry_orders[pair]])

    assert position_size * (1 - 0.05) < qty < position_size * (1 + 0.05), 'wrong qty'

    exit_0 = {'pair': pair, 'side': side_1, 'position_size': position_size}
    # exit_1 = {'pair': 'ETHUSDT', 'side': 'Sell', 'position_size': 2}

    exit_orders = self.exit_limit_then_market([exit_0])

    real_profit = self.get_token_balance('USDT') - start_bk

    entry_price = 0
    fees = 0
    pos_size = 0

    for order in entry_orders[pair]:
        pos_size += order['cum_exec_qty']
        entry_price += order['cum_exec_value']
        fees += order['cum_exec_fee']

    entry_price = entry_price / pos_size
    pos_size = pos_size * entry_price

    exit_price = 0
    d_exit = 0

    for order in exit_orders[pair]:
        d_exit += order['cum_exec_qty']
        exit_price += order['cum_exec_value']
        fees += order['cum_exec_fee']

    exit_price = exit_price / d_exit

    side = 1 if pos_type == 'Long' else -1

    non_realized_pnl = side * (exit_price - entry_price) / entry_price * pos_size
    expected_profit = non_realized_pnl - fees

    print(f"Real profit = {real_profit}")
    print(f"Expected profit = {expected_profit}")

    assert abs(expected_profit) * (1 - 0.01) < abs(real_profit) < abs(expected_profit * (1 + 0.01)), 'wrong profit'

    time.sleep(30)


