import numpy as np
import requests

from nova.utils.helpers import interval_to_milliseconds, retry_requests
from nova.utils.constant import DATA_FORMATING
from requests import Request, Session
from urllib.parse import urlencode
import hashlib
import time
import hmac
import json
import pandas as pd
import asyncio
import aiohttp
from multiprocessing import Pool
from datetime import datetime
from typing import Union
import random
import string


class BTCEX:

    def __init__(self,
                 key: str,
                 secret: str,
                 testnet: bool = False):

        self.api_key = key
        self.api_secret = secret

        self.based_endpoint = "" if testnet else "https://api.btcex.com/api/v1"

        self._session = Session()

        self.historical_limit = 10_000

        self.access_token = ''
        self.refresh_token = ''
        self.end_connection_date = np.Inf
        self.connected = False
        if key != '' and secret != '':
            self.connected = True
            self.connect()

        self.pairs_info = self.get_pairs_info()

    # API REQUEST FORMAT
    @retry_requests
    def _send_request(self,
                      end_point: str,
                      request_type: str,
                      params: dict = None,
                      signed: bool = False):

        if params is None:
            params = {}

        if request_type == 'POST':
            request = Request(request_type, f'{self.based_endpoint}{end_point}',
                              json=params)
        elif request_type == 'GET':
            request = Request(request_type, f'{self.based_endpoint}{end_point}',
                              params=urlencode(params, True))
        else:
            raise ValueError("Please enter valid request_type")

        prepared = request.prepare()
        if signed:
            prepared.headers['Authorization'] = f"bearer {self.access_token}"

        response = self._session.send(prepared)

        data = response.json()

        if 'error' in data.keys():
            raise ConnectionError(data['error'])

        return data

    def connect(self):

        params = {'grant_type': 'client_credentials',
                  'client_id': self.api_key,
                  'client_secret': self.api_secret}

        data = self._send_request(
            end_point=f"/public/auth",
            request_type="GET",
            params=params,
        )['result']

        self.access_token = data['access_token']
        self.refresh_token = data['refresh_token']
        self.end_connection_date = int(time.time()) + data['expires_in']

    def logout(self):

        data = self._send_request(
            end_point=f"/private/logout",
            request_type="GET",
            signed=True
        )['result']

        return data

    def refresh_connection(self):

        params = {'grant_type': 'refresh_token',
                  'refresh_token': self.refresh_token}

        data = self._send_request(
            end_point=f"/public/auth",
            request_type="GET",
            params=params,
        )['result']

        self.access_token = data['access_token']
        self.refresh_token = data['refresh_token']
        self.end_connection_date = int(time.time()) + data['expires_in']

    def get_server_time(self) -> int:
        """
        Returns:
            the timestamp in milliseconds
        """
        ts = self._send_request(
            end_point=f"/public/ping",
            request_type="GET",
            signed=False,
        )['usOut']
        return int(ts)

    def get_pairs_info(self) -> dict:

        pairs_info = {}

        data = self._send_request(
            end_point=f"/public/get_instruments",
            params={'currency': 'PERPETUAL'},
            request_type="GET"
        )['result']

        for info in data:
            if info['is_active']:
                pair_name = info['instrument_name']
                pairs_info[pair_name] = {}

                pairs_info[pair_name]['quote_asset'] = info['base_currency']

                pairs_info[pair_name]['maxQuantity'] = np.Inf
                pairs_info[pair_name]['minQuantity'] = float(info['min_qty'])

                pairs_info[pair_name]['tick_size'] = float(info['tick_size'])

                pairs_info[pair_name]['step_size'] = float(info['min_trade_amount'])

                pairs_info[pair_name]['creation_timestamp'] = int(info['creation_timestamp'])

        return pairs_info

    @staticmethod
    def _convert_interval(std_interval) -> str:
        """
        Args:
            std_interval: Binance's interval format
        Returns:
            Bybit's interval format
        """

        if 'm' in std_interval:
            return std_interval[:-1]

        elif 'h' in std_interval:
            mul = int(std_interval[:-1])
            return str(60 * mul)
        else:
            return std_interval[-1].upper()

    def _format_price(self,
                      pair: str,
                      raw_price: float) -> float:

        raw_price = float(raw_price)

        return round(raw_price - raw_price % self.pairs_info[pair]['tick_size'], 10)

    def _format_quantity(self,
                         pair: str,
                         raw_quantity: float) -> float:

        raw_quantity = float(raw_quantity)

        return round(raw_quantity - raw_quantity % self.pairs_info[pair]['step_size'], 10)

    def _get_candles(self,
                     pair: str,
                     interval: str,
                     start_time: int,
                     end_time: int = None) -> list:

        """

        Args:
            pair: pair to get the candles
            interval: Data refresh interval. Enum : 1 3 5 15 30 60 120 240 360 720 "D" "M" "W"
            start_time: From timestamp in milliseconds
            limit: Limit for data size per page, max size is 200. Default as showing 200 pieces of data per page

        Returns:
            list of candles
        """

        _interval = self._convert_interval(std_interval=interval)

        params = {
            'instrument_name': pair,
            'resolution': _interval,
            'start_timestamp': start_time // 1000,
            'end_timestamp': end_time // 1000
        }
        data = self._send_request(
            end_point=f"/public/get_tradingview_chart_data",
            request_type="GET",
            params=params
        )['result']

        return data

    def _get_earliest_timestamp(self, pair: str) -> int:

        return int(self.pairs_info[pair]['creation_timestamp'])

    @staticmethod
    def _format_data(all_data: list, historical: bool = True) -> pd.DataFrame:
        """
        Args:
            all_data: output from _full_history

        Returns:
            standardized pandas dataframe
        """

        interval_ms = 1000 * (all_data[1]['tick'] - all_data[0]['tick'])
        df = pd.DataFrame(all_data)[DATA_FORMATING['btcex']['columns']]

        for var in DATA_FORMATING['btcex']['num_var']:
            df[var] = pd.to_numeric(df[var], downcast="float")

        df = df.rename(columns={'tick': 'open_time'})

        df['open_time'] = 1000 * df['open_time']

        if historical:
            df['next_open'] = df['open'].shift(-1)

        df['close_time'] = df['open_time'] + interval_ms - 1

        return df.dropna()

    def get_historical_data(self,
                            pair: str,
                            interval: str,
                            start_ts: int,
                            end_ts: int) -> pd.DataFrame:
        """
        Args:
            pair: pair to get data from
            interval: granularity of the candle ['1m', '1h', ... '1d']
            start_ts: timestamp in milliseconds of the starting date
            end_ts: timestamp in milliseconds of the end date
        Returns:
            the complete raw data history desired -> multiple requested could be executed
        """

        # init our list
        klines = []

        # convert interval to useful value in ms
        timeframe = interval_to_milliseconds(interval)

        # establish first available start timestamp
        if start_ts is not None:
            first_valid_ts = self._get_earliest_timestamp(
                pair=pair,
            )
            start_ts = max(start_ts, first_valid_ts)

        if end_ts and start_ts and end_ts <= start_ts:
            raise ValueError('end_ts must be greater than start_ts')

        while True:
            # fetch the klines from start_ts up to max 500 entries or the end_ts if set
            temp_data = self._get_candles(
                pair=pair,
                interval=interval,
                start_time=start_ts,
                end_time=start_ts + self.historical_limit * timeframe
            )

            # append this loops data to our output data
            if temp_data:
                klines += temp_data

            # handle the case where exactly the limit amount of data was returned last loop
            # check if we received less than the required limit and exit the loop
            if not len(temp_data) or len(temp_data) < self.historical_limit:
                # exit the while loop
                break

            # increment next call by our timeframe
            start_ts = 1000 * temp_data[-1]['tick'] + timeframe

            # exit loop if we reached end_ts before reaching <limit> klines
            if end_ts and start_ts >= end_ts:
                break

        df = self._format_data(all_data=klines)

        return df[df['open_time'] <= end_ts]

    def update_historical(self, pair: str, interval: str, current_df: pd.DataFrame) -> pd.DataFrame:
        """
        Note:
            It will automatically download the latest data  points (excluding the candle not yet finished)
        Args:
            pair: pair to get information from
            interval: granularity of the candle ['1m', '1h', ... '1d']
            current_df: pandas dataframe of the current data
        Returns:
            a concatenated dataframe of the current data and the new data
        """

        end_date_data_ts = current_df['open_time'].max()
        now_date_ts = int(time.time() * 1000)

        df_temp = self.get_historical_data(pair=pair,
                                           interval=interval,
                                           start_ts=end_date_data_ts,
                                           end_ts=now_date_ts)

        return pd.concat([current_df, df_temp], ignore_index=True).drop_duplicates(subset=['open_time'])

    def get_token_balance(self,
                          quote_asset: str) -> float:

        params = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "/private/get_assets_info",
            "params": {
                'asset_type': ['PERPETUAL']
            }
        }

        data = self._send_request(
            end_point=f"/private/get_assets_info",
            request_type="POST",
            params=params,
            signed=True
        )['result']

        current_balance = data['PERPETUAL']['wallet_balance']

        return float(current_balance)

    def get_order_book(self, pair: str) -> dict:

        data = self._send_request(
            end_point=f"/public/get_order_book",
            request_type="GET",
            params={'instrument_name': pair}
        )['result']

        std_ob = {'bids': [], 'asks': []}

        for ask in data['asks']:
            std_ob['asks'].append({
                'price': float(ask[0]),
                'size': float(ask[1])
            })
        for bid in data['bids']:
            std_ob['bids'].append({
                'price': float(bid[0]),
                'size': float(bid[1])
            })

        return std_ob

    def enter_market_order(self, pair: str, type_pos: str, quantity: float) -> dict:

        method = '/private/buy' if type_pos == 'LONG' else '/private/sell'

        std_qty = self._format_quantity(pair=pair, raw_quantity=quantity)

        params = {
            "instrument_name": pair,
            "position_side": type_pos,
            "amount": std_qty,
            "type": 'market',
            "time_in_force": 'immediate_or_cancel',
            "reduce_only": False,
        }

        response = self._send_request(
            end_point=method,
            request_type="GET",
            params=params,
            signed=True
        )

        return self.get_order(order_id=response['result']['order']['order_id'])

    def exit_market_order(self, pair: str, type_pos: str, quantity: float) -> dict:

        method = '/private/sell' if type_pos == 'LONG' else '/private/buy'

        std_qty = self._format_quantity(pair=pair, raw_quantity=quantity)

        params = {
            "instrument_name": pair,
            "position_side": type_pos,
            "amount": std_qty,
            "type": 'market',
            "time_in_force": 'immediate_or_cancel',
            "reduce_only": True,
        }

        response = self._send_request(
            end_point=method,
            request_type="GET",
            params=params,
            signed=True
        )

        return self.get_order(order_id=response['result']['order']['order_id'])

    @retry_requests
    def get_order(self,
                  order_id: str):

        response = self._send_request(
            end_point=f"/private/get_order_state",
            request_type="GET",
            params={'order_id': order_id},
            signed=True
        )['result']

        formated_order = self._format_order(data=response)

        return formated_order

    def _format_order(self, data: dict) -> dict:

        date_ts = data['last_update_timestamp']

        _order_type = data['order_type'].upper()
        if data['custom_order_id'][:2] == 'TP':
            _order_type = 'TAKE_PROFIT'

        _order_type = 'STOP_MARKET' if _order_type == 'STOP_LOSS_MARKET' else _order_type

        data['order_state'] = data['order_state'].upper()
        data['order_state'] = 'CANCELED' if data['order_state'] == 'cancelled' else data['order_state']

        condition_partially_filled = (_order_type == 'TAKE_PROFIT') and (float(data['filled_amount']) != 0) and \
                                     (float(data['filled_amount']) < float(data['amount']))
        data['order_state'] = 'PARTIALLY_FILLED' if condition_partially_filled else data['order_state']

        _order_name = 'order_id'

        _stop_price = 0
        _executed_quantity = 0
        _executed_price = 0
        _price = 0

        if _order_type == 'MARKET' and data['filled_amount'] != 0:
            _executed_quantity = float(data['filled_amount'])
            _executed_price = float(data['average_price'])

        elif _order_type == 'LIMIT':
            _price = float(data['price'])
            _executed_price = float(data['price'])
            _executed_quantity = float(data['filled_amount'])

        elif _order_type == 'TAKE_PROFIT':
            _stop_price = float(data['price'])
            _executed_quantity = float(data['filled_amount'])
            _executed_price = 0 if _executed_quantity == 0 else float(data['price'])

        elif _order_type == 'STOP_MARKET':

            _executed_quantity = float(data['filled_amount'])
            _executed_price = float(data['average_price'])

        formatted = {
            'time': int(date_ts),
            'order_id': data[_order_name],
            'pair': data['instrument_name'],
            'status': data['order_state'],
            'type': _order_type.upper(),
            'time_in_force': data['time_in_force'],
            'reduce_only': data['reduce_only'],
            'side': data['direction'].upper(),
            'price': _price,
            'stop_price': _stop_price,
            'original_quantity': data['amount'],
            'executed_quantity': _executed_quantity,
            'executed_price': _executed_price
        }

        return formatted

    def get_order_trades(self, pair: str, order_id: str):
        """
              Args:
                  pair: pair that is currently analysed
                  order_id: order_id number

              Returns:
                  standardize output of the trades needed to complete an order
              """

        order = self.get_order(
            order_id=order_id
        )

        trades = self._send_request(
            end_point=f"/private/get_user_trades_by_order",
            request_type="GET",
            params={"order_id": order_id},
            signed=True
        )['result']

        order['tx_fee_in_quote_asset'] = 0
        order['tx_fee_in_other_asset'] = {}
        order['nb_of_trades'] = trades['count']

        if trades['count'] > 0:
            for trade in trades['trades']:
                order['tx_fee_in_quote_asset'] += float(trade['fee'])

        return order

    def place_limit_tp(self, pair: str, side: str, quantity: float, tp_price: float):
        """
        Place a limit order as Take Profit.
        Args:
            pair:
            side:
            quantity:
            tp_price:
        Returns:
            response of the API call
        """

        method = '/private/buy' if side == 'BUY' else '/private/sell'

        std_price = self._format_price(pair=pair, raw_price=tp_price)
        std_quantity = self._format_quantity(pair=pair, raw_quantity=quantity)

        params = {
            "position_side": 'LONG' if side == 'SELL' else 'SHORT',
            "instrument_name": pair,
            "price": std_price,
            "amount": std_quantity,
            "type": 'limit',
            "post_only": True,
            "reduce_only": True,
            "custom_order_id": 'TP_' + ''.join(random.choice(string.ascii_lowercase) for i in range(25))
        }

        response = self._send_request(
            end_point=method,
            request_type="GET",
            params=params,
            signed=True
        )['result']

        return self.get_order(order_id=response['order']['order_id'])

    def place_market_sl(self, pair: str, side: str, quantity: float, sl_price: float):

        method = '/private/buy' if side == 'BUY' else '/private/sell'

        std_price = self._format_price(pair=pair, raw_price=sl_price)
        std_quantity = self._format_quantity(pair=pair, raw_quantity=quantity)

        params = {
            "position_side": 'LONG' if side == 'SELL' else 'SHORT',
            "instrument_name": pair,
            "type": 'market',
            "amount": std_quantity,
            "trigger_price": std_price,
            "condition_type": 'STOP',
            "trigger_price_type": 2,
            "post_only": False,
            "reduce_only": True,
        }

        response = self._send_request(
            end_point=method,
            request_type="GET",
            params=params,
            signed=True
        )['result']

        return self.get_order(order_id=response['order']['order_id'])

    def get_last_price(self, pair: str):

        data = self._send_request(
            end_point=f"/public/tickers",
            request_type="GET",
            params={"instrument_name": pair},
        )['result']

        return {
            'pair': data[0]['instrument_name'],
            'timestamp': int(data[0]['timestamp']),
            'latest_price': float(data[0]['last_price'])
        }

    def place_limit_order_best_price(
            self,
            pair: str,
            side: str,
            quantity: float,
            reduce_only: bool = False
    ):

        ob = self.get_order_book(pair=pair)
        _type = 'bids' if side == 'BUY' else 'asks'
        best_price = float(ob[_type][0]['price'])

        method = '/private/buy' if side == 'BUY' else '/private/sell'

        std_quantity = self._format_quantity(pair=pair, raw_quantity=quantity)

        params = {
            "instrument_name": pair,
            "price": best_price,
            "amount": std_quantity,
            "type": 'limit',
            "post_only": True,
            "reduce_only": reduce_only,
        }

        response = self._send_request(
            end_point=method,
            request_type="GET",
            params=params,
            signed=True
        )['result']

        time.sleep(1)

        limit_order_posted, order_data = self._verify_limit_posted(
            order_id=response['order']['order_id']
        )

        return limit_order_posted, order_data

    def _verify_limit_posted(self, order_id: str):
        """
        When posting a limit order (with time_in_force='PostOnly') the order can be immediately canceled if its
        price is to high for buy orders and to low for sell orders. Sometimes the first order book changes too quickly
        that the first buy or sell order prices are no longer the same since the time we retrieve the OB. This can
        eventually get our limit order automatically canceled and never posted. Thus each time we send a limit order
        we verify that the order is posted.

        Args:
            pair:
            order_id:

        Returns:
            This function returns True if the limit order has been posted, False else.
        """

        order_data = self.get_order(
            order_id=order_id
        )

        if order_data['status'] in ['NEW', 'FILLED', 'PARTIALLY_FILLED', 'OPEN']:
            return True, order_data

        elif order_data['status'] in ['REJECTED', 'CANCELED']:
            print(f'Limit order rejected or canceled: {order_id}')
            return False, None

    def _looping_limit_orders(
            self,
            pair: str,
            side: str,
            quantity: float,
            reduce_only: bool,
            duration: int
    ):

        """
        This function will try to enter in position by sending only limit orders to be sure to pay limit orders fees.

        Args:
            pair:
            side:
            quantity:
            duration: number of seconds we keep trying to enter in position with limit orders
            reduce_only: True if we are exiting a position

        Returns:
            Residual size to fill the based qty
        """

        residual_size = quantity
        t_start = time.time()
        all_limit_orders = []

        # Try to enter with limit order during duration number of seconds
        while (residual_size >= self.pairs_info[pair]['minQuantity']) and (time.time() - t_start < duration):

            posted, data = self.place_limit_order_best_price(
                pair=pair,
                side=side,
                quantity=residual_size,
                reduce_only=reduce_only
            )

            if posted:

                _price = data['price']
                _status = data['status']

                # If the best order book price stays the same, do not cancel current order
                while (_price == data['price']) and (time.time() - t_start < duration) and (_status != 'FILLED'):
                    time.sleep(10)

                    ob = self.get_order_book(pair=pair)
                    _type = 'bids' if side == 'BUY' else 'asks'
                    _price = float(ob[_type][0]['price'])
                    _status = self.get_order(
                        order_id=data['order_id']
                    )['status']

                self.cancel_order(
                    pair=pair,
                    order_id=data['order_id']
                )

                _order_trade = self.get_order_trades(
                    pair=pair,
                    order_id=data['order_id']
                )

                all_limit_orders.append(_order_trade)

            # Get the positions information
            pos_info = self.get_actual_positions(pairs=pair)

            # looping enter position : current_size = 0 => no limit execution => try again
            if pair not in list(pos_info.keys()) and not reduce_only:
                residual_size = quantity
            # 0 < current_size < quantity => partial limit execution => update residual_size => try again
            elif pair in list(pos_info.keys()) and not reduce_only and pos_info[pair]['position_size'] <= quantity:
                residual_size = quantity - pos_info[pair]['position_size']

            # looping exit position (current_size > 0 => no or partial limit execution => try again)
            elif pair in list(pos_info.keys()) and reduce_only:
                residual_size = pos_info[pair]['position_size']
            # current_size = 0 => limit exit order fully executed => update residual_size to 0
            elif pair not in list(pos_info.keys()) and reduce_only and posted:
                residual_size = 0

            # side situation 1 : current_size = 0 + exit position but latest order has not been posted
            # => complete execution from the tp or sl happening between checking position and exiting position
            elif pair not in list(pos_info.keys()) and reduce_only and not posted:
                residual_size = 0

        return residual_size, all_limit_orders

    def _format_enter_limit_info(self, all_orders: list, tp_order: dict, sl_order: dict) -> dict:

        final_data = {
            'pair': all_orders[0]['pair'],
            'position_type': 'LONG' if all_orders[0]['side'] == 'BUY' else 'SHORT',
            'original_position_size': 0,
            'current_position_size': 0,
            'entry_time': all_orders[-1]['time'],
            'tp_id': tp_order['order_id'],
            'tp_price': tp_order['stop_price'],
            'sl_id': sl_order['order_id'],
            'sl_price': sl_order['stop_price'],
            'trade_status': 'ACTIVE',
            'entry_fees': 0,
        }

        _price_information = []
        _avg_price = 0

        for order in all_orders:
            _trades = self.get_order_trades(pair=order['pair'], order_id=order['order_id'])

            if _trades['executed_quantity'] > 0:
                final_data['entry_fees'] += _trades['tx_fee_in_quote_asset']
                final_data['original_position_size'] += _trades['executed_quantity']
                _price_information.append({'price': _trades['executed_price'], 'qty': _trades['executed_quantity']})

        # Can be small differences due to float approximations, so we have to round position size
        final_data['original_position_size'] = self._format_quantity(pair=final_data['pair'],
                                                                     raw_quantity=final_data['original_position_size'])
        final_data['current_position_size'] = final_data['original_position_size']

        for _info in _price_information:
            _avg_price += _info['price'] * (_info['qty'] / final_data['current_position_size'])

        final_data['entry_price'] = _avg_price

        # needed for TP partial Execution
        final_data['last_tp_time'] = float('inf')
        final_data['exit_time'] = 0
        final_data['exit_fees'] = 0
        final_data['exit_price'] = 0
        final_data['quantity_exited'] = 0
        final_data['total_fees'] = 0
        final_data['realized_pnl'] = 0
        final_data['exchange'] = 'btcex'

        return final_data

    def cancel_order(self,
                     pair: str,
                     order_id: str):

        self._send_request(
            end_point=f"/private/cancel/",
            request_type="GET",
            params={"order_id": order_id},
            signed=True
        )

    def _set_margin_type(self,
                         pair: str,
                         margin: str = 'isolate'):

        params = {"instrument_name": pair,
                  "margin_type": margin}

        return self._send_request(
            end_point=f"/private/adjust_perpetual_margin_type",
            request_type="GET",
            params=params,
            signed=True
        )['result']

    def _set_leverage(self,
                      pair: str,
                      leverage: int = 1):

        params = {"instrument_name": pair,
                  "leverage": leverage}

        return self._send_request(
            end_point=f"/private/adjust_perpetual_leverage",
            request_type="GET",
            params=params,
            signed=True
        )['result']

    def setup_account(self,
                      quote_asset: str,
                      leverage: int,
                      list_pairs: list,
                      bankroll: float):
        """
        Note: Setup leverage, margin type (= ISOLATED) and check if the account has enough quote asset in balance.

        Args:
            quote_asset: most of the time USDT
            leverage:
            list_pairs:
            bankroll: the amount of quote asset (= USDT) the bot will trade with
            max_down: the maximum bk's percentage loss

        Returns:
            None
        """

        ## ACCOUNT MUST BE ON ONE-WAY MODE

        for pair in list_pairs:
            # Set margin type to ISOLATED
            self._set_margin_type(
                pair=pair,
                margin="isolate",
            )

            # Set leverage
            self._set_leverage(
                pair=pair,
                leverage=leverage
            )

        # Check with the account has enough bk
        balance = self.get_token_balance(quote_asset=quote_asset)

        assert balance >= bankroll, f"The account has only {round(balance, 2)} {quote_asset}. " \
                                    f"{round(bankroll, 2)} {quote_asset} is required"

        params = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "/private/get_assets_info",
            "params": {
                'asset_type': ['PERPETUAL']
            }
        }

        data = self._send_request(
            end_point=f"/private/get_assets_info",
            request_type="POST",
            params=params,
            signed=True
        )['result']['PERPETUAL']

        # Make sure we are in One-Way-Mode
        assert not data['dual_side_position'], 'Please change your position mode to One-Way Mode'

        # Make sure there is no current position
        assert data['available_funds'] == data['wallet_balance'], \
            'Please exit all your positions before running the bot'

    def get_actual_positions(self, pairs: Union[list, str]) -> dict:

        _pairs = [pairs] if isinstance(pairs, str) else pairs
        pos_inf = []
        final = {}

        for pair in _pairs:
            data = self._send_request(
                end_point=f"/private/get_position",
                request_type="GET",
                params={'instrument_name': pair},
                signed=True
            )['result']

            if data != {}:
                pos_inf.append(data)

        for i in pos_inf:
            pair = i['instrument_name']
            final[pair] = {}
            final[pair]['position_size'] = abs(float(i['size']))
            final[pair]['entry_price'] = float(i['average_price'])
            final[pair]['unrealized_pnl'] = float(i['floating_profit_loss'])
            final[pair]['type_pos'] = 'LONG' if i['direction'] == 'buy' else 'SHORT'
            final[pair]['exit_side'] = 'SELL' if i['direction'] == 'buy' else 'BUY'

        return final

    def get_tp_sl_state(self,
                        pair: str,
                        tp_id: str,
                        sl_id: str):

        tp_info = self.get_order_trades(pair=pair, order_id=tp_id)
        sl_info = self.get_order_trades(pair=pair, order_id=sl_id)
        return {
            'tp': tp_info,
            'sl': sl_info,
        }

    def _enter_limit_then_market(self,
                                 pair,
                                 type_pos,
                                 quantity,
                                 sl_price,
                                 tp_price):
        """
        Optimized way to enter in position. The method tries to enter with limit orders during 2 minutes.
        If after 2min we still did not entered with the desired amount, a market order is sent.

        Args:
            pair:
            type_pos:
            sl_price:
            quantity:

        Returns:
            Size of the current position
        """

        side = 'BUY' if type_pos == 'LONG' else 'SELL'

        std_qty = self._format_quantity(pair=pair, raw_quantity=quantity)

        residual_size, all_orders = self._looping_limit_orders(
            pair=pair,
            side=side,
            quantity=std_qty,
            duration=60,
            reduce_only=False
        )

        # If there is residual, enter with market order
        if residual_size >= self.pairs_info[pair]['minQuantity']:
            market_order = self.enter_market_order(
                pair=pair,
                type_pos=type_pos,
                quantity=residual_size
            )

            all_orders.append(market_order)

        time.sleep(5)
        # Get current position info
        pos_info = self.get_actual_positions(pairs=pair)

        exit_side = 'SELL' if side == 'BUY' else 'BUY'

        # Place take profit limit order
        tp_data = self.place_limit_tp(
            pair=pair,
            side=exit_side,
            quantity=pos_info[pair]['position_size'],
            tp_price=tp_price
        )

        sl_data = self.place_market_sl(
            pair=pair,
            side=exit_side,
            quantity=pos_info[pair]['position_size'],
            sl_price=sl_price
        )

        return self._format_enter_limit_info(
            all_orders=all_orders,
            tp_order=tp_data,
            sl_order=sl_data
        )

    def enter_limit_then_market(self, orders: list):

        final = {}
        all_arguments = []

        for order in orders:
            arguments = tuple(order.values())
            all_arguments.append(arguments)

        with Pool() as pool:
            results = pool.starmap(func=self._enter_limit_then_market, iterable=all_arguments)

        for _information in results:
            final[_information['pair']] = _information

        return final

    def _exit_limit_then_market(self, pair: str, type_pos: str, quantity: float, tp_time: int, tp_id: str, sl_id: str):

        side = 'SELL' if type_pos == 'LONG' else 'BUY'

        residual_size, all_orders = self._looping_limit_orders(
            pair=pair,
            side=side,
            quantity=quantity,
            duration=60,
            reduce_only=True
        )

        if residual_size == 0 and all_orders == {}:
            return None

        # If there is residual, exit with market order
        if residual_size >= self.pairs_info[pair]['minQuantity']:

            market_order = self.exit_market_order(
                pair=pair,
                type_pos=type_pos,
                quantity=residual_size
            )

            if market_order:
                all_orders.append(market_order)

        return self._format_exit_limit_info(
            pair=pair,
            all_orders=all_orders,
            tp_id=tp_id,
            tp_time=tp_time,
            sl_id=sl_id
        )

    def _format_exit_limit_info(self, pair: str, all_orders: list, tp_id: str, tp_time: int, sl_id: str):

        final_data = {
            'pair': pair,
            'executed_quantity': 0,
            'time': int(time.time() * 1000),
            'trade_status': 'CLOSED',
            'exit_fees': 0,
        }

        data = self.get_tp_sl_state(pair=pair, tp_id=tp_id, sl_id=sl_id)

        tp_execution = {
            'tp_execution_unregistered': True,
            'executed_quantity': 0,
            'executed_price': 0,
            'tx_fee_in_quote_asset': 0,
        }

        if data['tp']['time'] > tp_time:
            print('IN BETWEEN TP EXECUTION TO BUILD')

        if data['sl']['status'] in ['FILLED']:
            print('IN BETWEEN SL EXECUTION')
            all_orders.append(data['sl'])

        _price_information = []
        _avg_price = 0

        for order in all_orders:
            if 'tp_execution_unregistered' in order.keys():
                print('TP BETWEEN EXECUTION')
                _trades = tp_execution
            else:
                _trades = self.get_order_trades(pair=order['pair'], order_id=order['order_id'])

            if _trades['executed_quantity'] > 0:
                final_data['exit_fees'] += _trades['tx_fee_in_quote_asset']
                final_data['executed_quantity'] += _trades['executed_quantity']
                _price_information.append({'price': _trades['executed_price'], 'qty': _trades['executed_quantity']})

        for _info in _price_information:
            _avg_price += _info['price'] * (_info['qty'] / final_data['executed_quantity'])

        final_data['exit_price'] = _avg_price

        return final_data

    def exit_limit_then_market(self,
                               orders: list) -> dict:

        """
        Parallelize the execution of _exit_limit_then_market.
        Args:
            orders: list of dict. Each element represents the params of an order.
            [{'pair': 'BTCUSDT', 'type_pos': 'LONG', 'position_size': 0.1},
             {'pair': 'ETHUSDT', 'type_pos': 'SHORT', 'position_size': 1}]
        Returns:
            list of positions info after executing all exit orders.
        """

        final = {}
        all_arguments = []

        for order in orders:
            arguments = tuple(order.values())
            all_arguments.append(arguments)

        with Pool() as pool:
            results = pool.starmap(func=self._exit_limit_then_market, iterable=all_arguments)

        for _information in results:
            if _information is not None:
                final[_information['pair']] = _information

        return final

    async def get_prod_candles(
            self,
            session,
            pair,
            interval,
            window,
            current_pair_state: dict = None
    ):

        url = self.based_endpoint + '/public/get_tradingview_chart_data'

        final_dict = {}
        final_dict[pair] = {}

        if current_pair_state is not None:
            start_time = int(current_pair_state[pair]['latest_update'] / 1000) - \
                         int(interval_to_milliseconds(interval) / 1000)
        else:
            start_time = int(time.time() - (window + 1) * interval_to_milliseconds(interval=interval) / 1000)

        params = {
            'instrument_name': pair,
            'resolution': self._convert_interval(interval),
            'start_timestamp': start_time,
            'end_timestamp': int(time.time() + 10)
        }

        # Compute the server time
        s_time = int(1000 * time.time())

        async with session.get(url=url, params=params) as response:
            data = await response.json()

            df = self._format_data(data['result'], historical=False)

            df = df[df['close_time'] <= s_time]

            latest_update = df['open_time'].values[-1]

            for var in ['open_time', 'close_time']:
                df[var] = pd.to_datetime(df[var], unit='ms')

            if current_pair_state is None:
                final_dict[pair]['latest_update'] = latest_update
                final_dict[pair]['data'] = df

            else:
                df_new = pd.concat([current_pair_state[pair]['data'], df])
                df_new = df_new.drop_duplicates(subset=['open_time']).sort_values(
                    by=['open_time'],
                    ascending=True
                )
                df_new = df_new.tail(window)
                df_new = df_new.reset_index(drop=True)

                final_dict[pair]['latest_update'] = latest_update
                final_dict[pair]['data'] = df_new

            return final_dict

    async def get_prod_data(
            self,
            list_pair: list,
            interval: str,
            nb_candles: int,
            current_state: dict
    ):
        """
        Note: This function is called once when the bot is instantiated.
        This function execute n API calls with n representing the number of pair in the list
        Args:
            list_pair: list of all the pairs you want to run the bot on.
            interval: time interval
            nb_candles: number of candles needed
            current_state: boolean indicate if this is an update
        Returns: None, but it fills the dictionary self.prod_data that will contain all the data
        needed for the analysis.
        !! Command to run async function: asyncio.run(self.get_prod_data(list_pair=list_pair)) !!
        """
        # Refresh token if necessary
        if self.connected and self.end_connection_date - time.time() < 86400:
            self.refresh_connection()

        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
            tasks = []
            for pair in list_pair:
                task = asyncio.ensure_future(
                    self.get_prod_candles(
                        session=session,
                        pair=pair,
                        interval=interval,
                        window=nb_candles,
                        current_pair_state=current_state)
                )
                tasks.append(task)
            all_info = await asyncio.gather(*tasks)

            all_data = {}
            for info in all_info:
                all_data.update(info)
            return all_data

