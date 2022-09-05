from nova.utils.helpers import interval_to_milliseconds
from nova.utils.constant import DATA_FORMATING

from requests import Request, Session
from urllib.parse import urlencode
import hashlib
import time
import hmac
import json
from decouple import config
import pandas as pd


class Bybit:

    def __init__(self,
                 key: str,
                 secret: str,
                 _testnet: bool = False):

        self.api_key = key
        self.api_secret = secret

        self.based_endpoint = "https://api-testnet.bybit.com" if _testnet else "https://api.bybit.com"

        self._session = Session()

        self.historical_limit = 200

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

    def _get_kline(self,
                   pair: str, interval: str, start_time: int,
                   limit: int = 200) -> list:

        """

        Args:
            pair: pair to get the candles
            interval: Data refresh interval. Enum : 1 3 5 15 30 60 120 240 360 720 "D" "M" "W"
            start_time: From timestamp in seconds
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

    def get_pairs_info(self,
                       quote_asset) -> dict:
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
            quote_currency = pair['quote_currency'] == quote_asset

            if tradable and quote_currency:
                pairs_info[pair['name']] = {}
                pairs_info[pair['name']]['pair'] = pair['name']
                pairs_info[pair['name']]['pricePrecision'] = pair['price_scale']
                pairs_info[pair['name']]['max_market_trading_qty'] = pair['lot_size_filter']['max_trading_qty']
                ## qty precision ??

        return pairs_info

    def _get_earliest_valid_timestamp(self, pair: str, interval: str) -> int:
        """
        Args:
            pair: Name of symbol pair -- BNBBTC
            interval: Binance Kline interval

        return:
            the earliest valid open timestamp
        """
        # 946684800000 == Jan 1st 2020

        kline = self._get_kline(
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

    @staticmethod
    def _format_data(klines: list, historical: bool = True) -> pd.DataFrame:
        """
        Args:
            all_data: output from _full_history

        Returns:
            standardized pandas dataframe
        """
        # Remove the last row bc it's not finished yet
        if historical:
            del klines[-1]

        df = pd.DataFrame(klines)[DATA_FORMATING['bybit']['columns']]

        for var in DATA_FORMATING['bybit']['num_var']:
            df[var] = pd.to_numeric(df[var], downcast="float")

        df['open_time'] = 1000 * df['open_time']

        if historical:
            df['next_open'] = df['open'].shift(-1)

        return df.dropna()

    def get_historical_data(self, pair: str, interval: str, start_ts: int, end_ts: int) -> pd.DataFrame:
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
            temp_data = self._get_kline(
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

        df = self._format_data(klines=klines)

        df['close_time'] = df['open_time'] + timeframe - 1

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

    def _get_active_order(self,
                          pair,
                          order_id):

        response = self._send_request(
            end_point=f"/private/linear/order/list",
            request_type="GET",
            params={"symbol": pair,
                    "order_id": order_id},
            signed=True
        )

        return response.json()['result']['data']

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
        t_start = time.time()

        # Keep trying to get order status during 30s
        while time.time() - t_start < 30:

            time.sleep(3)

            last_active_order = self._get_active_order(pair=pair,
                                                       order_id=order_id)
            if last_active_order:
                break

        if not last_active_order:
            raise ValueError("Failed to retrieve limit order")

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

        limit_order_posted = self._verify_limit_order_posted(order_id=response['order_id'],
                                                             pair=pair)

        return limit_order_posted, response['order_id']

    def place_limit_tp(self,
                       pair: str,
                       side: str,
                       qty: float,
                       tp_prc: float):
        """
        Place a limit order as Take Profit.
        (The market SL is place when entering in position)

        Args:
            pair:
            side:
            qty:
            tp_prc:

        Returns:
            response of the API call
        """

        response = self._send_order(pair=pair,
                                    side=side,
                                    qty=qty,
                                    price=tp_prc,
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

    def enter_limit_then_market(self,
                                pair,
                                side,
                                sl_price,
                                price_precision,
                                qty):

        residual_size = qty

        t_start = time.time()

        while (residual_size != 0) and (time.time() - t_start < 120):

            posted, order_id = self._send_limit_order_at_best_price(pair=pair,
                                                                    side=side,
                                                                    qty=residual_size,
                                                                    sl_price=sl_price,
                                                                    reduce_only=False)

            if posted:
                time.sleep(10)

                # Cancel order
                self._cancel_order(pair=pair,
                                   order_id=order_id)

                # Get current position size
                pos_info = self._get_position_info(pair=pair)

                residual_size = round(qty - pos_info[0]['size'], price_precision)

        if residual_size != 0:
            self.enter_market(pair=pair,
                              side=side,
                              qty=residual_size,
                              sl_price=sl_price)

    def exit_limit_then_market(self,
                               pair,
                               side,
                               qty):

        residual_size = qty

        t_start = time.time()

        while (residual_size != 0) and (time.time() - t_start < 120):

            posted, order_id = self._send_limit_order_at_best_price(pair=pair,
                                                                    side=side,
                                                                    qty=residual_size,
                                                                    reduce_only=True)

            if posted:
                # Cancel order
                self._cancel_order(pair=pair,
                                   order_id=order_id)

                # Get current position size
                pos_info = self._get_position_info(pair=pair)

                residual_size = pos_info[0]['size']

        if residual_size != 0:
            self.exit_market(pair=pair,
                             side=side,
                             qty=residual_size)


self = Bybit(key=config('BYBIT_KEY_TEST'),
             secret=config('BYBIT_SECRET_TEST'),
             _testnet=True)

pair = 'BTCUSDT'
qty = 0.1
sl_price = 19000
price_precision = 3
side = 'Buy'

while True:
    self.enter_limit_then_market(pair=pair,
                                 side='Buy',
                                 qty=qty,
                                 price_precision=price_precision,
                                 sl_price=sl_price)

    time.sleep(20)

    pos_info = self._get_position_info(pair=pair)

    pos_size = pos_info[0]['size']

    assert pos_size == qty, "wrong qty !"

    self.exit_limit_then_market(pair=pair,
                                side='Sell',
                                qty=qty)

    time.sleep(10)

    pos_info = self._get_position_info(pair=pair)

    pos_size = pos_info[0]['size']

    assert pos_size == 0, "did not exit all pos"

    time.sleep(10)
