from nova.utils.telegram import TelegramBOT
from nova.api.client import NovaAPI

from nova.utils.helpers import get_timedelta_unit, is_opening_candle
from nova.clients.clients import clients
import asyncio

from datetime import datetime, timedelta
from typing import Union
import random
import time


class Bot(TelegramBOT):

    def __init__(self,
                 exchange: str,
                 key: str,
                 secret: str,
                 # nova_api_key: str,
                 bot_id: str,

                 bot_name: str,
                 quote_asset: str,

                 candle: str,
                 historical_window: int,

                 list_pair: Union[str, list],
                 bankroll: float,
                 leverage: int,
                 max_pos: int,

                 max_down: float,
                 max_hold: float,

                 limit_time_execution: int = 15,

                 telegram_notification: bool = False,
                 telegram_bot_token: str = '',
                 telegram_bot_chat_id: str = '',
                 testnet: bool = False,
                 geometric_size: bool = False
                 ):

        # BOT INFORMATION
        self.bot_id = bot_id
        self.bot_name = bot_name

        # STRATEGY INFORMATION
        self.quote_asset = quote_asset
        self.candle = candle
        self.time_step = get_timedelta_unit(self.candle)
        self.max_holding = max_hold
        self.position_size = leverage / max_pos
        self.geometric_size = geometric_size
        self.historical_window = historical_window
        self.max_pos = max_pos
        self.leverage = leverage
        self.max_sl_percentage = 1 / leverage - 0.02
        self.bankroll = bankroll
        self.max_down = max_down

        self.limit_time_execution = limit_time_execution
        # NOVA API
        # self.nova = NovaAPI(api_secret=nova_api_key)

        # Get the correct
        if type(list_pair).__name__ == 'str':
            if list_pair != 'All pairs':
                raise Exception("Please enter valid list_pair")
            # else:
            # self.list_pair = self.nova.trading_pairs()
        elif type(list_pair).__name__ == 'list':
            # raw_list = self.nova.trading_pairs()
            # assert list_pair in raw_list
            self.list_pair = list_pair

        # EXCHANGE CLIENT
        self.exchange = exchange
        self.client = clients(exchange=exchange, key=key, secret=secret, testnet=testnet)

        # TELEGRAM NOTIFICATION
        self.telegram_notification = telegram_notification
        if self.telegram_notification:
            TelegramBOT.__init__(self,
                                 bot_token=telegram_bot_token,
                                 bot_chatID=telegram_bot_chat_id)

        # BOT STATE
        self.unrealizedPNL = 0
        self.realizedPNL = 0
        self.current_positions_amt = 0
        self.position_opened = {}
        self.prod_data = {}

    def entry_signals_prod(self, pair: str) -> dict:
        return {}

    def exit_signals_prod(self,
                          pair: str,
                          type_pos: str) -> bool:
        return False

    def get_position_size(self):
        """
        Note: it returns 0 if all the amount has been used
        Returns:
             the position amount from the balance that will be used for the transaction
        """
        max_in_pos = self.bankroll
        if self.geometric_size:
            pos_size = self.position_size * (self.bankroll + self.unrealizedPNL)
            max_in_pos += self.unrealizedPNL
        else:
            pos_size = self.position_size * self.bankroll

        available = self.client.get_token_balance(quote_asset=self.quote_asset)

        if (available < pos_size / self.leverage) or (max_in_pos - self.current_positions_amt - pos_size < 0):
            return 0
        else:
            return pos_size

    def entering_positions(self):
        """
        Args:
        Returns:
            Send all transaction to the exchange and update the backend and the class
        """

        all_entries = []

        random.shuffle(self.list_pair)

        remaining_position = int(self.max_pos - len(self.position_opened.keys()))

        actual_pos = self.client.get_actual_positions(list_pair=self.list_pair)

        for pair in self.list_pair:

            if remaining_position == 0:
                print('Maximum position reached')
                break
            if pair in actual_pos.keys():
                break

            entry_signal = self.entry_signals_prod(pair)

            if entry_signal['action'] != 0:
                _action = {'pair': pair}
                print(f'Enter in position on {pair}')

                _action['type_pos'] = 'LONG' if entry_signal['action'] == 1 else 'SHORT'

                actual_price = self.client.get_last_price(pair=pair)
                _action['qty'] = (self.bankroll * self.position_size) / actual_price
                _action['sl_price'] = entry_signal['sl_price']
                _action['tp_price'] = entry_signal['tp_price']

                all_entries.append(_action)
                remaining_position -= 1

        completed_entries = self.client.enter_limit_then_market(
            orders=all_entries,
        )

        for _pair_, _info_ in completed_entries.items():
            # 7 - todo : create the position data in nova labs backend
            self.position_opened[_pair_] = _info_

            if self.telegram_notification:
                self.telegram_enter_position(entry_info=_info_)

    def _compute_profit(self,
                        pair: str):
        """
        Must be call only when the position has been completely exit
        Args:
            pair:

        Returns:

        """

        trade_info = self.position_opened[pair]

        # Get total fees paid
        trade_info['cum_exec_fees'] = trade_info['exit_fees'] + trade_info['entry_fees']

        side = 1 if trade_info['type_pos'] == 'LONG' else -1
        non_realized_pnl = side * (trade_info['exit_price'] - trade_info['entry_price']) \
                           * trade_info['original_pos_size']

        trade_info['realized_pnl'] = round(non_realized_pnl - trade_info['cum_exec_fees'], 2)

        self.position_opened[pair] = trade_info

    def add_exit_info(self,
                      pair: str,
                      exit_info: dict,
                      exit_type: str):

        trade_info = self.position_opened[pair]

        trade_info['exit_fees'] += exit_info['exit_fees']
        trade_info['qty_exited'] += exit_info['executedQuantity']
        trade_info['current_pos_size'] = trade_info['original_pos_size'] - trade_info['qty_exited']
        trade_info['last_exit_time'] = exit_info['last_exit_time']

        if exit_type == 'TP':
            trade_info['exit_price'] = (exit_info['exit_price'] * exit_info['executedQuantity']) \
                                       / trade_info['original_pos_size']
        else:
            trade_info['exit_price'] += (exit_info['exit_price'] * exit_info['executedQuantity']) \
                                        / trade_info['original_pos_size']

        if trade_info['current_pos_size'] == 0:
            trade_info['trade_status'] = 'CLOSED'

        self.position_opened[pair] = trade_info

    def update_local_state(self,
                           pair: str):

        self.realizedPNL += self.position_opened[pair]['realized_pnl']

        self.delete_position_in_local(pair=pair)

        if self.telegram_notification:
            self.telegram_realized_pnl(pnl=self.realizedPNL)

        # todo: add exited position to local trades history

        print(f'Current pnl = {round(self.realizedPNL, 2)} $')

    def delete_position_in_local(self,
                                 pair: str):

        del self.position_opened[pair]

    def exiting_positions(self):
        """
        Returns:
            This function verify the positions that should be exited and execute the
            position closing logic.
        """

        date = datetime.now()

        all_exits = []

        # Add a security by getting all real actual positions and call exit function only if we are still in position
        current_positions = self.client.get_actual_positions(list_pair=self.list_pair)

        for _pair, _info in self.position_opened.items():
            entry_time_date = datetime.fromtimestamp(_info['entry_time'] // 1000)

            # Add 3 minutes for the time to entry position
            diff = date - entry_time_date + timedelta(minutes=3)
            diff_in_hours = diff.total_seconds() / 3600

            exit_signal = self.exit_signals_prod(pair=_pair,
                                                 type_pos=self.position_opened[_pair]['type_pos'])

            in_position = _pair in current_positions.keys()

            if (exit_signal or diff_in_hours >= self.max_holding) and in_position:
                # exit_type = 'EXIT_SIGNAL' if exit_signal == 1 else 'MAX_HOLDING'
                print(f'Exiting {_pair} position')
                all_exits.append({'pair': _pair,
                                  'type_pos': _info['type_pos'],
                                  'position_size': _info['current_pos_size'],
                                  })

        # Execute Exit Orders
        completed_exits = self.client.exit_limit_then_market(
            orders=all_exits
        )

        for _pair_, _exit_info in completed_exits.items():
            # Add new exit information to local bot positions data
            self.add_exit_info(pair=_pair_,
                               exit_info=_exit_info,
                               exit_type='ExitSignal')

            # Compute total fees, profits and get trade_id
            self._compute_profit(pair=_pair_)

            # 7 - todo : create the position data in nova labs backend
            self._push_backend()

            if self.telegram_notification:
                self.telegram_exit_position(exit_info=_exit_info)

            # 8 - update bot state (PnL; current_positions_amt; etc) + delete position
            self.update_local_state(pair=_pair_)

    def verify_positions(self):
        """
        Returns:
            This function updates the open position of the bot, checking if there is any TP or SL
        """

        all_pos = self.position_opened.copy()

        # for each position opened by the bot we are executing a verification
        for _pair, _info in all_pos.items():

            print(f"Checking {_pair}'s Position")
            data = self.client.get_tp_sl_state(
                pair=_pair,
                tp_id=_info['tp_id'],
                sl_id=_info['sl_id']
            )

            # tp_manually_canceled = (data['tp']['order_status'] == 'CANCELED') and (data['current_quantity'] != 0)
            # sl_manually_canceled = (data['sl']['order_status'] == 'CANCELED') and (data['current_quantity'] != 0)
            # position_size_manually_changed = (data['current_quantity'] != _info['original_pos_size']) and \
            #                                  (data['tp']['executedQuantity'] == 0) and \
            #                                  (data['sl']['order_status'] != 'FILLED')
            #
            # # 1 Verify if still opened and not Cancelled
            # if tp_manually_canceled or sl_manually_canceled or position_size_manually_changed:
            #     print(f"{_pair} Position or Orders have been manually changed -> delete pos from bot's management")
            #
            #     # todo: delete the position data in nova labs backend
            #     self._push_backend()
            #
            #     self.delete_position_in_local(pair=_pair)
            #
            #     continue

            # 2 Verify if sl has been executed (ALL SL ARE MARKET)
            if data['sl']['order_status'] == 'FILLED':
                # Cancel TP order
                self.client.cancel_order(pair=_pair, order_id=data['tp']['order_id'])

                print('SL market order has been triggered')

                self.add_exit_info(pair=_pair,
                                   exit_info=data['sl'],
                                   exit_type='SL')

                self._compute_profit(pair=_pair)

                # todo: push data in nova labs backend
                self._push_backend()

                if self.telegram_notification:
                    self.telegram_sl_triggered(pair=_pair)

                self.update_local_state(pair=_pair)

                continue

            # 3 Verify if tp has been executed
            if data['tp']['order_status'] in ['FILLED', 'PARTIALLY_FILLED']:

                remaining_quantity = data['tp']['originalQuantity'] - data['tp']['executedQuantity']

                if remaining_quantity == 0:
                    # Cancel sl order
                    self.client.cancel_order(pair=_pair, order_id=data['sl']['order_id'])

                    print('TP limit order completely executed -> Remove Position')

                    self.add_exit_info(pair=_pair,
                                       exit_info=data['tp'],
                                       exit_type='TP')

                    self._compute_profit(pair=_pair)

                    # todo: push data in nova labs backend
                    self._push_backend()

                    if self.telegram_notification:
                        self.telegram_tp_fully_filled(pair=_pair)

                    self.update_local_state(pair=_pair)

                else:

                    print('TP partially executed')
                    self.add_exit_info(pair=_pair,
                                       exit_info=data['tp'],
                                       exit_type='TP')

                    # todo: push data in nova labs backend
                    self._push_backend()

                    if self.telegram_notification:
                        self.telegram_tp_partially_filled(pair=_pair,
                                                          tp_info=data['tp'])

        print('All Positions under BOT management updated')

    def update_tp_sl(
            self,
            pair: str,
            order_id: str,
            order_type: str,
            exit_side: str,
            stop_price: float,
            quantity: float
    ):

        print(f"Update Order: {pair}")

        # Cancel old Take profit order
        self.client.cancel_order(
            pair=pair,
            order_id=order_id
        )

        # Create new Take profit order
        tp_open = self.client.sl_market_order(
            pair=pair,
            side=exit_side,
            stop_price=stop_price,
            quantity=quantity
        )

        self.position_opened[pair][f'{order_type}_id'] = tp_open['order_id']

    def _push_backend(self):
        """
        Args:

        Returns:
            Updates the data in novalabs backend
        """
        return None

    def security_close_all_positions(self):
        print('SECURITY CLOSE ALL')

        positions = self.position_opened.copy()

        for _pair, _info in positions.items():
            self.client.cancel_order(pair=_pair, order_id=_info['tp_id'])
            self.client.cancel_order(pair=_pair, order_id=_info['sl_id'])

            self.client.exit_market(
                pair=_pair,
                type_pos=_info['type_pos'],
                quantity=_info['original_pos_size']
            )

            del self.position_opened[_pair]
            # todo: update database

    def security_max_down(self):
        """
        Notes: This function should be executed at the beginning of every run.
        We are checking for a Salus update of our current situation.
        If Salus triggered a stop are a Max Down from the user, this function will
        go get the information and stop the bot.

        Returns:
        """
        return None

    def update_available_trading_pairs(self):

        pairs_info = self.client.get_pairs_info()

        for pair in self.list_pair:

            if pair not in pairs_info.keys():
                print(f'{pair} not available for trading -> removing from list pairs')

                self.list_pair.remove(pair)

    def get_historical_data(self):

        print(f'Fetching historical data', "\U000023F3", end="\r")
        t0 = time.time()
        self.prod_data = asyncio.run(self.client.get_prod_data(
            list_pair=self.list_pair,
            interval=self.candle,
            nb_candles=self.historical_window,
            current_state=None
        ))
        print(f'Historical data downloaded (in {round(time.time() - t0, 2)}s)', "\U00002705")

    def update_historical_data(self):

        print("Updating historical data", "\U000023F3", end="\r")

        t0 = time.time()
        # 4 - Update dataframes
        self.prod_data = asyncio.run(self.client.get_prod_data(
            list_pair=self.list_pair,
            interval=self.candle,
            nb_candles=self.historical_window,
            current_state=self.prod_data
        ))

        print(f"Historical data updated (in {round(time.time() - t0, 2)}s)", "\U00002705")

    def set_up_account(self):

        print(f'Setting up account', "\U000023F3", end="\r")
        self.client.setup_account(bankroll=self.bankroll,
                                  quote_asset=self.quote_asset,
                                  leverage=self.leverage,
                                  max_down=self.max_down,
                                  list_pairs=self.list_pair
                                  )
        print(f'Account set', "\U00002705")

    def production_run(self):

        last_crashed_time = datetime.utcnow()

        print(f'Nova L@bs {self.bot_name} starting')

        if self.telegram_notification:
            self.telegram_bot_starting(bot_name=self.bot_name,
                                       exchange=self.exchange)

        # start account
        self.set_up_account()

        # get historical price (and volume) evolution
        self.get_historical_data()

        # Begin the infinite loop
        while True:

            try:

                # Start the logic at each candle opening
                if is_opening_candle(interval=self.candle):

                    print(f'------- time : {datetime.utcnow()} -------\nNew candle opens')

                    # todo: check if we reached max down
                    self.security_max_down()

                    self.update_available_trading_pairs()

                    # update historical data
                    self.update_historical_data()

                    if len(self.position_opened) > 0:
                        # verify positions (reach tp or sl)
                        self.verify_positions()

                        # check exit signals and perform actions
                        self.exiting_positions()

                    # check entry signals and perform actions
                    self.entering_positions()

            except Exception as e:

                print(f'{self.bot_name} crashed with the error:\n{str(e)[:100]}')

                since_last_crash = datetime.utcnow() - last_crashed_time

                if since_last_crash < self.time_step * 1.5:
                    # exit all current positions
                    self.security_close_all_positions()

                    if self.telegram_notification:
                        self.telegram_bot_crashed(exchange=self.exchange,
                                                  bot_name=self.bot_name,
                                                  error=str(e))

                    return str(e)

                last_crashed_time = datetime.utcnow()
                time.sleep(60)
