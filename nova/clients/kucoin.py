from requests import Request, Session
import hmac
import base64
import json
import time
import hashlib
from nova.utils.helpers import interval_to_minutes, interval_to_milliseconds, milliseconds_to_interval
from nova.utils.constant import DATA_FORMATING
import pandas as pd
from datetime import datetime
from typing import Union
import uuid
import numpy as np
import aiohttp
import asyncio
from multiprocessing import Pool


class Kucoin:

    def __init__(self,
                 key: str,
                 secret: str,
                 pass_phrase: str,
                 testnet: bool):
        self.api_key = key
        self.api_secret = secret
        self.pass_phrase = pass_phrase

        self.based_endpoint = "https://api-futures.kucoin.com"

        self._session = Session()

        self.historical_limit = 190

        self.pairs_info = self.get_pairs_info()

        self.leverage = 2

    def _send_request(self, end_point: str, request_type: str, params: dict = {}, signed: bool = False):

        to_use = "https://api-futures.kucoin.com" if not signed else self.based_endpoint
        request = Request(request_type, f'{to_use}{end_point}', data=json.dumps(params))
        prepared = request.prepare()

        timestamp = int(time.time() * 1000)

        prepared.headers['Content-Type'] = "application/json"
        prepared.headers['KC-API-KEY-VERSION '] = "2"
        prepared.headers['User-Agent'] = "NovaLabs"
        prepared.headers['KC-API-TIMESTAMP'] = str(timestamp)

        if signed:

            final_dict = ""
            if params:
                final_dict = json.dumps(params)

            sig_str = f"{timestamp}{request_type}{end_point}{final_dict}".encode('utf-8')
            signature = base64.b64encode(
                hmac.new(self.api_secret.encode('utf-8'), sig_str, hashlib.sha256).digest()
            )

            prepared.headers['KC-API-SIGN'] = signature
            prepared.headers['KC-API-KEY'] = self.api_key
            prepared.headers['KC-API-PASSPHRASE'] = self.pass_phrase

        response = self._session.send(prepared)

        return response.json()

    def get_server_time(self) -> int:
        """
        Returns:
            the timestamp in milliseconds
        """
        return self._send_request(
            end_point=f"/api/v1/timestamp",
            request_type="GET"
        )['data']

    def get_pairs_info(self):

        data = self._send_request(
            end_point=f"/api/v1/contracts/active",
            request_type="GET",
            signed=False
        )['data']

        pairs_info = {}

        for pair in data:

            if pair['status'] == "Open":

                _min_quantity = pair['lotSize'] * pair['multiplier']
                precision_quantity = str(_min_quantity)[::-1].find('.') if _min_quantity < 1 else 0

                pairs_info[pair['symbol']] = {}
                pairs_info[pair['symbol']]['quote_asset'] = pair['quoteCurrency']
                pairs_info[pair['symbol']]['maxQuantity'] = pair['maxOrderQty']
                pairs_info[pair['symbol']]['minQuantity'] = _min_quantity
                pairs_info[pair['symbol']]['tick_size'] = pair['tickSize']
                pairs_info[pair['symbol']]['pricePrecision'] = str(pair['tickSize'])[::-1].find('.')
                pairs_info[pair['symbol']]['quantityPrecision'] = precision_quantity
                pairs_info[pair['symbol']]['earliest_time'] = pair['firstOpenDate']
                pairs_info[pair['symbol']]['multiplier'] = pair['multiplier']

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
        _interval_min = interval_to_minutes(interval)
        _interval_ms = interval_to_milliseconds(interval)

        _end_time = start_time + self.historical_limit * _interval_ms
        _endpoint = f"/api/v1/kline/query?symbol={pair}&granularity={_interval_min}&from={start_time}&to={_end_time}"
        return self._send_request(
            end_point=f'{_endpoint}',
            request_type="GET",
        )['data']

    def _get_earliest_timestamp(self, pair: str, interval: str):
        """
        Note the historical data for the
        of the time
        Args:
            pair: Name of symbol pair
            interval: interval in string
        return:
            the earliest valid open timestamp in milliseconds
        """

        current_time = (time.time() * 1000)
        _interval_ms = interval_to_milliseconds(interval)

        return int(current_time - 15 * _interval_ms * self.historical_limit)

    @staticmethod
    def _format_data(all_data: list, historical: bool = True) -> pd.DataFrame:
        """
        Args:
            all_data: output from _full_history

        Returns:
            standardized pandas dataframe
        """

        df = pd.DataFrame(all_data, columns=DATA_FORMATING['kucoin']['columns'])

        for var in DATA_FORMATING['kucoin']['num_var']:
            df[var] = pd.to_numeric(df[var], downcast="float")

        interval_ms = df['open_time'].iloc[1] - df['open_time'].iloc[0]

        clean_df = df

        if historical:

            final_data = df.drop_duplicates().dropna().reset_index(drop=True)

            _first_time = datetime.fromtimestamp(final_data.loc[0, 'open_time'] // 1000.0)
            _last_time = datetime.fromtimestamp(final_data.loc[len(final_data)-1, 'open_time'] // 1000.0)
            _freq = milliseconds_to_interval(interval_ms)

            final_timeseries = pd.DataFrame(
                pd.date_range(start=_first_time, end=_last_time, freq=_freq, tz='US/Eastern'),
                columns=['open_time']
            )

            final_timeseries['open_time'] = final_timeseries['open_time'].astype(np.int64) // 10 ** 6
            clean_df = final_timeseries.merge(final_data, on='open_time', how='left')

            all_missing = clean_df.isna().sum().sum()

            if all_missing > 0:
                print(f'Kucoin returned {all_missing} missing values ! Forward Fill Applied')
                clean_df = clean_df.ffill()

            clean_df['next_open'] = clean_df['open'].shift(-1)

        clean_df['close_time'] = clean_df['open_time'] + interval_ms - 1

        for var in ['open_time', 'close_time']:
            clean_df[var] = clean_df[var].astype(int)

        return clean_df.dropna()

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

            # fetch the klines from start_ts up to max 500 entries or the end_ts if set
            temp_data = self._get_candles(
                pair=pair,
                interval=interval,
                start_time=start_time,
                end_time=end_ts
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
            start_time = temp_data[-1][0] + timeframe

            # exit loop if we reached end_ts before reaching klines
            if start_time >= end_ts:
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

        self.leverage = leverage

        account_info = self._send_request(
            end_point=f"/api/v1/account-overview?currency={quote_asset}",
            request_type="GET",
            params={"currency": quote_asset},
            signed=True
        )['data']

        balance = account_info['availableBalance']

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

        ts_ms = interval_to_milliseconds(interval)

        end_time = int(1000 * time.time())
        start_time = int(end_time - (self.historical_limit + 1) * ts_ms)

        _interval_min = interval_to_minutes(interval)
        _interval_ms = interval_to_milliseconds(interval)

        _endpoint = f"/api/v1/kline/query?symbol={pair}&granularity={_interval_min}&from={start_time}&to={end_time}"

        final_dict = {}
        final_dict[pair] = {}

        if current_pair_state is not None:
            final_dict[pair]['data'] = current_pair_state[pair]['data']
            final_dict[pair]['latest_update'] = current_pair_state[pair]['latest_update']

        async with session.get(url=f"{self.based_endpoint}{_endpoint}") as response:
            data = await response.json()

            df = self._format_data(all_data=data['data'], historical=False)
            df = df[df['close_time'] < end_time]

            for var in ['open_time', 'close_time']:
                df[var] = pd.to_datetime(df[var], unit='ms')

            if current_pair_state is None:
                final_dict[pair]['latest_update'] = end_time
                final_dict[pair]['data'] = df

            else:
                df_new = pd.concat([final_dict[pair]['data'], df])
                df_new = df_new.drop_duplicates(subset=['open_time']).sort_values(
                    by=['open_time'],
                    ascending=True
                )
                final_dict[pair]['latest_update'] = end_time
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

        # If we need more than 200 candles (which is the API's limit) we call self.get_historical_data instead
        if nb_candles > self.historical_limit and current_state is None:

            final_dict = {}

            for pair in list_pair:
                final_dict[pair] = {}
                start_time = int(1000 * time.time() - (nb_candles + 1) * interval_to_milliseconds(interval=interval))
                last_update = int(1000 * time.time())

                df = self.get_historical_data(
                    pair=pair,
                    start_ts=start_time,
                    interval=interval,
                    end_ts=last_update
                )

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

    def get_actual_positions(self, pairs: Union[list, str]) -> dict:
        """
        Args:
            pairs: list of pair that we want to run analysis on
        Returns:
            a dictionary containing all the current OPEN positions
        """

        if isinstance(pairs, str):
            pairs = [pairs]

        position = {}

        for pair in pairs:

            pos = self._send_request(
                end_point=f'/api/v1/position?symbol={pair}',
                params={"symbol": pair},
                request_type="GET",
                signed=True
            )['data']

            if pos['isOpen']:
                position[pair] = {}
                position[pair]['position_size'] = abs(float(pos['currentQty']*self.pairs_info[pair]['multiplier']))
                position[pair]['entry_price'] = float(pos['avgEntryPrice'])
                position[pair]['unrealized_pnl'] = float(pos['unrealisedPnl'])
                position[pair]['type_pos'] = 'LONG' if float(pos['currentQty']) > 0 else 'SHORT'
                position[pair]['exit_side'] = 'SELL' if float(pos['currentQty']) > 0 else 'BUY'

        return position

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

        _quantity = quantity / self.pairs_info[pair]['multiplier']

        _params = {
            "clientOid": str(uuid.uuid4()),
            "symbol": pair,
            "side": side,
            "size": float(round(_quantity, self.pairs_info[pair]['quantityPrecision'])),
            "type": "market",
            "leverage": str(self.leverage)
        }

        data = self._send_request(
            end_point=f"/api/v1/orders",
            request_type="POST",
            params=_params,
            signed=True
        )

        return self.get_order_trades(pair=pair, order_id=data['data']['orderId'])

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

        _quantity = quantity / self.pairs_info[pair]['multiplier']

        _params = {
            "clientOid": str(uuid.uuid4()),
            "symbol": pair,
            "side": side,
            "size": float(round(_quantity, self.pairs_info[pair]['quantityPrecision'])),
            "type": "market",
            "leverage": str(self.leverage),
            "reduceOnly": True
        }

        data = self._send_request(
            end_point=f"/api/v1/orders",
            request_type="POST",
            params=_params,
            signed=True
        )['data']

        return self.get_order_trades(pair=pair, order_id=data['orderId'])

    def get_order(self, pair: str, order_id: str):
        data = self._send_request(
            end_point=f"/api/v1/orders/{order_id}",
            request_type="GET",
            params={'order-id': order_id},
            signed=True
        )['data']

        return self._format_order(data=data)

    def _format_order(self, data: dict):

        _status = 'CLOSED' if not data['isActive'] else 'OPEN'
        executed_quantity = data['filledSize'] * self.pairs_info[data['symbol']]['multiplier']
        executed_price = 0 if executed_quantity == 0 else float(data['filledValue']) / executed_quantity
        original_quantity = data['size'] * self.pairs_info[data['symbol']]['multiplier']

        formatted = {
            'time': data['createdAt'],
            'order_id': data['id'],
            'pair': data['symbol'],
            'status': _status,
            'type': data['type'].upper(),
            'time_in_force': data['timeInForce'],
            'reduce_only': data['reduceOnly'],
            'side': data['side'].upper(),
            'price': data['price'],
            'stop_price': data['stop'],
            'original_quantity': float(original_quantity),
            'executed_quantity': float(executed_quantity),
            'executed_price': float(executed_price)
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
            end_point=f"/api/v1/fills?orderId={order_id}",
            request_type="GET",
            params={'symbol': pair, 'orderId': order_id},
            signed=True
        )['data']

        if len(trades['items']) > 0:
            results['time'] = trades['items'][-1]['createdAt']
            results['quote_asset'] = trades['items'][-1]['feeCurrency']

        results['tx_fee_in_quote_asset'] = 0
        results['tx_fee_in_other_asset'] = {}
        results['nb_of_trades'] = trades['totalNum']
        results['is_buyer'] = None

        for trade in trades['items']:
            if results['is_buyer'] is None:
                results['is_buyer'] = True if trade['side'] == 'buy' else False

            results['tx_fee_in_quote_asset'] += float(trade['fee'])

        return results

    def get_last_price(self, pair: str) -> dict:
        """
        Args:
            pair: pair desired
        Returns:
            a dictionary containing the pair_id, latest_price, price_timestamp in timestamp
        """
        data = self._send_request(
            end_point=f"/api/v1/ticker?symbol={pair}",
            request_type="GET",
            signed=False
        )['data']

        return {
            'pair': data['symbol'],
            'timestamp': data['ts'],
            'latest_price': float(data['price'])
        }

    def get_token_balance(self, quote_asset: str):

        account_info = self._send_request(
            end_point=f"/api/v1/account-overview?currency={quote_asset}",
            request_type="GET",
            params={"currency": quote_asset},
            signed=True
        )['data']

        balance = account_info['availableBalance']
        print(f'The current amount is : {balance} {quote_asset}')
        return round(balance, 2)

    def get_order_book(self, pair: str):
        """
        Args:
            pair:

        Returns:
            the current orderbook with a depth of 20 observations
        """

        data = self._send_request(
            end_point=f'/api/v1/level2/depth20?symbol={pair}',
            request_type="GET",
            signed=False
        )['data']

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

        _stop = 'up' if side == 'SELL' else 'down'
        _quantity = quantity / self.pairs_info[pair]['multiplier']

        _params = {
            "clientOid": str(uuid.uuid4()),
            "symbol": pair,
            "reduceOnly": True,
            "side": side.lower(),
            "type": "limit",
            "stop": _stop,
            "stopPrice": float(round(tp_price,  self.pairs_info[pair]['pricePrecision'])),
            "price": float(round(tp_price,  self.pairs_info[pair]['pricePrecision'])),
            "size": float(round(_quantity, self.pairs_info[pair]['quantityPrecision'])),
            "stopPriceType": "TP"
        }

        data = self._send_request(
            end_point=f"/api/v1/orders",
            request_type="POST",
            params=_params,
            signed=True
        )

        return data

        # return self.get_order(pair=pair, order_id=data['orderId'])

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

        _stop = 'down' if side == 'SELL' else 'up'
        _quantity = quantity / self.pairs_info[pair]['multiplier']

        _params = {
            "clientOid": str(uuid.uuid4()),
            "symbol": pair,
            "reduceOnly": True,
            "side": side.lower(),
            "type": 'market',
            "stop": _stop,
            "stopPrice": float(round(sl_price,  self.pairs_info[pair]['pricePrecision'])),
            "size": float(round(_quantity, self.pairs_info[pair]['quantityPrecision'])),
            "stopPriceType": "TP",
            "leverage": str(self.leverage)
        }

        data = self._send_request(
            end_point=f"/api/v1/orders",
            request_type="POST",
            params=_params,
            signed=True
        )

        return data

    def cancel_order(self, pair: str, order_id: str):

        data = self._send_request(
            end_point=f"/api/v1/orders/{order_id}",
            request_type="DELETE",
            params={"order-id": order_id},
            signed=True
        )

        if data['code'] == '200000':
            print(f'Order id {order_id} has been cancelled')
        else:
            print(f'Order id {order_id} has been already cancelled or filled')

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
        _quantity = quantity / self.pairs_info[pair]['multiplier']

        _params = {
            "clientOid": str(uuid.uuid4()),
            "symbol": pair,
            "reduceOnly": reduce_only,
            "side": side.lower(),
            "type": "limit",
            "leverage": self.leverage,
            "price": float(round(best_price, self.pairs_info[pair]['pricePrecision'])),
            "size": float(round(_quantity, self.pairs_info[pair]['quantityPrecision'])),
        }

        response = self._send_request(
            end_point=f"/api/v1/orders",
            request_type="POST",
            params=_params,
            signed=True
        )['data']

        return self._verify_limit_posted(
                     order_id=response['orderId'],
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