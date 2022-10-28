import time
from nova.utils.helpers import interval_to_milliseconds
from nova.utils.constant import DATA_FORMATING
import pandas as pd
from requests import Request, Session
import hmac
import hashlib
import base64
import numpy as np
from typing import Union
import aiohttp
import asyncio
import datetime


class Kraken:

    def __init__(
            self,
            key: str,
            secret: str,
            testnet: bool = False
    ):

        self.api_key = key
        self.api_secret = secret
        self.based_endpoint = "https://futures.kraken.com/derivatives"

        if testnet:
            self.based_endpoint = "https://demo-futures.kraken.com/derivatives"

        self._session = Session()

        self.historical_limit = 4990

        self.pairs_info = self.get_pairs_info()

    def _send_request(self, end_point: str,
                      request_type: str,
                      signed: bool = False,
                      params: str = "",
                      is_ohlc: bool = False):

        to_use = "https://futures.kraken.com/derivatives" if not signed else self.based_endpoint

        if is_ohlc:
            to_use = 'https://futures.kraken.com'

        final_end_point = end_point

        if params != "":
            final_end_point += '?' + params

        request = Request(request_type, f'{to_use}{final_end_point}')
        prepared = request.prepare()
        prepared.headers['Content-Type'] = "application/json;charset=utf-8"
        prepared.headers['User-Agent'] = "NovaLabs"

        if signed:
            prepared.headers['apiKey'] = self.api_key
            nonce = str(int(time.time() * 1000))
            concat_str = (params + nonce + end_point).encode()
            sha256_hash = hashlib.sha256(concat_str).digest()

            signature = hmac.new(base64.b64decode(self.api_secret),
                                 sha256_hash,
                                 hashlib.sha512
                                 )

            rebase = base64.b64encode(signature.digest())

            prepared.headers['nonce'] = nonce
            prepared.headers['authent'] = rebase.decode()

        response = self._session.send(prepared)

        return response.json()

    @staticmethod
    def get_server_time() -> int:
        """
        Returns:
            the timestamp in milliseconds
        """
        return int(time.time() * 1000)

    def get_pairs_info(self):
        data = self._send_request(
            end_point=f"/api/v3/instruments",
            request_type="GET",
        )['instruments']

        output = {}

        for pair in data:

            if pair['type'] == 'flexible_futures' and pair['tradeable']:

                decimal_notation = np.format_float_positional(pair['tickSize'], trim="-")
                decimal = decimal_notation[::-1].find('.')

                precision = pair['tickSize'] if pair['tickSize'] >= 1 else decimal

                output[pair['symbol']] = {}
                output[pair['symbol']]['quote_asset'] = "USD"
                output[pair['symbol']]['tick_size'] = float(pair['tickSize'])
                output[pair['symbol']]['pricePrecision'] = precision
                output[pair['symbol']]['maxQuantity'] = pair['maxPositionSize']
                output[pair['symbol']]['minQuantity'] = 1 / (10 ** pair['contractValueTradePrecision'])
                output[pair['symbol']]['quantityPrecision'] = pair['contractValueTradePrecision']

        return output

    def get_order_book(self, pair: str):
        """
        Args:
            pair:

        Returns:
            the current orderbook with a depth of 20 observations
        """

        data = self._send_request(
            end_point=f"/api/v3/orderbook?symbol={pair}",
            request_type="GET",
        )['orderBook']

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

        _start_time = start_time // 1000
        _end_time = end_time // 1000

        return self._send_request(
            end_point=f"/api/charts/v1/trade/{pair}/{interval}?from={_start_time}&to={_end_time}",
            request_type="GET",
            is_ohlc=True
        )['candles']

    def _get_earliest_timestamp(self, pair: str, interval: str):
        """
        Args:
            pair: Name of symbol pair
            interval: Binance Kline interval

        return:
            the earliest valid open timestamp
        """
        data = self._get_candles(
            pair=pair,
            interval='1w',
            start_time=1451624400000,
            end_time=int(time.time() * 1000),
        )
        return int(data[0]['time'])

    @staticmethod
    def _format_data(all_data: list, historical: bool = True) -> pd.DataFrame:
        """
        Args:
            all_data: output from _full_history

        Returns:
            standardized pandas dataframe
        """

        df = pd.DataFrame(all_data)

        df.columns = DATA_FORMATING['kraken']['columns']

        for var in DATA_FORMATING['kraken']['num_var']:
            df[var] = pd.to_numeric(df[var], downcast="float")

        if historical:
            df['next_open'] = df['open'].shift(-1)

        interval_ms = df['open_time'].iloc[1] - df['open_time'].iloc[0]

        df['close_time'] = df['open_time'] + interval_ms - 1

        for var in ['open_time', 'close_time']:
            df[var] = df[var].astype(int)

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

        # establish first available start timestamp
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
                output_data += temp_data

            # handle the case where exactly the limit amount of data was returned last loop
            # check if we received less than the required limit and exit the loop
            if not len(temp_data) or len(temp_data) < self.historical_limit:
                # exit the while loop
                break

            # increment next call by our timeframe
            start_time = temp_data[-1]['time'] + timeframe

            # exit loop if we reached end_ts before reaching <limit> klines
            if end_ts and start_time >= end_ts:
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

            pair = pair.upper()

            _set_leverage = self._send_request(
                end_point=f"/api/v3/leveragepreferences",
                params=f"symbol={pair}&maxLeverage={leverage}",
                request_type="PUT",
                signed=True
            )

            if _set_leverage['result'] == 'success':
                print(f'Leverage of {pair} set to {leverage}')

            _set_pnl_payment = self._send_request(
                end_point=f"/api/v3/pnlpreferences",
                request_type="PUT",
                params=f"symbol={pair}&pnlPreference={quote_asset}",
                signed=True
            )

            if _set_pnl_payment['result'] == 'success':
                print(f'PnL for {pair} is paid in {quote_asset}')

        balance = self.get_token_balance(quote_asset)

        assert balance >= bankroll * (1 + max_down), f"The account has only {round(balance, 2)} {quote_asset}. " \
                                                     f"{round(bankroll * (1 + max_down), 2)} {quote_asset} is required"

    def get_token_balance(self, quote_asset: str):

        account_info = self._send_request(
            end_point=f"/api/v3/accounts",
            request_type="GET",
            signed=True
        )['accounts']

        print(f"The current amount is : {account_info['flex']['currencies'][quote_asset]['value']} {quote_asset}")

        return round(account_info['flex']['currencies'][quote_asset]['value'], 2)

    def get_actual_positions(self, pairs: Union[list, str]) -> dict:
        """
        Args:
            pairs: list of pair that we want to run analysis on
        Returns:
            a dictionary containing all the current OPEN positions
        """

        if isinstance(pairs, str):
            pairs = [pairs]

        all_pos = self._send_request(
            end_point=f"/api/v3/openpositions",
            request_type="GET",
            signed=True,
        )['openPositions']

        position = {}

        for pos in all_pos:

            if pos['symbol'] in pairs and pos['size'] != 0:
                position[pos['symbol']] = {}
                position[pos['symbol']]['position_size'] = abs(float(pos['size']))
                position[pos['symbol']]['entry_price'] = float(pos['price'])
                position[pos['symbol']]['unrealized_pnl'] = float(pos['unrealizedFunding'])
                position[pos['symbol']]['type_pos'] = pos['side'].upper()
                position[pos['symbol']]['exit_side'] = 'SELL' if pos['side'].upper() == "LONG" else 'BUY'

        return position

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

        url = f"https://futures.kraken.com/api/charts/v1/trade/{pair}/{interval}?from={start_time}&to={end_time}"

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

            df = self._format_data(all_data=data['candles'], historical=False)

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

    def get_last_price(self, pair: str) -> dict:
        """
        Args:
            pair: pair desired
        Returns:
            a dictionary containing the pair_id, latest_price, price_timestamp in timestamp
        """
        data = self._send_request(
            end_point=f"/api/v3/tickers",
            request_type="GET",
            signed=False
        )['tickers']

        for info in data:
            if info['symbol'] == pair:
                dt = datetime.datetime.strptime(info['lastTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
                return {
                    'pair': info['symbol'],
                    'timestamp': int(dt.timestamp() * 1000),
                    'latest_price': float(info['last'])
                }

    def get_order(self, pair: str, order_id: str):

        data = self._send_request(
            end_point=f"/api/v3/editorder",
            request_type="POST",
            params=f'orderId={order_id}',
            signed=True
        )

        return data

    def cancel_order(self, pair: str, order_id: str):

        data = self._send_request(
            end_point=f"/api/v3/cancelorder",
            request_type="POST",
            params=f'order_id={order_id}',
            signed=True
        )

        return data

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

        response = self._send_request(
            end_point=f"/api/v3/sendorder",
            request_type="POST",
            params=f"orderType=mkt&symbol={pair}&side={side}&size={quantity}",
            signed=True
        )['sendStatus']

        return response

        # return self.get_order_trades(
        #     pair=pair,
        #     order_id=response['id']
        # )

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

        response = self._send_request(
            end_point=f"/api/v3/sendorder",
            request_type="POST",
            params=f"orderType=mkt&symbol={pair}&side={side}&size={quantity}&reduceOnly=true",
            signed=True
        )['sendStatus']

        return response

        # return self.get_order_trades(
        #     pair=pair,
        #     order_id=response['id']
        # )


