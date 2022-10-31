from requests import Request, Session
import time
import datetime
import hmac
from nova.utils.helpers import interval_to_milliseconds, milliseconds_to_interval
from nova.utils.constant import DATA_FORMATING
import pandas as pd
import numpy as np
import aiohttp
import asyncio
import json
import urllib.parse
from typing import Union
import math
from multiprocessing import Pool


class FTX:

    def __init__(self,
                 key: str,
                 secret: str,
                 testnet: bool = False
                 ):
        self.api_key = key
        self.api_secret = secret
        self.based_endpoint = "https://ftx.com/"
        self._session = Session()
        self.historical_limit = 1500
        self.pairs_info = self.get_pairs_info()
        self.holding_days = 5

    def _send_request(self, end_point: str, request_type: str, params: dict = None, signed: bool = False):
        if params is None:
            params = {}

        url = f'{self.based_endpoint}{end_point}'
        request = Request(request_type, url, data=json.dumps(params))
        prepared = request.prepare()
        prepared.headers['Content-Type'] = 'application/json'

        if signed:
            ts = int(time.time() * 1000)

            signature_payload = f'{ts}{request_type}{end_point}'

            if prepared.body:
                signature_payload += prepared.body

            signature_payload = signature_payload.encode()

            signature = hmac.new(self.api_secret.encode(), signature_payload, 'sha256').hexdigest()

            prepared.headers['FTX-KEY'] = self.api_key
            prepared.headers['FTX-SIGN'] = signature
            prepared.headers['FTX-TS'] = str(ts)

            prepared.headers['FTX-SUBACCOUNT'] = urllib.parse.quote('novalabs')

        response = self._session.send(prepared)
        data = response.json()

        if not data['success']:
            if data['error'] == 'Order not found' or data['error'] == 'Order already closed':
                return data
            else:
                print(data['error'])

        if 'result' in data.keys():
            return data['result']
        else:
            return data

    @staticmethod
    def get_server_time() -> int:
        """
        Note: FTX does not have any server time end point so we are simulating it with the time function
        Returns:
            the timestamp in milliseconds
        """
        return int(time.time() * 1000)

    def get_pairs_info(self) -> dict:
        data = self._send_request(
            end_point=f"/api/markets",
            request_type="GET"
        )

        pairs_info = {}

        for pair in data:

            if 'PERP' in pair['name']:
                pairs_info[pair['name']] = {}
                pairs_info[pair['name']]['quote_asset'] = 'USD'
                pairs_info[pair['name']]['pricePrecision'] = str(pair['priceIncrement'])[::-1].find('.')
                pairs_info[pair['name']]['maxQuantity'] = pair['largeOrderThreshold']
                pairs_info[pair['name']]['minQuantity'] = pair['sizeIncrement']
                pairs_info[pair['name']]['tick_size'] = pair['priceIncrement']
                pairs_info[pair['name']]['quantityPrecision'] = str(pair['sizeIncrement'])[::-1].find('.')

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
        _start_time = int(start_time//1000)
        _end_time = int(end_time//1000)
        _interval = int(interval_to_milliseconds(interval)//1000)
        _endpoint = f"/api/markets/{pair}/candles?resolution={_interval}&start_time={_start_time}&end_time={_end_time}"
        return self._send_request(
            end_point=_endpoint,
            request_type="GET"
        )

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
        kline = self._get_candles(
            pair=pair,
            interval='4d',
            start_time=0,
            end_time=int(time.time()*1000)
        )
        return int(kline[0]['time'])

    def _format_data(self, all_data: list, historical: bool = True) -> pd.DataFrame:
        """
        Args:
            all_data: output from _combine_history
        Returns:
            standardized pandas dataframe
        """
        # Remove the last row if it's not finished yet
        df = pd.DataFrame(all_data)
        df.drop('startTime', axis=1, inplace=True)
        df.columns = ['open_time', 'open', 'high', 'low', 'close', 'volume']

        for var in DATA_FORMATING['ftx']['num_var']:
            df[var] = pd.to_numeric(df[var], downcast="float")

        interval_ms = df['open_time'].iloc[1] - df['open_time'].iloc[0]

        clean_df = df

        if historical:

            final_data = df.drop_duplicates().dropna().reset_index(drop=True)

            _first_time = datetime.datetime.fromtimestamp(final_data.loc[0, 'open_time'] // 1000.0)
            _last_time = datetime.datetime.fromtimestamp(final_data.loc[len(final_data)-1, 'open_time'] // 1000.0)
            _freq = milliseconds_to_interval(interval_ms)

            final_timeseries = pd.DataFrame(
                pd.date_range(start=_first_time, end=_last_time, freq=_freq, tz='US/Eastern'),
                columns=['open_time']
            )

            final_timeseries['open_time'] = final_timeseries['open_time'].astype(np.int64) // 10 ** 6
            clean_df = final_timeseries.merge(final_data, on='open_time', how='left')

            all_missing = clean_df.isna().sum().sum()

            if all_missing > 0:
                print(f'FTX returned {all_missing} missing values ! Forward Fill Applied')
                clean_df = clean_df.ffill()

            clean_df['next_open'] = clean_df['open'].shift(-1)

        clean_df['close_time'] = clean_df['open_time'] + interval_ms - 1

        for var in ['open_time', 'close_time']:
            clean_df[var] = clean_df[var].astype(int)

        return clean_df

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

            end_t = start_time + timeframe * self.historical_limit
            end_time = min(end_t, end_ts)

            # fetch the klines from start_ts up to max 500 entries or the end_ts if set
            temp_data = self._get_candles(
                pair=pair,
                interval=interval,
                start_time=start_time,
                end_time=end_time
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
            start_time = temp_data[-1]['time'] + timeframe

            # exit loop if we reached end_ts before reaching <limit> klines
            if end_time and start_time >= end_ts:
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

        _set_leverage = self._send_request(
            end_point=f"/api/account/leverage",
            request_type="POST",
            params={"leverage": leverage},
            signed=True
        )

        account_info = self._send_request(
            end_point=f"/api/account",
            request_type="GET",
            signed=True
        )

        balance = account_info['freeCollateral']

        assert account_info['leverage'] == leverage

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

    def get_actual_positions(self, pairs: Union[list, str]) -> dict:
        """
        Args:
            pairs: list of pair that we want to run analysis on
        Returns:
            a dictionary containing all the current OPEN positions
        """

        _params = {}

        if isinstance(pairs, str):
            _params['symbol'] = pairs

        all_pos = self._send_request(
            end_point=f"/api/positions",
            request_type="GET",
            params={"showAvgPrice": True},
            signed=True
        )

        position = {}

        for pos in all_pos:

            if pos['future'] in pairs and pos['size'] != 0:
                position[pos['future']] = {}
                position[pos['future']]['position_size'] = abs(float(pos['size']))
                position[pos['future']]['entry_price'] = float(pos['entryPrice'])
                position[pos['future']]['unrealized_pnl'] = float(pos['realizedPnl'])
                position[pos['future']]['type_pos'] = 'LONG' if float(pos['netSize']) > 0 else 'SHORT'
                position[pos['future']]['exit_side'] = 'SELL' if float(pos['netSize']) > 0 else 'BUY'

        return position

    def get_token_balance(self, quote_asset: str):

        account_info = self._send_request(
            end_point=f"/api/account",
            request_type="GET",
            signed=True
        )

        print(f'The current amount is : {account_info["freeCollateral"]} {quote_asset}')

        return round(account_info['freeCollateral'], 2)

    def get_order_book(self, pair: str):
        """
        Args:
            pair:

        Returns:
            the current orderbook with a depth of 20 observations
        """

        url = f'/api/markets/{pair}/orderbook?depth=20'

        data = self._send_request(
            end_point=url,
            request_type="GET",
            signed=False
        )

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
            end_point=f"/api/markets/{pair}",
            request_type="GET",
            signed=False
        )

        return {
            'pair': data['name'],
            'timestamp': int(time.time()*1000),
            'latest_price': float(data['last'])
        }

    @staticmethod
    def _format_order(data: dict):

        _order_type = 'STOP_MARKET' if data['type'] == 'stop' else data['type'].upper()

        _price = 0.0 if _order_type in ["MARKET", "STOP_MARKET", "TAKE_PROFIT"] else data['price']
        _stop_price = 0.0 if _order_type in ["MARKET", "LIMIT"] else data['triggerPrice']
        _time_in_force = 'IOC' if 'ioc' in data.keys() and data['ioc'] else 'GTC'

        dt = datetime.datetime.strptime(data['createdAt'], '%Y-%m-%dT%H:%M:%S.%f+00:00')

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
            end_point=f"/api/orders/{order_id}",
            request_type="GET",
            signed=True
        )

        if 'success' in data.keys():

            if data['error'] == 'Order not found':

                conditional_open_data = self._send_request(
                    end_point=f"/api/conditional_orders?market={pair}",
                    request_type="GET",
                    signed=True
                )

                not_inside = True

                # if conditional still "open"
                for order in conditional_open_data:
                    if order['id'] == order_id:
                        not_inside = False
                        data = order
                        break

                # if conditional not opened anymore
                if not_inside:

                    conditional_executed = self._send_request(
                        end_point=f"/api/conditional_orders/{order_id}/triggers",
                        request_type="GET",
                        signed=True
                    )

                    # determine start time and
                    all_time = []
                    for execution in conditional_executed:
                        dt = datetime.datetime.strptime(execution['time'], '%Y-%m-%dT%H:%M:%S.%f+00:00')
                        all_time.append(math.floor(dt.timestamp()))
                    end_time = max(all_time)
                    start_time = end_time - self.holding_days * 24 * 3600

                    historical = self._send_request(
                        end_point=f"/api/conditional_orders/history?market={pair}&start_time{start_time}&{end_time}",
                        request_type="GET",
                        signed=True
                    )

                    for order in historical:
                        if order['id'] == order_id:
                            data = order
                            break

        return self._format_order(data=data)

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
            end_point=f"/api/fills?market={pair}&orderId={results['order_id']}",
            request_type="GET",
            signed=True
        )

        if len(trades) > 0:
            dt = datetime.datetime.strptime(trades[-1]['time'], '%Y-%m-%dT%H:%M:%S.%f+00:00')
            results['time'] = int(dt.timestamp() * 1000)

        results['quote_asset'] = None
        results['tx_fee_in_quote_asset'] = 0
        results['tx_fee_in_other_asset'] = {}
        results['nb_of_trades'] = 0
        results['is_buyer'] = None

        for trade in trades:
            if results['quote_asset'] is None:
                results['quote_asset'] = 'USD' if trade['quoteCurrency'] is None else trade['quoteCurrency']
            if results['is_buyer'] is None:
                results['is_buyer'] = True if trade['side'] == 'buy' else False

            results['tx_fee_in_quote_asset'] += float(trade['fee'])
            results['nb_of_trades'] += 1

        return results

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

        _params = {
            "market": pair,
            "side": side,
            "price": None,
            "size": float(round(quantity, self.pairs_info[pair]['quantityPrecision'])),
            "type": "market",
        }

        response = self._send_request(
            end_point=f"/api/orders",
            request_type="POST",
            params=_params,
            signed=True
        )

        return self.get_order_trades(
            pair=pair,
            order_id=response['id']
        )

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

        _params = {
            "market": pair,
            "side": side,
            "price": None,
            "size": float(round(quantity, self.pairs_info[pair]['quantityPrecision'])),
            "type": "market",
            "reduceOnly": True
        }

        response = self._send_request(
            end_point=f"/api/orders",
            request_type="POST",
            params=_params,
            signed=True
        )

        return self.get_order_trades(
            pair=pair,
            order_id=response['id']
        )

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
            "market": pair,
            "reduceOnly": True,
            "side": side.lower(),
            "type": 'takeProfit',
            "triggerPrice": float(round(tp_price,  self.pairs_info[pair]['pricePrecision'])),
            "orderPrice": float(round(tp_price,  self.pairs_info[pair]['pricePrecision'])),
            "size": float(round(quantity, self.pairs_info[pair]['quantityPrecision']))
        }

        data = self._send_request(
            end_point=f"/api/conditional_orders",
            request_type="POST",
            params=_params,
            signed=True
        )

        return self.get_order(pair=pair, order_id=data['id'])

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
            "market": pair,
            "reduceOnly": True,
            "side": side.lower(),
            "type": 'stop',
            "triggerPrice": float(round(sl_price,  self.pairs_info[pair]['pricePrecision'])),
            "size": float(round(quantity, self.pairs_info[pair]['quantityPrecision']))
        }

        data = self._send_request(
            end_point=f"/api/conditional_orders",
            request_type="POST",
            params=_params,
            signed=True
        )

        return self.get_order(pair=pair, order_id=data['id'])

    def cancel_order(self, pair: str, order_id: str):

        data = self._send_request(
            end_point=f"/api/orders/{order_id}",
            request_type="DELETE",
            signed=True
        )

        if isinstance(data, dict):

            if data['error'] == 'Order not found':

                data = self._send_request(
                    end_point=f"/api/conditional_orders/{order_id}",
                    request_type="DELETE",
                    signed=True
                )

        result = data
        if isinstance(data, dict):
            result = data['error']

        print(f'{pair} order_id {order_id} --> {result}')

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

        side = 'buy' if side == 'BUY' else 'sell'

        _params = {
            "market": pair,
            "side": side,
            "price": float(round(best_price, self.pairs_info[pair]['pricePrecision'])),
            "size": float(round(quantity, self.pairs_info[pair]['quantityPrecision'])),
            "type": "limit",
            "postOnly": True,
            "reduceOnly": reduce_only
        }

        response = self._send_request(
            end_point=f"/api/orders",
            request_type="POST",
            params=_params,
            signed=True
        )

        return self._verify_limit_posted(
                     order_id=response['id'],
                     pair=pair
                )

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

        # Keep trying to get order status during 2
        while time.time() - t_start < 2:

            time.sleep(0.5)

            order_data = self.get_order(
                pair=pair,
                order_id=order_id
            )

            if order_data['status'] == 'OPEN':
                return True, order_data

            if order_data['status'] == 'CLOSED' and order_data['executed_quantity'] > 0:
                return True, order_data

            if order_data['status'] == 'CLOSED' and order_data['executed_quantity'] == 0:
                return False, None

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
                while (_price == data['price']) and (time.time() - t_start < duration) and (_status != 'CLOSED'):

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
                print('inside 1')
                residual_size = quantity
            # 0 < current_size < quantity => partial limit execution => update residual_size => try again
            elif pair in list(pos_info.keys()) and not reduce_only and pos_info[pair]['position_size'] <= quantity:
                print('inside 2')
                residual_size = quantity - pos_info[pair]['position_size']

            # looping exit position (current_size > 0 => no or partial limit execution => try again)
            elif pair in list(pos_info.keys()) and reduce_only:
                print('inside 3')
                residual_size = pos_info[pair]['position_size']
            # current_size = 0 => limit exit order fully executed => update residual_size to 0
            elif pair not in list(pos_info.keys()) and reduce_only and posted:
                print('inside 4')
                residual_size = 0

            # side situation 1 : current_size = 0 + exit position but latest order has not been posted
            # => complete execution from the tp or sl happening between checking position and exiting position
            elif pair not in list(pos_info.keys()) and reduce_only and not posted:
                print('inside 5')
                residual_size = 0

            print(residual_size)

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

            if order['executed_quantity'] > 0:

                final_data['entry_fees'] += order['tx_fee_in_quote_asset']
                final_data['original_position_size'] += order['executed_quantity']
                final_data['current_position_size'] += order['executed_quantity']
                _price_information.append({'price': order['executed_price'], 'qty': order['executed_quantity']})

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

        exit_side = 'sell' if side == 'BUY' else 'buy'

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

        side = 'sell' if type_pos == 'LONG' else 'buy'

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

    def exit_limit_then_market(self, orders: list) -> dict:
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
