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
                 nova_api_key: str,
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
                 passphrase: str = '',
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
        if isinstance(list_pair, str):
            if list_pair != 'All pairs':
                raise Exception("Please enter valid list_pair")
            # else:
            # self.list_pair = self.nova.trading_pairs()
        elif isinstance(list_pair, list):
            # raw_list = self.nova.trading_pairs()
            # assert list_pair in raw_list
            self.list_pair = list_pair

        # EXCHANGE CLIENT
        self.exchange = exchange
        self.client = clients(exchange=exchange, key=key, secret=secret, passphrase=passphrase, testnet=testnet)

        # TELEGRAM NOTIFICATION
        self.telegram_notification = telegram_notification

        if self.telegram_notification:
            TelegramBOT.__init__(
                self,
                bot_token=telegram_bot_token,
                bot_chat_id=telegram_bot_chat_id
            )

        # BOT STATE
        self.unrealizedPNL = 0
        self.realizedPNL = 0
        self.current_positions_amt = 0
        self.position_opened = {}
        self.prod_data = {}

    def entry_signals_prod(self, pair: str) -> dict:
        return {}

    def exit_signals_prod(self, pair: str, type_pos: str) -> bool:
        return False

    def get_position_size(self) -> float:
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

        actual_pos = self.client.get_actual_positions(pairs=self.list_pair)

        for pair in self.list_pair:

            if remaining_position == 0:
                print(f'Maximum position reached {self.max_pos}')
                break

            if pair in actual_pos.keys():
                print(f'Already in Position for {pair}')
                continue

            entry_signal = self.entry_signals_prod(pair)

            if entry_signal['action'] != 0:

                _action = {'pair': pair}
                _action['type_pos'] = 'LONG' if entry_signal['action'] == 1 else 'SHORT'

                actual_price = self.client.get_last_price(pair=pair)['latest_price']
                _action['quantity'] = (self.bankroll * self.position_size) / actual_price
                _action['sl_price'] = entry_signal['sl_price']
                _action['tp_price'] = entry_signal['tp_price']
                print(f"Enter in position {_action['type_pos']} on {pair}")

                all_entries.append(_action)
                remaining_position -= 1

        completed_entries = self.client.enter_limit_then_market(
            orders=all_entries,
        )

        for _pair_, _info_ in completed_entries.items():
            self.position_opened[_pair_] = _info_

            if self.telegram_notification:
                self.telegram_enter_position(entry_info=_info_)

    def update_exit_info(self, pair: str, exit_info: dict, exit_type: str):

        fees_var = 'exit_fees' if exit_type not in ['TP', 'SL'] else 'tx_fee_in_quote_asset'
        price_var = 'exit_price' if exit_type not in ['TP', 'SL'] else 'executed_price'

        old_pricing = 0 if exit_type != "TP" else self.position_opened[pair]['exit_price']
        old_quantity_exited = 0 if exit_type != "TP" else self.position_opened[pair]['quantity_exited']

        prc_precision = self.client.pairs_info[pair]['pricePrecision']

        self.position_opened[pair]['exit_time'] = exit_info['time']
        self.position_opened[pair]['exit_fees'] += exit_info[fees_var]

        # Manage the Partial TP Update
        if exit_type == "TP" and exit_info['executed_quantity'] < self.position_opened[pair]['last_tp_executed']:
            self.position_opened[pair]['quantity_exited'] = exit_info['executed_quantity']
            self.position_opened[pair]['last_tp_executed'] = exit_info['executed_quantity']
            self.position_opened[pair]['last_tp_time'] = exit_info['time']
        if exit_type == "TP" and exit_info['status'] == 'FILLED':
            self.position_opened[pair]['last_tp_executed'] = exit_info['executed_quantity']
            self.position_opened[pair]['quantity_exited'] = exit_info['executed_quantity']

        else:
            self.position_opened[pair]['quantity_exited'] += exit_info['executed_quantity']

        self.position_opened[pair]['current_position_size'] = self.position_opened[pair]['original_position_size'] - \
                                                              self.position_opened[pair]['quantity_exited']

        if old_pricing == 0 and old_quantity_exited == 0:
            self.position_opened[pair]['exit_price'] = exit_info[price_var]
        else:
            _price_ = (old_pricing * old_quantity_exited + exit_info[price_var] * exit_info['executed_quantity']) / \
                      self.position_opened[pair]['quantity_exited']
            self.position_opened[pair]['exit_price'] = float(round(_price_, prc_precision))

        if self.position_opened[pair]['current_position_size'] == 0:

            self.position_opened[pair]['trade_status'] = 'CLOSED'

            self.position_opened[pair]['total_fees'] = self.position_opened[pair]['exit_fees']\
                                                          + self.position_opened[pair]['entry_fees']

            side = 1 if self.position_opened[pair]['position_type'] == 'LONG' else -1

            _pnl = side * (self.position_opened[pair]['exit_price'] - self.position_opened[pair]['entry_price']) \
                   * self.position_opened[pair]['original_position_size']

            self.position_opened[pair]['realized_pnl'] = round(_pnl - self.position_opened[pair]['total_fees'], 2)

    def close_local_state(self, pair: str):

        self.realizedPNL += self.position_opened[pair]['realized_pnl']

        print(f'Realized PNL for {pair} = {self.position_opened[pair]["realized_pnl"]}')

        del self.position_opened[pair]

        if self.telegram_notification:
            self.telegram_realized_pnl(pnl=self.realizedPNL)

        assert pair not in self.position_opened.keys(), f'{pair} HAS NOT BEEN REMOVED'
        print(f'Current pnl = {round(self.realizedPNL, 2)} $')

    def exiting_positions(self):
        """
        Returns:
            This function verify the positions that should be exited and execute the
            position closing logic.
        """

        date = datetime.now()

        all_exits = []

        # Add a security by getting all real actual positions and call exit function only if we are still in position
        current_positions = self.client.get_actual_positions(pairs=self.list_pair)

        for _pair, _info in self.position_opened.items():

            entry_time_date = datetime.fromtimestamp(_info['entry_time'] // 1000)
            diff = date - entry_time_date + timedelta(minutes=3)
            diff_in_hours = diff.total_seconds() / 3600

            exit_signal = self.exit_signals_prod(
                pair=_pair,
                type_pos=self.position_opened[_pair]['position_type']
            )

            if (exit_signal or diff_in_hours >= self.max_holding) and _pair in current_positions.keys():

                print(f'Exiting {_pair} position')

                all_exits.append({'pair': _pair,
                                  'type_pos': _info['position_type'],
                                  'quantity': _info['current_position_size'],
                                  'tp_time': self.position_opened[_pair]['last_tp_time'],
                                  'tp_id': self.position_opened[_pair]['tp_id'],
                                  'sl_id': self.position_opened[_pair]['sl_id'],
                                  })

        for _exit in all_exits:
            print(f'Cancel TP {_exit["pair"]}')
            self.client.cancel_order(
                pair=_exit['pair'],
                order_id=self.position_opened[_exit['pair']]['tp_id']
            )

        # Execute Exit Orders
        completed_exits = self.client.exit_limit_then_market(
            orders=all_exits
        )

        for _pair_, _exit_info in completed_exits.items():
            self.client.cancel_order(
                pair=_pair_,
                order_id=self.position_opened[_pair_]['sl_id']
            )
            # Add new exit information to local bot positions data
            self.update_exit_info(
                pair=_pair_,
                exit_info=_exit_info,
                exit_type='ExitSignal',
            )

            self._push_backend()

            if self.telegram_notification:
                self.telegram_exit_position(
                    pair=_pair_,
                    pnl=self.position_opened[_pair_]['realized_pnl']
                )

            # 8 - update bot state (PnL; current_positions_amt; etc) + delete position
            self.close_local_state(pair=_pair_)

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

            # 2 Verify if sl has been executed (ALL SL ARE MARKET)
            if data['sl']['status'] == 'FILLED':

                print('SL market order has been triggered')
                self.client.cancel_order(pair=_pair, order_id=data['tp']['order_id'])

                self.update_exit_info(
                    pair=_pair,
                    exit_info=data['sl'],
                    exit_type='SL',
                )

                self._push_backend()

                if self.telegram_notification:
                    self.telegram_sl_triggered(
                        pair=_pair,
                        pnl=self.position_opened[_pair]['realized_pnl']
                    )

                self.close_local_state(pair=_pair)

                continue

            # 3 Verify if tp has been executed
            if data['tp']['status'] in ['FILLED', 'PARTIALLY_FILLED']:

                remaining_quantity = data['tp']['original_quantity'] - data['tp']['executed_quantity']

                if remaining_quantity == 0:
                    print('TP Limit has been triggered')
                    # Cancel sl order
                    self.client.cancel_order(pair=_pair, order_id=data['sl']['order_id'])

                    self.update_exit_info(
                        pair=_pair,
                        exit_info=data['tp'],
                        exit_type='TP',
                    )

                    self._push_backend()

                    if self.telegram_notification:
                        self.telegram_tp_fully_filled(
                            pair=_pair,
                            pnl=self.position_opened[_pair]['realized_pnl']
                        )

                    self.close_local_state(pair=_pair)

                else:
                    print('PARTIAL TP Limit has been triggered')
                    self.update_exit_info(
                        pair=_pair,
                        exit_info=data['tp'],
                        exit_type='TP',
                    )

                    self._push_backend()

                    if self.telegram_notification:
                        self.telegram_tp_partially_filled(
                            pair=_pair,
                            tp_info=data['tp']
                        )

    @staticmethod
    def _push_backend():
        """
        Args:

        Returns:
            Updates the data in novalabs backend
        """
        return None

    def security_close_all_positions(self):

        positions = self.position_opened.copy()

        for _pair, _info in positions.items():
            self.client.cancel_order(pair=_pair, order_id=_info['tp_id'])
            self.client.cancel_order(pair=_pair, order_id=_info['sl_id'])

            order_information = self.client.exit_market_order(
                pair=_pair,
                type_pos=_info['position_type'],
                quantity=_info['original_position_size']
            )

            self._push_backend()

            del self.position_opened[_pair]

    def security_max_down(self):
        """
        Notes: This function should be executed at the beginning of every run.
        We are checking for a Salus update of our current situation.
        If Salus triggered a stop are a Max Down from the user, this function will
        go get the information and stop the bot.
        Returns:
        """
        total_pnl = (self.bankroll + self.realizedPNL + self.unrealizedPNL) / self.bankroll
        max_down = True if total_pnl <= 1 - self.max_down else False
        return max_down

    def update_trading_pairs(self):
        pairs_info = self.client.get_pairs_info()
        for pair in self.list_pair:
            if pair not in pairs_info.keys():
                print(f'{pair} not available for trading -> removing from list pairs')
                self.list_pair.remove(pair)

    def production_run(self):

        last_crashed_time = datetime.utcnow()

        print(f'Nova L@bs {self.bot_name} starting')

        if self.telegram_notification:
            self.telegram_bot_starting(
                bot_name=self.bot_name,
                exchange=self.exchange
            )
            print(f'Telegram Messages', "\U00002705")

        # start account
        print(f'Setting up account', "\U000023F3", end="\r")
        self.client.setup_account(
            bankroll=self.bankroll,
            quote_asset=self.quote_asset,
            leverage=self.leverage,
            max_down=self.max_down,
            list_pairs=self.list_pair
        )
        print(f'Account set', "\U00002705")

        # get historical price (and volume) evolution
        print(f'Fetching historical data', "\U000023F3", end="\r")
        self.prod_data = asyncio.run(self.client.get_prod_data(
            list_pair=self.list_pair,
            interval=self.candle,
            nb_candles=self.historical_window,
            current_state=None
        ))
        print(f'Historical data downloaded', "\U00002705")

        # Begin the infinite loop
        while True:

            try:

                # Start the logic at each candle opening
                if is_opening_candle(interval=self.candle):

                    print(f'------- time : {datetime.utcnow()} -------\nNew candle opens')

                    if self.security_max_down():
                        print('Security Maximum Loss Triggered')
                        self.security_close_all_positions()
                        break

                    self.update_trading_pairs()

                    # update historical data
                    print("Fetching Latest Data", "\U000023F3", end="\r")
                    self.prod_data = asyncio.run(self.client.get_prod_data(
                        list_pair=self.list_pair,
                        interval=self.candle,
                        nb_candles=self.historical_window,
                        current_state=self.prod_data
                    ))
                    print(f"Data Updated", "\U00002705")

                    if len(self.position_opened) > 0:
                        # verify positions (reach tp or sl)
                        self.verify_positions()

                        # check exit signals and perform actions
                        self.exiting_positions()

                    # check entry signals and perform actions
                    self.entering_positions()

                    # If the previous code takes less than 1 second to execute, it will be executed again
                    time.sleep(1)

            except Exception as e:

                print(f'{self.bot_name} crashed with the error:\n{str(e)[:100]}')

                since_last_crash = datetime.utcnow() - last_crashed_time

                if since_last_crash < self.time_step * 1.5:
                    # exit all current positions
                    self.security_close_all_positions()

                    if self.telegram_notification:
                        self.telegram_bot_crashed(
                            exchange=self.exchange,
                            bot_name=self.bot_name,
                            error=str(e)
                        )

                    return str(e)

                last_crashed_time = datetime.utcnow()

                time.sleep(60)