from nova.utils.strategy import Strategy

import pandas as pd
import numpy as np
import time
from binance.client import Client
from decouple import config
from datetime import datetime


class RandomStrategy (Strategy):

    """
    Note: The random strategy will always be used in the testing environment since
    there is no volume.
    """

    def __init__(self,
                 bot_id: str,
                 api_key: str,
                 api_secret: str,
                 list_pair: list,
                 size: float,
                 bankroll: float,
                 max_down: float,
                 is_logging: bool
                 ):

        # all optimized hyper parameters or set to stone
        self.entry_long_prob = 1/5
        self.entry_short_prob = 1/5
        self.exit_prob = 0.1

        self.client = Client(api_key, api_secret, testnet=True)

        Strategy.__init__(self,
                          bot_id=bot_id,
                          candle='1m',
                          size=size,
                          window=5,
                          holding=0.05,
                          bankroll=bankroll,
                          max_down=max_down,
                          is_logging=is_logging
                          )

        self.list_pair = list_pair

    def build_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Args:
            df: pandas dataframe coming from the get_all_historical_data() method in the BackTest class
            ['timeUTC', 'open', 'high', 'low', 'close', 'volume', 'next_open', 'date']

        Returns:
            pandas dataframe with the technical indicators that wants
        """
        df['entry_long'] = np.random.random(df.shape[0])
        df['entry_short'] = np.random.random(df.shape[0])
        df['exit_point'] = np.random.random(df.shape[0])
        df['index_num'] = np.arange(len(df))
        return df

    def entry_signals_prod(self, pair: str):
        """
        Args:
            pair:  pair string that we are currently looking
        Returns:
            a integer that indicates what type of action will be taken
        """
        df_ind = self.build_indicators(self.prod_data[pair]['data'])
        df_ind['action'] = np.where(df_ind['entry_long'] < self.entry_long_prob, 1,
                                         np.where(df_ind['entry_short'] < self.entry_short_prob, -1, 0))
        action = df_ind[df_ind['timeUTC'] == self.prod_data[pair]['latest_update']]['action']
        return int(action)

    def exit_signals_prod(self):
        self.print_log_send_msg('Check Exit -> Max Holding')
        self.is_max_holding()

    def production_run(self):

        # 0.1 - instantiate the bot
        data = self.nova.get_bot(self.bot_id)
        bot_name = data['bot']['name']
        self.print_log_send_msg(f'Nova L@bs {bot_name} Starting in 1 second')
        time.sleep(1)

        # 0.2 - Download the production data
        self.get_prod_data(self.list_pair)

        try:
            while True:
                # Every Minute Monitor the Market
                if datetime.now().second == 0:

                    # 1 - print current PNL
                    self.print_log_send_msg(f'Current bot PNL is {self.currentPNL}')

                    # 2 - check if there the bot loss the maximum amount
                    self.security_check_max_down()

                    # 2.1 - check current position
                    current_position = self.get_actual_position()

                    # 2.2 - check if positions have been updated
                    self.verify_positions(current_position)

                    # 2.2 - print current position
                    print(self.position_opened)

                    # 3 - check the exit positions
                    self.exit_signals_prod()

                    # 4 - for each token
                    for pair in self.list_pair:

                        # 4.1 - update the data
                        self.update_prod_data(pair=pair)

                        # 4.2 - if pair not in position yet
                        if pair not in list(self.position_opened.pair):

                            # 4.2.1 - compute bot action
                            self.print_log_send_msg(f'Check Entry -> {pair}')
                            action = self.entry_signals_prod(pair=pair)

                            # 4.2.2 - if action is different from 0
                            if action != 0:

                                # 4.3 - send entering position
                                self.print_log_send_msg(f'{pair} action is {action}')

                                # 4.4 - enter position
                                self.enter_position(
                                    action=action,
                                    pair=pair,
                                    bot_name=bot_name,
                                    tp=0.2,
                                    sl=0.2
                                )

                    time.sleep(1)

        except Exception:

            self.print_log_send_msg(
                msg='Bot faced and error',
                error=True
            )


random_strat = RandomStrategy(
    bot_id="624df78dbae86bec19577df1",
    api_key=config("BinanceAPIKeyTest"),
    api_secret=config("BinanceAPISecretTest"),
    list_pair=['XRPUSDT', 'BTCUSDT', 'ETHUSDT'],
    size=100.0,
    bankroll=1000.0,
    max_down=0.2,
    is_logging=False
)


random_strat.production_run()

positions = random_strat.get_actual_position(['XRPUSDT', 'BTCUSDT', 'ETHUSDT'])

trades = random_strat.client.futures_account_trades()

data = random_strat.client.futures_get_all_orders()

data = random_strat.client.futures_get_all_orders()

all_pos = random_strat.client.futures_position_information()

position = {}
for pos in all_pos:
    position[pos['symbol']] = pos


position['BTCUSDT']

trades = random_strat.client.futures_account_trades(symbol ='ETHUSDT')
import pandas as pd



trades = random_strat.client.futures_account_trades(startTime=1649252285943)
df = pd.DataFrame(trades)


entry_tx = df[df['orderId'] == 3019566738]
entry_tx.to_dict('records')



df_pair = df[(df['symbol']=='ETHUSDT') & (df['time'] > 1649254722046)]

for index, row_tx in df_pair.iterrows():
    print(row_tx.qty)
    #
    # if float(row_tx.qty) > 0.02:
    #     print('break')
    #     break

df_btc = df[(df['symbol']=='BTCUSDT') & (df['time'] > 1649268965735)]

order_iddd = 841984428

if order_iddd in list(df.orderId):
    print(1)

s_time = random_strat.client.get_server_time()

s = [-1,2,3]
min(s)

open_orders = random_strat.client.futures_get_open_orders()
df_orders = pd.DataFrame(open_orders)

##################### EXAMPLE #####################

# random_strat.get_prod_data(random_strat.list_pair)
# data = random_strat.prod_data
# random_strat.security_check_max_down()
#

# pair = 'BNBUSDT'
# action = -1
# tp = 0.1
# sl = 0.1
#
# prc = random_strat.get_price_binance(pair)
# size = random_strat.get_position_size()
# quantity = (size / prc)
# q_precision, p_precision = random_strat.get_quantity_precision(pair)
#
# quantity = float(round(quantity, q_precision))
#
# if action == 1:
#     side = 'BUY'
#     prc_tp = float(round(prc * (1 + tp), p_precision))
#     prc_sl = float(round(prc * (1 - sl), p_precision))
#     type_pos = 'LONG'
#     closing_side = 'SELL'
# elif action == -1:
#     side = 'SELL'
#     prc_tp = float(round(prc * (1 - tp), p_precision))
#     prc_sl = float(round(prc * (1 + sl), p_precision))
#     type_pos = 'SHORT'
#     closing_side = 'BUY'
#
# order = random_strat.client.futures_create_order(
#     symbol=pair,
#     side=side,
#     type='MARKET',
#     quantity=quantity
# )
#
# tp_open = random_strat.client.futures_create_order(
#     symbol=pair,
#     side=closing_side,
#     type='TAKE_PROFIT_MARKET',
#     stopPrice=prc_tp,
#     closePosition=True
# )
#
# sl_open = random_strat.client.futures_create_order(
#     symbol=pair,
#     side=closing_side,
#     type='STOP_MARKET',
#     stopPrice=prc_sl,
#     closePosition=True
# )
#
#
# # all tx since
# tx = random_strat.client.futures_account_trades(startTime=1649299015009)

# order = random_strat.client.futures_create_order(symbol='XRPUSDT', side='BUY', type='MARKET', quantity=100.0)
# entry_tx = random_strat.client.futures_account_trades(orderId=order['orderId'])

# data = random_strat.get_actual_position(['XRPUSDT', 'BTCUSDT', 'ETHUSDT'])
#
# random_strat.nova.update_bot_position(
#     pos_id='624d8575fc922c884ae6cc7a',
#     pos_type='LONG',
#     state='CLOSED',
#     entry_price=0.7913,
#     exit_price=0.8027,
#     exit_type='MAX_HOLDING',
#     profit=-1.42842,
#     fees=34.944441497999996,
#     pair='XRPUSDT'
# )

