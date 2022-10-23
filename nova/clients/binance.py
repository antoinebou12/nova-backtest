from nova.utils.helpers import interval_to_milliseconds
from nova.utils.constant import DATA_FORMATING
from requests import Request, Session
from urllib.parse import urlencode
import pandas as pd
import aiohttp
import asyncio
import hashlib
import time
import hmac
from multiprocessing import Pool
from typing import Union


class Binance:

    def __init__(self,
                 key: str,
                 secret: str,
                 testnet: bool
                 ):

        self.api_key = key
        self.api_secret = secret

        self.based_endpoint = "https://testnet.binancefuture.com" if testnet else "https://fapi.binance.com"

        self._session = Session()

        self.historical_limit = 1000

        self.pairs_info = self.get_pairs_info()

    # API REQUEST FORMAT
    def _send_request(self, end_point: str, request_type: str, params: dict = None, signed: bool = False):

        if params is None:
            params = {}
        if signed:

            params['timestamp'] = int(time.time() * 1000)
            query_string = urlencode(params, True).replace("%40", "@")
            m = hmac.new(self.api_secret.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256)
            params['signature'] = m.hexdigest()

        request = Request(request_type, f'{self.based_endpoint}{end_point}',
                          params=urlencode(params, True).replace("%40", "@"))

        prepared = request.prepare()
        prepared.headers['Content-Type'] = "application/json;charset=utf-8"
        prepared.headers['User-Agent'] = "NovaLabs"
        prepared.headers['X-MBX-APIKEY'] = self.api_key
        response = self._session.send(prepared)
        data = response.json()

        if isinstance(data, dict) and 'code' in data.keys() and data['code'] not in [200, -2011]:
            print(f'##### ERROR : {data["msg"]} #####')

        return data

    def get_server_time(self) -> int:
        """
        Returns:
            the timestamp in milliseconds
        """
        data = self._send_request(
            end_point=f"/fapi/v1/time",
            request_type="GET"
        )
        return int(data['serverTime'])

    def _get_candles(self, pair: str, interval: str, start_time: int, end_time: int, limit: int = None):
        """
        Args:
            pair: pair to get information from
            interval: granularity of the candle ['1m', '1h', ... '1d']
            start_time: timestamp in milliseconds of the starting date
            end_time: timestamp in milliseconds of the end date
            limit: number of data points returned by binance

        Returns:
            the none formatted candle information requested
        """
        _limit = limit if limit else self.historical_limit
        _params = {
            "symbol": pair,
            "interval": interval,
            "startTime": start_time,
            "endTime": end_time,
            "limit": _limit
        }
        return self._send_request(
            end_point=f"/fapi/v1/klines",
            request_type="GET",
            params=_params
        )

    def _get_earliest_timestamp(self, pair: str, interval: str):
        """
        Args:
            pair: Name of symbol pair
            interval: Binance Kline interval

        return:
            the earliest valid open timestamp
        """
        kline = self._get_candles(
            pair=pair,
            interval=interval,
            start_time=0,
            end_time=int(time.time() * 1000),
            limit=1
        )
        return kline[0][0]

    @staticmethod
    def _format_data(all_data: list, historical: bool = True) -> pd.DataFrame:
        """
        Args:
            all_data: output from _full_history

        Returns:
            standardized pandas dataframe
        """

        df = pd.DataFrame(all_data, columns=DATA_FORMATING['binance']['columns'])

        for var in DATA_FORMATING['binance']['num_var']:
            df[var] = pd.to_numeric(df[var], downcast="float")

        for var in DATA_FORMATING['binance']['date_var']:
            df[var] = pd.to_numeric(df[var], downcast="integer")

        if historical:
            df['next_open'] = df['open'].shift(-1)

        return df.dropna()

    def get_historical_data(self, pair: str, interval: str, start_ts: int, end_ts: int) -> pd.DataFrame:
        """
        Args:
            pair: pair to get information from
            interval: granularity of the candle ['1m', '1h', ... '1d']
            start_ts: timestamp in milliseconds of the starting date
            end_ts: timestamp in milliseconds of the end date
        Returns:
            historical data requested in a standardized pandas dataframe
        """

        # init our list
        output_data = []

        # convert interval to useful value in seconds
        timeframe = interval_to_milliseconds(interval)

        # if a start time was passed convert it
        start_ts = start_ts

        # establish first available start timestamp
        first_valid_ts = self._get_earliest_timestamp(
            pair=pair,
            interval=interval
        )
        start_ts = max(start_ts, first_valid_ts)

        # if an end time was passed convert it
        end_ts = end_ts

        if end_ts and start_ts and end_ts <= start_ts:
            return pd.DataFrame()

        idx = 0
        while True:
            # fetch the klines from start_ts up to max 500 entries or the end_ts if set
            temp_data = self._get_candles(
                pair=pair,
                interval=interval,
                limit=self.historical_limit,
                start_time=start_ts,
                end_time=end_ts
            )

            # append this loops data to our output data
            if temp_data:
                output_data += temp_data

            # handle the case where exactly the limit amount of data was returned last loop
            # check if we received less than the required limit and exit the loop
            if not len(temp_data) or len(temp_data) < self.historical_limit:
                # exit the while loop
                break

            # increment next call by our timeframe
            start_ts = temp_data[-1][0] + timeframe

            # exit loop if we reached end_ts before reaching <limit> klines
            if end_ts and start_ts >= end_ts:
                break

            # sleep after every 3rd call to be kind to the API
            idx += 1
            if idx % 3 == 0:
                time.sleep(1)

        return self._format_data(all_data=output_data, historical=True)

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

        end_date_data_ts = int(current_df['open_time'].max())
        now_date_ts = int(time.time() * 1000)
        df = self.get_historical_data(
            pair=pair,
            interval=interval,
            start_ts=end_date_data_ts,
            end_ts=now_date_ts
        )
        return pd.concat([current_df, df], ignore_index=True).drop_duplicates(subset=['open_time'])

    # BINANCE SPECIFIC FUNCTION
    def setup_account(self,
                      quote_asset: str,
                      leverage: int,
                      list_pairs: list,
                      bankroll: float,
                      max_down: float):
        """
        Note: We execute verification of the account (balance, leverage, etc.)

        Args:
            quote_asset:
            leverage:
            list_pairs:
            bankroll:
            max_down:

        Returns:
            None
        """
        accounts = self.get_account_info()
        positions_info = self._send_request(
                end_point=f"/fapi/v2/positionRisk",
                request_type="GET",
                signed=True
        )
        balance = self.get_token_balance(quote_asset=quote_asset)
        position_mode = self.get_position_mode()

        for info in positions_info:

            if info['symbol'] in list_pairs:

                # ISOLATE MARGIN TYPE -> ISOLATED
                if info['marginType'] != 'isolated':
                    self.change_margin_type(
                        pair=info['symbol'],
                        margin_type="ISOLATED",
                    )

                # SET LEVERAGE
                if int(info['leverage']) != leverage:
                    self.change_leverage(
                        pair=info['symbol'],
                        leverage=leverage,
                    )

        if position_mode['dualSidePosition']:
            self.change_position_mode(
                dual_position="false",
            )

        for x in accounts["assets"]:

            if x["asset"] == quote_asset:
                # Assert_1: The account need to have the minimum bankroll
                assert float(x['availableBalance']) >= bankroll * (1 + max_down), \
                    f"The account has only {round(balance, 2)} {quote_asset}. " \
                    f"{round(bankroll * (1 + max_down), 2)} {quote_asset} is required"

                # Assert_2: The account has margin available
                assert x['marginAvailable']

            if x['asset'] == "BNB" and float(x["availableBalance"]) == 0:
                print(f"You can save Tx Fees if you transfer BNB in your Future Account")

    def get_exchange_info(self):
        return self._send_request(
            end_point=f"/fapi/v1/exchangeInfo",
            request_type="GET",
        )

    def change_position_mode(self, dual_position: str):
        response = self._send_request(
            end_point=f"/fapi/v1/positionSide/dual",
            request_type="POST",
            params={"dualSidePosition": dual_position},
            signed=True
        )
        print(response['msg'])

    def get_position_mode(self):
        return self._send_request(
            end_point=f"/fapi/v1/positionSide/dual",
            request_type="GET",
            signed=True
        )

    def change_margin_type(self, pair: str, margin_type: str):
        response = self._send_request(
            end_point=f"/fapi/v1/marginType",
            request_type="POST",
            params={"symbol": pair, "marginType": margin_type},
            signed=True
        )
        print(f"{response['msg']}")

    def get_pairs_info(self) -> dict:
        """
        Note: This output is used for standardization purpose because binance order api has
        decimal restriction per pair.
        Returns:
            a dict where the key is equal to the pair symbol and the value is a dict that contains
            the following information "quantityPrecision" and "quantityPrecision".
        """
        info = self.get_exchange_info()

        output = {}

        for symbol in info['symbols']:
            if symbol['contractType'] == 'PERPETUAL':
                output[symbol['symbol']] = {}

                output[symbol['symbol']]['quote_asset'] = symbol['quoteAsset']

                for fil in symbol['filters']:
                    if fil['filterType'] == 'PRICE_FILTER':
                        tick_size = str(float(fil['tickSize']))
                        output[symbol['symbol']]['pricePrecision'] = min(tick_size[::-1].find('.'),
                                                                         symbol['pricePrecision'])
                    if fil['filterType'] == 'LOT_SIZE':
                        step_size = str(float(fil['stepSize']))
                        output[symbol['symbol']]['quantityPrecision'] = min(step_size[::-1].find('.'),
                                                                            symbol['quantityPrecision'])
                        output[symbol['symbol']]['minQuantity'] = float(fil['minQty'])

                    if fil['filterType'] == 'MARKET_LOT_SIZE':
                        output[symbol['symbol']]['maxQuantity'] = float(fil['maxQty'])

        return output

    # STANDARDIZED FUNCTIONS
    def change_leverage(self, pair: str, leverage: int):
        data = self._send_request(
            end_point=f"/fapi/v1/leverage",
            request_type="POST",
            params={"symbol": pair, "leverage": leverage},
            signed=True
        )
        print(f"{pair} leverage is now set to : x{data['leverage']} with max notional to {data['maxNotionalValue']}")

    def get_account_info(self):
        return self._send_request(
            end_point=f"/fapi/v2/account",
            request_type="GET",
            signed=True
        )

    def get_pair_price(self, pair: str):
        return self._send_request(
            end_point=f"/fapi/v1/ticker/price",
            request_type="GET",
            params={"symbol": pair}
        )

    async def get_prod_candles(
            self,
            session,
            pair: str,
            interval: str,
            window: int,
            current_pair_state: dict = None
    ):

        url = "https://fapi.binance.com/fapi/v1/klines"

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

            df = self._format_data(all_data=data, historical=False)

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
                end_point=f"/fapi/v2/positionRisk",
                request_type="GET",
                params=_params,
                signed=True
        )

        position = {}

        for pos in all_pos:

            if (pos['symbol'] in pairs) and (float(pos['positionAmt']) != 0):
                position[pos['symbol']] = {}
                position[pos['symbol']]['position_size'] = abs(float(pos['positionAmt']))
                position[pos['symbol']]['entry_price'] = float(pos['entryPrice'])
                position[pos['symbol']]['unrealized_pnl'] = float(pos['unRealizedProfit'])
                position[pos['symbol']]['type_pos'] = 'LONG' if float(pos['positionAmt']) > 0 else 'SHORT'
                position[pos['symbol']]['exit_side'] = 'SELL' if float(pos['positionAmt']) > 0 else 'BUY'

        return position

    def get_token_balance(self, quote_asset: str):
        """
        Args:
            quote_asset: asset used for the trades (USD, USDT, BUSD, ...)

        Returns:
            Available based_asset amount.
        """

        balances = self._send_request(
            end_point=f"/fapi/v2/balance",
            request_type="GET",
            signed=True
        )

        for balance in balances:
            if balance['asset'] == quote_asset:
                return float(balance['availableBalance'])

    def get_order_book(self, pair: str):
        """
        Args:
            pair:

        Returns:
            the current orderbook with a depth of 20 observations
        """

        _params = {
            'symbol': pair,
            'limit': 20
        }

        data = self._send_request(
            end_point=f"/fapi/v1/depth",
            request_type="GET",
            params=_params
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

    @staticmethod
    def _format_order(data: dict):

        _price = 0.0 if data['type'] in ["MARKET", "STOP_MARKET", "TAKE_PROFIT"] else data['price']
        _stop_price = 0.0 if data['type'] in ["MARKET", "LIMIT"] else data['stopPrice']

        formatted = {
            'time': data['time'] if 'time' in list(data.keys()) else data['updateTime'],
            'order_id': data['orderId'],
            'pair': data['symbol'],
            'status': data['status'],
            'type': data['type'],
            'time_in_force': data['timeInForce'],
            'reduce_only': data['reduceOnly'],
            'side': data['side'],
            'price': float(_price),
            'stop_price': float(_stop_price),
            'original_quantity': float(data['origQty']),
            'executed_quantity': float(data['executedQty']),
            'executed_price': float(data['avgPrice'])
        }

        return formatted

    def get_order(self, pair: str, order_id: str):
        """
        Args:
            pair: pair traded in the order
            order_id: order id

        Returns:
            order information from binance
        """
        data = self._send_request(
            end_point=f"/fapi/v1/order",
            request_type="GET",
            params={"symbol": pair, "orderId": order_id},
            signed=True
        )

        return self._format_order(data)

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
            end_point=f"/fapi/v1/userTrades",
            request_type="GET",
            params={"symbol": pair, "startTime": results['time']},
            signed=True
        )

        results['quote_asset'] = None
        results['tx_fee_in_quote_asset'] = 0
        results['tx_fee_in_other_asset'] = {}
        results['nb_of_trades'] = 0
        results['is_buyer'] = None

        for trade in trades:
            if trade['orderId'] == order_id:
                if results['quote_asset'] is None:
                    results['quote_asset'] = trade['marginAsset']
                if results['is_buyer'] is None:
                    results['is_buyer'] = trade['buyer']
                if trade['commissionAsset'] != trade['marginAsset']:
                    if trade['commissionAsset'] not in results['tx_fee_in_other_asset'].keys():
                        results['tx_fee_in_other_asset'][trade['commissionAsset']] = float(trade['commission'])
                    else:
                        results['tx_fee_in_other_asset'][trade['commissionAsset']] += float(trade['commission'])
                else:
                    results['tx_fee_in_quote_asset'] += float(trade['commission'])
                results['nb_of_trades'] += 1

        for key, value in results['tx_fee_in_other_asset'].items():
            price_info = self.get_pair_price(f'{key}{results["quote_asset"]}')
            results['tx_fee_in_quote_asset'] += float(price_info['price']) * value

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

        side = 'BUY' if type_pos == 'LONG' else 'SELL'

        _params = {
            "symbol": pair,
            "side": side,
            "quantity": float(round(quantity, self.pairs_info[pair]['quantityPrecision'])),
            "type": "MARKET",
        }

        response = self._send_request(
            end_point=f"/fapi/v1/order",
            request_type="POST",
            params=_params,
            signed=True
        )

        return self.get_order_trades(
            pair=pair,
            order_id=response['orderId']
        )

    def exit_market_order(self, pair: str, type_pos: str, quantity: float):
        """

        Args:
            pair: pair id that we want to create the order for
            type_pos: could be 'BUY' or 'SELL'
            quantity: quantity should respect the minimum precision

        Returns:
                standardized output
        """
        side = 'SELL' if type_pos == 'LONG' else 'BUY'

        _params = {
            "symbol": pair,
            "side": side,
            "quantity": float(round(quantity, self.pairs_info[pair]['quantityPrecision'])),
            "type": "MARKET",
            "reduceOnly": "true"
        }

        response = self._send_request(
            end_point=f"/fapi/v1/order",
            request_type="POST",
            params=_params,
            signed=True
        )

        return self.get_order_trades(
            pair=pair,
            order_id=response['orderId']
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
            "symbol": pair,
            "reduceOnly": "true",
            "side": side,
            "type": 'TAKE_PROFIT',
            "timeInForce": 'GTC',
            "price": float(round(tp_price,  self.pairs_info[pair]['pricePrecision'])),
            "stopPrice": float(round(tp_price,  self.pairs_info[pair]['pricePrecision'])),
            "quantity": float(round(quantity, self.pairs_info[pair]['quantityPrecision']))
        }

        data = self._send_request(
            end_point=f"/fapi/v1/order",
            request_type="POST",
            params=_params,
            signed=True
        )

        while 'code' in data.keys():

            multiplier = 1.005 if side == 'SELL' else 0.995
            _params['stopPrice'] = float(round(_params['stopPrice'] * multiplier,
                                               self.pairs_info[pair]['pricePrecision']))
            _params['price'] = float(round(_params['price'] * multiplier, self.pairs_info[pair]['pricePrecision']))

            del _params['signature']
            del _params['timestamp']

            print(f'Placing TP new_price {_params["stopPrice"]}')
            time.sleep(1)

            data = self._send_request(
                end_point=f"/fapi/v1/order",
                request_type="POST",
                params=_params,
                signed=True
            )

        return self._format_order(data)

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
            "symbol": pair,
            "side": side,
            "type": 'STOP_MARKET',
            "timeInForce": 'GTC',
            "stopPrice": float(round(sl_price, self.pairs_info[pair]['pricePrecision'])),
            "quantity": float(round(quantity, self.pairs_info[pair]['quantityPrecision'])),
            "reduceOnly": "true"
        }

        data = self._send_request(
            end_point=f"/fapi/v1/order",
            request_type="POST",
            params=_params,
            signed=True
        )

        while 'code' in data.keys():

            multiplier = 1.005 if side == 'BUY' else 0.995
            _params['stopPrice'] = float(round(_params['stopPrice'] * multiplier,
                                               self.pairs_info[pair]['pricePrecision']))

            del _params['signature']
            del _params['timestamp']

            print(f'Placing SL new_price {_params["stopPrice"]}')

            time.sleep(1)

            data = self._send_request(
                end_point=f"/fapi/v1/order",
                request_type="POST",
                params=_params,
                signed=True
            )

        return self._format_order(data)

    def _verify_limit_posted(self,
                             pair: str,
                             order_id: str):
        """
        When posting a limit order (with time_in_force='PostOnly') the order can be immediately canceled if its
        price is too high for buy orders and to low for a sell orders. Sometimes the first order book changes too
        quickly that the first buy or sell order prices are no longer the same since the time we retrieve the OB. This
        can eventually get our limit order automatically canceled and never posted. Thus each time we send a limit order
        we verify that the order is posted.

        Args:
            pair:
            order_id:

        Returns:
            This function returns True if the limit order has been posted, False else.
        """

        t_start = time.time()
        # try to request the order in the next 5 seconds
        while time.time() - t_start < 5:

            order_data = self.get_order(
                pair=pair,
                order_id=order_id
            )

            if order_data['status'] != ['EXPIRED', 'CANCELED']:
                return True, order_data

            time.sleep(1)

        return False, None

    def place_limit_order_best_price(
            self,
            pair: str,
            side: str,
            quantity: float,
            reduce_only: bool = False
    ):

        """

        Args:
            pair: pair
            side:
            quantity:
            reduce_only:

        Returns:

        """

        ob = self.get_order_book(pair=pair)
        _type = 'bids' if side == 'BUY' else 'asks'
        best_price = float(ob[_type][0]['price'])

        _params = {
            "symbol": pair,
            "side": side,
            "quantity": float(round(quantity, self.pairs_info[pair]['quantityPrecision'])),
            "type": "LIMIT",
            "price": float(round(best_price, self.pairs_info[pair]['pricePrecision'])),
            "timeInForce": "GTX",
            "reduceOnly": "true" if reduce_only else "false"
        }

        response = self._send_request(
            end_point=f"/fapi/v1/order",
            request_type="POST",
            params=_params,
            signed=True
        )

        if 'orderId' in list(response.keys()):
            return self._verify_limit_posted(
                order_id=response['orderId'],
                pair=pair
            )
        else:
            return False, response

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
            reduce_only: True if we are exiting a position
            duration: number of seconds we keep trying to enter in position with limit orders

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
    
    def _enter_limit_then_market(self,
                                 pair,
                                 type_pos,
                                 quantity,
                                 sl_price,
                                 tp_price,
                                 ):
        """
        Optimized way to enter in position. The method tries to enter with limit orders during 2 minutes.
        If after 2min we still did not enter with the desired amount, a market order is sent.

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

    def _format_enter_limit_info(self, all_orders: list, tp_order: dict, sl_order: dict):

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
                    final_data['current_position_size'] += _trades['executed_quantity']
                    _price_information.append({'price': _trades['executed_price'], 'qty': _trades['executed_quantity']})

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

            print('IN BETWEEN TP EXECUTION')
            # TP activation between verification and execution
            trades = self._send_request(
                end_point=f"/fapi/v1/userTrades",
                request_type="GET",
                params={"symbol": data['tp']['pair'], "startTime": data['tp']['time']},
                signed=True
            )

            for trade in trades:
                if trade['orderId'] == tp_id:
                    tp_execution['executed_quantity'] += float(trade['qty'])
                    tp_execution['executed_price'] = float(trade['price'])
                    tp_execution['tx_fee_in_quote_asset'] += float(trade['commission'])

            all_orders.append(tp_execution)

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

    def cancel_order(self, pair: str, order_id: str):
        data = self._send_request(
            end_point=f"/fapi/v1/order",
            request_type="DELETE",
            params={"symbol": pair, "orderId": order_id},
            signed=True
        )

        if 'code' not in list(data.keys()):
            print(f'Order id : {order_id} has been Cancelled')
        else:
            if data['code'] == -2011:
                print(f'Order id : {order_id} has been already Cancelled')
            else:
                print(data['msg'])

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

    def get_last_price(self, pair: str) -> dict:
        """
        Args:
            pair: pair desired
        Returns:
            a dictionary containing the pair_id, latest_price, price_timestamp in timestamp
        """
        data = self._send_request(
            end_point=f"/fapi/v1/ticker/price",
            request_type="GET",
            params={"symbol": pair}
        )

        return {
            'pair': data['symbol'],
            'timestamp': data['time'],
            'latest_price': float(data['price'])
        }

