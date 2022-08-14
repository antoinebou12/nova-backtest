from nova.utils.telegram import TelegramBOT
from nova.api.client import NovaAPI

from nova.utils.helpers import get_timedelta_unit, is_opening_candle
from nova.clients.clients import clients
import asyncio

from datetime import datetime
from typing import Union
import pandas as pd
import random
import time


class Bot(TelegramBOT):

    def __init__(self,
                 exchange: str,
                 key: str,
                 secret: str,
                 nova_api_key: str,
                 bot_id: str,

                 bot_name: str,
                 based_asset: str,

                 candle: str,
                 historical_window: int,

                 list_pair: Union[str, list],
                 bankroll: float,
                 position_size: float,
                 geometric_size: bool,
                 max_pos: int,

                 max_down: float,
                 max_hold: int,

                 limit_time_execution: int = 15,

                 telegram_notification: bool = False,
                 bot_token: str = '',
                 bot_chat_id: str = ''
                 ):

        # BOT INFORMATION
        self.bot_id = bot_id
        self.bot_name = bot_name

        # STRATEGY INFORMATION
        self.based_asset = based_asset
        self.candle = candle
        self.time_step = get_timedelta_unit(self.candle)
        self.max_holding = max_hold
        self.position_size = position_size
        self.geometric_size = geometric_size
        self.historical_window = historical_window
        self.max_pos = max_pos
        # Leverage is automatically set to max
        self.leverage = int(self.max_pos * self.position_size)
        self.max_sl_percentage = 1 / self.leverage - 0.02
        self.bankroll = bankroll
        self.max_down = max_down

        self.limit_time_execution = limit_time_execution
        # NOVA API
        self.nova = NovaAPI(api_secret=nova_api_key)

        # Get the correct
        if type(list_pair).__name__ == 'str':
            if list_pair != 'All pairs':
                raise Exception("Please enter valid list_pair")
            else:
                self.list_pair = self.nova.trading_pairs()
        elif type(list_pair).__name__ == 'list':
            raw_list = self.nova.trading_pairs()
            # assert list_pair in raw_list
            self.list_pair = list_pair

        # EXCHANGE CLIENT
        self.exchange = exchange
        self.client = clients(exchange=exchange, key=key, secret=secret)

        # TELEGRAM NOTIFICATION
        self.telegram_notification = telegram_notification
        if self.telegram_notification:
            TelegramBOT.__init__(self,
                                 bot_token=bot_token,
                                 bot_chatID=bot_chat_id)

        # BOT STATE
        self.unrealizedPNL = 0
        self.realizedPNL = 0
        self.current_positions_amt = 0
        self.position_opened = {}
        self.prod_data = {}

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

        available = self.client.get_token_balance(based_asset=self.based_asset)

        if (available < pos_size / self.leverage) or (max_in_pos - self.current_positions_amt - pos_size < 0):
            return 0
        else:
            return pos_size

    def ltm_order_execution(self, actions: list, execution_type: str):
        """
        Note: ltm stands for limit than market order
        Args:
            actions:
            execution_type:
        Returns:
        """

        limit_executions = {}
        final_executions = {}

        for _info in actions:

            prc = self.client.get_order_book_prices(pair=_info['pair'])

            if execution_type == 'entry':

                limit_executions[_info['pair']] = {}

                size = self.client.get_position_size()

                if size == 0:
                    print(f'Balance too low')
                    self.telegram_bot_sendtext(f'Tried to enter in position for {_info["pair"]} but balance is too low')
                    return None

                # 2 - derive the quantity from the previous variables
                quantity = (size / prc)

                limit_executions[_info['pair']]['quantity'] = quantity

                # 3 - send the order to the exchange
                limit_order = self.client.open_close_order(
                    pair=_info['pair'],
                    side=_info['side'],
                    quantity=quantity,
                    price=prc,
                    order_type='limit'
                )

                limit_executions[_info['pair']]['action_inf'] = _info
                limit_executions[_info['pair']]['limit_order'] = limit_order

            elif execution_type == 'exit':

                print(f'Exiting {_info["pair"]}')

                # Close tp and sl orders
                self.client.cancel_order(
                    pair=_info["pair"],
                    order_id=self.position_opened[_info["pair"]]['tp_id']
                )

                self.client.cancel_order(
                    pair=_info["pair"],
                    order_id=self.position_opened[_info["pair"]]['sl_id']
                )

                # close limit order
                limit_order = self.client.open_close_order(
                    pair=_info['pair'],
                    side=self.position_opened[_info["pair"]]['exit_side'],
                    quantity=self.position_opened[_info["pair"]]['quantity'],
                    price=prc,
                    order_type='limit'
                )
                
                limit_executions[_info['pair']]['limit_order'] = limit_order
                limit_executions[_info['pair']]['action_inf'] = {}
                limit_executions[_info['pair']]['action_inf']['side'] = self.position_opened[_info["pair"]]['exit_side']

        # Waiting for limit execution
        time.sleep(self.limit_time_execution)

        for key, value in limit_executions.items():
            
            final_executions[key] = {}
    
            # 1 - get the order state
            order_state = self.client.get_order_trades(
                pair=key,
                order=value['limit_order']['order_id']
            )
    
            remaining_quantity = order_state['originalQuantity'] - order_state['executedQuantity']
    
            if remaining_quantity > 0:

                # cancel order
                self.client.cancel_order(pair=key, order_id=value['limit_order']['order_id'])

                # send market order
                market_order = self.client.open_close_order(
                    pair=key,
                    side=value['action_inf']['side'],
                    quantity=remaining_quantity,
                    order_type='market'
                )
    
                # todo: rebuild the average entry point
                final_executions[key]['market_order'] = market_order

            if execution_type == 'entry':
                # send tp and sl
                tp_info = self.client.tp_order(
                    pair=key,
                    side=value['action_inf']['closing_side'],
                    quantity=value['quantity'],
                    price=value['action_inf']['tp'],
                    tp_type='limit'
                )
                final_executions[key]['tp_info'] = tp_info

                sl_info = self.client.sl_market_order(
                    pair=key,
                    side=value['action_inf']['closing_side'],
                    quantity=value['quantity'],
                    stop_price=value['action_inf']['sl'],
                )
                final_executions[key]['sl_info'] = sl_info

        return final_executions

    def entering_positions(self):
        """
        Args:
        Returns:
            Send all transaction to the exchange and update the backend and the class
        """

        all_entries = []

        random.shuffle(self.list_pair)

        remaining_position = int(self.max_pos - len(self.position_opened.keys()))

        for pair in self.list_pair:

            if remaining_position == 0:
                print('Maximum position reached')
                break

            _action = self.entry_signals_prod(pair)
            _action['pair'] = pair
            if _action['action'] != 0:
                _action['side'] = 'BUY' if _action['action'] == 1 else 'SELL'
                _action['type_pos'] = 'LONG' if _action['action'] == 1 else 'SHORT'
                _action['closing_side'] = 'SELL' if _action['action'] == 1 else 'BUY'
                all_entries.append(_action)
                remaining_position -= 1

        completed_entries = self.ltm_order_execution(
            actions=all_entries,
            execution_type='entry'
        )

        for _pair_, _info_ in completed_entries.items():
            # 7 - todo : create the position data in nova labs backend

            # 8 - todo: update the dataframe position_opened that keeps track of orders
            self.position_opened[_pair_] = {
                'type': _info_,
                'entry_time': _info_['time'],
                'entry_price': _info_['price'],
                'exit_side': _info_,
                'tp_id': _info_['order_id'],
                'sl_id': _info_['order_id'],
                'quantity': _info_['quantity']
            }

            # 9 - todo : send Telegram notification
            if self.telegram_notification:
                self.enter_position_message(
                    type=_info_,
                    pair=_info_,
                    qty=_info_,
                    entry_price=_info_,
                    tp=_info_,
                    sl=_info_
                )

    def exiting_positions(self):
        """
        Returns:
            This function verify the positions that should be exited and execute the
            position closing logic.
        """
        s_time = self.client.get_server_time()
        server_time = int(str(s_time)[:-3])
        server = datetime.fromtimestamp(server_time)

        all_exits = []

        for _pair, _info in self.position_opened.items():
            entry_time_date = datetime.fromtimestamp(_info['entryTime'])
            diff = server + self.time_step / 10 - entry_time_date
            diff_in_hours = diff.total_seconds() / 3600

            exit_signal = self.exit_signals_prod(pair=_pair)

            if exit_signal or diff_in_hours >= self.max_holding:
                exit_type = 'EXIT_SIGNAL' if exit_signal == 1 else 'MAX_HOLDING'
                all_exits.append({'pair': _pair, 'exit_type': exit_type})

        # Execute Exit Orders
        completed_exits = self.ltm_order_execution(
            actions=all_exits,
            execution_type='exit'
        )

        for _pair_, _info_ in completed_exits.items():
            # 7 - todo : create the position data in nova labs backend

            # 8 - todo: update bot state (PnL; current_positions_amt; etc) + delete position
            del self.position_opened[_pair_]

            # 9 - todo : send Telegram notification
            if self.telegram_notification:
                self.enter_position_message(
                    type=_info_,
                    pair=_info_,
                    qty=_info_,
                    entry_price=_info_,
                    tp=_info_,
                    sl=_info_
                )

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

            condition_tp_touched = data['tp']['order_status'] == 'CANCELED'
            condition_sl_touched = data['sl']['order_status'] == 'CANCELED'
            condition_position_touched = data['current_quantity'] != _info['quantity']

            # 1 Verify if still opened and not Cancelled
            if condition_tp_touched or condition_sl_touched or condition_position_touched:
                print(f'{_pair} Position or Orders have been touched')

                self.client.cancel_order(pair=_pair, order_id=data['tp']['order_id'])
                self.client.cancel_order(pair=_pair, order_id=data['sl']['order_id'])

                self._push_backend()

                del self.position_opened[_pair]

                break

            # 2 Verify if sl has been executed (ALL SL ARE MARKET)
            if data['sl']['order_status'] == 'FILLED':
                print('sl order has been triggered')

                self.client.cancel_order(pair=_pair, order_id=data['tp']['order_id'])
                self._push_backend()

                del self.position_opened[_pair]

                break

            # 3 Verify if tp has been executed
            if data['tp']['executedQuantity'] != 0:

                remaining_quantity = data['tp']['originalQuantity'] - data['sl']['executedQuantity']

                if remaining_quantity == 0:

                    print('tp completely executed -> Remove Position')
                    self.client.cancel_order(pair=_pair, order_id=data['sl']['order_id'])
                    self._push_backend()
                    del self.position_opened[_pair]

                else:

                    print('tp partially executed -> Update Position')
                    self.position_opened[_pair]['quantity'] = remaining_quantity
                    self.update_tp_sl(
                        pair=_pair,
                        order_id=_info['sl_id'],
                        order_type='sl',
                        exit_side=_info['exitSide'],
                        stop_price=data['sl']['price'],
                        quantity=remaining_quantity
                    )

                    self._push_backend()

                break

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
        pass

    def security_close_all_positions(self):
        print('SECURITY CLOSE ALL')

        positions = self.position_opened.copy()

        for _pair, _info in positions:

            self.client.cancel_order(pair=_pair, order_id=_info['tp_id'])
            self.client.cancel_order(pair=_pair, order_id=_info['sl_id'])

            self.client.open_close_order(
                pair=_pair,
                side=_info['exit_side'],
                quantity=_info['quantity'],
                order_type='market'
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
        pass
        
    def production_run(self):

        last_crashed_time = datetime.utcnow()

        # 1 - Print and send telegram message
        print(f'Nova L@bs {self.bot_name} starting')
        self.telegram_bot_sendtext(bot_message=f'Nova L@bs {self.bot_name} starting')

        # 2 - Download the production data
        print(f'Fetching historical data')
        self.prod_data = asyncio.run(self.client.get_prod_data(
            list_pair=self.list_pair,
            interval=self.candle,
            nb_candles=self.historical_window,
            current_state=None
        ))

        # 3 - Begin the infinite loop
        while True:

            try:

                # Start the logic at each candle opening
                if is_opening_candle(interval=self.candle):

                    print(f'------- time : {datetime.utcnow()} -------')
                    self.security_max_down()

                    # 4 - Update dataframes
                    self.prod_data = asyncio.run(self.client.get_prod_data(
                        list_pair=self.list_pair,
                        interval=self.candle,
                        nb_candles=self.historical_window,
                        current_state=self.prod_data.copy()
                    ))

                    # 5 - Verify Positions
                    if len(self.position_opened) > 0:
                        self.verify_positions()
                        self.exiting_positions()

                    # 6 - Enter Positions
                    self.entering_positions()

            except Exception as e:

                print(f'{self.bot_name} crashed with the error:\n{str(e)[:100]}')

                since_last_crash = datetime.utcnow() - last_crashed_time

                if since_last_crash < self.time_step * 1.5:

                    self.security_close_all_positions()

                    self.telegram_bot_sendtext(
                        bot_message=f"{self.bot_name} crashed with the following error:\n\n{str(e)[100]}"
                    )

                    self.telegram_bot_sendtext(
                        bot_message=f"{self.bot_name} crashed again.\n\nAll positions have been closed\n\n"             
                                    f"We recommend you to check your account"
                                    f"Bot stopped \U0001F6D1."
                    )
                    return None

                self.telegram_bot_sendtext(
                    bot_message=f"{self.bot_name} crashed with the following error:\n\n{str(e)[:100]}\n\n"
                                f"Try to restart..."
                )

                last_crashed_time = datetime.utcnow()
                time.sleep(60)
