from requests import Request, Session
import hmac
import base64
import json
from datetime import datetime, date
from nova.utils.helpers import interval_to_milliseconds
import time
from nova.utils.constant import DATA_FORMATING
import pandas as pd
import aiohttp
import asyncio
from typing import Union


class OKX:

    def __init__(self,
                 key: str,
                 secret: str,
                 pass_phrase: str,
                 testnet: bool):
        self.api_key = key
        self.api_secret = secret
        self.pass_phrase = pass_phrase

        self.historical_limit = 100

        self.based_endpoint = "https://www.okx.com"
        self._session = Session()

        self.quote_asset = 'USDT'

        self.pairs_info = self.get_pairs_info()

    def _send_request(self, end_point: str, request_type: str, params: Union[dict, list] = None, signed: bool = False):

        now = datetime.utcnow()
        timestamp = now.isoformat("T", "milliseconds") + "Z"

        request = Request(request_type, f'{self.based_endpoint}{end_point}', data=json.dumps(params))
        prepared = request.prepare()

        if signed:
            body = ""
            if params:
                body = json.dumps(params)
                prepared.body = body

            to_hash = str(timestamp) + str.upper(request_type) + end_point + body

            mac = hmac.new(bytes(self.api_secret, encoding='utf8'),
                           bytes(to_hash, encoding='utf-8'),
                           digestmod='sha256')

            signature = base64.b64encode(mac.digest())

            prepared.headers['OK-ACCESS-KEY'] = self.api_key
            prepared.headers['OK-ACCESS-SIGN'] = signature
            prepared.headers['OK-ACCESS-PASSPHRASE'] = self.pass_phrase

        prepared.headers['Content-Type'] = "application/json"
        prepared.headers['OK-ACCESS-TIMESTAMP'] = timestamp

        response = self._session.send(prepared)

        return response.json()

    def get_server_time(self) -> int:
        """
        Note: FTX does not have any server time end point so we are simulating it with the time function
        Returns:
            the timestamp in milliseconds
        """
        return int(self._send_request(
            end_point=f"/api/v5/public/time",
            request_type="GET",
        )['data'][0]['ts'])

    def get_pairs_info(self) -> dict:

        data = self._send_request(
            end_point=f"/api/v5/public/instruments?instType=MARGIN",
            request_type="GET"
        )['data']

        pairs_info = {}

        for pair in data:

            if pair['state'] == 'live':
                pairs_info[pair['instId']] = {}
                pairs_info[pair['instId']]['quote_asset'] = pair['quoteCcy']
                pairs_info[pair['instId']]['pricePrecision'] = int(str(pair['tickSz'])[::-1].find('.'))
                pairs_info[pair['instId']]['maxQuantity'] = float(pair['maxMktSz'])
                pairs_info[pair['instId']]['minQuantity'] = float(pair['minSz'])
                pairs_info[pair['instId']]['tick_size'] = float(pair['tickSz'])
                pairs_info[pair['instId']]['quantityPrecision'] = int(str(pair['minSz'])[::-1].find('.'))

        return pairs_info

    def _get_candles(self, pair: str, interval: str, start_time: int, end_time: int):
        """
        Args:
            pair: pair to get information from
            interval: granularity of the candle ['1m', '1h', ... '1d']
            start_time: timestamp in milliseconds of the starting date
            end_time: timestamp in milliseconds of the end date
        Returns:
            the none formatted candle information requested
        """
        _end_time = start_time + interval_to_milliseconds(interval) * self.historical_limit
        _bar = interval if 'm' in interval else interval.upper()
        _endpoint = f"/api/v5/market/history-candles?instId={pair}&bar={_bar}&before={start_time}&after={_end_time}"
        return self._send_request(
            end_point=_endpoint,
            request_type="GET",
        )['data']

    def _get_earliest_timestamp(self, pair: str, interval: str):
        """
        Note we are using an interval of 4 days to make sure we start at the beginning
        of the time
        Args:
            pair: Name of symbol pair
            interval: interval in string
        return:
            the earliest valid open timestamp in milliseconds
        """

        starting_year = 2018

        while starting_year <= date.today().year:
            kline = self._get_candles(
                pair=pair,
                interval=interval,
                start_time=int(datetime(starting_year, 1, 1).timestamp() * 1000),
                end_time=0
            )

            if len(kline) > 0:

                print(f'Starting Year date {starting_year}')

                return int(kline[-1][0])

        return time.time() * 1000

    @staticmethod
    def _format_data(all_data: list, historical: bool = True) -> pd.DataFrame:
        """
        Args:
            all_data: output from _full_history

        Returns:
            standardized pandas dataframe
        """

        df = pd.DataFrame(all_data, columns=DATA_FORMATING['okx']['columns'])

        for var in DATA_FORMATING['okx']['num_var']:
            df[var] = pd.to_numeric(df[var], downcast="float")

        for var in ['open_time']:
            df[var] = df[var].astype(int)

        df = df.sort_values(by='open_time').reset_index(drop=True)

        if historical:
            df['next_open'] = df['open'].shift(-1)

        interval_ms = df.loc[1, 'open_time'] - df.loc[0, 'open_time']

        df['close_time'] = df['open_time'] + interval_ms - 1

        return df.dropna()

    def get_historical_data(self, pair: str, interval: str, start_ts: int, end_ts: int) -> pd.DataFrame:
        """
        Note : There is a problem when computing the earliest timestamp for pagination, it seems that the
        earliest timestamp computed in "days" does not match the minimum timestamp in hours.

        In the
        Args:
            pair: pair to get information from
            interval: granularity of the candle ['1m', '1h', ... '1d']
            start_ts: timestamp in milliseconds of the starting date
            end_ts: timestamp in milliseconds of the end date
        Returns:
            historical data requested in a standardized pandas dataframe
        """
        # init our list
        klines = []

        # convert interval to useful value in seconds
        timeframe = interval_to_milliseconds(interval)

        first_valid_ts = self._get_earliest_timestamp(
            pair=pair,
            interval=interval
        )

        start_time = max(start_ts, first_valid_ts)

        idx = 0
        while True:

            end_t = int(start_time + timeframe * self.historical_limit)
            end_time = min(end_t, end_ts)

            # fetch the klines from start_ts up to max 500 entries or the end_ts if set
            temp_data = self._get_candles(
                pair=pair,
                interval=interval,
                start_time=start_time,
                end_time=end_time
            )

            print(start_time, end_time)

            # append this loops data to our output data
            if temp_data:
                klines += temp_data

            # handle the case where exactly the limit amount of data was returned last loop
            # check if we received less than the required limit and exit the loop
            if not len(temp_data) or len(temp_data) < self.historical_limit:
                print('inside 1')
                # exit the while loop
                break

            # increment next call by our timeframe
            start_time = int(float(temp_data[0][0]) + timeframe)

            # exit loop if we reached end_ts before reaching <limit> klines
            if end_time and start_time >= end_ts:
                print('inside 2')

                break

            # sleep after every 3rd call to be kind to the API
            idx += 1
            if idx % 3 == 0:
                time.sleep(1)

        data = self._format_data(all_data=klines)

        return data[(data['open_time'] >= start_ts) & (data['open_time'] <= end_ts)]

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
        df = self.get_historical_data(
            pair=pair,
            interval=interval,
            start_ts=end_date_data_ts,
            end_ts=int(time.time() * 1000)
        )
        return pd.concat([current_df, df], ignore_index=True).drop_duplicates(subset=['open_time'])

    def setup_account(self, quote_asset: str, leverage: int, bankroll: float, max_down: float, list_pairs: list):

        for pair in list_pairs:
            _set_leverage = self._send_request(
                end_point=f"/api/v5/account/set-leverage",
                request_type="POST",
                params={
                    "instId": pair,
                    "lever": str(leverage),
                    'mgnMode': 'cross'
                },
                signed=True
            )['data']

            assert _set_leverage[0]['lever'] == str(leverage)
            assert _set_leverage[0]['mgnMode'] == 'cross'

        self.quote_asset = quote_asset

        balance = float(self._send_request(
            end_point=f"/api/v5/account/balance",
            request_type="GET",
            params={
                "ccy": quote_asset
            },
            signed=True
        )['data'][0]['details'][0]['availEq'])

        assert balance >= bankroll * (1 + max_down), f"The account has only {round(balance, 2)} {quote_asset}. " \
                                                     f"{round(bankroll * (1 + max_down), 2)} {quote_asset} is required"

    async def get_prod_candles(
            self,
            session,
            pair: str,
            interval: str,
            window: int,
            current_pair_state: dict = None
    ):
        milli_sec = interval_to_milliseconds(interval) // 1000
        end_time = int(time.time())
        start_time = int(end_time - (window + 1) * milli_sec)

        input_req = f"api/markets/{pair}/candles?resolution={milli_sec}&start_time={start_time}&end_time={end_time}"

        url = f"{self.based_endpoint}{input_req}"

        final_dict = {}
        final_dict[pair] = {}

        if current_pair_state is not None:
            limit = 3
            final_dict[pair]['data'] = current_pair_state[pair]['data']
            final_dict[pair]['latest_update'] = current_pair_state[pair]['latest_update']
        else:
            limit = window

        params = dict(symbol=pair, interval=interval, limit=limit)

        # Compute the server time
        s_time = int(1000 * time.time())

        async with session.get(url=url, params=params) as response:
            data = await response.json()

            df = self._format_data(all_data=data['result'], historical=False)

            df = df[df['close_time'] < s_time]

            for var in ['open_time', 'close_time']:
                df[var] = pd.to_datetime(df[var], unit='ms')

            if current_pair_state is None:
                final_dict[pair]['latest_update'] = s_time
                final_dict[pair]['data'] = df

            else:
                df_new = pd.concat([final_dict[pair]['data'], df])
                df_new = df_new.drop_duplicates(subset=['open_time']).sort_values(
                    by=['open_time'],
                    ascending=True
                )
                final_dict[pair]['latest_update'] = s_time
                final_dict[pair]['data'] = df_new.tail(window)

            return final_dict

    async def get_prod_data(self,
                            list_pair: list,
                            interval: str,
                            nb_candles: int,
                            current_state: dict):
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

    def get_token_balance(self, quote_asset: str):

        balance = float(self._send_request(
            end_point=f"/api/v5/account/balance",
            request_type="GET",
            params={
                "ccy": quote_asset
            },
            signed=True
        )['data'][0]['details'][0]['availEq'])
        print(f'The current amount is : {round(balance, 2)} {quote_asset}')

        return round(balance, 2)

    def get_order_book(self, pair: str):
        """
        Args:
            pair:

        Returns:
            the current orderbook with a depth of 20 observations
        """

        data = self._send_request(
            end_point=f'/api/v5/market/books?instId={pair}&sz=10',
            request_type="GET",
            signed=False
        )['data'][0]

        std_ob = {'bids': [], 'asks': []}

        for i in range(len(data['asks'])):
            std_ob['bids'].append({
                'price': float(data['bids'][i][0]),
                'size': float(data['bids'][i][1])
            })

            std_ob['asks'].append({
                'price': float(data['asks'][i][0]),
                'size': float(data['asks'][i][1])
            })

        return std_ob

    def get_last_price(self, pair: str) -> dict:
        """
        Args:
            pair: pair desired
        Returns:
            a dictionary containing the pair_id, latest_price, price_timestamp in timestamp
        """
        data = self._send_request(
            end_point=f"/api/v5/market/ticker?instId={pair}",
            request_type="GET",
            signed=False
        )['data'][0]

        return {
            'pair': data['instId'],
            'timestamp': int(time.time()*1000),
            'latest_price': float(data['last'])
        }

    def enter_market_order(self, pair: str, type_pos: str, quantity: float):

        """
            Args:
                pair: pair id that we want to create the order for
                type_pos: could be 'LONG' or 'SHORT'
                quantity: quantity should respect the minimum precision

            Returns:
                standardized output
        """

        side = 'buy' if type_pos == 'LONG' else 'sell'

        quote_size = 0

        if side == 'buy':
            last_price = self.get_last_price(pair=pair)
            quote_size = last_price['latest_price'] * quantity

        _quantity = quantity if side == 'sell' else quote_size

        _params = {
            "instId": pair,
            "tdMode": "cross",
            "ccy": "USDT",
            "side": side,
            "sz": str(float(round(_quantity, self.pairs_info[pair]['quantityPrecision']))),
            "ordType": "market",
        }

        response = self._send_request(
            end_point=f"/api/v5/trade/order",
            request_type="POST",
            params=_params,
            signed=True
        )

        return response

    def exit_market_order(self, pair: str, type_pos: str, quantity: float):

        """
            Args:
                pair: pair id that we want to create the order for
                type_pos: could be 'LONG' or 'SHORT'
                quantity: quantity should respect the minimum precision

            Returns:
                standardized output
        """

        side = 'sell' if type_pos == 'LONG' else 'buy'

        quote_size = 0

        if side == 'buy':
            last_price = self.get_last_price(pair=pair)
            quote_size = last_price['latest_price'] * quantity * 1.02

        _quantity = quantity if side == 'sell' else quote_size

        _params = {
            "instId": pair,
            "tdMode": "cross",
            "ccy": self.quote_asset,
            "reduceOnly": True,
            "side": side,
            "sz": str(float(round(_quantity, self.pairs_info[pair]['quantityPrecision']))),
            "ordType": "market",
        }

        response = self._send_request(
            end_point=f"/api/v5/trade/order",
            request_type="POST",
            params=_params,
            signed=True
        )

        return response

    def get_order(self, pair: str, order_id: str):
        """
        Note : to query the conditional order, we are setting the following assumptions
            - The position is not kept more thant 5 days
            -
        Args:
            pair: pair traded in the order
            order_id: order id

        Returns:
            order information from binance
        """
        data = self._send_request(
            end_point=f"/api/v5/trade/order?instId={pair}&ordId={order_id}",
            request_type="GET",
            params={
                "instId": pair,
                "ordId": order_id,
            },
            signed=True
        )

        return data

    @staticmethod
    def _format_order(data: dict):

        _order_type = 'STOP_MARKET' if data['type'] == 'stop' else data['type'].upper()

        _price = 0.0 if _order_type in ["MARKET", "STOP_MARKET", "TAKE_PROFIT"] else data['price']
        _stop_price = 0.0 if _order_type in ["MARKET", "LIMIT"] else data['triggerPrice']
        _time_in_force = 'IOC' if 'ioc' in data.keys() and data['ioc'] else 'GTC'

        dt = datetime.strptime(data['createdAt'], '%Y-%m-%dT%H:%M:%S.%f+00:00')

        _executed_price = 0 if data['avgFillPrice'] is None else data['avgFillPrice']

        formatted = {
            'time': int(dt.timestamp() * 1000),
            'order_id': data['id'],
            'pair': data['market'],
            'status': data['status'].upper(),
            'type': _order_type,
            'time_in_force': _time_in_force,
            'reduce_only': data['reduceOnly'],
            'side': data['side'].upper(),
            'price': float(_price),
            'stop_price': float(_stop_price),
            'original_quantity': float(data['size']),
            'executed_quantity': float(data['filledSize']),
            'executed_price': float(_executed_price)
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

        results = self.get_order(
            pair=pair,
            order_id=order_id
        )

        trades = self._send_request(
            end_point=f"/api/v5/trade/fills?instType=MARGIN&instId={pair}&ordId={order_id}",
            request_type="GET",
            params={
                "instType": "MARGIN",
                "instId": pair,
                "ordId": order_id
            },
            signed=True
        )

        # if len(trades) > 0:
        #     dt = datetime.strptime(trades[-1]['time'], '%Y-%m-%dT%H:%M:%S.%f+00:00')
        #     results['time'] = int(dt.timestamp() * 1000)
        #
        # results['quote_asset'] = None
        # results['tx_fee_in_quote_asset'] = 0
        # results['tx_fee_in_other_asset'] = {}
        # results['nb_of_trades'] = 0
        # results['is_buyer'] = None
        #
        # for trade in trades:
        #     if results['quote_asset'] is None:
        #         results['quote_asset'] = 'USD' if trade['quoteCurrency'] is None else trade['quoteCurrency']
        #     if results['is_buyer'] is None:
        #         results['is_buyer'] = True if trade['side'] == 'buy' else False
        #
        #     results['tx_fee_in_quote_asset'] += float(trade['fee'])
        #     results['nb_of_trades'] += 1

        return trades

    def place_limit_tp(self, pair: str, side: str, quantity: float, tp_price: float):
        """
        Args:
            pair: pair id that we want to create the order for
            side: could be 'BUY' or 'SELL'
            quantity: for binance  quantity is not needed since the tp order "closes" the "opened" position
            tp_price: price of the tp or sl
        Returns:
            Standardized output
        """

        _params = {
            "instId": pair,
            "tdMode": "cross",
            "ccy": self.quote_asset,
            "side": side.lower(),
            "reduceOnly": True,
            "ordType": 'conditional',
            "tpTriggerPx": float(round(tp_price,  self.pairs_info[pair]['pricePrecision'])),
            "tpOrdPx": float(round(tp_price,  self.pairs_info[pair]['pricePrecision'])),
            "sz": float(round(quantity, self.pairs_info[pair]['quantityPrecision']))
        }

        data = self._send_request(
            end_point=f"/api/v5/trade/order-algo",
            request_type="POST",
            params=_params,
            signed=True
        )

        return data

    def place_market_sl(self, pair: str, side: str, quantity: float, sl_price: float):
        """
        Args:
            pair: pair id that we want to create the order for
            side: could be 'BUY' or 'SELL'
            quantity: for binance  quantity is not needed since the tp order "closes" the "opened" position
            sl_price: price of the tp or sl
        Returns:
            Standardized output
        """

        _params = {
            "instId": pair,
            "tdMode": "cross",
            "ccy": self.quote_asset,
            "side": side.lower(),
            "reduceOnly": True,
            "ordType": 'conditional',
            "slTriggerPx": float(round(sl_price, self.pairs_info[pair]['pricePrecision'])),
            "slOrdPx": -1,
            "sz": float(round(quantity, self.pairs_info[pair]['quantityPrecision']))
        }

        data = self._send_request(
            end_point=f"/api/v5/trade/order-algo",
            request_type="POST",
            params=_params,
            signed=True
        )

        return data

    def get_tp_sl_state(self, pair: str, tp_id: str, sl_id: str):
        """

        Args:
            pair:
            tp_id:
            sl_id:

        Returns:

        """
        tp_info = self.get_order_trades(pair=pair, order_id=tp_id)
        sl_info = self.get_order_trades(pair=pair, order_id=sl_id)
        return {
            'tp': tp_info,
            'sl': sl_info,
        }

    def get_all_orders(self):
        return self._send_request(
            end_point=f"/api/v5/trade/orders-pending?instType=MARGIN",
            params={"instType": "MARGIN"},
            request_type="GET",
            signed=True
        )['data']

    def get_all_conditional_orders(self):
        return self._send_request(
            end_point=f"/api/v5/trade/orders-algo-pending?instType=MARGIN&ordType=conditional",
            params={"instType": "MARGIN", "ordType": "conditional"},
            request_type="GET",
            signed=True
        )['data']

    def cancel_order(self, pair: str, order_id: str):

        data = self._send_request(
            end_point=f"/api/v5/trade/cancel-order",
            request_type="POST",
            params={
                'instId': pair,
                'ordId': order_id
            },
            signed=True
        )['data'][0]

        if data['sMsg'] == 'Cancellation failed as the order does not exist.':
            data = self._send_request(
                end_point=f"/api/v5/trade/cancel-algos",
                request_type="POST",
                params=[{
                    'instId': pair,
                    'algoId': order_id
                }],
                signed=True
            )['data'][0]

            if data['sMsg'] == 'Cancellation failed as the order does not exist.':

                print(f'order_id : {order_id} for pair {pair} has already been cancelled')

        print(f'order_id : {order_id} for pair {pair} has been cancelled')
