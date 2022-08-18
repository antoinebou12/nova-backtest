from nova.utils.helpers import interval_to_milliseconds
from nova.utils.constant import DATA_FORMATING, STD_CANDLE_FORMAT
from requests import Request, Session
from urllib.parse import urlencode
import pandas as pd
import aiohttp
import asyncio
import hashlib
import time
import hmac


class Binance:

    def __init__(self,
                 key: str,
                 secret: str):

        self.api_key = key
        self.api_secret = secret

        self.based_endpoint = "https://fapi.binance.com"
        self._session = Session()

        self.historical_limit = 1000
        self.pair_info = self._get_pair_info()

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
        return response.json()

    # GENERAL INFORMATION
    def get_exchange_info(self):
        return self._send_request(
            end_point=f"/fapi/v1/exchangeInfo",
            request_type="GET",
        )

    # STANDARDIZED BACKTEST
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

    def get_all_pairs(self) -> list:
        """
        Note:
            Only stable coins pairs will be filtered [BUSD / USDT]
        Returns:
             list of all the pairs that we can trade on.
        """
        info = self.get_exchange_info()
        list_pairs = []
        for pair in info['symbols']:
            if 'BUSD' or 'USDT' in pair['symbol']:
                list_pairs.append(pair['symbol'])
        return list_pairs

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

    def _get_earliest_valid_timestamp(self, pair: str, interval: str):
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
            start_time=0,
            end_time=int(time.time() * 1000),
            limit=1
        )
        return kline[0][0]

    def _combine_history(self, pair: str, interval: str, start_time: int, end_time: int):
        """
        Args:
            pair: pair to get information from
            interval: granularity of the candle ['1m', '1h', ... '1d']
            start_time: timestamp in milliseconds of the starting date
            end_time: timestamp in milliseconds of the end date
        Returns:
            the complete raw data history desired -> multiple requested could be executed
        """

        # init our list
        output_data = []

        # convert interval to useful value in seconds
        timeframe = interval_to_milliseconds(interval)

        # if a start time was passed convert it
        start_ts = start_time

        # establish first available start timestamp
        if start_ts is not None:
            first_valid_ts = self._get_earliest_valid_timestamp(
                pair=pair,
                interval=interval
            )
            start_ts = max(start_ts, first_valid_ts)

        # if an end time was passed convert it
        end_ts = end_time
        if end_ts and start_ts and end_ts <= start_ts:
            return output_data

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

        return output_data

    def _format_data(self, all_data: list, historical: bool = True) -> pd.DataFrame:
        """
        Args:
            all_data: output from _combine_history

        Returns:
            standardized pandas dataframe
        """
        # Remove the last row if it's not finished yet
        if historical:
            if self.get_server_time() < all_data[-1][6]:
                del all_data[-1]

        df = pd.DataFrame(all_data, columns=DATA_FORMATING['binance']['columns'])

        for var in DATA_FORMATING['binance']['num_var']:
            df[var] = pd.to_numeric(df[var], downcast="float")

        df = df[STD_CANDLE_FORMAT]
        if historical:
            df['next_open'] = df['open'].shift(-1)
            return df.dropna()
        else:
            df['open_time_datetime'] = pd.to_datetime(df['open_time'], unit='ms')
            return df.dropna()

    def get_historical(self, pair: str, interval: str, start_time: int, end_time: int) -> pd.DataFrame:
        """
        Args:
            pair: pair to get information from
            interval: granularity of the candle ['1m', '1h', ... '1d']
            start_time: timestamp in milliseconds of the starting date
            end_time: timestamp in milliseconds of the end date
        Returns:
            historical data requested in a standardized pandas dataframe
        """

        data = self._combine_history(
            pair=pair,
            interval=interval,
            start_time=start_time,
            end_time=end_time
        )

        return self._format_data(all_data=data)

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
        data = self._combine_history(
            pair=pair,
            interval=interval,
            start_time=end_date_data_ts,
            end_time=now_date_ts
        )
        format_df = self._format_data(all_data=data)
        return pd.concat([current_df, format_df], ignore_index=True).drop_duplicates()

    # BINANCE SPECIFIC FUNCTION
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

    def _get_pair_info(self) -> dict:
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
            output[symbol['symbol']] = {}

            for fil in symbol['filters']:
                if fil['filterType'] == 'PRICE_FILTER':
                    tick_size = str(float(fil['tickSize']))
                    output[symbol['symbol']]['pricePrecision'] = min(tick_size[::-1].find('.'),
                                                                     symbol['pricePrecision'])
                if fil['filterType'] == 'LOT_SIZE':
                    step_size = str(float(fil['stepSize']))
                    output[symbol['symbol']]['quantityPrecision'] = min(step_size[::-1].find('.'),
                                                                        symbol['quantityPrecision'])
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

    def get_position_info(self, pair: str = None):
        _params = {}
        if pair:
            _params['symbol'] = pair

        # get a standardized return
        return self._send_request(
            end_point=f"/fapi/v2/positionRisk",
            request_type="GET",
            params=_params,
            signed=True
        )

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

    def get_balance(self) -> dict:
        return self._send_request(
            end_point=f"/fapi/v2/balance",
            request_type="GET",
            signed=True
        )

    # STANDARDIZED BOT
    def setup_account(self, base_asset: str, leverage: int, bankroll: float):
        """
        Note: We execute verification of the account (balance, leverage, etc.)

        Args:
            base_asset:
            leverage:
            bankroll:

        Returns:
            None
        """
        accounts = self.get_account_info()
        positions_info = self.get_position_info()
        position_mode = self.get_position_mode()

        for info in positions_info:

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

            if x["asset"] == base_asset:
                # Assert_1: The account need to have the minimum bankroll
                assert float(x['availableBalance']) >= bankroll
                # Assert_2: The account has margin available
                assert x['marginAvailable']

            if x['asset'] == "BNB" and float(x["availableBalance"]) == 0:
                print(f"You can save Tx Fees if you transfer BNB in your Future Account")

    async def get_prod_candles(self, session, pair, interval, window, current_pair_state: dict = None):

        url = "https://fapi.binance.com/fapi/v1/klines"

        final_dict = {}
        final_dict[pair] = {}

        if current_pair_state is not None:
            limit = 3
        else:
            limit = window

        params = dict(symbol=pair, interval=interval, limit=limit)

        # Compute the server time
        s_time = self.get_server_time()

        async with session.get(url=url, params=params) as response:
            data = await response.json()
            df = self._format_data(data, historical=False)
            df = df[df['close_time'] < s_time]

            if current_pair_state is None:
                final_dict[pair]['latest_update'] = s_time
                final_dict[pair]['data'] = df

            else:
                df_new = pd.concat([current_pair_state['data'], df])
                df_new = df_new.drop_duplicates(subset=['open_time_datetime']).sort_values(by=['open_time_datetime'],
                                                                                           ascending=True)
                final_dict[pair]['latest_update'] = s_time
                final_dict[pair]['data'] = df_new.tail(window)

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

        last_info = {
            'pair_id': data['symbol'],
            'price_timestamp': data['time'],
            'latest_price': data['price']
        }

        return last_info

    def get_actual_positions(self, list_pair: list):
        """
        Args:
            list_pair: list of pair that we want to run analysis on
        Returns:
            a dictionary containing all the current OPEN positions
        """
        all_pos = self.get_position_info()
        position = {}

        for pos in all_pos:
            if (pos['symbol'] in list_pair) and (float(pos['positionAmt']) != 0):
                position[pos['symbol']] = {}
                position[pos['symbol']]['position_amount'] = pos['positionAmt']
                position[pos['symbol']]['entry_price'] = pos['entryPrice']
                position[pos['symbol']]['unrealized_pnl'] = pos['unRealizedProfit']

        return position

    def get_token_balance(self, based_asset: str):
        """
        Args:
            based_asset: asset used for the trades (USD, USDT, BUSD, ...)

        Returns:
            Available based_asset amount.
        """
        balances = self.get_balance()
        for balance in balances:
            if balance['asset'] == based_asset:
                return float(balance['availableBalance'])

    def get_order(self, pair: str, order_id: str):
        """
        Args:
            pair: pair traded in the order
            order_id: order id

        Returns:
            order information from binance
        """
        return self._send_request(
            end_point=f"/fapi/v1/order",
            request_type="GET",
            params={"symbol": pair, "orderId": order_id},
            signed=True
        )

    def get_order_trades(self, pair: str, order_id: str):
        """
        Args:
            pair: pair that is currently analysed
            order_id: order_id number

        Returns:
            standardize output of the trades needed to complete an order
        """

        order_data = self.get_order(
            pair=pair,
            order_id=order_id
        )
        trades = self._send_request(
            end_point=f"/fapi/v1/userTrades",
            request_type="GET",
            params={"symbol": pair, "startTime": order_data['time']},
            signed=True
        )

        results = {
            'time': order_data['time'],
            'pair': order_data['symbol'],
            'based_asset': None,
            'order_id': order_id,
            'tx_fee_in_based_asset': 0,
            'tx_fee_in_other_asset': {},
            'price': float(order_data['avgPrice']),
            'originalQuantity':  float(order_data['origQty']),
            'executedQuantity': float(order_data['executedQty']),
            'nb_of_trades': 0,
            'is_buyer': None,
            'order_status': order_data['status']
        }

        for trade in trades:
            if trade['orderId'] == order_id:
                if results['based_asset'] is None:
                    results['based_asset'] = trade['marginAsset']
                if results['is_buyer'] is None:
                    results['is_buyer'] = trade['buyer']
                if trade['commissionAsset'] != trade['marginAsset']:
                    if trade['commissionAsset'] not in results['tx_fee_in_other_asset'].keys():
                        results['tx_fee_in_other_asset'][trade['commissionAsset']] = float(trade['commission'])
                    else:
                        results['tx_fee_in_other_asset'][trade['commissionAsset']] += float(trade['commission'])
                else:
                    results['tx_fee_in_based_asset'] += float(trade['commission'])
                results['nb_of_trades'] += 1

        for key, value in results['tx_fee_in_other_asset'].items():
            price_info = self.get_pair_price(f'{key}{results["based_asset"]}')
            results['tx_fee_in_based_asset'] += float(price_info['price']) * value

        return results

    def open_close_order(self, pair: str, side: str, quantity: float, order_type: str, price: float = None):
        """
        Args:
            pair: pair id that we want to create the order for
            side: could be 'BUY' or 'SELL'
            quantity: quantity should respect the minimum precision
            price:
            order_type:

        Returns:
            standardized output containing time, pair, order_id, quantity, price, side, is_position_closing
        """
        _params = {
            "symbol": pair,
            "side": side,
            "quantity": float(round(quantity, self.pair_info[pair]['quantityPrecision'])),
            "type": "MARKET" if order_type == 'market' else "LIMIT"
        }

        if order_type == 'limit':
            _params["price"] = float(round(price, self.pair_info[pair]['pricePrecision']))

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

    def sl_market_order(self, pair: str, side: str, quantity: float, stop_price: float):

        _params = {
            "symbol": pair,
            "side": side,
            "type": 'STOP_MARKET',
            "timeInForce": 'GTC',
            "stopPrice": float(round(stop_price,  self.pair_info[pair]['pricePrecision'])),
        }

        data = self._send_request(
            end_point=f"/fapi/v1/order",
            request_type="POST",
            params=_params,
            signed=True
        )

        return {
            'time': data['updateTime'],
            'pair': data['symbol'],
            'order_id': data['orderId'],
            'type': data['type'],
            'sl_price': data['stopPrice'],
            'executedQty': data['executedQty']
        }

    def tp_order(self, pair: str, side: str, quantity: float, price: float, tp_type: str):
        """
        Args:
            pair: pair id that we want to create the order for
            side: could be 'BUY' or 'SELL'
            quantity: for binance  quantity is not needed since the tp order "closes" the "opened" position
            price: price of the tp or sl
            tp_type: 'market' or 'limit'
        Returns:
            Standardized output
        """
        _params = {
            "symbol": pair,
            "side": side,
            "type": 'TAKE_PROFIT' if tp_type == 'limit' else 'TAKE_PROFIT_MARKET',
            "timeInForce": 'GTC',
            "price": float(round(price,  self.pair_info[pair]['pricePrecision'])),
            "stopPrice": float(round(price,  self.pair_info[pair]['pricePrecision'])),
            "quantity": float(round(quantity, self.pair_info[pair]['quantityPrecision']))
        }

        data = self._send_request(
            end_point=f"/fapi/v1/order",
            request_type="POST",
            params=_params,
            signed=True
        )

        return {
            'time': data['updateTime'],
            'pair': data['symbol'],
            'order_id': data['orderId'],
            'type': data['type'],
            'tp_price': data['price'],
            'executedQty': data['executedQty']
        }

    def cancel_order(self, pair: str, order_id: str):
        return self._send_request(
            end_point=f"/fapi/v1/order",
            request_type="DELETE",
            params={"symbol": pair, "orderId": order_id},
            signed=True
        )

    def cancel_pair_orders(self, pair: str):
        return self._send_request(
            end_point=f"/fapi/v1/allOpenOrders",
            request_type="DELETE",
            params={"symbol": pair},
            signed=True
        )

    def get_tp_sl_state(self, pair: str, tp_id: str, sl_id: str):

        tp_info = self.get_order_trades(pair=pair, order_id=tp_id)
        sl_info = self.get_order_trades(pair=pair, order_id=sl_id)
        position_info = self.get_position_info(pair=pair)
        return {
            'tp': tp_info,
            'sl': sl_info,
            'current_quantity': position_info['positionAmt']
        }

    def get_order_book_prices(self, pair, ):
        pass

