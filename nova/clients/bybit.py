from nova.utils.helpers import interval_to_milliseconds
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


class Bybit:

    def __init__(self,
                 key: str,
                 secret: str,
                 testnet: bool = False):

        self.api_key = key
        self.api_secret = secret

        self.based_endpoint = "https://api-testnet.bybit.com" if testnet else "https://api.bybit.com"

        self._session = Session()

        self.historical_limit = 200

        self.pairs_info = self.get_pairs_info()

    # API REQUEST FORMAT
    def _send_request(self, end_point: str, request_type: str, params: dict = None, signed: bool = False):

        if params is None:
            params = {}

        if signed:
            params['api_key'] = self.api_key
            params['timestamp'] = int(time.time() * 1000)
            params = dict(sorted(params.items()))

            query_string = urlencode(params, True)
            query_string = query_string.replace('False', 'false').replace('True', 'true')

            m = hmac.new(self.api_secret.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256)
            params['sign'] = m.hexdigest()

        if request_type == 'POST':
            request = Request(request_type, f'{self.based_endpoint}{end_point}',
                              data=json.dumps(params))
        elif request_type == 'GET':
            request = Request(request_type, f'{self.based_endpoint}{end_point}',
                              params=urlencode(params, True))
        else:
            raise ValueError("Please enter valid request_type")

        prepared = request.prepare()
        prepared.headers['Content-Type'] = "application/json"
        response = self._session.send(prepared)
        data = response.json()

        if data['ret_msg'] != "OK" and data['ret_code'] != 20001:
            print(f"{data['ret_code']} : {data['ret_msg']}")

        return data

    def get_server_time(self) -> int:
        """
        Returns:
            the timestamp in milliseconds
        """
        ts = self._send_request(
            end_point=f"/public/time",
            request_type="GET"
        )['time_now']
        return int(float(ts) * 1000)

    def _get_candles(self,
                     pair: str,
                     interval: str,
                     start_time: int,
                     limit: int = 200,
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
            'symbol': pair,
            'interval': _interval,
            'from': start_time // 1000,
            'limit': limit
        }
        data = self._send_request(
            end_point=f"/public/linear/kline",
            request_type="GET",
            params=params
        )
        return data['result']

    def get_pairs_info(self) -> dict:
        """
        Returns:
            All pairs available and tradable on the exchange.
        """
        data = self._send_request(
            end_point=f"/v2/public/symbols",
            request_type="GET"
        )['result']

        pairs_info = {}

        for pair in data:
            tradable = pair['status'] == 'Trading'

            if tradable:
                pairs_info[pair['name']] = {}
                pairs_info[pair['name']]['quote_asset'] = pair['quote_currency']
                pairs_info[pair['name']]['pricePrecision'] = pair['price_scale']
                pairs_info[pair['name']]['maxQuantity'] = pair['lot_size_filter']['max_trading_qty']
                pairs_info[pair['name']]['minQuantity'] = pair['lot_size_filter']['min_trading_qty']
                pairs_info[pair['name']]['tick_size'] = float(pair['price_filter']['tick_size'])
                pairs_info[pair['name']]['quantityPrecision'] = str(pair['lot_size_filter']['qty_step'])[::-1].find('.')

        return pairs_info

    def _get_earliest_timestamp(self, pair: str, interval: str) -> int:
        """
        Args:
            pair: Name of symbol pair -- BNBBTC
            interval: Binance Kline interval

        return:
            the earliest valid open timestamp
        """

        kline = self._get_candles(
            pair=pair,
            interval=interval,
            start_time=1467900800000,
            limit=1
        )

        return kline[0]['open_time'] * 1000

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

    @staticmethod
    def _format_data(all_data: list, historical: bool = True) -> pd.DataFrame:
        """
        Args:
            all_data: output from _full_history

        Returns:
            standardized pandas dataframe
        """

        interval_ms = 1000 * (all_data[1]['start_at'] - all_data[0]['start_at'])
        df = pd.DataFrame(all_data)[DATA_FORMATING['bybit']['columns']]

        for var in DATA_FORMATING['bybit']['num_var']:
            df[var] = pd.to_numeric(df[var], downcast="float")

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
                interval=interval
            )
            start_ts = max(start_ts, first_valid_ts)

        if end_ts and start_ts and end_ts <= start_ts:
            raise ValueError('end_ts must be greater than start_ts')

        while True:
            # fetch the klines from start_ts up to max 500 entries or the end_ts if set
            temp_data = self._get_candles(
                pair=pair,
                interval=interval,
                limit=self.historical_limit,
                start_time=start_ts
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
            start_ts = 1000 * temp_data[-1]['open_time'] + timeframe

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

        df = self.get_historical_data(pair=pair,
                                      interval=interval,
                                      start_ts=end_date_data_ts,
                                      end_ts=now_date_ts)

        return pd.concat([current_df, df], ignore_index=True).drop_duplicates(subset=['open_time'])

    def get_token_balance(self, quote_asset: str) -> float:
        """
        Args:
            quote_asset: asset used for the trades (USD, USDT, BUSD, ...)

        Returns:
            Available quote_asset amount.
        """
        data = self._send_request(
            end_point=f"/v2/private/wallet/balance",
            request_type="GET",
            signed=True
        )['result']

        return float(data[quote_asset]['available_balance'])

    def get_order_book(self, pair: str) -> dict:

        data = self._send_request(
            end_point=f"/v2/public/orderBook/L2",
            request_type="GET",
            params={'symbol': pair}
        )['result']

        std_ob = {'bids': [], 'asks': []}

        for info in data:
            if info['side'] == 'Buy':
                std_ob['bids'].append({
                    'price': float(info['price']),
                    'size': float(info['size'])
                })
            elif info['side'] == 'Sell':
                std_ob['asks'].append({
                    'price': float(info['price']),
                    'size': float(info['size'])
                })

        return std_ob

    def enter_market_order(self, pair: str, type_pos: str, quantity: float) -> dict:

        side = 'Buy' if type_pos == 'LONG' else 'Sell'

        params = {
            "side": side,
            "symbol": pair,
            "qty": float(round(quantity, self.pairs_info[pair]['quantityPrecision'])),
            "order_type": 'Market',
            "time_in_force": 'GoodTillCancel',
            "close_on_trigger": False,
            "reduce_only": False,
            "recv_window": "5000",
            "position_idx": 0
        }

        response = self._send_request(
            end_point=f"/private/linear/order/create",
            request_type="POST",
            params=params,
            signed=True
        )

        return self.get_order(pair=pair, order_id=response['result']['order_id'])

    def exit_market_order(self, pair: str, type_pos: str, quantity: float) -> dict:

        side = 'Sell' if type_pos == 'LONG' else 'Buy'

        params = {
            "side": side,
            "symbol": pair,
            "qty": float(round(quantity, self.pairs_info[pair]['quantityPrecision'])),
            "order_type": 'Market',
            "time_in_force": 'ImmediateOrCancel',
            "close_on_trigger": True,
            "reduce_only": True,
            "recv_window": "5000",
            "position_idx": 0
        }

        response = self._send_request(
            end_point=f"/private/linear/order/create",
            request_type="POST",
            params=params,
            signed=True
        )

        return self.get_order(pair=pair, order_id=response['result']['order_id'])

    def _format_order(self, data: dict) -> dict:

        date = datetime.strptime(data['updated_time'], '%Y-%m-%dT%H:%M:%SZ')

        _order_type = data['order_type']
        if data['order_type'] == 'Limit' and data['order_status'] in ['Untriggered', 'Deactivated', 'Triggered']:
            _order_type = 'TAKE_PROFIT'
        if data['order_type'] == 'Market' and data['order_status'] in ['Untriggered', 'Deactivated', 'Triggered']:
            _order_type = 'STOP_MARKET'

        if data['order_status'] == 'PartiallyFilled':
            data['order_status'] = 'PARTIALLY_FILLED'

        _order_name = 'order_id' if 'order_id' in data.keys() else 'stop_order_id'

        _stop_price = 0
        _executed_quantity = 0
        _executed_price = 0
        _price = 0

        if _order_type == 'Market' and data['cum_exec_qty'] != 0:
            _executed_quantity = data['cum_exec_qty']
            _executed_price = data['cum_exec_value'] / data['cum_exec_qty']

        elif _order_type == 'Limit':
            _price = data['price']
            _executed_price = data['price']
            _executed_quantity = data['cum_exec_qty']

        elif _order_type == 'TAKE_PROFIT':
            _stop_price = data['price']
            _executed_quantity = data['cum_exec_qty']
            _executed_price = data['last_exec_price']

        elif _order_type == 'STOP_MARKET':

            _stop_price = self._send_request(
                end_point=f"/private/linear/stop-order/search",
                request_type="GET",
                params={'symbol': data['symbol'], 'stop_order_id': data['order_id']},
                signed=True
            )['result']['trigger_price']
            _executed_quantity = data['cum_exec_qty']
            _executed_price = 0 if data['cum_exec_qty'] == 0 else data['cum_exec_value'] / data['cum_exec_qty']

        formatted = {
            'time': int(datetime.timestamp(date) * 1000),
            'order_id': data[_order_name],
            'pair': data['symbol'],
            'status': data['order_status'].upper(),
            'type': _order_type.upper(),
            'time_in_force': data['time_in_force'],
            'reduce_only': data['reduce_only'],
            'side': data['side'].upper(),
            'price': _price,
            'stop_price': _stop_price,
            'original_quantity': data['qty'],
            'executed_quantity': _executed_quantity,
            'executed_price': _executed_price
        }

        return formatted

    def get_order(self, pair, order_id: str):

        response = self._send_request(
            end_point=f"/private/linear/order/search",
            request_type="GET",
            params={'symbol': pair, 'order_id': order_id},
            signed=True
        )

        formated_order = self._format_order(data=response['result'])

        return formated_order

    def get_order_trades(self, pair: str, order_id: str):
        """
              Args:
                  pair: pair that is currently analysed
                  order_id: order_id number

              Returns:
                  standardize output of the trades needed to complete an order
              """

        results = self.get_order(
            pair=pair,
            order_id=order_id
        )

        trades = self._send_request(
            end_point=f"/private/linear/trade/execution/history-list",
            request_type="GET",
            params={"symbol": pair, "start_time": int(results['time'] // 1000 - 10)},
            signed=True
        )

        results['quote_asset'] = 'USDT'
        results['tx_fee_in_quote_asset'] = 0
        results['tx_fee_in_other_asset'] = {}
        results['nb_of_trades'] = 0
        results['is_buyer'] = None

        if trades['result']['data']:
            for trade in trades['result']['data']:
                if trade['order_id'] == order_id:
                    if results['is_buyer'] is None:
                        results['is_buyer'] = True if trade['side'] == 'Buy' else False
                    results['tx_fee_in_quote_asset'] += float(trade['exec_fee'])
                    results['nb_of_trades'] += 1

        return results

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

        params = {
            "side": 'Buy' if side == 'BUY' else 'Sell',
            "symbol": pair,
            "price": float(round(tp_price, self.pairs_info[pair]['pricePrecision'])),
            "qty": float(round(quantity, self.pairs_info[pair]['quantityPrecision'])),
            "order_type": 'Limit',
            "time_in_force": 'PostOnly',
            "close_on_trigger": True,
            "reduce_only": True,
            "recv_window": "5000",
            "position_idx": 0
        }

        response = self._send_request(
            end_point=f"/private/linear/order/create",
            request_type="POST",
            params=params,
            signed=True
        )

        return self.get_order(pair=pair, order_id=response['result']['order_id'])

    def place_market_sl(self, pair: str, side: str, quantity: float, sl_price: float):

        # specificity of bybit
        multi = 1.005 if side == 'SELL' else 0.995

        params = {
            "side": 'Buy' if side == 'BUY' else 'Sell',
            "symbol": pair,
            "order_type": 'Market',
            "qty": float(round(quantity, self.pairs_info[pair]['quantityPrecision'])),
            "base_price": float(round(sl_price * multi, self.pairs_info[pair]['pricePrecision'])),
            "stop_px":  float(round(sl_price, self.pairs_info[pair]['pricePrecision'])),
            "trigger_by": "LastPrice",
            "time_in_force": 'GoodTillCancel',
            "close_on_trigger": True,
            "reduce_only": True,
            "recv_window": "5000",
            "position_idx": 0
        }

        response = self._send_request(
            end_point=f"/private/linear/stop-order/create",
            request_type="POST",
            params=params,
            signed=True
        )

        return self.get_order(pair=pair, order_id=response['result']['stop_order_id'])

    def get_last_price(self, pair: str):

        data = self._send_request(
            end_point=f"/public/linear/recent-trading-records",
            request_type="GET",
            params={"symbol": pair,
                    "limit": 1},
        )

        return {
            'pair': data['result'][0]['symbol'],
            'timestamp': data['result'][0]['trade_time_ms'],
            'latest_price': float(data['result'][0]['price'])
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

        _side = 'Buy' if side == 'BUY' else 'Sell'

        params = {
            "side": _side,
            "symbol": pair,
            "price": float(round(best_price, self.pairs_info[pair]['pricePrecision'])),
            "qty": float(round(quantity, self.pairs_info[pair]['quantityPrecision'])),
            "order_type": 'Limit',
            "time_in_force": 'PostOnly',
            "close_on_trigger": False,
            "reduce_only": reduce_only,
            "recv_window": "5000",
            "position_idx": 0
        }

        response = self._send_request(
            end_point=f"/private/linear/order/create",
            request_type="POST",
            params=params,
            signed=True
        )

        if not response['result']:
            return False, ''

        limit_order_posted, order_data = self._verify_limit_posted(
            order_id=response['result']['order_id'],
            pair=pair
        )

        return limit_order_posted, order_data

    def _verify_limit_posted(self, pair: str, order_id: str):
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

        t_start = time.time()

        # Keep trying to get order status during 30s
        while time.time() - t_start < 12:

            time.sleep(1)

            order_data = self.get_order(
                pair=pair,
                order_id=order_id
            )

            if order_data['status'] == 'NEW':
                return True, order_data

        print(f'Failed to get order: {order_id}')

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
                        pair=pair,
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
        final_data['original_position_size'] = round(final_data['original_position_size'],
                                                     self.pairs_info[final_data['pair']]['quantityPrecision'])
        final_data['current_position_size'] = final_data['original_position_size']

        for _info in _price_information:
            _avg_price += _info['price'] * (_info['qty'] / final_data['current_position_size'])

        final_data['entry_price'] = round(_avg_price, self.pairs_info[final_data['pair']]['pricePrecision'])

        # needed for TP partial Execution
        final_data['last_tp_executed'] = 0
        final_data['last_tp_time'] = float('inf')
        final_data['exit_time'] = 0
        final_data['exit_fees'] = 0
        final_data['exit_price'] = 0
        final_data['quantity_exited'] = 0
        final_data['total_fees'] = 0
        final_data['realized_pnl'] = 0

        return final_data

    def cancel_order(self,
                     pair: str,
                     order_id: str):

        response = self._send_request(
            end_point=f"/private/linear/order/cancel",
            request_type="POST",
            params={"symbol": pair,
                    "order_id": order_id},
            signed=True
        )

        if response['ret_code'] == 0:
            print(f'Order id : {order_id} has been Cancelled')
        else:
            if response['ret_code'] == 20001:
                print(f'Order id : {order_id} has been already Cancelled')
            else:
                print(response['ret_msg'])

    def _set_margin_type(self,
                         pair: str,
                         margin: str = 'ISOLATED',
                         leverage: int = 1):

        params = {"symbol": pair,
                  "is_isolated": margin == 'ISOLATED',
                  "buy_leverage": leverage,
                  "sell_leverage": leverage}

        return self._send_request(
            end_point=f"/private/linear/position/switch-isolated",
            request_type="POST",
            params=params,
            signed=True
        )['result']

    def _set_leverage(self,
                      pair: str,
                      leverage: int = 1):

        params = {"symbol": pair,
                  "buy_leverage": leverage,
                  "sell_leverage": leverage}

        return self._send_request(
            end_point=f"/private/linear/position/set-leverage",
            request_type="POST",
            params=params,
            signed=True
        )['result']

    def _set_position_mode(self,
                           pair: str,
                           mode: str = 'MergedSingle'):

        params = {"symbol": pair,
                  "mode": mode}

        return self._send_request(
            end_point=f"/private/linear/position/switch-mode",
            request_type="POST",
            params=params,
            signed=True
        )['result']

    def setup_account(self,
                      quote_asset: str,
                      leverage: int,
                      list_pairs: list,
                      bankroll: float,
                      max_down: float):
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

        positions_info = self._send_request(
            end_point=f"/private/linear/position/list",
            request_type="GET",
            params={},
            signed=True
        )['result']

        for info in positions_info:

            if info['data']['symbol'] in list_pairs:

                pair = info['data']['symbol']
                current_leverage = info['data']['leverage']
                current_margin_type = 'ISOLATED' if info['data']['is_isolated'] else 'CROSS'
                current_position_mode = info['data']['mode']

                assert info['data']['size'] == 0, f'Please exit your position on {pair} before starting the bot'

                if current_position_mode != 'MergedSingle':
                    # Set position mode
                    self._set_position_mode(
                        pair=pair,
                        mode='MergedSingle'
                    )

                if current_margin_type != "ISOLATED":
                    # Set margin type to ISOLATED
                    self._set_margin_type(
                        pair=pair,
                        margin="ISOLATED",
                        leverage=leverage
                    )

                elif current_leverage != leverage:
                    # Set leverage
                    self._set_leverage(
                        pair=pair,
                        leverage=leverage
                    )

        # Check with the account has enough bk
        balance = self.get_token_balance(quote_asset=quote_asset)

        assert balance >= bankroll * (1 + max_down), f"The account has only {round(balance, 2)} {quote_asset}. " \
                                                     f"{round(bankroll * (1 + max_down), 2)} {quote_asset} is required"

    def get_actual_positions(self, pairs: Union[list, str]) -> dict:

        pos_inf = self._send_request(
            end_point=f"/private/linear/position/list",
            request_type="GET",
            params={},
            signed=True
        )['result']

        _pairs = [pairs] if isinstance(pairs, str) else pairs

        final = {}

        for i in pos_inf:

            if i['data']['symbol'] in _pairs and i['data']['size'] != 0:
                final[i['data']['symbol']] = {}
                final[i['data']['symbol']]['position_size'] = float(i['data']['size'])
                final[i['data']['symbol']]['entry_price'] = float(i['data']['entry_price'])
                final[i['data']['symbol']]['unrealized_pnl'] = float(i['data']['unrealised_pnl'])
                final[i['data']['symbol']]['type_pos'] = 'LONG' if i['data']['side'] == 'Buy' else 'SHORT'
                final[i['data']['symbol']]['exit_side'] = 'SELL' if i['data']['side'] == 'Buy' else 'BUY'

        return final

    def get_tp_sl_state(self, pair: str, tp_id: str, sl_id: str):

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

        residual_size, all_orders = self._looping_limit_orders(
            pair=pair,
            side=side,
            quantity=float(round(quantity, self.pairs_info[pair]['quantityPrecision'])),
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

        final_data['exit_price'] = round(_avg_price, self.pairs_info[final_data['pair']]['pricePrecision'])

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

        url = self.based_endpoint + '/public/linear/kline'

        final_dict = {}
        final_dict[pair] = {}

        if current_pair_state is not None:
            start_time = int(current_pair_state[pair]['latest_update'] / 1000) - \
                         int(interval_to_milliseconds(interval) / 1000)
        else:
            start_time = int(time.time() - (window + 1) * interval_to_milliseconds(interval=interval) / 1000)

        params = {
            'symbol': pair,
            'interval': self._convert_interval(interval),
            'limit': 200,
            'from': start_time
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

        # If we need more than 200 candles (which is the API's limit) we call self.get_historical_data instead
        if nb_candles > 200 and current_state is None:

            final_dict = {}

            for pair in list_pair:
                final_dict[pair] = {}
                start_time = int(1000 * time.time() - (nb_candles + 1) * interval_to_milliseconds(interval=interval))
                last_update = int(1000 * time.time())

                df = self.get_historical_data(pair=pair,
                                              start_ts=start_time,
                                              interval=interval,
                                              end_ts=int(1000 * time.time())).drop(['next_open'], axis=1)

                df = df[df['close_time'] < last_update]

                latest_update = df['open_time'].values[-1]
                for var in ['open_time', 'close_time']:
                    df[var] = pd.to_datetime(df[var], unit='ms')

                final_dict[pair]['latest_update'] = latest_update
                final_dict[pair]['data'] = df

            return final_dict

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