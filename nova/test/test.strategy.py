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
        action = df_ind[df_ind['timeUTC'] == df_ind['timeUTC'].max()]['action']
        return int(action)

    def exit_signals_prod(self):
        self.print_log_send_msg('-- Checking Exit --')
        pass

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

                    # 2- is max holding
                    self.is_max_holding()

                    # 3 - check if there the bot loss the maximum amount
                    self.security_check_max_down()

                    # 4 - check current position
                    current_position = self.get_actual_position()

                    # 5 - check if positions have been updated
                    self.verify_positions(current_position)

                    # 6 - check the exit positions
                    self.exit_signals_prod()

                    # 7 - for each token
                    for pair in self.list_pair:

                        # 8 - update the data
                        self.print_log_send_msg('-- Update Data --')
                        self.update_prod_data(pair=pair)

                        # 9 - if pair not in position yet
                        if float(current_position[pair]['positionAmt']) == 0:

                            # 10 - compute bot action
                            self.print_log_send_msg(f'Check Entry -> {pair}')
                            action = self.entry_signals_prod(pair=pair)

                            # 11 - if action is different from 0
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
                        else:
                            self.print_log_send_msg(f'Already in position -> {pair}')

                    time.sleep(1)

        except Exception:

            self.security_close_all('ERROR')

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
#
# # current_position = random_strat.get_actual_position()
# current_position = random_strat.get_actual_position()
#
# position_info = current_position['BTCUSDT']
# qty = 1 * '0.01'
# if float(position_info['positionAmt']) == qty:
#     print(1)
#
# ###
#
#
# order = random_strat.client.futures_create_order(
#     symbol='XRPUSDT',
#     side='SELL',
#     type='MARKET',
#     quantity=100.0
# )

#
# open_orders = random_strat.client.futures_get_open_orders()
# df_orders = pd.DataFrame(open_orders)
#
# for index, row in df_orders.iterrows():
#     print(index)
#     if index>=4:
#         print('delete')
#         df_orders.drop(
#             index=index,
#             inplace=True
#         )
#

