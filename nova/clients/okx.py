from requests import Request, Session
import hmac
import base64
import json
from datetime import datetime
from nova.utils.helpers import interval_to_milliseconds
import time
from nova.utils.constant import DATA_FORMATING
import pandas as pd
import aiohttp
import asyncio
from typing import Union
from multiprocessing import Pool


class OKX:

    def __init__(self,
                 key: str,
                 secret: str,
                 pass_phrase: str,
                 testnet: bool):

        self.api_key = key
        self.api_secret = secret
        self.pass_phrase = pass_phrase

        self.based_endpoint = "https://www.okx.com"
        self._session = Session()

        self.quote_asset = 'USDT'

        self.pairs_info = self.get_pairs_info()

        self.historical_limit = 90

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

            if pair['quoteCcy'] == 'USDT' and pair['state'] == 'live' and pair['instType'] == 'MARGIN':

                pairs_info[pair['instId']] = {}
                pairs_info[pair['instId']]['quote_asset'] = pair['quoteCcy']
                pairs_info[pair['instId']]['maxQuantity'] = float('inf')
                pairs_info[pair['instId']]['minQuantity'] = float(pair['minSz'])
                pairs_info[pair['instId']]['tick_size'] = float(pair['tickSz'])
                pairs_info[pair['instId']]['pricePrecision'] = int(str(pair['tickSz'])[::-1].find('.'))

                qty_precision = int(str(pair['minSz'])[::-1].find('.')) if float(pair['minSz']) > 1 else 0
                pairs_info[pair['instId']]['quantityPrecision'] = qty_precision

                pairs_info[pair['instId']]['earliest_timestamp'] = int(pair['listTime'])

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

        return self.pairs_info[pair]['earliest_timestamp']

    @staticmethod
    def _format_data(all_data: list, historical: bool = True) -> pd.DataFrame:
        """
        Args:
            all_data: output from _full_history

        Returns:
            standardized pandas dataframe
        """

        df = pd.DataFrame(all_data, columns=DATA_FORMATING['okx']['columns'])
        df = df.sort_values(by='open_time').reset_index(drop=True)

        for var in DATA_FORMATING['okx']['num_var']:
            df[var] = pd.to_numeric(df[var], downcast="float")

        for var in ['open_time']:
            df[var] = df[var].astype(int)

        df = df.sort_values(by='open_time').reset_index(drop=True)

        if historical:
            df['next_open'] = df['open'].shift(-1)

        interval_ms = df.loc[1, 'open_time'] - df.loc[0, 'open_time']

        df['close_time'] = df['open_time'] + interval_ms - 1

        return df.dropna().drop_duplicates('open_time')

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

            if len(temp_data) == 0:
                break

            # append this loops data to our output data
            if temp_data:
                klines += temp_data

            # handle the case where exactly the limit amount of data was returned last loop
            # check if we received less than the required limit and exit the loop

            # increment next call by our timeframe
            start_time = int(temp_data[0][0])

            # exit loop if we reached end_ts before reaching <limit> klines
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

        ts_ms = interval_to_milliseconds(interval)

        end_time = int(1000 * time.time())
        start_time = int(end_time - (self.historical_limit + 1) * ts_ms)
        _bar = interval if 'm' in interval else interval.upper()

        input_req = f"/api/v5/market/candles?instId={pair}&bar={_bar}&before={start_time}&after={end_time}"

        final_dict = {}
        final_dict[pair] = {}

        if current_pair_state is not None:
            final_dict[pair]['data'] = current_pair_state[pair]['data']
            final_dict[pair]['latest_update'] = current_pair_state[pair]['latest_update']

        async with session.get(url=f"{self.based_endpoint}{input_req}") as response:
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

        _params = {}

        if isinstance(pairs, str):
            _params['symbol'] = pairs

        all_pos = self._send_request(
            end_point=f"/api/v5/account/positions?instType=MARGIN",
            request_type="GET",
            params={"instType": "MARGIN"},
            signed=True
        )['data']

        position = {}

        for pos in all_pos:

            if pos['instId'] in pairs:

                _size = abs(float(pos['liab'])) if pos['posCcy'] == self.quote_asset else abs(float(pos['pos']))

                position[pos['instId']] = {}
                position[pos['instId']]['position_size'] = _size
                position[pos['instId']]['entry_price'] = float(pos['avgPx'])
                position[pos['instId']]['unrealized_pnl'] = float(pos['upl'])
                position[pos['instId']]['type_pos'] = 'SHORT' if pos['posCcy'] == self.quote_asset else 'LONG'
                position[pos['instId']]['exit_side'] = 'BUY' if pos['posCcy'] == self.quote_asset else 'SELL'

        return position

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

        _quantity = quote_size if side == 'buy' else quantity

        _params = {
            "instId": pair,
            "tdMode": "cross",
            "ccy": self.quote_asset,
            "side": side,
            "sz": _quantity,
            "ordType": "market",
        }

        data = self._send_request(
            end_point=f"/api/v5/trade/order",
            request_type="POST",
            params=_params,
            signed=True
        )['data'][0]

        return self.get_order_trades(pair=pair, order_id=data['ordId'])

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
            quote_size = last_price['latest_price'] * quantity

        _quantity = quote_size if side == 'buy' else quantity

        _params = {
            "instId": pair,
            "ccy": self.quote_asset,
            "tdMode": "cross",
            "reduceOnly": True,
            "side": side,
            "sz": _quantity,
            "ordType": "market",
        }

        while True:

            data = self._send_request(
                end_point=f"/api/v5/trade/order",
                request_type="POST",
                params=_params,
                signed=True
            )['data'][0]

            if data['sMsg'] == 'Insufficient balance ':
                _params['sz'] = _params['sz'] * 0.998
                print(f'Exit New Size : {_params["sz"]}')
            elif data['ordId'] != '':
                break
            elif data['sMsg'] not in ['', 'Insufficient balance ']:
                break

        self._send_request(
            end_point=f"/api/v5/trade/close-position",
            request_type="POST",
            params={
                "instId": pair,
                "mgnMode": 'cross',
                "ccy": self.quote_asset,
            },
            signed=True
        )

        return self.get_order_trades(pair=pair, order_id=data['ordId'])

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
        print({
                "instId": pair,
                "ordId": order_id,
            })

        print(data)

        if data['msg'] == 'Order does not exist':

            print('Open Conditional')
            url = f"/api/v5/trade/orders-algo-pending?ordType=conditional&instId={pair}&algoId={order_id}"

            data = self._send_request(
                end_point=url,
                request_type="GET",
                params={
                    "instId": pair,
                    "ordId": order_id,
                },
                signed=True
            )

            if data['msg'] == 'Order does not exist':
                print('Closed Conditional')

                url = f"/api/v5/trade/orders-algo-history?ordType=conditional&instId={pair}&algoId={order_id}"
                data = self._send_request(
                    end_point=url,
                    request_type="GET",
                    params={
                        "instId": pair,
                        "ordId": order_id,
                    },
                    signed=True
                )

                if data['msg'] == 'Order does not exist':
                    print('No Order Found')
                    return {}

        print(data)
        return self._format_order(data=data['data'][0])

    @staticmethod
    def _format_order(data: dict):

        _order_id_name = 'algoId' if 'algoId' in data.keys() else 'ordId'
        time_force = 'IOC' if data['ordType'] == 'market' else 'GTC'

        _price = float(data['px']) if data['ordType'] == 'post_only' else 0.0

        _order_type = data['ordType']

        if _order_type == 'conditional':
            if data['tpTriggerPx'] != '':
                _order_type = 'TAKE_PROFIT'
            if data['slTriggerPx'] != '':
                _order_type = 'STOP_MARKET'
        if _order_type == 'post_only':
            _order_type = "LIMIT"

        _stop_price = 0
        if data['tpOrdPx'] != '':
            _stop_price = float(data['tpTriggerPx'])
        elif data['slOrdPx'] != '':
            _stop_price = float(data['slTriggerPx'])

        _executed_px_name = 'actualPx' if 'algoId' in data.keys() else 'avgPx'
        _executed_qty_name = 'actualSz' if 'algoId' in data.keys() else 'fillSz'
        _executed_px = 0 if float(data[_executed_qty_name]) == 0 else data[_executed_px_name]

        _original_size = 0
        if data['side'] == 'sell':
            _original_size = float(data['sz'])
        else:
            if data['avgPx'] != '':
                _original_size = float(data['sz']) / float(data['avgPx'])
            elif data['px'] != '':
                _original_size = float(data['sz']) / float(data['px'])
            elif data['tpOrdPx'] != '':
                _original_size = float(data['sz']) / float(data['tpOrdPx'])
            elif data['slOrdPx'] != '':
                _original_size = float(data['sz']) / float(data['slOrdPx'])

        formatted = {
            'time': int(data['cTime']),
            'order_id': data[_order_id_name],
            'pair': data['instId'],
            'status': data['state'].upper(),
            'type': _order_type.upper(),
            'time_in_force': time_force,
            'reduce_only': data['reduceOnly'],
            'side': data['side'].upper(),
            'price': _price,
            'stop_price': _stop_price,
            'original_quantity': _original_size,
            'executed_quantity': float(data[_executed_qty_name]),
            'executed_price': float(_executed_px)
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

        trades = []

        if results['type'] not in ['TAKE_PROFIT', 'STOP_MARKET']:

            while len(trades) == 0 and results['executed_quantity'] > 0:
                trades = self._send_request(
                    end_point=f"/api/v5/trade/fills?instType=MARGIN&instId={pair}&ordId={order_id}",
                    request_type="GET",
                    params={
                        "instType": "MARGIN",
                        "instId": pair,
                        "ordId": order_id
                    },
                    signed=True
                )['data']

        results['quote_asset'] = self.quote_asset
        results['tx_fee_in_quote_asset'] = 0
        results['nb_of_trades'] = 0
        results['is_buyer'] = None

        for trade in trades:

            if results['quote_asset'] is None:
                results['quote_asset'] = 'USD' if trade['quoteCurrency'] is None else trade['quoteCurrency']

            if results['is_buyer'] is None:
                results['is_buyer'] = True if trade['side'] == 'buy' else False

            if trade['side'] == 'buy':
                results['tx_fee_in_quote_asset'] += abs(float(trade['fillPx']) * float(trade['fee']))
            else:
                results['tx_fee_in_quote_asset'] += abs(float(trade['fee']))

            results['nb_of_trades'] += 1

        return results

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
            "tpTriggerPx": tp_price,
            "tpOrdPx": tp_price,
            "sz": quantity
        }

        data = self._send_request(
            end_point=f"/api/v5/trade/order-algo",
            request_type="POST",
            params=_params,
            signed=True
        )['data'][0]

        print(data)

        return self.get_order(pair=pair, order_id=data['algoId'])

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
            "slTriggerPx": sl_price,
            "slOrdPx": -1,
            "sz": quantity
        }

        data = self._send_request(
            end_point=f"/api/v5/trade/order-algo",
            request_type="POST",
            params=_params,
            signed=True
        )['data'][0]

        return self.get_order(pair=pair, order_id=data['algoId'])

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
            "instId": pair,
            "side": side,
            "tdMode": "cross",
            "ccy": self.quote_asset,
            "px": best_price,
            "sz": quantity,
            "ordType": "post_only",
            "reduceOnly": reduce_only
        }

        data = self._send_request(
            end_point=f"/api/v5/trade/order",
            request_type="POST",
            params=_params,
            signed=True
        )['data'][0]

        return self._verify_limit_posted(
            pair=pair,
            order_id=data['ordId']
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

            if order_data['status'] == 'LIVE':
                return True, order_data

            if order_data['status'] in ['FILLED', 'PARTIALLY_FILLED']:
                return True, order_data

            if order_data['status'] == 'CANCELED':
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

        return residual_size, all_limit_orders

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
            quantity=float(quantity),
            duration=60,
            reduce_only=False
        )

        print(residual_size, all_orders)

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

        print('POSITION')

        print(pos_info)

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

        final_data['entry_price'] = _avg_price

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
