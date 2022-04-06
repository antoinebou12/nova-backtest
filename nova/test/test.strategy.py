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
        self.is_max_holding()

    def production_run(self):

        data = self.nova.get_bot(self.bot_id)
        bot_name = data['bot']['name']

        self.print_log_send_msg(f'Nova L@bs {bot_name} Starting in 5 seconds')
        time.sleep(5)

        print('### Download Data ###')
        self.get_prod_data(self.list_pair)

        try:
            while True:
                # Every Minute Monitor the Market
                if datetime.now().second == 0:

                    # First we check if there is
                    self.security_check_max_down()

                    self.print_log_send_msg(f'Checking if Exit - m{datetime.now().minute}###')

                    self.exit_signals_prod()

                    # This code indicates that the function is called every 2 minutes

                    for pair in self.list_pair:
                        self.update_prod_data(pair=pair)

                        if pair not in list(self.position_opened.pair):

                            self.print_log_send_msg(f'### Checking Entry Signals {pair} ###')
                            action = self.entry_signals_prod(pair=pair)

                            if action != 0:
                                self.print_log_send_msg(f'Action is : {action}')
                                self.enter_position(
                                    action=action,
                                    pair=pair,
                                    bot_name=bot_name,
                                    tp=0.2,
                                    sl=0.2
                                )

                    time.sleep(1)
        except:
            self.print_log_send_msg('Bot faced and error', True)


random_strat = RandomStrategy(
    bot_id="624a144e230b2ba25a3a639e",
    api_key=config("BinanceAPIKeyTest"),
    api_secret=config("BinanceAPISecretTest"),
    list_pair=['XRPUSDT', 'BTCUSDT', 'ETHUSDT'],
    size=100.0,
    bankroll=1000.0,
    max_down=0.2,
    is_logging=True
)

random_strat.print_log_send_msg('MESSAGE')

# random_strat.production_run()


# random_strat.get_prod_data(random_strat.list_pair)
# data = random_strat.prod_data
# random_strat.security_check_max_down()
#


# action = 1
# tp = 0.1
# sl = 0.1

# prc = random_strat.get_price_binance('XRPUSDT')
# size = random_strat.get_position_size()
# quantity = (size / prc)
# q_precision, p_precision = random_strat.get_quantity_precision('XRPUSDT')
#
# quantity = float(round(quantity, q_precision))
#
# if action == 1:
#     side = 'BUY'
#     prc_tp = float(round(prc * (1 + tp), p_precision))
#     prc_sl = float(round(prc * (1 - sl), p_precision))
#     type_pos = 'LONG'
#     closing_side = 'SELL'
#
# order = random_strat.client.futures_create_order(symbol='XRPUSDT',
#                                                  side=side,
#                                                  type='MARKET',
#                                                  quantity=quantity)
# tp_open = self.client.futures_create_order(symbol=pair, side=closing_side, type='TAKE_PROFIT_MARKET',
#                                            stopPrice=prc_tp, closePosition=True)

#
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