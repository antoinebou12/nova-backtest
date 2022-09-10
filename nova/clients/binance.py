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
from multiprocessing import Process, Manager


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
        return response.json()

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

        if historical:
            df['next_open'] = df['open'].shift(-1)
            return df.dropna()
        else:
            df['open_time_datetime'] = pd.to_datetime(df['open_time'], unit='ms')
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
            list_pairs: todo:  execute setup only if asset in list
            bankroll:
            max_down:

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

            if x["asset"] == quote_asset:
                # Assert_1: The account need to have the minimum bankroll
                assert float(x['availableBalance']) >= bankroll * (1 + max_down), f"The account has only {round(balance, 2)} {quote_asset}. " \
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
                    if fil['filterType'] == 'MARKET_LOT_SIZE':
                        output[symbol['symbol']]['max_market_trading_qty'] = fil['maxQty']
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
            df = self._format_data(all_data=data, historical=False)
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

    def get_token_balance(self, quote_asset: str):
        """
        Args:
            quote_asset: asset used for the trades (USD, USDT, BUSD, ...)

        Returns:
            Available based_asset amount.
        """
        balances = self.get_balance()
        for balance in balances:
            if balance['asset'] == quote_asset:
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

    def enter_market_order(self, pair: str, side: str, quantity: float):

        """
            Args:
                pair: pair id that we want to create the order for
                side: could be 'BUY' or 'SELL'
                quantity: quantity should respect the minimum precision

            Returns:
                standardized output containing time, pair, order_id, quantity, price, side, is_position_closing
        """
        
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

    def exit_market_order(self, pair: str, side: str, quantity: float):

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

    def _verify_limit_order_posted(self,
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

        last_active_order = None
        t_start = time.time()

        # Keep trying to get order status during 30s
        while time.time() - t_start < 30:

            time.sleep(5)

            last_active_order = self.get_order(
                pair=pair,
                order_id=order_id
            )

            if last_active_order:
                break

        if not last_active_order:
            return False

        return last_active_order['status'] != 'CANCELLED'

    def _limit_order_best_price(self,
                                pair: str,
                                side: str,
                                qty: float,
                                reduce_only: bool = False
                                ):

        """

        Args:
            pair:
            side:
            qty:
            reduce_only:

        Returns:

        """
        ob = self.get_order_book(pair=pair)
        _type = 'bids' if side == 'BUY' else 'asks'
        price = float(ob[_type][0]['price'])

        _params = {
            "symbol": pair,
            "side": side,
            "quantity": float(round(qty, self.pairs_info[pair]['quantityPrecision'])),
            "type": "LIMIT",
            "price": float(round(price, self.pairs_info[pair]['pricePrecision'])),
            "timeInForce": "GTX",
            "reduceOnly": "true" if reduce_only else "false"
        }

        response = self._send_request(
            end_point=f"/fapi/v1/order",
            request_type="POST",
            params=_params,
            signed=True
        )

        if not response:
            return False, ''

        limit_order_posted = self._verify_limit_order_posted(
            order_id=response['orderId'],
            pair=pair
        )

        return limit_order_posted, response

    def _looping_limit_orders(
            self,
            pair: str,
            side: str,
            position_size: float,
            duration: int,
            reduce_only: bool
    ):
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

            posted, order = self._limit_order_best_price(
                pair=pair,
                side=side,
                qty=residual_size,
                reduce_only=reduce_only
            )

            if posted:

                all_limit_orders.append(order)

                new_price = order['price']
                order_status = order['status']

                # If the best order book price stays the same, do not cancel current order
                while (new_price == order['price']) and (time.time() - t_start < 120) and (order_status != 'FILLED'):
                    time.sleep(10)

                    ob = self.get_order_book(pair=pair)
                    _type = 'bids' if side == 'BUY' else 'asks'

                    new_price = float(ob[_type][0]['price'])

                    order_status = self.get_order(pair=pair, order_id=order['orderId'])

                # Cancel order
                self.cancel_order(
                    pair=pair,
                    order_id=order['orderId']
                )

                # Get current position size
                pos_info = self.get_position_info(pair=pair)

                if reduce_only:
                    residual_size = pos_info[0]['size']
                else:
                    residual_size = position_size - pos_info[0]['size']

        return {'residual_size': residual_size, 'all_limit_orders': all_limit_orders}
    
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

        after_looping_limit = self._looping_limit_orders(
            pair=pair,
            side=side,
            position_size=qty,
            duration=120,
            reduce_only=False
        )

        residual_size = after_looping_limit['residual_size']
        all_orders = after_looping_limit['all_limit_orders']

        # If there is residual, enter with market order
        if residual_size != 0:
            market_order = self.enter_market_order(
                pair=pair,
                side=side,
                quantity=residual_size
            )

            all_orders.append(market_order)

        # Get current position info
        pos_info = self.get_position_info(pair=pair)

        exit_side = 'SELL' if side == 'BUY' else 'BUY'

        # Place take profit limit order
        self.place_limit_tp(pair=pair,
                            side=exit_side,
                            position_size=pos_info[0]['size'],
                            tp_prc=tp_price
                            )

        self.place_market_sl(pair=pair,
                             side=exit_side,
                             position_size=pos_info[0]['size'],
                             sl_prc=sl_price
                             )

        return_dict[pair] = all_orders

    def enter_limit_then_market(self, pair: str, side: str, qty: float, price: float, tp_price, sl_price: float):
        pass

    def exit_limit_then_market(self, pair: str, side: str, position_size: float):
        pass

    def place_limit_tp(self, pair: str, side: str, position_size: float, tp_prc: float):
        """
        Args:
            pair: pair id that we want to create the order for
            side: could be 'BUY' or 'SELL'
            position_size: for binance  quantity is not needed since the tp order "closes" the "opened" position
            tp_prc: price of the tp or sl
        Returns:
            Standardized output
        """
        _params = {
            "symbol": pair,
            "side": side,
            "type": 'TAKE_PROFIT',
            "timeInForce": 'GTC',
            "price": float(round(tp_prc,  self.pairs_info[pair]['pricePrecision'])),
            "stopPrice": float(round(tp_prc,  self.pairs_info[pair]['pricePrecision'])),
            "quantity": float(round(position_size, self.pairs_info[pair]['quantityPrecision']))
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

    def place_market_sl(self, pair: str, side: str, position_size: float, sl_prc: float):
        """
        Args:
            pair: pair id that we want to create the order for
            side: could be 'BUY' or 'SELL'
            position_size: for binance  quantity is not needed since the tp order "closes" the "opened" position
            sl_prc: price of the tp or sl
        Returns:
            Standardized output
        """
        _params = {
            "symbol": pair,
            "side": side,
            "type": 'STOP_MARKET',
            "timeInForce": 'GTC',
            "price": float(round(sl_prc, self.pairs_info[pair]['pricePrecision'])),
            "stopPrice": float(round(sl_prc, self.pairs_info[pair]['pricePrecision'])),
            "quantity": float(round(position_size, self.pairs_info[pair]['quantityPrecision'])),
            "reduceOnly": "true"
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

    def get_order_book(self,
                       pair):

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
