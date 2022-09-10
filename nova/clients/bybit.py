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
from multiprocessing import Process, Manager


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

        return response

    def get_server_time(self) -> int:
        """
        Returns:
            the timestamp in milliseconds
        """
        data = self._send_request(
            end_point=f"/public/time",
            request_type="GET"
        )

        ts = float(data.json()['time_now'])

        return int(ts * 1000)

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

        params = {
            'symbol': pair,
            'interval': interval,
            'from': start_time // 1000,
            'limit': limit
        }
        data = self._send_request(
            end_point=f"/public/linear/kline",
            request_type="GET",
            params=params
        )
        return data.json()['result']

    def get_pairs_info(self) -> dict:
        """
        Returns:
            All pairs available and tradable on the exchange.
        """
        data = self._send_request(
            end_point=f"/v2/public/symbols",
            request_type="GET"
        ).json()['result']

        pairs_info = {}

        for pair in data:
            tradable = pair['status'] == 'Trading'

            if tradable:
                pairs_info[pair['name']] = {}
                pairs_info[pair['name']]['pair'] = pair['name']
                pairs_info[pair['name']]['quote_asset'] = pair['quote_currency']
                pairs_info[pair['name']]['pricePrecision'] = pair['price_scale']
                pairs_info[pair['name']]['max_market_trading_qty'] = pair['lot_size_filter']['max_trading_qty']

        return pairs_info

    def _get_earliest_valid_timestamp(self,
                                      pair: str,
                                      interval: str) -> int:
        """
        Args:
            pair: Name of symbol pair -- BNBBTC
            interval: Binance Kline interval

        return:
            the earliest valid open timestamp
        """
        # 946684800000 == Jan 1st 2020

        kline = self._get_candles(
            pair=pair,
            interval=interval,
            start_time=946684800000,
            limit=1
        )

        return kline[0]['open_time']

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

    def _format_data(self,
                     klines: list,
                     timeframe: int,
                     historical: bool = True) -> pd.DataFrame:
        """
        Args:
            all_data: output from _full_history

        Returns:
            standardized pandas dataframe
        """
        # Remove the last row bc it's not finished yet
        if historical:
            interval_seconds = klines[1]['start_at'] - klines[0]['start_at']
            if self.get_server_time() < 1000 * (klines[-1]['start_at'] + interval_seconds):
                del klines[-1]

        df = pd.DataFrame(klines)[DATA_FORMATING['bybit']['columns']]

        for var in DATA_FORMATING['bybit']['num_var']:
            df[var] = pd.to_numeric(df[var], downcast="float")

        df['open_time'] = 1000 * df['open_time']

        if historical:
            df['next_open'] = df['open'].shift(-1)

        df['close_time'] = df['open_time'] + timeframe - 1

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

        # Convert standardized interval to Bybit specific interval
        interval = self._convert_interval(std_interval=interval)

        # establish first available start timestamp
        if start_ts is not None:
            first_valid_ts = self._get_earliest_valid_timestamp(
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

        df = self._format_data(klines=klines,
                               timeframe=timeframe)

        return df

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

    def _get_balance(self):

        data = self._send_request(
            end_point=f"/v2/private/wallet/balance",
            request_type="GET",
            signed=True
        )

        return data.json()['result']

    def get_token_balance(self, quote_asset: str):
        """
        Args:
            quote_asset: asset used for the trades (USD, USDT, BUSD, ...)

        Returns:
            Available quote_asset amount.
        """
        balances = self._get_balance()

        return float(balances[quote_asset]['available_balance'])

    def get_order_book(self,
                       pair):

        data = self._send_request(
            end_point=f"/v2/public/orderBook/L2",
            request_type="GET",
            params={'symbol': pair}
        )

        OB = data.json()['result']

        std_OB = {'buy': [], 'sell': []}

        for order in OB:
            std_OB[order['side'].lower()].append({'price': order['price'],
                                                  'size': order['size']})

        return std_OB

    def _send_order(self,
                    pair,
                    side,
                    order_type,
                    qty,
                    price: float = None,
                    sl_price: float = None,
                    time_in_force: str = "GoodTillCancel",
                    reduce_only: bool = False,
                    close_on_trigger: bool = False):

        params = {
            "side": side,
            "symbol": pair,
            "order_type": order_type,
            "qty": qty,
            "time_in_force": time_in_force,
            "reduce_only": reduce_only,
            "close_on_trigger": close_on_trigger,
            "recv_window": "5000",
            "position_idx": 0
        }

        if sl_price:
            params["stop_loss"] = sl_price

        if order_type == 'Limit':
            params['price'] = price

        response = self._send_request(
            end_point=f"/private/linear/order/create",
            request_type="POST",
            params=params,
            signed=True
        )

        return response.json()['result']

    def enter_market(self,
                     pair,
                     side,
                     qty,
                     sl_price):

        response = self._send_order(pair=pair,
                                    side=side,
                                    order_type='Market',
                                    qty=qty,
                                    sl_price=sl_price,
                                    reduce_only=False)

        return response

    def exit_market(self,
                    pair,
                    side,
                    qty):

        response = self._send_order(pair=pair,
                                    side=side,
                                    order_type='Market',
                                    qty=qty,
                                    reduce_only=True)

        return response

    def get_order(self,
                  pair,
                  order_id):

        response = self._send_request(
            end_point=f"/private/linear/order/list",
            request_type="GET",
            params={"symbol": pair,
                    "order_id": order_id},
            signed=True
        )

        if response.json()['result']:
            return response.json()['result']['data']
        else:
            return None

    def _cancel_order(self,
                      pair: str,
                      order_id: str):

        response = self._send_request(
            end_point=f"/private/linear/order/cancel",
            request_type="POST",
            params={"symbol": pair,
                    "order_id": order_id},
            signed=True
        )

        return response.json()['result']

    def get_last_price(self, pair):

        response = self._send_request(
            end_point=f"/public/linear/recent-trading-records",
            request_type="GET",
            params={"symbol": pair,
                    "limit": 1},
        )

        return response.json()['result'][0]['price']

    def _verify_limit_order_posted(self,
                                   pair: str,
                                   order_id: str):
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

        last_active_order = None

        # Keep trying to get order status during 30s
        idx = 0
        while not last_active_order:

            # Security
            if idx >= 10:
                raise ConnectionError('Failed to retrieve order')

            time.sleep(5)

            last_active_order = self.get_order(pair=pair,
                                               order_id=order_id)

            idx += 1

        return last_active_order[0]['order_status'] != 'Cancelled'

    def _send_limit_order_at_best_price(self,
                                        pair,
                                        side,
                                        qty,
                                        reduce_only: bool = False,
                                        sl_price: float = None):
        """
        Send a limit order at first OrderBook price. This allows trader to be sure to enter in market order and have
        0.01% fees instead of 0.06% for taker.
        The param time_in_force='PostOnly' ensure that the order isn't executed immediately.

        It also verify if the order has been posted (cf. self._verify_limit_order_posted()).

        Args:
            pair:
            side:
            qty:
            reduce_only: True if we are closing a position, False else.
            sl_price: Stop loss price if we enter in position. The SL is placed as conditional market order
                        (price triggered = Last Price)

        Returns:
            1 - returns True if the limit order has been posted, else False
            2 - returns the order_id
        """

        orderBook = self.get_order_book(pair=pair)

        price = float(orderBook[side.lower()][0]['price'])

        response = self._send_order(pair=pair,
                                    side=side,
                                    price=price,
                                    order_type='Limit',
                                    qty=qty,
                                    sl_price=sl_price,
                                    reduce_only=reduce_only,
                                    time_in_force='PostOnly')

        if not response:
            return False, ''

        limit_order_posted = self._verify_limit_order_posted(order_id=response['order_id'],
                                                             pair=pair)

        return limit_order_posted, response

    def place_limit_tp(self,
                       pair: str,
                       side: str,
                       position_size: float,
                       tp_price: float):
        """
        Place a limit order as Take Profit.
        (The market SL is place when entering in position)

        Args:
            pair:
            side:
            position_size:
            tp_price:

        Returns:
            response of the API call
        """

        response = self._send_order(pair=pair,
                                    side=side,
                                    qty=position_size,
                                    price=tp_price,
                                    reduce_only=True,
                                    order_type='Limit',
                                    time_in_force='PostOnly')

        return response

    def _set_margin_type(self,
                         pair: str,
                         margin: str = 'ISOLATED',
                         leverage: int = 1):

        params = {"symbol": pair,
                  "is_isolated": margin == 'ISOLATED',
                  "buy_leverage": leverage,
                  "sell_leverage": leverage}

        response = self._send_request(
            end_point=f"/private/linear/position/switch-isolated",
            request_type="POST",
            params=params,
            signed=True
        )

        return response.json()['result']

    def _set_leverage(self,
                      pair: str,
                      leverage: int = 1):

        params = {"symbol": pair,
                  "buy_leverage": leverage,
                  "sell_leverage": leverage}

        response = self._send_request(
            end_point=f"/private/linear/position/set-leverage",
            request_type="POST",
            params=params,
            signed=True
        )

        return response.json()['result']

    def _set_position_mode(self,
                           pair: str,
                           mode: str = 'MergedSingle'):

        params = {"symbol": pair,
                  "mode": mode}

        response = self._send_request(
            end_point=f"/private/linear/position/switch-mode",
            request_type="POST",
            params=params,
            signed=True
        )

        return response.json()['result']

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

        positions_info = self._get_position_info()

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

    def _get_position_info(self,
                           pair: str = None):

        params = {}
        if pair:
            params = {'symbol': pair}

        response = self._send_request(
            end_point=f"/private/linear/position/list",
            request_type="GET",
            params=params,
            signed=True
        )

        return response.json()['result']

    def get_actual_positions(self,
                             list_pair: list):

        pos_inf = self._get_position_info()

        positions = {}

        for pos in pos_inf:
            pair = pos['data']['symbol']
            amt = pos['data']['size']
            if (pair in list_pair) and (amt != 0):
                positions[pair] = pos['data']

        return positions

    def _looping_limit_orders(self,
                              pair: str,
                              side: str,
                              position_size: float,
                              duration: int,
                              reduce_only: bool,
                              sl_price: float = None):
        """
        This function will try to enter in position by sending only limit orders to be sure to pay limit orders fees.

        Args:
            pair:
            side:
            position_size:
            duration: number of seconds we keep trying to enter in position with limit orders
            reduce_only: True if we are exiting a position

        Returns:
            Residual size to fill the based qty
        """

        residual_size = position_size

        t_start = time.time()

        all_limit_orders = []

        # Try to enter with limit order during 2 min
        while (residual_size != 0) and (time.time() - t_start < duration):

            posted, order = self._send_limit_order_at_best_price(pair=pair,
                                                                 side=side,
                                                                 qty=residual_size,
                                                                 reduce_only=reduce_only,
                                                                 sl_price=sl_price)

            if posted:

                all_limit_orders.append(order)

                new_price = order['price']
                order_status = order['order_status']

                # If the best order book price stays the same, do not cancel current order
                while (new_price == order['price']) and (time.time() - t_start < 120) and (order_status != 'Filled'):
                    time.sleep(10)

                    orderBook = self.get_order_book(pair=pair)
                    new_price = float(orderBook[side.lower()][0]['price'])

                    order_status = self.get_order(pair=pair, order_id=order['order_id'])

                # Cancel order
                self._cancel_order(pair=pair,
                                   order_id=order['order_id'])

                # Get current position size
                pos_info = self._get_position_info(pair=pair)

                if reduce_only:
                    residual_size = pos_info[0]['size']
                else:
                    residual_size = position_size - pos_info[0]['size']

        return {'residual_size': residual_size, 'all_limit_orders': all_limit_orders}

    def _get_all_filled_orders(self, orders: list):

        final_state_orders = []

        for order in orders:

            order_status = 'New'

            idx = 0
            while not (order_status in ['Filled', 'Cancelled']):

                # Security
                if idx >= 10:
                    raise ConnectionError('Failed to retrieve order')

                final_order = self.get_order(pair=order['symbol'],
                                             order_id=order['order_id'])
                if final_order:
                    order_status = final_order[0]['order_status']

                time.sleep(3)
                idx += 1

            if final_order[0]['cum_exec_qty'] != 0:
                final_state_orders.append(final_order[0])

        return final_state_orders

    def _enter_limit_then_market(self,
                                 pair,
                                 side,
                                 qty,
                                 sl_price,
                                 tp_price,
                                 return_dict):
        """
        Optimized way to enter in position. The method tries to enter with limit orders during 2 minutes.
        If after 2min we still did not entered with the desired amount, a market order is sent.

        Args:
            pair:
            side:
            sl_price:
            qty:

        Returns:
            Size of the current position
        """

        sl_price = round(sl_price, self.pairs_info[pair]['pricePrecision'])

        after_looping_limit = self._looping_limit_orders(pair=pair, side=side, position_size=qty, sl_price=sl_price,
                                                         duration=120, reduce_only=False)

        residual_size = after_looping_limit['residual_size']
        all_orders = after_looping_limit['all_limit_orders']

        # If there is residual, enter with market order
        if residual_size != 0:
            market_order = self.enter_market(pair=pair,
                                             side=side,
                                             qty=residual_size,
                                             sl_price=sl_price)

            if market_order:
                all_orders.append(market_order)

        # Get current position info
        pos_info = self._get_position_info(pair=pair)

        tp_side = 'Sell' if side == 'Buy' else 'Buy'

        # Place take profit limit order
        self.place_limit_tp(pair=pair,
                            side=tp_side,
                            position_size=pos_info[0]['size'],
                            tp_price=round(tp_price, self.pairs_info[pair]['pricePrecision']))

        return_dict[pair] = self._get_all_filled_orders(orders=all_orders)

    def _exit_limit_then_market(self,
                                pair,
                                side,
                                position_size,
                                return_dict):
        """
        Optimized way to exit position. The method tries to exit with limit orders during 2 minutes.
        If after 2min we still did not exit totally, a market order is sent.

        Args:
            pair:
            side:
        """

        after_looping_limit = self._looping_limit_orders(pair=pair, side=side, position_size=position_size,
                                                         duration=120, reduce_only=True)

        residual_size = after_looping_limit['residual_size']
        all_orders = after_looping_limit['all_limit_orders']

        # If there is residual, exit with market order
        if residual_size != 0:
            market_order = self.exit_market(pair=pair,
                                            side=side,
                                            qty=residual_size)

            if market_order:
                all_orders.append(market_order)

        return_dict[pair] = self._get_all_filled_orders(orders=all_orders)

    @staticmethod
    def prepare_args(args: dict,
                     return_dict: dict) -> tuple:
        args = tuple(args.values()) + (return_dict,)

        return args

    def enter_limit_then_market(self,
                                orders: list) -> dict:
        """
        Parallelize the execution of _enter_limit_then_market.
        Args:
            orders: list of dict. Each element represents the params of an order.
            [{'pair': 'BTCUSDT', 'side': 'Buy', 'qty': 0.1, 'sl_price': 18000, 'tp_price': 20000},
             {'pair': 'ETHUSDT', 'side': 'Buy', 'qty': 1, 'sl_price': 1200, 'tp_price': 2000}]
        Returns:
            list of positions info after executing all enter orders.
        """

        manager = Manager()
        return_dict = manager.dict()

        running_tasks = [Process(target=self._enter_limit_then_market, args=self.prepare_args(order, return_dict)) for
                         order in
                         orders]

        for running_task in running_tasks:
            running_task.start()

        for running_task in running_tasks:
            running_task.join()

        return dict(return_dict)

    def exit_limit_then_market(self,
                               orders: list) -> dict:

        """
        Parallelize the execution of _exit_limit_then_market.
        Args:
            orders: list of dict. Each element represents the params of an order.
            [{'pair': 'BTCUSDT', 'side': 'Sell', 'position_size': 0.1},
             {'pair': 'ETHUSDT', 'side': 'Sell', 'position_size': 1}]
        Returns:
            list of positions info after executing all exit orders.
        """

        manager = Manager()
        return_dict = manager.dict()

        running_tasks = [Process(target=self._exit_limit_then_market, args=self.prepare_args(order, return_dict)) for
                         order in
                         orders]

        for running_task in running_tasks:
            running_task.start()

        for running_task in running_tasks:
            running_task.join()

        return dict(return_dict)

    async def get_prod_candles(self, session, pair, interval, window, current_pair_state: dict = None):

        url = self.based_endpoint + '/public/linear/kline'

        final_dict = {}
        final_dict[pair] = {}

        if current_pair_state is not None:
            start_time = int((current_pair_state[pair]['latest_update'] - interval_to_milliseconds(interval=interval)) / 1000)
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

            df = self._format_data(data['result'],
                                   timeframe=interval_to_milliseconds(interval=interval),
                                   historical=False)

            df = df[df['close_time'] < s_time]

            for var in ['open_time', 'close_time']:
                df[var] = pd.to_datetime(df[var], unit='ms')

            if current_pair_state is None:
                final_dict[pair]['latest_update'] = s_time
                final_dict[pair]['data'] = df

            else:
                df_new = pd.concat([current_pair_state[pair]['data'], df])
                df_new = df_new.drop_duplicates(subset=['open_time']).sort_values(by=['open_time'],
                                                                                  ascending=True)
                df_new = df_new.tail(window)
                df_new = df_new.reset_index(drop=True)

                final_dict[pair]['latest_update'] = s_time
                final_dict[pair]['data'] = df_new

            return final_dict

    async def get_prod_data(self, list_pair: list, interval: str, nb_candles: int, current_state: dict):
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
                                              end_ts=int(1000 * time.time()))

                df = df[df['close_time'] < last_update]

                for var in ['open_time', 'close_time']:
                    df[var] = pd.to_datetime(df[var], unit='ms')

                final_dict[pair]['latest_update'] = last_update
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
